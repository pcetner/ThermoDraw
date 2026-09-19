import {expandSegment} from './group.js';
// Pure topology proposals. Coordinates never imply connectivity except at an
// explicit exact-overlap merge boundary. Callers own validation and Undo.
const copy = value => structuredClone(value);
const physical = ['regions', 'control_volumes', 'control_surfaces', 'transfers', 'annotations'];
export const emptyFree = n => n && (!n.kind || n.kind === 'free') &&
  Object.keys(n).every(k => ['id', 'at', 'kind'].includes(k) || n[k] == null || n[k] === '');
function fresh(d) {
  const ids = new Set(d.nodes.map(n => n.id));
  for (let i = 1; ; i++) if (!ids.has(`n${i}`)) return `n${i}`;
}
function remap(d, source, target) {
  for (const x of [...d.branches, ...(d.sources || [])]) {
    for (const end of ['from', 'to']) if (x[end] === source) x[end] = target;
  }
  if (d.rail?.reference === source) d.rail.reference = target;
  for(const g of d.cases||[])g.nodes=[...new Set(g.nodes.map(n=>n===source?target:n))];
  if(d.layout_options?.starts)d.layout_options.starts=[...new Set(d.layout_options.starts.map(n=>n===source?target:n))];
  for (const key of physical) for (const x of d[key] || []) {
    if (x.links) x.links = [...new Set(x.links.map(r => r === `node:${source}` ? `node:${target}` : r))];
  }
  const network = d.analysis?.network;
  if (network?.unknowns) network.unknowns = [...new Set(network.unknowns.map(id => id === source ? target : id))];
}
function filterBranches(d, keep) {
  const old = d.branches;
  d.branches = old.filter(keep);
  for(const key of physical)for(const x of d[key]||[])if(x.links)x.links=x.links.flatMap(ref=>{
    if(!ref.startsWith('branch:'))return [ref];
    const token=ref.slice(7),index=token.startsWith('@')?Number(token.slice(1)):old.findIndex(b=>b.id===token);
    const next=d.branches.indexOf(old[index]);
    return next<0?[]:[token.startsWith('@')?'branch:@'+next:ref];
  });
  const net = d.analysis?.network;
  if (net?.resistance_unknowns) net.resistance_unknowns = net.resistance_unknowns.flatMap(t => {
    const index = typeof t === 'number' ? d.branches.indexOf(old[t]) : d.branches.findIndex(b => b.id === t);
    return index < 0 ? [] : [typeof t === 'number' ? index : t];
  });
}
export function mergeNodes(document, sourceId, targetId) {
  const d = copy(document), conflicts = [];
  const source = d.nodes.find(n => n.id === sourceId), target = d.nodes.find(n => n.id === targetId);
  if (!source || !target || source === target) return {document: d, conflicts: ['Choose two different nodes.'], mapping: {}};
  const sourceCase=d.cases?.find(g=>g.nodes.includes(sourceId)),targetCase=d.cases?.find(g=>g.nodes.includes(targetId));
  if(sourceCase && targetCase && sourceCase!==targetCase) return {document:d,conflicts:['Remove or change the separate case declarations before joining these nodes.'],mapping:{}};
  const parent=new Map(d.nodes.map(n=>[n.id,n.id]));
  const find=id=>{while(parent.has(id)&&parent.get(id)!==id)id=parent.get(id);return id;};
  for(const b of d.branches)if(b.kind==='link')parent.set(find(b.from),find(b.to));
  const s=find(sourceId),t=find(targetId);
  if(s!==t && d.branches.some(b=>b.kind!=='link' &&
      (find(b.from)===s&&find(b.to)===t || find(b.from)===t&&find(b.to)===s)))
    conflicts.push('Merging these nodes would short-circuit a physical component through ideal connections.');
  for (const b of d.branches) if (b.kind !== 'link' &&
      ((b.from === sourceId && b.to === targetId) || (b.to === sourceId && b.from === targetId))) {
    conflicts.push('Merging these nodes would short-circuit a physical component.');
  }
  for (const [key, value] of Object.entries(source)) {
    if (['id', 'at'].includes(key) || value == null || value === '' || (key === 'kind' && value === 'free')) continue;
    if (target[key] == null || target[key] === '' || (key === 'kind' && target[key] === 'free')) target[key] = copy(value);
    else if (JSON.stringify(value) !== JSON.stringify(target[key])) conflicts.push(`Conflicting ${key}: ${value} / ${target[key]}`);
  }
  if (conflicts.length) return {document: copy(document), conflicts, mapping: {}};
  remap(d, sourceId, targetId);
  d.nodes = d.nodes.filter(n => n.id !== sourceId);
  const links = new Map();
  // Associations to a duplicate ideal link follow its surviving equivalent.
  for(let i=0;i<d.branches.length;i++) {
    const b=d.branches[i];if(b.kind!=='link')continue;
    const key=[b.from,b.to].sort().join('\0'),previous=links.get(key);
    if(b.from===b.to || previous!=null) {
      const replacement=b.from===b.to?'node:'+b.from:'branch:'+(d.branches[previous].id||'@'+previous);
      for(const collection of physical)for(const x of d[collection]||[])if(x.links)
        x.links=[...new Set(x.links.map(ref=>ref===`branch:@${i}` || b.id&&ref===`branch:${b.id}`?replacement:ref))];
    }else links.set(key,i);
  }
  links.clear();
  filterBranches(d, b => {
    if (b.kind !== 'link') return true;
    const key = [b.from, b.to].sort().join('\0');
    if (b.from === b.to || links.has(key)) return false;
    links.set(key,true); return true;
  });
  return {document: d, conflicts, mapping: {[sourceId]: targetId}, selection: {role: 'node', index: d.nodes.indexOf(target)}};
}
export function normalizeOverlaps(document) {
  let d = copy(document); const mapping = {}, conflicts = [];
  for (const n of [...d.nodes]) {
    // Re-resolve after each pure proposal, which replaces every object.
    const source = d.nodes.find(x => x.id === n.id);
    if (!source?.at) continue;
    const target = d.nodes.find(x => x.id !== source.id && x.at && x.at.every((v, i) => v === source.at[i]));
    if (!target) continue;
    const a = emptyFree(target) && !emptyFree(source) ? target : source;
    const b = a === source ? target : source;
    const proposal = mergeNodes(d, a.id, b.id);
    if (proposal.conflicts.length) conflicts.push(...proposal.conflicts);
    else { d = proposal.document; Object.assign(mapping, proposal.mapping); }
  }
  for(const id of Object.keys(mapping)) {let target=mapping[id];while(mapping[target])target=mapping[target];mapping[id]=target;}
  return {document: d, mapping, conflicts};
}
export function detachEndpoint(document, role, index, end, position) {
  const d = copy(document), x = d[role === 'branch' ? 'branches' : 'sources'][index];
  if (!x || !x[end]) return {document: d, conflicts: ['Endpoint no longer exists.']};
  const n = d.nodes.find(n => n.id === x[end]);
  const id = fresh(d);
  const group=d.cases?.find(g=>g.nodes.includes(x[end]));if(group)group.nodes.push(id);
  d.nodes.push({id, at: position || [(n?.at?.[0] || 0) + 20, (n?.at?.[1] || 0) + 20]});
  x[end] = id;
  return {document: d, conflicts: [], mapping: {}, selection: {role, index}};
}
export function deleteNode(document, id) {
  let d = copy(document); const node = d.nodes.find(n => n.id === id);
  if (!node) return {document: d, conflicts: []};
  const removesRail=d.rail?.reference===id;
  let offset = 0;
  for (const role of ['branch', 'source']) {
    const key = role === 'branch' ? 'branches' : 'sources';
    for (let index = 0; index < (d[key] || []).length; index++) for (const end of ['from', 'to']) {
      if (d[key][index][end] !== id && !(removesRail && d[key][index][end]==='rail')) continue;
      const angle = offset++ * 2.399963229728653;
      const at = [(node.at?.[0] || 0) + Math.round(30 * Math.cos(angle)), (node.at?.[1] || 0) + Math.round(30 * Math.sin(angle))];
      d = detachEndpoint(d, role, index, end, at).document;
    }
  }
  d.nodes = d.nodes.filter(n => n.id !== id);
  if(d.cases)d.cases=d.cases.map(g=>({...g,nodes:g.nodes.filter(n=>n!==id)})).filter(g=>g.nodes.length);
  if(d.layout_options?.starts)d.layout_options.starts=d.layout_options.starts.filter(n=>n!==id);
  if (d.rail?.reference === id) delete d.rail;
  if (d.analysis?.network?.unknowns) d.analysis.network.unknowns = d.analysis.network.unknowns.filter(x => x !== id);
  for (const key of physical) for (const x of d[key] || []) if (x.links) x.links = x.links.filter(r => r !== `node:${id}`);
  return {document: d, conflicts: [], mapping: {}};
}
export function pruneEndpoints(document, candidates) {
  const d = copy(document);
  const referenced = id => [...d.branches, ...(d.sources || [])].some(x => x.from === id || x.to === id) ||
    d.rail?.reference === id || d.analysis?.network?.unknowns?.includes(id) ||
    d.cases?.some(g=>g.nodes.includes(id)) || d.layout_options?.starts?.includes(id) ||
    physical.some(key => (d[key] || []).some(x => x.links?.includes(`node:${id}`)));
  d.nodes = d.nodes.filter(n => !candidates.includes(n.id) || !emptyFree(n) || referenced(n.id));
  return d;
}

