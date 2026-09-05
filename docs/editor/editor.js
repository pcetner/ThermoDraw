// The editor. One file, no framework: state, the canvas, the interactions,
// the popover, the findings strip, the files panel, share and present.
//
// The library does every drawing. This script keeps the diagram as the
// JSON the schema describes, sends it to the worker after every edit, and
// puts back what comes out: the page's parts inside its own <svg>, one
// transparent rectangle per thing that can be clicked, and the findings.
// Nothing here knows how a symbol looks.
//
// The workflow it is built around: drag components in (nodes go anywhere,
// a path or a source lands on a node), double-click a node to connect it
// to another, click anything to edit it.

const $ = (id) => document.getElementById(id);
const BUILD = window.THERMODRAW;
const GRID = 10;
const snap = (v) => Math.round(v / GRID) * GRID;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

// ------------------------------------------------------------- the library
const rpc = (() => {
  const w = new Worker("worker.js", {type: "module"});
  const pending = new Map();
  const listeners = {};
  let n = 0;
  w.onmessage = (e) => {
    const m = e.data;
    if (m.type) { (listeners[m.type] || []).forEach((f) => f(m)); return; }
    const p = pending.get(m.id);
    if (!p) return;
    pending.delete(m.id);
    if (m.error) p.reject(new Error(m.error)); else p.resolve(m.result);
  };
  return {
    on(type, f) { (listeners[type] = listeners[type] || []).push(f); },
    boot() {
      w.postMessage({type: "boot", pyodide: BUILD.pyodide,
                     wheel: new URL(BUILD.wheel, location.href).href});
    },
    call(op, ...args) {
      return new Promise((resolve, reject) => {
        const id = ++n;
        pending.set(id, {resolve, reject});
        w.postMessage({id, op, args});
      });
    },
  };
})();

// ------------------------------------------------------------------ state
const BLANK = () => ({
  units: {R: "K/W", C: "J/K", T: "°C", P: "W", q: "W", "q″": "W/cm²"},
  nodes: [], branches: [], sources: [],
});

const S = {
  ready: false,
  file: null,            // {id, name}
  data: null,            // the diagram, as JSON
  scene: null,           // the last good scene from the library
  sel: null,             // {role, index} or null
  mode: "idle",          // idle | place | connect
  pending: null,         // place: the palette entry; connect: {fromId, kind}
  view: {x: 0, y: 0, w: 1000, h: 600},
  undo: [], redo: [],
  notation: "boxes", physics: false,
  inflight: false, dirty: false,
  present: false,
  touched: false,        // has the reader panned or zoomed since the last fit
};

const KINDS = {
  node: ["free", "fixed", "break", "phase"],
  branch: ["cond", "conv", "rad", "contact", "spread", "pipe", "mixed", "cap", "flow", "break"],
  source: ["diss", "radin", "flow", "flux"],
};
const NAMES = {};  // role:kind -> name, from the palette in the page
for (const b of document.querySelectorAll(".ed-card")) {
  NAMES[`${b.dataset.role}:${b.dataset.kind}`] = b.querySelector("span").textContent;
}
const kindName = (role, kind) => NAMES[`${role}:${kind}`] || kind;

// -------------------------------------------------------------- the model
const list = (role) => S.data[{node: "nodes", branch: "branches", source: "sources"}[role]];
const element = (sel) => (sel ? list(sel.role)[sel.index] : null);
const nodeById = (id) => S.data.nodes.find((n) => n.id === id);

function newNodeId() {
  const used = new Set(S.data.nodes.map((n) => n.id));
  for (let i = 1; ; i++) if (!used.has(`n${i}`)) return `n${i}`;
}

function snapshot() { return JSON.stringify(S.data); }

// Every edit goes through here: snapshot for undo, apply, save, redraw.
function edit(fn) {
  S.undo.push(snapshot());
  if (S.undo.length > 200) S.undo.shift();
  S.redo.length = 0;
  fn(S.data);
  afterEdit();
}

function afterEdit() {
  save();
  refresh();
  updateChrome();
}

function undo() {
  if (!S.undo.length) return;
  S.redo.push(snapshot());
  S.data = JSON.parse(S.undo.pop());
  select(null);
  afterEdit();
}
function redo() {
  if (!S.redo.length) return;
  S.undo.push(snapshot());
  S.data = JSON.parse(S.redo.pop());
  select(null);
  afterEdit();
}

function removeElement(sel) {
  const d = S.data;
  if (sel.role === "node") {
    const id = d.nodes[sel.index].id;
    d.nodes.splice(sel.index, 1);
    d.branches = d.branches.filter((b) => b.from !== id && b.to !== id);
    d.sources = d.sources.filter((s) => s.from !== id && s.to !== id);
    if (d.rail && d.rail.reference === id) delete d.rail;
  } else {
    list(sel.role).splice(sel.index, 1);
  }
}

function renameNode(oldId, newId) {
  const d = S.data;
  for (const n of d.nodes) if (n.id === oldId) n.id = newId;
  for (const b of d.branches) { if (b.from === oldId) b.from = newId; if (b.to === oldId) b.to = newId; }
  for (const s of d.sources) { if (s.from === oldId) s.from = newId; if (s.to === oldId) s.to = newId; }
  if (d.rail && d.rail.reference === oldId) d.rail.reference = newId;
}

// --------------------------------------------------------------- the view
const canvas = $("ed-canvas");
const drawing = $("ed-drawing");
const hitsG = $("ed-hits");
const ui = $("ed-ui");

function setView(v) {
  S.view = v;
  canvas.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
  if (S.sel) drawSelection();
}

function stageSize() {
  const r = canvas.getBoundingClientRect();
  return {w: Math.max(r.width, 1), h: Math.max(r.height, 1)};
}

function fit(box) {
  const ink = box || (S.scene && S.scene.ink);
  const st = stageSize();
  if (st.w < 50 || st.h < 50) return;   // not laid out yet; the observer refits
  if (!ink || ink[2] <= ink[0]) {
    setView({x: -st.w / 2, y: -st.h / 2, w: st.w, h: st.h});
    return;
  }
  const pad = 60;
  const w = ink[2] - ink[0] + 2 * pad, h = ink[3] - ink[1] + 2 * pad;
  // never closer than one unit per pixel: a lone node is small, not huge
  const scale = Math.max(w / st.w, h / st.h, 1);
  const vw = st.w * scale, vh = st.h * scale;
  setView({x: (ink[0] + ink[2]) / 2 - vw / 2, y: (ink[1] + ink[3]) / 2 - vh / 2, w: vw, h: vh});
}

// The stage's size settles after the page's first paint and changes with
// the window; until the reader has panned or zoomed, the drawing stays
// fitted through both.
new ResizeObserver(() => { if (!S.touched) fit(); }).observe($("ed-stage"));

function toPage(clientX, clientY) {
  const m = canvas.getScreenCTM();
  if (!m) return {x: 0, y: 0};
  const p = new DOMPoint(clientX, clientY).matrixTransform(m.inverse());
  return {x: p.x, y: p.y};
}
function toScreen(x, y) {
  const m = canvas.getScreenCTM();
  const p = new DOMPoint(x, y).matrixTransform(m);
  const r = $("ed-stage").getBoundingClientRect();
  return {x: p.x - r.left, y: p.y - r.top};
}
const unitsPerPixel = () => S.view.w / stageSize().w;

function zoomAt(clientX, clientY, factor) {
  S.touched = true;
  const p = toPage(clientX, clientY);
  const v = S.view;
  const f = clamp(factor, 0.2, 5);
  const w = clamp(v.w * f, 200, 20000);
  const h = v.h * (w / v.w);
  setView({x: p.x - (p.x - v.x) * (w / v.w), y: p.y - (p.y - v.y) * (h / v.h), w, h});
}

