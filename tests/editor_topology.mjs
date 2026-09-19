import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {mergeNodes, normalizeOverlaps, deleteNode, pruneEndpoints, addJunction,insertResistance,deletePath,relocateResistance,sharedTerminalLead} from '../docs/editor/topology.js';
const diagram = () => ({nodes:[{id:'a',at:[0,0]},{id:'b',kind:'fixed',value:20,at:[0,0]},{id:'c',at:[200,0]}],branches:[{from:'a',to:'c',value:10}],sources:[]});

test('shared terminal insertion preserves parallel values and moved resistance identity',()=>{
  const d={nodes:[{id:'x',at:[-400,0]},{id:'y',at:[-200,0]},{id:'a',at:[0,0]},{id:'b',at:[600,0],kind:'fixed',value:20}],
    branches:[{id:'moving',from:'x',to:'y',value:30},
      {id:'first',from:'a',to:'b',at:[300,0],value:10},
      {id:'second',from:'b',to:'a',at:[300,100],value:20,via:[[520,0],[520,100],[80,100],[80,0]]}]};
  const candidates=[{index:1,i:0,at:[560,0]},{index:2,i:0,at:[560,0]}];
  const sharedLead=sharedTerminalLead(d,candidates);assert.equal(sharedLead.node,'b');
  const p=relocateResistance(d,0,1,{segment:0,at:[560,0],sharedLead});
  assert.deepEqual(p.conflicts,[]);assert.equal(p.document.branches.length,3);assert.equal(p.document.nodes.length,3);
  const [first,second,inserted]=p.document.branches;
  assert.equal(first.to,second.from);assert.equal(inserted.from,first.to);assert.equal(inserted.to,'b');
  assert.deepEqual([first.value,second.value,inserted.value],[10,20,30]);assert.equal(inserted.id,'moving');
  assert.equal(d.nodes.length,4);assert.equal(d.branches[1].to,'b');
  const unrelated=structuredClone(d);unrelated.branches[2].from='x';
  assert.equal(sharedTerminalLead(unrelated,candidates),null);
  assert.equal(sharedTerminalLead(d,[candidates[0],{...candidates[1],i:1}]),null);
  assert.equal(sharedTerminalLead(d,[candidates[0],{...candidates[1],at:[560,1]}]),null);
});
test('merge preserves target and references, including within the same network',()=>{
  const d=diagram(); d.branches.push({from:'b',to:'c',value:20});
  d.analysis={network:{unknowns:['a'],resistance_unknowns:[0]}};
  d.annotations=[{links:['node:a']}]; d.rail={reference:'a'};
  const p=mergeNodes(d,'a','b');
  assert.deepEqual(p.conflicts,[]); assert.equal(p.document.nodes.length,2);
  assert.equal(p.document.nodes[0].kind,'fixed');
  assert.equal(p.document.branches[0].value,10);
  assert.equal(p.document.branches[0].from,'b');
  assert.deepEqual(p.document.analysis.network.unknowns,['b']);
  assert.deepEqual(p.document.annotations[0].links,['node:b']);
  assert.equal(p.document.rail.reference,'b'); assert.equal(d.nodes.length,3);
});
test('conflicts and physical self loops leave original intact',()=>{
  const d=diagram();d.nodes[0].value=30;
  assert.ok(mergeNodes(d,'a','b').conflicts.length);
  delete d.nodes[0].value;d.branches.push({from:'a',to:'b'});
  const p=mergeNodes(d,'a','b');assert.ok(p.conflicts.length);assert.deepEqual(p.document,d);
});
test('all overlap pairs normalize in one proposal; near positions do not merge',()=>{
  const d=diagram();d.nodes.push({id:'d',at:[200,0],label:'Inner wall'},{id:'e',at:[200,1]});
  const p=normalizeOverlaps(d);assert.equal(p.document.nodes.length,3);
  assert.deepEqual(p.document.branches[0],{from:'b',to:'d',value:10});
});
test('junction deletion detaches three surviving components separately',()=>{
  const d=diagram();d.branches.push({from:'a',to:'b',kind:'link'});d.sources.push({to:'a',value:2});
  const p=deleteNode(d,'a').document;
  assert.equal(p.branches.length,2);assert.equal(p.sources.length,1);
  const ends=[p.branches[0].from,p.branches[1].from,p.sources[0].to];
  assert.equal(new Set(ends).size,3);assert.ok(ends.every(id=>p.nodes.some(n=>n.id===id)));
  assert.ok(!p.nodes.some(n=>n.id==='a'));assert.equal(d.nodes.length,3);
});
test('cleanup only removes unused empty candidate nodes',()=>{
  const d=diagram();d.branches=[];
  assert.deepEqual(pruneEndpoints(d,['a','b']).nodes.map(n=>n.id),['b','c']);
  d.annotations=[{links:['node:a']}];assert.equal(pruneEndpoints(d,['a']).nodes.length,3);
});
test('junction splits a lead without duplicating the physical resistance',()=>{
  const d=diagram();d.nodes[0].at=[-200,0];d.nodes[2].at=[200,0];
  const p=addJunction(d,0,0,[-150,0]);
  assert.deepEqual(p.conflicts,[]);assert.equal(p.document.branches.length,2);
  assert.equal(p.document.branches[0].value,10);assert.equal(p.document.branches[1].kind,'link');
  assert.equal(p.document.branches[1].to,p.document.branches[0].from);
  assert.ok(addJunction(d,0,0,[0,0]).conflicts.length);
});
test('supplied Insulation preserves all seven resistances and merges three pairs',()=>{
  const d=JSON.parse(readFileSync(new URL('./fixtures/editor/Insulation.json',import.meta.url),'utf8'));
  const p=normalizeOverlaps(d);assert.equal(p.document.nodes.length,6);assert.equal(p.document.branches.length,7);
  assert.equal(p.document.nodes.filter(n=>!n.kind||n.kind==='free').length,4);
  assert.ok(p.document.branches.every(b=>b.value==null));assert.equal(d.nodes.length,9);
});
test('supplied Just Ice Cream lead repairs using an ideal link',()=>{
  const d=JSON.parse(readFileSync(new URL('./fixtures/editor/Just-Ice-Cream.json',import.meta.url),'utf8'));
  const p=addJunction(d,0,1,[100,10],'n4');assert.deepEqual(p.conflicts,[]);
  assert.equal(p.document.nodes.length,5);assert.equal(p.document.branches.length,5);
  assert.equal(p.document.branches[0].from,'n4');assert.equal(p.document.branches.at(-1).kind,'link');
  assert.ok(p.document.branches.every(b=>b.value==null));
});
test('parallel insertion keeps independent values; series expands without replacing the target',()=>{
  const d=diagram();d.nodes[0].at=[-200,0];
  const parallel=insertResistance(d,0,'conv',{parallel:true,properties:{value:20}});
  assert.deepEqual(parallel.document.branches[0],d.branches[0]);
  assert.equal(parallel.document.branches[1].value,20);
  assert.ok(Math.abs(1/(1/parallel.document.branches[0].value+1/parallel.document.branches[1].value)-20/3)<1e-12);
  const series=insertResistance(d,0,'cond',{segment:0,at:[-150,0]});
  assert.deepEqual(series.conflicts,[]);assert.equal(series.document.branches[0].value,10);
  assert.equal(series.document.branches[1].value,undefined);
  assert.equal(series.document.branches.length,2);
  assert.ok(series.document.nodes.find(n=>n.id==='c').at[0]>200);
});


