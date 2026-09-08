// The editor. One file, no framework: state, the canvas, the interactions,
// the popover, the findings strip, the files panel, share and present.
//
// The library does every drawing. This script keeps the diagram as the
// JSON the schema describes, sends it to the worker after every edit, and
// puts back what comes out: the page's parts inside its own <svg>, one
// transparent rectangle per thing that can be clicked, and the findings.
// Nothing here knows how a symbol looks.
//
// The workflow it is built around: drag a component in and it lands whole,
// where you dropped it, joined to nothing. A path arrives as its own two
// nodes with the box between them, because a branch naming no node is not a
// diagram the schema can hold -- and because which end meets which node is
// the author's to say, never the editor's to guess. Loose ends are red, and
// the red dot is what joins one to something already drawn. Double-click a
// node to draw a path to another, click anything to edit it, [ and ] turn
// what is selected.

const $ = (id) => document.getElementById(id);
const BUILD = window.THERMODRAW;
const GRID = 10;
const snap = (v) => Math.round(v / GRID) * GRID;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

// The solver's own spacing between two nodes on a run, sent by
// `_editor.head` so the editor's number and the library's are one number.
// A dropped path is laid out at it, and a run built by hand at it is the
// run `_solve` would have placed. The habit's 220 until the library answers.
let PITCH = 220;

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
  units: {R: "K/W", C: "J/K", T: "°C", P: "W", q: "W", "q″": "W/cm²",
          mdot: "kg/s", cp: "kJ/kg·K"},
  nodes: [], branches: [], sources: [],
});

const S = {
  ready: false,
  file: null,            // {id, name}
  data: null,            // the diagram, as JSON
  scene: null,           // the last good scene from the library
  sel: null,             // {role, index} or null
  loose: [],             // the ends joined to nothing, as red dots
  mode: "idle",          // idle | place | connect | attach
  pending: null,         // place: the palette entry; connect: {fromId, kind};
                         // attach: {handle} from `looseEnds`
  view: {x: 0, y: 0, w: 1000, h: 600},
  undo: [], redo: [],
  notation: "boxes", physics: false,
  inflight: false, dirty: false,
  present: false,
  touched: false,        // has the reader panned or zoomed since the last fit
};