// --------------------------------------------------------------- drawing
function refresh() {
  if (!S.ready || !S.data) return;
  if (S.inflight) { S.dirty = true; return; }
  S.inflight = true;
  S.dirty = false;
  document.body.dataset.busy = "1";   // a test waits for this to clear
  rpc.call("scene", S.data, S.notation, S.physics).then((scene) => {
    S.inflight = false;
    if (scene.error) {
      showError(scene.error);
    } else {
      S.scene = scene;
      drawing.innerHTML = scene.parts;
      buildHits(scene.hits);
      showFindings(scene.findings);
      if (S.sel) drawSelection();
      if (S.mode === "connect") markFrom();
      if (!S.dirty && S.data.nodes.some((n) => !n.at)) bake();
    }
    $("ed-empty").hidden = S.data.nodes.length > 0;
    if (S.dirty) refresh(); else delete document.body.dataset.busy;
  }).catch((err) => {
    S.inflight = false;
    delete document.body.dataset.busy;
    showError(String(err));
  });
}

// A file with nodes the solver placed is drawn exactly as the solver
// placed it, so writing those coordinates into the file changes nothing
// on screen. It changes what a drag does: one node moves, instead of the
// solver re-flowing every unplaced node around the one that was pinned.
// Not an undo step; the drawing is the same.
let baking = false;
async function bake() {
  if (baking) return;
  baking = true;
  try {
    const solved = await rpc.call("solve", S.data);
    if (!solved.error && S.data.nodes.some((n) => !n.at)) {
      S.data = solved;
      save();
    }
  } finally { baking = false; }
}

function buildHits(hits) {
  hitsG.innerHTML = "";
  for (const h of hits) {
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    const [x0, y0, x1, y1] = h.bounds;
    // a finger needs something to land on: never thinner than 14 units
    const pad = (x1 - x0 < 14 || y1 - y0 < 14) ? 7 : 2;
    r.setAttribute("x", x0 - pad); r.setAttribute("y", y0 - pad);
    r.setAttribute("width", x1 - x0 + 2 * pad); r.setAttribute("height", y1 - y0 + 2 * pad);
    r.dataset.role = h.role; r.dataset.index = h.index; r.dataset.element = h.element;
    r.dataset.ref = h.ref; r.dataset.at = h.at.join(",");
    hitsG.appendChild(r);
  }
}

function hitsOf(sel) {
  return [...hitsG.children].filter((r) => r.dataset.role === sel.role && +r.dataset.index === sel.index);
}

function boundsOf(sel) {
  const rects = hitsOf(sel);
  if (!rects.length) return null;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of rects) {
    const x = +r.getAttribute("x"), y = +r.getAttribute("y");
    x0 = Math.min(x0, x); y0 = Math.min(y0, y);
    x1 = Math.max(x1, x + +r.getAttribute("width")); y1 = Math.max(y1, y + +r.getAttribute("height"));
  }
  return [x0, y0, x1, y1];
}

function svgEl(name, attrs, cls) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  if (cls) el.setAttribute("class", cls);
  return el;
}

function drawSelection() {
  ui.querySelectorAll(".ed-sel, .ed-via").forEach((e) => e.remove());
  if (!S.sel) return;
  const b = boundsOf(S.sel);
  if (!b) return;
  const upp = unitsPerPixel();
  ui.appendChild(svgEl("rect", {x: b[0] - 3, y: b[1] - 3, width: b[2] - b[0] + 6, height: b[3] - b[1] + 6, rx: 3}, "ed-sel"));
  const el = element(S.sel);
  if (S.sel.role === "branch" && el && el.via && el.via.length) {
    el.via.forEach(([x, y], i) => {
      const v = svgEl("circle", {cx: x, cy: y, r: 7 * upp}, "ed-via");
      v.dataset.via = i;
      ui.appendChild(v);
    });
  }
}

// -------------------------------------------------------------- findings
function showFindings(findings) {
  const list = $("ed-findings-list");
  list.innerHTML = "";
  const counts = {error: 0, warning: 0, note: 0};
  for (const f of findings) counts[f.severity] = (counts[f.severity] || 0) + 1;
  const parts = [];
  if (counts.error) parts.push(`<span class="ed-count-error">${counts.error} error${counts.error > 1 ? "s" : ""}</span>`);
  if (counts.warning) parts.push(`<span class="ed-count-warning">${counts.warning} warning${counts.warning > 1 ? "s" : ""}</span>`);
  if (counts.note) parts.push(`${counts.note} note${counts.note > 1 ? "s" : ""}`);
  const labels = S.scene ? `${S.scene.labels} labels placed` : "";
  $("ed-findings-count").innerHTML = parts.length ? `${labels}, ${parts.join(", ")}` : `${labels}, nothing to report`;
  for (const f of findings) {
    const li = document.createElement("li");
    li.className = `ed-sev-${f.severity}`;
    li.innerHTML = `<span class="ed-code">${f.severity}: ${escapeHtml(f.code)}</span><span>${escapeHtml(f.message)}<span class="ed-remedy">${escapeHtml(f.remedy)}</span></span>`;
    li.addEventListener("click", () => pointAt(f));
    list.appendChild(li);
  }
}

function pointAt(f) {
  if (f.at) {
    const v = S.view;
    setView({x: f.at[0] - v.w / 2, y: f.at[1] - v.h / 2, w: v.w, h: v.h});
  }
  for (const r of hitsG.children) {
    if (r.dataset.ref === f.where) {
      r.classList.remove("ed-flash"); void r.getBoundingClientRect(); r.classList.add("ed-flash");
    }
  }
}

function showError(text) {
  $("ed-findings-count").innerHTML = `<span class="ed-count-error">Cannot draw:</span> ${escapeHtml(text)}`;
  $("ed-findings-list").innerHTML = "";
  const pop = $("ed-popover");
  if (!pop.hidden) {
    let e = pop.querySelector(".ed-error");
    if (!e) { e = document.createElement("p"); e.className = "ed-error"; pop.appendChild(e); }
    e.textContent = text;
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
}

// ------------------------------------------------------------ interaction
let drag = null;  // {kind: element|pan|via, ...}
const pointers = new Map();
let pinch = null;
let lastTap = null;   // {sel, t, x, y} for a double-tap on touch

function hitAt(target) {
  const r = target && target.closest ? target.closest("#ed-hits rect") : null;
  return r ? {role: r.dataset.role, index: +r.dataset.index, element: r.dataset.element, rect: r} : null;
}

canvas.addEventListener("pointerdown", (e) => {
  if (S.present) return;
  pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinch = {d: Math.hypot(a.x - b.x, a.y - b.y), view: {...S.view}};
    drag = null;
    return;
  }
  closeQuick(); closeMenu();
  canvas.setPointerCapture(e.pointerId);
  const p = toPage(e.clientX, e.clientY);
  const via = e.target.dataset && e.target.dataset.via;
  if (via !== undefined && S.sel && S.sel.role === "branch") {
    drag = {kind: "via", sel: S.sel, i: +via, start: p, orig: [...element(S.sel).via[+via]], moved: false, snapshot: snapshot()};
    return;
  }
  const hit = hitAt(e.target);
  if (S.mode === "connect") {
    // connection mode: the next node clicked is the other end
    if (hit && hit.role === "node") finishConnect(S.pending.fromId, element(hit).id, S.pending.kind);
    else setMode("idle");
    return;
  }
  if (S.mode === "place" && S.pending) {
    if (S.pending.role === "node") { placeNode(S.pending.kind, p); return; }
    if (hit && hit.role === "node") { dropOnNode(S.pending, hit); return; }
    setMode("idle");
    return;
  }
  if (hit) {
    const movable = (hit.role === "node" && hit.element !== "label") || (hit.element === "symbol");
    drag = {kind: "element", hit, sel: {role: hit.role, index: hit.index}, start: p, moved: false, movable,
            orig: movable ? currentAt(hit) : null, snapshot: snapshot()};
    return;
  }
  drag = {kind: "pan", start: {x: e.clientX, y: e.clientY}, view: {...S.view}, moved: false};
  canvas.classList.add("ed-pan");
});