test('deleting a rail reference detaches rail branches and preserves all components',()=>{
  const d=diagram();d.rail={reference:'b',y:200};d.branches.push({kind:'cap',from:'c',to:'rail',value:2});
  const p=deleteNode(d,'b');assert.equal(p.document.branches.length,2);assert.equal(p.document.rail,undefined);
  assert.ok(p.document.branches.every(b=>b.from!=='rail'&&b.to!=='rail'));
});

test('deleting a path remaps numeric analysis and physical references',()=>{
  const d=diagram();d.branches.push({from:'b',to:'c',value:20});
  d.analysis={network:{resistance_unknowns:[1]}};d.annotations=[{links:['branch:@0','branch:@1']}];
  const p=deletePath(d,'branch',0).document;
  assert.deepEqual(p.analysis.network.resistance_unknowns,[0]);assert.deepEqual(p.annotations[0].links,['branch:@0']);
});

test('merge refuses a physical short through ideal leads',()=>{
  const d=diagram();d.nodes[0].at=[-100,0];d.branches=[{from:'a',to:'c',kind:'link'},{from:'c',to:'b',value:5}];
  assert.ok(mergeNodes(d,'a','b').conflicts.some(s=>s.includes('short-circuit')));
});

for(const kind of ['free','fixed','phase','break'])test('empty merge preserves '+kind+' target',()=>{
  const d=diagram();d.nodes[1].kind=kind;d.nodes[1].label='Target';
  assert.deepEqual(mergeNodes(d,'a','b').document.nodes[0],d.nodes[1]);
});

