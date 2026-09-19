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

import {emptyFree, mergeNodes, normalizeOverlaps, deleteNode, deletePath, detachEndpoint, pruneEndpoints, addJunction, insertResistance, relocateResistance, sharedTerminalLead} from './topology.js';
import {groupProposal, expandSegment, clearGroupLanes} from './group.js';
const $ = (id) => document.getElementById(id);
const BUILD = window.THERMODRAW;
const GRID = 10;
let freeDrag = false;
const snap = (v) => freeDrag ? v : Math.round(v / GRID) * GRID;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

// The solver's own spacing between two nodes on a run, sent by
// `_editor.head` so the editor's number and the library's are one number.
// A dropped path is laid out at it, and a run built by hand at it is the
// run `_solve` would have placed. The habit's 220 until the library answers.
let PITCH = 220;

// ------------------------------------------------------------- the library
const rpc = (() => {
  const w = new Worker(`worker.js?build=${BUILD.revision || BUILD.version}`, {type: "module"});
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
  analysis: {check_policy:"analysis", tolerance:{relative:0.01,absolute_w:0.001}},
  layout_options: {max_width:640,wrap:true,stack:true},
});

// Additional document and physics controls use the same validated Python bridge.
// Each committed edit is one Undo step; every asynchronous result is revision guarded.
async function openAssignmentOptions(selection=null, scenarioMode=false) {
  const session=scenarioMode?solveSession:null, sessionRevision=session?.revision;
  const revision=S.revision, base=structuredClone(session?session.data:S.data), sel=selection?{...selection}:null;
  const current=()=>S.revision===revision && (!session || session===solveSession && !session.stale && session.revision===sessionRevision);
  const info=await rpc.call('assignment_info',base);
  if(!current()) return;
  if(info.error){toast(info.error);return;}
  const object=sel?base[COLLECTION[sel.role]]?.[sel.index]:null;
  const dialog=document.createElement('dialog');dialog.className='ed-assignment-dialog';
  const field=(label,markup)=>`<label><span>${escapeHtml(label)}</span>${markup.replace(/<(input|select) /,`<$1 aria-label="${escapeHtml(label)}" `)}</label>`;
  const input=(id,value='',type='text')=>`<input id="${id}" type="${type}" ${type==='number'?'step="any"':''} value="${escapeHtml(String(value??''))}">`;
  const choice=(id,value,items)=>`<select id="${id}">${items.map(([v,label])=>`<option value="${v}" ${value===v?'selected':''}>${escapeHtml(label)}</option>`).join('')}</select>`;
  const button=(op,label)=>`<button type="button" data-assignment="${op}">${label}</button>`;
  const basis=base.network_basis||{kind:'total'}, opts=base.layout_options||{};
  let h='<h2>Physics and document options</h2><p>Apply one change at a time. Undo restores the previous drawing.</p>';
  h+='<details '+(!object?'open':'')+'><summary>Network basis and checking</summary>';
  h+=field('Network basis',choice('hw-basis',basis.kind,[['total','Total heat rate'],['area','Per unit area'],['length','Per unit length']]))+field('Reference size',input('hw-reference',basis.value??1,'number'))+field('Reference unit',input('hw-reference-unit',basis.unit||'m²'));
  h+=button('basis','Convert basis, preserving total heat rates');
  h+='<p>All network branches share this reference. Separate volume balances remain total rates. mK/W means millikelvin per watt; use m·K/W for metre-kelvin per watt.</p>';
  h+=field('Check policy',choice('hw-policy',base.analysis?.check_policy||'legacy',[['legacy','Legacy rounded annotations (15%)'],['analysis','Use analysis tolerance']]))+field('Relative tolerance (%)',input('hw-relative',100*(base.analysis?.tolerance?.relative??.01),'number'))+field('Absolute tolerance (W)',input('hw-absolute',base.analysis?.tolerance?.absolute_w??.001,'number'))+button('policy','Apply checking policy');
  h+=field('Temperature reference description',input('hw-reference-label',base.temperature_reference||''))+field('Temperature meaning',choice('hw-scale',temperatureScale(base)||'',[['','Unspecified'],['absolute','Actual temperature'],['rise','Temperature rise']]))+button('reference','Apply temperature meaning')+'</details>';
  const node=sel?.role==='node'?object.id:sel?.role==='branch'?object.from:sel?.role==='source'?(object.to||object.from):null;
  const component=info.components.find(ids=>ids.includes(node))||[];
  h+='<details><summary>Document layout and separate cases</summary>'+field('Maximum width (drawing units)',input('hw-width',opts.max_width??640,'number'))+field('Starting endpoint',choice('hw-start',opts.starts?.find(n=>component.includes(n))||'',[['','Use temperature heuristic'],...component.map(n=>[n,nodeName(n)])]));
  h+=field('Wrap long chains',choice('hw-wrap',opts.wrap===false?'no':'yes',[['yes','Yes'],['no','No']]))+field('Stack separate components',choice('hw-stack',opts.stack===false?'no':'yes',[['yes','Yes'],['no','No']]));
  h+=button('layout','Re-layout all components');if(component.length)h+=button('layout-selected','Re-layout this component');
  h+='<p>Re-layout replaces the affected node positions and routes. Fonts retain their size. Width limits that cannot be met appear in Findings.</p>';
  if(component.length){const existing=(base.cases||[]).find(g=>g.nodes.includes(node));h+=field('Case ID',input('hw-case-id',existing?.id||''))+field('Case heading',input('hw-case-label',existing?.label||''))+button('case','Declare this component as a separate case')+button('uncase','Remove case declaration');}
  h+='</details>';
  if(sel?.role==='source' && Number(object.value)<0) h+='<section><h3>Source direction conflict</h3><p>The negative magnitude reverses the drawn arrow. This correction makes the magnitude positive and reverses the arrow'+(!['flow','flux'].includes(object.kind)?' by converting this source to Flow':'')+'.</p>'+button('correct-source','Correct direction explicitly')+'</section>';
  const resistance=sel?.role==='branch' && !['cap','flow','stream','break','link'].includes(object.kind||'cond');
  if(resistance){h+='<details open><summary>Branch heat rate</summary>'+field('Rate convention',choice('hw-rate',object.rate_convention||'magnitude',[['magnitude','Magnitude'],['signed','Signed from start to end']]))+button('rate','Apply rate convention')+button('calculate-rate','Calculate heat rate')+'<p data-rate-result></p>'+button('apply-rate','Apply calculated heat rate to label')+'</details>';}
  if(sel?.role==='branch' && (resistance||object.kind==='cap')) {
    const kinds=object.kind==='cap'?['capacity']:['plane','cylinder','sphere','convection','contact'];
    const labels={plane:'Plane conduction',cylinder:'Cylindrical conduction',sphere:'Spherical conduction',convection:'Convection',contact:'Contact resistance',capacity:'Heat capacity'};
    h+='<details open><summary>Derive from physical inputs</summary>'+field('Relation',choice('hw-derivation',object.derivation?.kind||'manual',[['manual','Manual value'],...kinds.map(k=>[k,labels[k]])]))+'<div data-derivation-inputs></div>'+field('Source or assumptions',input('hw-source',object.derivation?.source||''))+button('derivation','Switch to selected relation')+'<p>Physical dimensions are independent of drawing size. Derived values are recalculated at full precision.</p></details>';
  }
  if(sel?.role==='volume') {
    const relation=object.storage_relation||{};
    const mode=relation.branch?'branch':relation.capacity_derivation?'materials':relation.capacity?'capacity':'manual';
    h+='<details open><summary>Finite-interval energy storage</summary>'+field('Capacity source',choice('hw-storage-mode',mode,[['manual','Manual storage power'],['capacity','Known heat capacity'],['materials','Density, specific heat and volume'],['branch','Capacitance branch']]))+'<div data-storage-inputs></div>'+field('Temperature change (signed)',input('hw-delta',relation.delta_t?.value??1,'number'))+field('Temperature change unit',input('hw-delta-unit',relation.delta_t?.unit||'K'))+field('Duration',input('hw-duration',relation.duration?.value??1,'number'))+field('Duration unit',input('hw-duration-unit',relation.duration?.unit||'h'))+button('storage','Apply storage relation')+'<p>Calculates energy change and average storage power over this interval. It does not integrate a transient temperature history.</p></details>';
  }
  if(object){
    h+='<details><summary>Label formatting</summary><div data-label-runs></div>'+button('add-run','Add text segment')+button('plain-label','Use plain label')+button('labels','Apply formatted label');
    if(['region','volume','surface','transfer','annotation'].includes(sel.role))h+=field('Show label',choice('hw-show',object.show_label===false?'no':'yes',[['yes','Yes'],['no','No']]));
    if(['region','volume'].includes(sel.role))h+=field('Keep label inside',choice('hw-inside',object.label_inside?'yes':'no',[['no','Allow outside'],['yes','Require inside']]))+'<p>Labels that cannot fit inside produce a finding.</p>';
    h+='</details>';
  }
  if(info.derivations.length)h+='<details><summary>Evaluated relations</summary>'+info.derivations.map(r=>`<p>${escapeHtml(r.id||'Branch '+r.index)}: ${escapeHtml(r.formula)} = ${fmtPhysics(r.value)} ${escapeHtml(r.unit)}${r.energy_j==null?'':`<br>Energy change: ${fmtPhysics(r.energy_j)} J; C = ${fmtPhysics(r.capacity_j_per_k)} J/K`}</p><pre>${escapeHtml(JSON.stringify(r.inputs,null,2))}</pre>`).join('')+'</details>';
  h+='<p data-assignment-error role="alert"></p><button type="button" data-assignment="close">Close</button>';
  dialog.innerHTML=h;document.body.appendChild(dialog);
  if(scenarioMode) {
    dialog.querySelector('h2').textContent='Scenario derivation inputs';
    dialog.querySelector('p').textContent='Changes stay in this calculation until Review and Apply.';
    for(const section of dialog.querySelectorAll('details,section')) if(!section.querySelector('#hw-derivation,#hw-storage-mode') && section.querySelector('summary')?.textContent!=='Evaluated relations') section.remove();
  }
  const val=id=>dialog.querySelector('#'+id)?.value;
  const numeric=id=>{const raw=val(id);if(raw==null||!raw.trim()||!Number.isFinite(Number(raw)))throw Error('Enter a finite number for '+id.replace('hw-',''));return Number(raw);};
  const names={L:'Length / thickness',A:'Physical area',k:'Thermal conductivity',r1:'Inner radius',r2:'Outer radius',h:'Convection coefficient',contact_resistivity:'Contact resistivity',rho:'Density',cp:'Specific heat',V:'Physical volume'};
  function quantityFields(prefix,kind,record={}) {return Object.entries(info.inputs[kind]||{}).map(([key,unit])=>field(names[key],input(prefix+key,record[key]?.value??'','number'))+field(names[key]+' unit',input(prefix+key+'-unit',record[key]?.unit||unit))).join('');}
  function readQuantities(prefix,kind){return Object.fromEntries(Object.keys(info.inputs[kind]).map(key=>[key,{value:numeric(prefix+key),unit:val(prefix+key+'-unit')}]));}
  const renderDerivation=()=>{const slot=dialog.querySelector('[data-derivation-inputs]');if(slot)slot.innerHTML=quantityFields('hw-d-',val('hw-derivation'),object.derivation?.inputs||{});};
  const renderStorage=()=>{const slot=dialog.querySelector('[data-storage-inputs]');if(!slot)return;const r=object.storage_relation||{},mode=val('hw-storage-mode');slot.innerHTML=mode==='materials'?quantityFields('hw-c-','capacity',r.capacity_derivation?.inputs||{}):mode==='capacity'?field('Heat capacity',input('hw-capacity',r.capacity?.value??'','number'))+field('Capacity unit',input('hw-capacity-unit',r.capacity?.unit||'J/K')):mode==='branch'?field('Capacitance branch',choice('hw-cap-branch',r.branch||'',[['','Choose a branch with an ID'],...base.branches.filter(b=>b.kind==='cap'&&b.id).map(b=>[b.id,b.label||b.id])])):'';};
  renderDerivation();renderStorage();
  const runSlot=dialog.querySelector('[data-label-runs]');
  function addRun(run={text:'',position:'normal'}){const row=document.createElement('div');row.className='ed-row';row.innerHTML=`<input data-run-text aria-label="Text segment" value="${escapeHtml(run.text)}"><select data-run-position aria-label="Text position">${['normal','subscript','superscript'].map(p=>`<option ${p===(run.position||'normal')?'selected':''}>${p}</option>`).join('')}</select><button type="button" data-remove-run aria-label="Remove text segment">Remove</button>`;runSlot.appendChild(row);}
  if(runSlot)(object.label_runs||[{text:object.label||''}]).forEach(addRun);
  dialog.addEventListener('change',e=>{if(e.target.id==='hw-derivation')renderDerivation();if(e.target.id==='hw-storage-mode')renderStorage();if(e.target.id==='hw-basis')dialog.querySelector('#hw-reference-unit').value=val('hw-basis')==='length'?'m':'m²';});
  dialog.addEventListener('close',()=>dialog.remove(),{once:true});
  dialog.addEventListener('click',async e=>{
    if(e.target.closest('[data-remove-run]')){e.target.closest('.ed-row').remove();return;}
    let op=e.target.closest('[data-assignment]')?.dataset.assignment;if(!op)return;
    if(op==='close'){dialog.close();return;}if(op==='add-run'){addRun();return;}
    const error=dialog.querySelector('[data-assignment-error]');error.textContent='';
    try {
      if(!current()||JSON.stringify(session?session.data:S.data)!==JSON.stringify(base))throw Error('The drawing changed. Close and reopen these options.');
      let payload={};
      if(op==='basis'){const kind=val('hw-basis');payload=kind==='total'?{kind}:{kind,value:numeric('hw-reference'),unit:val('hw-reference-unit')};}
      if(op==='policy')payload={policy:val('hw-policy'),tolerance:{relative:numeric('hw-relative')/100,absolute_w:numeric('hw-absolute')}};
      if(op==='reference')payload={scale:val('hw-scale'),reference:val('hw-reference-label')};
      if(op==='layout'||op==='layout-selected'){const starts=(opts.starts||[]).filter(n=>!component.includes(n));if(val('hw-start'))starts.push(val('hw-start'));payload={settings:{max_width:numeric('hw-width'),wrap:val('hw-wrap')==='yes',stack:val('hw-stack')==='yes',starts},apply:true,node:op==='layout-selected'?node:null};op='layout';}
      if(op==='case'||op==='uncase'){payload={id:op==='uncase'?'':val('hw-case-id'),label:val('hw-case-label'),nodes:component};if(op==='case'&&!payload.id.trim())throw Error('Enter a case ID.');op='case';}
      if(['correct-source','calculate-rate','apply-rate'].includes(op))payload={index:sel.index};
      if(op==='rate')payload={index:sel.index,signed:val('hw-rate')==='signed'};
      if(op==='derivation'){const kind=val('hw-derivation');payload={index:sel.index,replace_unknown:true,derivation:kind==='manual'?null:{kind,inputs:readQuantities('hw-d-',kind),source:val('hw-source')}};}
      if(op==='storage'){const mode=val('hw-storage-mode');let relation=null;if(mode!=='manual'){relation={delta_t:{value:numeric('hw-delta'),unit:val('hw-delta-unit')},duration:{value:numeric('hw-duration'),unit:val('hw-duration-unit')}};if(mode==='capacity')relation.capacity={value:numeric('hw-capacity'),unit:val('hw-capacity-unit')};if(mode==='materials')relation.capacity_derivation={kind:'capacity',inputs:readQuantities('hw-c-','capacity')};if(mode==='branch')relation.branch=val('hw-cap-branch');}payload={index:sel.index,relation};}
      if(op==='labels'||op==='plain-label'){payload={role:sel.role,index:sel.index,runs:op==='plain-label'?null:[...runSlot.children].map(row=>({text:row.querySelector('[data-run-text]').value,position:row.querySelector('[data-run-position]').value})),show:val('hw-show')!=='no',inside:val('hw-inside')==='yes'};op='labels';}
      const response=await rpc.call('assignment_edit',base,op,payload);
      if(!current())throw Error('The drawing or scenario changed while calculating. Reopen these options.');
      if(response.error)throw Error(response.error);
      if(op==='calculate-rate'){dialog.querySelector('[data-rate-result]').textContent=`${response.value} ${response.unit}, positive from ${response.from} to ${response.to} (${response.watts} W total).`;return;}
      if(session)sessionEdit(d=>replaceDocument(d,response.document));else edit(d=>replaceDocument(d,response.document));dialog.close();if(!session)closePopover();toast(session?'Scenario updated. Calculate, review and apply to save.':'Change applied. Undo restores the previous drawing.');
    }catch(exc){error.textContent=exc.message;}
  });
  dialog.showModal();
}

let physicsReview = null;
let solveSession=null, assessmentSequence=0;
let solveOpen=false, solveValue=null, physicsApplied=[], physicsRequest=0, exampleCatalog=[];
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
  generation: 0, revision: 0, selection: [], preview: null,
  needsFit: false,
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
const COLLECTION = {node: "nodes", branch: "branches", source: "sources", region: "regions", volume: "control_volumes", surface: "control_surfaces", transfer: "transfers", annotation: "annotations"};
const list = (role) => S.data[COLLECTION[role]] || [];
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
const ALIGN_PX = 12;
let lastAlign = {x: null, y: null};   // what the guides should show