function currentAt(hit) {
  const el = element(hit);
  if (el.at) return [...el.at];
  // placed by the library, not the file: start from where it is drawn
  return hit.rect.dataset.at.split(",").map(Number);
}

canvas.addEventListener("pointermove", (e) => {
  if (pointers.has(e.pointerId)) pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
  if (pinch && pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    const d = Math.hypot(a.x - b.x, a.y - b.y);
    const mid = {x: (a.x + b.x) / 2, y: (a.y + b.y) / 2};
    const f = pinch.d / Math.max(d, 1);
    const v = pinch.view;
    const w = clamp(v.w * f, 200, 20000), h = v.h * (w / v.w);
    const p = toPage(mid.x, mid.y);
    S.touched = true;
    setView({x: p.x - (p.x - v.x) * (w / v.w), y: p.y - (p.y - v.y) * (h / v.h), w, h});
    return;
  }
  if (S.mode === "connect" && !drag) {
    const from = nodeById(S.pending.fromId);
    if (from && from.at) rubber({x: from.at[0], y: from.at[1]}, toPage(e.clientX, e.clientY));
  }
  if (!drag) { hover(e.target); return; }
  const p = toPage(e.clientX, e.clientY);
  const dx = p.x - drag.start.x, dy = p.y - drag.start.y;
  if (!drag.moved && Math.hypot(dx, dy) * (stageSize().w / S.view.w) < 4) return;
  drag.moved = true;
  if (drag.kind === "pan") {
    S.touched = true;
    const upp = unitsPerPixel();
    setView({...drag.view, x: drag.view.x - (e.clientX - drag.start.x) * upp, y: drag.view.y - (e.clientY - drag.start.y) * upp});
  } else if (drag.kind === "element" && drag.movable) {
    const el = element(drag.sel);
    el.at = [snap(drag.orig[0] + dx), snap(drag.orig[1] + dy)];
    refresh();
  } else if (drag.kind === "via") {
    element(drag.sel).via[drag.i] = [snap(drag.orig[0] + dx), snap(drag.orig[1] + dy)];
    refresh();
  }
});

canvas.addEventListener("pointerup", (e) => {
  pointers.delete(e.pointerId);
  if (pinch) { if (pointers.size < 2) pinch = null; return; }
  if (!drag) return;
  const d = drag; drag = null;
  canvas.classList.remove("ed-pan");
  const p = toPage(e.clientX, e.clientY);
  if (d.kind === "pan") {
    if (!d.moved) { select(null); openQuick(p, e.clientX, e.clientY); }
    return;
  }
  if (d.kind === "element") {
    if (d.moved && d.movable) {
      S.undo.push(d.snapshot); S.redo.length = 0;
      afterEdit();
      select(d.sel, false);
    } else {
      // a second tap on the same node within a moment is a double-tap: the
      // touch form of the double-click that starts a connection
      const now = performance.now();
      if (e.pointerType !== "mouse" && lastTap && lastTap.role === d.sel.role && lastTap.index === d.sel.index
          && now - lastTap.t < 400 && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 20) {
        lastTap = null;
        if (d.sel.role === "node") { startConnect(element(d.sel).id, "cond"); return; }
      }
      lastTap = {role: d.sel.role, index: d.sel.index, t: now, x: e.clientX, y: e.clientY};
      select(d.sel, true);
    }
    return;
  }
  if (d.kind === "via") {
    if (d.moved) { S.undo.push(d.snapshot); S.redo.length = 0; afterEdit(); }
  }
});
canvas.addEventListener("pointercancel", (e) => { pointers.delete(e.pointerId); drag = null; pinch = null; canvas.classList.remove("ed-pan"); });

// the double-click that starts a connection
canvas.addEventListener("dblclick", (e) => {
  if (S.present) return;
  // the pointer was captured on the way down, so the event's target is the
  // canvas; what is under the pointer is what was double-clicked
  const hit = hitAt(document.elementFromPoint(e.clientX, e.clientY));
  drag = null;
  if (hit && hit.role === "node") {
    e.preventDefault();
    startConnect(element(hit).id, "cond");
  }
});

function rubber(a, b) {
  let l = ui.querySelector(".ed-rubber");
  if (!l) { l = svgEl("line", {}, "ed-rubber"); ui.appendChild(l); }
  l.setAttribute("x1", a.x); l.setAttribute("y1", a.y); l.setAttribute("x2", b.x); l.setAttribute("y2", b.y);
}

let hovered = null;
function hover(target) {
  const hit = hitAt(target);
  const rects = hit ? hitsOf(hit) : [];
  if (hovered) hovered.forEach((r) => r.classList.remove("ed-hover"));
  rects.forEach((r) => r.classList.add("ed-hover"));
  hovered = rects;
}

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (e.ctrlKey || e.metaKey || Math.abs(e.deltaY) > 0 && !e.shiftKey) {
    zoomAt(e.clientX, e.clientY, Math.exp(e.deltaY * 0.0015));
  } else {
    const upp = unitsPerPixel();
    S.touched = true;
    setView({...S.view, x: S.view.x + e.deltaX * upp, y: S.view.y + e.deltaY * upp});
  }
}, {passive: false});

function select(sel, popover = true) {
  S.sel = sel;
  drawSelection();
  $("ed-delete").disabled = !sel;
  if (sel && popover) openPopover(sel); else closePopover();
}

// ------------------------------------------------------------------ modes
// What the drawing is waiting for, said in a pill at the top of the stage.
function setMode(mode, pending = null) {
  S.mode = mode; S.pending = pending;
  canvas.classList.toggle("ed-place", mode === "place");
  canvas.classList.toggle("ed-connect", mode === "connect");
  document.querySelectorAll(".ed-card").forEach((c) => c.setAttribute("aria-pressed",
    String(mode === "place" && pending && c.dataset.key === pending.key)));
  hitsG.querySelectorAll(".ed-from").forEach((r) => r.classList.remove("ed-from"));
  ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
  const pill = $("ed-mode");
  let text = "";
  if (mode === "connect") {
    const from = nodeById(pending.fromId);
    text = `Connecting from <b>${escapeHtml((from && from.label) || pending.fromId)}</b> with ${escapeHtml(kindName("branch", pending.kind).toLowerCase())}: click the node it joins`;
    markFrom();
  } else if (mode === "place" && pending) {
    text = pending.role === "node" ? `Click where the ${escapeHtml(kindName("node", pending.kind).toLowerCase())} goes`
         : pending.role === "source" ? `Click the node this ${escapeHtml(kindName("source", pending.kind).toLowerCase())} joins`
         : `Click the node this ${escapeHtml(kindName("branch", pending.kind).toLowerCase())} leaves from, then the node it reaches`;
  }
  pill.innerHTML = text ? `<span>${text}</span><button type="button" id="ed-mode-cancel">Cancel (Esc)</button>` : "";
  pill.hidden = !text;
  if (text) $("ed-mode-cancel").addEventListener("click", () => setMode("idle"));
}

function markFrom() {
  if (S.mode !== "connect") return;
  const idx = S.data.nodes.findIndex((n) => n.id === S.pending.fromId);
  hitsOf({role: "node", index: idx}).forEach((r) => r.classList.add("ed-from"));
}

function startConnect(fromId, kind) {
  closePopover();
  select(null);
  setMode("connect", {fromId, kind});
}