const KINDS = {
  node: ["free", "fixed", "break", "phase"],
  branch: ["cond", "conv", "rad", "contact", "spread", "pipe", "mixed", "cap", "flow", "break", "link", "stream"],
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

// ------------------------------------------------- a node lands on a run
// `at` taken from the raw pointer is a number related to nothing else on the
// page, and `_layout` reads a branch's angle off its two endpoints, so two
// nodes dropped by eye give a wire at 6.58 degrees and a box turned to
// match. Nothing downstream objects: no check reads a run's bearing. The
// alignment is therefore made here, under the hand -- a drop within reach of
// another node's x or y takes that number exactly, and one within reach of
// the solver's pitch from it takes that. Reach is in pixels, so it is the
// same distance under the hand at every zoom; a page-unit reach would be
// four pixels zoomed out and thirty-six zoomed in.
// Generous, because there is no such thing as a run meant to be twenty
// units off square. A parallel pair stands 80 off its main line and the
// solver's own pitch is 220; anything inside 30 is a hand that meant one
// line and missed. The three nodes that started this -- dropped by eye and
// drawn at 6.58 and -4.97 degrees -- were 25 and 15 apart.
const ALIGN_PX = 30;
let lastAlign = {x: null, y: null};   // what the guides should show

function alignedSnap(x, y, excludeId) {
  const reach = ALIGN_PX * unitsPerPixel();
  const others = S.data.nodes.filter((n) => n.at && n.id !== excludeId);
  const pick = (v, axis) => {
    let best = null, bestD = reach;
    for (const n of others) {
      // the node's own line first, then the pitch either side of it
      for (const c of [n.at[axis], n.at[axis] - PITCH, n.at[axis] + PITCH]) {
        const d = Math.abs(v - c);
        if (d < bestD) { best = {value: c, from: n, own: c === n.at[axis]}; bestD = d; }
      }
    }
    return best;
  };
  let ax = pick(x, 0), ay = pick(y, 1);
  // Both lines taken from one node puts the drop exactly on top of it, and
  // two places at one point is not a drawing. Whichever line the hand was
  // nearer to is the one it meant; the other axis lands where it fell.
  if (ax && ay && ax.own && ay.own && ax.from === ay.from) {
    if (Math.abs(x - ax.value) <= Math.abs(y - ay.value)) ay = null; else ax = null;
  }
  lastAlign = {x: ax, y: ay};
  return [ax ? ax.value : snap(x), ay ? ay.value : snap(y)];
}

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
  // ahead of the library, which is a round trip away: the dots are read off
  // the diagram, and a reader who has just dropped a path should see where
  // its ends are before the drawing catches up
  if (S.data) drawLoose();
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

// ------------------------------------------------------------ loose ends
// Which nodes are joined to which, as one component number per node. A
// `break` counts as joined, as it does in `check`: the question is whether
// the network is one network, not whether heat crosses.
function islands() {
  const of = new Map(S.data.nodes.map((n) => [n.id, n.id]));
  const find = (a) => { while (of.get(a) !== a) a = of.get(a); return a; };
  for (const b of S.data.branches) {
    if (!of.has(b.from) || !of.has(b.to)) continue;   // the rail joins nothing
    const [x, y] = [find(b.from), find(b.to)];
    if (x !== y) of.set(x, y);
  }
  const out = new Map();
  for (const n of S.data.nodes) out.set(n.id, find(n.id));
  return out;
}

// Nothing has been said about this node: it is a place with no name, no
// temperature and no kind. Saying any of those makes it the reader's, and
// its end stops being loose whether or not it was ever joined.
function unsaid(node) {
  return node && node.label == null && node.value == null && node.sub == null
         && (!node.kind || node.kind === "free");
}

// The ends that are hanging: one per end of a path, and one per source,
// whose node is unsaid, joins no other path, and has somewhere to go.
//
// The last clause is what keeps the dot honest rather than decorative. A
// dot's whole offer is "click me and pick the node I meet", so a dot with
// no node outside its own island to meet is a control that cannot do
// anything. A lone path on an empty canvas is not disconnected from
// anything; the moment a second thing is on the page, both are.
//
// A bare node gets none. Its useful act is to be joined by a path, which is
// the double-click, not to be merged into another point.
function looseEnds() {
  const d = S.data;
  const where = islands();
  const degree = new Map(d.nodes.map((n) => [n.id, 0]));
  for (const b of d.branches) {
    for (const end of [b.from, b.to]) {
      if (degree.has(end)) degree.set(end, degree.get(end) + 1);
    }
  }
  const free = (id) => {
    const node = nodeById(id);
    return node && node.at && unsaid(node) && degree.get(id) <= 1
           && d.nodes.some((n) => where.get(n.id) !== where.get(id));
  };
  const out = [];
  d.branches.forEach((b, index) => {
    const route = routeOf(b);
    for (const end of ["from", "to"]) {
      const id = b[end];
      if (!free(id)) continue;
      // out along the wire, away from whatever the path leads to
      const node = nodeById(id);
      const near = route ? (end === "from" ? route[1] : route[route.length - 2])
                         : null;
      out.push({id, role: "branch", index, end,
                at: node.at, u: away(node.at, near)});
    }
  });
  d.sources.forEach((x, index) => {
    const id = x.to != null ? x.to : x.from;
    if (!free(id) || degree.get(id) !== 0) return;
    const node = nodeById(id);
    // the arrow's own side is taken; the dot goes on the other one
    const rad = (x.angle || 0) * Math.PI / 180;
    const along = [Math.cos(rad), Math.sin(rad)];
    const sign = x.from != null ? -1 : 1;
    out.push({id, role: "source", index, end: x.from != null ? "from" : "to",
              at: node.at, u: [along[0] * sign, along[1] * sign]});
  });
  return out;
}

// A unit step from `at` directly away from `near`, or to the right when
// there is nothing to be away from.
function away(at, near) {
  if (!near) return [1, 0];
  const dx = at[0] - near[0], dy = at[1] - near[1];
  const len = Math.hypot(dx, dy);
  return len ? [dx / len, dy / len] : [1, 0];
}

// A join carries one end of a path clear across the drawing and used to
// leave the other end where it had been dropped, so the run came out at 40
// degrees: the crooked wire this editor was built to stop, arriving by
// another road. The far end follows, to the nearest quarter turn, when it
// is joined to this path and nothing else and so is free to move. A routed
// path keeps its route; its legs are the author's.
function squareRun(branch, pivotId) {
  const otherId = branch.from === pivotId ? branch.to : branch.from;
  const pivot = nodeById(pivotId), other = nodeById(otherId);
  if (!pivot || !other || !pivot.at || !other.at) return;
  if (branch.via && branch.via.length) return;
  if (S.data.branches.filter(
        (b) => b.from === otherId || b.to === otherId).length !== 1) return;
  const len = snap(Math.hypot(other.at[0] - pivot.at[0],
                              other.at[1] - pivot.at[1])) || PITCH;
  const rad = (((Math.round(bearing(pivot.at, other.at) / 90) * 90) % 360)
               + 360) % 360 * Math.PI / 180;
  other.at = [snap(pivot.at[0] + Math.cos(rad) * len),
              snap(pivot.at[1] + Math.sin(rad) * len)];
}

// Two places become one. `renameNode` is the whole rewiring — branches,
// sources and the rail reference all point at ids — so this is that, then
// the node that has become a duplicate, then the far end of each path that
// moved squared up, then any source it carried given a side of its new
// node with nothing already on it.
function joinNodes(looseId, targetId) {
  const index = S.data.nodes.findIndex((n) => n.id === looseId);
  if (index < 0 || !nodeById(targetId)) return;
  edit((d) => {
    const carried = d.sources.filter(
      (x) => (x.to != null ? x.to : x.from) === looseId);
    const moved = d.branches.filter(
      (b) => b.from === looseId || b.to === looseId);
    renameNode(looseId, targetId);
    d.nodes.splice(index, 1);
    for (const b of moved) squareRun(b, targetId);
    for (const x of carried) {
      const angle = freeSide(targetId, x);
      if (angle) x.angle = angle; else delete x.angle;
    }
  });
  const target = nodeById(targetId);
  select(null);
  toast(`Joined to \u201c${target.label || targetId}\u201d.`,
        {label: "Undo", act: undo});
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
  if (S.data) drawLoose();   // sized in pixels, so a zoom redraws them
  // a step points at something on the drawing, and the drawing refits
  // itself after every addition: the card has to follow it
  if (tour) drawTour();
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
      // before the strip reads it: `showFindings` asks which ends are loose
      // before deciding whether to fling itself open
      drawLoose();
      showFindings(scene.findings);
      if (S.sel) drawSelection();
      // the hit rectangles were just rebuilt, so whatever a live mode had
      // marked on them went with the old ones
      if (S.mode === "attach") markTargets(S.pending.handle);
      // A new element's card opens before its hit rectangle exists, so it
      // had nothing to sit beside and went to the corner. It gets its
      // place the moment the drawing arrives.
      if (S.sel && !pop.hidden) placePopover(S.sel);
      if (S.mode === "connect") markFrom();
      if (!S.dirty && S.data.nodes.some((n) => !n.at)) bake();
    }
    $("ed-empty").hidden = S.data.nodes.length > 0 || tourRunning();
    tourCheck();
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

// The red dots. Drawn from the diagram rather than from the scene, so they
// are there the instant an edit lands and do not wait on the library; sized
// in pixels through `unitsPerPixel`, like the waypoint handles, so they stay
// under the thumb at every zoom. The dot sits just outside its node so the
// node underneath stays draggable and clickable: it is the loose tip of the
// wire, not the node.
const LOOSE_R = 7;

function drawLoose() {
  ui.querySelectorAll(".ed-loose, .ed-loose-ring").forEach((e) => e.remove());
  S.loose = S.data ? looseEnds() : [];
  if (S.present) { S.loose = []; return; }
  const upp = unitsPerPixel();
  S.loose.forEach((h, i) => {
    const [x, y] = [h.at[0] + h.u[0] * (5.5 + (LOOSE_R + 3) * upp),
                    h.at[1] + h.u[1] * (5.5 + (LOOSE_R + 3) * upp)];
    ui.appendChild(svgEl("circle",
      {cx: h.at[0], cy: h.at[1], r: 5.5 + 3 * upp}, "ed-loose-ring"));
    const dot = svgEl("circle", {cx: x, cy: y, r: LOOSE_R * upp}, "ed-loose");
    dot.dataset.loose = i;
    dot.dataset.node = h.id;
    dot.setAttribute("tabindex", "0");
    dot.append(svgEl("title", {}));
    dot.querySelector("title").textContent =
      "This end joins nothing. Click or drag it onto the node it meets.";
    ui.appendChild(dot);
  });
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
const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;

function showFindings(findings) {
  const list = $("ed-findings-list");
  list.innerHTML = "";
  // `--physics` reports what it could not check as a finding of its own.
  // That is right on a command line and wrong here, where it fires on
  // every sketch with no numbers in it yet and reads as a complaint. It
  // becomes the one line above the list that says how the check went.
  const skipped = S.physics
    ? findings.find((f) => f.code === "physics-not-checked") : null;
  const shown = findings.filter((f) => f !== skipped);
  const counts = {error: 0, warning: 0, note: 0};
  for (const f of shown) counts[f.severity] = (counts[f.severity] || 0) + 1;
  const parts = [];
  if (counts.error) parts.push(`<span class="ed-count-error">${plural(counts.error, "error")}</span>`);
  if (counts.warning) parts.push(`<span class="ed-count-warning">${plural(counts.warning, "warning")}</span>`);
  if (counts.note) parts.push(plural(counts.note, "note"));
  const labels = S.scene ? plural(S.scene.labels, "label") + " placed" : "";
  const first = shown.length ? `<span class="ed-first">${escapeHtml(shown[0].message)}</span>` : "";
  $("ed-findings-count").innerHTML = parts.length
    ? `${labels} · ${parts.join(", ")}${first}` : `${labels} · nothing to report`;
  $("ed-physics-said").textContent = !S.physics ? ""
    : skipped ? skipped.message
    : "The numbers agree at every node the diagram states.";
  $("ed-physics-said").hidden = !S.physics;
  for (const f of shown) {
    const li = document.createElement("li");
    li.className = `ed-sev-${f.severity}`;
    li.innerHTML = `<span class="ed-code">${f.severity}: ${escapeHtml(f.code)}</span><span>${escapeHtml(f.message)}<span class="ed-remedy">${escapeHtml(f.remedy)}</span></span>`;
    li.addEventListener("click", () => pointAt(f));
    list.appendChild(li);
  }
  // Something is wrong with the drawing: say what, without being asked.
  // Except that a drawing being built is in pieces by definition, and the
  // red dots say so in place, on the ends it is about. The finding stays in
  // the list; it just stops flinging the strip open once per drop.
  const shouted = shown.filter(
    (f) => !(f.code === "network-in-pieces" && S.loose.length));
  if (shouted.some((f) => f.severity !== "note")) openFindings(true);
}

function openFindings(on) {
  const l = $("ed-findings-list"), t = $("ed-findings-toggle");
  if (on && !t.dataset.closed) l.hidden = false;
  else if (!on) l.hidden = true;
  t.setAttribute("aria-expanded", String(!l.hidden));
  t.querySelector(".ed-findings-more").textContent = l.hidden ? "▾" : "▴";
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
let lastPointer = {x: 0, y: 0};   // where a card with nothing to sit beside goes

function hitAt(target) {
  const r = target && target.closest ? target.closest("#ed-hits rect") : null;
  return r ? {role: r.dataset.role, index: +r.dataset.index, element: r.dataset.element, rect: r} : null;
}

canvas.addEventListener("pointerdown", (e) => {
  if (S.present) return;
  lastPointer = {x: e.clientX, y: e.clientY};
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
  const loose = e.target.dataset && e.target.dataset.loose;
  if (loose !== undefined && S.loose[+loose]) {
    // either gesture means the same thing, so both start here: a drag that
    // moves offers the nodes for the duration, a press that does not opens
    // the same offer and leaves it open
    drag = {kind: "loose", handle: S.loose[+loose], start: p, moved: false};
    markTargets(drag.handle);
    return;
  }
  const hit = hitAt(e.target);
  if (S.mode === "attach") {
    const handle = S.pending.handle;
    const id = hit && hit.role === "node" ? element(hit).id : null;
    setMode("idle");
    if (id && eligible(handle, id)) joinNodes(handle.id, id);
    return;
  }
  if (S.mode === "connect") {
    // connection mode: the next node clicked is the other end
    if (hit && hit.role === "node") finishConnect(S.pending.fromId, element(hit).id, S.pending.kind);
    else setMode("idle");
    return;
  }
  if (S.mode === "place" && S.pending) { dropEntry(S.pending, p); return; }
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

// ------------------------------------------------- a path takes its wire
// `at` on a branch is used by the library exactly as written and is never
// projected onto the run, so a symbol dropped beside its wire makes the
// wire jog diagonally out to meet it and back, and the checker says so.
// A drag near the run therefore slides the symbol along it; a drag away
// from it bends the run to follow, with a waypoint either side of the
// symbol so the wire arrives at the box and leaves it.
// How far off its run a box has to be dragged before the wire bends to
// follow it, in **pixels**: the same distance under the hand at every zoom.
// It was twelve page units, six lines from a drag threshold that was
// correctly converted -- so zoomed out it was four pixels and any twitch
// bent the wire, and zoomed in it was thirty-six and a detour was hard to
// ask for at all. It is also a deliberate distance now rather than a hair's
// breadth, because sliding along the run is what nearly every drag means.
const OFF_RUN_PX = 40;
const DETOUR_PAD = 6;   // how far past the box the wire straightens again

const tidy = (v) => Math.round(v * 1000) / 1000;

function symbolHit(sel) {
  const hits = (S.scene && S.scene.hits) || [];
  return hits.find((h) => h.role === sel.role && h.index === sel.index
                          && h.element === "symbol") || null;
}

function routeOf(el) {
  // what the library routes: [source, *via, target]. Null when an end is
  // the rail or a node the solver has not placed yet.
  const ends = [el.from, el.to].map((id) => {
    const n = nodeById(id);
    return n && n.at ? [n.at[0], n.at[1]] : null;
  });
  if (!ends[0] || !ends[1]) return null;
  return [ends[0], ...(el.via || []).map((v) => [v[0], v[1]]), ends[1]];
}

function nearestSegment(route, p) {
  let best = 0, bestD = Infinity;
  for (let i = 0; i < route.length - 1; i++) {
    const [ax, ay] = route[i], [bx, by] = route[i + 1];
    const dx = bx - ax, dy = by - ay;
    const len = Math.hypot(dx, dy);
    if (!len) continue;
    const t = clamp(((p[0] - ax) * dx + (p[1] - ay) * dy) / (len * len), 0, 1);
    const d = Math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy);
    if (d < bestD) { best = i; bestD = d; }
  }
  const [ax, ay] = route[best], [bx, by] = route[best + 1];
  const len = Math.hypot(bx - ax, by - ay) || 1;
  const u = [(bx - ax) / len, (by - ay) / len];
  return {i: best, a: [ax, ay], u, len,
          along: (p[0] - ax) * u[0] + (p[1] - ay) * u[1],
          off: (p[0] - ax) * -u[1] + (p[1] - ay) * u[0]};
}

// The pair this editor wrote around `at` last time, if it is still there.
// Nothing in the file marks one, so it is recognised by its shape: two
// waypoints in a row whose midpoint is the symbol. Anything else is the
// author's and is left where it is.
function dropBracket(el) {
  const via = el.via;
  if (!via || via.length < 2 || !el.at) return;
  for (let i = 0; i < via.length - 1; i++) {
    if (Math.abs((via[i][0] + via[i + 1][0]) / 2 - el.at[0]) < 0.02
        && Math.abs((via[i][1] + via[i + 1][1]) / 2 - el.at[1]) < 0.02) {
      via.splice(i, 2);
      if (!via.length) delete el.via;
      return;
    }
  }
}

// Returns false when the drop was off the run but the run was too short to
// route around, so the caller can say why the symbol stayed on the wire.
function placeBranchSymbol(sel, p) {
  const el = element(sel);
  dropBracket(el);
  const route = routeOf(el);
  if (!route) { el.at = [snap(p[0]), snap(p[1])]; return true; }
  const seg = nearestSegment(route, p);
  const hit = symbolHit(sel);
  const d = (hit && hit.half_len != null ? hit.half_len : 42) + DETOUR_PAD;
  const offRun = OFF_RUN_PX * unitsPerPixel();
  if (Math.abs(seg.off) <= offRun || 2 * d > seg.len) {
    // Along the run, quantised along the run. Snapping to the page grid
    // instead would throw a point on a diagonal up to 7 units off its own
    // line, and the checker's tolerance for that is one unit.
    const t = clamp(snap(seg.along), 0, seg.len);
    el.at = [tidy(seg.a[0] + seg.u[0] * t), tidy(seg.a[1] + seg.u[1] * t)];
    return Math.abs(seg.off) <= offRun;
  }
  const c = [snap(p[0]), snap(p[1])];
  const out = (k) => [tidy(c[0] + seg.u[0] * k * d), tidy(c[1] + seg.u[1] * k * d)];
  el.via = el.via || [];
  // into the leg the drop landed on, not onto the end of the list: via[i]
  // is route[i+1], so the pair belongs at via index i
  el.via.splice(seg.i, 0, out(-1), out(1));
  el.at = c;
  return true;
}

// ---------------------------------------------------------------- turning
// `]` turns what is selected to the next multiple of 90 degrees and `[` to
// the previous one: a thing lying at 38 goes to 90 or to 0, and one at 90
// goes to 180 or to 0. Two unshifted keys, because a shortcut needing two
// hands is one nobody reaches for.
//
// What turns is the component, not a named field. A node is a point, so the
// only thing it has to turn is its label. A source turns its `angle`, which
// is the side of its node the arrow comes from -- for a source the field and
// the geometry are the same thing. A path turns its **run** wherever the run
// can move: an end joined to nothing else swings about the other end, and a
// path loose at both ends swings about its middle. That is what standing a
// dropped path upright means, and writing an angle onto the box instead
// would turn the box and leave the wire lying where it was.
//
// Only when both ends are pinned by other paths is there no geometry to
// turn. Then the box turns and the wire is re-routed to meet it -- a
// waypoint either side of the box along its new axis -- because `_layout`
// cuts the wire along the route, so a turned box on an uncut route has its
// leads crossing its own wire.
//
// No text is rotated by any of this: `angle` orients a label's frame and a
// symbol, never a glyph, which is the library's own standing decision.
const quarter = (a, dir) => ((((dir > 0 ? Math.floor(a / 90) + 1
                                        : Math.ceil(a / 90) - 1) * 90) % 360) + 360) % 360;
const bearing = (a, c) => ((Math.atan2(c[1] - a[1], c[0] - a[0])
                            * 180 / Math.PI) % 360 + 360) % 360;

// A turn rebuilds the card -- the angle it shows has just changed -- and a
// reader turning something they are halfway through naming must not lose
// the caret they were typing at. `turnBranch` also shuts the card on its
// way through `select`, so the card is put back either way.
function cardCaret() {
  const a = document.activeElement;
  if (!a || !pop.contains(a) || !a.dataset || !a.dataset.field) return null;
  let start = null, end = null;
  try { start = a.selectionStart; end = a.selectionEnd; } catch (_) {}
  return {field: a.dataset.field, start: start, end: end};
}

function putCaret(mark) {
  if (!mark) return;
  const box = pop.querySelector(`[data-field="${mark.field}"]`);
  if (!box) return;
  box.focus({preventScroll: true});
  if (mark.start != null && box.setSelectionRange) {
    try { box.setSelectionRange(mark.start, mark.end); } catch (_) {}
  }
}

function turnSelected(dir) {
  if (S.present) return;
  // Silence is what "the key does nothing" is made of: the keys arrived to
  // make turning cheap, so the one case where they cannot act says so.
  if (!S.sel) {
    toast("Nothing is selected. Click a component, then [ or ] turns it.");
    return;
  }
  const sel = S.sel, el = element(sel);
  if (!el) return;
  const open = !pop.hidden, mark = cardCaret();
  if (sel.role === "branch") turnBranch(sel, el, dir);
  else applyField(sel, "angle", String(quarter(el.angle || 0, dir)));
  if (open) { openPopover(sel); putCaret(mark); }
}

// Waypoints the reader put there themselves, as opposed to the pair this
// editor writes either side of a box. Swinging a node would leave those
// where they were and bend the run through them, so a hand-routed path
// turns its symbol instead.
function routedByHand(el) {
  if (!el.via || !el.via.length) return false;
  const copy = {at: el.at, via: el.via.map((v) => [...v])};
  dropBracket(copy);
  return !!(copy.via && copy.via.length);
}

function turnBranch(sel, el, dir) {
  const ends = [el.from, el.to];
  const nodes = ends.map(nodeById);
  const alone = (id) => S.data.branches.filter(
    (b) => b.from === id || b.to === id).length === 1;
  const swing = ends.map((id, i) => !!(nodes[i] && nodes[i].at && alone(id)));

  if ((swing[0] || swing[1]) && !routedByHand(el)) {
    const [a, c] = [nodes[0].at, nodes[1].at];
    const len = snap(Math.hypot(c[0] - a[0], c[1] - a[1])) || PITCH;
    const rad = quarter(bearing(a, c), dir) * Math.PI / 180;
    const u = [Math.cos(rad), Math.sin(rad)];
    edit(() => {
      if (swing[0] && swing[1]) {
        const mid = [snap((a[0] + c[0]) / 2), snap((a[1] + c[1]) / 2)];
        nodes[0].at = [snap(mid[0] - u[0] * len / 2), snap(mid[1] - u[1] * len / 2)];
        nodes[1].at = [snap(mid[0] + u[0] * len / 2), snap(mid[1] + u[1] * len / 2)];
      } else if (swing[1]) {
        nodes[1].at = [snap(a[0] + u[0] * len), snap(a[1] + u[1] * len)];
      } else {
        nodes[0].at = [snap(c[0] - u[0] * len), snap(c[1] - u[1] * len)];
      }
      // the box goes back to riding its own wire, wherever the wire now runs
      dropBracket(el);
      delete el.at;
      delete el.angle;
    });
    select(sel, false);
    return;
  }

  // Both ends are pinned, so only the symbol can turn. Two kinds refuse:
  // validation forbids `angle` on a directed path and `via` on a fan, and
  // saying so is better than a key that does nothing.
  if (el.kind === "flow") {
    toast("A heat flow's direction is its two ends, so the symbol cannot "
          + "turn against them. Swap ends instead.");
    return;
  }
  if (el.count > 1) {
    toast("A repeated path is drawn as a fan between its own nodes, so there "
          + "is no wire to route around a turn.");
    return;
  }
  const hit = symbolHit(sel);
  const now = el.angle != null ? el.angle : (hit ? hit.angle : 0);
  const next = quarter(((now % 360) + 360) % 360, dir);
  const reach = (hit && hit.half_len != null ? hit.half_len : 42) + DETOUR_PAD;
  edit(() => {
    dropBracket(el);
    const centre = el.at ? [...el.at] : (hit ? [...hit.at] : null);
    const route = routeOf(el);
    if (!centre || !route) { el.angle = next; return; }
    const seg = nearestSegment(route, centre);
    // turned back onto the line its wire already takes, the box wants no
    // detour and no angle: absent is what "turns with its wire" is written as
    const run = bearing([0, 0], seg.u);
    if (Math.min(Math.abs(run - next), 360 - Math.abs(run - next)) < 1) {
      delete el.angle;
      return;
    }
    el.angle = next;
    const rad = next * Math.PI / 180;
    const u = [Math.cos(rad), Math.sin(rad)];
    el.via = el.via || [];
    el.via.splice(seg.i, 0,
      [tidy(centre[0] - u[0] * reach), tidy(centre[1] - u[1] * reach)],
      [tidy(centre[0] + u[0] * reach), tidy(centre[1] + u[1] * reach)]);
    el.at = [tidy(centre[0]), tidy(centre[1])];
  });
  select(sel, false);
}

// What a drag has landed on, shown while it is still held. Both of these
// were only discoverable by letting go: a node's alignment was invisible
// until the drawing came back, and a box's route -- slide along the run, or
// bend the run to follow -- was computed on every move and shown on none of
// them, so the reader learned which of two very different edits they had
// made a round trip after making it.
function drawGuides(at) {
  clearGuides();
  const span = 4000;
  if (lastAlign.x) ui.appendChild(svgEl("line",
    {x1: at[0], y1: at[1] - span, x2: at[0], y2: at[1] + span}, "ed-guide"));
  if (lastAlign.y) ui.appendChild(svgEl("line",
    {x1: at[0] - span, y1: at[1], x2: at[0] + span, y2: at[1]}, "ed-guide"));
}
function clearGuides() { ui.querySelectorAll(".ed-guide").forEach((e) => e.remove()); }

function drawGhost(el) {
  clearGhost();
  const route = routeOf(el);
  if (!route) return;
  ui.appendChild(svgEl("polyline",
    {points: route.map((q) => `${q[0]},${q[1]}`).join(" ")}, "ed-ghost"));
}
function clearGhost() { ui.querySelectorAll(".ed-ghost").forEach((e) => e.remove()); }

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
  if (S.mode === "attach" && !drag) {
    const at = S.pending.handle.at;
    rubber({x: at[0], y: at[1]}, toPage(e.clientX, e.clientY));
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
    const q = [drag.orig[0] + dx, drag.orig[1] + dy];
    if (drag.sel.role === "branch") {
      drag.routed = placeBranchSymbol(drag.sel, q);
      drawGhost(el);
    } else {
      el.at = alignedSnap(q[0], q[1], el.id);
      drawGuides(el.at);
    }
    refresh();
  } else if (drag.kind === "via") {
    element(drag.sel).via[drag.i] = [snap(drag.orig[0] + dx), snap(drag.orig[1] + dy)];
    refresh();
  } else if (drag.kind === "loose") {
    rubber({x: drag.handle.at[0], y: drag.handle.at[1]}, p);
    hover(document.elementFromPoint(e.clientX, e.clientY));
  }
});

canvas.addEventListener("pointerup", (e) => {
  pointers.delete(e.pointerId);
  if (pinch) { if (pointers.size < 2) pinch = null; return; }
  if (!drag) return;
  const d = drag; drag = null;
  canvas.classList.remove("ed-pan");
  clearGuides(); clearGhost();
  const p = toPage(e.clientX, e.clientY);
  if (d.kind === "loose") {
    ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
    hover(null);
    // a press that never moved is the click form, and holds the offer open
    if (!d.moved) { startAttach(d.handle); return; }
    clearTargets();
    const hit = hitAt(document.elementFromPoint(e.clientX, e.clientY));
    const id = hit && hit.role === "node" ? element(hit).id : null;
    // let go over nothing and nothing happens: the end stays exactly where
    // it was, with no half-made state and no mode left armed
    if (id && eligible(d.handle, id)) joinNodes(d.handle.id, id);
    return;
  }
  if (d.kind === "pan") {
    if (!d.moved) { select(null); openQuick(p, e.clientX, e.clientY); }
    return;
  }
  if (d.kind === "element") {
    if (d.moved && d.movable) {
      S.undo.push(d.snapshot); S.redo.length = 0;
      afterEdit();
      select(d.sel, false);
      if (d.routed === false) toast("These nodes are too close to route "
                                    + "around, so the box stayed on the wire.");
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
canvas.addEventListener("pointercancel", (e) => {
  pointers.delete(e.pointerId); drag = null; pinch = null;
  canvas.classList.remove("ed-pan");
  clearGuides(); clearGhost(); clearTargets();
  ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
});

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

// `fresh` says the element was just made, and only then is the cursor put
// in its Label field: the key handler ignores every key typed in a field,
// so a card that grabs the cursor on a plain click is a card that swallows
// Delete on everything the reader selects.
// Removing a node takes every path and source hanging on it, which is
// what the file requires and not what the reader can see, so it says so.
function removeSelected() {
  if (!S.sel) return;
  const sel = S.sel, el = element(sel);
  let went = 0;
  if (sel.role === "node") {
    const id = el.id;
    went = S.data.branches.filter((b) => b.from === id || b.to === id).length
         + S.data.sources.filter((x) => (x.to || x.from) === id).length;
  }
  edit(() => removeElement(sel));
  select(null);
  if (went) toast(`Deleted, with ${plural(went, "path or source", "paths and sources")} that joined it.`,
                  {label: "Undo", act: undo});
}

function select(sel, popover = true, fresh = false) {
  S.sel = sel;
  drawSelection();
  $("ed-delete").disabled = !sel;
  if (sel && popover) openPopover(sel, fresh); else closePopover();
  if (!fresh) canvas.focus({preventScroll: true});
}

// ------------------------------------------------------------------ modes
// What the drawing is waiting for, said in a pill at the top of the stage.
function setMode(mode, pending = null) {
  S.mode = mode; S.pending = pending;
  canvas.classList.toggle("ed-place", mode === "place");
  canvas.classList.toggle("ed-connect", mode === "connect" || mode === "attach");
  document.querySelectorAll(".ed-card").forEach((c) => c.setAttribute("aria-pressed",
    String(mode === "place" && pending && c.dataset.key === pending.key)));
  hitsG.querySelectorAll(".ed-from").forEach((r) => r.classList.remove("ed-from"));
  clearTargets();
  ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
  const pill = $("ed-mode");
  let text = "";
  if (mode === "connect") {
    const from = nodeById(pending.fromId);
    text = `Connecting from <b>${escapeHtml((from && from.label) || pending.fromId)}</b> with ${escapeHtml(kindName("branch", pending.kind).toLowerCase())}: click the node it joins`;
    markFrom();
  } else if (mode === "attach") {
    text = "Joining a loose end: click the node it meets";
    markTargets(pending.handle);
  } else if (mode === "place" && pending) {
    text = `Click where the ${escapeHtml(kindName(pending.role, pending.kind).toLowerCase())} goes`;
  }
  pill.innerHTML = text ? `<span>${text}</span><button type="button" id="ed-mode-cancel">Cancel (Esc)</button>` : "";
  pill.hidden = !text;
  if (text) $("ed-mode-cancel").addEventListener("click", () => setMode("idle"));
}

// Where a loose end may go: any node outside its own island. Inside it,
// joining would either double a path already there or make a branch name
// one node twice, which validation refuses.
function eligible(handle, id) {
  if (!handle || id === handle.id) return false;
  const where = islands();
  return where.has(id) && where.get(id) !== where.get(handle.id);
}

function markTargets(handle) {
  clearTargets();
  S.data.nodes.forEach((n, i) => {
    if (!eligible(handle, n.id)) return;
    hitsOf({role: "node", index: i}).forEach((r) => r.classList.add("ed-target"));
  });
}

function clearTargets() {
  hitsG.querySelectorAll(".ed-target").forEach(
    (r) => r.classList.remove("ed-target"));
}

// Clicking a red dot rather than dragging it: the same offer, held open
// until a node is clicked. Escape and a click on empty canvas both drop it,
// through the chain every other mode already goes down.
function startAttach(handle) {
  closePopover();
  select(null);
  setMode("attach", {handle});
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
  const at = alignedSnap(p.x, p.y, null);
  edit((d) => {
    const n = {id, at};
    if (kind !== "free") n.kind = kind;
    d.nodes.push(n);
  });
  setMode("idle");
  select({role: "node", index: S.data.nodes.length - 1}, true, true);
}

// What a drop makes, for all three groups alike: the component, whole,
// where it was dropped, joined to nothing. A node dropped anywhere used to
// be the only drag that finished -- a source finished only on a node, and a
// path never finished at all, turning itself into a mode and throwing the
// drop point away.
function dropEntry(entry, p) {
  if (entry.role === "node") placeNode(entry.kind, p);
  else if (entry.role === "branch") dropPath(entry.kind, p);
  else dropSource(entry.kind, p);
}

// A path arrives as its own run: two nodes a pitch apart with the box
// between them, centred where it was dropped and running the way heat runs.
// The two nodes are not scaffolding to be tidied away -- a path between two
// places needs two places, and these are the two the reader was going to
// make. Both ends are loose, so both show a red dot.
// A stream is refused outright if it carries a number with no unit for it,
// so these are defaulted like every other unit on the card rather than left
// as a suggestion the author has to accept before the field will take a
// number. `BLANK` covers a new diagram; this covers one that arrives with a
// stream already in it -- an opened file, an imported one, a share link --
// and the two gestures that can add the first stream to a diagram that had
// none. The units card can change them afterwards, which is the point of
// its being a field rather than a fixed label.
function ensureStreamUnits(d) {
  if (!d || !Array.isArray(d.branches)) return d;
  if (!d.branches.some((b) => b.kind === "stream")) return d;
  if (!d.units) d.units = {};
  if (!d.units.mdot) d.units.mdot = "kg/s";
  if (!d.units.cp) d.units.cp = "kJ/kg·K";
  return d;
}

function dropPath(kind, p) {
  const [cx, cy] = alignedSnap(p.x, p.y, null);
  const half = PITCH / 2;
  edit((d) => {
    const a = newNodeId();
    d.nodes.push({id: a, at: [snap(cx - half), cy]});
    const b = newNodeId();
    d.nodes.push({id: b, at: [snap(cx + half), cy]});
    const branch = {from: a, to: b};
    if (kind !== "cond") branch.kind = kind;
    d.branches.push(branch);
    ensureStreamUnits(d);
  });
  setMode("idle");
  select({role: "branch", index: S.data.branches.length - 1}, true, true);
}

// A source arrives on a node of its own, from the left, which is where the
// library's own habit puts heat coming in. Its node is loose, so it shows a
// red dot; joining that node to one already drawn is how the source gets
// onto it.
function dropSource(kind, p) {
  const [x, y] = alignedSnap(p.x, p.y, null);
  edit((d) => {
    const id = newNodeId();
    d.nodes.push({id, at: [x, y]});
    const s = {to: id};
    if (kind !== "diss") s.kind = kind;
    d.sources.push(s);
  });
  setMode("idle");
  select({role: "source", index: S.data.sources.length - 1}, true, true);
}

// Which way a new source should arrive: the side of the node with nothing
// on it. The library's own habit is to arrive from the left (angle 0) and
// the solver turns an interior one to arrive from above; here the wires
// are known, so the emptiest of the four sides wins, above first.
function freeSide(nodeId, except) {
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
  for (const s of d.sources) if ((s.to || s.from) === nodeId && s !== except) taken.push(((s.angle || 0) + (s.from ? 0 : 180)) % 360);
  if (node.kind === "fixed" || node.kind === "break") taken.push({down: 90, up: 270, left: 180, right: 0}[node.wall || "down"]);
  const candidates = [90, 0, 270, 180];   // above, left, below, right
  const gap = (a) => Math.min(...taken.map((t) => { const dd = Math.abs(((a + 180) % 360) - t) % 360; return Math.min(dd, 360 - dd); }), 999);
  return candidates.reduce((best, a) => (gap(a) > gap(best) ? a : best), candidates[0]);
}

function finishConnect(fromId, toId, kind) {
  setMode("idle");
  if (fromId === toId) { toast("A path needs two different nodes."); return; }
  edit((d) => {
    const b = {from: fromId, to: toId};
    if (kind !== "cond") b.kind = kind;
    d.branches.push(b);
  });
  select({role: "branch", index: S.data.branches.length - 1}, true, true);
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
    lastPointer = {x: e.clientX, y: e.clientY};
    dropEntry(d.entry, toPage(e.clientX, e.clientY));
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
// The card is rebuilt whenever a field changes its shape -- a kind, a
// turn -- and a `details` that shuts every time is a field you cannot use.
let moreOpen = false;
const more = () => `<details${moreOpen ? " open" : ""}><summary>More</summary>`;
pop.addEventListener("toggle", (e) => {
  if (e.target.tagName === "DETAILS") moreOpen = e.target.open;
}, true);

// An angle field rests at 0 and is never blank, and the two buttons turn
// it in 45s, snapping whatever is in the box to the nearest 45 on the way.
// `reset` is the only way back to a branch's "turns with its wire", which
// is what an absent angle means and no number can say.
function rotateField(label, value, reset) {
  return `<label class="ed-rot"><span>${label}</span><span class="ed-rot-c">`
    + `<button type="button" data-rot="-45" title="Turn 45 degrees anticlockwise">&#8634;</button>`
    + `<input type="number" data-field="angle" value="${value}" step="45" aria-label="${escapeHtml(label)}">`
    + `<button type="button" data-rot="45" title="Turn 45 degrees clockwise">&#8635;</button>`
    + `<button type="button" data-rot="reset" class="ed-rot-reset" title="${escapeHtml(reset)}">reset</button>`
    + `</span></label>`;
}

// what a branch is drawn at when it carries no angle of its own: the
// bearing of the leg its box landed on, which is 0 for the usual left-to-
// right path and 90 for one running down the page
function shownAngle(sel, el) {
  if (el.angle != null) return el.angle;
  if (sel.role !== "branch") return 0;
  const h = symbolHit(sel);
  return h ? Math.round(h.angle) : 0;
}

function openPopover(sel, fresh = false) {
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
    h += more();
    h += field("Id", text("id", el.id));
    h += rotateField("Label angle", shownAngle(sel, el), "back to 0");
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="connect" title="Then click the node it joins">Connect to…</button><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  } else if (sel.role === "branch") {
    const kind = el.kind || "cond";
    h += `<h4>${escapeHtml(kindName("branch", kind))} <code>${escapeHtml(el.from)} → ${escapeHtml(el.to)}</code></h4>`;
    h += field("Kind", selectBox("kind", kind, KINDS.branch, Object.fromEntries(KINDS.branch.map((k) => [k, kindName("branch", k)]))));
    h += field("Label", text("label", el.label, "e.g. Die attach"));
    // A stream states neither: what it carries is worked out from `mdot`,
    // `cp` and its two ends, so offering `value` would be offering to
    // contradict it.
    const unvalued = kind === "break" || kind === "link" || kind === "stream";
    if (kind === "stream") {
      h += field(`ṁ, ${escapeHtml(u.mdot || "no unit")}`, text("mdot", el.mdot, "mass flow"));
      h += field(`<i>c</i><sub>p</sub>, ${escapeHtml(u.cp || "no unit")}`, text("cp", el.cp, "specific heat"));
    } else if (!unvalued) {
      const q = kind === "cap" ? "C" : kind === "flow" ? "q" : "R";
      h += field(`${q}, ${escapeHtml(u[q] || "no unit")}`, text("value", el.value, "value"));
    }
    if (kind === "cap" || kind === "stream") h += field("Subscript", text("sub", el.sub, kind === "stream" ? "names the medium" : "names the place"));
    if (!unvalued && kind !== "flow") h += field(`Rate q, ${escapeHtml(u.q || "no unit")}`, text("rate", el.rate, "optional"));
    h += more();
    // A stream refuses both: its number is derived, so a group would draw
    // with no value under it. Offering the field would be offering a refusal.
    if (kind !== "stream") {
      h += field("Count", num("count", el.count, 1));
      h += field("Arranged", selectBox("arrangement", el.arrangement || "", ["", "parallel", "series"], {"": "(one path)"}));
    }
    if (kind !== "flow" && kind !== "stream") h += rotateField("Symbol angle", shownAngle(sel, el), "back to turning with the wire");
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
    h += more();
    h += field("Count", num("count", el.count, 1));
    h += rotateField("Angle", shownAngle(sel, el), "back to 0");
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += `<div class="ed-row"><button type="button" data-act="unpin">Let it float</button></div>`;
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  }
  pop.innerHTML = h;
  pop.hidden = false;
  placePopover(sel);
  const first = pop.querySelector('input[data-field="label"]');
  if (fresh && first && !first.value) first.focus();
}

function placePopover(sel) {
  const st = $("ed-stage").getBoundingClientRect();
  const pw = pop.offsetWidth || 320, ph = pop.offsetHeight || 260;
  const b = boundsOf(sel);
  // The hit rectangles arrive a library round trip after the element does,
  // so a card opened on something new has nothing to sit beside yet. The
  // pointer is where the reader is looking; the corner is not. `refresh`
  // calls this again the moment the rectangles land.
  if (!b) {
    pop.style.left = clamp(lastPointer.x - st.left + 20, 8, Math.max(8, st.width - pw - 8)) + "px";
    pop.style.top = clamp(lastPointer.y - st.top - 20, 8, Math.max(8, st.height - ph - 8)) + "px";
    return;
  }
  const tl = toScreen(b[0], b[1]), br = toScreen(b[2], b[3]);
  // whichever side of the element has room, widest first, so the element's
  // own label stays readable while it is edited; then below, then above
  const right = st.width - br.x - 16, left = tl.x - 16;
  let x, y;
  if (Math.max(right, left) >= pw + 8) {
    x = right >= left ? br.x + 16 : tl.x - 16 - pw;
    y = clamp(tl.y - 8, 8, Math.max(8, st.height - ph - 8));
  } else if (br.y + 12 + ph <= st.height - 8) {
    x = clamp(tl.x, 8, Math.max(8, st.width - pw - 8));
    y = br.y + 12;
  } else {
    x = clamp(tl.x, 8, Math.max(8, st.width - pw - 8));
    y = Math.max(8, tl.y - ph - 12);
  }
  pop.style.left = clamp(x, 8, Math.max(8, st.width - pw - 8)) + "px";
  pop.style.top = y + "px";
}

function closePopover() { pop.hidden = true; pop.innerHTML = ""; delete pop.dataset.rename; }

// A card that belongs to a button in the chrome rather than to something
// on the drawing: under the button, kept inside the stage.
function underButton(card, btn) {
  const st = $("ed-stage").getBoundingClientRect(), b = btn.getBoundingClientRect();
  const w = card.offsetWidth || 300, h = card.offsetHeight || 220;
  card.style.left = clamp(b.left - st.left, 8, Math.max(8, st.width - w - 8)) + "px";
  card.style.top = clamp(b.bottom - st.top + 6, 8, Math.max(8, st.height - h - 8)) + "px";
}
// leaving a field must hand the keyboard back, or Delete goes on being
// swallowed by an input nobody is looking at any more
function toCanvas() { if (!S.present) canvas.focus({preventScroll: true}); }

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
  // The card is a card over the drawing, and the moment a component most
  // wants turning is the moment its card is open -- right after the drop
  // that made it, with the caret parked in the label box. The turn keys
  // therefore reach the drawing from inside the card, where every other
  // shortcut correctly does not: `f`, `d`, `z` and `p` are letters someone
  // is trying to type into a name, and a bracket is not. Without this the
  // keys were dead in the one place they were wanted, and the reader who
  // pressed `]` on a freshly dropped path got a `]` in its label.
  if ((e.key === "[" || e.key === "]") && S.sel) {
    e.preventDefault(); e.stopPropagation();
    turnSelected(e.key === "]" ? 1 : -1);
    return;
  }
  // the card handles its own keys and says so: the document's Escape
  // chain would otherwise find the card already shut and go on to close
  // whatever is behind it
  if (e.key === "Enter" && e.target.tagName === "INPUT") {
    e.preventDefault(); e.stopPropagation(); e.target.blur(); closePopover(); toCanvas();
  }
  if (e.key === "Escape") { e.stopPropagation(); closePopover(); toCanvas(); }
});
pop.addEventListener("click", (e) => {
  const rot = e.target.dataset.rot;
  if (rot && S.sel) {
    if (rot === "reset") { applyField(S.sel, "angle", ""); openPopover(S.sel); return; }
    const box = pop.querySelector('input[data-field="angle"]');
    const now = Number(box && box.value) || 0;
    // whatever is in the box tidies itself to a multiple of 45 on the way
    const next = ((Math.round(now / 45) * 45 + Number(rot)) % 360 + 360) % 360;
    applyField(S.sel, "angle", String(next));
    openPopover(S.sel);
    return;
  }
  const act = e.target.dataset.act;
  if (!act || !S.sel) return;
  const sel = S.sel, el = element(sel);
  if (act === "delete") { edit(() => removeElement(sel)); select(null); return; }
  if (act === "connect") { startConnect(el.id, "cond"); return; }
  if (act === "swap") { edit(() => { [el.from, el.to] = [el.to, el.from]; }); openPopover(sel); return; }
  if (act === "unpin") { edit(() => { dropBracket(el); delete el.at; }); return; }
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
      if (sel.role === "branch" && (value === "flow" || value === "stream")) delete e.angle;
      if (sel.role === "branch" && (value === "break" || value === "link" || value === "stream")) { delete e.value; delete e.rate; }
      if (sel.role === "branch" && value !== "stream") { delete e.mdot; delete e.cp; }
      if (sel.role === "branch" && value === "stream") { delete e.count; delete e.arrangement; ensureStreamUnits(d); }
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
  // The diagram's name is not here. It is the one in the top bar, which
  // names the file and, when the reader says so, is drawn on the page:
  // two boxes for one name was the confusion this card used to carry.
  let h = `<h4>Units &amp; rail</h4>`;
  for (const q of ["R", "C", "P", "q", "q″"]) h += field(`Unit of ${q}`, text(`unit:${q}`, u[q], q === "R" ? "K/W" : ""));
  // A stream states these two, and without them here the branch card asked
  // for a mass flow that validation then refused for having no unit, with
  // nowhere in the editor to give it one.
  h += field(`Unit of ṁ`, text("unit:mdot", u.mdot, "kg/s"));
  h += field(`Unit of <i>c</i><sub>p</sub>`, text("unit:cp", u.cp, "kJ/kg·K"));
  h += field("Unit of T", text("unit:T", T.unit, "°C or K"));
  h += field("T scale", selectBox("scale", T.scale || "", ["", "absolute", "rise"], {"": "(unstated)"}));
  h += `<details ${d.rail ? "open" : ""}><summary>Reference rail</summary>`;
  h += field("Reference", selectBox("rail:reference", d.rail ? d.rail.reference : "", ["", ...d.nodes.map((n) => n.id)], {"": "(no rail)"}));
  h += field("Rail y", num("rail:y", d.rail && d.rail.y, 10));
  h += `</details>`;
  h += `<div class="ed-row"><button type="button" data-act="solve" title="Give every node without a place one, along a chain">Place unplaced nodes</button></div>`;
  pop.innerHTML = h;
  pop.hidden = false;
  underButton(pop, $("ed-settings"));
  S.sel = null;
});
pop.addEventListener("change", (e) => {
  const f = e.target.dataset.field;
  if (!f || S.sel) return;
  const value = e.target.value === "" ? null : e.target.value;
  edit((d) => {
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
const STORE = {index: "thermodraw:index", file: (id) => `thermodraw:file:${id}`, last: "thermodraw:last", theme: "thermodraw:theme",
               toured: "thermodraw:toured"};
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
  S.data = ensureStreamUnits(data);
  save();
  showFile();
}

function openFile(id) {
  const raw = localStorage.getItem(STORE.file(id));
  const ix = readIndex().find((f) => f.id === id);
  if (!raw || !ix) return false;
  S.file = {id, name: ix.name};
  S.data = ensureStreamUnits(JSON.parse(raw));
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

// A diagram is named once. The name is the file's, and the checkbox says
// whether it also goes inside the file as `title`, which is what an
// exported page is called and what names the copy at the far end of a
// share link. It is not drawn on the diagram; nothing draws a title.
// There used to be a second name for this under Title & units, which is
// why nobody could tell which of the two they were editing.
function renameFile(id, anchor) {
  const ix = readIndex();
  const f = ix.find((x) => x.id === id);
  if (!f) { toast("That file is not in this browser any more."); return; }
  const open = S.file && S.file.id === id;
  const drawn = open && S.data && S.data.title != null;
  closeMenu();
  pop.innerHTML = `<h4>Name this diagram</h4>`
    + field("Name", `<input type="text" data-rn="name" value="${escapeHtml(f.name)}" autocomplete="off">`)
    + (open ? `<label class="ed-check"><input type="checkbox" data-rn="drawn"${drawn ? " checked" : ""}>`
              + `<span>Keep this name inside the file</span></label>`
              + `<p class="ed-hint">Then an exported page is called this, and so is the`
              + ` copy anyone gets from a share link.</p>`
            : `<p class="ed-hint">Open this file to choose whether its name travels with it.</p>`)
    + `<div class="ed-row"><button type="button" data-rn="ok">Rename</button>`
    + `<button type="button" data-rn="cancel">Cancel</button></div>`;
  pop.dataset.rename = id;
  pop.hidden = false;
  underButton(pop, anchor || $("ed-file"));
  const box = pop.querySelector('input[data-rn="name"]');
  box.focus(); box.select();
  S.sel = null;
}

function commitRename() {
  const id = pop.dataset.rename;
  if (!id) return;
  const name = (pop.querySelector('input[data-rn="name"]').value || "").trim();
  const drawnBox = pop.querySelector('input[data-rn="drawn"]');
  if (!name) { toast("A diagram needs a name."); return; }
  const ix = readIndex();
  const f = ix.find((x) => x.id === id);
  if (f) { f.name = name; writeIndex(ix); }
  if (S.file && S.file.id === id) {
    S.file.name = name;
    if (drawnBox) edit((d) => { if (drawnBox.checked) d.title = name; else delete d.title; });
    else save();
    updateChrome();
  }
  closeRename();
  renderFiles();
}

function closeRename() { delete pop.dataset.rename; closePopover(); toCanvas(); }

pop.addEventListener("click", (e) => {
  const a = e.target.dataset.rn;
  if (!a || !pop.dataset.rename) return;
  if (a === "ok") commitRename();
  if (a === "cancel") closeRename();
});
pop.addEventListener("keydown", (e) => {
  if (!pop.dataset.rename) return;
  if (e.key === "Enter") { e.preventDefault(); commitRename(); }
});

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
$("ed-file").addEventListener("click", () => { if (S.file) renameFile(S.file.id, $("ed-file")); });

// ---------------------------------------------------------------- menus
const menu = $("ed-menu");
function closeMenu() {
  menu.hidden = true;
  delete menu.dataset.file;
  $("ed-more").setAttribute("aria-expanded", "false");
}

// On a narrow screen the same buttons wrap to four rows and take a quarter
// of the window, so they move into one menu that opens under a single
// button. The buttons themselves stay: the menu clicks them.
$("ed-more").addEventListener("click", () => {
  if (!menu.hidden) { closeMenu(); return; }
  const ids = ["ed-delete", null, "ed-fit", "ed-notation", "ed-theme",
               "ed-present", null, "ed-settings", "ed-share", "ed-export"];
  menu.innerHTML = ids.map((id) => id
    ? `<button type="button" data-go="${id}"${$(id).disabled ? " disabled" : ""}>`
      + `${escapeHtml($(id).textContent)}</button>`
    : "<hr>").join("");
  delete menu.dataset.file;
  underButton(menu, $("ed-more"));
  menu.hidden = false;
  $("ed-more").setAttribute("aria-expanded", "true");
});
menu.addEventListener("click", async (e) => {
  const go = e.target.dataset.go;
  if (go) { closeMenu(); $(go).click(); return; }
  const f = e.target.dataset.f, x = e.target.dataset.x;
  const id = menu.dataset.file;
  closeMenu();
  if (f && id) {
    if (f === "rename") renameFile(id, $("ed-file"));
    if (f === "del") deleteFile(id);
    if (f === "dup") {
      const src = readIndex().find((y) => y.id === id);
      const copy = JSON.parse(localStorage.getItem(STORE.file(id)));
      const name = src.name + " (copy)";
      // one name: if the original drew its own, the copy draws the copy's
      if (copy.title != null) copy.title = name;
      newFile(name, copy);
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
$("ed-export").addEventListener("click", () => {
  menu.innerHTML = `
    <button data-x="svg">SVG that follows light and dark</button>
    <button data-x="svg-light">SVG, light, for Word and slides</button>
    <button data-x="svg-dark">SVG, dark</button>
    <button data-x="png-light">PNG, light, 2×</button>
    <button data-x="png-dark">PNG, dark, 2×</button>
    <hr><button data-x="page">HTML page with its controls</button>
    <button data-x="json">JSON, the diagram itself</button>`;
  // the button itself is hidden on a narrow screen, where the menu that
  // opened this one is the thing to sit under
  underButton(menu, $("ed-export").offsetParent ? $("ed-export") : $("ed-more"));
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

// ------------------------------------------------------------------ tour
// Four steps on the real editor, each finished by doing it rather than by
// clicking Next: a page of prose about dragging is not how anyone learns
// to drag. It runs on a scratch file so a reader who already has work open
// cannot lose any of it.
let tour = null;   // {step, fileId, from}

const TOUR = [
  {at: () => document.querySelector('.ed-card[data-key="cond"]'),
   text: "<b>Drag this onto the drawing.</b> A path is what heat crosses — "
       + "here, conduction. It arrives with a place at each end, which is "
       + "what a path needs to be a path.",
   done: () => S.data.branches.length >= 1},
  {at: () => hitFor("branch", 0),
   text: "<b>Click the path and give it a value.</b> Every component opens a "
       + "card beside itself: label, value, kind, and more under <i>More</i>. "
       + "<b>[</b> and <b>]</b> turn whatever is selected.",
   done: () => S.data.branches.length >= 1 && S.data.branches[0].value != null},
  {at: () => document.querySelector('.ed-card[data-key="conv"]'),
   text: "<b>Drag a second path in, then drag one of its red ends onto an "
       + "end of the first.</b> A red dot is an end joined to nothing; drag "
       + "or click it to say which place it meets.",
   done: () => S.data.branches.length >= 2 && S.loose.length === 0},
  {at: () => $("ed-findings"),
   text: "<b>That is the whole editor.</b> This strip is what "
       + "<code>thermodraw check</code> says about your drawing. Everything "
       + "else is behind <b>?</b>. Your practice drawing is kept, as "
       + "<i>Tour</i>.",
   done: null},
];

function tourRunning() { return tour !== null; }

function hitFor(role, index) {
  return hitsG.querySelector(`rect[data-role="${role}"][data-index="${index}"]`);
}

function startTour() {
  setHelp(false);
  closePopover(); closeMenu(); closeFiles();
  const from = S.file ? S.file.id : null;
  // marked as taken the moment it starts, not when it ends: a reload
  // partway through must not hand the reader the same four steps again
  try { localStorage.setItem(STORE.toured, "1"); } catch {}
  newFile("Tour", BLANK());
  tour = {step: 0, fileId: S.file.id, from};
  drawTour();
}

function tourCheck() {
  if (!tour) return;
  const step = TOUR[tour.step];
  if (step && step.done && step.done()) { tour.step++; }
  drawTour();
}

function drawTour() {
  const card = $("ed-tour");
  if (!tour || tour.step >= TOUR.length) { card.hidden = true; return; }
  const step = TOUR[tour.step];
  const last = tour.step === TOUR.length - 1;
  card.innerHTML = `<p class="ed-tour-n">Step ${tour.step + 1} of ${TOUR.length}</p>`
    + `<p>${step.text}</p>`
    + `<div class="ed-row"><button type="button" data-tour="end">`
    + `${last ? "Done" : "Skip the tour"}</button></div>`;
  card.hidden = false;
  const target = step.at();
  const r = target ? target.getBoundingClientRect() : null;
  const w = card.offsetWidth || 260, h = card.offsetHeight || 130;
  // beside what it points at, on whichever side has room for it
  let x = 16, y = 16;
  if (r && r.width) {
    x = r.left - w - 14 >= 8 ? r.left - w - 14 : r.right + 14;
    y = r.top;
    if (x + w > innerWidth - 8) { x = clamp(r.left, 8, innerWidth - w - 8); y = r.top - h - 14; }
    if (y + h > innerHeight - 8) y = innerHeight - h - 8;
  }
  card.style.left = clamp(x, 8, Math.max(8, innerWidth - w - 8)) + "px";
  card.style.top = clamp(y, 8, Math.max(8, innerHeight - h - 8)) + "px";
  card.classList.toggle("ed-tour-done", last);
  document.querySelectorAll(".ed-tour-mark").forEach((n) => n.classList.remove("ed-tour-mark"));
  if (target) target.classList.add("ed-tour-mark");
}

function endTour() {
  if (!tour) return;
  const t = tour;
  tour = null;
  $("ed-tour").hidden = true;
  document.querySelectorAll(".ed-tour-mark").forEach((n) => n.classList.remove("ed-tour-mark"));
  // A reader who reached the end drew that themselves and keeps it. One
  // who skipped part way asked for nothing and is left with nothing.
  const finished = t.step >= TOUR.length - 1;
  if (S.file && S.file.id === t.fileId && !finished) {
    writeIndex(readIndex().filter((f) => f.id !== t.fileId));
    localStorage.removeItem(STORE.file(t.fileId));
    if (!(t.from && openFile(t.from))) {
      const first = readIndex().sort((a, b) => b.updated - a.updated)[0];
      if (!(first && openFile(first.id))) newFile("Untitled", BLANK());
    }
    renderFiles();
  }
}

$("ed-tour").addEventListener("click", (e) => { if (e.target.dataset.tour === "end") endTour(); });
$("ed-take-tour").addEventListener("click", startTour);
addEventListener("resize", () => { if (tour) drawTour(); });

// ----------------------------------------------------------------- chrome
function updateChrome() {
  $("ed-file").textContent = S.file ? S.file.name : "Untitled";
  $("ed-undo").disabled = !S.undo.length;
  $("ed-redo").disabled = !S.redo.length;
  $("ed-delete").disabled = !S.sel;
  $("ed-notation").textContent = `Notation: ${S.notation}`;
  $("ed-notation").setAttribute("aria-pressed", String(S.notation === "zigzags"));
  $("ed-physics").checked = S.physics;
  $("ed-theme").textContent = `Theme: ${currentTheme()}`;
  document.title = `${S.file ? S.file.name : "Editor"} · ThermoDraw ${BUILD.version}`;
}
$("ed-undo").addEventListener("click", undo);
$("ed-redo").addEventListener("click", redo);
$("ed-delete").addEventListener("click", removeSelected);
$("ed-fit").addEventListener("click", () => { S.touched = false; fit(); });
$("ed-notation").addEventListener("click", () => {
  S.notation = S.notation === "boxes" ? "zigzags" : "boxes";
  updateChrome();
  refresh();
});
$("ed-physics").addEventListener("change", () => {
  S.physics = $("ed-physics").checked;
  refresh();
});
$("ed-findings-toggle").addEventListener("click", () => {
  const shut = !$("ed-findings-list").hidden;
  if (shut) $("ed-findings-toggle").dataset.closed = "1";
  else delete $("ed-findings-toggle").dataset.closed;
  openFindings(!shut);
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
    if (!pop.hidden) { closePopover(); toCanvas(); return; }
    if (filesPanel.classList.contains("ed-open")) { closeFiles(); return; }
    if (S.mode !== "idle") { setMode("idle"); return; }
    // last, and only with nothing else open: closing the card you were
    // asked to type into must not throw away the tour and its drawing
    if (tour) { endTour(); return; }
    select(null);
    return;
  }
  if (typingInField) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
  if (e.key === "Delete" || e.key === "Backspace") {
    if (S.sel && !S.present) { e.preventDefault(); removeSelected(); }
    return;
  }
  if (S.present) {
    if (e.key === "ArrowRight") stepFile(1);
    if (e.key === "ArrowLeft") stepFile(-1);
  }
  if (e.key === "[" || e.key === "]") { turnSelected(e.key === "]" ? 1 : -1); return; }
  if (e.key === "f" || e.key === "F") { S.touched = false; fit(); }
  if (e.key === "z" || e.key === "Z") $("ed-notation").click();
  if (e.key === "d" || e.key === "D") $("ed-theme").click();
  if (e.key === "p" || e.key === "P") { $("ed-physics").checked = !$("ed-physics").checked; $("ed-physics").dispatchEvent(new Event("change")); }
});

document.addEventListener("pointerdown", (e) => {
  if (!pop.hidden && !pop.contains(e.target) && !e.target.closest("#ed-hits") && !e.target.closest("#ed-ui")
      && e.target.id !== "ed-settings" && e.target.id !== "ed-file") closePopover();
  if (!menu.hidden && !menu.contains(e.target) && e.target.id !== "ed-export" && e.target.id !== "ed-more" && e.target.dataset.act !== "more") closeMenu();
  if (!$("ed-help-panel").hidden && !$("ed-help-panel").contains(e.target) && e.target.id !== "ed-help") setHelp(false);
});
window.addEventListener("resize", () => { if (S.sel && !pop.hidden) placePopover(S.sel); });

// ------------------------------------------------------------------- boot
(async function boot() {
  try { const t = localStorage.getItem(STORE.theme); if (t) document.documentElement.dataset.theme = t; } catch {}
  rpc.on("progress", (m) => { $("ed-loading-text").textContent = m.text; });
  rpc.on("failed", (m) => { $("ed-loading-text").textContent = "The library could not start: " + m.text; });
  rpc.on("ready", (m) => {
    const style = document.createElement("style");
    style.textContent = m.head.faces.join("") + m.head.vars + m.head.css;
    document.head.appendChild(style);
    if (m.head.pitch) PITCH = m.head.pitch;
    S.ready = true;
    $("ed-loading").hidden = true;
    refresh();
    setTimeout(() => fit(), 60);
    // a first visit is taught by doing, not by reading the help panel
    try {
      if (!localStorage.getItem(STORE.toured) && !location.hash
          && S.data && !S.data.nodes.length) setTimeout(startTour, 400);
    } catch {}
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
