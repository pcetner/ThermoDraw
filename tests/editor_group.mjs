import {test} from 'node:test';
import assert from 'node:assert/strict';
import {groupProposal,expandSegment} from '../docs/editor/group.js';
const initial=()=>({nodes:[{id:'a',at:[0,0]},{id:'b',at:[200,0]}],branches:[{id:'r',from:'a',to:'b',value:10}],sources:[]});
test('count requires explicit arrangement and preserves per-component values',()=>{
  const d=initial();assert.ok(groupProposal(d,0,'2','').error);
  for(const bad of ['','0','-1','1.5','1e2','abc']) assert.ok(groupProposal(d,0,bad,'series').error);
  const series=groupProposal(d,0,'2','series');assert.equal(series.combined,20);
  const parallel=groupProposal(d,0,'2','parallel');assert.equal(parallel.combined,5);
  assert.equal(parallel.document.branches[0].value,10);assert.deepEqual(d,initial());
  const single=groupProposal(series.document,0,'1','series');assert.deepEqual(single.document,d);
  const cap=initial();cap.branches[0].kind='cap';assert.equal(groupProposal(cap,0,'2','series').combined,5);
  delete cap.branches[0].value;assert.equal(groupProposal(cap,0,'2','series').combined,null);
});
test('expansion is deterministic and moves physical objects without resizing',()=>{
  const d=initial();d.regions=[{id:'box',at:[220,10],size:[50,30]}];
  const p=expandSegment(d,0,0,400);
  assert.deepEqual(p.document.nodes.map(n=>n.at),[[0,0],[400,0]]);
  assert.deepEqual(p.document.regions[0],{id:'box',at:[420,10],size:[50,30]});
  assert.deepEqual(p,expandSegment(d,0,0,400));assert.equal(d.nodes[1].at[0],200);
});