// ------------------------------------------------------------ adding
function placeNode(kind, p) {
  const id = newNodeId();
  edit((d) => {
    const n = {id, at: [snap(p.x), snap(p.y)]};
    if (kind !== "free") n.kind = kind;
    d.nodes.push(n);
  });
  setMode("idle");
  select({role: "node", index: S.data.nodes.length - 1});
}

// A path or a source dropped on a node: a source attaches there; a path
// starts a connection from there, with its kind, and waits for the other end.
function dropOnNode(entry, hit) {
  const id = element(hit).id;
  if (entry.role === "source") attachSource(entry.kind, id);
  else if (entry.role === "branch") startConnect(id, entry.kind);
}

// Which way a new source should arrive: the side of the node with nothing
// on it. The library's own habit is to arrive from the left (angle 0) and
// the solver turns an interior one to arrive from above; here the wires
// are known, so the emptiest of the four sides wins, above first.
function freeSide(nodeId) {
  const d = S.data;
  const node = nodeById(nodeId);
  if (!node || !node.at) return 0;
  const taken = [];
  const other = (a, b) => (a === nodeId ? b : a);
  for (const b of d.branches) {
    if (b.from !== nodeId && b.to !== nodeId) continue;
    const id = other(b.from, b.to);
    const n = nodeById(id);
    const to = b.via && b.via.length ? (b.from === nodeId ? b.via[0] : b.via[b.via.length - 1]) : (n && n.at);
    if (id === "rail") taken.push(90);
    else if (to) taken.push((Math.atan2(to[1] - node.at[1], to[0] - node.at[0]) * 180 / Math.PI + 360) % 360);
  }
  for (const s of d.sources) if ((s.to || s.from) === nodeId) taken.push(((s.angle || 0) + (s.from ? 0 : 180)) % 360);
  if (node.kind === "fixed" || node.kind === "break") taken.push({down: 90, up: 270, left: 180, right: 0}[node.wall || "down"]);
  const candidates = [90, 0, 270, 180];   // above, left, below, right
  const gap = (a) => Math.min(...taken.map((t) => { const dd = Math.abs(((a + 180) % 360) - t) % 360; return Math.min(dd, 360 - dd); }), 999);
  return candidates.reduce((best, a) => (gap(a) > gap(best) ? a : best), candidates[0]);
}

function attachSource(kind, nodeId) {
  const angle = freeSide(nodeId);
  edit((d) => {
    const s = {to: nodeId};
    if (kind !== "diss") s.kind = kind;
    if (angle) s.angle = angle;
    d.sources.push(s);
  });
  setMode("idle");
  select({role: "source", index: S.data.sources.length - 1});
}

function finishConnect(fromId, toId, kind) {
  setMode("idle");
  if (fromId === toId) { toast("A path needs two different nodes."); return; }
  edit((d) => {
    const b = {from: fromId, to: toId};
    if (kind !== "cond") b.kind = kind;
    d.branches.push(b);
  });
  select({role: "branch", index: S.data.branches.length - 1});
}

// the palette: tap to arm, drag to drop
let cardDrag = null;
document.querySelectorAll(".ed-card").forEach((card) => {
  const entry = {key: card.dataset.key, role: card.dataset.role, kind: card.dataset.kind};
  card.addEventListener("pointerdown", (e) => {
    card.setPointerCapture(e.pointerId);
    cardDrag = {entry, start: {x: e.clientX, y: e.clientY}, moved: false, ghost: null};
  });
  card.addEventListener("pointermove", (e) => {
    if (!cardDrag) return;
    if (!cardDrag.moved && Math.hypot(e.clientX - cardDrag.start.x, e.clientY - cardDrag.start.y) < 6) return;
    cardDrag.moved = true;
    if (!cardDrag.ghost) {
      const g = card.cloneNode(true);
      g.style.cssText = "position:fixed;z-index:20;width:110px;pointer-events:none;opacity:.85;margin:0";
      document.body.appendChild(g);
      cardDrag.ghost = g;
    }
    cardDrag.ghost.style.left = (e.clientX - 55) + "px";
    cardDrag.ghost.style.top = (e.clientY - 30) + "px";
    // the node under the ghost lights up when a path or a source can land on it
    const over = document.elementFromPoint(e.clientX, e.clientY);
    hover(entry.role === "node" ? null : over);
  });
  const finish = (e) => {
    if (!cardDrag) return;
    const d = cardDrag; cardDrag = null;
    if (d.ghost) d.ghost.remove();
    hover(null);
    if (!d.moved) {
      // a tap arms the card; a second tap disarms it
      if (S.mode === "place" && S.pending && S.pending.key === d.entry.key) setMode("idle");
      else setMode("place", d.entry);
      return;
    }
    const over = document.elementFromPoint(e.clientX, e.clientY);
    if (!over || !over.closest("#ed-stage")) return;
    const p = toPage(e.clientX, e.clientY);
    const hit = hitAt(over);
    if (d.entry.role === "node") placeNode(d.entry.kind, p);
    else if (hit && hit.role === "node") dropOnNode(d.entry, hit);
    else { setMode("place", d.entry); toast(d.entry.role === "source" ? "A source joins a node: drop it on one, or click the node." : "A path joins two nodes: drop it on the first, or click it."); }
  };
  card.addEventListener("pointerup", finish);
  card.addEventListener("pointercancel", () => { if (cardDrag && cardDrag.ghost) cardDrag.ghost.remove(); cardDrag = null; hover(null); });
});

// quick add: tap empty space, type a name
const quick = $("ed-quick"), quickInput = $("ed-quick-input"), quickList = $("ed-quick-list");
let quickAt = null, quickItems = [], quickIndex = 0;

function openQuick(p, clientX, clientY) {
  quickAt = p;
  const r = $("ed-stage").getBoundingClientRect();
  quick.style.left = clamp(clientX - r.left, 8, r.width - 320) + "px";
  quick.style.top = clamp(clientY - r.top + 8, 8, r.height - 200) + "px";
  quick.hidden = false;
  quickInput.value = "";
  quickList.innerHTML = "";
  quickItems = [];
  quickInput.focus();
}
function closeQuick() { quick.hidden = true; quickAt = null; }

quickInput.addEventListener("input", async () => {
  const text = quickInput.value.trim();
  if (!text) { quickList.innerHTML = ""; quickItems = []; return; }
  try { quickItems = await rpc.call("quick_add", text); } catch { quickItems = []; }
  if (quickInput.value.trim() !== text) return;
  quickIndex = 0;
  quickList.innerHTML = quickItems.map((it, i) =>
    `<li aria-selected="${i === 0}" data-i="${i}"><b>${escapeHtml(it.name)}</b><small>${escapeHtml(it.role)} · ${escapeHtml(it.kind)}</small></li>`).join("");
});
quickInput.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { closeQuick(); return; }
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault();
    if (!quickItems.length) return;
    quickIndex = (quickIndex + (e.key === "ArrowDown" ? 1 : quickItems.length - 1)) % quickItems.length;
    [...quickList.children].forEach((li, i) => li.setAttribute("aria-selected", String(i === quickIndex)));
    return;
  }
  if (e.key === "Enter" || e.code === "Enter" || e.code === "NumpadEnter" || e.keyCode === 13) {
    e.preventDefault();
    if (quickItems.length) chooseQuick(quickItems[quickIndex]);
  }
});
quickList.addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (li) chooseQuick(quickItems[+li.dataset.i]);
});
function chooseQuick(it) {
  const p = quickAt;
  closeQuick();
  if (it.role === "node") placeNode(it.kind, p);
  else setMode("place", it);
}

// ------------------------------------------------------------- popover
const pop = $("ed-popover");