export function deletePath(document,role,index) {
  let d=copy(document),key=role==='branch'?'branches':'sources',removed=d[key]?.[index];
  if(!removed)return {document:d,conflicts:[]};
  if(role==='branch')filterBranches(d,(_b,i)=>i!==index);
  else {
    d.sources.splice(index,1);
    for(const collection of physical)for(const x of d[collection]||[])if(x.links)x.links=x.links.flatMap(ref=>{
      if(ref===`source:${removed.id}` || ref===`source:@${index}`)return [];
      const m=ref.match(/^source:@(\d+)$/);return m&&Number(m[1])>index?[`source:@${Number(m[1])-1}`]:[ref];
    });
  }
  d=pruneEndpoints(d,[removed.from,removed.to]);
  return {document:d,conflicts:[],mapping:{}};
}

export function addJunction(document, branchIndex, segment, at, nodeId) {
  const d=copy(document), b=d.branches[branchIndex];
  if(!b || (b.count || 1)>1) return {document:d,conflicts:['Choose an external connection lead.']};
  const a=d.nodes.find(n=>n.id===b.from)?.at, z=d.nodes.find(n=>n.id===b.to)?.at;
  if(!a || !z) return {document:d,conflicts:['Place the endpoints first.']};
  const route=[a,...(b.via||[]),z];
  if(segment<0 || segment>=route.length-1) return {document:d,conflicts:['Connection no longer exists.']};
  const lengths=route.slice(1).map((p,i)=>Math.hypot(p[0]-route[i][0],p[1]-route[i][1]));
  let symbolSegment=lengths.indexOf(Math.max(...lengths));
  if(b.at) {
    let best=Infinity;
    for(let i=0;i<lengths.length;i++) {
      const p=route[i],q=route[i+1],dx=q[0]-p[0],dy=q[1]-p[1];
      const t=Math.max(0,Math.min(1,((b.at[0]-p[0])*dx+(b.at[1]-p[1])*dy)/(lengths[i]**2||1)));
      const distance=Math.hypot(b.at[0]-p[0]-t*dx,b.at[1]-p[1]-t*dy);
      if(distance<best) {best=distance;symbolSegment=i;}
    }
  }
  const centre=b.at || route[symbolSegment].map((v,i)=>(v+route[symbolSegment+1][i])/2);
  const projection=p=>(p[0]-route[segment][0])*(route[segment+1][0]-route[segment][0])+(p[1]-route[segment][1])*(route[segment+1][1]-route[segment][1]);
  if(b.kind!=='link' && segment===symbolSegment && Math.hypot(at[0]-centre[0],at[1]-centre[1])<62)
    return {document:d,conflicts:['Place the junction on a connection lead, outside the component.']};
  const before=segment<symbolSegment || (segment===symbolSegment && projection(at)<projection(centre));
  const id=nodeId || fresh(d);
  if(!nodeId) d.nodes.push({id,at:[...at]});
  else {
    const existing=d.nodes.find(n=>n.id===nodeId);
    if(!existing)return {document:copy(document),conflicts:['The junction no longer exists.']};
    existing.at=[...at];
  }
  if(b.from===id || b.to===id) return {document:copy(document),conflicts:[]};
  const link={kind:'link',from:before?b.from:id,to:before?id:b.to};
  const leadVia=before?route.slice(1,segment+1):route.slice(segment+1,-1);
  if(leadVia.length) link.via=leadVia;
  b[before?'from':'to']=id;
  const remaining=before?route.slice(segment+1,-1):route.slice(1,segment+1);
  if(remaining.length) b.via=remaining; else delete b.via;
  if(b.kind!=='link' && !b.at) b.at=[...centre];
  d.branches.push(link);
  return {document:d,conflicts:[],mapping:{},selection:{role:'node',index:d.nodes.findIndex(n=>n.id===id)}};
}

