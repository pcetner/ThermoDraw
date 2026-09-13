// Group edits always start with the committed snapshot, never a previous preview.
export function groupProposal(original,index,countText,arrangement) {
  const document=structuredClone(original),b=document.branches[index];
  const fail=message=>({document:structuredClone(original),error:message});
  if(!b) return fail('The component no longer exists.');
  if(!/^[1-9]\d*$/.test(String(countText)) || !Number.isSafeInteger(Number(countText))) return fail('Count must be a positive, safe integer.');
  const count=Number(countText);
  if(count>1 && !['series','parallel'].includes(arrangement)) return fail('Choose Series or Parallel.');
  if(count===1) {delete b.count;delete b.arrangement;}
  else {b.count=count;b.arrangement=arrangement;}
  const value=b.value==null || b.value==='' ? null : Number(b.value);
  const factor=count===1 ? 1 : (b.kind==='cap') === (arrangement==='parallel') ? count : 1/count;
  // Resistances in series add; capacitances in parallel add.
  const combined=Number.isFinite(value) && value!==null ? value*factor : null;
  if(combined!==null && !Number.isFinite(combined))return fail('The combined value exceeds the numeric range.');
  return {document,combined,error:null};
}

export function expandSegment(original,index,segment,required,betweenEndpoints=false) {
  const document=structuredClone(original),b=document.branches[index];
  const nodes=new Map(document.nodes.map(n=>[n.id,n]));
  const route=[nodes.get(b.from)?.at,...(b.via||[]),nodes.get(b.to)?.at];
  if(route.some(p=>!p)) return {document,error:'Place the group endpoints before changing its layout.'};
  const a=betweenEndpoints?route[0]:route[segment],z=betweenEndpoints?route.at(-1):route[segment+1];
  const length=Math.hypot(z[0]-a[0],z[1]-a[1]);
  if(!length) return {document,error:'The selected route segment has zero length.'};
  const distance=Math.max(0,Math.ceil((required-length)/10)*10);
  if(!distance) return {document,error:null};
  const u=[(z[0]-a[0])/length,(z[1]-a[1])/length];
  const cut=a.map((v,i)=>(v+z[i])/2);
  const downstream=p=>p && (p[0]-cut[0])*u[0]+(p[1]-cut[1])*u[1]>0;
  const shift=p=>p.map((v,i)=>v+u[i]*distance);
  const moved=new Set();
  for(const n of document.nodes) if(downstream(n.at)) {n.at=shift(n.at);moved.add(n.id);}
  for(const x of [...document.branches,...(document.sources||[])]) {
    if(downstream(x.at)) x.at=shift(x.at);
    if(x.via) x.via=x.via.map(p=>downstream(p)?shift(p):p);
  }
  if(original.branches[index].at) {
    const centre=original.branches[index].at;
    b.at=centre.map((v,i)=>v+u[i]*distance/2);
  }
  for(const key of ['regions','control_volumes','annotations','transfers']) for(const x of document[key]||[]) {
    if(downstream(x.at)) {x.at=shift(x.at);if(x.end) x.end=shift(x.end);}
  }
  return {document,error:null,movement:{distance,axis:u,nodes:[...moved]}};
}

export function clearGroupLanes(original,index,segment,halfEnvelope) {
  const document=structuredClone(original),branch=document.branches[index],nodes=new Map(document.nodes.map(n=>[n.id,n]));
  const route=[nodes.get(branch.from)?.at,...(branch.via||[]),nodes.get(branch.to)?.at];
  const a=route[segment],b=route[segment+1];
  if(!a||!b)return {document,error:'Place group endpoints before expanding lanes.'};
  const length=Math.hypot(b[0]-a[0],b[1]-a[1]);if(!length)return {document,error:'Choose a nonzero route segment.'};
  const u=[(b[0]-a[0])/length,(b[1]-a[1])/length],normal=[-u[1],u[0]],centre=a.map((v,i)=>(v+b[i])/2);
  const offset=p=>(p[0]-centre[0])*normal[0]+(p[1]-centre[1])*normal[1];
  const along=p=>(p[0]-centre[0])*u[0]+(p[1]-centre[1])*u[1];
  const endpoints=new Set([branch.from,branch.to]),obstacles=[];
  for(const n of document.nodes)if(n.at&&!endpoints.has(n.id))obstacles.push({at:n.at,margin:35});
  for(let i=0;i<document.branches.length;i++)if(i!==index) {
    const x=document.branches[i],p=nodes.get(x.from)?.at,q=nodes.get(x.to)?.at;
    if(p&&q)obstacles.push({at:x.at||p.map((v,k)=>(v+q[k])/2),margin:45});
    for(const at of x.via||[])obstacles.push({at,margin:15});
  }
  for(const key of ['regions','control_volumes'])for(const x of document[key]||[])
    obstacles.push({at:x.at.map((v,i)=>v+x.size[i]/2),margin:(Math.abs(normal[0])*x.size[0]+Math.abs(normal[1])*x.size[1])/2+20});
  for(const sign of [-1,1]) {
    const relevant=obstacles.filter(x=>Math.abs(along(x.at))<length/2+80 && offset(x.at)*sign>0);
    const required=Math.max(0,...relevant.map(x=>halfEnvelope-(offset(x.at)*sign-x.margin)));
    const distance=Math.ceil(required/10)*10;if(!distance)continue;
    const shift=p=>p.map((v,i)=>v+normal[i]*distance*sign);
    const affected=p=>p&&offset(p)*sign>0;
    for(const n of document.nodes)if(!endpoints.has(n.id)&&affected(n.at))n.at=shift(n.at);
    for(const x of [...document.branches,...(document.sources||[])]) {
      if(x===branch)continue;
      if(affected(x.at))x.at=shift(x.at);
      if(x.via)x.via=x.via.map(p=>affected(p)?shift(p):p);
    }
    for(const key of ['regions','control_volumes','annotations','transfers'])for(const x of document[key]||[])
      if(affected(x.size?x.at.map((v,i)=>v+x.size[i]/2):x.at)){x.at=shift(x.at);if(x.end)x.end=shift(x.end);}
  }
  return {document,error:null};
}