function field(label, inputHtml) { return `<label><span>${label}</span>${inputHtml}</label>`; }
function text(name, value, placeholder = "") {
  return `<input type="text" data-field="${name}" value="${escapeHtml(value == null ? "" : value)}" placeholder="${escapeHtml(placeholder)}" autocomplete="off">`;
}
function num(name, value, step = 1) {
  return `<input type="number" data-field="${name}" value="${value == null ? "" : value}" step="${step}">`;
}
function selectBox(name, value, options, labels = {}) {
  return `<select data-field="${name}">${options.map((o) => `<option value="${o}"${o === value ? " selected" : ""}>${escapeHtml(labels[o] || o)}</option>`).join("")}</select>`;
}
const SIDES = ["auto", "up", "down", "left", "right"];

function openPopover(sel) {
  const el = element(sel);
  if (!el) return;
  const u = S.data.units || {};
  let h = "";
  if (sel.role === "node") {
    const kind = el.kind || "free";
    h += `<h4>${escapeHtml(kindName("node", kind))} <code>${escapeHtml(el.id)}</code></h4>`;
    h += field("Label", text("label", el.label, "e.g. Junction"));
    h += field("Subscript", text("sub", el.sub, "names the place: j"));
    h += field(`T, ${escapeHtml(u.T && u.T.unit || u.T || "no unit")}`, text("value", el.value, "temperature"));
    h += field("Kind", selectBox("kind", kind, KINDS.node, Object.fromEntries(KINDS.node.map((k) => [k, kindName("node", k)]))));
    if (kind === "fixed" || kind === "break") h += field("Wall faces", selectBox("wall", el.wall || "down", ["down", "up", "left", "right"]));
    h += `<details><summary>More</summary>`;
    h += field("Id", text("id", el.id));
    h += field("Label angle", num("angle", el.angle || 0, 45));
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="connect" title="Then click the node it joins">Connect to…</button><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  } else if (sel.role === "branch") {
    const kind = el.kind || "cond";
    h += `<h4>${escapeHtml(kindName("branch", kind))} <code>${escapeHtml(el.from)} → ${escapeHtml(el.to)}</code></h4>`;
    h += field("Kind", selectBox("kind", kind, KINDS.branch, Object.fromEntries(KINDS.branch.map((k) => [k, kindName("branch", k)]))));
    h += field("Label", text("label", el.label, "e.g. Die attach"));
    if (kind !== "break") {
      const q = kind === "cap" ? "C" : kind === "flow" ? "q" : "R";
      h += field(`${q}, ${escapeHtml(u[q] || "no unit")}`, text("value", el.value, "value"));
    }
    if (kind === "cap") h += field("Subscript", text("sub", el.sub, "names the place"));
    if (kind !== "break" && kind !== "flow") h += field(`Rate q, ${escapeHtml(u.q || "no unit")}`, text("rate", el.rate, "optional"));
    h += `<details><summary>More</summary>`;
    h += field("Count", num("count", el.count, 1));
    h += field("Arranged", selectBox("arrangement", el.arrangement || "", ["", "parallel", "series"], {"": "(one path)"}));
    if (kind !== "flow") h += field("Symbol angle", num("angle", el.angle, 45));
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += `<div class="ed-row"><button type="button" data-act="swap">Swap ends</button><button type="button" data-act="unpin">Let the symbol float</button></div>`;
    h += `<p style="margin:8px 0 4px;font-size:12.5px;color:var(--ink-3)">Bends</p><ul class="ed-vias">`;
    (el.via || []).forEach((v, i) => { h += `<li>${v[0]}, ${v[1]} <button type="button" data-act="via-del" data-i="${i}">remove</button></li>`; });
    h += `</ul><div class="ed-row"><button type="button" data-act="via-add">Add a bend</button></div>`;
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  } else {
    const kind = el.kind || "diss";
    const outward = el.from != null;
    h += `<h4>${escapeHtml(kindName("source", kind))} <code>${outward ? escapeHtml(el.from) + " →" : "→ " + escapeHtml(el.to)}</code></h4>`;
    h += field("Kind", selectBox("kind", kind, KINDS.source, Object.fromEntries(KINDS.source.map((k) => [k, kindName("source", k)]))));
    h += field("Label", text("label", el.label, "e.g. Switching loss"));
    h += field("Subscript", text("sub", el.sub, "names the place"));
    const q = kind === "diss" ? "P" : kind === "flux" ? "q″" : "q";
    h += field(`${q}, ${escapeHtml(u[q] || "no unit")}`, text("value", el.value, "value"));
    if (kind === "flow" || kind === "flux") h += field("Direction", selectBox("direction", outward ? "out" : "in", ["in", "out"], {in: "into the node", out: "leaving the node"}));
    h += `<details><summary>More</summary>`;
    h += field("Count", num("count", el.count, 1));
    h += field("Angle", num("angle", el.angle || 0, 45));
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += `<div class="ed-row"><button type="button" data-act="unpin">Let it float</button></div>`;
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  }
  pop.innerHTML = h;
  pop.hidden = false;
  placePopover(sel);
  const first = pop.querySelector('input[data-field="label"]');
  if (first && !first.value) first.focus();
}

function placePopover(sel) {
  const b = boundsOf(sel);
  const st = $("ed-stage").getBoundingClientRect();
  if (!b) { pop.style.left = "12px"; pop.style.top = "12px"; return; }
  const tl = toScreen(b[0], b[1]), br = toScreen(b[2], b[3]);
  const pw = pop.offsetWidth || 320, ph = pop.offsetHeight || 260;
  // beside the element first, so its own label stays readable while it is
  // edited; below it, then above it, when there is no room to the right
  let left, top;
  if (br.x + 16 + pw <= st.width - 8) {
    left = br.x + 16;
    top = clamp(tl.y - 8, 8, Math.max(8, st.height - ph - 8));
  } else if (br.y + 12 + ph <= st.height - 8) {
    left = clamp(tl.x, 8, st.width - pw - 8);
    top = br.y + 12;
  } else {
    left = clamp(tl.x, 8, st.width - pw - 8);
    top = Math.max(8, tl.y - ph - 12);
  }
  pop.style.left = left + "px"; pop.style.top = top + "px";
}

function closePopover() { pop.hidden = true; pop.innerHTML = ""; }

pop.addEventListener("change", (e) => {
  const f = e.target.dataset.field;
  if (!f || !S.sel) return;
  applyField(S.sel, f, e.target.value);
});
pop.addEventListener("input", (e) => {
  const f = e.target.dataset.field;
  if (!f || !S.sel || e.target.tagName !== "INPUT" || e.target.type !== "text") return;
  if (f === "id") return;  // ids rename on change, not per keystroke
  applyField(S.sel, f, e.target.value, true);
});
pop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.target.tagName === "INPUT") { e.preventDefault(); e.target.blur(); closePopover(); }
  if (e.key === "Escape") closePopover();
});
pop.addEventListener("click", (e) => {
  const act = e.target.dataset.act;
  if (!act || !S.sel) return;
  const sel = S.sel, el = element(sel);
  if (act === "delete") { edit(() => removeElement(sel)); select(null); return; }
  if (act === "connect") { startConnect(el.id, "cond"); return; }
  if (act === "swap") { edit(() => { [el.from, el.to] = [el.to, el.from]; }); openPopover(sel); return; }
  if (act === "unpin") { edit(() => { delete el.at; }); return; }
  if (act === "via-add") {
    const b = boundsOf(sel);
    const at = b ? [snap((b[0] + b[2]) / 2), snap((b[1] + b[3]) / 2)] : [0, 0];
    edit(() => { el.via = el.via || []; el.via.push(at); });
    openPopover(sel);
    return;
  }
  if (act === "via-del") { edit(() => { el.via.splice(+e.target.dataset.i, 1); if (!el.via.length) delete el.via; }); openPopover(sel); return; }
});

