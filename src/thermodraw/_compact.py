"""Optional measured chain wrapping. Explicit coordinates always win."""
import copy
import math


def components(d):
    graph: dict[str, set[str]] = {n.id:set() for n in d.nodes}
    for b in d.branches:
        if b.source in graph and b.target in graph:
            graph[b.source].add(b.target); graph[b.target].add(b.source)
    groups=[]; seen=set()
    for n in d.nodes:
        if n.id in seen: continue
        pending=[n.id]; group=set()
        while pending:
            v=pending.pop()
            if v in group: continue
            group.add(v);pending.extend(graph[v]-group)
        seen |= group; groups.append([n.id for n in d.nodes if n.id in group])
    return groups


def place(d, start_y=150.0):
    from . import _solve as S
    from .model import DiagramError
    from ._layout import layout
    from ._render import compose
    out=copy.deepcopy(d); options=out.layout_options; y=start_y; offset_x=0.0
    for ids in components(out):
        sub=copy.deepcopy(out)
        sub.nodes=[n for n in sub.nodes if n.id in ids]
        sub.branches=[b for b in sub.branches if b.source in ids and (b.target in ids or b.target=='rail') or b.target in ids and b.source=='rail']
        sub.sources=[s for s in sub.sources if s.node in ids]
        sub.cases=[];sub.layout_options={};sub.analysis={}
        for key in ('regions','control_volumes','control_surfaces','transfers','annotations'): setattr(sub,key,[])
        # Shared rails belong to the full diagram, not to temporary components.
        if sub.rail and sub.rail.reference not in ids: sub.rail.reference=ids[0]
        if any(n.at is not None for n in sub.nodes):
            placed=S.solve(sub)
        else:
            order=S._chain(sub)
            starts=[n for n in options.get('starts',[]) if n in ids]
            if len(starts)>1 or starts and starts[0] not in (order[0],order[-1]):
                raise DiagramError('Specify at most one starting endpoint for each chain')
            if starts and starts[0]==order[-1]:order.reverse()
            first=S._place(sub,order,{})
            room=S._room(first,order)
            placed=copy.deepcopy(sub)
            left=200.0+offset_x; right=left+max(0,options.get('max_width',640)-180)
            x=left; row_y=y; direction=1
            for i,ident in enumerate(order):
                if i:
                    need=max(S.PITCH,10*math.ceil(room.get((order[i-1],ident),0)/10))
                    candidate=x+direction*need
                    if options.get('wrap') and (candidate>right or candidate<left):
                        row_y+=max(240,need); direction*=-1
                    else:x=candidate
                placed.node(ident).at=[x,row_y]
            S._route_pairs(placed)
            S._place_sources(placed,order)
            # Source and capacitance placement can require a vertical label frame.
            placed=S._with_rail(placed)
        for n in placed.nodes:
            original=out.node(n.id)
            if original.at is None:
                original.at=list(n.at); original.angle=n.angle
        for index, source in enumerate(placed.sources):
            original=[s for s in out.sources if s.node in ids][index]
            if original.at is None:original.at=source.at;original.angle=source.angle
        originals=[b for b in out.branches if b.source in ids and (b.target in ids or b.target=='rail') or b.target in ids and b.source=='rail']
        for original,branch in zip(originals,placed.branches):
            if not original.via and original.at is None:original.via=branch.via
        scene=compose(layout(placed))
        if options.get('stack'):y=max(y,scene.box[3]+140)
        else:offset_x=max(offset_x,scene.box[2]+140-200)
    return S._with_rail(out)


def relayout(d, node=None):
    """Explicitly replace placement for one connected component or the whole network."""
    out=copy.deepcopy(d)
    ids={n.id for n in out.nodes} if node is None else next((set(g) for g in components(out) if node in g),set())
    if node is not None and not ids: raise ValueError('Select a node in the component to re-layout')
    for n in out.nodes:
        if n.id in ids:n.at=None
    for b in out.branches:
        if b.source in ids or b.target in ids:b.at=None;b.via=[];b.angle=None
    for s in out.sources:
        if s.node in ids:s.at=None
    if out.rail and node is None:out.rail.y=None;out.rail.span=None
    out.layout_options={'max_width':640,'wrap':True,'stack':True,**out.layout_options}
    # Keep a selected component clear of the surviving authored components.
    # Their coordinates, routes and labels remain untouched.
    start_y=150.0
    if node is not None:
        others=copy.deepcopy(out)
        others.nodes=[n for n in others.nodes if n.id not in ids]
        others.branches=[b for b in others.branches if b.source not in ids and b.target not in ids]
        others.sources=[s for s in others.sources if s.node not in ids]
        others.analysis={};others.cases=[];others.layout_options={};others.rail=None
        others.branches=[b for b in others.branches if 'rail' not in (b.source,b.target)]
        for volume in others.control_volumes:volume.storage_relation=None
        if others.nodes and all(n.at is not None for n in others.nodes):
            from ._render import compose
            from ._layout import layout
            start_y=max(start_y,compose(layout(others)).box[3]+140)
    return place(out,start_y)