// Coincident terminal leads attached to the same node are one connection.
// Interior crossings, even within a network, are not shared terminal leads.
export function sharedTerminalLead(document,candidates) {
  if(candidates.length<2)return null;
  const point=candidates[0].at;
  let common=null;
  for(const c of candidates) {
    if(Math.hypot(c.at[0]-point[0],c.at[1]-point[1])>1e-6)return null;
    const b=document.branches[c.index];
    if(!b)return null;
    const ends=[];
    if(c.i===0)ends.push(b.from);
    if(c.i===(b.via||[]).length)ends.push(b.to);
    if(ends.length===2) {
      const split=addJunction(document,c.index,c.i,c.at);
      if(split.conflicts.length)return null;
      const link=split.document.branches.at(-1);
      const endpoint=[link.from,link.to].find(id=>ends.includes(id));
      ends.splice(0,ends.length,endpoint);
    }
    common=common===null?ends:common.filter(id=>ends.includes(id));
  }
  return common?.length===1?{node:common[0],candidates}:null;
}

export function insertResistance(document,index,kind,options={}) {
  const {parallel=false,segment=0,at,properties={}}=options;
  if(!document.branches[index]) return {document:copy(document),conflicts:['The target path no longer exists.']};
  let d=copy(document),branch;
  if(parallel) {
    let target=d.branches[index];
    const a=d.nodes.find(n=>n.id===target.from)?.at,z=d.nodes.find(n=>n.id===target.to)?.at;
    if(!a||!z)return {document:d,conflicts:['Place the target endpoints first.']};
    const dx=z[0]-a[0],dy=z[1]-a[1],length=Math.hypot(dx,dy);
    if(!length)return {document:d,conflicts:['The target endpoints overlap.']};
    const axis=[dx/length,dy/length],normal=[-axis[1],axis[0]];
    const project=p=>[(p[0]-a[0])*axis[0]+(p[1]-a[1])*axis[1],(p[0]-a[0])*normal[0]+(p[1]-a[1])*normal[1]];
    const rects=(options.obstacles||[]).map(item=>{
      const [x,y,xx,yy]=item.bounds||item;
      const corners=[[x,y],[x,yy],[xx,y],[xx,yy]].map(project);
      return {owner:item,box:[Math.min(...corners.map(p=>p[0])),Math.min(...corners.map(p=>p[1])),
        Math.max(...corners.map(p=>p[0])),Math.max(...corners.map(p=>p[1]))]};
    });
    // Reserve an axial lead before either riser. Endpoint decorations travel
    // with their nodes; creating space in the middle preserves those collars.
    const endpointRects=id=>rects.filter(r=>r.owner.nodeId===id || !r.owner.bounds && r.box[0]<= (id===target.from?0:length) && r.box[2]>=(id===target.from?0:length));
    const left=Math.ceil(Math.max(40,...endpointRects(target.from).map(r=>r.box[2]+24))/10)*10;
    const right=Math.ceil(Math.max(40,...endpointRects(target.to).map(r=>length-r.box[0]+24))/10)*10;
    const required=2*Math.max(left,right)+220;
    const expanded=expandSegment(d,index,0,required,true);
    if(expanded.error)return {document:copy(document),conflicts:[expanded.error]};
    d=expanded.document;target=d.branches[index];
    const distance=expanded.movement?.distance||0,span=length+distance;
    // Sibling parallel bodies follow the expanded middle, while their outer
    // waypoints and the downstream chain follow their respective endpoints.
    if(distance) for(let i=0;i<d.branches.length;i++) {
      const b=d.branches[i],old=document.branches[i];
      if(i!==index && old.at && [target.from,target.to].includes(old.from) && [target.from,target.to].includes(old.to))
        b.at=old.at.map((v,k)=>v+axis[k]*distance/2);
    }
    const points=d.nodes.filter(n=>n.at).map(n=>n.at).concat(d.branches.flatMap(b=>[...(b.via||[]),...(b.at?[b.at]:[])]));
    const offsets=points.map(project).filter(p=>p[0]>=0&&p[0]<=span).map(p=>p[1]);
    const sign=offsets.filter(v=>v< -10).length<=offsets.filter(v=>v>10).length?-1:1;
    const offset=sign*Math.ceil(Math.max(100,Math.max(0,...offsets.map(v=>v*sign))+100,
      ...rects.filter(r=>r.box[2]>=0&&r.box[0]<=length).map(r=>(sign<0?-r.box[1]:r.box[3])+70))/10)*10;
    const world=p=>a.map((v,i)=>v+axis[i]*p[0]+normal[i]*p[1]);
    const via=[[left,0],[left,offset],[span-right,offset],[span-right,0]].map(world);
    branch={...copy(properties),from:target.from,to:target.to,kind,via,at:world([(left+span-right)/2,offset])};
    delete branch.angle;
    d.branches.push(branch);
  } else {
    const shared=options.sharedLead;
    if(shared && !sharedTerminalLead(d,shared.candidates))
      return {document:d,conflicts:['The shared connection has changed.']};
    const split=addJunction(d,index,segment,at);
    if(split.conflicts.length)return split;
    d=split.document;const added=d.branches.length-1;
    if(shared) {
      const junction=d.nodes[split.selection.index].id;
      for(const candidate of shared.candidates) {
        if(candidate.index===index)continue;
        const next=addJunction(d,candidate.index,candidate.i,at,junction);
        if(next.conflicts.length)return {document:copy(document),conflicts:next.conflicts};
        d=next.document;
        // Only the first copy of the shared ideal lead becomes a resistance.
        d.branches.pop();
      }
    }
    const b=d.branches[added],a=d.nodes.find(n=>n.id===b.from).at,z=d.nodes.find(n=>n.id===b.to).at;
    const route=[a,...(b.via||[]),z],lengths=route.slice(1).map((p,i)=>Math.hypot(p[0]-route[i][0],p[1]-route[i][1]));
    const expanded=expandSegment(d,added,lengths.indexOf(Math.max(...lengths)),220);
    if(expanded.error)return {document:copy(document),conflicts:[expanded.error]};
    d=expanded.document;branch=d.branches[added];Object.assign(branch,copy(properties),{from:branch.from,to:branch.to,kind});
    delete branch.at;delete branch.angle;
  }
  if(!branch.id) {
    const ids=new Set(d.branches.filter(b=>b!==branch).map(b=>b.id));
    let id=1;while(ids.has('r'+id))id++;branch.id='r'+id;
  }
  return {document:d,conflicts:[],selection:{role:'branch',index:d.branches.length-1},mapping:{}};
}