test('moved isolated resistance keeps its independent value and identity',()=>{
  const d=diagram();d.nodes[0].at=[-200,0];d.nodes.push({id:'x',at:[0,300]},{id:'y',at:[300,300]});
  d.branches.push({id:'moving',from:'x',to:'y',kind:'rad',value:20});
  const p=relocateResistance(d,1,0,{parallel:true});assert.deepEqual(p.conflicts,[]);
  assert.equal(p.document.branches[1].value,20);assert.equal(p.document.branches[1].id,'moving');
  assert.ok(!p.document.nodes.some(n=>['x','y'].includes(n.id)));
});

test('parallel leads clear measured endpoint labels in either orientation',()=>{
  for(const vertical of [false,true]) {
    const d=diagram();d.nodes=d.nodes.filter(n=>n.id!=='b');d.nodes[1].at=[400,0];
    d.branches.push({from:'a',to:'c',kind:'rad',via:[[0,-200],[400,-200]],at:[200,-200]});
    let labels=[[-80,18,80,62],[310,18,490,62]];
    if(vertical) {
      for(const n of d.nodes)n.at=[-n.at[1],n.at[0]];
      for(const b of d.branches){if(b.at)b.at=[-b.at[1],b.at[0]];if(b.via)b.via=b.via.map(p=>[-p[1],p[0]]);}
      labels=labels.map(([x,y,xx,yy])=>[-yy,x,-y,xx]);
    }
    const p=insertResistance(d,0,'cond',{parallel:true,obstacles:labels});
    assert.deepEqual(p.conflicts,[]);assert.deepEqual(p.document.branches[0],d.branches[0]);
    const route=[p.document.nodes[0].at,...p.document.branches.at(-1).via,p.document.nodes[1].at];
    const shift=p.document.nodes[1].at.map((v,i)=>v-d.nodes[1].at[i]);
    labels=labels.map((r,i)=>i?r.map((v,k)=>v+shift[k%2]):r);
    for(const [x,y,xx,yy] of labels)for(let i=1;i<route.length;i++) {
      const [a,b]=[route[i-1],route[i]];
      assert.ok(!(a[0]===b[0]&&a[0]>x&&a[0]<xx&&Math.max(a[1],b[1])>y&&Math.min(a[1],b[1])<yy),JSON.stringify(route));
      assert.ok(!(a[1]===b[1]&&a[1]>y&&a[1]<yy&&Math.max(a[0],b[0])>x&&Math.min(a[0],b[0])<xx),JSON.stringify(route));
    }
  }
});


test('case membership and layout starts follow node merges and deletion',()=>{
  const d={nodes:[{id:'a'},{id:'b'},{id:'c'}],branches:[],sources:[],cases:[{id:'one',nodes:['a','b','c']}],layout_options:{starts:['a']}};
  const merged=mergeNodes(d,'a','b');assert.deepEqual(merged.conflicts,[]);
  assert.deepEqual(merged.document.cases[0].nodes,['b','c']);assert.deepEqual(merged.document.layout_options.starts,['b']);
  const removed=deleteNode(merged.document,'b').document;
  assert.deepEqual(removed.cases[0].nodes,['c']);assert.deepEqual(removed.layout_options.starts,[]);
  const separate=structuredClone(d);separate.cases=[{id:'one',nodes:['a']},{id:'two',nodes:['b','c']}];
  assert.match(mergeNodes(separate,'a','b').conflicts[0],/case declarations/);
});

test('capacitance deletion leaves an unresolved stable reference, never another branch',()=>{
  const d={nodes:[{id:'a'},{id:'b'}],branches:[{id:'c',kind:'cap',from:'a',to:'b'},{id:'r',from:'a',to:'b',value:2}],sources:[],control_volumes:[{id:'v',storage_relation:{branch:'c'}}]};
  const removed=deletePath(d,'branch',0).document;
  assert.equal(removed.branches[0].id,'r');assert.equal(removed.control_volumes[0].storage_relation.branch,'c');
});
