"""Resistance identification uses independent conservation equations."""
import copy
import pytest
from thermodraw import Diagram, DiagramError, solve_physics, assess_physics


def case():
    return {'units':{'T':'K','R':'K/W','P':'W','q':'W'},
            'nodes':[{'id':'hot','value':400},{'id':'cold','kind':'fixed','value':300}],
            'branches':[{'id':'r','from':'hot','to':'cold','value':99}],
            'sources':[{'kind':'diss','to':'hot','value':20}],
            'analysis':{'network':{'steady':True,'unknowns':[], 'resistance_unknowns':['r']}}}


def test_resistance_and_complete_scenario_application():
    data=case();original=copy.deepcopy(data)
    result=solve_physics(Diagram.from_dict(data))
    assert result.status=='solved'
    assert result.updates[0]['value']==pytest.approx(5)
    assert result.apply(Diagram.from_dict(data)).branches[0].value==pytest.approx(5)
    report=assess_physics(data)
    assert report['applied']['branches'][0]['value']==pytest.approx(5)
    assert report['comparisons'][0]['original']==99
    assert data==original


def test_mixed_temperature_and_resistance():
    d=case();d['nodes'].insert(1,{'id':'mid'})
    d['branches'][0]['to']='mid'
    d['branches'].append({'from':'mid','to':'cold','value':3})
    d['analysis']['network']['unknowns']=['mid']
    result=solve_physics(Diagram.from_dict(d))
    assert result.status=='solved'
    assert {u['entity']:u['value'] for u in result.updates}==pytest.approx({'node':360,'branch':2})


@pytest.mark.parametrize('temperature,power,message',[
    (300,0,'indeterminate'),(400,0,'no finite resistance'),(400,-20,'nonpositive')])
def test_invalid_or_indeterminate_resistance(temperature,power,message):
    d=case();d['nodes'][0]['value']=temperature;d['sources'][0]['value']=power
    result=solve_physics(Diagram.from_dict(d))
    assert not result.updates
    assert message in ' '.join(result.components[0]['diagnostics'])


def test_parallel_resistances_require_independent_information():
    d=case();d['branches'].append({'id':'r2','from':'hot','to':'cold'})
    d['analysis']['network']['resistance_unknowns'].append('r2')
    result=solve_physics(Diagram.from_dict(d))
    assert result.components[0]['status']=='underdetermined'
    d['branches'][0]['rate']=5
    result=solve_physics(Diagram.from_dict(d))
    assert result.status=='solved'
    assert [u['value'] for u in result.updates]==pytest.approx([20,100/15])


@pytest.mark.parametrize('arrangement,expected',[('parallel',10),('series',2.5)])
def test_repeated_resistance_returns_per_item_value(arrangement,expected):
    d=case();d['branches'][0].update(count=2,arrangement=arrangement)
    result=solve_physics(Diagram.from_dict(d))
    assert result.updates[0]['value']==pytest.approx(expected)


def test_legacy_index_and_units():
    d=case();del d['branches'][0]['id'];d['analysis']['network']['resistance_unknowns']=[0]
    d['units']['R']='K/kW'
    result=assess_physics(d)
    assert result['applied']['branches'][0]['value']==pytest.approx(5000)
    assert result['comparisons'][0]['index']==0


@pytest.mark.parametrize('target',[[True],['absent'],[10],['r',0]])
def test_invalid_resistance_targets(target):
    d=case();d['analysis']['network']['resistance_unknowns']=target
    with pytest.raises(DiagramError):Diagram.from_dict(d)



def test_known_series_rate_assertion_agrees_after_application():
    d=case();d['branches'][0].update(count=2,arrangement='series',rate=20)
    original=Diagram.from_dict(d)
    applied=solve_physics(original).apply(original)
    applied.analysis['network']['resistance_unknowns']=[]
    assert solve_physics(applied,check_supplied=True).status=='solved'


def test_badge_reservation_is_centered_and_clear_of_symbol():
    from thermodraw._editor import scene
    d=case();d['nodes'][0]['at']=[200,200];d['nodes'][1]['at']=[600,200]
    out=scene(d,adornments=[{'role':'branch','index':0,'width':120,'height':21}])
    label=next(h for h in out['hits'] if h['role']=='branch' and h['element']=='label')
    badge=out['adornments'][0]['bounds']
    assert badge[0]+badge[2]/2==pytest.approx((label['bounds'][0]+label['bounds'][2])/2)
    assert badge[1]+badge[3]<=label['bounds'][1]+1e-8
    symbol=next(h for h in out['hits'] if h['role']=='branch' and h['element']=='symbol')['bounds']
    assert badge[0]+badge[2]<=symbol[0] or badge[0]>=symbol[2] or badge[1]+badge[3]<=symbol[1] or badge[1]>=symbol[3]
    assert out['adornments'][0]['clear']


def test_parallel_rate_assertion_is_group_total_in_solver_and_checker():
    d=case();d['branches'][0].update(count=2,arrangement='parallel',rate=20)
    result=solve_physics(Diagram.from_dict(d))
    assert result.status=='solved'
    assert result.updates[0]['value']==pytest.approx(10)
    applied=result.apply(Diagram.from_dict(d))
    assert not [f for f in applied.check(physics=True).findings if f.code=='rate-does-not-match']
    assert solve_physics(applied).status=='solved'