function alignedSnap(x, y, excludeId) {
  if (freeDrag) { lastAlign = {x:null, y:null}; return [x,y]; }
  const reach = ALIGN_PX * unitsPerPixel();
  const others = S.data.nodes.filter((n) => n.at && n.id !== excludeId);
  const pick = (v, axis) => {
    const held = lastAlign[axis ? "y" : "x"];
    if (drag && held && held.from.id !== excludeId && Math.abs(v - held.value) < 20 * unitsPerPixel()) return held;
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
  lastAlign = {x: ax, y: ay};
  return [ax ? ax.value : snap(x), ay ? ay.value : snap(y)];
}

function newNodeId() {
  const used = new Set(S.data.nodes.map((n) => n.id));
  for (let i = 1; ; i++) if (!used.has(`n${i}`)) return `n${i}`;
}

function snapshot() { return JSON.stringify(S.data); }
function replaceDocument(target,source) {
  if(target===source)return;
  for(const key of Object.keys(target))if(!(key in source))delete target[key];
  Object.assign(target,source);
}

let topologyPending=0;
function clearBusy(){if(!topologyPending)delete document.body.dataset.busy;}

async function commitTopology(proposal,selection=proposal.selection,undoSnapshot=null) {
  if(proposal.conflicts?.length){toast(proposal.conflicts.join(' '));return false;}
  const original=snapshot(),generation=S.generation,revision=S.revision;
  topologyPending++;document.body.dataset.busy='1';
  try {
    const scene=await rpc.call('scene',proposal.document,S.notation,S.physics,null,S.file?.display||{mode:'automatic'});
    if(generation!==S.generation || revision!==S.revision || snapshot()!==original)return false;
    if(scene.error){toast(scene.error);return false;}
    proposal.validatedInk=scene.ink;
    if(JSON.stringify(proposal.document)===original)return true;
    edit(d=>replaceDocument(d,proposal.document));
    if(undoSnapshot!=null)S.undo[S.undo.length-1]=undoSnapshot;
    if(selection!==undefined)select(selection,false);
    return true;
  }catch(error){toast(error.message);return false;}
  finally {topologyPending--;if(!S.inflight)clearBusy();}
}

function mutationProposal(fn) {
  const original=S.data;S.data=structuredClone(original);
  try{fn();return {document:S.data,conflicts:[]};}finally{S.data=original;}
}

// Every edit goes through here: snapshot for undo, apply, save, redraw.
function edit(fn) {
  cancelGesture();
  S.undo.push(snapshot());
  if (S.undo.length > 200) S.undo.shift();
  S.redo.length = 0;
  const net=S.data.analysis?.network;
  const targets=(net?.resistance_unknowns||[]).map(t=>({target:t,obj:typeof t==='number'?S.data.branches[t]:S.data.branches.find(b=>b.id===t)}));
  fn(S.data);
  if(net && net===S.data.analysis?.network && net.resistance_unknowns) net.resistance_unknowns=targets.filter(t=>S.data.branches.includes(t.obj)).map(t=>typeof t.target==='number'?S.data.branches.indexOf(t.obj):t.obj.id);
  afterEdit();
}

function afterEdit() {
  syncCanonicalTemperatures();
  physicsReview = null; physicsApplied=[];
  if(solveSession) solveSession.stale=true;
  reconcileAnalysis();
  S.revision++;
  save();
  // ahead of the library, which is a round trip away: the dots are read off
  // the diagram, and a reader who has just dropped a path should see where
  // its ends are before the drawing catches up
  if (S.data) drawLoose();
  refresh();
  updateChrome();
  if(solveOpen) analysisPanel();
}

function undo() {
  if(groupDraft) {gateGroup(undo);return;}
  cancelGesture();
  if (!S.undo.length) return;
  S.redo.push(snapshot());
  S.data = JSON.parse(S.undo.pop());
  select(null);
  afterEdit();
}
function redo() {
  if(groupDraft) {gateGroup(redo);return;}
  cancelGesture();
  if (!S.redo.length) return;
  S.undo.push(snapshot());
  S.data = JSON.parse(S.redo.pop());
  select(null);
  afterEdit();
}

function removeElement(sel) {
  const d = S.data;
  if (!element(sel)) return;
  const removed=element(sel), reference=removed.id ? `${sel.role}:${removed.id}` : null;
  if (reference) for (const key of ["regions","control_volumes","control_surfaces","transfers","annotations"]) {
    for (const obj of d[key]||[]) if (obj.links) obj.links=obj.links.filter(l=>l!==reference);
  }
  if (sel.role==="region") for (const v of d.control_volumes||[]) {
    if ((v.regions||[]).includes(removed.id)) { v.regions=v.regions.filter(id=>id!==removed.id); v.incomplete=true; }
  }
  if (sel.role==="surface" || sel.role==="volume") {
    const gone=(d.control_surfaces||[]).filter(s=>sel.role==="volume"?s.volume===removed.id:s.id===removed.id);
    for (const s of gone) {
      const v=(d.control_volumes||[]).find(v=>v.id===s.volume); if(v) v.incomplete=true;
      for(const t of d.transfers||[]) if(t.surface===s.id) {
        const pts=physicalPoints("transfer",t,d); t.at=pts[0].map((n,i)=>(n+pts[1][i])/2); delete t.surface;
      }
    }
    if(sel.role==="volume") d.control_surfaces=(d.control_surfaces||[]).filter(s=>s.volume!==removed.id);
  }
  if(sel.role==="transfer") {
    const s=(d.control_surfaces||[]).find(s=>s.id===removed.surface);
    const v=s&&(d.control_volumes||[]).find(v=>v.id===s.volume); if(v) v.incomplete=true;
  }
  if (sel.role === "node") {
    const id = d.nodes[sel.index].id;
    replaceDocument(d, deleteNode(d, id).document);
  } else {
    if (sel.role === 'branch' || sel.role === 'source') replaceDocument(d,deletePath(d,sel.role,sel.index).document);
    else list(sel.role).splice(sel.index, 1);
  }
  const surviving=new Set(["node","branch","source"].flatMap(role=>list(role).flatMap((e,i)=>[`${role}:@${i}`,...(e.id?[`${role}:${e.id}`]:[])])));
  for(const role of ["region","volume","surface","transfer","annotation"]) for(const obj of list(role)) {
    if(obj.links) obj.links=obj.links.filter(l=>surviving.has(l));
  }
}

function renameNode(oldId, newId) {
  const d = S.data;
  for (const n of d.nodes) if (n.id === oldId) n.id = newId;
  for (const b of d.branches) { if (b.from === oldId) b.from = newId; if (b.to === oldId) b.to = newId; }
  for (const s of d.sources) { if (s.from === oldId) s.from = newId; if (s.to === oldId) s.to = newId; }
  if (d.rail && d.rail.reference === oldId) d.rail.reference = newId;
  for(const g of d.cases||[])g.nodes=g.nodes.map(n=>n===oldId?newId:n);
  if(d.layout_options?.starts)d.layout_options.starts=d.layout_options.starts.map(n=>n===oldId?newId:n);
  if(d.analysis?.network?.unknowns)d.analysis.network.unknowns=d.analysis.network.unknowns.map(n=>n===oldId?newId:n);
  for(const role of ["region","volume","surface","transfer","annotation"]) for(const obj of list(role)) {
    if(obj.links) obj.links=obj.links.map(l=>l===`node:${oldId}`?`node:${newId}`:l);
  }
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
  return emptyFree(node);
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
  for(const source of d.sources||[])for(const end of [source.from,source.to])if(degree.has(end))degree.set(end,degree.get(end)+1);
  const free = (id) => {
    const node = nodeById(id);
    return node && node.at && unsaid(node) && degree.get(id) <= 1;
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
    if (!free(id) || degree.get(id) !== 1) return;
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
async function joinNodes(looseId, targetId) {
  const index = S.data.nodes.findIndex((n) => n.id === looseId);
  if (index < 0 || !nodeById(targetId)) return;
  const proposal = mergeNodes(S.data, looseId, targetId);
  if (proposal.conflicts.length) { reviewNodeMerge(looseId,targetId,proposal.conflicts); return; }
  if(!await commitTopology(proposal,null))return;
  const target = nodeById(targetId);
  select(null);
  toast(`Joined to \u201c${target.label || targetId}\u201d.`,
        {label: "Undo", act: undo});
}

function reviewNodeMerge(sourceId,targetId,conflicts) {
  if(conflicts.some(c=>c.includes('short-circuit'))) {toast(conflicts.join(' '));return;}
  const source=nodeById(sourceId),target=nodeById(targetId),revision=S.revision,generation=S.generation;
  if(!source||!target)return;
  const dialog=document.createElement('dialog');dialog.className='ed-conflict-review';dialog.setAttribute('aria-label','Resolve node properties');
  dialog.innerHTML='<h3>Resolve node properties</h3><p>Choose which information the merged node will keep. The target node retains its identifier.</p>';
  const choices=[];
  for(const key of Object.keys(source)) {
    if(['id','at'].includes(key) || source[key]==null || target[key]==null || JSON.stringify(source[key])===JSON.stringify(target[key]) || key==='kind'&&source[key]==='free')continue;
    const row=document.createElement('label'),caption=document.createElement('span'),choice=document.createElement('select');caption.textContent=key;
    for(const [value,name] of [['target','Target'],['source','Dragged node']]){const option=document.createElement('option');option.value=value;option.textContent=name+': '+JSON.stringify(value==='target'?target[key]:source[key]);choice.appendChild(option);}
    row.append(caption,choice);dialog.appendChild(row);choices.push([key,choice]);
  }
  const apply=document.createElement('button'),cancel=document.createElement('button');apply.textContent='Merge with chosen properties';cancel.textContent='Cancel';dialog.append(apply,cancel);
  cancel.onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();apply.onclick=async()=>{
    if(revision!==S.revision||generation!==S.generation){dialog.close();toast('The diagram changed. Review the merge again.');return;}
    const data=structuredClone(S.data),a=data.nodes.find(n=>n.id===sourceId),b=data.nodes.find(n=>n.id===targetId);
    for(const [key,choice]of choices){const chosen=choice.value==='source'?a[key]:b[key];a[key]=structuredClone(chosen);b[key]=structuredClone(chosen);}
    const proposal=mergeNodes(data,sourceId,targetId);if(proposal.conflicts.length){toast(proposal.conflicts.join(' '));return;}
    if(await commitTopology(proposal))dialog.close();
  };
  document.body.appendChild(dialog);dialog.showModal();
}

function reviewSelectedMerge(ids,targetId) {
  const base=structuredClone(S.data),generation=S.generation,revision=S.revision;
  const nodes=ids.map(id=>base.nodes.find(n=>n.id===id)),target=nodes.find(n=>n.id===targetId);
  const dialog=document.createElement('dialog');dialog.className='ed-conflict-review';dialog.setAttribute('aria-label','Resolve selected node properties');
  dialog.innerHTML='<h3>Resolve selected node properties</h3><p>Choose meaningful properties for the merged node. Nothing changes until the whole selection validates.</p>';
  const choices=[];
  for(const key of new Set(nodes.flatMap(n=>Object.keys(n)))) {
    if(['id','at'].includes(key))continue;
    const values=[...new Set(nodes.map(n=>n[key]).filter(v=>v!=null&&v!==''&&!(key==='kind'&&v==='free')).map(v=>JSON.stringify(v)))];
    if(values.length<2)continue;
    const row=document.createElement('label'),name=document.createElement('span'),select=document.createElement('select');name.textContent=key;
    for(const value of values){const option=document.createElement('option');option.value=value;option.textContent=value;select.appendChild(option);}
    if(target[key]!=null)select.value=JSON.stringify(target[key]);row.append(name,select);dialog.appendChild(row);choices.push([key,select]);
  }
  const message=document.createElement('p');message.setAttribute('role','alert');dialog.appendChild(message);
  const apply=document.createElement('button'),cancel=document.createElement('button');apply.textContent='Merge with chosen properties';cancel.textContent='Cancel';dialog.append(apply,cancel);
  apply.onclick=async()=>{
    if(generation!==S.generation||revision!==S.revision){message.textContent='The diagram changed. Reopen the merge review.';return;}
    let data=structuredClone(base);
    for(const [key,select]of choices)for(const node of data.nodes.filter(n=>ids.includes(n.id)))node[key]=JSON.parse(select.value);
    for(const id of ids.filter(id=>id!==targetId)) {const p=mergeNodes(data,id,targetId);if(p.conflicts.length){message.textContent=p.conflicts.join(' ');return;}data=p.document;}
    if(await commitTopology({document:data,conflicts:[],selection:{role:'node',index:data.nodes.findIndex(n=>n.id===targetId)}}))dialog.close();
  };
  cancel.onclick=()=>dialog.close();dialog.onclose=()=>dialog.remove();document.body.appendChild(dialog);dialog.showModal();
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
  if(solveOpen) drawPhysicsValues();
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
  const scale = Math.max(w / st.w, h / st.h, S.present ? 0 : 1);
  const vw = st.w * scale, vh = st.h * scale;
  setView({x: (ink[0] + ink[2]) / 2 - vw / 2, y: (ink[1] + ink[3]) / 2 - vh / 2, w: vw, h: vh});
}

// The stage's size settles after the page's first paint and changes with
// the window; until the reader has panned or zoomed, the drawing stays
// fitted through both.
new ResizeObserver(() => { if (!S.touched && !drag) fit(); }).observe($("ed-stage"));

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
const unitsPerPixel = () => {
  const m=canvas.getScreenCTM();
  return m ? 1 / Math.hypot(m.a,m.b) : S.view.w / stageSize().w;
};

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
  const generation = S.generation, revision = S.revision;
  rpc.call("scene", S.data, S.notation, S.physics, null, S.file?.display || {mode:'automatic'}).then((scene) => {
    S.inflight = false;
    if (generation !== S.generation || revision !== S.revision || S.preview) {
      if (!S.preview) refresh(); else clearBusy();
      return;
    }
    if (scene.error) {
      showError(scene.error);
    } else {
      S.scene = scene;
      drawing.innerHTML = scene.parts;
      buildHits(scene.hits);
      if(solveOpen && solveSession && !solveSession.stale) {solveSession.renderKey=null;renderSolveScene();}
      drawPhysicsValues();
      // before the strip reads it: `showFindings` asks which ends are loose
      // before deciding whether to fling itself open
      drawLoose();
      showFindings(scene.findings);
      if(S.sel?.role==="volume" && !pop.hidden) {
        const slot=pop.querySelector('[data-budget]'),budget=scene.budgets.find(b=>b.id===element(S.sel)?.id);
        if(slot) slot.innerHTML=budgetMarkup(budget);
      }
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
      if(S.needsFit) {S.needsFit=false;if(!S.touched) fit();}
    }
    $("ed-empty").hidden = Object.values(COLLECTION).some(k => (S.data[k] || []).length) || tourRunning();
    tourCheck();
    if (S.dirty) refresh(); else clearBusy();
  }).catch((err) => {
    S.inflight = false;
    clearBusy();
    if (generation !== S.generation || revision !== S.revision) { refresh(); return; }
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
  const generation = S.generation, revision = S.revision;
  try {
    const solved = await rpc.call("solve", S.data);
    if (!solved.error && generation === S.generation && revision === S.revision && !S.preview) {
      const coords = new Map(solved.nodes.map(n => [n.id,n.at]));
      for (const n of S.data.nodes) if (!n.at && coords.has(n.id)) n.at = coords.get(n.id);
      save();
      if(solveSession && JSON.stringify(S.data)!==JSON.stringify(solveSession.base)) {solveSession.stale=true;physicsReview=null;analysisPanel();}
    }
  } catch(err) {
    if(generation===S.generation && revision===S.revision) toast("Could not place missing nodes: " + err.message);
  } finally {
    baking = false;
    if ((generation !== S.generation || revision !== S.revision) && !S.preview && S.data.nodes.some(n => !n.at)) bake();
  }
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
    dot.dataset.help='connection';dot.setAttribute('role','button');dot.setAttribute('aria-label','Unconnected endpoint — drag to connect');
    dot.setAttribute("tabindex", "0");
    dot.append(svgEl("title", {}));
    dot.querySelector("title").textContent =
      interactionHelp('connection');
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
  for(const sel of S.selection) if(!sameSel(sel,S.sel)) {
    const box=boundsOf(sel); if(box) ui.appendChild(svgEl("rect",{x:box[0]-3,y:box[1]-3,width:box[2]-box[0]+6,height:box[3]-box[1]+6},"ed-sel"));
  }
  if ((S.sel.role==="region" || S.sel.role==="volume") && el) {
    const [x,y]=el.at,[w,h]=el.size;
    [[x,y],[x+w,y],[x+w,y+h],[x,y+h]].forEach((p,i)=>{
      const c=svgEl("circle",{cx:p[0],cy:p[1],r:7*upp},"ed-via");c.dataset.resize=i;ui.appendChild(c);
    });
    [["left",x,y+h/2],["right",x+w,y+h/2],["top",x+w/2,y],["bottom",x+w/2,y+h]].forEach(([edge,cx,cy])=>{
      const c=svgEl("circle",{cx,cy,r:5*upp},"ed-via");c.dataset.resizeEdge=edge;
      c.style.cursor=edge==="left"||edge==="right"?"ew-resize":"ns-resize";
      const title=svgEl("title",{});title.textContent=`Resize selected rectangles' ${edge==="left"||edge==="right"?"widths":"heights"}`;
      c.appendChild(title);ui.appendChild(c);
    });
  }
  if (S.sel.role === "branch" && el && el.via && el.via.length) {
    el.via.forEach(([x, y], i) => {
      const v = svgEl("rect", {x:x-5*upp,y:y-5*upp,width:10*upp,height:10*upp,rx:1}, "ed-via");
      v.dataset.via = i;
      v.dataset.help='route';const help=svgEl('title',{});help.textContent=interactionHelp('route');v.appendChild(help);
      ui.appendChild(v);
    });
  }
  drawPorts();
}

function drawPorts() {
  const el=element(S.sel),upp=unitsPerPixel();
  if(S.sel?.role==="branch" && el) for(const end of ["from","to"]) {
    const n=nodeById(el[end]);if(!n?.at) continue;
    if(S.loose.some(h=>h.id===n.id)) continue;
    const other=nodeById(el[end==="from"?"to":"from"]);
    const dx=(other?.at?.[0]??n.at[0]+1)-n.at[0],dy=(other?.at?.[1]??n.at[1])-n.at[1],len=Math.hypot(dx,dy)||1;
    const c=svgEl("circle",{cx:n.at[0]+dx/len*18*upp,cy:n.at[1]+dy/len*18*upp,r:5*upp},"ed-via");c.dataset.endpoint=end;ui.appendChild(c);
  }
  if(S.sel?.role==="node" && el?.at) {
    const c=svgEl("circle",{cx:el.at[0]+18*upp,cy:el.at[1],r:5*upp},"ed-via");c.dataset.port=el.id;
    c.appendChild(svgEl("title",{}));c.firstChild.textContent="Click to connect this node";ui.appendChild(c);
  }
}

// -------------------------------------------------------------- findings
const plural = (n, one, many) => `${n} ${n === 1 ? one : many || one + "s"}`;

let currentIssues=[],selectedIssue=null;
function issueNames(f){return (f.targets||[]).map(t=>{const e=S.data[COLLECTION[t.role]]?.[t.index];return t.role==='node'?nodeName(e?.id):e?.label||kindName(t.role,e?.kind||(t.role==='branch'?'cond':'free'));}).join(', ');}
function showFindings(findings) {
  const rank={error:0,warning:1,note:2};
  currentIssues=findings.filter(f=>!['parallel-pair-same-side','physics-not-checked'].includes(f.code)).sort((a,b)=>rank[a.severity]-rank[b.severity]);
  if(selectedIssue&&!currentIssues.some(f=>f.key===selectedIssue))selectedIssue=null;
  const counts={error:0,warning:0,note:0};for(const f of currentIssues)counts[f.severity]++;
  const summary=$('ed-findings-count');summary.replaceChildren();
  for(const [severity,label,icon] of [['error','Errors','⨯'],['warning','Warnings','⚠'],['note','Suggestions','ⓘ']])if(counts[severity]){
    const badge=document.createElement('span');badge.className='ed-count-'+severity;badge.textContent=`${icon} ${label}: ${counts[severity]}`;summary.appendChild(badge);
  }
  const text=document.createElement('span');text.className='ed-first';text.textContent=currentIssues[0]?.title||'No drawing issues';summary.appendChild(text);
  $('ed-findings-toggle').disabled=!currentIssues.length;
  $('ed-all-issues').textContent=`All issues (${currentIssues.length})`;
  $('ed-physics-said').hidden=false;$('ed-physics-said').textContent=!S.physics?'Physics not checked':findings.some(f=>f.code==='physics-not-checked')?'Physics check incomplete':'Physics check complete';
  renderIssues();
}
function renderIssues(){
  const list=$('ed-findings-list');const focus=document.activeElement?.dataset.issueKey;
  list.replaceChildren();
  for(const f of currentIssues){const li=document.createElement('li');li.className='ed-issue';li.dataset.code=f.code;
    const button=document.createElement('button');button.dataset.issueKey=f.key;button.textContent=`${{error:'Error',warning:'Warning',note:'Suggestion'}[f.severity]} — ${f.title}`;
    button.onclick=()=>activateIssue(f);button.setAttribute('aria-expanded',String(selectedIssue===f.key));li.appendChild(button);
    if(selectedIssue===f.key){const detail=document.createElement('div');detail.className='ed-issue-detail';
      const names=issueNames(f);detail.innerHTML=`<p>${escapeHtml(f.explanation||f.title)}</p>${names?`<p>Affected: ${escapeHtml(names)}</p>`:''}<details><summary>Technical details</summary><p>${escapeHtml(f.code)}: ${escapeHtml(f.message)}</p><p>${escapeHtml(f.remedy||'')}</p></details>`;
      const action=document.createElement('button');action.textContent=f.action==='units'?'Open Units':f.targets?.length?'Show affected objects':'About this issue';action.onclick=()=>pointAt(f);detail.prepend(action);li.appendChild(detail);}
    list.appendChild(li);
  }
  if(focus)list.querySelector(`[data-issue-key="${CSS.escape(focus)}"]`)?.focus({preventScroll:true});
}
function activateIssue(f){if(groupDraft){gateGroup(()=>activateIssue(f));return;}selectedIssue=f.key;delete $('ed-findings-toggle').dataset.closed;openFindings(true);pointAt(f);renderIssues();}

function openFindings(on) {
  const l = $("ed-findings-list"), t = $("ed-findings-toggle");
  if (on && !t.dataset.closed) l.hidden = false;
  else if (!on) l.hidden = true;
  t.setAttribute("aria-expanded", String(!l.hidden));
  t.querySelector(".ed-findings-more").textContent = l.hidden ? "▾" : "▴";
}

function pointAt(f) {
  if(groupDraft){gateGroup(()=>pointAt(f));return;}
  if(f.targets?.length){
    const drawerOpen=!$('ed-findings-list').hidden;
    if(!sameSel(S.sel,f.targets[0])||S.selection.length!==f.targets.length)inspectorTab='Properties';
    S.selection=f.targets;S.sel=f.targets[0];drawSelection();updateChrome();
    if(pop.classList.contains('ed-docked')){
      const view=panelView,collapsed=document.body.classList.contains('ed-components-collapsed'),opened=document.body.classList.contains('ed-components-open');
      openPopover(S.sel);setPanelView(view,true);
      document.body.classList.toggle('ed-components-collapsed',collapsed);document.body.classList.toggle('ed-components-open',opened);
    }
    openFindings(drawerOpen);
  }
  else if(f.action==='units'){$('ed-settings').click();return;}
  else if(f.action==='explain'&&!f.at){toast(f.message+' '+f.remedy);return;}
  const bounds=(f.targets||[]).map(boundsOf).filter(Boolean);
  if(bounds.length){
    const left=Math.min(...bounds.map(b=>b[0]))-24,top=Math.min(...bounds.map(b=>b[1]))-24;
    const right=Math.max(...bounds.map(b=>b[2]))+24,bottom=Math.max(...bounds.map(b=>b[3]))+24;
    const factor=Math.max(1,(right-left)/S.view.w,(bottom-top)/S.view.h),w=S.view.w*factor,h=S.view.h*factor;
    setView({x:(left+right-w)/2,y:(top+bottom-h)/2,w,h});
  } else if (f.at) {
    const v = S.view;
    setView({x: f.at[0] - v.w / 2, y: f.at[1] - v.h / 2, w: v.w, h: v.h});
  }
  drawHover(null);
  for(const target of f.targets||[])drawHover(target,true);
  if(!f.targets?.length)for(const r of hitsG.children)if(r.dataset.ref===f.where){select({role:r.dataset.role,index:+r.dataset.index},false);drawHover({role:r.dataset.role,index:+r.dataset.index},true);}
  const highlights=[...ui.querySelectorAll('.ed-hover-ink')];setTimeout(()=>highlights.forEach(e=>e.remove()),1600);
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
let drag = null, cardDrag = null;  // canvas transaction or palette gesture
let touchQuickUntil=0;
const pointers = new Map();
let pinch = null;
let lastTap = null;   // {sel, t, x, y} for a double-tap on touch
let lastPointer = {x: 0, y: 0};   // where a card with nothing to sit beside goes

// A gesture owns a disposable model. The saved model changes only on release.
let previewFrame = null, previewGroups = null, lastGestureMove = -Infinity;
function cancelGesture() {
  clearDropHint();
  if(drag?.holdTimer) clearTimeout(drag.holdTimer);
  if(cardDrag?.ghost) cardDrag.ghost.remove();
  cardDrag=null;
  if (previewFrame != null) cancelAnimationFrame(previewFrame);
  previewFrame = null;
  previewGroups = null;
  const hadPreview = !!S.preview;
  S.preview = null; drag = null; freeDrag = false;
  clearGuides();clearGhost();clearTargets();
  ui.querySelectorAll(".ed-rubber").forEach(n=>n.remove());
  canvas.classList.remove("ed-pan");
  if (typeof ui !== "undefined") ui.querySelectorAll(".ed-marquee,.ed-shape-preview").forEach(n=>n.remove());
  if (hadPreview && S.scene) drawing.innerHTML = S.scene.parts;
  if (hadPreview && S.sel) drawSelection();
}

function mutatePreview(fn) {
  if(!S.preview) previewGroups=null;
  const committed = S.data;
  S.data = JSON.parse(drag.snapshot);
  try { fn(); S.preview = S.data; } finally { S.data = committed; }
}

const sameSel = (a,b) => a && b && a.role === b.role && a.index === b.index;
function toggleSelection(hit) {
  if(groupDraft){gateGroup(()=>toggleSelection(hit));return;}
  const sel = {role:hit.role,index:hit.index};
  if (!S.selection.length && S.sel) S.selection = [S.sel];
  const found = S.selection.findIndex(s=>sameSel(s,sel));
  if (found >= 0) S.selection.splice(found,1); else S.selection.push(sel);
  S.sel = S.selection.at(-1) || null; closePopover(); drawSelection(); updateChrome();
}

function movementSelection(sel, label) {
  if (label) return [sel];
  if (S.selection.length > 1 && S.selection.some(s=>sameSel(s,sel))) return [...S.selection];
  const out = [sel];
  if (sel.role === "branch") {
    const b = element(sel);
    const ends = [b.from,b.to];
    const isolated = ends.every(id => id !== "rail" && !S.data.branches.some((p,i)=>i!==sel.index && (p.from===id || p.to===id))
      && !S.data.sources.some(s=>(s.to||s.from)===id) && !(S.data.rail && S.data.rail.reference===id));
    if (isolated) for (const id of ends) out.push({role:"node",index:S.data.nodes.findIndex(n=>n.id===id)});
  }
  return out;
}

function moveGroup(group, dx, dy) {
  const movedVolumes = new Set();
  const nodes = new Set(group.filter(s=>s.role==="node").map(s=>element(s).id));
  const shift = p => [p[0]+dx,p[1]+dy];
  for (const sel of group) {
    const el = element(sel);
    if (sel.role === "surface") continue;
    if (el.at) el.at = shift(el.at);
    else if (sel.role === "node" || sel.role === "source") {
      const h = S.scene.hits.find(h=>h.role===sel.role && h.index===sel.index && h.element!=="label");
      if (h) el.at = shift(h.at);
    }
    if (el.end && Array.isArray(el.end)) el.end = shift(el.end);
    if (sel.role === "region") for (const v of list("volume")) {
      if ((v.regions||[]).includes(el.id) && !movedVolumes.has(v.id) && !group.some(s=>s.role==="volume" && element(s)===v)) {v.at=shift(v.at);movedVolumes.add(v.id);}
    }
  }
  for (let i=0;i<S.data.branches.length;i++) {
    const b=S.data.branches[i];
    if (nodes.has(b.from) && nodes.has(b.to)) {
      if (b.via) b.via=b.via.map(shift);
      if (b.at && !group.some(s=>s.role==="branch" && s.index===i)) b.at=shift(b.at);
    }
  }
  for (let i=0;i<S.data.sources.length;i++) {
    const s=S.data.sources[i];
    if (nodes.has(s.to||s.from) && s.at && !group.some(p=>p.role==="source" && p.index===i)) s.at=shift(s.at);
  }
}

function drawMarquee(a,b) {
  ui.querySelectorAll(".ed-marquee").forEach(n=>n.remove());
  ui.appendChild(svgEl("rect",{x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),width:Math.abs(a.x-b.x),height:Math.abs(a.y-b.y)},"ed-sel ed-marquee"));
}
function finishMarquee(a,b) {
  const x0=Math.min(a.x,b.x),x1=Math.max(a.x,b.x),y0=Math.min(a.y,b.y),y1=Math.max(a.y,b.y);
  S.selection=[];
  for (const h of S.scene?.hits || []) {
    if (h.element==="label" || h.element==="wire") continue;
    const [x,y,xx,yy]=h.bounds;
    if (x>=x0 && xx<=x1 && y>=y0 && yy<=y1 && !S.selection.some(s=>sameSel(s,h))) S.selection.push({role:h.role,index:h.index});
  }
  ui.querySelectorAll(".ed-marquee").forEach(n=>n.remove());
  S.sel=S.selection.at(-1)||null; closePopover(); drawSelection(); updateChrome();
}

function physicalPoints(role, el, data) {
  if (role==="annotation") return [el.at,el.end||el.at];
  const s=role==="surface" ? el : (data.control_surfaces||[]).find(s=>s.id===el.surface);
  const v=s && (data.control_volumes||[]).find(v=>v.id===s.volume);
  let points,normal=[1,0];
  if (v) {
    const [x,y]=v.at,[w,h]=v.size,a=s.start??.25,b=s.end??.75;
    if (s.edge==="top" || s.edge==="bottom") {
      const yy=y+(s.edge==="bottom"?h:0); points=[[x+w*a,yy],[x+w*b,yy]]; normal=[0,s.edge==="bottom"?1:-1];
    } else {
      const xx=x+(s.edge==="right"?w:0); points=[[xx,y+h*a],[xx,y+h*b]]; normal=[s.edge==="right"?1:-1,0];
    }
  } else points=[el.at||[0,0],el.at||[0,0]];
  if (role==="surface") return points;
  const c=points[0].map((n,i)=>(n+points[1][i])/2),len=el.length||80;
  points=[c.map((n,i)=>n-normal[i]*len/2),c.map((n,i)=>n+normal[i]*len/2)];
  return el.direction==="in"?points.reverse():points;
}

function schedulePreview() {
  if (previewFrame != null) return;
  previewFrame=requestAnimationFrame(()=>{previewFrame=null; paintPreview();});
}
function paintPreview() {
  if (!S.preview || !S.scene) return;
  const before=S.data,after=S.preview;
  const deltaNode=id=>{
    const a=before.nodes.find(n=>n.id===id)?.at,b=after.nodes.find(n=>n.id===id)?.at;
    return a&&b?[b[0]-a[0],b[1]-a[1]]:[0,0];
  };
  // Route vertices are document geometry; symbol sizes and SVG remain Python-owned.
  const frames=new Map();
  after.branches.forEach((b,i)=>{
    if(b.count>1 || JSON.stringify(b)===JSON.stringify(before.branches[i]) &&
       deltaNode(b.from).every(n=>!n) && deltaNode(b.to).every(n=>!n)) return;
    const ends=[b.from,b.to].map(id=>after.nodes.find(n=>n.id===id)?.at);
    const hit=S.scene.hits.find(h=>h.role==="branch" && h.index===i && h.element==="symbol");
    if(!ends.every(Boolean) || !hit) return;
    const route=[ends[0],...(b.via||[]),ends[1]];
    let centre=b.at;
    if(!centre) {
      let longest=0;
      for(let j=1;j<route.length-1;j++) if(Math.hypot(...route[j+1].map((n,k)=>n-route[j][k]))>
        Math.hypot(...route[longest+1].map((n,k)=>n-route[longest][k]))) longest=j;
      centre=route[longest].map((n,k)=>(n+route[longest+1][k])/2);
    }
    const seg=nearestSegment(route,centre),half=hit.half_len;
    const left=centre.map((n,k)=>n-seg.u[k]*half),right=centre.map((n,k)=>n+seg.u[k]*half);
    frames.set(i,{centre,angle:b.angle??bearing([0,0],seg.u),
      runs:[[...route.slice(0,seg.i+1),left],[right,...route.slice(seg.i+1)]],wired:false});
  });
  if(!previewGroups) {
    drawing.innerHTML="";
    previewGroups=(S.scene.preview||[]).map(p=>{
      const g=svgEl("g",{});g.innerHTML=p.markup;drawing.appendChild(g);
      for(const line of g.querySelectorAll("polyline")) line.dataset.originalPoints=line.getAttribute("points");
      return g;
    });
  }
  for (const [index,p] of (S.scene.preview || []).entries()) {
    const a=before[COLLECTION[p.role]]?.[p.index], b=after[COLLECTION[p.role]]?.[p.index];
    const g=previewGroups[index];
    if (!a || !b) continue;
    let d=[0,0];
    const frame=p.role==="branch"?frames.get(p.index):null;
    if (p.role==="surface" || p.role==="transfer") {
      const old=physicalPoints(p.role,a,before),now=physicalPoints(p.role,b,after);
      d=old[0].map((n,i)=>(now[0][i]+now[1][i]-n-old[1][i])/2);
    } else if (a.at && b.at) d=[b.at[0]-a.at[0],b.at[1]-a.at[1]];
    else if (p.role==="node" && b.at) d=[b.at[0]-p.at[0],b.at[1]-p.at[1]];
    else if (p.role==="source") d=b.at?[b.at[0]-p.at[0],b.at[1]-p.at[1]]:deltaNode(b.to||b.from);
    else if (p.role==="branch") {
      const da=deltaNode(b.from),db=deltaNode(b.to);
      d=b.at?[b.at[0]-p.at[0],b.at[1]-p.at[1]]:da.map((n,i)=>(n+db[i])/2);
    } else if (p.role==="surface" || p.role==="transfer") {
      const old=physicalPoints(p.role,a,before),now=physicalPoints(p.role,b,after);
      d=old[0].map((n,i)=>(now[0][i]+now[1][i]-n-old[1][i])/2);
    }
    if(frame && p.element!=="wire") d=frame.centre.map((n,i)=>n-p.at[i]);
    if(frame && p.element==="wire") {
      g.replaceChildren();
      g.dataset.routed="1";
      if(!frame.wired) for(const run of frame.runs) {
        const line=svgEl("polyline",{points:run.map(p=>p.join(",")).join(" ")},"w");
        g.appendChild(line);
      }
      frame.wired=true;
    } else if (p.element==="label") {
      if (drag?.label && sameSel(p,drag.sel)) {
        const old=a.label_offset || [drag.labelOrig[0]-drag.orig[0],drag.labelOrig[1]-drag.orig[1]];
        d=b.label_offset.map((n,i)=>n-old[i]);
      }
      g.setAttribute("transform",`translate(${d})`);
    } else if (p.element==="region" || p.element==="volume") {
      const r=g.querySelector("rect");
      if(r) for(const [k,v] of Object.entries({x:b.at[0],y:b.at[1],width:b.size[0],height:b.size[1]})) r.setAttribute(k,v);
    } else if(p.element==="surface") {
      const line=g.querySelector("polyline");if(line) line.setAttribute("points",physicalPoints("surface",b,after).map(p=>p.join(",")).join(" "));
    } else if (p.element==="wire") {
      if(g.dataset.routed) {
        g.innerHTML=p.markup;delete g.dataset.routed;
        for(const line of g.querySelectorAll("polyline")) line.dataset.originalPoints=line.getAttribute("points");
      }
      const da=p.role==="branch"?deltaNode(b.from):d,db=p.role==="branch"?deltaNode(b.to):d;
      for(const line of g.querySelectorAll("polyline")) {
        const points=line.dataset.originalPoints.trim().split(/\s+/).map(s=>s.split(",").map(Number));
        const aa=before.nodes.find(n=>n.id===b.from)?.at,bb=before.nodes.find(n=>n.id===b.to)?.at;
        line.setAttribute("points",points.map((pt,j)=>{
          const shift=p.role==="source" && j===0?deltaNode(b.to||b.from):aa&&Math.hypot(pt[0]-aa[0],pt[1]-aa[1])<1?da:bb&&Math.hypot(pt[0]-bb[0],pt[1]-bb[1])<1?db:d;
          return pt.map((n,i)=>n+shift[i]).join(",");
        }).join(" "));
      }
    } else g.setAttribute("transform",`translate(${d})${frame?` rotate(${frame.angle-p.angle} ${p.at[0]} ${p.at[1]})`:""}`);
  }
  if(drag?.kind==="resize") {
    const r=after[COLLECTION[drag.sel.role]][drag.sel.index],[x,y]=r.at,[w,h]=r.size;
    const corners=[[x,y],[x+w,y],[x+w,y+h],[x,y+h]];
    const edges={left:[x,y+h/2],right:[x+w,y+h/2],top:[x+w/2,y],bottom:[x+w/2,y+h]};
    ui.querySelectorAll('[data-resize],[data-resize-edge]').forEach(handle=>{
      const p=handle.dataset.resizeEdge?edges[handle.dataset.resizeEdge]:corners[+handle.dataset.resize];
      handle.setAttribute("cx",p[0]);handle.setAttribute("cy",p[1]);
    });
  }
}

function nodeTarget(p) {
  const reach=12*unitsPerPixel();
  const n=S.data.nodes.find(n=>n.at && Math.hypot(n.at[0]-p.x,n.at[1]-p.y)<=reach);
  return n?.id || null;
}
function attachEndpoint(sel,end,id) {
  const b=element(sel);if(!b || b[end==="from"?"to":"from"]===id) {toast("A path needs two different nodes.");return;}
  edit(()=>{b[end]=id;delete b.at;delete b.via;});
}

// Physical tools share the existing popover, menu, hit map and selection UI.
let shapeStart=null;
function physicalId(role) {
  const used=new Set(Object.keys(COLLECTION).flatMap(r=>list(r).map(e=>e.id)));
  for(let i=1;;i++) if(!used.has(`${role}${i}`)) return `${role}${i}`;
}
function addPhysical(role,props) {
  edit(d=>{ (d[COLLECTION[role]] ||= []).push({id:physicalId(role),...props}); });
  setMode("idle");shapeStart=null;
  select({role,index:list(role).length-1},true,true);
}
function startPhysicalGesture(e,p) {
  const resize=e.target.dataset?.resize,edge=e.target.dataset?.resizeEdge;
  if((resize!==undefined || edge) && S.sel && S.mode!=="sketch") {
    const group=(S.selection.length?S.selection:[S.sel]).filter(s=>s.role==="region" || s.role==="volume");
    drag={kind:"resize",sel:S.sel,corner:resize===undefined?null:+resize,edge,group,start:p,snapshot:snapshot(),moved:false};return true;
  }
  if(S.mode!=="sketch") return false;
  const role=S.pending.role,kind=S.pending.kind;
  if(role==="surface") {
    const h=hitAt(e.target), selected=h?.role==="volume"?h:S.sel;
    const v=selected?.role==="volume"?element(selected):null;
    if(!v) {toast("Click the edge of a control volume.");return true;}
    const [x,y]=v.at,[w,hg]=v.size;
    const edges=[["left",Math.abs(p.x-x)],["right",Math.abs(p.x-x-w)],["top",Math.abs(p.y-y)],["bottom",Math.abs(p.y-y-hg)]];
    const edge=edges.sort((a,b)=>a[1]-b[1])[0][0];
    addPhysical(role,{volume:v.id,edge,start:.25,end:.75});return true;
  }
  if(role==="transfer") {
    const h=hitAt(e.target), selected=h?.role==="surface"?h:S.sel;
    addPhysical(role,{kind:"heat",...(selected?.role==="surface"?{surface:element(selected).id}:{at:[p.x,p.y]})});return true;
  }
  if(role==="annotation" && kind==="text") {addPhysical(role,{at:[p.x,p.y],kind,label:"Text"});return true;}
  drag={kind:"shape",role,shapeKind:kind,start:shapeStart||p,moved:!!shapeStart,snapshot:snapshot()};
  return true;
}
function movePhysicalGesture(p,dx,dy) {
  if(drag.kind==="shape") {
    ui.querySelectorAll(".ed-shape-preview").forEach(n=>n.remove());
    const a=drag.start;
    const attrs=drag.role==="annotation"?{x1:a.x,y1:a.y,x2:p.x,y2:p.y}:{x:Math.min(a.x,p.x),y:Math.min(a.y,p.y),width:Math.abs(a.x-p.x),height:Math.abs(a.y-p.y)};
    ui.appendChild(svgEl(drag.role==="annotation"?"line":"rect",attrs,"ed-sel ed-shape-preview"));return true;
  }
  if(drag.kind==="resize") {
    mutatePreview(()=>{
      if(drag.edge || drag.group.length>1) {
        const rects=drag.group.map(element);
        const left=drag.edge==="left" || drag.corner===0 || drag.corner===3;
        const top=drag.edge==="top" || drag.corner===0 || drag.corner===1;
        const changeWidth=!drag.edge || drag.edge==="left" || drag.edge==="right";
        const changeHeight=!drag.edge || drag.edge==="top" || drag.edge==="bottom";
        // A common delta preserves differing sizes. Clamp the entire group at
        // the smallest rectangle so every selected edge moves together.
        const dw=changeWidth?Math.max(snap(dx)*(left?-1:1),10-Math.min(...rects.map(r=>r.size[0]))):0;
        const dh=changeHeight?Math.max(snap(dy)*(top?-1:1),10-Math.min(...rects.map(r=>r.size[1]))):0;
        for(const r of rects) {
          r.at=[r.at[0]-(left?dw:0),r.at[1]-(top?dh:0)];
          r.size=[r.size[0]+dw,r.size[1]+dh];
        }
        return;
      }
      const el=element(drag.sel),[x,y]=el.at,[w,h]=el.size;
      const opposite=[[x+w,y+h],[x,y+h],[x,y],[x+w,y]][drag.corner];
      el.at=[Math.min(opposite[0],snap(p.x)),Math.min(opposite[1],snap(p.y))];
      el.size=[Math.max(10,Math.abs(opposite[0]-snap(p.x))),Math.max(10,Math.abs(opposite[1]-snap(p.y)))];
    });schedulePreview();return true;
  }
  return false;
}
function finishPhysicalGesture(d,p) {
  if(d.kind==="resize") {
    if(S.preview) {S.data=S.preview;S.preview=null;S.undo.push(d.snapshot);S.redo=[];afterEdit();}return true;
  }
  if(d.kind!=="shape") return false;
  ui.querySelectorAll(".ed-shape-preview").forEach(n=>n.remove());
  if(!d.moved) {shapeStart=d.start;toast("Click the opposite corner, or drag to draw.");return true;}
  const a=d.start;
  if(d.role==="annotation") addPhysical(d.role,{at:[a.x,a.y],end:[p.x,p.y],kind:d.shapeKind});
  else {
    const at=[snap(Math.min(a.x,p.x)),snap(Math.min(a.y,p.y))];
    const size=[Math.max(10,snap(Math.abs(a.x-p.x))),Math.max(10,snap(Math.abs(a.y-p.y)))];
    addPhysical(d.role,{at,size});
  }
  return true;
}

function budgetMarkup(b) {
  if(!b) return "Checking supplied terms…";
  return `<p data-budget-status="${b.status}">${escapeHtml(b.status)}: ${b.incoming} W in − ${b.outgoing} W out + ${b.generation??"?"} W generated − ${b.storage??"?"} W stored${b.residual==null?"":` = ${b.residual.toPrecision(4)} W`}</p>${b.missing?.length?`<p>${escapeHtml(b.missing.join("; "))}</p>`:""}`;
}
function openPhysicalPopover(sel) {
  const el=element(sel);
  const input=(name,value,type="text")=>`<input data-physical="${name}" type="${type}" value="${escapeHtml(value??"")}" ${type==="number"?'step="any"':''}>`;
  const options=(name,value,values)=>`<select data-physical="${name}">${values.map(v=>`<option value="${escapeHtml(v)}" ${v===value?'selected':''}>${escapeHtml(v ? ([...list("volume"),...list("surface")].find(o=>o.id===v)?.label ? [...list("volume"),...list("surface")].find(o=>o.id===v).label+" ("+v+")" : v) : "Unattached")}</option>`).join("")}</select>`;
  let h=`<h4>${escapeHtml({region:"Region",volume:"Control volume",surface:"Control surface",transfer:"Energy transfer",annotation:"Annotation"}[sel.role])} <code>${escapeHtml(el.id)}</code></h4>`;
  h+=field("Label",input("label",el.label));
  if(sel.role==="region" || sel.role==="volume") {
    h+=field("Drawing width",input("width",el.size[0],"number"))+field("Drawing height",input("height",el.size[1],"number"));
  }
  if(sel.role==="volume") {
    h+=relationshipPicker("Included regions","regions",list("region").map(o=>({value:o.id,label:o.label||o.id})),el.regions||[]);
    h+=field("Rate unit",options("unit",el.unit||"W",["W","kW","mW"]));
    h+=field("Generation",input("generation",el.generation));
    if(!el.steady) h+=field("Storage (+ accumulates)",input("storage",el.storage));
    h+=field("Steady state",`<input type="checkbox" data-physical="steady" ${el.steady?'checked':''}>`);
    if(el.incomplete) h+=`<p>Boundary terms were removed. Review the balance.</p><button data-review-budget>Reviewed boundary terms</button>`;
    const b=S.scene?.budgets?.find(b=>b.id===el.id);
    h+=`<div data-budget>${budgetMarkup(b)}</div>`;
  }
  if(sel.role==="surface") {
    h+=field("Volume",options("volume",el.volume,list("volume").map(v=>v.id)));
    h+=field("Edge (normal points outward)",options("edge",el.edge||"right",["left","right","top","bottom"]));
    h+=field("Start fraction",input("start",el.start??.25,"number"))+field("End fraction",input("end",el.end??.75,"number"));
    h+=field("Physical area",input("area",el.area))+field("Area unit",options("area_unit",el.area_unit||"m²",["m²","cm²","mm²"]));
  }
  if(sel.role==="transfer") {
    h+=field("Surface",options("surface",el.surface||"",["",...list("surface").map(s=>s.id)]));
    h+=field("Kind",options("kind",el.kind||"heat",["heat","work","mass"]));
    h+=field("Direction",options("direction",el.direction||"out",["in","out"]));
    if(!el.kind || el.kind==="heat") h+=field("Supply as",`<select data-transfer-input><option value="rate" ${el.flux==null?'selected':''}>Energy rate</option><option value="flux" ${el.flux!=null?'selected':''}>Heat flux × surface area</option></select>`);
    if(el.flux!=null) h+=field("Heat flux",input("flux",el.flux))+field("Flux unit",options("flux_unit",el.flux_unit||"W/m²",["W/m²","W/cm²","kW/m²"]))+'<p>Requires an explicit physical area on the surface.</p>';
    else h+=field("Energy rate",input("rate",el.rate))+field("Rate unit",options("unit",el.unit||"W",["W","kW","mW"]));
    h+=field("Arrow length",input("length",el.length||80,"number"));
  }
  if(sel.role==="annotation") h+=field("Kind",options("kind",el.kind||"text",["text","line","arrow"]));
  h+='<details><summary>Descriptive associations</summary><p>Associations do not add balance terms.</p>';
  h+=relationshipPicker("Network objects","links",["node","branch","source"].flatMap(role=>list(role).map((o,index)=>({value:o.id?role+":"+o.id:role+":@"+index,label:o.label||o.id||role+" "+(index+1)}))),el.links||[])+ '</details>';
  h+=`<p class="ed-hint">Label position: ${el.label_offset?'Manual':'Automatic'}</p><div class="ed-row"><button data-act="auto-label">Auto position label</button><button data-act="delete" class="ed-danger">Delete</button></div>`;
  h += `<button type="button" data-assignment-open>Physics and document options…</button>`;
  pop.innerHTML=h;pop.hidden=false;placePopover(sel);
}

function hitAt(target) {
  const r = target && target.closest ? target.closest("#ed-hits rect") : null;
  return r ? {role: r.dataset.role, index: +r.dataset.index, element: r.dataset.element, rect: r} : null;
}

canvas.addEventListener("pointerdown", (e) => {
  if (S.present || e.button !== 0) return;
  if(groupDraft){e.preventDefault();const hit=hitAt(e.target);if(hit&&!sameSel(hit,groupDraft.sel))gateGroup(()=>select(hit));return;}
  lastPointer = {x: e.clientX, y: e.clientY};
  pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()];
    pinch = {d: Math.hypot(a.x - b.x, a.y - b.y), view: {...S.view}};
    cancelGesture();
    return;
  }
  closeQuick(); closeMenu();
  canvas.setPointerCapture(e.pointerId);
  const p = toPage(e.clientX, e.clientY);
  freeDrag = e.altKey;
  lastAlign = {x:null,y:null};
  if (startPhysicalGesture(e, p)) return;
  if(e.target.dataset?.port) { startConnect(e.target.dataset.port,"link"); return; }
  if(e.target.dataset?.endpoint && S.sel) {
    drag={kind:"endpoint",sel:S.sel,end:e.target.dataset.endpoint,start:p,moved:false};
    markEndpointTargets(drag);return;
  }
  if(S.mode==="endpoint") {
    const target=nodeTarget(p),pending=S.pending;
    setMode("idle");if(target) attachEndpoint(pending.sel,pending.end,target);return;
  }
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
    if (e.shiftKey) { toggleSelection(hit); return; }
    const movable = true;
    const labelHit = hit.element === "label";
    drag = {kind: "element", hit, sel: {role: hit.role, index: hit.index}, start: p, moved: false, movable,
            orig: currentAt(hit), snapshot: snapshot(), label: labelHit};
    if (labelHit) {
      const rect = hit.rect;
      drag.labelOrig = [+rect.getAttribute("x") + 2, +rect.getAttribute("y") + 2];
    }
    drag.group = movementSelection(drag.sel, labelHit);
    return;
  }
  if (e.shiftKey) { drag = {kind:"marquee",start:p,moved:false}; return; }
  const lead=resistanceLead(p);
  if(lead && lead.distance<=6*unitsPerPixel()) {
    const sel={role:'branch',index:lead.index};
    drag={kind:'route',sel,start:p,lead,moved:false,snapshot:snapshot(),centre:symbolHit(sel)?.at};
    return;
  }
  drag = {kind: "pan", start: {x: e.clientX, y: e.clientY}, view: {...S.view}, moved: false};
  canvas.classList.add("ed-pan");
  if(e.pointerType==="touch") {
    const held=drag;
    held.holdTimer=setTimeout(()=>{
      if(drag===held && !held.moved && pointers.size===1) {
        requestQuick(e.clientX,e.clientY);touchQuickUntil=performance.now()+1000;
      }
    },500);
  }
});

function currentAt(hit) {
  const el = element(hit);
  if (el.at) return [...el.at];
  // placed by the library, not the file: start from where it is drawn
  return hit.rect ? hit.rect.dataset.at.split(",").map(Number) : [0,0];
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
  // Move the lane carrying the symbol, retaining its perpendicular risers.
  // In particular, do not replace a parallel lane with a short bracket near
  // the body: joining that bracket to distant junctions creates diagonals.
  const original = routeOf(el), hit = symbolHit(sel);
  if(original){
    const lane=nearestSegment(original,hit?.at||el.at||p);
    const axis=Math.abs(lane.u[0])>0.999999?0:Math.abs(lane.u[1])>0.999999?1:null;
    if(axis!==null){
      const normal=1-axis,a=original[lane.i],b=original[lane.i+1];
      const clearance=(hit?.terminal_half??hit?.half_len??62)+DETOUR_PAD;
      const threshold=(drag?.detouring?28:OFF_RUN_PX)*unitsPerPixel();
      const off=Math.abs(p[normal]-a[normal]);
      if(drag)drag.detouring=off>threshold;
      const low=Math.min(a[axis],b[axis]),high=Math.max(a[axis],b[axis]);
      const along=high-low>=2*clearance?clamp(snap(p[axis]),low+clearance,high-clearance):(low+high)/2;
      const c=[0,0];c[axis]=along;c[normal]=off>threshold?snap(p[normal]):a[normal];
      if(off>threshold && high-low>=2*clearance){
        const first=[...a],last=[...b];first[normal]=last[normal]=c[normal];
        const before=original.slice(0,lane.i+1),after=original.slice(lane.i+1);
        if(lane.i>0 && Math.abs(original[lane.i-1][axis]-a[axis])<0.001)before[before.length-1]=first;
        else before.push(first);
        if(lane.i+2<original.length && Math.abs(original[lane.i+2][axis]-b[axis])<0.001)after[0]=last;
        else after.unshift(last);
        el.via=before.concat(after).slice(1,-1);
      }else c[normal]=a[normal];
      el.at=c;
      return off<=threshold || high-low>=2*clearance;
    }
  }
  dropBracket(el);
  const route = routeOf(el);
  if (!route) { el.at = [snap(p[0]), snap(p[1])]; return true; }
  const seg = nearestSegment(route, p);
  const d = (hit?.terminal_half ?? hit?.half_len ?? 62) + DETOUR_PAD;
  const offRun = (drag && drag.detouring ? 28 : OFF_RUN_PX) * unitsPerPixel();
  if (drag) drag.detouring = Math.abs(seg.off) > offRun;
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
  if(!["node","branch","source"].includes(sel.role)) {toast("Regions stay rectangular. Use the edge and direction controls for physical arrows.");return;}
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

function turnBranch(sel, el, dir, targetAngle=null) {
  const ends = [el.from, el.to];
  const nodes = ends.map(nodeById);
  const alone = (id) => S.data.branches.filter(
    (b) => b.from === id || b.to === id).length === 1;
  const swing = ends.map((id, i) => !!(nodes[i]?.at && unsaid(nodes[i]) && alone(id)
    && !S.data.sources.some(s=>s.from===id||s.to===id) && S.data.rail?.reference!==id));

  if ((swing[0] || swing[1]) && !routedByHand(el)) {
    const [a, c] = [nodes[0].at, nodes[1].at];
    const len = snap(Math.hypot(c[0] - a[0], c[1] - a[1])) || PITCH;
    const rad = (targetAngle ?? quarter(bearing(a, c), dir)) * Math.PI / 180;
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

  if (['flow','stream'].includes(el.kind)) {toast('Use Reverse direction for this directional component.');return;}
  const hit=symbolHit(sel),next=targetAngle ?? quarter(el.angle ?? hit?.angle ?? 0,dir);
  let proposal=mutationProposal(()=>{const b=element(sel);b.angle=((next%360)+360)%360;if(!b.at && hit)b.at=[...hit.at];});
  const route=routeOf(el);
  if(route && hit) {
    const segment=nearestSegment(route,hit.at).i,a=route[segment],b=route[segment+1];
    const relative=(next-bearing(a,b))*Math.PI/180;
    const count=Math.min(el.count||1,3),reach=(hit.terminal_half||62)*(el.arrangement==='series'?count:1);
    const half=Math.abs(Math.sin(relative))*reach+Math.abs(Math.cos(relative))*16+30;
    const expanded=clearGroupLanes(proposal.document,sel.index,segment,half);
    if(!expanded.error)proposal.document=expanded.document;
  }
  commitTopology(proposal,sel).then(ok=>{if(ok&&!pop.hidden)openPopover(sel);});
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
  const moving=drag?.sel?.role==='node'?element(drag.sel)?.id:null;
  const target=S.data.nodes.find(n=>n.id!==moving&&n.at?.every((v,i)=>v===at[i]));
  if(target) {
    ui.appendChild(svgEl('circle',{cx:at[0],cy:at[1],r:14*unitsPerPixel(),fill:'none'},'ed-guide'));
    const label=svgEl('text',{x:at[0]+18*unitsPerPixel(),y:at[1]-18*unitsPerPixel(),'font-size':13*unitsPerPixel(),fill:'var(--accent)'},'ed-guide');
    label.textContent='Merge into '+nodeName(target.id);ui.appendChild(label);
  }
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
  lastPointer={x:e.clientX,y:e.clientY};
  if(drag?.holdTimer && Math.hypot(e.clientX-drag.start.x,e.clientY-drag.start.y)>=4) {
    clearTimeout(drag.holdTimer);delete drag.holdTimer;
  }
  freeDrag = e.altKey;
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
  if (!drag.moved && Math.hypot(dx, dy) / unitsPerPixel() < 4) return;
  drag.moved = true;
  drawHover(null);
  S.touched = true;
  lastGestureMove = performance.now();
  if (movePhysicalGesture(p, dx, dy)) return;
  if (drag.kind === "marquee") { drawMarquee(drag.start,p); return; }
  if(drag.kind==="endpoint") {rubber(drag.start,p);hover(document.elementFromPoint(e.clientX,e.clientY));return;}
  if (drag.kind === "pan") {
    S.touched = true;
    const upp = unitsPerPixel();
    setView({...drag.view, x: drag.view.x - (e.clientX - drag.start.x) * upp, y: drag.view.y - (e.clientY - drag.start.y) * upp});
  } else if (drag.kind === "element" && drag.movable) {
    mutatePreview(() => {
      const el = element(drag.sel);
      if (drag.label) {
        el.label_offset = [snap(drag.labelOrig[0] + dx) - drag.orig[0], snap(drag.labelOrig[1] + dy) - drag.orig[1]];
      } else if (drag.group.length > 1) {
        moveGroup(drag.group, snap(dx), snap(dy));
      } else if (drag.sel.role === "branch") {
        drag.routed = placeBranchSymbol(drag.sel, [drag.orig[0] + dx,drag.orig[1] + dy]);
      } else {
        const q = alignedSnap(drag.orig[0] + dx, drag.orig[1] + dy, el.id);
        moveGroup(drag.group, q[0]-drag.orig[0],q[1]-drag.orig[1]);
        drawGuides(q);
      }
    });
    if(!drag.label && drag.sel.role==='branch' && drag.group.length===1) {
      const proposal=movedResistanceProposal(drag.sel,p);
      if(proposal && !proposal.conflicts.length) {previewResistanceDrop(null,p,drag,proposal);return;}
      clearDropHint();dropPreviewSequence++;
    }
    schedulePreview();
  } else if (drag.kind === 'route') {
    mutatePreview(()=>{
      const b=element(drag.sel);b.via||=[];
      b.via.splice(drag.lead.i,0,[snap(drag.lead.at[0]+dx),snap(drag.lead.at[1]+dy)]);
      if(!b.at && drag.centre && b.kind!=='link')b.at=[...drag.centre];
    });schedulePreview();
  } else if (drag.kind === "via") {
    mutatePreview(() => { element(drag.sel).via[drag.i] = [snap(drag.orig[0] + dx), snap(drag.orig[1] + dy)]; });
    schedulePreview();
  } else if (drag.kind === "loose") {
    rubber({x: drag.handle.at[0], y: drag.handle.at[1]}, p);
    hover(document.elementFromPoint(e.clientX, e.clientY));
  }
});

canvas.addEventListener("pointerup", async (e) => {
  if(drag?.holdTimer) clearTimeout(drag.holdTimer);
  pointers.delete(e.pointerId);
  if (pinch) { if (pointers.size < 2) pinch = null; return; }
  if (!drag) return;
  const d = drag; drag = null;
  clearDropHint();dropPreviewSequence++;
  canvas.classList.remove("ed-pan");
  clearGuides(); clearGhost();
  const p = toPage(e.clientX, e.clientY);
  freeDrag = e.altKey;
  const physicalFinished=finishPhysicalGesture(d,p);
  freeDrag = false;
  if (physicalFinished) return;
  if (d.kind === "marquee") { finishMarquee(d.start,p); return; }
  if(d.kind==="endpoint") {
    ui.querySelectorAll(".ed-rubber").forEach(n=>n.remove());clearTargets();
    if(!d.moved) setMode("endpoint",{sel:d.sel,end:d.end});
    else {const target=nodeTarget(p);if(target) attachEndpoint(d.sel,d.end,target);
      else await commitTopology(detachEndpoint(S.data,d.sel.role,d.sel.index,d.end,[snap(p.x),snap(p.y)]),d.sel);}
    return;
  }
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
    if (!d.moved) select(null);
    return;
  }
  if (d.kind === "element") {
    if (d.moved && d.movable) {
      let inserted=!d.label && d.sel.role==='branch'?movedResistanceProposal(d.sel,p):null;
      if(inserted?.lead?.alternatives.length>1) {
        const lead=await chooseLead(inserted.lead);
        if(!lead){S.preview=null;drawing.innerHTML=S.scene.parts;return;}
        inserted=relocateResistance(S.data,d.sel.index,lead.index,{segment:lead.i,at:lead.at});
      }
      if(inserted && !inserted.conflicts.length) {
        S.preview=null;if(await commitTopology(inserted,inserted.selection,d.snapshot))fit(inserted.validatedInk);return;
      }
      const committed=S.data;
      if (S.preview) S.data = S.preview;
      S.preview = null;
      let selected = d.sel;
      let mergeReview=null;
      if (d.sel.role === 'node' && !d.label) {
        const node = element(d.sel);
        const target = node?.at && S.data.nodes.find(n => n.id !== node.id && n.at && n.at.every((v,i) => v === node.at[i]));
        if (target) {
          const proposal = mergeNodes(S.data,node.id,target.id);
          if (!proposal.conflicts.length) { S.data = proposal.document; selected = proposal.selection; }
          else mergeReview=[node.id,target.id,proposal.conflicts];
        } else if(node?.at) {
          let lead=junctionLead(node.at,null,null,node.id);
          if(lead?.alternatives.length>1) {
            const preview=S.data;S.data=committed;
            lead=await chooseLead(lead);
            if(!lead){if(S.scene)drawing.innerHTML=S.scene.parts;return;}
            S.data=preview;
          }
          if(lead) {
            const proposal=addJunction(S.data,lead.index,lead.i,lead.at,node.id);
            if(!proposal.conflicts.length) {S.data=proposal.document;selected=proposal.selection;}
          }
        }
      }
      const proposed=S.data;S.data=committed;
      if(mergeReview){if(S.scene)drawing.innerHTML=S.scene.parts;reviewNodeMerge(...mergeReview);return;}
      await commitTopology({document:proposed,conflicts:[]},selected,d.snapshot);
      if (d.routed === false) toast("These nodes are too close to route "
                                    + "around, so the box stayed on the wire.");
    } else {
      // a second tap on the same node within a moment is a double-tap: the
      // touch form of the double-click that starts a connection
      const now = performance.now();
      if (e.pointerType !== "mouse" && lastTap && lastTap.role === d.sel.role && lastTap.index === d.sel.index
          && now - lastTap.t < 400 && Math.hypot(e.clientX - lastTap.x, e.clientY - lastTap.y) < 20) {
        lastTap = null;
        if (d.sel.role === "node") { startConnect(element(d.sel).id, "link"); return; }
      }
      lastTap = {role: d.sel.role, index: d.sel.index, t: now, x: e.clientX, y: e.clientY};
      select(d.sel, true);
    }
    return;
  }
  if (d.kind === "via" || d.kind==='route') {
    if (d.moved) { if (S.preview) S.data = S.preview; S.preview = null; S.undo.push(d.snapshot); S.redo.length = 0; afterEdit(); }
  }
});
canvas.addEventListener("pointercancel", (e) => {
  pointers.delete(e.pointerId); cancelGesture(); pinch = null;
  canvas.classList.remove("ed-pan");
  clearGuides(); clearGhost(); clearTargets();
  ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
});

// the double-click that starts a connection
canvas.addEventListener("dblclick", (e) => {
  if (S.present) return;
  if(performance.now()-lastGestureMove<500) return;
  // the pointer was captured on the way down, so the event's target is the
  // canvas; what is under the pointer is what was double-clicked
  const hit = hitAt(document.elementFromPoint(e.clientX, e.clientY));
  drag = null;
  if (hit && hit.role === "node") {
    e.preventDefault();
    startConnect(element(hit).id, "link");
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
  drawHover(hit);
  hovered = rects;
}

let wheelQuietUntil = 0;
function fitFromCommand() {
  cancelGesture(); pinch=null; pointers.clear();
  wheelQuietUntil=performance.now()+150; S.touched=false; fit();
}
canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  if (performance.now()<wheelQuietUntil) {wheelQuietUntil=performance.now()+150;return;}
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
async function removeSelected() {
  if(groupDraft){gateGroup(removeSelected);return;}
  if (!S.sel) return;
  const sel = S.sel, el = element(sel);
  let went = 0;
  if (sel.role === "node") {
    const id = el.id;
    went = S.data.branches.filter((b) => b.from === id || b.to === id).length
         + S.data.sources.filter((x) => (x.to || x.from) === id).length;
  }
  const group=S.selection.length>1?[...S.selection]:[sel];
  const ordered=group.map(s=>({...s,id:element(s)?.id})).sort((a,b)=>a.role===b.role ? b.index-a.index : a.role==='node'?1:b.role==='node'?-1:a.role.localeCompare(b.role));
  const proposal=mutationProposal(()=>{ for(const item of ordered) {
    const index=item.role==='node'?S.data.nodes.findIndex(n=>n.id===item.id):item.index;
    if(index>=0) removeElement({...item,index});
  } });
  if(!await commitTopology(proposal,null))return;
  select(null);
  if (went) toast(`Deleted selection; preserved ${plural(went, "attached component", "attached components")}.`,
                  {label: "Undo", act: undo});
}

function select(sel, popover = true, fresh = false) {
    if(groupDraft && !sameSel(sel,groupDraft.sel)) {gateGroup(()=>select(sel,popover,fresh));return;}
    if(!sameSel(sel,S.sel))inspectorTab='Properties';
    S.sel = sel;
    if (!S.selection.some(s=>sameSel(s,sel)) || popover || !sel) S.selection=sel?[sel]:[];
  drawSelection();
  $("ed-delete").disabled = !sel;
  if (sel && popover) openPopover(sel, fresh); else closePopover();
  updateChrome();
  if (!fresh) canvas.focus({preventScroll: true});
}

// ------------------------------------------------------------------ modes
// What the drawing is waiting for, said in a pill at the top of the stage.
function setMode(mode, pending = null) {
  if(mode!=="sketch") shapeStart=null;
  S.mode = mode; S.pending = pending;
  canvas.classList.toggle("ed-place", mode === "place");
  canvas.classList.toggle("ed-connect", mode === "connect" || mode === "attach");
  document.querySelectorAll(".ed-card").forEach((c) => c.setAttribute("aria-pressed",
    String(mode === "place" && pending && c.dataset.key === pending.key)));
  document.querySelectorAll('.ed-shape-card').forEach(c=>c.setAttribute('aria-pressed',String(mode==='sketch' && pending && c.dataset.sketch===pending.kind)));
  hitsG.querySelectorAll(".ed-from").forEach((r) => r.classList.remove("ed-from"));
  clearTargets();
  ui.querySelectorAll(".ed-rubber").forEach((r) => r.remove());
  const pill = $("ed-mode");
    let text = "";
    if(mode==="sketch") text={
      region:"Region: drag opposite corners, or click each corner",
      volume:"Control volume: drag opposite corners, or click each corner",
      surface:"Control surface: click an edge of a control volume",
      transfer:"Energy transfer: click a control surface",
      annotation:pending.kind==="text"?"Text: click to place":"Line or arrow: drag, or click both endpoints"
    }[pending.role];
    if(mode==="endpoint") {text="Click the node this endpoint meets";markEndpointTargets(pending);}
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
  const guidance=$("ed-component-guidance");if(guidance) {guidance.textContent=text.replace(/<[^>]*>/g,'');guidance.hidden=!text;}
  if(text && window.matchMedia('(max-width: 820px)').matches) showComponents(false);
  if (text) $("ed-mode-cancel").addEventListener("click", () => setMode("idle"));
}

// Where a loose end may go: any node outside its own island. Inside it,
// joining would either double a path already there or make a branch name
// one node twice, which validation refuses.
function eligible(handle, id) {
  if (!handle || id === handle.id) return false;
  return !!nodeById(id) && !mergeNodes(S.data, handle.id, id).conflicts.length;
}

function markTargets(handle) {
  clearTargets();
  S.data.nodes.forEach((n, i) => {
    if (!eligible(handle, n.id)) return;
    hitsOf({role: "node", index: i}).filter(r=>r.dataset.element==="node").forEach((r) => r.classList.add("ed-target"));
  });
}

function clearTargets() {
  hitsG.querySelectorAll(".ed-target").forEach(
    (r) => r.classList.remove("ed-target"));
}

function markEndpointTargets(pending) {
  clearTargets();
  const b=element(pending.sel),other=b?.[pending.end==="from"?"to":"from"];
  hitsG.querySelectorAll('[data-role="node"][data-element="node"]').forEach(r=>{
    if(S.data.nodes[+r.dataset.index]?.id!==other) r.classList.add("ed-target");
  });
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
async function placeNode(kind, p) {
  const id = newNodeId();
  const at = alignedSnap(p.x, p.y, null);
  const target=S.data.nodes.find(n=>n.at?.every((v,i)=>v===at[i]));
  if(kind==='free' && target) {
    // Reuse the existing junction when repairing a lead drawn through it.
    let lead=junctionLead(at,S.pending?.branchIndex,null,target.id);
    if(lead){lead=await chooseLead(lead);if(!lead)return;}
    if(lead) {
      const proposal=addJunction(S.data,lead.index,lead.i,lead.at,target.id);
      if(proposal.conflicts.length) {toast(proposal.conflicts.join(' '));return;}
      if(!await commitTopology(proposal))return;
    }
    setMode('idle');select({role:'node',index:S.data.nodes.findIndex(n=>n.id===target.id)},true,true);return;
  }
  let lead=kind==='free' ? junctionLead(at,S.pending?.branchIndex) : null;
  if(lead){lead=await chooseLead(lead);if(!lead)return;}
  if(lead) {
    const proposal=addJunction(S.data,lead.index,lead.i,lead.at);
    if(proposal.conflicts.length) {toast(proposal.conflicts.join(' '));return;}
    if(!await commitTopology(proposal))return;setMode('idle');select(proposal.selection,true,true);return;
  }
  edit((d) => {
    const n = {id, at};
    if (kind !== "free") n.kind = kind;
    d.nodes.push(n);
  });
  setMode("idle");
  select({role: "node", index: S.data.nodes.length - 1}, true, true);
}

function junctionLead(at, onlyIndex, excludeIndex, nodeId) {
  const candidates=[];
  S.data.branches.forEach((b,index)=>{
    if(index===excludeIndex || onlyIndex!=null && index!==onlyIndex || (b.count||1)>1) return;
    if(nodeId && (b.from===nodeId || b.to===nodeId)) return;
    const route=routeOf(b);if(!route) return;
    const segment=nearestSegment(route,at),distance=Math.abs(segment.off);
    if(segment.along<0 || segment.along>segment.len || distance>12*unitsPerPixel()) return;
    const point=segment.a.map((v,i)=>tidy(v+segment.u[i]*segment.along));
    if(addJunction(S.data,index,segment.i,point,nodeId).conflicts.length) return;
    candidates.push({index,i:segment.i,at:point,distance});
  });
  candidates.sort((a,b)=>a.distance-b.distance||a.index-b.index);
  const best=candidates[0];
  return best?{...best,alternatives:candidates.filter(c=>c.distance<=best.distance+3*unitsPerPixel())}:null;
}

function chooseLead(lead) {
  if(!lead || lead.alternatives.length<2)return Promise.resolve(lead);
  return new Promise(resolve=>{
    const dialog=document.createElement('dialog');dialog.className='ed-conflict-review';dialog.setAttribute('aria-label','Choose connection');
    dialog.innerHTML='<h3>Choose connection</h3><p>These lines cross without joining. Choose the connection to change.</p>';
    let result=null;
    for(const candidate of lead.alternatives) {
      const b=S.data.branches[candidate.index],button=document.createElement('button');
      button.textContent=(b.label||kindName('branch',b.kind||'cond'))+' — '+nodeName(b.from)+' → '+nodeName(b.to);
      button.onfocus=button.onpointerenter=()=>{clearGuides();const route=routeOf(b);ui.appendChild(svgEl('polyline',{points:route.map(p=>p.join(',')).join(' '),fill:'none'},'ed-guide'));};
      button.onclick=()=>{result=candidate;dialog.close();};dialog.appendChild(button);
    }
    const cancel=document.createElement('button');cancel.textContent='Cancel';cancel.onclick=()=>dialog.close();dialog.appendChild(cancel);
    dialog.onclose=()=>{clearGuides();dialog.remove();resolve(result);};document.body.appendChild(dialog);dialog.showModal();
  });
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

async function dropPath(kind, p) {
  let proposal=resistanceDropProposal(kind,p);
  if(proposal?.lead?.alternatives.length>1) {
    const lead=await chooseLead(proposal.lead);if(!lead)return;
    proposal=insertResistance(S.data,lead.index,kind,{segment:lead.i,at:lead.at});
  }
  if(proposal) {
    if(proposal.conflicts.length){toast(proposal.conflicts.join(' '));return;}
    if(!await commitTopology(proposal))return;setMode('idle');select(proposal.selection,true,true);fit(proposal.validatedInk);return;
  }
  const [cx, cy] = alignedSnap(p.x, p.y, null);
  const half = PITCH / 2;
  const left=nodeTarget({x:cx-half,y:cy}),right=nodeTarget({x:cx+half,y:cy});
  const leftAt=[snap(cx-half),cy],rightAt=[snap(cx+half),cy];
  edit((d) => {
    const a = left || newNodeId();
    if(!left) d.nodes.push({id: a, at: leftAt});
    const b = right && right!==a ? right : newNodeId();
    if(b!==right) d.nodes.push({id: b, at: rightAt});
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
  const target = nodeTarget(p);
  const [x, y] = alignedSnap(p.x, p.y, null);
  edit((d) => {
    const id = target || newNodeId();
    if(!target) d.nodes.push({id, at: [x, y]});
    const s = {to: id};
    if (kind !== "diss") s.kind = kind;
    if(target) s.angle=freeSide(target);
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
document.querySelectorAll(".ed-card").forEach((card) => {
  const entry = {key: card.dataset.key, role: card.dataset.role, kind: card.dataset.kind};
  card.addEventListener('click',e=>{if(e.detail===0) setMode('place',entry);});
  card.addEventListener("pointerdown", (e) => {
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});
    freeDrag=e.altKey;lastAlign={x:null,y:null};
    card.setPointerCapture(e.pointerId);
    cardDrag = {entry, start: {x: e.clientX, y: e.clientY}, moved: false, ghost: null};
  });
  card.addEventListener("pointermove", (e) => {
    if (!cardDrag) return;
    freeDrag=e.altKey;
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
    const p=toPage(e.clientX,e.clientY);
    if(entry.role==='branch' && resistanceKinds.has(entry.kind)) previewResistanceDrop(entry.kind,p,cardDrag);
    const [cx,cy]=entry.role==="branch"?alignedSnap(p.x,p.y,null):[p.x,p.y];
    const targets=entry.role==="source"?[nodeTarget(p)]:entry.role==="branch"?[nodeTarget({x:cx-PITCH/2,y:cy}),nodeTarget({x:cx+PITCH/2,y:cy})]:[];
    clearTargets();
    targets.filter(Boolean).forEach(id=>hitsOf({role:"node",index:S.data.nodes.findIndex(n=>n.id===id)}).filter(r=>r.dataset.element==="node").forEach(r=>r.classList.add("ed-target")));
  });
  const finish = (e) => {
    clearDropHint();
    pointers.delete(e.pointerId);
    freeDrag=e.altKey;
    if (!cardDrag) return;
    const d = cardDrag; cardDrag = null;
    S.preview=null;dropPreviewSequence++;if(S.scene)drawing.innerHTML=S.scene.parts;
    if (d.ghost) d.ghost.remove();
    hover(null);clearTargets();
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
  card.addEventListener("pointercancel", (e) => { pointers.delete(e.pointerId);cancelGesture();hover(null); });
});

// Quick add is intentional; ordinary empty-space clicks only deselect.
let dropPreviewSequence=0;
async function previewResistanceDrop(kind,p,gesture,provided=null) {
  const proposal=provided||resistanceDropProposal(kind,p),sequence=++dropPreviewSequence;
  if(!proposal || proposal.conflicts.length){clearDropHint();S.preview=null;if(S.scene)drawing.innerHTML=S.scene.parts;return;}
  showDropHint(proposal,p);
  S.preview=proposal.document;
  try {
    const scene=await rpc.call('scene',proposal.document,S.notation,false,null,S.file?.display||{mode:'automatic'});
    if(cardDrag!==gesture && drag!==gesture || sequence!==dropPreviewSequence)return;
    if(!scene.error)drawing.innerHTML=scene.parts;
  }catch {if(cardDrag===gesture || drag===gesture)S.preview=null;}
}
const quick = $("ed-quick"), quickInput = $("ed-quick-input"), quickList = $("ed-quick-list");
let quickAt = null, quickItems = [], quickIndex = 0;

function requestQuick(x,y) {
  if(!S.ready || !S.data || S.present) return;
  cancelGesture();setMode("idle");select(null);closeMenu();
  openQuick(toPage(x,y),x,y);
}

canvas.addEventListener("contextmenu",e=>{
  if(S.present || hitAt(e.target) || e.target.closest("#ed-ui")) return;
  e.preventDefault();
  // Touch uses the cancellable hold timer, not the browser's native hold menu.
  if(e.pointerType==="touch" || e.sourceCapabilities?.firesTouchEvents) return;
  requestQuick(e.clientX,e.clientY);
});

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

canvas.addEventListener("click",e=>{
  // The compatibility click after releasing a hold must not steal search focus.
  if(!quick.hidden && performance.now()<touchQuickUntil) {e.preventDefault();quickInput.focus();}
});

// Clipboard objects use ordinary JSON so they also travel between editor tabs.
const editingText = target => ["INPUT","TEXTAREA","SELECT"].includes(target.tagName) || target.isContentEditable;
let pastedText=null,pasteCount=0;
document.addEventListener("copy",e=>{
  if(editingText(e.target) || !S.data || !S.sel || !e.clipboardData) return;
  cancelGesture();
  const chosen=new Map(Object.keys(COLLECTION).map(role=>[role,new Set()]));
  const add=(role,obj)=>{
    if(!obj || chosen.get(role).has(obj)) return;
    chosen.get(role).add(obj);
    if(role==="branch" || role==="source") for(const id of [obj.from,obj.to]) {
      if(id==="rail") add("node",nodeById(S.data.rail?.reference));
      else add("node",nodeById(id));
    }
    if(role==="volume") {
      if(obj.storage_relation?.branch)add("branch",list("branch").find(b=>b.id===obj.storage_relation.branch));
      for(const id of obj.regions||[]) add("region",list("region").find(r=>r.id===id));
      for(const s of list("surface").filter(s=>s.volume===obj.id)) add("surface",s);
    }
    if(role==="region") for(const v of list("volume").filter(v=>(v.regions||[]).includes(obj.id))) add("volume",v);
    if(role==="surface") {
      add("volume",list("volume").find(v=>v.id===obj.volume));
      for(const t of list("transfer").filter(t=>t.surface===obj.id)) add("transfer",t);
    }
    if(role==="transfer") add("surface",list("surface").find(s=>s.id===obj.surface));
  };
  for(const sel of S.selection.length?S.selection:[S.sel]) add(sel.role,element(sel));
  const data=Object.fromEntries([...chosen].map(([role,objects])=>[COLLECTION[role],[...objects]]));
  data.units=S.data.units||{};
  data.network_basis=S.data.network_basis||{};
  const copiedNodes=new Set(data.nodes.map(n=>n.id));
  data.cases=(S.data.cases||[]).filter(g=>g.nodes.every(n=>copiedNodes.has(n)));
  data.layout_options={starts:(S.data.layout_options?.starts||[]).filter(n=>copiedNodes.has(n))};
  if(data.branches.some(b=>b.from==="rail" || b.to==="rail")) data.rail=S.data.rail;
  const payload={type:"thermodraw-selection",origin:S.file.id,data};
  e.clipboardData.setData("text/plain",JSON.stringify(payload));e.preventDefault();
  pastedText=null;pasteCount=0;
  toast("Selection copied. Paste to duplicate it here or in another diagram.");
});

document.addEventListener("paste",async e=>{
  if(editingText(e.target) || !S.data || S.present || !e.clipboardData) return;
  const raw=e.clipboardData.getData("text/plain");
  let payload;
  try {payload=JSON.parse(raw);} catch {return;}
  if(payload?.type!=="thermodraw-selection") return;
  e.preventDefault();cancelGesture();
  try {
    const data=structuredClone(payload.data),candidate=JSON.parse(snapshot());
    const generation=S.generation,revision=S.revision;
    if(JSON.stringify(data.network_basis||{})!==JSON.stringify(candidate.network_basis||{}))throw Error('Match the network basis and reference size before pasting');
    const count=raw===pastedText?pasteCount+1:1,shift=20*count;
    const ids=new Map(),physical=new Set(["region","volume","surface","transfer","annotation"]);
    const allPhysical=new Set([...physical].flatMap(role=>list(role).map(o=>o.id)));
    for(const [role,key] of Object.entries(COLLECTION)) {
      if(!Array.isArray(data[key])) throw new Error("Invalid selection data");
      const used=physical.has(role)?allPhysical:new Set(list(role).map(o=>o.id));
      for(const obj of data[key]) if(obj.id!=null) {
        const base=obj.id;let id=base,n=1;
        while(used.has(id)) id=`${base}_copy${n++}`;
        used.add(id);ids.set(`${role}:${base}`,id);obj.id=id;
      }
    }
    const physicalId=(role,id)=>ids.get(`${role}:${id}`)||id;
    const point=p=>[p[0]+shift,p[1]+shift];
    const selection=[];
    for(const [role,key] of Object.entries(COLLECTION)) for(const obj of data[key]) {
      if(obj.at) obj.at=point(obj.at);
      if(Array.isArray(obj.end)) obj.end=point(obj.end);
      if(obj.via) obj.via=obj.via.map(point);
      if(role==="branch" || role==="source") for(const end of ["from","to"]) if(obj[end] && obj[end]!=="rail") obj[end]=physicalId("node",obj[end]);
      if(obj.regions) obj.regions=obj.regions.map(id=>physicalId("region",id));
      if(obj.volume) obj.volume=physicalId("volume",obj.volume);
      if(obj.surface) obj.surface=physicalId("surface",obj.surface);
      if(obj.storage_relation?.branch)obj.storage_relation.branch=physicalId("branch",obj.storage_relation.branch);
      if(obj.links) obj.links=obj.links.flatMap(link=>{
        const split=link.indexOf(":"),role=link.slice(0,split);
        return ids.has(link)?[`${role}:${ids.get(link)}`]:payload.origin===S.file.id && list(role).some(o=>`${role}:${o.id}`===link)?[link]:[];
      });
      candidate[key] ||= [];selection.push({role,index:candidate[key].length});candidate[key].push(obj);
    }
    for(const group of data.cases||[]) {
      const used=new Set((candidate.cases||[]).map(g=>g.id));let id=group.id,i=1;while(used.has(id))id=group.id+'_copy'+i++;
      (candidate.cases||=[]).push({...group,id,nodes:group.nodes.map(n=>physicalId('node',n))});
    }
    if(data.layout_options?.starts?.length){candidate.layout_options||={};(candidate.layout_options.starts||=[]).push(...data.layout_options.starts.map(n=>physicalId('node',n)));}
    candidate.units ||= {};
    for(const [key,value] of Object.entries(data.units||{})) {
      if(candidate.units[key]!=null && JSON.stringify(candidate.units[key])!==JSON.stringify(value)) throw new Error(`Different ${key} units; match the diagram units before pasting`);
      candidate.units[key]=value;
    }
    if(data.rail && !candidate.rail) {
      candidate.rail={...data.rail,reference:physicalId("node",data.rail.reference),y:data.rail.y+shift};
      if(data.rail.span) candidate.rail.span=data.rail.span.map(x=>x+shift);
    }
    const checked=await rpc.call("scene",candidate,S.notation,S.physics);
    if(checked.error) throw new Error(checked.error);
    if(generation!==S.generation || revision!==S.revision) {toast("The diagram changed while pasting. Paste again.");return;}
    edit(()=>{S.data=candidate;});S.selection=selection;S.sel=selection.at(-1)||null;
    closePopover();drawSelection();updateChrome();
    pastedText=raw;pasteCount=count;
  } catch(err) {toast("Could not paste: "+err.message);}
});

quickInput.addEventListener("input", async () => {
  const text = quickInput.value.trim();
  if (!text) { quickList.innerHTML = ""; quickItems = []; return; }
  try { quickItems = await rpc.call("quick_add", text); } catch { quickItems = []; }
  if (quickInput.value.trim() !== text) return;
  quickItems.push(...[...document.querySelectorAll('.ed-shape-card')].filter(b=>b.textContent.toLowerCase().includes(text.toLowerCase())).map(b=>({name:b.textContent,role:'drawing',kind:b.dataset.sketch,sketch:b.dataset.sketch})));
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
  if(it.sketch) {armSketch(it.sketch);return;}
  if (it.role === "node") placeNode(it.kind, p);
  else setMode("place", it);
}

// ------------------------------------------------------------- popover
const pop = $("ed-popover");
const menu = $("ed-menu");
let componentCategory = "Network";
function showComponents(open=true) {
  if(groupDraft){gateGroup(()=>showComponents(open));return;}
  if(open)setPanelView('Components',true);
  document.body.classList.toggle("ed-components-collapsed",!open);
  document.body.classList.toggle("ed-components-open",open);
  $("ed-sketch").setAttribute("aria-expanded",String(open));
}
function filterComponents() {
  const query=$("ed-component-search").value.trim().toLowerCase();let count=0;
  document.querySelectorAll('[data-component-group]').forEach(group=>{
    let visible=0;
    group.querySelectorAll('.ed-component-row').forEach(row=>{
      const match=query ? row.dataset.search.toLowerCase().includes(query) : group.dataset.category===componentCategory;
      row.hidden=!match;if(match) visible++;
    });group.hidden=!visible;count+=visible;
  });
  $("ed-component-empty").hidden=count>0;$("ed-component-clear").hidden=!query;
}
$("ed-component-search").addEventListener("input",filterComponents);
$("ed-component-clear").addEventListener("click",()=>{$("ed-component-search").value="";filterComponents();$("ed-component-search").focus();});
$("ed-components-close").addEventListener("click",()=>{showComponents(false);$("ed-sketch").focus();});
$("ed-sketch").addEventListener("click",()=>{showComponents(!document.body.classList.contains("ed-components-open"));});
document.querySelectorAll('[data-category-tab]').forEach(button=>button.addEventListener('click',()=>{
  componentCategory=button.dataset.categoryTab;$("ed-component-search").value="";
  document.querySelectorAll('[data-category-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));filterComponents();
}));
function armSketch(kind) {
  cancelGesture();closeMenu();shapeStart=null;
  const prerequisite=kind==='surface'&&!list('volume').length?'volume':kind==='transfer'&&!list('surface').length?'surface':null;
  if(prerequisite) {
    const note=$("ed-component-note");note.hidden=false;note.innerHTML=`Add a control ${prerequisite} first. <button type="button" data-sketch="${prerequisite}">Add control ${prerequisite}</button>`;showComponents();return;
  }
  $("ed-component-note").hidden=true;
  setMode("sketch",{role:["text","line","arrow"].includes(kind)?"annotation":kind,kind});
}
$("ed-component-tools").addEventListener('click',e=>{
  const shape=e.target.closest('[data-sketch]');if(shape) armSketch(shape.dataset.sketch);
  const help=e.target.closest('[data-component-note]');if(help) {
    const note=$(help.getAttribute('aria-controls')),open=note.hidden;
    note.hidden=!open;help.setAttribute('aria-expanded',String(open));
  }
});
menu.addEventListener("click",e=>{if(e.target.dataset.sketch) armSketch(e.target.dataset.sketch);});
// Escape closes the component drawer before changing canvas state.
document.addEventListener('keydown',e=>{
  if(e.key==='Escape' && !solveOpen && !e.target.closest('dialog') && document.body.classList.contains('ed-components-open') && window.matchMedia('(max-width: 820px)').matches) {showComponents(false);e.preventDefault();e.stopImmediatePropagation();$("ed-sketch").focus();}
},true);
window.matchMedia('(max-width: 820px)').addEventListener('change',e=>{
  if(panelView==='Properties'&&S.sel || panelView==='Solve'&&solveOpen)setPanelView(panelView,true);
  else showComponents(!e.matches);
});
if(!window.matchMedia('(max-width: 820px)').matches) document.body.classList.add('ed-components-open');
else $("ed-sketch").setAttribute('aria-expanded','false');
function relationshipPicker(label,key,choices,selected) {
  return `<fieldset class="ed-relationships"><legend>${label}</legend><input type="search" data-relationship-search aria-label="Find ${label.toLowerCase()}" placeholder="Search by label or ID">${choices.map(o=>`<label data-relationship-row><input type="checkbox" data-relationship="${key}" value="${escapeHtml(o.value)}" ${selected.includes(o.value)?'checked':''}><span>${escapeHtml(o.label)} <small>${escapeHtml(o.value)}</small></span></label>`).join('')}${!choices.length?'<p>No available objects. Add one first.</p>':''}</fieldset>`;
}
pop.addEventListener('input',e=>{if(e.target.hasAttribute('data-relationship-search')) e.target.parentElement.querySelectorAll('[data-relationship-row]').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase()));});
pop.addEventListener('change',e=>{
  if(e.target.dataset.relationship) {const field=e.target.dataset.relationship;edit(()=>{element(S.sel)[field]=[...pop.querySelectorAll(`[data-relationship="${field}"]:checked`)].map(box=>{let value=box.value;if(field==='links' && value.includes(':@')) {const [role,index]=value.split(':@'),obj=list(role)[+index];let id=role+'_'+(+index+1),n=1;while(list(role).some(o=>o.id===id)) id=role+'_'+(+index+1)+'_'+n++;obj.id=id;value=role+':'+id;box.value=value;}return value;});});return;}
  if(e.target.hasAttribute('data-transfer-input')) {edit(()=>{const el=element(S.sel);if(e.target.value==='flux') {delete el.rate;el.flux='';}else {delete el.flux;el.rate='';}});openPhysicalPopover(S.sel);}
});
pop.addEventListener("change",e=>{
  const f=e.target.dataset.physical;if(!f || !S.sel) return;
  const raw=e.target.type==="checkbox"?e.target.checked:e.target.value;
  const bounded={width:[10,Infinity],height:[10,Infinity],start:[0,1],end:[0,1],length:[1,Infinity]};
  let error='';if(bounded[f] && (raw==='' || !Number.isFinite(Number(raw)) || Number(raw)<bounded[f][0] || Number(raw)>bounded[f][1])) error='Enter a number between '+bounded[f][0]+' and '+bounded[f][1]+'.';
  const current=element(S.sel);if(current.storage_relation && (f==='storage'||f==='steady'&&raw))error='Switch to Manual storage power before changing this input.';if(f==='start' && Number(raw)>=current.end || f==='end' && Number(raw)<=current.start) error='Start must be before end.';
  pop.querySelector('[data-property-error]')?.remove();e.target.removeAttribute('aria-invalid');
  if(error) {e.target.setAttribute('aria-invalid','true');const note=document.createElement('p');note.dataset.propertyError='';note.className='ed-danger';note.textContent=error;e.target.after(note);return;}
  edit(()=>{
    const el=element(S.sel);
    if(f==="width" || f==="height") {el.size[f==="width"?0:1]=Math.max(10,Number(raw)||10);return;}
    if(f==="regions" || f==="links") el[f]=raw.split(",").map(s=>s.trim()).filter(Boolean);
    else if(f==="steady") {el.steady=raw;if(raw) delete el.storage;}
    else if(raw==="") delete el[f];
    else el[f]=["start","end","length"].includes(f)?Number(raw):raw;
    if(f==="rate" && raw!=="") delete el.flux;
    if(f==="flux" && raw!=="") delete el.rate;
    if(f==="kind" && raw!=="heat") delete el.flux;
  });
  const scroll=pop.scrollTop;
  openPhysicalPopover(S.sel);pop.scrollTop=scroll;
  pop.querySelector(`[data-physical="${f}"]`)?.focus({preventScroll:true});
});
pop.addEventListener("click",e=>{
  if(e.target.hasAttribute("data-review-budget")) {edit(()=>{delete element(S.sel).incomplete;});openPhysicalPopover(S.sel);}
});

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
const more = () => `<details open class="ed-common-controls"><summary>Connections and Appearance</summary>`;
pop.addEventListener("toggle", (e) => {
  if (e.target.tagName === "DETAILS") moreOpen = e.target.open;
}, true);

// An angle field rests at 0 and is never blank, and the two buttons turn
// it in 45s, snapping whatever is in the box to the nearest 45 on the way.
// `reset` is the only way back to a branch's "turns with its wire", which
// is what an absent angle means and no number can say.
function rotateField(label, value, reset) {
  return `<label class="ed-rot"><span>${label}</span><span class="ed-rot-c">`
    + `<button type="button" data-rot="-45" aria-label="Rotate counterclockwise" title="Turn 45 degrees anticlockwise">&#8634;</button>`
    + `<input type="number" data-field="angle" value="${value}" step="45" aria-label="${escapeHtml(label)}">`
    + `<button type="button" data-rot="45" aria-label="Rotate clockwise" title="Turn 45 degrees clockwise">&#8635;</button>`
    + `<button type="button" data-rot="reset" aria-label="Reset rotation" class="ed-rot-reset" title="${escapeHtml(reset)}">reset</button>`
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
  openFindings(false);
  if(S.selection.length>1){
    pop.innerHTML=`<h4>${S.selection.length} selected objects</h4><p data-selection-summary>${escapeHtml(issueNames({targets:S.selection}))}</p><button type="button" data-act="delete-selection" class="ed-danger">Delete ${S.selection.length} selected objects</button>`;
    dockInspector(sel);return;
  }
  const el = element(sel);
  if (!el) return;
  if (["region","volume","surface","transfer","annotation"].includes(sel.role)) { openPhysicalPopover(sel); return; }
  const u = S.data.units || {};
  let h = "";
  if (sel.role === "node") {
    const kind = el.kind || "free";
    h += `<h4>${escapeHtml(nodeName(el.id))}</h4>`;
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
    h += `<h4>${escapeHtml(el.label||kindName("branch",kind))} <small>${escapeHtml(nodeName(el.from))} → ${escapeHtml(nodeName(el.to))}</small></h4>`;
    h += field("Kind", selectBox("kind", kind, KINDS.branch, Object.fromEntries(KINDS.branch.map((k) => [k, kindName("branch", k)]))));
    h += field("From",selectBox("from",el.from,list("node").map(n=>n.id),Object.fromEntries(list("node").map(n=>[n.id,nodeName(n.id)]))));
    h += field("To",selectBox("to",el.to,list("node").map(n=>n.id),Object.fromEntries(list("node").map(n=>[n.id,nodeName(n.id)]))));
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
      h += field(`${el.count>1?'Value per component — ':''}${q}, ${escapeHtml(u[q] || "no unit")}`, text("value", el.value, "value"));
    }
    if (kind === "cap" || kind === "stream") h += field("Subscript", text("sub", el.sub, kind === "stream" ? "names the medium" : "names the place"));
    if (!unvalued && kind !== "flow") h += field(`Rate q, ${escapeHtml(u.q || "no unit")}`, text("rate", el.rate, "optional"));
    h += more();
    // A stream refuses both: its number is derived, so a group would draw
    // with no value under it. Offering the field would be offering a refusal.
    if (kind !== "stream") {
      h += field("Count", num("count", el.count || 1, 1));
      h += `<div data-group-arrangement ${!(el.count>1)?'hidden':''}>`+field("Arrangement", selectBox("arrangement", el.arrangement || "", ["", "series", "parallel"], {"": "Choose arrangement"}))+`</div>`;
      const combined=el.count>1?groupProposal(S.data,sel.index,String(el.count),el.arrangement).combined:null;
      h += `<div data-group-preview aria-live="polite">${el.count>1?'Combined value: '+(combined??'unspecified'):''}</div><div class="ed-row" data-group-actions hidden><button type="button" data-group-apply>Apply</button><button type="button" data-group-cancel>Cancel</button></div>`;
    }
    if (kind !== "flow" && kind !== "stream") h += rotateField("Symbol angle", shownAngle(sel, el), "back to turning with the wire");
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += field("Reference ID", text("id", el.id, "optional, for physical links"));
    h += field('Symbol position',selectBox('symbol-position',el.at?'manual':'automatic',['automatic','manual'],{automatic:'Automatic',manual:'Manual'}));
    h += `<div class="ed-row"><button type="button" data-act="swap">Reverse direction</button><button type="button" data-act="unpin">Reset position</button></div>`;
    h += `<div class="ed-row"><button type="button" data-act="disconnect-from">Disconnect start</button><button type="button" data-act="disconnect-to">Disconnect end</button><button type="button" data-act="disconnect-both">Disconnect both</button></div>`;
    h += `<p style="margin:8px 0 4px;font-size:12.5px;color:var(--ink-3)">Bends</p><ul class="ed-vias">`;
    (el.via || []).forEach((v, i) => { h += `<li><input type="number" step="any" data-route-point="${i}" data-axis="0" aria-label="Waypoint ${i+1} x" value="${v[0]}"><input type="number" step="any" data-route-point="${i}" data-axis="1" aria-label="Waypoint ${i+1} y" value="${v[1]}"> <button type="button" data-act="via-del" data-i="${i}">remove</button></li>`; });
    h += `</ul><div class="ed-row"><button type="button" data-act="via-add">Add junction</button></div>`;
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  } else {
    const kind = el.kind || "diss";
    const outward = el.from != null;
    h += `<h4>${escapeHtml(kindName("source", kind))} <code>${outward ? escapeHtml(nodeName(el.from)) + " →" : "→ " + escapeHtml(nodeName(el.to))}</code></h4>`;
    h += field("Kind", selectBox("kind", kind, KINDS.source, Object.fromEntries(KINDS.source.map((k) => [k, kindName("source", k)]))));
    h += field("Label", text("label", el.label, "e.g. Switching loss"));
    h += field("Attached node",selectBox(outward?"from":"to",outward?el.from:el.to,list("node").map(n=>n.id),Object.fromEntries(list("node").map(n=>[n.id,nodeName(n.id)]))));
    h += field("Subscript", text("sub", el.sub, "names the place"));
    const q = kind === "diss" ? "P" : kind === "flux" ? "q″" : "q";
    h += field(`${q}, ${escapeHtml(u[q] || "no unit")}`, text("value", el.value, "value"));
    if (kind === "flow" || kind === "flux") h += field("Direction", selectBox("direction", outward ? "out" : "in", ["in", "out"], {in: "into the node", out: "leaving the node"}));
    h += more();
    h += field("Reference ID", text("id", el.id, "optional, for physical links"));
    h += field("Count", num("count", el.count, 1));
    h += rotateField("Angle", shownAngle(sel, el), "back to 0");
    h += field("Label side", selectBox("side", el.side || "auto", SIDES));
    h += field('Symbol position',selectBox('symbol-position',el.at?'manual':'automatic',['automatic','manual'],{automatic:'Automatic',manual:'Manual'}));
    h += `<div class="ed-row"><button type="button" data-act="unpin">Reset position</button></div>`;
    h += `</details>`;
    h += `<div class="ed-row"><button type="button" data-act="delete" class="ed-danger">Delete</button></div>`;
  }
  h += `<p class="ed-hint">Label position: ${el.label_offset?'Manual':'Automatic'}</p><div class="ed-row"><button type="button" data-act="auto-label">Auto position label</button></div>`;
  h += `<button type="button" data-assignment-open>Physics and document options…</button>`;
  pop.innerHTML = h;
  const advanced=document.createElement('details');advanced.innerHTML='<summary>Advanced metadata</summary>';
  for(const input of pop.querySelectorAll('input[data-field="id"]'))advanced.appendChild(input.closest('label'));
  if(advanced.children.length>1)pop.appendChild(advanced);
  pop.hidden = false;
  placePopover(sel);
  const first = pop.querySelector('input[data-field="label"]');
  if (fresh && first && !first.value) first.focus();
}

function placePopover(sel) {
  dockInspector(sel);return;
}
function placeLegacyPopover(sel) {
  pop.style.position='absolute';
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

function closePopover() { if(groupDraft) return; if(pop.classList.contains('ed-docked')) {pop.classList.remove('ed-docked');$('ed-stage').appendChild(pop);setPanelView(solveOpen?'Solve':'Components',true);} pop.hidden = true; pop.innerHTML = ""; delete pop.dataset.rename; }

let groupDraft=null, groupPreviewSequence=0;
function gateGroup(action) {
  pop.querySelector('[data-group-leave]')?.remove();
  const box=document.createElement('div');box.dataset.groupLeave='';
  box.innerHTML='<p>Finish the group change before leaving.</p><button data-leave-apply>Apply</button> <button data-leave-discard>Discard</button> <button data-leave-keep>Keep editing</button>';
  box.querySelector('[data-leave-apply]').onclick=async()=>{if(await applyGroupDraft()) action();};
  box.querySelector('[data-leave-discard]').onclick=()=>{cancelGroupDraft();action();};
  box.querySelector('[data-leave-keep]').onclick=()=>box.remove();pop.appendChild(box);
}

function nodeName(id,data=S.data) {const node=data.nodes.find(n=>n.id===id);return node?.label || (node?'Junction '+id.replace(/^n(?=\d+$)/,''):id==='rail'?'Reference rail':id);}

const resistanceKinds=new Set(['cond','conv','rad','contact','spread','pipe','mixed']);
function insertionObstacles(excludeIndex) {
  return (S.scene?.hits||[]).filter(h=>['label','symbol','node','ground','phase','region','volume','annotation'].includes(h.element)
    && !(h.role==='branch'&&h.index===excludeIndex)).map(h=>({bounds:h.bounds,nodeId:h.role==='node'?S.data.nodes[h.index]?.id:null}));
}
function resistanceLead(p,excludeIndex) {
  const lead=junctionLead([p.x,p.y],null,excludeIndex);
  if(!lead)return null;
  const sharedLead=sharedTerminalLead(S.data,lead.alternatives);
  return sharedLead?{...lead,sharedLead,alternatives:[lead]}:lead;
}
function resistanceDropProposal(kind,p) {
  if(!resistanceKinds.has(kind))return null;
  const hit=(S.scene?.hits||[]).find(h=>h.role==='branch' && h.element==='symbol' && resistanceKinds.has(S.data.branches[h.index]?.kind||'cond') && p.x>=h.bounds[0] && p.x<=h.bounds[2] && p.y>=h.bounds[1] && p.y<=h.bounds[3]);
  if(hit)return {...insertResistance(S.data,hit.index,kind,{parallel:true,obstacles:insertionObstacles()}),hint:'Add in parallel',target:hit.index};
  const lead=resistanceLead(p);
  return lead?{...insertResistance(S.data,lead.index,kind,{segment:lead.i,at:lead.at,sharedLead:lead.sharedLead}),lead,hint:'Insert in series',target:lead.index}:null;
}
function clearDropHint() {document.querySelector('.ed-drop-hint')?.remove();}
function showDropHint(proposal,p) {
  let hint=document.querySelector('.ed-drop-hint');
  if(!hint){hint=document.createElement('div');hint.className='ed-drop-hint card';hint.setAttribute('role','status');document.body.appendChild(hint);}
  const b=S.data.branches[proposal.target],screen=toScreen(p.x,p.y),rect=$('ed-stage').getBoundingClientRect();
  hint.textContent=proposal.hint+' — '+(proposal.lead?.sharedLead?'shared lead ('+proposal.lead.sharedLead.candidates.length+' paths)':b?.label||kindName('branch',b?.kind||'cond'))+(proposal.lead?.alternatives.length>1?' (choose crossing line on release)':'');
  hint.style.left=clamp(rect.left+screen.x+16,8,innerWidth-300)+'px';hint.style.top=clamp(rect.top+screen.y+20,8,innerHeight-70)+'px';
}
function movedResistanceProposal(sel,p) {
  const b=S.data.branches[sel.index];if(!resistanceKinds.has(b?.kind||'cond'))return null;
  const hit=(S.scene?.hits||[]).find(h=>h.role==='branch'&&h.index!==sel.index&&h.element==='symbol'&&resistanceKinds.has(S.data.branches[h.index]?.kind||'cond')&&p.x>=h.bounds[0]&&p.x<=h.bounds[2]&&p.y>=h.bounds[1]&&p.y<=h.bounds[3]);
  if(hit)return {...relocateResistance(S.data,sel.index,hit.index,{parallel:true,obstacles:insertionObstacles(sel.index)}),hint:'Add in parallel',target:hit.index};
  const lead=resistanceLead(p,sel.index);
  return lead?{...relocateResistance(S.data,sel.index,lead.index,{segment:lead.i,at:lead.at,sharedLead:lead.sharedLead}),lead,hint:'Insert in series',target:lead.index}:null;
}
async function updateGroupDraft(field,raw) {
  // A text field emits both input and change. Blurring it must not invalidate
  // the already validated proposal between an Apply pointerdown and click.
  if(groupDraft && groupDraft[field]===raw) return;
  if(!groupDraft) {
    const committed=element(S.sel);
    if(raw===(field==='count'?String(committed.count||1):committed.arrangement||'')) return;
  }
  if(!groupDraft) groupDraft={base:structuredClone(S.data),sel:{...S.sel},count:String(element(S.sel).count||1),arrangement:element(S.sel).arrangement||'',revision:S.revision,generation:S.generation};
  const draft=groupDraft;draft[field]=raw;
  for(const input of pop.querySelectorAll('input[data-field],select[data-field]'))if(!['count','arrangement'].includes(input.dataset.field))input.disabled=true;
  for(const button of pop.querySelectorAll('button[data-act],button[data-rot]'))button.disabled=true;
  const sequence=++groupPreviewSequence;
  const controls=pop.querySelector('[data-group-actions]'),slot=pop.querySelector('[data-group-preview]');
  controls.hidden=false;controls.querySelector('[data-group-apply]').disabled=true;
  pop.querySelector('[data-group-arrangement]').hidden=!(Number(draft.count)>1);
  let proposal=groupProposal(draft.base,draft.sel.index,draft.count,draft.arrangement);
  draft.proposal=null;
  if(proposal.error) {slot.textContent=proposal.error;drawing.innerHTML=S.scene.parts;return;}
  const b=proposal.document.branches[draft.sel.index],old=draft.base.branches[draft.sel.index];
  if(Number(draft.count)>(old.count||1) || draft.arrangement!==old.arrangement && Number(draft.count)>1) {
    const route=routeOf(old),hit=symbolHit(draft.sel);
    if(route) {
      const segment=nearestSegment(route,b.at||hit?.at||route[0]).i;
      const count=Math.min(Number(draft.count),3),required=draft.arrangement==='series'?count*142+40:180;
      const expanded=expandSegment(proposal.document,draft.sel.index,segment,required);
      if(expanded.error) {slot.textContent=expanded.error;return;}
      proposal.document=expanded.document;
      if(draft.arrangement==='parallel') {
        const cleared=clearGroupLanes(proposal.document,draft.sel.index,segment,((count-1)*46)/2+36);
        if(cleared.error){slot.textContent=cleared.error;return;}
        proposal.document=cleared.document;
      }
    }
  }
  slot.textContent='Validating geometry…';
  try {
    const scene=await rpc.call('scene',proposal.document,S.notation,S.physics,null,S.file?.display||{mode:'automatic'});
    if(groupDraft!==draft || sequence!==groupPreviewSequence) return;
    if(scene.error) {slot.textContent=scene.error;return;}
    draft.proposal=proposal;drawing.innerHTML=scene.parts;
    slot.textContent=Number(draft.count)>1 ? `Value per component: ${b.value??'unspecified'}. Combined value: ${proposal.combined??'unspecified'}. Preview — Apply to save.` : 'Preview — Apply to save.';
    controls.querySelector('[data-group-apply]').disabled=false;
  } catch(error) {if(groupDraft===draft) slot.textContent=error.message;}
}
function cancelGroupDraft() {
  const selected=groupDraft?.sel;groupDraft=null;groupPreviewSequence++;
  if(S.scene) drawing.innerHTML=S.scene.parts;
  if(selected) openPopover(selected);
}
async function applyGroupDraft() {
  const draft=groupDraft;if(!draft?.proposal) return false;
  if(draft.revision!==S.revision || draft.generation!==S.generation) {toast('The diagram changed. Cancel this draft and try again.');return false;}
  groupDraft=null;groupPreviewSequence++;
  if(JSON.stringify(draft.proposal.document)!==JSON.stringify(S.data)) edit(d=>replaceDocument(d,draft.proposal.document));
  else drawing.innerHTML=S.scene.parts;
  openPopover(draft.sel);return true;
}
pop.addEventListener('click',e=>{if(e.target.hasAttribute('data-group-apply')) applyGroupDraft();if(e.target.hasAttribute('data-group-cancel')) cancelGroupDraft();});

// A card that belongs to a button in the chrome rather than to something
// on the drawing: under the button, kept inside the stage.
function underButton(card, btn) {
  const b = btn.getBoundingClientRect();
  const w = card.offsetWidth || 300, h = card.offsetHeight || 220;
  card.style.position='fixed';
  card.style.left = clamp(b.left, 8, Math.max(8, innerWidth - w - 8)) + "px";
  card.style.top = clamp(b.bottom + 6, 8, Math.max(8, innerHeight - h - 8)) + "px";
}
// leaving a field must hand the keyboard back, or Delete goes on being
// swallowed by an input nobody is looking at any more
function toCanvas() { if (!S.present) canvas.focus({preventScroll: true}); }

pop.addEventListener("change", async (e) => {
  if(e.target.hasAttribute('data-route-point')){
    const raw=e.target.value,value=Number(raw),sel={...S.sel},index=Number(e.target.dataset.routePoint),axis=Number(e.target.dataset.axis);
    if(!raw.trim()||!Number.isFinite(value)){e.target.setCustomValidity('Enter a finite coordinate.');e.target.reportValidity();return;}
    e.target.setCustomValidity('');
    await commitTopology(mutationProposal(()=>{element(sel).via[index][axis]=value;}),sel);return;
  }
  const f = e.target.dataset.field;
  if (!f || !S.sel) return;
  if(S.sel.role==='branch' && ['count','arrangement'].includes(f)) {updateGroupDraft(f,e.target.value);return;}
  applyField(S.sel, f, e.target.value);
});
pop.addEventListener("input", (e) => {
  const f = e.target.dataset.field;
  if(f==='count' && S.sel?.role==='branch') {updateGroupDraft(f,e.target.value);return;}
  if (!f || !S.sel || e.target.tagName !== "INPUT" || e.target.type !== "text") return;
  if (f === "id") return;  // ids rename on change, not per keystroke
  applyField(S.sel, f, e.target.value, true);
});
pop.addEventListener("keydown", (e) => {
  if(groupDraft && ['Enter','Escape'].includes(e.key)) {e.preventDefault();e.stopPropagation();if(e.key==='Escape') cancelGroupDraft();else applyGroupDraft();return;}
  // The card is a card over the drawing, and the moment a component most
  // wants turning is the moment its card is open -- right after the drop
  // that made it, with the caret parked in the label box. The turn keys
  // therefore reach the drawing from inside the card, where every other
  // shortcut correctly does not: `f`, `d`, `z` and `p` are letters someone
  // is trying to type into a name, and a bracket is not. Without this the
  // keys were dead in the one place they were wanted, and the reader who
  // pressed `]` on a freshly dropped path got a `]` in its label.
  if ((e.key === "[" || e.key === "]") && S.sel && !["INPUT","TEXTAREA","SELECT"].includes(e.target.tagName)) {
    e.preventDefault(); e.stopPropagation();
    turnSelected(e.key === "]" ? 1 : -1);
    return;
  }
  // the card handles its own keys and says so: the document's Escape
  // chain would otherwise find the card already shut and go on to close
  // whatever is behind it
  if (e.key === "Enter" && e.target.tagName === "INPUT") {
    if (pop.dataset.rename) return;
    e.preventDefault(); e.stopPropagation(); e.target.blur(); closePopover(); toCanvas();
  }
  if (e.key === "Escape") { e.stopPropagation(); closePopover(); toCanvas(); }
});
pop.addEventListener("click", (e) => {
  if(e.target.dataset.act==="delete-selection"){removeSelected();return;}
  if(e.target.dataset.act==="auto-label") { edit(()=>{const el=element(S.sel);delete el.label_offset;if('side' in el) el.side='auto';}); return; }
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
  if (act.startsWith('disconnect-')) {
    const proposal=mutationProposal(()=>{const data=S.data;
      for (const end of act === 'disconnect-both' ? ['from','to'] : [act.slice(11)])
        replaceDocument(data,detachEndpoint(data,sel.role,sel.index,end).document);
    });commitTopology(proposal,sel).then(ok=>{if(ok)openPopover(sel);});return;
  }
  if (act === "delete") { commitTopology(mutationProposal(()=>removeElement(sel)),null); return; }
  if (act === "connect") { startConnect(el.id, "link"); return; }
  if (act === "swap") { edit(() => { [el.from, el.to] = [el.to, el.from]; if(el.via) el.via.reverse(); if(el.angle != null) el.angle=(el.angle+180)%360; }); openPopover(sel); return; }
  if (act === "unpin") { edit(() => { delete el.at; });openPopover(sel);return; }
  if (act === "via-add") {
    closePopover();setMode('place',{role:'node',kind:'free',branchIndex:sel.index,name:'Junction'});
    toast('Click a connection lead to add a connected junction. Escape cancels.');
    return;
  }
  if (act === "via-del") { edit(() => { el.via.splice(+e.target.dataset.i, 1); if (!el.via.length) delete el.via; }); openPopover(sel); return; }
});

// A field edit while typing coalesces into one undo step per field.
let typing = null;
function applyField(sel, f, raw, live = false) {
  if(sel.role==='source' && f==='value' && Number.isFinite(Number(raw)) && Number(raw)<0 && !(Number(element(sel)?.value)<0)) {toast('Use a positive magnitude and choose the source direction.');return;}
  if(sel.role==='branch' && f==='value' && element(sel)?.derivation) {toast('Edit the physical inputs or switch the derivation to Manual value.');return;}
  if(sel.role==='volume' && f==='storage' && element(sel)?.storage_relation) {toast('Edit the storage relation or switch to Manual storage power.');return;}
  if(f==='symbol-position') {
    const hit=symbolHit(sel);
    edit(()=>{const el=element(sel);if(raw==='automatic')delete el.at;else if(hit)el.at=[...hit.at];});
    openPopover(sel);return;
  }
  if(sel.role==='branch' && f==='angle' && raw!=='') {
    if(!Number.isFinite(Number(raw))) {toast('Enter a finite angle.');return;}
    turnBranch(sel,element(sel),0,((Number(raw)%360)+360)%360);return;
  }
  if(sel.role==='branch' && ['from','to'].includes(f) && raw===element(sel)[f==='from'?'to':'from']) {toast('Choose two different endpoint nodes.');openPopover(sel);return;}
  const value = raw === "" ? null : raw;
  const apply = (d) => {
    const e = element(sel);
  if (f === "id") {
      if(sel.role!=="node") {
        if(!value || list(sel.role).some(x=>x!==e && x.id===value)) return;
        const old=e.id;e.id=value;
        if(sel.role==='branch')for(const v of d.control_volumes||[])if(v.storage_relation?.branch===old)v.storage_relation.branch=value;
        if(old) for(const role of ["region","volume","surface","transfer","annotation"]) for(const obj of list(role)) {
          obj.links=(obj.links||[]).map(l=>l===`${sel.role}:${old}`?`${sel.role}:${value}`:l);
        }
        return;
      }
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

// JSON remains unit-declared. Numeric temperature state is independently held
// in Kelvin; changing display units never reparses a rounded drawing label.
const canonicalTemperatures=new Map();
function temperatureUnit(data=S.data) {const t=data.units?.T;return typeof t==='object'?t.unit:t;}
function temperatureScale(data=S.data) {return typeof data.units?.T==='object'?data.units.T.scale:null;}
function toKelvin(value,unit,scale) {
  const factor=['°F','F'].includes(unit)?5/9:1;
  if(scale==='rise')return value*factor;
  return unit==='K'?value:['°C','C'].includes(unit)?value+273.15:(value-32)*factor+273.15;
}
function fromKelvin(value,unit,scale) {
  if(scale==='rise')return value*(['°F','F'].includes(unit)?9/5:1);
  return unit==='K'?value:['°C','C'].includes(unit)?value-273.15:(value-273.15)*9/5+32;
}
function syncCanonicalTemperatures() {
  if(!S.data)return;
  const unit=temperatureUnit(),scale=temperatureScale(),ids=new Set();
  for(const n of S.data.nodes) {
    ids.add(n.id);const signature=JSON.stringify([n.value,unit,scale]);
    if(n.value==null || String(n.value).trim()==='' || !Number.isFinite(Number(n.value)) || !['K','°C','C','°F','F'].includes(unit)) {canonicalTemperatures.delete(n.id);continue;}
    if(canonicalTemperatures.get(n.id)?.signature!==signature)canonicalTemperatures.set(n.id,{kelvin:toKelvin(Number(n.value),unit,scale),signature});
  }
  for(const id of canonicalTemperatures.keys())if(!ids.has(id))canonicalTemperatures.delete(id);
}
let unitChangeSequence=0;
async function changeQuantityUnit(quantity,target) {
  const original=S.data,revision=S.revision,generation=S.generation,request=++unitChangeSequence;
  const data=structuredClone(original),said=data.units?.[quantity],source=typeof said==='object'?said.unit:said;
  if(source===target)return;
  const fields=[];
  if(quantity==='T')for(const n of data.nodes)fields.push([n,'value']);
  for(const b of data.branches) {
    const kind=b.kind||'cond',q=kind==='cap'?'C':kind==='flow'?'q':['link','break','stream'].includes(kind)?null:'R';
    if(q===quantity)fields.push([b,'value']);
    if(quantity==='q')fields.push([b,'rate']);
    if(['mdot','cp'].includes(quantity))fields.push([b,quantity]);
  }
  for(const s of data.sources) {const q=!s.kind||s.kind==='diss'?'P':s.kind==='flux'?'q″':'q';if(q===quantity)fields.push([s,'value']);}
  try {
    await rpc.call('physics_convert',1,source||target,target,quantity,temperatureScale(data));
    for(const [object,field] of fields) {
      if(object[field]==null || object[field]==='')continue;
      if(!Number.isFinite(Number(object[field])))throw Error('Convert or remove symbolic values before changing this unit. The diagram is unchanged.');
      if(quantity==='T') {
        const canonical=canonicalTemperatures.get(object.id);
        if(!canonical)throw Error('The source temperature unit must be specified before conversion.');
        object[field]=fromKelvin(canonical.kelvin,target,temperatureScale(data));
      } else object[field]=await rpc.call('physics_convert',object[field],source,target,quantity,temperatureScale(data));
      if(!Number.isFinite(object[field]))throw Error('Conversion exceeded the numeric range.');
    }
    if(request!==unitChangeSequence || revision!==S.revision || generation!==S.generation)return;
    data.units||={};data.units[quantity]=typeof said==='object'?{...said,unit:target}:target;
    if(quantity==='T')for(const n of data.nodes) {
      const entry=canonicalTemperatures.get(n.id);if(entry)entry.signature=JSON.stringify([n.value,target,temperatureScale(data)]);
    }
    edit(d=>replaceDocument(d,data));
    pop.querySelector('[data-unit-error]')?.replaceChildren();
  }catch(error){const slot=pop.querySelector('[data-unit-error]');if(slot)slot.textContent=error.message;else toast(error.message);}
}

// ------------------------------------------------------------- diagram
$("ed-settings").addEventListener("click", () => {
  if(groupDraft){gateGroup(()=>$('ed-settings').click());return;}
  select(null);
  const d = S.data, u = d.units || {};
  const T = typeof u.T === "object" && u.T ? u.T : {unit: u.T || "", scale: ""};
  // The diagram's name is not here. It is the one in the top bar, which
  // names the file and, when the reader says so, is drawn on the page:
  // two boxes for one name was the confusion this card used to carry.
  let h = `<h4>Units</h4>`+field('Number display',selectBox('display-mode',S.file.display?.mode||'automatic',['automatic','scientific'],{automatic:'Automatic prefixes',scientific:'SI units + scientific notation'}));
  for (const q of ["R", "C", "P", "q", "q″"]) h += field(`Unit of ${q}`, text(`unit:${q}`, u[q], q === "R" ? "K/W" : ""));
  // A stream states these two, and without them here the branch card asked
  // for a mass flow that validation then refused for having no unit, with
  // nowhere in the editor to give it one.
  h += field(`Unit of ṁ`, text("unit:mdot", u.mdot, "kg/s"));
  h += field(`Unit of <i>c</i><sub>p</sub>`, text("unit:cp", u.cp, "kJ/kg·K"));
  h += field("Temperature",selectBox('unit:T',T.unit,['°C','°F','K']));
  h += `<details><summary>Advanced temperature settings</summary>`+field("Temperature meaning", selectBox("scale", T.scale || "", ["", "absolute", "rise"], {"": "Unspecified (legacy)",absolute:'Actual temperature',rise:'Temperature difference'}))+`<p>Actual temperature: 32 °F = 273.15 K. A difference of 18 °F = 10 K. Unspecified retains the file’s original meaning.</p></details>`;
  h += `<p data-unit-error role="alert"></p>`;
  h += `<button type="button" data-assignment-open>Physics and document options…</button>`;
  pop.innerHTML = h;
  pop.hidden = false;
  underButton(pop, $("ed-settings"));
  S.sel = null;
});
pop.addEventListener("change", async (e) => {
  const f = e.target.dataset.field;
  if (!f || S.sel) return;
  const value = e.target.value === "" ? null : e.target.value;
  if(f==='display-mode') {S.file.display={mode:value};save();refresh();return;}
  if(f.startsWith('unit:') && value) {await changeQuantityUnit(f.slice(5),value);return;}
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
  cancelGesture();
  const generation=S.generation,revision=S.revision;
  const out = await rpc.call("solve", S.data);
  if(generation!==S.generation || revision!==S.revision) return;
  if (out.error) { showError(out.error); return; }
  edit((d) => { for(const n of d.nodes) if(!n.at) n.at=out.nodes.find(s=>s.id===n.id)?.at; });
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
    if (e) { e.updated = Date.now(); e.name = S.file.name; e.topologyVersion=S.file.topologyVersion;e.display=S.file.display; } else ix.unshift({...S.file, updated: Date.now()});
    writeIndex(ix);
    localStorage.setItem(STORE.last, S.file.id);
  } catch (err) {
    toast("Could not save: the browser's storage is full or blocked.");
  }
}

function showFile() {
  openFindings(false);
  if(solveSession && sessionDirty()) toast("Temporary solve changes discarded when switching files.");
  closeAnalysis(true);
  physicsReview = null;
  cancelGesture(); S.generation++; S.revision=0;
  S.undo.length = 0; S.redo.length = 0;
  const original = snapshot(), normalized = S.file.topologyVersion===1 ? {document:S.data,conflicts:[]} : normalizeOverlaps(S.data);
  if (JSON.stringify(normalized.document) !== original) {
    S.undo.push(original); S.data = normalized.document; save();
  }
  if (normalized.conflicts.length) toast([...new Set(normalized.conflicts)].join(' '));
  S.file.topologyVersion=1;save();
  canonicalTemperatures.clear();syncCanonicalTemperatures();
  S.scene = null;
  select(null);
  setMode("idle");
  updateChrome();
  drawing.innerHTML = ""; hitsG.innerHTML = "";
  S.touched = false;
  S.needsFit = true;
  refresh();
  renderFiles();
}

function completeEditorDefaults(data) {
  for(const key of Object.values(COLLECTION)) if(!data[key]) data[key]=[];
  for(const [key,size] of [["regions",[200,120]],["control_volumes",[240,160]]]) for(const r of data[key]) {
    r.at ||= [0,0];r.size ||= [...size];
  }
  for(const a of data.annotations) {a.at ||= [0,0];a.end ||= [100,0];}
  for(const s of data.control_surfaces) {s.edge ||= "right";s.start ??= .25;s.end ??= .75;}
}

function newFile(name, data) {
  if(groupDraft) {gateGroup(()=>newFile(name,data));return;}
  cancelGesture();
  completeEditorDefaults(data);
  const id = Math.random().toString(36).slice(2, 10);
  S.file = {id, name};
  S.data = ensureStreamUnits(data);
  save();
  showFile();
}

function openFile(id) {
  if(groupDraft) {gateGroup(()=>openFile(id));return false;}
  cancelGesture();
  const raw = localStorage.getItem(STORE.file(id));
  const ix = readIndex().find((f) => f.id === id);
  if (!raw || !ix) return false;
  S.file = {id, name: ix.name, topologyVersion:ix.topologyVersion,display:ix.display};
  S.data = ensureStreamUnits(JSON.parse(raw));
  completeEditorDefaults(S.data);
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
  if(groupDraft){gateGroup(()=>renameFile(id,anchor));return;}
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
  if (!name) {let error=pop.querySelector('[data-rename-error]');if(!error){error=document.createElement('p');error.dataset.renameError='';error.setAttribute('role','alert');pop.appendChild(error);}error.textContent='Enter a diagram name.';pop.querySelector('[data-rn="name"]').focus();return;}
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
  requestAnimationFrame(sizeFiles);
}
$("ed-files").addEventListener("click", (e) => {
  const li = e.target.closest("li"); if (!li) return;
  const id = li.dataset.id;
  if (e.target.dataset.act === "more") {
    const r = e.target.getBoundingClientRect(), st = $("ed-stage").getBoundingClientRect();
    menu.innerHTML = `<button data-f="rename">Rename</button><button data-f="dup">Make a copy</button><hr><button data-f="del" class="ed-danger">Delete</button>`;
    menu.dataset.file = id;
    menu.hidden = false;
    underButton(menu,e.target);
    return;
  }
  openFile(id); closeFiles();
});
$("ed-new").addEventListener("click", () => { newFile("Untitled", BLANK()); closeFiles(); });
async function loadExamples() {
  const ul=$('ed-examples');
  if(ul.children.length)return;
  try {
    const response=await fetch('examples.json');if(!response.ok)throw new Error('Could not load examples');
    exampleCatalog=await response.json();
    ul.innerHTML=exampleCatalog.map(e=>`<li data-path="${escapeHtml(e.path)}"><button type="button">${escapeHtml(e.title)}</button><small>${escapeHtml(e.description)}</small></li>`).join('');
  } catch(error){toast(error.message);}
}
$('ed-open-example').addEventListener('click',async()=>{
  const ul=$('ed-examples');ul.hidden=!ul.hidden;
  $('ed-open-example').setAttribute('aria-expanded',String(!ul.hidden));
  if(!ul.hidden)await loadExamples();
});
$("ed-examples").addEventListener("click", async (e) => {
  const li = e.target.closest("li[data-path]"); if (!li) return;
  if(groupDraft){gateGroup(()=>li.querySelector('button').click());return;}
  cancelGesture();const generation=++S.generation,revision=S.revision;
  const data = await (await fetch(li.dataset.path)).json();
  if(generation!==S.generation || revision!==S.revision) return;
  newFile(data.title ? data.title.slice(0, 60) : li.textContent, data);
  const catalog=exampleCatalog;
  if(S.data.title===data.title) {
    const entry=catalog.find(e=>e.path===li.dataset.path);
    if(entry) {pop.innerHTML=`<h4>${escapeHtml(entry.title)}</h4><p>${escapeHtml(entry.description)}</p><ol>${entry.exercises.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ol>`;pop.hidden=false;underButton(pop,$('ed-open-example'));}
  }
  closeFiles();
});
$("ed-import").addEventListener("change", async (e) => {
  const f = e.target.files[0]; if (!f) return;
  cancelGesture();const generation=++S.generation,revision=S.revision;
  try {
    const data = JSON.parse(await f.text());
    if(generation!==S.generation || revision!==S.revision) return;
    newFile(f.name.replace(/\.json$/i, ""), data);
    closeFiles();
  } catch { toast("That file is not JSON."); }
  e.target.value = "";
});
// on a narrow screen the files panel is an overlay
const filesPanel = $("ed-files-panel");
let fileSizing;
try {fileSizing=JSON.parse(localStorage.getItem('thermodraw:files-sizing')||'{}');} catch {fileSizing={};}
function sizeFiles() {
  const width=window.innerWidth;
  const right=document.body.classList.contains('ed-components-collapsed')?0:360;
  const overlay=width-right-480<220;
  if(document.body.classList.contains('ed-files-overlay')!==overlay) document.body.classList.toggle('ed-files-overlay',overlay);
  const cap=overlay?Math.min(640,width-32):Math.max(0,Math.min(640,width*.4,width-right-480));
  const sample=$('ed-files').querySelector('.ed-fname');
  const measure=document.createElement('canvas').getContext('2d');
  measure.font=sample?getComputedStyle(sample).font:getComputedStyle(filesPanel).font;
  const longest=Math.max(180,...readIndex().map(f=>measure.measureText(f.name).width+76));
  const desired=fileSizing.mode==='manual'?fileSizing.width:longest;
  document.body.style.setProperty('--files-width',Math.min(cap,Math.max(180,desired))+'px');
}
function collapseFiles(on) {
  document.body.classList.toggle('ed-files-collapsed',on);
  $('ed-files-reopen').hidden=!on;
}
const reopenFiles=document.createElement('button');reopenFiles.id='ed-files-reopen';reopenFiles.textContent='Files';reopenFiles.hidden=true;
reopenFiles.onclick=()=>{collapseFiles(false);filesPanel.classList.add('ed-open');};document.body.appendChild(reopenFiles);
const resizeFiles=document.createElement('div');resizeFiles.className='ed-files-resizer';resizeFiles.tabIndex=0;resizeFiles.setAttribute('role','separator');resizeFiles.setAttribute('aria-label','Resize Files panel');
resizeFiles.setAttribute('aria-orientation','vertical');filesPanel.appendChild(resizeFiles);
const resetFiles=document.createElement('button');resetFiles.textContent='Reset to automatic';resetFiles.onclick=()=>{fileSizing={mode:'automatic'};localStorage.setItem('thermodraw:files-sizing',JSON.stringify(fileSizing));sizeFiles();};filesPanel.appendChild(resetFiles);
resizeFiles.onpointerdown=e=>{resizeFiles.setPointerCapture(e.pointerId);};
resizeFiles.onpointermove=e=>{if(!resizeFiles.hasPointerCapture(e.pointerId))return;fileSizing={mode:'manual',width:Math.max(180,e.clientX-filesPanel.getBoundingClientRect().left)};sizeFiles();};
resizeFiles.onpointerup=e=>{resizeFiles.releasePointerCapture(e.pointerId);localStorage.setItem('thermodraw:files-sizing',JSON.stringify(fileSizing));};
resizeFiles.onkeydown=e=>{if(!['ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();fileSizing={mode:'manual',width:filesPanel.getBoundingClientRect().width+(e.key==='ArrowRight'?10:-10)};localStorage.setItem('thermodraw:files-sizing',JSON.stringify(fileSizing));sizeFiles();};
window.addEventListener('resize',sizeFiles);document.fonts.ready.then(sizeFiles);
new MutationObserver(sizeFiles).observe(document.body,{attributes:true,attributeFilter:['class']});
function closeFiles() { filesPanel.classList.remove("ed-open"); }
$("ed-files-toggle").addEventListener("click", () => filesPanel.classList.toggle("ed-open"));
$("ed-files-close").addEventListener("click", ()=>{closeFiles();collapseFiles(true);});
$("ed-file").addEventListener("click", () => { if (S.file) renameFile(S.file.id, $("ed-file")); });

// ---------------------------------------------------------------- menus
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
  const ids = ["ed-delete", null, "ed-fit", "ed-auto-labels", "ed-notation", "ed-theme",
               "ed-present", null, "ed-sketch", "ed-analysis", "ed-settings", "ed-share", "ed-export"];
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
  cancelGesture();
  const base = (S.file ? S.file.name : "diagram").replace(/[^\w.-]+/g, "-");
  try {
    if(x==="document") {
      const generation=S.generation,revision=S.revision;
      const cropped={...S.data};delete cropped.size;
      const svg=await rpc.call("export",cropped,"svg","light",S.notation);
      if(generation!==S.generation || revision!==S.revision) return;
      pop.innerHTML='<h4>Export for document</h4><div id="ed-document-preview"></div><div class="ed-row"><button id="ed-save-svg">Save SVG</button><button id="ed-save-png">Save PNG</button></div>';
      // An image isolates the export's styles from the editor's dark canvas.
      const picture=new Image();picture.alt="Cropped light diagram export";
      picture.src="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
      picture.style.cssText="width:100%;height:auto;background:#fff";
      $("ed-document-preview").appendChild(picture);
      $("ed-save-svg").onclick=()=>download(`${base}-light.svg`,svg,"image/svg+xml");
      $("ed-save-png").onclick=async()=>download(`${base}-light.png`,await rasterise(svg,2,"light"),"image/png");
      pop.hidden=false;underButton(pop,$("ed-export"));return;
    }
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
  cancelGesture();
  showExportDialog();
});

async function showExportDialog() {
  document.getElementById('ed-export-dialog')?.remove();
  const dialog=document.createElement('dialog');dialog.id='ed-export-dialog';dialog.setAttribute('aria-labelledby','ed-export-title');
  dialog.innerHTML='<h3 id="ed-export-title">Export</h3><label>Output <select data-export-output><option value="image">Image for documents</option><option value="page">HTML page with controls</option><option value="json">JSON, the raw diagram data</option></select></label><div data-export-image><label>Format <select data-export-format><option>SVG</option><option>PNG</option></select></label><label>Theme <select data-export-theme><option value="light">Light</option><option value="dark">Dark</option><option value="auto">Follow light and dark</option></select></label><label>Resolution <select data-export-resolution><option value="1">1×</option><option value="2" selected>2×</option><option value="4">4×</option></select></label><div data-export-preview></div></div><p data-export-error role="alert"></p><div class="ed-row"><button data-export-save disabled>Save SVG</button><button data-export-close>Close</button></div>';
  document.body.appendChild(dialog);dialog.showModal();
  const data=structuredClone(S.data),display=structuredClone(S.file?.display||{mode:'automatic'}),notation=S.notation;
  const base=(S.file?.name||'diagram').replace(/[^\w.-]+/g,'-');
  let sequence=0,svg=null;
  const get=name=>dialog.querySelector(`[data-export-${name}]`);
  async function preview() {
    const token=++sequence,output=get('output').value;svg=null;get('save').disabled=true;get('error').textContent='';
    get('image').hidden=output!=='image';get('save').textContent='Save '+(output==='image'?get('format').value:output==='page'?'HTML':'JSON');
    get('resolution').closest('label').hidden=get('format').value!=='PNG';
    if(output!=='image'){get('save').disabled=false;return;}
    try {
      const theme=get('theme').value,cropped={...data};delete cropped.size;
      const effectiveTheme=theme==='auto'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):theme;
      get('preview').style.background=effectiveTheme==='dark'?'#0f1115':'#ffffff';
      get('preview').style.colorScheme=effectiveTheme;
      const content=await rpc.call('export',cropped,'svg',theme==='auto'?null:theme,notation,display);
      if(token!==sequence || !dialog.open)return;
      svg=content;const image=new Image();image.alt='Export preview';image.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);get('preview').replaceChildren(image);get('save').disabled=false;
    }catch(error){if(token===sequence)get('error').textContent=error.message;}
  }
  dialog.onchange=preview;get('close').onclick=()=>dialog.close();dialog.onclose=()=>{sequence++;dialog.remove();};
  get('save').onclick=async()=>{
    try {
      const output=get('output').value;
      if(output==='json')download(base+'.json',await rpc.call('export',data,'json'),'application/json');
      else if(output==='page')download(base+'.html',await rpc.call('export',data,'page',null,notation,display),'text/html');
      else if(svg && get('format').value==='SVG')download(base+'.svg',svg,'image/svg+xml');
      else if(svg)download(base+'.png',await rasterise(svg,Number(get('resolution').value),get('theme').value),'image/png');
    }catch(error){get('error').textContent=error.message;}
  };
  preview();
}

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
      const dark=mode==='dark' || mode==='auto' && matchMedia('(prefers-color-scheme: dark)').matches;
      g.fillStyle = dark ? "#0f1115" : "#ffffff"; g.fillRect(0, 0, w, h);
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
  cancelGesture();
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
  if(groupDraft){gateGroup(()=>setPresent(on));return;}
  cancelGesture();
  if(on && !S.present)S.presentState={view:{...S.view},touched:S.touched,filesOpen:filesPanel.classList.contains('ed-open')};
  S.present = on;
  document.body.classList.toggle("ed-present", on);
  closePopover(); closeQuick(); closeMenu(); closeFiles(); setHelp(false);
  const lbl = $("ed-present-label");
  lbl.hidden = !on;
  lbl.textContent = on ? ((S.data && S.data.title) || (S.file && S.file.name) || "") : "";
  if (on && document.fullscreenEnabled && !document.fullscreenElement) document.documentElement.requestFullscreen().then(()=>{if(S.present)fit();else if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});}).catch(() => {if(S.present)fit();});
  if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
  requestAnimationFrame(()=>requestAnimationFrame(()=>{
    if(S.present){S.touched=false;fit();}
    else if(S.presentState){S.touched=S.presentState.touched;setView(S.presentState.view);filesPanel.classList.toggle('ed-open',S.presentState.filesOpen);S.presentState=null;}
  }));
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
  const dialog=$("ed-help-panel");dialog.hidden=!on;
  if(on&&!dialog.open)dialog.showModal();else if(!on&&dialog.open)dialog.close();
  $("ed-help").setAttribute("aria-expanded", String(on));
}
$("ed-help").addEventListener("click", () => setHelp($("ed-help-panel").hidden));
$("ed-help-panel").addEventListener('cancel',()=>setHelp(false));
$("ed-help-close").addEventListener("click", () => setHelp(false));

// ---------------------------------------------------------- optional quick start
// Explanations only: never create files or require a gesture to advance.
let tour = null;
const TOUR = [
  {at:()=>$("ed-sketch"),title:"1. Build a diagram",
   text:"Open <b>Components</b>. Click a part, then click the drawing to place it. Drag a path endpoint onto a node to connect it. Use <b>Physical</b> for rectangles and control volumes.<br><br>To start with a complete drawing, open <b>Files → Example</b>."},
  {at:()=>$("ed-canvas"),title:"2. Edit the drawing",
   text:"Click an object to edit its label and values beside it. Drag the object to move it. Drag its label to reposition the text.<br><br><b>Shift-click</b> selects several objects. <b>Undo</b> reverses an edit; <b>Escape</b> cancels a drag."},
  {at:()=>$("ed-analysis").getBoundingClientRect().width ? $("ed-analysis") : $("ed-more"),title:"3. Check or solve",
   text:"Open <b>Solve physics</b>. Values already in the drawing start as known.<br><br>Use <b>Check supplied values</b> to check the numbers. To calculate a value, mark it <b>Unknown</b>. The panel explains any missing inputs or unsupported case.<br><br>Overrides are temporary. Only <b>Apply changes</b> writes the reviewed result to your drawing."},
  {at:()=>$("ed-export").getBoundingClientRect().width ? $("ed-export") : $("ed-more"),title:"4. Export the figure",
   text:"Open <b>Export</b> for a cropped SVG or PNG, or save JSON to edit later. The export uses saved drawing values, not temporary Solve overrides.<br><br>Your files stay in this browser. Export JSON to keep a separate copy. On a narrow screen, Solve and Export are under <b>…</b>."}
];
function tourRunning() {return tour!==null;}
function startTour() {
  setHelp(false);closePopover();closeMenu();
  tour={step:0};drawTour();$("ed-tour").querySelector('[data-tour="next"]').focus({preventScroll:true});
}
function tourCheck() {} // Document edits do not advance an introduction.
function drawTour() {
  const card=$("ed-tour");if(!tour) {card.hidden=true;return;}
  const step=TOUR[tour.step],last=tour.step===TOUR.length-1;
  card.innerHTML=`<p class="ed-tour-n">Quick start · ${tour.step+1} of ${TOUR.length}</p><h3>${step.title}</h3><p>${step.text}</p><div class="ed-row"><button type="button" data-tour="back" ${tour.step===0?'disabled':''}>Back</button><button type="button" data-tour="next">${last?'Done':'Next'}</button><button type="button" data-tour="end">Close</button></div>`;
  card.hidden=false;
  document.querySelectorAll('.ed-tour-mark').forEach(n=>n.classList.remove('ed-tour-mark'));
  const target=step.at();if(target && target!==canvas) target.classList.add('ed-tour-mark');
  const stage=$("ed-stage").getBoundingClientRect();
  card.style.left=clamp(stage.left+20,8,Math.max(8,innerWidth-card.offsetWidth-8))+'px';
  card.style.top=clamp(stage.top+20,8,Math.max(8,innerHeight-card.offsetHeight-8))+'px';
}
function endTour() {
  tour=null;$("ed-tour").hidden=true;
  document.querySelectorAll('.ed-tour-mark').forEach(n=>n.classList.remove('ed-tour-mark'));
  $("ed-help").focus({preventScroll:true});
}
$("ed-tour").addEventListener('click',e=>{
  const action=e.target.dataset.tour;if(!action||!tour) return;
  if(action==='end'||action==='next'&&tour.step===TOUR.length-1) {endTour();return;}
  tour.step+=action==='back'?-1:1;drawTour();
  $("ed-tour").querySelector(`[data-tour="${action}"]`).focus({preventScroll:true});
});
$("ed-take-tour").addEventListener('click',startTour);
$("ed-empty-start").addEventListener('click',startTour);
addEventListener('resize',()=>{if(tour) drawTour();});

// ----------------------------------------------------------------- chrome
function updateChrome() {
  for(const b of document.querySelectorAll('#ed-panel-views button'))if(b.textContent==='Properties')b.disabled=!S.sel;
  $("ed-file").textContent = S.file ? S.file.name : "Untitled";
  $("ed-undo").disabled = !S.undo.length;
  $("ed-redo").disabled = !S.redo.length;
  $("ed-delete").disabled = !S.sel;
  if($('ed-copy'))$('ed-copy').disabled=!S.sel;
  if($('ed-merge'))$('ed-merge').disabled=S.selection.filter(s=>s.role==='node').length<2;
  $("ed-notation").textContent = `Notation: ${S.notation}`;
  $("ed-notation").setAttribute("aria-pressed", String(S.notation === "zigzags"));
  $("ed-physics").checked = S.physics;
  $("ed-theme").textContent = `Theme: ${currentTheme()}`;
  document.title = `${S.file ? S.file.name : "Editor"} · ThermoDraw ${BUILD.version}`;
}
$("ed-undo").addEventListener("click", undo);
$("ed-redo").addEventListener("click", redo);
$("ed-delete").addEventListener("click", removeSelected);
function autoPositionAllLabels() {edit(d=>{for(const key of Object.values(COLLECTION)) for(const obj of d[key]||[]) {delete obj.label_offset;if('side' in obj) obj.side='auto';}});if(solveOpen) {startSolveSession();analysisPanel();}toast('All labels use automatic placement. Undo restores their positions.');}
$('ed-auto-labels').addEventListener('click',autoPositionAllLabels);
$("ed-fit").addEventListener("click", fitFromCommand);
$("ed-notation").addEventListener("click", () => {
  S.notation = S.notation === "boxes" ? "zigzags" : "boxes";
  updateChrome();
  refresh();
});
$("ed-physics").addEventListener("change", () => {
  S.physics = $("ed-physics").checked;
  refresh();
});
$('ed-findings-toggle').addEventListener('click',()=>{if(currentIssues[0])activateIssue(currentIssues[0]);});
$('ed-all-issues').addEventListener('click',()=>{delete $('ed-findings-toggle').dataset.closed;openFindings($('ed-findings-list').hidden);$('ed-all-issues').setAttribute('aria-expanded',String(!$('ed-findings-list').hidden));});

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
  const typingInField = ["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName) || e.target.isContentEditable;
  if (e.key === "Escape") {
    if(drag || cardDrag || S.preview) { cancelGesture(); clearGuides(); clearGhost(); clearTargets(); return; }
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
  if(S.present && ['ArrowLeft','ArrowRight'].includes(e.key)){stepFile(e.key==='ArrowRight'?1:-1);return;}
  const shortcut=SHORTCUTS.find(x=>x.match(e)&& (x.keys.includes('Mod')||!e.ctrlKey&&!e.metaKey&&!e.altKey));
  if(shortcut){e.preventDefault();shortcut.run(e);}

});

document.addEventListener("pointerdown", (e) => {
  if (!pop.hidden && !pop.classList.contains('ed-docked') && !pop.contains(e.target) && !e.target.closest('.ed-mini-picker') && !e.target.closest("#ed-hits") && !e.target.closest("#ed-ui")
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
    S.catalogue=m.head.units;installMiniPickers();
    S.ready = true;
    $("ed-loading").hidden = true;
    refresh();
    if(!S.touched) fit();
    // Quick start is optional; opening the editor never starts a tour.
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

// Explicit physics analysis uses the same inspector and document transactions.

function reconcileAnalysis() {
  const ids=new Set(S.data.nodes.map(n=>n.id));
  if(S.data.cases)S.data.cases=S.data.cases.map(g=>({...g,nodes:g.nodes.filter(n=>ids.has(n))})).filter(g=>g.nodes.length);
  if(S.data.layout_options?.starts)S.data.layout_options.starts=S.data.layout_options.starts.filter(n=>ids.has(n));
  const a=S.data?.analysis;if(!a) return;
  if(a.network) a.network.unknowns=(a.network.unknowns||[]).filter(id=>S.data.nodes.some(n=>n.id===id && (!n.kind || n.kind==="free")));
  for(const [id,t] of Object.entries(a.volumes||{})) {
    const v=(S.data.control_volumes||[]).find(v=>v.id===id);
    const tr=(S.data.transfers||[]).find(x=>x.id===t.id);
    const sf=tr && (S.data.control_surfaces||[]).find(x=>x.id===tr.surface);
    if(!v || (t.entity==="volume" && (t.id!==id || (t.field==="storage" && v.steady))) ||
       (t.entity==="transfer" && (!sf || sf.volume!==id || (t.field==="flux" && (tr.kind!=="heat" || tr.rate!=null)) || (t.field==="rate" && tr.flux!=null)))) delete a.volumes[id];
  }
}
const solvePanel=$('ed-solve-panel');
function solveSurface(id,tag='section') {
  const el=document.createElement(tag);el.id=id;el.className='ed-solve-float';el.hidden=tag!=='dialog';document.body.appendChild(el);return el;
}
const valueFloat=solveSurface('ed-solve-value');
valueFloat.setAttribute('aria-label','Edit physical value');
const valueNavigator=solveSurface('ed-solve-values');
valueNavigator.setAttribute('aria-label','Physical value navigator');
const solveToolbar=solveSurface('ed-solve-toolbar');solveToolbar.className='ed-solve-toolbar';
const solveClose=solveSurface('ed-solve-close','dialog');
solveClose.setAttribute('aria-labelledby','ed-close-title');
solveClose.innerHTML='<h3 id="ed-close-title">Discard this calculation?</h3><p>Your drawing will keep its saved values.</p><div class="ed-close-actions"><button data-session-keep autofocus>Keep editing</button><button data-session-discard>Discard and close</button></div>';
const solveEvent=e=>!!e.target.closest('#ed-solve-panel,.ed-solve-float,.ed-solve-toolbar');
function showSolveClose() {if(!solveClose.open) solveClose.showModal();solveClose.querySelector('[data-session-keep]').focus();}
function positionSolveFloat(el,row=null) {
  const area=canvas.getBoundingClientRect(),margin=8;
  el.style.width=Math.min(el===valueNavigator?520:330,window.innerWidth-16)+'px';
  // At narrow widths use an independent sheet above the bottom solve panel.
  el.style.maxHeight=Math.max(180,window.innerWidth<=820?window.innerHeight*.6:area.height-60)+'px';
  let x=area.left+margin,y=area.top+48;
  if(row && window.innerWidth>820) {
    const hit=(solveSession.scene||S.scene)?.hits.find(h=>h.role===row.role&&h.index===row.index&&h.element==='label');
    if(hit) {const pt=new DOMPoint(hit.bounds[2],hit.bounds[1]).matrixTransform(canvas.getScreenCTM());x=pt.x+12;y=pt.y;if(x+el.offsetWidth>area.right-margin) x=new DOMPoint(hit.bounds[0],hit.bounds[1]).matrixTransform(canvas.getScreenCTM()).x-el.offsetWidth-12;}
  }
  el.style.left=clamp(x,Math.max(8,area.left+8),Math.max(8,area.right-el.offsetWidth-8))+'px';
  const top=clamp(y,area.top+8,Math.max(area.top+8,window.innerHeight-el.offsetHeight-8));
  el.style.top=top+'px';el.style.maxHeight=Math.max(140,window.innerHeight-top-8)+'px';
}
function physicsUnits(r) {
  const q=r.quantity||r.field;
  const units={T:['K','°C','°F','C','F'],R:['K/W','K/kW'],P:['W','kW','mW'],q:['W','kW','mW'],rate:['W','kW','mW'],generation:['W','kW','mW'],storage:['W','kW','mW'],area:['m²','cm²','mm²'],flux:['W/m²','kW/m²','W/cm²'],'q″':['W/m²','kW/m²','W/cm²'],C:['J/K','kJ/K'],mdot:['kg/s','g/s'],cp:['J/kg·K','kJ/kg·K']};
  const kind=solveSession?.data.network_basis?.kind;
  if(['R','q','P'].includes(q)&&['area','length'].includes(kind)&&['branch','source'].includes(r.role)){const ref=kind==='area'?'m²':'m';return [...new Set([r.unit,...(q==='R'?[`K*${ref}/W`,`K*${ref}/kW`]:[`W/${ref}`,`kW/${ref}`])])];}
  return [...new Set([r.unit,...(units[q]||[])])];
}
function renderValueFloat() {
  const r=physicalValues().find(r=>r.key===solveValue);
  if(!solveOpen||!r||!solveSession.valueEditorOpen||solveSession.stale) {valueFloat.hidden=true;return;}
  const editing=solveSession.overrides.has(r.key),mode=r.unknown?'unknown':editing||r.overridden?'override':'known';
  const reason=unknownReason(r),siblings=physicalValues().filter(v=>v.role===r.role&&v.index===r.index);
  let h=`<div class="ed-panel-head"><h3>${escapeHtml(r.label)}</h3><button data-value-close aria-label="Close value editor">×</button></div>`;
  if(siblings.length>1) h+=`<label>Quantity <select data-value-quantity>${siblings.map(v=>`<option value="${v.key}" ${v.key===r.key?'selected':''}>${escapeHtml(v.field)}</option>`).join('')}</select></label>`;
  h+='<div class="ed-value-modes" role="group" aria-label="Use as">';
  for(const [key,label] of [['known','Known'],['unknown','Unknown'],['override','Override']]) h+=`<button data-physics-mode="${key}" aria-pressed="${mode===key}" ${key==='unknown'&&reason||key==='override'&&(r.locked||r.derived)?'disabled':''}>${label}</button>`;
  h+='</div>';
  if(reason) h+=`<p class="ed-value-restriction">${escapeHtml(reason)}</p>`;
  if(solveSession.notice) h+=`<p class="ed-physics-error" role="alert">${escapeHtml(solveSession.notice)}</p>`;
  if(!r.unknown) h+=`<label>Value <input data-physics-number aria-invalid="${!numericPhysics(r.value)}" value="${escapeHtml(r.value??'')}" ${r.locked||r.derived?'disabled':''} placeholder="Enter a number"></label>`;
  h+=`<label>Unit <select data-physics-unit ${r.locked||r.derived||r.unknown?'disabled':''}>${physicsUnits(r).map(u=>`<option ${u===r.unit?'selected':''}>${escapeHtml(u)}</option>`).join('')}</select></label>`;
  if(!r.unknown&&!numericPhysics(r.value)) h+='<p class="ed-physics-error">Enter a numeric value to use this input.</p>';
  if(r.overridden) h+=`<p>Saved: ${escapeHtml(fmtPhysics(r.original))} ${escapeHtml(r.unit)}</p>`;
  if(['branch','volume'].includes(r.role)) h+='<button data-scenario-derivation>Edit derivation inputs</button>';
  if(r.overridden||r.unknown) h+='<button data-session-reset-field>Restore saved value</button>';
  if(r.calculated) {h+=`<p class="ed-solve-success">✓ Calculated: ${fmtPhysics(r.calculated.value)} ${escapeHtml(r.unit)}</p>`;if(numericPhysics(r.original)) h+=`<p>Saved: ${fmtPhysics(r.original)} · Difference: ${fmtPhysics(r.calculated.value-Number(r.original))} ${escapeHtml(r.unit)}</p>`;}
  const changed=valueFloat.dataset.key!==r.key||valueFloat.hidden;
  const template=document.createElement('template');template.innerHTML=h;
  const head=template.content.querySelector('.ed-panel-head'),modes=template.content.querySelector('.ed-value-modes'),reset=template.content.querySelector('[data-session-reset-field]');
  head.remove();modes.remove();reset?.remove();
  if(!valueFloat.querySelector('.ed-value-fields')) {
    valueFloat.replaceChildren(head,modes);
    const fields=document.createElement('div');fields.className='ed-value-fields';valueFloat.appendChild(fields);
    const restore=document.createElement('button');restore.dataset.sessionResetField='';restore.textContent='Restore saved value';valueFloat.appendChild(restore);
  }
  // Keep action nodes and their positions stable through a value's blur commit.
  valueFloat.querySelector('h3').textContent=r.label;
  for(const button of modes.children) {
    const old=valueFloat.querySelector(`[data-physics-mode="${button.dataset.physicsMode}"]`);
    old.disabled=button.disabled;old.setAttribute('aria-pressed',button.getAttribute('aria-pressed'));
  }
  valueFloat.querySelector('.ed-value-fields').replaceChildren(template.content);
  valueFloat.querySelector('[data-session-reset-field]').hidden=!reset;
  valueFloat.hidden=false;valueFloat.dataset.key=r.key;if(changed) positionSolveFloat(valueFloat,r);
}
function openNavigator(filter='all') {
  solveValue=null;valueFloat.hidden=true;valueNavigator.hidden=false;
  valueNavigator.innerHTML=`<div class="ed-panel-head"><h3>Values</h3><button data-navigator-close aria-label="Close values">×</button></div><label>Search <input data-value-search type="search" placeholder="Component or quantity"></label><label>Show <select data-value-filter>${['all','eligible','known','unknown','overrides','problems'].map(f=>`<option value="${f}" ${f===filter?'selected':''}>${f[0].toUpperCase()+f.slice(1)}</option>`).join('')}</select></label><div data-value-rows></div>`;
  renderNavigator();valueNavigator.querySelector('input').focus();drawPhysicsValues();
}
function renderNavigator() {
  if(valueNavigator.hidden) return;
  const filter=valueNavigator.querySelector('[data-value-filter]').value,query=valueNavigator.querySelector('input').value.toLowerCase();
  const rows=physicalValues().filter(r=>[r.label,r.id,...(r.members||[])].join(' ').toLowerCase().includes(query)&&(filter==='all'||filter==='eligible'&&r.eligible||filter==='known'&&!r.unknown&&numericPhysics(r.value)||filter==='unknown'&&r.unknown||filter==='overrides'&&r.overridden||filter==='problems'&&(r.state==='Missing'||solveSession.assessment?.systems.some(s=>!['solved','balanced'].includes(s.status)&&(s.nodes.includes(r.id)||s.id==='volume:'+r.volume)))));
  valueNavigator.querySelector('[data-value-rows]').innerHTML='<table><thead><tr><th>Component</th><th>Quantity</th><th>Value</th><th>State</th></tr></thead><tbody>'+rows.map(r=>`<tr><td><button data-physics-value="${r.key}" aria-label="${escapeHtml(r.label)}">${escapeHtml(r.label.split(' · ').slice(0,-1).join(' · '))}</button></td><td>${escapeHtml(r.label.split(' · ').at(-1))}</td><td>${r.unknown&&!r.calculated?'?':escapeHtml(fmtPhysics(r.calculated?.value??r.value))} ${escapeHtml(r.unit)}</td><td data-state="${r.state.toLowerCase()}">${r.state}</td></tr>`).join('')+'</tbody></table>'+(!rows.length?'<p>No matching values.</p>':'');
  positionSolveFloat(valueNavigator);
}
function renderSolveToolbar() {
  solveToolbar.hidden=!solveOpen;if(!solveOpen) return;
  if(solveSession.help===undefined) {try {solveSession.help=!localStorage.getItem('thermodraw:solve-hint');}catch {solveSession.help=true;}}
  solveToolbar.innerHTML='<button data-values-open="all">Values</button><button data-auto-labels>Auto-position all labels</button><button data-solve-help aria-label="Solve help">? Help</button>'+(solveSession.help?'<div class="ed-solve-tip">Click a badge to change its state. Click a component to edit its value. <button data-help-dismiss aria-label="Dismiss solve hint">×</button></div>':'');
  const rect=canvas.getBoundingClientRect();solveToolbar.style.left=rect.left+8+'px';solveToolbar.style.top=rect.top+8+'px';
}
document.addEventListener('input',e=>{if(e.target.hasAttribute('data-value-search')) renderNavigator();});
const physicsMarks=svgEl('g',{'aria-label':'Physical values'},'ed-physics-marks');
canvas.appendChild(physicsMarks);
const fmtPhysics=x=>x==null?'—':Number.isFinite(Number(x))?Number(Number(x).toPrecision(5)).toLocaleString('en-US',{maximumSignificantDigits:5}):String(x);
function sessionChangeText(value,field) {
  if(field==='analysis') {const a=value||{};return [a.network?`Steady network: ${!!a.network.steady}; unknown temperatures: ${(a.network.unknowns||[]).join(', ')||'none'}`:'No network analysis',...Object.entries(a.volumes||{}).map(([id,t])=>`${id}: solve ${t.id} ${t.field}`)].join('; ');}
  return typeof value==='object'&&value!==null?JSON.stringify(value):String(value??'missing');
}
function sessionDirty() {return solveSession && (JSON.stringify(solveSession.data,physicsComparable)!==JSON.stringify(JSON.parse(solveSession.initial),physicsComparable) || !!physicsReview?.result.updates.length || solveSession.systems!==null);}
const physicsComparable=(key,value)=>numericPhysics(value)?Number(value):value;
const numericPhysics=v=>v!=null && String(v).trim()!=='' && Number.isFinite(Number(v));
function inferSolveInputs(d) {
  d.analysis||={};
  if(d.nodes.length) {
    d.analysis.network||={steady:false};
    d.analysis.network.unknowns=d.nodes.filter(n=>(!n.kind||n.kind==='free')&&!numericPhysics(n.value)).map(n=>n.id);
  }
  if(d.analysis.network?.resistance_unknowns) d.analysis.network.resistance_unknowns=d.analysis.network.resistance_unknowns.filter(t=>{const b=typeof t==='number'?d.branches[t]:d.branches.find(b=>b.id===t);return b&&!numericPhysics(b.value);});
  for(const [volume,t] of Object.entries(d.analysis.volumes||{})) {
    const obj=(t.entity==='volume'?d.control_volumes:d.transfers).find(o=>o.id===t.id);
    if(obj && numericPhysics(obj[t.field])) delete d.analysis.volumes[volume];
  }
}
function startSolveSession() {
  const base=JSON.parse(JSON.stringify(S.data));
  solveSession={base,data:JSON.parse(JSON.stringify(base)),generation:S.generation,documentRevision:S.revision,revision:0,overrides:new Set(),systems:null,stale:false,assessment:null};
  inferSolveInputs(solveSession.data);
  solveSession.initial=JSON.stringify(solveSession.data);
  physicsReview=null;solveValue=null;assessSession();
}
function restoreSessionValue(r) {
  if(r.role==='node' && r.members?.length>1) {
    for(const id of r.members) {
      const index=solveSession.data.nodes.findIndex(n=>n.id===id);
      if(index>=0)restoreSessionValue({...r,id,index,members:null,key:`node:${index}:${r.field}`});
    }
    solveSession.overrides.delete(r.key);return;
  }
  const obj=solveSession.data[COLLECTION[r.role]][r.index],original=solveSession.base[COLLECTION[r.role]][r.index];
  if(original[r.field]===undefined) delete obj[r.field];else obj[r.field]=original[r.field];
  solveSession.overrides.delete(r.key);
  const a=solveSession.data.analysis;
  if(r.role==='node' && a?.network) a.network.unknowns=(a.network.unknowns||[]).filter(id=>id!==r.id);
  else if(r.role==='branch' && a?.network) a.network.resistance_unknowns=(a.network.resistance_unknowns||[]).filter(t=>t!==(r.id||r.index));
  else if(r.unknown && r.volume && a?.volumes) delete a.volumes[r.volume];
}
function sessionEdit(fn) {
  if(!solveSession || solveSession.stale) return;
  fn(solveSession.data);solveSession.operation=null;solveSession.running=false;solveSession.unitError=false;solveSession.revision++;solveSession.assessment=null;solveSession.applyReview=false;physicsReview=null;physicsRequest++;
  analysisPanel();assessSession();
}
async function assessSession() {
  const session=solveSession,revision=session.revision,sequence=++assessmentSequence;
  try {
    const out=await rpc.call('physics_session',session.base,session.data,session.systems);
    if(session!==solveSession || session.stale || revision!==session.revision || sequence!==assessmentSequence) return;
    session.assessment=out;
    updateSolveStatus();
    // Avoid replacing a field while the user is typing; the next action renders it.
    if(!solvePanel.contains(document.activeElement)) analysisPanel(valueFloat.contains(document.activeElement));
  } catch(err) {if(session===solveSession && !session.stale) {session.assessment={systems:[],issues:[{message:String(err.message||err)}]};analysisPanel();}}
}
function physicalValues() {
  const d=solveSession?.data||S.data,a=d.analysis||{},rows=[];
  const add=(role,index,field,label,unit,quantity=null,eligible=false,reason='',volume=null,locked=false)=>{
    const obj=d[COLLECTION[role]][index],id=obj.id;
    const target=a.volumes?.[volume];
    const unknown=role==='branch'?field==='value'&&(a.network?.resistance_unknowns||[]).includes(id||index):role==='node'?(a.network?.unknowns||[]).includes(id):target?.id===id && target?.field===field;
    const entity=role==='branch'?'branch':role==='node'?'node':role==='volume'?'volume':'transfer';
    const calculated=(physicsReview?.result.updates||[]).find(u=>u.entity===entity && (role==='branch'?u.index===index:u.id===id) && u.field===field);
    const derived=role==='branch'&&field==='value'&&!!obj.derivation || role==='volume'&&field==='storage'&&!!obj.storage_relation;
    const value=locked?0:obj[field];
    const original=solveSession?.base[COLLECTION[role]]?.[index]?.[field];
    const overridden=numericPhysics(value)&&numericPhysics(original)?Math.abs(Number(value)-Number(original))>Number.EPSILON*8*Math.max(1,Math.abs(Number(original))):String(value??'')!==String(original??'');
    const numeric=value!=null && String(value).trim()!=='' && Number.isFinite(Number(value));
    rows.push({key:`${role}:${index}:${field}`,role,index,field,label,unit,quantity,eligible,reason,volume,locked,derived,id,value,
      state:calculated?'Calculated':unknown?'Unknown':!numeric?'Missing':overridden?'Override':'Known',unknown,calculated,original,overridden});
  };
  const unit=q=>typeof d.units?.[q]==='object'?d.units[q].unit:d.units?.[q]||'';
  const groups=idealTemperatureGroups(d);
  d.nodes.forEach((n,i)=>{
    const members=groups.get(n.id),stated=members.filter(x=>x.value!=null&&x.value!=='');
    const conflict=stated.some(x=>String(x.value)!==String(stated[0]?.value));
    const representative=members.find(x=>x.kind==='fixed')||stated[0]||members.find(x=>x.label)||members[0];
    if(!conflict && representative.id!==n.id)return;
    const eligible=members.every(x=>!x.kind||x.kind==='free');
    add('node',i,'value',`${nodeName(n.id,d)} · T`,unit('T'),'T',eligible,eligible?'Ideal-connected nodes share one temperature.':members.some(x=>x.kind==='fixed')?'Boundary temperature: this fixed node stays a boundary.':'Phase and break nodes are not supported by steady network solving.');
    rows.at(-1).members=conflict?[n.id]:members.map(x=>x.id);
  });
  d.branches.forEach((b,i)=>{
    const name=b.label||`${b.id||b.kind||"cond"} · ${b.from} → ${b.to}`;
    if(['break','link'].includes(b.kind)) return;
    if(b.kind==='stream') {for(const f of ['mdot','cp']) add('branch',i,f,`${name} · ${f}`,unit(f),f,false,'Stream solving is not supported. These are drawing inputs.');return;}
    const q=b.kind==='cap'?'C':b.kind==='flow'?'q':'R';
    add('branch',i,'value',`${name} · ${q}`,unit(q),q,q==='R',q==='R'?'Select Unknown to calculate this resistance from temperatures and independent heat rates.':q==='C'?'Capacitance has zero storage rate only under the steady-state assumption.':'Supply this value; this milestone solves temperatures, not network resistances or powers.');
    if(b.rate!=null) add('branch',i,'rate',`${name} · supplied rate`,unit('q'),'q',false,'This is a supplied rate assertion for the whole branch or repeated group.');
  });
  d.sources.forEach((s,i)=>{const q=s.kind==='diss'?'P':s.kind==='flux'?'q″':'q';add('source',i,'value',`${s.label||s.id||s.to||s.from} · ${q}`,unit(q),q,false,s.kind==='flux'?'Network flux has no physical area; use a control-surface transfer for flux analysis.':'Supply network power; it cannot be selected as an unknown.');});
  (d.control_volumes||[]).forEach((v,i)=>{add('volume',i,'generation',`${v.label||v.id} · generation`,v.unit||'W',null,true,'',v.id);add('volume',i,'storage',`${v.label||v.id} · storage`,v.unit||'W',null,!v.steady,v.steady?'Steady state fixes storage at zero.':'Storage is signed: positive means accumulation.',v.id,!!v.steady);});
  (d.transfers||[]).forEach((t,i)=>{
    const sf=(d.control_surfaces||[]).find(s=>s.id===t.surface),f=t.flux!=null?'flux':'rate';
    add('transfer',i,f,`${t.label||t.id} · ${f}`,f==='flux'?(t.flux_unit||'W/m²'):(t.unit||'W'),null,!!sf,sf?'Only one unknown per control volume.':'Attach this transfer to a control surface before solving.',sf?.volume);
  });
  (d.control_surfaces||[]).forEach((sf,i)=>{
    if(sf.area!=null || d.transfers.some(t=>t.surface===sf.id && t.flux!=null)) add('surface',i,'area',`${sf.label||sf.id} · area`,sf.area_unit||'m²',null,false,'Supply physical area explicitly; rectangle dimensions do not determine it.');
  });
  return rows;
}

function idealTemperatureGroups(data) {
  const parents=new Map(data.nodes.map(n=>[n.id,n.id]));
  const root=id=>{while(parents.get(id)!==id)id=parents.get(id);return id;};
  for(const b of data.branches)if(b.kind==='link'&&parents.has(b.from)&&parents.has(b.to))parents.set(root(b.to),root(b.from));
  const groups=new Map();for(const n of data.nodes){const id=root(n.id);if(!groups.has(id))groups.set(id,[]);groups.get(id).push(n);}
  return new Map(data.nodes.map(n=>[n.id,groups.get(root(n.id))]));
}
function setQuantityValue(data,row,value) {
  const objects=row.role==='node'?data.nodes.filter(n=>(row.members||[row.id]).includes(n.id)):[data[COLLECTION[row.role]][row.index]];
  for(const object of objects){if(value==='')delete object[row.field];else object[row.field]=value;}
}
function closeAnalysis(force=false) {
  if(!force && solveSession && sessionDirty()) {showSolveClose();return;}
  solveClose.close();valueFloat.hidden=true;valueNavigator.hidden=true;solveToolbar.hidden=true;
  solveSession=null;physicsReview=null;assessmentSequence++;
  solveOpen=false;solveValue=null;physicsRequest++;
  $('ed-component-tools').hidden=false; $('ed-solve-panel').hidden=true;setPanelView('Components',true);
  document.body.classList.remove('ed-solving');
  $('ed-analysis').setAttribute('aria-expanded','false');
  if(typeof physicsMarks!=='undefined') physicsMarks.replaceChildren();
  if(S.scene) {drawing.innerHTML=S.scene.parts;buildHits(S.scene.hits);}
}
function choosePhysics(key) {
  if(key!==solveValue && solveSession) solveSession.notice=null;
  solveValue=key;solveSession.valueEditorOpen=true;valueNavigator.hidden=true;analysisPanel();
}
function unknownReason(r) {
  if(r.derived) return 'This value is owned by a derivation. Switch to Manual value in derivation inputs before selecting Unknown.';
  if(!r.eligible) return r.reason||'This value must be supplied.';
  const other=solveSession.data.analysis?.volumes?.[r.volume];
  if(other && !(other.id===r.id && other.field===r.field)) return 'Only one unknown can be solved per control volume. Another value is unknown; make it known before choosing this one.';
  return '';
}
function setPhysicsUse(r,use) {
  const reason=use==='unknown'?unknownReason(r):'';
  if(reason) {solveSession.notice=reason;choosePhysics(r.key);return;}
  sessionEdit(d=>{
    d.analysis||={};solveSession.notice=null;
    if(use==='known') restoreSessionValue(r);
    if(use==='override') solveSession.overrides.add(r.key);
    if(r.role==='node') {
      d.analysis.network||={steady:false,unknowns:[]};
      const ids=new Set(d.analysis.network.unknowns||[]);
      for(const id of r.members||[r.id])if(use==='unknown') ids.add(id);else ids.delete(id);
      d.analysis.network.unknowns=[...ids];
    } else if(r.role==='branch') {
      d.analysis.network||={steady:false,unknowns:[]};const targets=new Set(d.analysis.network.resistance_unknowns||[]);if(use==='unknown') targets.add(r.id||r.index);else targets.delete(r.id||r.index);d.analysis.network.resistance_unknowns=[...targets];
    } else if(r.volume) {
      d.analysis.volumes||={};
      if(use==='unknown') d.analysis.volumes[r.volume]={entity:r.role==='volume'?'volume':'transfer',id:r.id,field:r.field};
      else if(r.unknown) delete d.analysis.volumes[r.volume];
    }
  });
}
function cyclePhysics(key) {
  const r=physicalValues().find(r=>r.key===key);if(!r || solveSession.stale) return;
  solveValue=key;
  if(r.locked) {solveSession.notice=r.reason;choosePhysics(key);return;}
  const next=r.unknown?'override':(r.overridden||solveSession.overrides.has(r.key))?'known':r.eligible?'unknown':'override';
  solveSession.valueEditorOpen=next==='override';
  setPhysicsUse(r,next);
  if(next==='override') choosePhysics(key);
  if(next==='override') valueFloat.querySelector('[data-physics-number]')?.focus({preventScroll:true});
}
function physicsBadgeText(value,group) {
  return (value.state==='Unknown'?'? ':value.state==='Known'?'✓ ':value.state==='Calculated'?'= ':value.state==='Override'?'~ ':'? ')+value.state+(group.length>1?' · '+value.field:'');
}
function solveAdornments() {
  const scale=unitsPerPixel(),groups=new Map();
  for(const r of physicalValues()) {const key=r.role+':'+r.index;if(!groups.has(key)) groups.set(key,[]);groups.get(key).push(r);}
  return [...groups.values()].map(group=>{
    const widths=group.map(r=>{const text=svgEl('text',{'font-size':11*scale,visibility:'hidden'});text.textContent=physicsBadgeText(r,group);physicsMarks.appendChild(text);const w=text.getComputedTextLength()+12*scale;text.remove();return w;});
    return {role:group[0].role,index:group[0].index,width:Math.max(...widths),height:group.length*21*scale};
  });
}
let solveLabelTimer=null;
function scheduleSolveLabels() {
  clearTimeout(solveLabelTimer);solveLabelTimer=setTimeout(()=>{if(solveOpen) renderSolveScene();},100);
}
async function renderSolveScene() {
  const session=solveSession;if(!session || session.stale || !S.scene) return;
  const key=session.revision+':'+S.notation+':'+unitsPerPixel().toFixed(4)+':'+JSON.stringify(physicsReview?.result.updates||[]);
  if(session.renderKey===key) return;session.renderKey=key;
  const data=JSON.parse(JSON.stringify(session.data));
  for(const r of physicalValues()) {
    if(r.calculated) data[COLLECTION[r.role]][r.index][r.field]=r.calculated.value;
    else if(r.unknown) data[COLLECTION[r.role]][r.index][r.field]='?';
  }
  try {
    const scene=await rpc.call('scene',data,S.notation,false,solveAdornments(),S.file?.display||{mode:'automatic'});
    if(session!==solveSession || session.stale || key!==session.renderKey) return;
    if(scene.error) return;
    session.scene=scene;
    let parts=scene.parts;
    for(const p of scene.preview||[]) {
      const r=physicalValues().find(r=>r.role===p.role&&r.index===p.index&&(r.unknown||r.overridden||r.calculated));
      if(p.element==='label'&&r) parts=parts.replace(p.markup,`<g class="ed-solve-label" data-state="${r.state.toLowerCase()}">${p.markup}</g>`);
    }
    drawing.innerHTML=parts;buildHits(scene.hits);drawPhysicsValues();
  } catch { /* Readiness reports invalid values; retain the last valid drawing. */ }
}
function drawPhysicsValues() {
  const focused=physicsMarks.contains(document.activeElement)?document.activeElement.closest('[data-physics-cycle]')?.dataset.physicsCycle:null;
  physicsMarks.replaceChildren();if(!solveOpen || !S.scene || solveSession?.stale) return;
  const rows=physicalValues(),scale=unitsPerPixel();
  const groups=new Map();
  for(const r of rows) {const k=`${r.role}:${r.index}`;if(!groups.has(k)) groups.set(k,[]);groups.get(k).push(r);}
  for(const group of groups.values()) {
    const r=group.find(r=>r.key===solveValue)||group.find(r=>r.state==='Missing'||r.state==='Unknown')||group[0];
    const scene=solveSession?.scene||S.scene;
    const hit=scene.hits.find(h=>h.role===r.role && h.index===r.index && h.element==='label')||scene.hits.find(h=>h.role===r.role && h.index===r.index);
    if(!hit) continue;
    const [x,y,x1,y1]=hit.bounds;
    const g=svgEl('g',{'data-physics-pick':r.key});
    const selected=group.some(v=>v.key===solveValue);
    g.appendChild(svgEl('rect',{x:x-3*scale,y:y-3*scale,width:x1-x+6*scale,height:y1-y+6*scale,rx:3*scale,'stroke-width':(selected?2:1)*scale},selected?'ed-physics-selected':'ed-physics-outline'));
    group.forEach((value,i)=>{
      const label=physicsBadgeText(value,group);
      const reservation=scene.adornments?.find(a=>a.role===value.role&&a.index===value.index);
      if(reservation && !reservation.clear) return;
      const w=reservation?.bounds[2]||(label.length*6+12)*scale;
      const left=(x+x1-w)/2,top=reservation?reservation.bounds[1]+i*21*scale:y-(group.length-i)*21*scale;
      const badge=svgEl('g',{'data-physics-pick':value.key,'data-physics-cycle':value.key,'data-state':value.state.toLowerCase(),role:'button',tabindex:0,'aria-label':`${value.label}: ${value.state}`});
      const title=svgEl('title',{});title.textContent=unknownReason(value)||'Click to cycle Known → Unknown → Override. Click the component to edit.';badge.appendChild(title);
      badge.appendChild(svgEl('rect',{x:left,y:top,width:w,height:17*scale,rx:3*scale},'ed-physics-badge'));
      const t=svgEl('text',{x:(x+x1)/2,y:top+12*scale,'text-anchor':'middle','font-size':11*scale});t.textContent=label;badge.appendChild(t);g.appendChild(badge);
    });
    physicsMarks.appendChild(g);
  }
  if(focused) physicsMarks.querySelector(`[data-physics-cycle="${focused}"]`)?.focus({preventScroll:true});
  let warning=solveToolbar.querySelector('[data-label-warning]');
  const collision=solveSession?.scene?.adornments?.some(a=>!a.clear);
  if(collision&&!warning) {warning=document.createElement('span');warning.dataset.labelWarning='';warning.className='ed-physics-error';warning.textContent='Some badges need more space. Auto-position all labels to clear overlaps.';solveToolbar.appendChild(warning);}
  if(!collision&&warning) warning.remove();
  scheduleSolveLabels();
}
function updateSolveStatus() {
  if(!solveSession || !solveOpen) return;
  const a=solveSession.assessment,d=solveSession.data;
  const rows=physicalValues().filter(r=>{
    if(!a || solveSession.systems===null) return true;
    const node=r.role==='node'?r.id:r.role==='branch'?d.branches[r.index].from:r.role==='source'?(d.sources[r.index].to||d.sources[r.index].from):null;
    const volume=r.volume||(r.role==='surface'?d.control_surfaces[r.index].volume:null);
    return a.systems.some(s=>s.selected&&(node?s.nodes.includes(node):s.id==='volume:'+volume));
  });
  const unknown=rows.filter(r=>r.unknown).length,missing=rows.filter(r=>r.state==='Missing'&&!(r.role==='branch'&&d.branches[r.index].kind==='cap')).length;
  const blocked=solveSession.stale||solveSession.unitError||a&&(a.status==='invalid'||!a.systems.some(s=>s.selected)||a.systems.some(s=>s.selected&&!['solved','balanced'].includes(s.status)));
  const checking=solveSession.operation==='check';
  const checkFailure=a?.systems.some(s=>s.selected&&!['solved','balanced','inconsistent','unbalanced'].includes(s.status))||a?.status==='invalid';
  const title=!unknown&&!solveSession.stale?(checking?(checkFailure?'Cannot check these values':blocked?'Supplied values do not balance':'Supplied values balance'):'No unknown selected'):solveSession.stale?'Drawing changed — restart':!a?'Checking inputs…':blocked?'Not ready to solve':unknown?'Ready to solve':'Ready to check supplied values';
  const systems=a?.systems.filter(s=>s.selected)||[],good=systems.filter(s=>['solved','balanced'].includes(s.status));
  const partial=unknown>0&&good.length>0&&good.length<systems.length;
  const status=document.createElement('section');status.className='ed-solve-status'+(blocked||!unknown&&!checking?' ed-physics-error':a?' ed-solve-success':'');status.setAttribute('role','status');
  const overrides=rows.filter(r=>r.overridden&&!r.unknown).length;
  const reason=solveSession.unitError||a?.issues?.[0]?.message||(a&&!a.systems.length?'Add a network or control volume to solve.':a&&!a.systems.some(s=>s.selected)?'Choose at least one system to solve.':'');
  status.innerHTML=`<strong>${partial?`${good.length} systems ready · ${systems.length-good.length} blocked`:title}</strong><p><button data-values-open="known">${rows.filter(r=>!r.unknown&&numericPhysics(r.value)).length} known</button>${overrides?` (<button data-values-open="overrides">${overrides} overridden</button>)`:''} · <button data-values-open="unknown">${unknown} unknown</button>${missing?` · <button data-values-open="problems">${missing} missing</button>`:''}</p>${!unknown&&!checking?`<p>${missing?'Supply the missing inputs and choose an unknown.':`All ${rows.length} values are supplied. Choose a temperature or resistance to calculate.`}</p>`:blocked&&reason?`<p>${escapeHtml(reason)}</p>`:''}${blocked&&d.nodes.length&&!d.analysis?.network?.steady?'<button data-set-time>Set time model</button>':!unknown?'<button data-values-open="eligible" class="ed-choose-unknown">Choose unknown</button>':''}`;
  const old=solvePanel.querySelector(':scope > .ed-solve-status');
  if(old) old.replaceWith(status);else solvePanel.querySelector('.ed-panel-head')?.after(status);
  const run=solvePanel.querySelector('[data-physics-run]');
  if(run) {
    run.disabled=!unknown||!!solveSession.stale||!!solveSession.unitError||!!solveSession.running||!a||(!good.length && !(unknown===0 && systems.length && systems.every(s=>s.status==='inconsistent')));
    run.classList.add('ed-solve-primary');
    run.textContent=solveSession.running?'Solving…':partial?`Solve ${good.length} ready systems`:!unknown?'Solve':physicsReview?'Recalculate':unknown===1?'Solve for '+rows.find(r=>r.unknown).label.replace(' · T',' temperature'):unknown?`Solve ${unknown} unknowns`:'Check supplied values';
  }
}
function analysisPanel(preserveValueFocus=false) {
  if(!solveOpen) {cancelGesture();setMode('idle');solveOpen=true;panelView='Solve';startSolveSession();}
  $('ed-component-tools').hidden=true;solvePanel.hidden=false;document.body.classList.add('ed-solving');setPanelView(panelView,true);
  $('ed-analysis').setAttribute('aria-expanded','true');
  const rows=physicalValues(),selected=rows.find(r=>r.key===solveValue),result=physicsReview?.result;
  const working=solveSession.data,assessment=solveSession.assessment,stale=solveSession.stale;
  if(stale && S.scene) {drawing.innerHTML=S.scene.parts;buildHits(S.scene.hits);}
  const relevant=r=>{
    if(!assessment || solveSession.systems===null) return true;
    const node=r.role==='node'?r.id:r.role==='branch'?working.branches[r.index].from:r.role==='source'?(working.sources[r.index].to||working.sources[r.index].from):null;
    const volume=r.volume||(r.role==='surface'?working.control_surfaces[r.index].volume:null);
    return assessment.systems.some(s=>s.selected && (node?s.nodes.includes(node):s.id==='volume:'+volume));
  };
  const unknowns=rows.filter(r=>r.unknown&&relevant(r)),missingInputs=rows.filter(r=>r.state==='Missing'&&relevant(r)&&!(r.role==='branch'&&working.branches[r.index].kind==='cap'));
  const missing=missingInputs;
  let h='<div class="ed-panel-head"><h2>Solve physics</h2><button type="button" data-physics-close>Close</button></div>';
  h+='<div class="ed-solve-actions">';
  h+=`<button type="button" data-physics-run ${stale?'disabled':''}>${result?'Recalculate':unknowns.length===1?'Solve for '+escapeHtml(unknowns[0].label):unknowns.length?'Solve selected unknowns':missingInputs.length?'Review missing values':'Check supplied values'}</button>`;
  if(!unknowns.length) h+=`<button data-physics-check ${stale?'disabled':''}>${solveSession.operation==='check'?'Check again':'Check supplied values'}</button>`;
  if(physicsReview?.applied && !stale) h+=`<button type="button" data-physics-apply>Review changes…</button>`;
  h+='</div><div class="ed-solve-body">';
  if(stale) h+='<p class="ed-solve-message">The drawing changed. This session is outdated; its results cannot be applied.</p><button data-session-restart>Restart from current drawing</button>';
  if(solveSession.applyReview && physicsReview) {
    h+='<section class="ed-value-editor"><h3>Review complete scenario</h3><p>Includes the inputs and assumptions used to calculate these answers. Only complete successful systems are applied.</p>';
    for(const c of physicsReview.changes) {const label=rows.find(r=>COLLECTION[r.role]===c.collection&&r.index===c.index&&r.field===c.field)?.label||c.id||c.collection;h+=`<p>${escapeHtml(label)} · ${escapeHtml(c.field)}: ${escapeHtml(sessionChangeText(c.before,c.field))} → ${escapeHtml(sessionChangeText(c.after,c.field))}</p>`;}
    h+='<button data-session-commit>Apply changes</button><button data-session-copy>Copy results only</button><button data-session-cancel-apply>Keep reviewing</button></section>';
  }
  if(result) {
    h+=`<h3>${solveSession.operation==='check'?(result.status==='solved'?'Supplied values balance':assessment?.systems.some(s=>!['solved','balanced','inconsistent','unbalanced'].includes(s.status))?'Cannot check these values':'Supplied values do not balance'):result.status==='solved'?(result.updates.length?'Ready to apply':'Checks passed'):result.status==='not-configured'?'Choose values to solve':escapeHtml(result.status.replaceAll('-',' '))}</h3>`;
    for(const u of result.updates) {const row=rows.find(r=>(u.entity==='branch'?r.role==='branch'&&r.index===u.index:r.id===u.id) && r.field===u.field),comparison=physicsReview.comparisons?.find(c=>c.entity===u.entity&&(u.entity==='branch'?c.index===u.index:c.id===u.id)&&c.field===u.field);h+=`<p class="ed-answer">${escapeHtml(row?.label||u.id)}<br>Drawing: ${escapeHtml(fmtPhysics(comparison?.original))}<br><strong>Calculated: ${fmtPhysics(u.value)} ${escapeHtml(u.unit)}</strong>${comparison?.difference==null?'':`<br>Difference: ${fmtPhysics(comparison.difference)} ${escapeHtml(u.unit)}`}</p>`;}
    if(result.coverage?.diagnostics) h+=`<p class="ed-solve-message">${escapeHtml(result.coverage.diagnostics.map(x=>typeof x==='string'?x:x.message).join('; '))}</p>`;
    h+=`<p>Assertion tolerance: ${100*(working.analysis?.tolerance?.relative??.01)}%; absolute ${working.analysis?.tolerance?.absolute_w??.001} W. Numerical solver residual checks are separate.</p>`;
    for(const r of [...result.components,...result.volumes]) {
      for(const message of r.diagnostics) h+=`<p class="ed-solve-message">${escapeHtml(message)}</p>`;
      if(!result.updates.length) for(const [id,residual] of Object.entries(r.residuals_w||{})) h+=`<p>${escapeHtml(working.nodes.find(n=>n.id===id)?.label||id)}: ${fmtPhysics(Math.abs(residual))} W ${residual>=0?'excess input':'excess output'}; allowed mismatch ${fmtPhysics(r.tolerances_w?.[id])} W</p>`;
      if(r.totals) h+=`<p>${escapeHtml(r.id)}: ${escapeHtml(r.status)}<br>${fmtPhysics(r.totals.incoming)} in − ${fmtPhysics(r.totals.outgoing)} out + ${fmtPhysics(r.totals.generation)} generation − ${fmtPhysics(r.totals.storage)} storage = ${fmtPhysics(r.totals.residual)} W</p>`;
    }
  }
  if(result) {
    h+='<button data-session-copy>Copy results only</button><details><summary>Calculation details</summary>';
    for(const c of result.components) {
      for(const b of c.branch_rates) h+=`<p>${escapeHtml(b.id)}: ${b.watts==null?escapeHtml(b.reason):fmtPhysics(b.watts)+' W (from → to)'}</p>`;
      for(const [id,q] of Object.entries(c.boundary_reactions)) h+=`<p>${escapeHtml(id)} boundary input: ${fmtPhysics(q)} W</p>`;
    }
    h+='<h3>Equations</h3>';
    for(const c of result.components) for(const eq of c.equations) h+=`<p>${escapeHtml(eq.node)}: ${Object.entries(eq.coefficients_w_per_k).filter(([,v])=>v).map(([id,v])=>`${fmtPhysics(v)} × T(${escapeHtml(id)})`).join(' + ')} = ${fmtPhysics(eq.net_input_w)} W${Object.entries(eq.rate_coefficients||{}).filter(([,v])=>v).map(([id,v])=>`<br>Includes ${fmtPhysics(v)} × Q(${escapeHtml(id)})`).join('')}</p>`;
    for(const v of result.volumes) h+=`<p>${escapeHtml(v.id)}: incoming − outgoing + generation − storage = 0${v.coefficient_w==null?'':`<br>${fmtPhysics(v.coefficient_w)} × unknown + ${fmtPhysics(v.known_residual_w)} = 0 W`}</p>`;
    h+='<h3>Assumptions &amp; coverage</h3>';
    for(const c of result.components) for(const assumption of c.assumptions) h+=`<p>${escapeHtml(assumption)}</p>`;
    h+=`<p>${escapeHtml(result.coverage.limits)}</p><p>Unselected volumes: ${escapeHtml(result.coverage.unselected_volumes.join(', ')||'none')}. Detached transfers: ${escapeHtml(result.coverage.detached_transfers.join(', ')||'none')}.</p><button data-physics-json>Export calculation report</button></details>`;
  }
  h+='<details data-solve-settings><summary>Settings</summary>';
  if(assessment) {

    h+=`<details><summary>Included systems</summary><p>Each network or control volume is checked independently.</p>`;
    for(const sys of assessment.systems) {const name=sys.id.startsWith('volume:')?(working.control_volumes.find(v=>'volume:'+v.id===sys.id)?.label||sys.id.slice(7)):'Network: '+sys.nodes.map(id=>working.nodes.find(n=>n.id===id)?.label||id).join(', ');h+=`<label><input type="checkbox" data-session-system="${escapeHtml(sys.id)}" ${sys.selected?'checked':''}>${escapeHtml(name)} · ${escapeHtml(sys.status.replaceAll('-',' '))}</label>`;}
    if(!assessment.systems.length) h+='<p>No analyzable system. Add a network or control volume, or repair the invalid model.</p>';
    for(const issue of assessment.issues) {
      const candidates=rows.filter(r=>relevant(r)&&(issue.nodes?.includes(r.id)||issue.volume===r.volume&&r.volume||r.id&&issue.message.startsWith(r.id+':')));
      for(const r of candidates.filter(r=>r.state==='Missing').slice(0,5)) h+=`<button class="ed-value-link" data-physics-value="${r.key}">Review ${escapeHtml(r.label)}</button>`;
    }
    h+='</details>';
  }
  if(working.nodes.length) h+=`<label>Time model <select data-analysis-steady><option value="" ${working.analysis?.network?.steady?'':'selected'}>Choose…</option><option value="steady" ${working.analysis?.network?.steady?'selected':''}>Steady state</option></select></label><p>Temperatures are constant in time; energy storage is zero. Transient solving is not supported.</p>`;
  for(const [i,v] of (working.control_volumes||[]).entries()) h+=`<label>${escapeHtml(v.label||v.id)}: steady state <input type="checkbox" data-volume-steady="${i}" ${v.steady?'checked':''}></label>`;
  h+='<button data-session-reset>Restore all saved values</button></details>';
  h+='</div>';const scroll=solvePanel.querySelector('.ed-solve-body')?.scrollTop||0;
  if(!solvePanel.querySelector('.ed-solve-body')) solvePanel.innerHTML=h;
  else {
    // Preserve action buttons across blur commits so a click is not lost when
    // a field updates the body between pointerdown and pointerup.
    const template=document.createElement('template');template.innerHTML=h;
    const actions=solvePanel.querySelector('.ed-solve-actions'),next=template.content.querySelector('.ed-solve-actions');
    for(const old of [...actions.children]) if(![...next.children].some(n=>Object.keys(n.dataset)[0]===Object.keys(old.dataset)[0])) old.remove();
    for(const n of [...next.children]) {
      const old=[...actions.children].find(o=>Object.keys(o.dataset)[0]===Object.keys(n.dataset)[0]);
      if(old) {old.textContent=n.textContent;old.disabled=n.disabled;}else actions.appendChild(n);
    }
    solvePanel.querySelector('.ed-solve-body').innerHTML=template.content.querySelector('.ed-solve-body').innerHTML;
  }
  updateSolveStatus();solvePanel.querySelector('.ed-solve-body').scrollTop=scroll;drawPhysicsValues();renderSolveScene();if(!preserveValueFocus) renderValueFloat();renderSolveToolbar();
}
$('ed-analysis').addEventListener('click',()=>solveOpen ? closeAnalysis() : analysisPanel());
document.addEventListener('change',async e=>{
  if(!solveEvent(e)||!solveSession) return;
  const input=e.target,r=physicalValues().find(r=>r.key===solveValue);
  if(input.hasAttribute('data-value-quantity')) {choosePhysics(input.value);return;}
  if(input.hasAttribute('data-value-filter')) {renderNavigator();return;}
  if(input.hasAttribute('data-volume-steady') && input.checked && solveSession.data.control_volumes[Number(input.dataset.volumeSteady)].storage_relation){input.checked=false;toast('Switch to Manual storage power before selecting steady state.');return;}
  if(input.hasAttribute('data-volume-steady')) {sessionEdit(d=>{const v=d.control_volumes[Number(input.dataset.volumeSteady)];v.steady=input.checked;if(v.steady) delete v.storage;if(v.steady && d.analysis?.volumes?.[v.id]?.field==='storage') delete d.analysis.volumes[v.id];});return;}
  if(solveSession.stale) return;
  if(input.dataset.sessionSystem) {const ids=new Set(solveSession.systems??solveSession.assessment.systems.map(s=>s.id));if(input.checked) ids.add(input.dataset.sessionSystem);else ids.delete(input.dataset.sessionSystem);solveSession.systems=[...ids];sessionEdit(()=>{});return;}
  if(input.hasAttribute('data-physics-unit') && r) {
    if(input.dataset.normalizing) return;input.dataset.normalizing='true';
    const session=solveSession,rev=session.revision;session.unitError=false;
    try {session.pendingUnit=rpc.call('physics_convert',r.value,input.value,r.unit,r.quantity||r.field,session.data.units?.T?.scale);const normalized=await session.pendingUnit;
      if(session!==solveSession || rev!==session.revision || session.stale) return;
      sessionEdit(d=>{setQuantityValue(d,r,normalized);session.overrides.add(r.key);});
    } catch(err) {if(session===solveSession) {session.unitError=String(err.message||err);analysisPanel();}} finally {session.pendingUnit=null;}return;
  }
  if(input.hasAttribute('data-analysis-steady')) {sessionEdit(d=>{d.analysis||={};d.analysis.network||={unknowns:[]};d.analysis.network.steady=input.value==='steady';});return;}
  if(!r) return;
  if(input.hasAttribute('data-physics-number') && (r.derived || r.role==='source'&&Number(input.value)<0&&!(Number(r.value)<0))){input.value=String(r.value??'');toast(r.derived?'Edit derivation inputs to change this value.':'Use a positive magnitude and an explicit source direction.');return;}
  if(input.hasAttribute('data-physics-use')) {setPhysicsUse(r,input.value);return;}
  sessionEdit(d=>{
    const obj=d[COLLECTION[r.role]][r.index];d.analysis||={};
    if(input.hasAttribute('data-physics-number')) {setQuantityValue(solveSession.data,r,input.value.trim());solveSession.overrides.add(r.key);}
    else if(input.hasAttribute('data-physics-volume-steady')) {obj.steady=input.checked;if(obj.steady) {delete obj.storage;if(d.analysis.volumes?.[obj.id]?.field==='storage') delete d.analysis.volumes[obj.id];}}
  });
});
// Some embedded browsers emit input but no native change when scripted or
// assistive edits blur. Commit a differing field before the next action.
document.addEventListener('focusout',e=>{
  if(!solveEvent(e)) return;
  const input=e.target;if(!solveSession || solveSession.stale) return;
  const r=physicalValues().find(r=>r.key===solveValue);if(!r) return;
  const changed=input.hasAttribute('data-physics-number')?input.value!==String(r.value??''):input.hasAttribute('data-physics-unit')?input.value!==r.unit:false;
  if(changed && !input.dataset.normalizing) input.dispatchEvent(new Event('change',{bubbles:true}));
});
document.addEventListener('click',async e=>{
  if(!solveEvent(e)||!solveSession) return;
  const target=e.target.closest('button');if(!target) return;
  if(target.hasAttribute('data-auto-labels')) {autoPositionAllLabels();return;}
  if(target.hasAttribute('data-value-close')) {solveValue=null;valueFloat.hidden=true;drawPhysicsValues();return;}
  if(target.hasAttribute('data-navigator-close')) {valueNavigator.hidden=true;return;}
  if(target.hasAttribute('data-values-open')) {openNavigator(target.dataset.valuesOpen);return;}
  if(target.hasAttribute('data-solve-help')) {solveSession.help=!solveSession.help;renderSolveToolbar();return;}
  if(target.hasAttribute('data-help-dismiss')) {solveSession.help=false;try {localStorage.setItem('thermodraw:solve-hint','1');} catch {} renderSolveToolbar();return;}
  if(target.hasAttribute('data-set-time')) {solvePanel.querySelector('[data-solve-settings]').open=true;solvePanel.querySelector('[data-analysis-steady]')?.focus();return;}
  if(target.dataset.physicsMode) {const r=physicalValues().find(r=>r.key===solveValue);if(r) {setPhysicsUse(r,target.dataset.physicsMode);if(target.dataset.physicsMode==='override') valueFloat.querySelector('[data-physics-number]')?.focus();}return;}
  if(target.hasAttribute('data-physics-close')) {closeAnalysis();return;}
  if(target.hasAttribute('data-session-discard')) {closeAnalysis(true);return;}
  if(target.hasAttribute('data-session-keep')) {solveClose.close();return;}
  if(target.hasAttribute('data-session-restart')) {startSolveSession();analysisPanel();return;}
  if(target.hasAttribute('data-session-reset')) {if(!solveSession.stale) {solveSession.data=JSON.parse(solveSession.initial);solveSession.overrides.clear();solveSession.systems=null;sessionEdit(()=>{});}return;}
  if(target.hasAttribute('data-session-reset-field')) {const r=physicalValues().find(r=>r.key===solveValue);if(r) sessionEdit(()=>restoreSessionValue(r));return;}
  if(target.dataset.physicsValue) {choosePhysics(target.dataset.physicsValue);return;}
  if(target.hasAttribute('data-physics-json') && physicsReview) {download('physics-scenario.json',JSON.stringify(physicsReview,null,2),'application/json');return;}
  if(target.hasAttribute('data-session-copy') && physicsReview) {try {await navigator.clipboard.writeText(JSON.stringify({comparisons:physicsReview.comparisons,effective_inputs:physicsReview.effective_inputs,result:physicsReview.result},null,2));toast('Results copied; drawing unchanged.');}catch {toast('Clipboard unavailable. Use Export calculation report.');}return;}
  if(target.hasAttribute('data-physics-run')||target.hasAttribute('data-physics-check')) {
    solveSession.operation=target.hasAttribute('data-physics-check')?'check':'solve';
    if(solveSession.stale) return;
    const origin=solveSession;try {await origin.pendingUnit;} catch {return;}
    if(origin!==solveSession || origin.stale || origin.unitError) return;
    cancelGesture();const session=solveSession,revision=session.revision,request=++physicsRequest;session.running=true;target.disabled=true;target.textContent='Calculating…';
    try {
      const out=await rpc.call('physics_session',session.base,session.data,session.systems);
      if(session!==solveSession || session.stale || request!==physicsRequest || revision!==session.revision) return;
      session.running=false;session.assessment=out;physicsReview=out.result?out:null;analysisPanel();solvePanel.querySelector('.ed-solve-body').scrollTop=0;
    } catch(err) {if(session===solveSession && !session.stale && revision===session.revision) {session.running=false;analysisPanel();toast(String(err.message||err));}}
  }
  if(target.hasAttribute('data-physics-apply')) {solveSession.applyReview=true;analysisPanel();solvePanel.querySelector('.ed-value-editor')?.scrollIntoView({block:'nearest'});}
  if(target.hasAttribute('data-session-cancel-apply')) {solveSession.applyReview=false;analysisPanel();}
  if(target.hasAttribute('data-session-commit')) {
    const session=solveSession,r=physicsReview;
    if(!r?.applied || session.stale || session.generation!==S.generation || session.documentRevision!==S.revision || JSON.stringify(session.base)!==JSON.stringify(S.data)) {toast('The drawing changed. Restart this session.');return;}
    edit(d=>{for(const key of Object.keys(d)) delete d[key];Object.assign(d,JSON.parse(JSON.stringify(r.applied)));completeEditorDefaults(d);});
    startSolveSession();analysisPanel();toast('Complete scenario applied. Undo restores the drawing.');
  }
});
// In Solve mode, selecting a physical object must never start a drawing drag.
canvas.addEventListener('pointerdown',e=>{
  if(!solveOpen || panelView!=='Solve') return;
  const badge=e.target.closest('[data-physics-pick]'),hit=e.target.closest('[data-role]');
  const row=badge?physicalValues().find(r=>r.key===badge.dataset.physicsPick):hit?physicalValues().find(r=>r.role===hit.dataset.role && r.index===Number(hit.dataset.index)):null;
  if(!row && !hit) return;e.preventDefault();e.stopImmediatePropagation();if(row) {if(badge?.hasAttribute('data-physics-cycle')) cyclePhysics(row.key);else choosePhysics(row.key);}else toast('This component has no editable physical value.');
},true);
for(const event of ['click','dblclick']) canvas.addEventListener(event,e=>{if(solveOpen && panelView==='Solve' && e.target.closest('[data-physics-pick],[data-role]')) {e.preventDefault();e.stopImmediatePropagation();}},true);
physicsMarks.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' ') {e.preventDefault();const key=e.target.closest('[data-physics-pick]').dataset.physicsPick;cyclePhysics(key);physicsMarks.querySelector(`[data-physics-cycle="${key}"]`)?.focus();}});
window.addEventListener('resize',()=>{if(solveOpen) {drawPhysicsValues();renderSolveToolbar();if(!valueFloat.hidden) positionSolveFloat(valueFloat,physicalValues().find(r=>r.key===solveValue));if(!valueNavigator.hidden) positionSolveFloat(valueNavigator);}});


document.addEventListener('keydown',e=>{if(solveOpen && panelView==='Solve' && !S.present && e.key==='Escape') {if(solveClose.open) solveClose.close();else if(!valueFloat.hidden) {valueFloat.hidden=true;solveValue=null;drawPhysicsValues();}else if(!valueNavigator.hidden) valueNavigator.hidden=true;else closeAnalysis();e.preventDefault();e.stopImmediatePropagation();}},true);

// Familiar menus own their actions; the primary controls remain one click away.
function installEditorMenus() {
  const top=$('ed-top'),nav=document.createElement('nav');nav.className='ed-menu-categories';nav.setAttribute('aria-label','Editor menus');
  const panels=new Map(),buttons=new Map();
  const editActions=document.createElement('div');editActions.id='ed-edit-actions';editActions.setAttribute('role','group');editActions.setAttribute('aria-label','Editing actions');
  for(const name of ['File','View','Help']) {
    const button=document.createElement('button');button.textContent=name;button.type='button';button.setAttribute('aria-expanded','false');
    const panel=document.createElement('div');panel.className='ed-category-menu card';panel.setAttribute('role','menu');button.setAttribute('aria-haspopup','menu');panel.hidden=true;panel.setAttribute('aria-label',name+' menu');
    button.onclick=()=>{const open=panel.hidden;for(const p of panels.values())p.hidden=true;for(const b of buttons.values())b.setAttribute('aria-expanded','false');panel.hidden=!open;button.setAttribute('aria-expanded',String(open));if(open)underButton(panel,button);};
    panel.addEventListener('click',e=>{if(e.target.closest('button') && !e.target.closest('details') && e.target.closest('button').dataset.menuKind!=='toggle') {panel.hidden=true;button.setAttribute('aria-expanded','false');}});
    nav.appendChild(button);document.body.appendChild(panel);panels.set(name,panel);buttons.set(name,button);
  }
  const move=(name,ids)=>{for(const id of ids) if($(id)) panels.get(name).appendChild($(id));};
  move('File',['ed-new','ed-export','ed-share']);
  panels.get('File').appendChild($('ed-import').closest('label'));
  editActions.appendChild($('ed-delete'));
  move('View',['ed-fit','ed-auto-labels','ed-notation','ed-theme','ed-present']);
  move('Help',['ed-help']);$('ed-help').textContent='Editor guide';$('ed-help').classList.remove('ed-help-btn');
  const action=(name,label,run)=>{const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=run;(name==='Edit'?editActions:panels.get(name)).appendChild(b);return b;};
  action('File','Rename',()=>renameFile(S.file.id,$('ed-file')));
  action('File','Duplicate',()=>{const data=structuredClone(S.data),name=S.file.name+' (copy)';if(data.title)data.title=name;newFile(name,data);});
  action('Edit','Copy',()=>{toCanvas();document.execCommand('copy');});
  action('Edit','Paste',async()=>{try{const data=new DataTransfer();data.setData('text/plain',await navigator.clipboard.readText());canvas.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true}));}catch{toast('Use Ctrl+V to paste from the clipboard.');}});
  action('Edit','Merge selected nodes',()=>{
    const selected=S.selection.filter(s=>s.role==='node').map(s=>element(s).id);
    if(selected.length<2) {toast('Select at least two nodes using Shift-click.');return;}
    const target=selected.at(-1);let data=S.data;
    if(selected.length===2) {joinNodes(selected[0],target);return;}
    for(const id of selected.slice(0,-1)) {const p=mergeNodes(data,id,target);if(p.conflicts.length){reviewSelectedMerge(selected,target);return;}data=p.document;}
    commitTopology({document:data,conflicts:[],selection:{role:'node',index:data.nodes.findIndex(n=>n.id===target)}});
  });
  action('View','Files',()=>collapseFiles(!document.body.classList.contains('ed-files-collapsed'))).dataset.menuKind='toggle';
  action('View','Components',()=>showComponents(document.body.classList.contains('ed-components-collapsed'))).dataset.menuKind='toggle';
  action('View','Advanced layout',()=>{
    select(null);pop.innerHTML='<h4>Advanced layout</h4><p>The reference rail is a shared reference-temperature line. Connecting to it uses the selected node’s temperature.</p>'+field('Reference node',selectBox('rail:reference',S.data.rail?.reference||'',['',...S.data.nodes.map(n=>n.id)],{'':'No rail'}))+field('Rail y',num('rail:y',S.data.rail?.y,10))+'<button data-act="solve">Place unplaced nodes</button>';
    pop.hidden=false;underButton(pop,buttons.get('View'));
  });
  // Supplied-value checks remain in Solve and on the P shortcut.
  $('ed-physics').closest('label').hidden=true;
  action('Help','Keyboard shortcuts',showShortcuts);

  const primary=document.createElement('div');primary.className='ed-primary';
  for(const id of ['ed-file','ed-undo','ed-redo','ed-settings']) primary.appendChild($(id));
  primary.insertBefore(editActions,primary.querySelector('#ed-settings'));
  installEditIcons(editActions);
  const examples=document.createElement('section');examples.id='ed-example-section';examples.setAttribute('aria-label','Examples');
  const toggle=$('ed-open-example');toggle.textContent='Examples';toggle.setAttribute('aria-expanded','true');
  const exampleList=$('ed-examples');exampleList.hidden=false;examples.append(toggle,exampleList);$('ed-files-panel').appendChild(examples);loadExamples();
  top.append(nav,primary);
  top.querySelectorAll(':scope > .ed-group').forEach(el=>el.hidden=true);
  $('ed-sketch').hidden=true;$('ed-more').hidden=true;
  const chip=document.createElement('button');chip.id='ed-components-reopen';chip.textContent='Components';chip.onclick=()=>showComponents(true);document.body.appendChild(chip);
  document.addEventListener('pointerdown',e=>{if(!e.target.closest('.ed-category-menu,.ed-menu-categories')){for(const p of panels.values())p.hidden=true;for(const b of buttons.values())b.setAttribute('aria-expanded','false');}});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){for(const p of panels.values())p.hidden=true;}});
  for(const panel of panels.values()) wireMenu(panel);
  const mobile=document.createElement('details');mobile.className='ed-mobile-menu';mobile.innerHTML='<summary>Menu</summary>';top.prepend(mobile);
  const position=()=>{(innerWidth<760?mobile:top).appendChild(nav);};position();window.addEventListener('resize',position);
}
installEditorMenus();

function interactionHelp(id) {
  const entry=S.catalogue?.interactions?.find(x=>x.id===id);
  return entry?`${entry.name}. ${entry.when} ${entry.action} Changes: ${entry.changes}. ${entry.cancel}`:'Unconnected endpoint — drag to connect. Escape cancels; Undo restores the connection.';
}

function installMiniPickers() {
  const catalogue=S.catalogue;if(!catalogue)return;
  const picker=document.createElement('div');picker.className='ed-mini-picker card';picker.hidden=true;picker.setAttribute('role','dialog');picker.setAttribute('aria-label','Scientific notation picker');document.body.appendChild(picker);
  let owner=null,start=0,end=0;
  const close=()=>{picker.hidden=true;owner?.focus({preventScroll:true});};
  function insert(token,prefix=false) {
    if(!owner)return;
    if(owner.tagName==='SELECT') {
      if(![...owner.options].some(o=>o.value===token)){toast('Choose one of the supported temperature units.');return;}
      owner.value=token;owner.dispatchEvent(new Event('change',{bubbles:true}));close();return;
    }
    let value=owner.value,a=start,b=end;
    if(prefix) {
      const selected=value.slice(a,b);
      if(selected && !/^[A-Za-zµμ°]+$/.test(selected)) {toast('Select one unit token before applying a prefix.');return;}
      if(!selected) {
        const left=value.slice(0,a).match(/[A-Za-zµμ°]+$/)?.[0]||'',right=value.slice(a).match(/^[A-Za-zµμ°]+/)?.[0]||'';
        a-=left.length;b+=right.length;
      }
      const unit=value.slice(a,b);
      if(!unit || ['kg','°C','°F'].includes(unit)) {toast('Choose a prefixable unit token, such as g, W, J, m, or K.');return;}
      const base=unit.match(/(?:W|J|K|g|m|s)$/)?.[0];
      if(!base) {toast('Select a supported unit token.');return;}
      token+=base;
    }
    owner.focus();
    if(owner.type==='number')owner.value=value.slice(0,a)+token+value.slice(b);
    else {owner.setSelectionRange(a,b);if(!document.execCommand('insertText',false,token))owner.setRangeText(token,a,b,'end');}
    owner.dispatchEvent(new Event('input',{bubbles:true}));owner.dispatchEvent(new Event('change',{bubbles:true}));close();
  }
  function open(field,button) {
    owner=field;start=field.selectionStart??field.value.length;end=field.selectionEnd??start;
    const key=field.hasAttribute('data-run-text')?'label':field.dataset.field||field.dataset.physical||'',isUnit=key.startsWith('unit:'),integer=key==='count',notation=['label','sub'].includes(key);
    const quantity=isUnit?key.slice(5):null;
    picker.replaceChildren();
    const search=document.createElement('input');search.type='search';search.placeholder='Find a symbol or unit';search.setAttribute('aria-label','Search picker');picker.appendChild(search);
    const entries=[];
    const section=name=>{const heading=document.createElement('h4');heading.textContent=name;picker.appendChild(heading);};
    const option=(token,name,details='',prefix=false)=>{
      const b=document.createElement('button');b.type='button';b.textContent=token||'No prefix';b.title=name+(details?' — '+details:'');b.setAttribute('aria-label',b.title);b.onclick=()=>insert(token,prefix);picker.appendChild(b);entries.push([b,(token+' '+name).toLowerCase()]);
    };
    section('Common');
    if(integer)for(const digit of '1234567890')option(digit,digit);
    else if(isUnit) {
      const presets=catalogue.presets;
      for(const unit of presets[quantity]||[])option(unit,unit);
      section('Units');for(const unit of catalogue.units.filter(x=>x.quantity===quantity))option(unit.symbol,unit.name,unit.help);
      if(quantity!=='T') {
        section('Prefixes');for(const p of catalogue.prefixes)option(p.symbol,p.name,'10'+String(p.exponent).replace(/[-0-9]/g,c=>'⁻⁰¹²³⁴⁵⁶⁷⁸⁹'['-0123456789'.indexOf(c)]),true);
        section('Notation');for(const [s,n] of [['·','multiplication dot'],['/','division'],['(','opening parenthesis'],[')','closing parenthesis'],['²','squared'],['³','cubed']])option(s,n);
      }
    } else if(notation) {
      section('Symbols');for(const s of catalogue.symbols)option(s.symbol,s.name);
    } else {option('e','scientific exponent');option('-','minus sign');option('.','decimal point');}
    const help=document.createElement('p');help.textContent='Inserts at the caret. Prefixes apply to the selected unit token. Escape closes; Undo restores inserted text.';picker.appendChild(help);
    const done=document.createElement('button');done.textContent='Close';done.onclick=close;picker.appendChild(done);
    search.oninput=()=>{for(const [b,text]of entries)b.hidden=!text.includes(search.value.toLowerCase());};
    (field.closest('dialog')||document.body).appendChild(picker);picker.hidden=false;underButton(picker,button);search.focus();
  }
  function attach(root) {
    for(const field of root.querySelectorAll('input[data-field],input[data-physical],input[data-physics-number],input[data-run-text],select[data-field="unit:T"]')) {
      if(field.dataset.picker || field.readOnly || field.type==='checkbox' || ['count','angle','id'].includes(field.dataset.field))continue;
      field.dataset.picker='true';const b=document.createElement('button');b.type='button';b.className='ed-picker-button';b.textContent='⌨';b.setAttribute('aria-label','Open notation picker');b.title='Units and scientific notation';
      b.onpointerdown=e=>e.preventDefault();b.onclick=()=>open(field,b);
      const focused=document.activeElement===field,caret=field.selectionStart,tail=field.selectionEnd;
      const wrap=document.createElement('span');wrap.className='ed-field-picker';field.replaceWith(wrap);wrap.append(field,b);
      if(focused){field.focus({preventScroll:true});if(caret!=null)field.setSelectionRange(caret,tail);}
    }
    for(const control of root.querySelectorAll('[data-field],[data-act]')) {
      const key=control.dataset.field||control.dataset.act,help=catalogue.controls[key];
      if(!help || control.dataset.helpReady)continue;
      control.dataset.helpReady='true';control.title=help;control.setAttribute('aria-description',help);
      const label=control.closest('label')?.querySelector('span');if(label){label.title=help;label.tabIndex=0;label.setAttribute('aria-description',help);}
    }
  }
  for(const root of [pop,valueFloat]) {new MutationObserver(()=>attach(root)).observe(root,{childList:true,subtree:true});attach(root);}
  new MutationObserver(()=>{for(const root of document.querySelectorAll('.ed-assignment-dialog'))attach(root);}).observe(document.body,{childList:true,subtree:true});
  picker.onkeydown=e=>{if(e.key==='Escape'){e.preventDefault();e.stopPropagation();close();}};
  document.addEventListener('pointerdown',e=>{if(!picker.hidden && !picker.contains(e.target) && !e.target.closest('.ed-picker-button'))picker.hidden=true;});
}

// Shared panel shell. Document edits remain in the existing inspector handlers.
let panelView='Components',inspectorTab='Properties';
function setPanelView(view,force=false) {
  if(!force&&groupDraft){gateGroup(()=>setPanelView(view,true));return;}
  if(view==='Solve'&&!solveOpen){analysisPanel();return;}
  panelView=view;document.body.dataset.panelView=view;
  const palette=$('ed-palette');
  let tabs=$('ed-panel-views');
  if(!tabs){tabs=document.createElement('nav');tabs.id='ed-panel-views';tabs.setAttribute('aria-label','Panel views');palette.prepend(tabs);}
  tabs.replaceChildren();document.body.classList.toggle('ed-right-overlay',innerWidth<1100);
  for(const name of ['Components','Properties','Solve']) {
    const b=document.createElement('button');b.textContent=name;b.type='button';b.disabled=name==='Properties'&&!S.sel;b.setAttribute('aria-pressed',String(name===view));
    b.onclick=()=>{if(name==='Properties'&&!pop.classList.contains('ed-docked')){if(groupDraft)gateGroup(()=>openPopover(S.sel));else openPopover(S.sel);}else setPanelView(name);};tabs.appendChild(b);
  }
  $('ed-component-tools').hidden=view!=='Components';$('ed-solve-panel').hidden=view!=='Solve';
  if(pop.classList.contains('ed-docked'))pop.hidden=view!=='Properties';
  if(view==='Properties'||view==='Solve'){document.body.classList.remove('ed-components-collapsed');document.body.classList.add('ed-components-open');}
}
function dockInspector(sel) {
  if(!pop.querySelector('[data-inspector-tabs]')) {
    const heading=pop.querySelector('h4');
    const header=document.createElement('header');header.className='ed-inspector-head';if(heading)header.appendChild(heading);
    const close=document.createElement('button');close.type='button';close.textContent='×';close.setAttribute('aria-label','Close properties');close.onclick=()=>{if(groupDraft)gateGroup(()=>select(null));else select(null);};header.appendChild(close);
    const nav=document.createElement('nav');nav.dataset.inspectorTabs='';nav.setAttribute('aria-label','Property sections');
    const sections=new Map();
    for(const name of ['Properties','Connections','Appearance']){const section=document.createElement('section');section.dataset.inspectorSection=name;sections.set(name,section);const b=document.createElement('button');b.textContent=name;b.type='button';b.onclick=()=>showInspectorTab(name);nav.appendChild(b);}
    const footer=document.createElement('footer');footer.className='ed-inspector-footer';
    // Flatten old layout containers; move live fields, preserving delegation.
    for(const label of [...pop.querySelectorAll('label')]) {
      if(label.parentElement?.closest('label') || label.closest('fieldset'))continue;
      const field=label.querySelector('[data-field],[data-physical]'),key=field?.dataset.field||field?.dataset.physical;
      const name=['from','to','direction'].includes(key)?'Connections':['angle','side','symbol-position'].includes(key)?'Appearance':'Properties';
      if(key==='id')continue;
      if(key==='arrangement'){sections.get(name).appendChild(label.parentElement);continue;}
      sections.get(name).appendChild(label);
    }
    for(const e of [...pop.querySelectorAll('[data-act]')]) {
      if(e.closest('.ed-vias'))continue;
      const act=e.dataset.act;if(['delete','delete-selection'].includes(act)){footer.appendChild(e);continue;}
      const name=['connect','swap','via-add','disconnect-from','disconnect-to','disconnect-both'].includes(act)?'Connections':'Appearance';
      if(['disconnect-from','disconnect-to'].includes(act)){const field=sections.get(name).querySelector(`[data-field="${act==='disconnect-from'?'from':'to'}"]`);if(field){const wrap=document.createElement('span');wrap.className='ed-endpoint-control';field.replaceWith(wrap);wrap.append(field,e);continue;}}
      if(act==='disconnect-both'){const advanced=document.createElement('details');advanced.innerHTML='<summary>More connection actions</summary>';advanced.appendChild(e);sections.get(name).appendChild(advanced);}
      else sections.get(name).appendChild(e);
    }
    const advanced=document.createElement('details');advanced.innerHTML='<summary>Advanced</summary>';
    if(['region','volume','surface','transfer','annotation'].includes(sel.role)){const id=header.querySelector('code');if(id){const row=document.createElement('p');row.textContent='Identifier: '+id.textContent;id.remove();advanced.appendChild(row);}}
    for(const e of [...pop.querySelectorAll('input[data-field="id"],.ed-vias')])advanced.appendChild(e.matches('input')?e.closest('label'):e);
    if(advanced.children.length>1)sections.get('Appearance').appendChild(advanced);
    for(const hint of [...pop.querySelectorAll('p.ed-hint')])if(hint.textContent.startsWith('Label position:'))sections.get('Appearance').appendChild(hint);
    const selectionSummary=pop.querySelector('[data-selection-summary]');if(selectionSummary)sections.get('Properties').appendChild(selectionSummary);
    const preview=pop.querySelector('[data-group-preview]');if(preview)sections.get('Properties').appendChild(preview);
    const actions=pop.querySelector('[data-group-actions]');if(actions)footer.prepend(actions);
    // Physical relationships are already grouped semantically.
    for(const e of [...pop.querySelectorAll('fieldset,.ed-error,[data-budget],[data-review-budget]')])sections.get('Properties').appendChild(e);
    const assignment=pop.querySelector('[data-assignment-open]');if(assignment)footer.prepend(assignment);
    pop.replaceChildren(header,nav,...sections.values(),footer);
    for(const [name,section] of sections){const help=document.createElement('button');help.type='button';help.className='ed-section-help';help.textContent='Help';help.onclick=()=>{
      let text=section.querySelector('.ed-section-explanation');if(text){text.remove();return;}
      text=document.createElement('div');text.className='ed-section-explanation';text.setAttribute('role','note');
      const definitions=[...section.querySelectorAll('[data-field],[data-act]')].map(e=>S.catalogue?.controls?.[e.dataset.field||e.dataset.act]).filter(Boolean);
      text.textContent=[...new Set(definitions)].join(' ')||'Edit the selected component. Undo restores a committed change.';help.after(text);
    };section.prepend(help);}
  }
  pop.classList.add('ed-docked');pop.style.cssText='';if(pop.parentElement!==$('ed-palette'))$('ed-palette').appendChild(pop);pop.hidden=false;setPanelView('Properties',true);showInspectorTab(inspectorTab);
}
function showInspectorTab(name) {
  inspectorTab=name;
  for(const section of pop.querySelectorAll('[data-inspector-section]'))section.hidden=section.dataset.inspectorSection!==name;
  for(const b of pop.querySelectorAll('[data-inspector-tabs] button'))b.setAttribute('aria-pressed',String(b.textContent===name));
}
function wireMenu(panel) {
  const items=()=>[...panel.querySelectorAll('button,label.btn')].filter(e=>!e.disabled&&!e.hidden);
  for(const e of items()) {if(['ed-theme','ed-notation'].includes(e.id))e.dataset.menuKind='toggle';e.dataset.menuKind||='command';e.setAttribute('role',e.dataset.menuKind==='toggle'?'menuitemcheckbox':'menuitem');e.setAttribute('aria-label',e.textContent.trim());if(e.tagName==='LABEL')e.tabIndex=0;}
  const sync=()=>{for(const e of items())if(e.dataset.menuKind==='toggle'){const checked=e.id==='ed-theme'?document.documentElement.dataset.theme==='dark':e.id==='ed-notation'?S.notation==='zigzags':e.textContent==='Files'?!document.body.classList.contains('ed-files-collapsed'):!document.body.classList.contains('ed-components-collapsed');e.setAttribute('aria-checked',String(checked));e.setAttribute('aria-label',e.textContent.trim());}};
  panel.addEventListener('click',()=>queueMicrotask(sync));sync();
  panel.addEventListener('keydown',e=>{if(e.target.tagName==='LABEL'&&['Enter',' '].includes(e.key)){e.preventDefault();e.target.click();return;}const rows=items(),i=rows.indexOf(document.activeElement);if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();rows[e.key==='Home'?0:e.key==='End'?rows.length-1:(i+(e.key==='ArrowDown'?1:-1)+rows.length)%rows.length]?.focus();}if(e.key==='Escape'){e.preventDefault();e.stopPropagation();panel.hidden=true;document.querySelector('.ed-menu-categories button[aria-expanded="true"]')?.focus();for(const b of document.querySelectorAll('.ed-menu-categories button'))b.setAttribute('aria-expanded','false');}});
}
function drawHover(hit,append=false) {
  if(!append)ui.querySelectorAll('.ed-hover-ink').forEach(e=>e.remove());if(!hit)return;
  if(hit.element==='label'&&hit.rect){const b=['x','y','width','height'].map(k=>+hit.rect.getAttribute(k));ui.appendChild(svgEl('rect',{x:b[0],y:b[1],width:b[2],height:b[3],fill:'none'},'ed-hover-ink'));}
  else if(hit.role==='branch') {const route=routeOf(element(hit)),symbol=symbolHit(hit);if(route){let runs=[route];if(symbol){const near=nearestSegment(route,symbol.at),half=symbol.terminal_half||62;const tip=t=>near.a.map((v,i)=>v+near.u[i]*t);runs=[route.slice(0,near.i+1).concat([tip(Math.max(0,near.along-half))]),[tip(Math.min(near.len,near.along+half))].concat(route.slice(near.i+1))];}for(const run of runs)ui.appendChild(svgEl('polyline',{points:run.map(p=>p.join(',')).join(' '),fill:'none'},'ed-hover-ink'));}}

  else {const b=boundsOf(hit);if(b)ui.appendChild(svgEl('rect',{x:b[0]-3,y:b[1]-3,width:b[2]-b[0]+6,height:b[3]-b[1]+6,rx:4,fill:'none'},'ed-hover-ink'));}
}
function showShortcuts() {
  const dialog=document.createElement('dialog');dialog.className='ed-help-dialog';dialog.setAttribute('aria-label','Keyboard shortcuts');dialog.innerHTML='<header class="ed-dialog-heading"><h2>Keyboard shortcuts</h2></header>';
  for(const group of ['Editing','Navigation','Connections']){const h=document.createElement('h3');h.textContent=group;dialog.appendChild(h);for(const item of SHORTCUTS.filter(x=>x.group===group)){const row=document.createElement('p');row.innerHTML=`<span>${escapeHtml(item.label)}</span><kbd>${escapeHtml(item.keys.replaceAll('Mod',/Mac|iPhone|iPad/.test(navigator.platform)?'⌘':'Ctrl'))}</kbd>`;dialog.appendChild(row);}}
  const close=document.createElement('button');close.className='ed-dialog-close';close.textContent='×';close.setAttribute('aria-label','Close keyboard shortcuts');close.title='Close (Escape)';close.onclick=()=>dialog.close();dialog.querySelector('.ed-dialog-heading').appendChild(close);dialog.onclose=()=>dialog.remove();document.body.appendChild(dialog);dialog.showModal();
}
const SHORTCUTS=[
 {group:'Editing',label:'Copy selection',keys:'Mod+C',match:()=>false},
 {group:'Editing',label:'Paste selection',keys:'Mod+V',match:()=>false},
 {group:'Navigation',label:'Cancel / close',keys:'Escape',match:()=>false},
 {group:'Navigation',label:'Previous / next file in Present',keys:'← / →',match:()=>false},
 {group:'Editing',label:'Undo',keys:'Mod+Z',match:e=>(e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'&&!e.shiftKey,run:()=>undo()},
 {group:'Editing',label:'Redo',keys:'Mod+Shift+Z / Ctrl+Y',match:e=>(e.ctrlKey||e.metaKey)&&(e.key.toLowerCase()==='y'||e.key.toLowerCase()==='z'&&e.shiftKey),run:()=>redo()},
 {group:'Editing',label:'Delete selection',keys:'Delete / Backspace',match:e=>['Delete','Backspace'].includes(e.key),run:()=>{if(S.sel&&!S.present)removeSelected();}},
 {group:'Navigation',label:'Fit drawing',keys:'F',match:e=>e.key.toLowerCase()==='f',run:()=>fitFromCommand()},
 {group:'Navigation',label:'Switch theme',keys:'D',match:e=>e.key.toLowerCase()==='d',run:()=>$('ed-theme').click()},
 {group:'Navigation',label:'Switch notation',keys:'Z',match:e=>e.key.toLowerCase()==='z',run:()=>$('ed-notation').click()},
 {group:'Navigation',label:'Check supplied values',keys:'P',match:e=>e.key.toLowerCase()==='p',run:()=>{$('ed-physics').checked=!$('ed-physics').checked;$('ed-physics').dispatchEvent(new Event('change'));}},
 {group:'Connections',label:'Rotate counterclockwise / clockwise',keys:'[ / ]',match:e=>['[',']'].includes(e.key),run:e=>turnSelected(e.key===']'?1:-1)},
 {group:'Connections',label:'Quick add',keys:'/',match:e=>e.key==='/',run:()=>{const r=canvas.getBoundingClientRect();requestQuick(lastPointer.x||r.left+r.width/2,lastPointer.y||r.top+r.height/2);}}
];
(function installPanelChrome(){
  const header=document.createElement('div');header.id='ed-canvas-header';header.setAttribute('aria-label','Panel controls');$('ed-stage').prepend(header);
  for(const [id,label] of [['ed-files-reopen','Files'],['ed-components-reopen','Components']]){const b=$(id);b.textContent='▥ '+label;b.setAttribute('aria-label',label);header.appendChild(b);if(id==='ed-files-reopen')b.onclick=()=>{collapseFiles(false);filesPanel.classList.add('ed-open');};}
  for(const [id,reverse] of [['ed-undo',false],['ed-redo',true]]){const b=$(id);b.setAttribute('aria-label',reverse?'Redo':'Undo');b.title=(reverse?'Redo (':'Undo (')+(/Mac/.test(navigator.platform)?'⌘':'Ctrl')+(reverse?'+Shift+Z)':'+Z)');b.innerHTML=`<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" ${reverse?'style="transform:scaleX(-1)"':''}><path d="M8 5 3 10l5 5M3 10h10a7 7 0 0 1 7 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;}
  setPanelView('Components',true);
  document.querySelector('.ed-menu-categories').addEventListener('keydown',e=>{if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();if(e.target.getAttribute('aria-expanded')!=='true')e.target.click();const panel=[...document.querySelectorAll('.ed-category-menu')].find(p=>!p.hidden);panel?.querySelector('[role^="menuitem"]')?.focus();}});
})();

// Menu dismissal takes precedence over canvas and Solve Escape handlers.
window.addEventListener('keydown',e=>{
  const panel=[...document.querySelectorAll('.ed-category-menu')].find(p=>!p.hidden);
  if(!panel)return;
  const triggers=[...document.querySelectorAll('.ed-menu-categories button')],active=triggers.find(b=>b.getAttribute('aria-expanded')==='true');
  if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();panel.hidden=true;active?.setAttribute('aria-expanded','false');const mobile=document.querySelector('.ed-mobile-menu');if(mobile?.open){mobile.open=false;mobile.querySelector('summary').focus();}else active?.focus();}
  else if(['ArrowLeft','ArrowRight'].includes(e.key)&&!e.target.matches('input,textarea')){e.preventDefault();e.stopImmediatePropagation();const next=triggers[(triggers.indexOf(active)+(e.key==='ArrowRight'?1:-1)+triggers.length)%triggers.length];next?.click();next?.focus();}
},true);
document.addEventListener('pointerdown',e=>{
  if(!e.target.closest('.ed-mobile-menu,.ed-category-menu')){const mobile=document.querySelector('.ed-mobile-menu');if(mobile)mobile.open=false;}
});

function installEditIcons(container){
  const mod=/Mac|iPhone|iPad/.test(navigator.platform)?'⌘':'Ctrl';
  const icons={
    'Copy':['ed-copy',`Copy (${mod}+C)`,'<rect x="8" y="8" width="12" height="12" rx="1"/><path d="M16 8V4H4v12h4"/>'],
    'Paste':['ed-paste',`Paste (${mod}+V)`,'<path d="M9 5H5v16h14V5h-4"/><rect x="9" y="3" width="6" height="4" rx="1"/>'],
    'Delete':['ed-delete','Delete selection (Delete)','<path d="M4 7h16M9 7V4h6v3M6 7l1 14h10l1-14M10 10v7M14 10v7"/>'],
    'Merge selected nodes':['ed-merge','Merge selected nodes','<circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><path d="M5 7v3l7 5 7-5V7"/><circle cx="12" cy="18" r="3"/>']
  };
  for(const button of container.querySelectorAll('button')){
    const label=button.textContent.trim(),entry=icons[label];if(!entry)continue;
    button.id=entry[0];button.className='ed-icon-button';button.title=entry[1];button.setAttribute('aria-label',label==='Delete'?'Delete selection':label);
    button.innerHTML=`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${entry[2]}</svg>`;
  }
  for(const id of ['ed-copy','ed-paste','ed-delete','ed-merge'])container.appendChild(container.querySelector('#'+id));
}
// A programmatic canvas focus after a pointer action is not keyboard navigation.
document.addEventListener('pointerdown',()=>document.body.classList.remove('ed-keyboard-navigation'),true);
document.addEventListener('keydown',e=>{if(e.key==='Tab')document.body.classList.add('ed-keyboard-navigation');},true);
new ResizeObserver(()=>document.documentElement.style.setProperty('--ed-toolbar-height',$('ed-top').getBoundingClientRect().height+'px')).observe($('ed-top'));

pop.addEventListener("click", e=>{if(e.target.closest("[data-assignment-open]"))openAssignmentOptions(S.sel);});

document.addEventListener('click',e=>{if(e.target.closest('[data-scenario-derivation]')) {const r=physicalValues().find(r=>r.key===solveValue);if(r)openAssignmentOptions({role:r.role,index:r.index},true);}});