// A field edit while typing coalesces into one undo step per field.
let typing = null;
function applyField(sel, f, raw, live = false) {
  const value = raw === "" ? null : raw;
  const apply = (d) => {
    const e = element(sel);
    if (f === "id") {
      if (!value || d.nodes.some((n) => n !== e && n.id === value)) return;
      renameNode(e.id, value); return;
    }
    if (f === "direction") {
      const node = e.to != null ? e.to : e.from;
      delete e.to; delete e.from;
      if (value === "out") e.from = node; else e.to = node;
      return;
    }
    if (f === "kind") {
      const dflt = {node: "free", branch: "cond", source: "diss"}[sel.role];
      if (value === dflt || value == null) delete e.kind; else e.kind = value;
      // fields the new kind refuses
      if (sel.role === "node" && !(value === "fixed" || value === "break")) delete e.wall;
      if (sel.role === "branch" && value === "flow") delete e.angle;
      if (sel.role === "branch" && value === "break") { delete e.value; delete e.rate; }
      if (sel.role === "source" && !(value === "flow" || value === "flux") && e.from != null) { e.to = e.from; delete e.from; }
      return;
    }
    if (["angle", "count"].includes(f)) {
      if (value == null) delete e[f]; else e[f] = Number(value);
      if (f === "count" && e.count > 1 && !e.arrangement) e.arrangement = "parallel";
      if (f === "count" && !(e.count > 1)) { delete e.count; delete e.arrangement; }
      return;
    }
    if (f === "arrangement" && value == null) { delete e.arrangement; return; }
    if (f === "side" && value === "auto") { delete e.side; return; }
    if (f === "wall" && value === "down") { delete e.wall; return; }
    if (value == null) delete e[f]; else e[f] = value;
  };
  if (live) {
    if (typing !== f) { S.undo.push(snapshot()); S.redo.length = 0; typing = f; }
    apply(S.data);
    afterEdit();
  } else {
    typing = null;
    edit(apply);
    if (f === "kind" || f === "id" || f === "direction") openPopover(sel);
  }
}

// ------------------------------------------------------------- diagram
$("ed-settings").addEventListener("click", () => {
  select(null);
  const d = S.data, u = d.units || {};
  const T = typeof u.T === "object" && u.T ? u.T : {unit: u.T || "", scale: ""};
  let h = `<h4>Title &amp; units</h4>`;
  h += field("Title", text("title", d.title, "shown on the page"));
  for (const q of ["R", "C", "P", "q", "q″"]) h += field(`Unit of ${q}`, text(`unit:${q}`, u[q], q === "R" ? "K/W" : ""));
  h += field("Unit of T", text("unit:T", T.unit, "°C or K"));
  h += field("T scale", selectBox("scale", T.scale || "", ["", "absolute", "rise"], {"": "(unstated)"}));
  h += `<details ${d.rail ? "open" : ""}><summary>Reference rail</summary>`;
  h += field("Reference", selectBox("rail:reference", d.rail ? d.rail.reference : "", ["", ...d.nodes.map((n) => n.id)], {"": "(no rail)"}));
  h += field("Rail y", num("rail:y", d.rail && d.rail.y, 10));
  h += `</details>`;
  h += `<div class="ed-row"><button type="button" data-act="solve" title="Give every node without a place one, along a chain">Place unplaced nodes</button></div>`;
  pop.innerHTML = h;
  pop.hidden = false;
  pop.style.left = "12px"; pop.style.top = "12px";
  S.sel = null;
});
pop.addEventListener("change", (e) => {
  const f = e.target.dataset.field;
  if (!f || S.sel) return;
  const value = e.target.value === "" ? null : e.target.value;
  edit((d) => {
    if (f === "title") { if (value) d.title = value; else delete d.title; return; }
    d.units = d.units || {};
    if (f.startsWith("unit:")) {
      const q = f.slice(5);
      if (q === "T") {
        const T = typeof d.units.T === "object" && d.units.T ? d.units.T : {unit: d.units.T};
        if (!value) delete d.units.T; else if (T.scale) d.units.T = {unit: value, scale: T.scale}; else d.units.T = value;
      } else if (value) d.units[q] = value; else delete d.units[q];
      return;
    }
    if (f === "scale") {
      const unit = typeof d.units.T === "object" && d.units.T ? d.units.T.unit : d.units.T;
      if (!unit) return;
      d.units.T = value ? {unit, scale: value} : unit;
      return;
    }
    if (f === "rail:reference") { if (value) d.rail = {...(d.rail || {}), reference: value}; else delete d.rail; return; }
    if (f === "rail:y") { if (d.rail) { if (value == null) delete d.rail.y; else d.rail.y = Number(value); } }
  });
});
pop.addEventListener("click", async (e) => {
  if (e.target.dataset.act !== "solve") return;
  const out = await rpc.call("solve", S.data);
  if (out.error) { showError(out.error); return; }
  edit((d) => { Object.assign(d, out); });
  fit();
  toast("Every node has a place now.");
});

// ---------------------------------------------------------------- files
const STORE = {index: "thermodraw:index", file: (id) => `thermodraw:file:${id}`, last: "thermodraw:last", theme: "thermodraw:theme"};
function readIndex() { try { return JSON.parse(localStorage.getItem(STORE.index) || "[]"); } catch { return []; } }
function writeIndex(ix) { localStorage.setItem(STORE.index, JSON.stringify(ix)); }

function save() {
  if (!S.file) return;
  try {
    localStorage.setItem(STORE.file(S.file.id), snapshot());
    const ix = readIndex();
    const e = ix.find((f) => f.id === S.file.id);
    if (e) { e.updated = Date.now(); e.name = S.file.name; } else ix.unshift({id: S.file.id, name: S.file.name, updated: Date.now()});
    writeIndex(ix);
    localStorage.setItem(STORE.last, S.file.id);
  } catch (err) {
    toast("Could not save: the browser's storage is full or blocked.");
  }
}

function showFile() {
  S.undo.length = 0; S.redo.length = 0;
  S.scene = null;
  select(null);
  setMode("idle");
  updateChrome();
  drawing.innerHTML = ""; hitsG.innerHTML = "";
  S.touched = false;
  refresh();
  setTimeout(() => fit(), 60);
  renderFiles();
}

function newFile(name, data) {
  const id = Math.random().toString(36).slice(2, 10);
  S.file = {id, name};
  S.data = data;
  save();
  showFile();
}

function openFile(id) {
  const raw = localStorage.getItem(STORE.file(id));
  const ix = readIndex().find((f) => f.id === id);
  if (!raw || !ix) return false;
  S.file = {id, name: ix.name};
  S.data = JSON.parse(raw);
  localStorage.setItem(STORE.last, id);
  showFile();
  return true;
}

function deleteFile(id) {
  const ix = readIndex();
  const e = ix.find((f) => f.id === id);
  const raw = localStorage.getItem(STORE.file(id));
  writeIndex(ix.filter((f) => f.id !== id));
  localStorage.removeItem(STORE.file(id));
  if (S.file && S.file.id === id) {
    const next = readIndex()[0];
    if (next) openFile(next.id); else newFile("Untitled", BLANK());
  }
  renderFiles();
  toast(`Deleted “${e ? e.name : "file"}”.`, {label: "Undo", act: () => {
    localStorage.setItem(STORE.file(id), raw);
    writeIndex([e, ...readIndex()]);
    openFile(id);
  }});
}

function renameFile(id) {
  const ix = readIndex();
  const f = ix.find((x) => x.id === id);
  const name = prompt("Name this diagram", f.name);
  if (!name) return;
  f.name = name; writeIndex(ix);
  if (S.file && S.file.id === id) { S.file.name = name; updateChrome(); }
  renderFiles();
}

