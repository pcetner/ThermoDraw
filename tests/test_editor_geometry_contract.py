"""Terminal, routed-group and export contracts independent of UI gestures."""
import math
import pytest
from thermodraw import Diagram,layout
from thermodraw import _editor

def network(angle=0,count=None,arrangement=None):
    b={'id':'r','from':'a','to':'b','kind':'rad','value':10,
       'via':[[0,-200],[600,-200]],'at':[300,-200],'angle':angle}
    if count:b.update(count=count,arrangement=arrangement)
    return {'units':{'R':'K/W','T':'K'},'nodes':[{'id':'a','at':[0,0]},{'id':'b','at':[600,0]}],
            'branches':[b]}

@pytest.mark.parametrize('angle',[0,45,90,135,180,225,270,315])
def test_connected_routes_meet_actual_terminal_tips(angle):
    placements=layout(Diagram.from_dict(network(angle)))
    symbol=next(p for p in placements if p.role=='branch' and p.element=='symbol')
    ends=[point for p in placements if p.role=='branch' and p.element=='wire' for point in (p.points[0],p.points[-1])]
    theta=math.radians(angle)
    for x,y in symbol.symbol.terminals:
        target=(symbol.at[0]+x*math.cos(theta)-y*math.sin(theta),symbol.at[1]+x*math.sin(theta)+y*math.cos(theta))
        assert any(math.dist(target,p)<1e-9 for p in ends)

@pytest.mark.parametrize('arrangement',['series','parallel'])
@pytest.mark.parametrize('count',[2,3,8,1000000])
def test_repeated_routes_preserve_external_leads_and_bound_svg_size(arrangement,count):
    data=network(count=count,arrangement=arrangement)
    d=Diagram.from_dict(data);placements=layout(d)
    ends=[point for p in placements if p.role=='branch' and p.element=='wire' for point in (p.points[0],p.points[-1])]
    assert (0,0) in ends and (600,0) in ends
    assert (0,-200) in ends and (600,-200) in ends
    assert d.to_dict()['branches'][0]['via']==data['branches'][0]['via']
    if count>100:assert len(placements)<50
    assert len(d.svg())<200000

@pytest.mark.parametrize('angle',[0,45,90])
def test_notation_and_export_share_terminals_and_centres(angle):
    data=network(angle)
    scenes=[_editor.scene(data,notation=n) for n in ('boxes','zigzags')]
    hits=[next(h for h in s['hits'] if h['role']=='branch' and h['element']=='symbol') for s in scenes]
    assert hits[0]['at']==hits[1]['at']
    assert hits[0]['terminals']==hits[1]['terminals']
    assert hits[0]['terminal_half']>hits[0]['half_len']
    for notation in ('boxes','zigzags'):
        svg=_editor.export(data,'svg','light',notation,{'mode':'scientific'})
        assert '1e1 K/W' in svg
        assert '@font-face' in svg