export function relocateResistance(document,sourceIndex,targetIndex,options) {
  const source=document.branches[sourceIndex];
  if(!source || sourceIndex===targetIndex)return {document:copy(document),conflicts:['Choose a different target component.']};
  const ends=[source.from,source.to];
  if(ends.some(id=>document.branches.filter(b=>b.from===id||b.to===id).length!==1 ||
      (document.sources||[]).some(s=>s.from===id||s.to===id) || !emptyFree(document.nodes.find(n=>n.id===id))))
    return {document:copy(document),conflicts:['Only isolated resistances can be inserted by moving.']};
  let d=copy(document);
  const unknown=d.analysis?.network?.resistance_unknowns?.includes(sourceIndex);
  filterBranches(d,(_b,i)=>i!==sourceIndex);d=pruneEndpoints(d,ends);
  const properties=copy(source);for(const key of ['from','to','at','via','angle'])delete properties[key];
  const sharedLead=options.sharedLead?{...options.sharedLead,candidates:options.sharedLead.candidates.map(c=>({...c,index:c.index-(sourceIndex<c.index?1:0)}))}:undefined;
  const result=insertResistance(d,targetIndex-(sourceIndex<targetIndex?1:0),source.kind||'cond',{...options,sharedLead,properties});
  if(unknown && !result.conflicts.length)result.document.analysis.network.resistance_unknowns.push(result.document.branches.length-1);
  return result;
}