function renderFiles() {
  const ul = $("ed-files");
  const ix = readIndex().sort((a, b) => b.updated - a.updated);
  ul.innerHTML = ix.map((f) => `<li data-id="${f.id}" class="${S.file && S.file.id === f.id ? "ed-current" : ""}" title="Open “${escapeHtml(f.name)}”">
    <span class="ed-fname">${escapeHtml(f.name)}</span><small>${new Date(f.updated).toLocaleDateString()}</small>
    <button type="button" class="ed-more" data-act="more" title="Rename, copy, delete">⋯</button></li>`).join("");
}
$("ed-files").addEventListener("click", (e) => {
  const li = e.target.closest("li"); if (!li) return;
  const id = li.dataset.id;
  if (e.target.dataset.act === "more") {
    const r = e.target.getBoundingClientRect(), st = $("ed-stage").getBoundingClientRect();
    menu.innerHTML = `<button data-f="rename">Rename</button><button data-f="dup">Make a copy</button><hr><button data-f="del" class="ed-danger">Delete</button>`;
    menu.dataset.file = id;
    menu.style.left = clamp(r.right - st.left + 4, 8, st.width - 230) + "px";
    menu.style.top = clamp(r.top - st.top, 8, st.height - 140) + "px";
    menu.hidden = false;
    return;
  }
  openFile(id); closeFiles();
});
$("ed-new").addEventListener("click", () => { newFile("Untitled", BLANK()); closeFiles(); });
$("ed-open-example").addEventListener("click", async () => {
  const ul = $("ed-examples");
  if (!ul.children.length) {
    const ex = await (await fetch("examples.json")).json();
    ul.innerHTML = ex.map((e) => `<li data-path="${escapeHtml(e.path)}">${escapeHtml(e.title)}</li>`).join("");
  }
  ul.hidden = !ul.hidden;
  $("ed-open-example").setAttribute("aria-expanded", String(!ul.hidden));
});
$("ed-examples").addEventListener("click", async (e) => {
  const li = e.target.closest("li"); if (!li) return;
  const data = await (await fetch(li.dataset.path)).json();
  newFile(data.title ? data.title.slice(0, 60) : li.textContent, data);
  $("ed-examples").hidden = true;
  $("ed-open-example").setAttribute("aria-expanded", "false");
  closeFiles();
});
$("ed-import").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  try {
    const data = JSON.parse(await f.text());
    newFile(f.name.replace(/\.json$/i, ""), data);
    closeFiles();
  } catch { toast("That file is not JSON."); }
  e.target.value = "";
});
// on a narrow screen the files panel is an overlay
const filesPanel = $("ed-files-panel");
function closeFiles() { filesPanel.classList.remove("ed-open"); }
$("ed-files-toggle").addEventListener("click", () => filesPanel.classList.toggle("ed-open"));
$("ed-files-close").addEventListener("click", closeFiles);
$("ed-file").addEventListener("click", () => { if (S.file) renameFile(S.file.id); });

// ---------------------------------------------------------------- menus
const menu = $("ed-menu");
function closeMenu() { menu.hidden = true; delete menu.dataset.file; }
menu.addEventListener("click", async (e) => {
  const f = e.target.dataset.f, x = e.target.dataset.x;
  const id = menu.dataset.file;
  closeMenu();
  if (f && id) {
    if (f === "rename") renameFile(id);
    if (f === "del") deleteFile(id);
    if (f === "dup") {
      const src = readIndex().find((y) => y.id === id);
      newFile(src.name + " (copy)", JSON.parse(localStorage.getItem(STORE.file(id))));
    }
    return;
  }
  if (!x) return;
  const base = (S.file ? S.file.name : "diagram").replace(/[^\w.-]+/g, "-");
  try {
    if (x === "json") return download(`${base}.json`, await rpc.call("export", S.data, "json"), "application/json");
    if (x === "page") return download(`${base}.html`, await rpc.call("export", S.data, "page", null, S.notation), "text/html");
    if (x.startsWith("svg")) {
      const mode = x === "svg" ? null : x.slice(4);
      return download(`${base}${mode ? "-" + mode : ""}.svg`, await rpc.call("export", S.data, "svg", mode, S.notation), "image/svg+xml");
    }
    const mode = x.slice(4);
    const svg = await rpc.call("export", S.data, "svg", mode, S.notation);
    download(`${base}-${mode}.png`, await rasterise(svg, 2, mode), "image/png");
  } catch (err) { toast("Export failed: " + err.message); }
});
$("ed-export").addEventListener("click", (e) => {
  const r = e.target.getBoundingClientRect(), st = $("ed-stage").getBoundingClientRect();
  menu.innerHTML = `
    <button data-x="svg">SVG that follows light and dark</button>
    <button data-x="svg-light">SVG, light, for Word and slides</button>
    <button data-x="svg-dark">SVG, dark</button>
    <button data-x="png-light">PNG, light, 2×</button>
    <button data-x="png-dark">PNG, dark, 2×</button>
    <hr><button data-x="page">HTML page with its controls</button>
    <button data-x="json">JSON, the diagram itself</button>`;
  menu.style.left = clamp(r.left - st.left, 8, st.width - 240) + "px";
  menu.style.top = "8px";
  menu.hidden = false;
});

function download(name, content, type) {
  const blob = content instanceof Blob ? content : new Blob([content], {type});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

function rasterise(svg, scale, mode) {
  return new Promise((resolve, reject) => {
    const m = svg.match(/width="([\d.]+)" height="([\d.]+)"/);
    const w = Math.ceil(+m[1] * scale), h = Math.ceil(+m[2] * scale);
    const img = new Image();
    const url = URL.createObjectURL(new Blob([svg], {type: "image/svg+xml"}));
    img.onload = () => {
      const c = document.createElement("canvas"); c.width = w; c.height = h;
      const g = c.getContext("2d");
      g.fillStyle = mode === "dark" ? "#0f1115" : "#ffffff"; g.fillRect(0, 0, w, h);
      g.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      c.toBlob((b) => b ? resolve(b) : reject(new Error("no image")), "image/png");
    };
    img.onerror = () => reject(new Error("the browser could not draw the SVG"));
    img.src = url;
  });
}

// ----------------------------------------------------------------- share
const b64u = {
  enc: (bytes) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""),
  dec: (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0)),
};
async function pack(text) {
  const bytes = new TextEncoder().encode(text);
  if (!("CompressionStream" in window)) return "j=" + b64u.enc(bytes);
  const out = await new Response(new Blob([bytes]).stream().pipeThrough(new CompressionStream("deflate-raw"))).arrayBuffer();
  return "d=" + b64u.enc(new Uint8Array(out));
}
async function unpack(frag) {
  const [k, v] = [frag.slice(0, 1), frag.slice(2)];
  const bytes = b64u.dec(v);
  if (k === "j") return new TextDecoder().decode(bytes);
  if (!("DecompressionStream" in window)) throw new Error("this browser cannot open compressed links");
  const out = await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream("deflate-raw"))).arrayBuffer();
  return new TextDecoder().decode(out);
}
$("ed-share").addEventListener("click", async () => {
  try {
    const url = location.origin + location.pathname + "#" + await pack(snapshot());
    try {
      await navigator.clipboard.writeText(url);
      toast(`Link copied, ${url.length} characters. It carries the whole diagram.`);
    } catch {
      // no clipboard here: show the link, selected, to copy by hand
      select(null);
      pop.innerHTML = `<h4>Share</h4><p style="font-size:13px;margin:0 0 8px">This link carries the whole diagram. Copy it.</p>` +
        `<input type="text" id="ed-share-url" readonly value="${escapeHtml(url)}">`;
      pop.hidden = false; pop.style.left = "12px"; pop.style.top = "12px";
      const i = $("ed-share-url"); i.focus(); i.select();
    }
  } catch (err) { toast("Could not make a link: " + err.message); }
});
async function openShared() {
  const frag = location.hash.slice(1);
  if (!/^[jd]=/.test(frag)) return false;
  try {
    const data = JSON.parse(await unpack(frag));
    history.replaceState(null, "", location.pathname);
    newFile(data.title ? data.title.slice(0, 60) : "Shared diagram", data);
    toast("Opened the shared diagram as a new file here.");
    return true;
  } catch (err) { toast("Could not open the shared link: " + err.message); return false; }
}

// --------------------------------------------------------------- present
function setPresent(on) {
  S.present = on;
  document.body.classList.toggle("ed-present", on);
  closePopover(); closeQuick(); closeMenu(); closeFiles(); setHelp(false);
  const lbl = $("ed-present-label");
  lbl.hidden = !on;
  lbl.textContent = on ? ((S.data && S.data.title) || (S.file && S.file.name) || "") : "";
  if (on && document.fullscreenEnabled && !document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
  if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
  setTimeout(() => fit(), 80);
}
$("ed-present").addEventListener("click", () => setPresent(true));
document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && S.present) setPresent(false); });

function stepFile(delta) {
  const ix = readIndex().sort((a, b) => b.updated - a.updated);
  if (!S.file || ix.length < 2) return;
  const i = ix.findIndex((f) => f.id === S.file.id);
  const next = ix[(i + delta + ix.length) % ix.length];
  const updated = ix.map((f) => f.updated);  // keep the order stable across steps
  openFile(next.id);
  const ix2 = readIndex(); ix2.forEach((f) => { const j = ix.findIndex((g) => g.id === f.id); if (j >= 0) f.updated = updated[j]; }); writeIndex(ix2);
  $("ed-present-label").textContent = (S.data && S.data.title) || S.file.name;
}

// ------------------------------------------------------------------ help
function setHelp(on) {
  $("ed-help-panel").hidden = !on;
  $("ed-help").setAttribute("aria-expanded", String(on));
}
$("ed-help").addEventListener("click", () => setHelp($("ed-help-panel").hidden));
$("ed-help-close").addEventListener("click", () => setHelp(false));

// ----------------------------------------------------------------- chrome
function updateChrome() {
  $("ed-file").textContent = S.file ? S.file.name : "Untitled";
  $("ed-undo").disabled = !S.undo.length;
  $("ed-redo").disabled = !S.redo.length;
  $("ed-delete").disabled = !S.sel;
  $("ed-notation").textContent = `Notation: ${S.notation}`;
  $("ed-notation").setAttribute("aria-pressed", String(S.notation === "zigzags"));
  $("ed-physics").textContent = `Physics: ${S.physics ? "on" : "off"}`;
  $("ed-physics").setAttribute("aria-pressed", String(S.physics));
  $("ed-theme").textContent = `Theme: ${currentTheme()}`;
  document.title = `${S.file ? S.file.name : "Editor"} · ThermoDraw ${BUILD.version}`;
}
$("ed-undo").addEventListener("click", undo);
$("ed-redo").addEventListener("click", redo);
$("ed-delete").addEventListener("click", () => { if (S.sel) { const sel = S.sel; edit(() => removeElement(sel)); select(null); } });
$("ed-fit").addEventListener("click", () => { S.touched = false; fit(); });
$("ed-notation").addEventListener("click", () => {
  S.notation = S.notation === "boxes" ? "zigzags" : "boxes";
  updateChrome();
  refresh();
});
$("ed-physics").addEventListener("click", () => {
  S.physics = !S.physics;
  updateChrome();
  refresh();
});
$("ed-findings-toggle").addEventListener("click", () => {
  const l = $("ed-findings-list");
  l.hidden = !l.hidden;
  $("ed-findings-toggle").setAttribute("aria-expanded", String(!l.hidden));
  $("ed-findings-toggle").querySelector(".ed-findings-more").textContent = l.hidden ? "▾" : "▴";
});

function currentTheme() {
  return document.documentElement.dataset.theme
    || (matchMedia("(prefers-color-scheme:dark)").matches ? "dark" : "light");
}
function setTheme(mode) {
  document.documentElement.dataset.theme = mode;
  try { localStorage.setItem(STORE.theme, mode); } catch {}
  updateChrome();
}
$("ed-theme").addEventListener("click", () => setTheme(currentTheme() === "dark" ? "light" : "dark"));

let toastTimer = null;
function toast(text, action) {
  const t = $("ed-toast");
  t.innerHTML = escapeHtml(text) + (action ? ` <button type="button" style="margin-left:10px;padding:2px 10px;font-size:12px">${escapeHtml(action.label)}</button>` : "");
  if (action) t.querySelector("button").addEventListener("click", () => { action.act(); t.hidden = true; });
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, action ? 8000 : 3200);
}

document.addEventListener("keydown", (e) => {
  const typingInField = ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName);
  if (e.key === "Escape") {
    if (S.present) { setPresent(false); return; }
    if (!$("ed-help-panel").hidden) { setHelp(false); return; }
    if (!quick.hidden) { closeQuick(); return; }
    if (!menu.hidden) { closeMenu(); return; }
    if (!pop.hidden) { closePopover(); return; }
    if (filesPanel.classList.contains("ed-open")) { closeFiles(); return; }
    if (S.mode !== "idle") { setMode("idle"); return; }
    select(null);
    return;
  }
  if (typingInField) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
  if (e.key === "Delete" || e.key === "Backspace") {
    if (S.sel && !S.present) { e.preventDefault(); const sel = S.sel; edit(() => removeElement(sel)); select(null); }
    return;
  }
  if (S.present) {
    if (e.key === "ArrowRight") stepFile(1);
    if (e.key === "ArrowLeft") stepFile(-1);
  }
  if (e.key === "f" || e.key === "F") { S.touched = false; fit(); }
  if (e.key === "z" || e.key === "Z") $("ed-notation").click();
  if (e.key === "d" || e.key === "D") $("ed-theme").click();
  if (e.key === "p" || e.key === "P") $("ed-physics").click();
});

document.addEventListener("pointerdown", (e) => {
  if (!pop.hidden && !pop.contains(e.target) && !e.target.closest("#ed-hits") && !e.target.closest("#ed-ui") && e.target.id !== "ed-settings") closePopover();
  if (!menu.hidden && !menu.contains(e.target) && e.target.id !== "ed-export" && e.target.dataset.act !== "more") closeMenu();
  if (!$("ed-help-panel").hidden && !$("ed-help-panel").contains(e.target) && e.target.id !== "ed-help") setHelp(false);
});
window.addEventListener("resize", () => { if (S.sel) placePopover(S.sel); });

// ------------------------------------------------------------------- boot
(async function boot() {
  try { const t = localStorage.getItem(STORE.theme); if (t) document.documentElement.dataset.theme = t; } catch {}
  rpc.on("progress", (m) => { $("ed-loading-text").textContent = m.text; });
  rpc.on("failed", (m) => { $("ed-loading-text").textContent = "The library could not start: " + m.text; });
  rpc.on("ready", (m) => {
    const style = document.createElement("style");
    style.textContent = m.head.faces.join("") + m.head.vars + m.head.css;
    document.head.appendChild(style);
    S.ready = true;
    $("ed-loading").hidden = true;
    refresh();
    setTimeout(() => fit(), 60);
  });
  rpc.boot();

  if (!(await openShared())) {
    const last = localStorage.getItem(STORE.last);
    if (!(last && openFile(last))) {
      const first = readIndex()[0];
      if (!(first && openFile(first.id))) newFile("Untitled", BLANK());
    }
  }
  updateChrome();
  renderFiles();
  fit();
})();
