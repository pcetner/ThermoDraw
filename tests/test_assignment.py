"""Independent regression calculations from the HW3 workflows."""
import copy
import json
import math
import pytest
from thermodraw import Diagram, solve_physics


def wall(**extra):
    data = dict(units={'T':'°C','R':'K/W','q':'W'},
                nodes=[{'id':'a','kind':'fixed','value':70}, {'id':'b','value':126}],
                branches=[{'id':'wall','from':'a','to':'b','value':.007}],
                sources=[{'to':'b','kind':'flow','value':8000}],
                analysis={'network':{'steady':True,'unknowns':['b']}})
    data.update(extra)
    return Diagram.from_dict(data)


def test_negative_arrow_retains_results_but_cannot_apply_as_verified():
    d=wall(sources=[{'from':'b','kind':'flow','value':-8000}])
    before=d.to_dict()
    result=solve_physics(d)
    assert result.components[0]['temperatures']['b']==pytest.approx(126)
    assert result.components[0]['status']=='direction-conflict'
    assert result.updates==[]
    assert 'source-direction-conflict' in [f.code for f in d.check(physics=True).findings]
    assert d.to_dict()==before


def test_glass_tolerance_is_explicit_and_override_does_not_mutate():
    d=wall(nodes=[{'id':'a','kind':'fixed','value':90},{'id':'b','kind':'fixed','value':0}],
           sources=[],branches=[{'from':'a','to':'b','value':.078125,'rate':1000}],analysis={})
    before=d.to_dict()
    loose=d.check(physics=True)
    strict=d.check(physics=True,check_policy='analysis')
    assert not any(f.code=='rate-does-not-match' for f in loose.findings)
    assert any(f.code=='rate-does-not-match' for f in strict.findings)
    assert strict.to_dict()['physics']['relative']==.01
    assert '1.0%' in strict.text()
    assert d.to_dict()==before


def test_capacitance_unit_warning_preserves_drawing():
    d=Diagram.from_dict({'units':{'C':'furlongs','T':'K'},'nodes':[{'id':'n','value':300}],
                         'rail':{'reference':'n'},'branches':[{'from':'n','to':'rail','kind':'cap','value':4}]})
    assert '<svg' in d.svg()
    assert 'capacitance-unit-invalid' in [f.code for f in d.check(physics=True).findings]


def test_signed_rate_is_an_additive_convention():
    d=wall(branches=[{'id':'wall','from':'a','to':'b','value':.007,'rate':-8000,'rate_convention':'signed'}])
    assert solve_physics(d).status=='solved'
    assert not any(f.code=='rate-does-not-match' for f in d.check(physics=True).findings)
    d.branches[0].rate_convention=None
    assert solve_physics(d).status!='solved'


@pytest.mark.parametrize('kind,value,unit,runit,qunit',[
    ('area',2,'m²','K*m²/W','W/m²'),('length',300,'cm','K*m/W','W/m')])
def test_normalized_network_keeps_watts_and_converts_display(kind,value,unit,runit,qunit):
    from thermodraw import convert_basis
    d=wall()
    normalized=convert_basis(d,{'kind':kind,'value':value,'unit':unit})
    result=solve_physics(normalized)
    assert result.status=='solved'
    assert result.components[0]['temperatures']['b']==pytest.approx(126)
    rate=result.components[0]['branch_rates'][0]
    assert rate['watts']==pytest.approx(-8000)
    assert rate['display_value']==pytest.approx(-8000/(2 if kind=='area' else 3))
    assert normalized.units['R']==runit
    assert normalized.units['q']==qunit
    assert not any(f.code=='physics-not-checked' for f in normalized.check(physics=True).findings)
    assert solve_physics(convert_basis(normalized,{'kind':'total'})).components[0]['temperatures']['b']==pytest.approx(126)
    assert normalized.to_dict()==Diagram.from_json(normalized.to_json()).to_dict()
    assert 'Per '+kind in normalized.svg()


def test_unknown_normalized_resistance_applies_in_declared_units():
    from thermodraw import convert_basis
    d=wall(analysis={'network':{'steady':True,'resistance_unknowns':['wall']}})
    d=convert_basis(d,{'kind':'area','value':2,'unit':'m²'})
    d.branches[0].value=None
    result=solve_physics(d)
    assert result.status=='solved'
    assert result.apply(d).branches[0].value==pytest.approx(.014)


def test_dimension_conflict_is_specific():
    d=wall(network_basis={'kind':'area','value':1,'unit':'m²'})
    assert solve_physics(d).status=='not-solved'
    assert 'incompatible dimensions' in str(solve_physics(d).coverage)


def spec(kind,**values):
    from thermodraw.derivations import INPUTS
    return {'kind':kind,'inputs':{k:{'value':v,'unit':INPUTS[kind][k]} for k,v in values.items()}}


@pytest.mark.parametrize('record,expected',[
    (spec('plane',L=.35,k=50,A=1),.007),
    (spec('cylinder',r1=.0015,r2=.0035,k=.13,L=1),math.log(.0035/.0015)/(2*math.pi*.13)),
    (spec('sphere',r1=2,r2=2.25,k=.06),(1/2-1/2.25)/(4*math.pi*.06)),
    (spec('convection',h=15,A=2),1/30),
    (spec('contact',contact_resistivity=.05,A=2),.025)])
def test_resistance_formula_helpers(record,expected):
    from thermodraw import derive_resistance
    assert derive_resistance(record)==pytest.approx(expected)


def test_derivation_owns_stale_value_and_input_is_pure():
    d=wall(branches=[{'id':'wall','from':'a','to':'b','value':999,'derivation':spec('plane',L=.35,k=50,A=1)}])
    original=d.to_dict()
    result=solve_physics(d)
    assert result.status=='solved'
    assert result.components[0]['temperatures']['b']==pytest.approx(126)
    assert result.apply(d).branches[0].value==pytest.approx(.007)
    assert '.007' in d.svg()
    assert d.to_dict()==original


def test_invalid_derivation_never_uses_cached_value():
    d=wall(branches=[{'from':'a','to':'b','value':.007,'derivation':spec('plane',L=-.35,k=50,A=1)}])
    assert solve_physics(d).status=='not-solved'
    assert 'derivation-invalid' in [f.code for f in d.check(physics=True).findings]


def test_storage_is_signed_finite_interval_and_needs_no_rail():
    from thermodraw import derive_storage
    relation={'capacity_derivation':spec('capacity',rho=1000,cp=4200,V=1),
              'delta_t':{'value':-2,'unit':'K'},'duration':{'value':1,'unit':'h'}}
    result=derive_storage(relation)
    assert result['energy_j']==-8400000
    assert result['watts']==pytest.approx(-8400000/3600)
    d=Diagram.from_dict({'control_volumes':[{'id':'v','storage_relation':relation,'generation':0}],
                        'control_surfaces':[{'id':'s','volume':'v'}],
                        'transfers':[{'id':'q','surface':'s','direction':'out'}],
                        'analysis':{'volumes':{'v':{'entity':'transfer','id':'q','field':'rate'}}}})
    solved=solve_physics(d)
    assert solved.status=='solved'
    assert solved.apply(d).transfers[0].rate==pytest.approx(8400000/3600)
    relation['duration']['value']=0
    with pytest.raises(ValueError):derive_storage(relation)


def test_structured_labels_escape_measure_and_roundtrip():
    from thermodraw.core import RichText,measure,text_w
    runs=[{'text':'C'},{'text':'p','position':'subscript'},{'text':'<&'},{'text':'2','position':'superscript'}]
    d=wall();d.nodes[0].label_runs=runs
    svg=d.svg()
    assert '&lt;&amp;' in svg and 'dy="-4"' in svg
    assert measure(RichText(runs).markup(),10)==pytest.approx(text_w('C<&',10)+text_w('p2',7))
    assert Diagram.from_json(d.to_json()).nodes[0].label_runs==runs


def test_wrapping_orientation_and_independent_cases():
    d=wall(nodes=[{'id':str(i),'value':i} for i in range(6)],sources=[],
           branches=[{'from':str(i),'to':str(i+1),'value':1} for i in range(5)],analysis={},
           layout_options={'max_width':640,'wrap':True,'stack':True,'starts':['0']})
    from thermodraw import solve
    placed=solve(d)
    assert len({n.at[1] for n in placed.nodes})>1
    assert placed.nodes[0].at[0]<placed.nodes[1].at[0]
    assert all(n.at is None for n in d.nodes)
    d=wall(nodes=[{'id':n,'value':300} for n in ('a','b','c','d')],sources=[],
           branches=[{'from':'a','to':'b','value':1},{'from':'c','to':'d','value':1}],analysis={},
           layout_options={'stack':True},cases=[{'id':'one','nodes':['a','b']},{'id':'two','nodes':['c','d']}])
    assert not any(f.code=='network-in-pieces' for f in d.check().findings)
    d.cases[1]['nodes']=['c']
    assert any(f.code=='network-in-pieces' for f in d.check().findings)


def test_transfer_own_shaft_is_checked_and_label_can_be_hidden():
    d=Diagram.from_dict({'transfers':[{'id':'q','at':[100,100],'label':'crossed','label_offset':[0,0]}]})
    assert any(f.code=='label-collision' for f in d.check().findings)
    d.transfers[0].show_label=False
    assert 'crossed' not in d.svg()


def test_basis_conversion_refuses_symbols_and_does_not_touch_physical_budgets():
    from thermodraw import convert_basis
    d=wall();d.branches[0].value='Rwall'
    with pytest.raises(ValueError,match='symbolic'):
        convert_basis(d,{'kind':'area','value':2,'unit':'m²'})
    d=wall(control_volumes=[{'id':'v','storage':123,'storage_relation':{
        'capacity':{'value':4200,'unit':'J/K'},'delta_t':{'value':1,'unit':'K'},'duration':{'value':1,'unit':'h'}}}])
    converted=convert_basis(d,{'kind':'area','value':2,'unit':'m²'})
    assert converted.control_volumes==d.control_volumes


def test_normalized_per_value_conversion_uses_matching_dimensions():
    from thermodraw._session import convert_value
    assert convert_value(3,'K*m²/kW','K*m²/W','R')==pytest.approx(.003)
    assert convert_value(4,'kW/m','W/m','q')==4000
    with pytest.raises(ValueError):convert_value(3,'W','W/m','q')


def test_session_materializes_derived_known_values_without_solver_updates():
    from thermodraw._session import assess_physics
    d=wall(nodes=[{'id':'a','kind':'fixed','value':70},{'id':'b','kind':'fixed','value':126}],sources=[],
           branches=[{'from':'a','to':'b','value':999,'derivation':spec('plane',L=.35,k=50,A=1)}],analysis={'network':{'steady':True}})
    report=assess_physics(d)
    assert report['result']['updates']==[]
    assert report['applied']['branches'][0]['value']==pytest.approx(.007)


def test_capacitance_reference_missing_bad_units_and_cycles_never_use_cache():
    from thermodraw.derivations import evaluate
    data={'units':{'C':'seconds','T':'K'},'nodes':[{'id':'n','value':300}],
          'rail':{'reference':'n'},'branches':[{'id':'c','from':'n','to':'rail','kind':'cap','value':4200}],
          'control_volumes':[{'id':'v','storage':99,'storage_relation':{'branch':'c','delta_t':{'value':1,'unit':'K'},'duration':{'value':1,'unit':'h'}}}]}
    out,_,errors=evaluate(Diagram.from_dict(data))
    assert errors and out.control_volumes[0].storage is None
    data['units']['C']='J/K';data['control_volumes'][0]['storage_relation']['branch']='missing'
    assert evaluate(Diagram.from_dict(data))[2]
    data['branches'][0]['derivation']={'kind':'capacity','inputs':{'branch':'v'}}
    assert evaluate(Diagram.from_dict(data))[2]


def test_console_json_roundtrips_under_cp1252(tmp_path):
    import os,subprocess,sys
    from pathlib import Path
    d=wall();d.nodes[0].label='ΔT — 岩石'
    path=tmp_path/'unicode.json';path.write_text(d.to_json(),encoding='utf-8')
    env={**os.environ,'PYTHONPATH':str(Path(__file__).resolve().parents[1]/'src'),'PYTHONIOENCODING':'cp1252'}
    result=subprocess.run([sys.executable,'-m','thermodraw','describe',str(path),'--json'],env=env,capture_output=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout.decode('ascii'))
    assert any('ΔT — 岩石' in e['says'] for e in report['elements'])
    human=subprocess.run([sys.executable,'-m','thermodraw','describe',str(path)],env=env,capture_output=True)
    assert human.returncode==0 and b'\\u5ca9' in human.stdout


def test_shared_capacity_requires_every_storage_consumer_on_apply():
    import copy
    from pathlib import Path
    from thermodraw._session import assess_physics
    data=json.loads((Path(__file__).resolve().parents[1]/'examples/assignment/storage.json').read_text(encoding='utf-8'))
    second=copy.deepcopy(data['control_volumes'][0]);second['id']='second'
    data['control_volumes'].append(second)
    data['control_surfaces'].append({'id':'second-surface','volume':'second'})
    data['transfers'].append({'id':'second-heat','surface':'second-surface','direction':'in'})
    data['analysis']['volumes']['second']={'entity':'transfer','id':'second-heat','field':'rate'}
    scenario=copy.deepcopy(data)
    scenario['branches'][0]['derivation']['inputs']['rho']['value']=2000
    complete=assess_physics(data,scenario,systems=['volume:block','volume:second'])
    assert complete['applied']['branches'][0]['value']==8400000
    assert all(t['rate']==pytest.approx(8400000/3600) for t in complete['applied']['transfers'])
    partial=assess_physics(data,scenario,systems=['volume:block'])
    assert partial['applied'] is None
    assert any(i['status']=='application-limited' for i in partial['issues'])


def test_editor_budget_evaluates_storage_instead_of_stale_cache():
    from thermodraw._editor import scene
    relation={'capacity':{'value':4200,'unit':'J/K'},'delta_t':{'value':1,'unit':'K'},'duration':{'value':1,'unit':'h'}}
    data={'control_volumes':[{'id':'v','storage':999,'storage_relation':relation}]}
    actual=scene(data)['budgets']
    data['control_volumes'][0]['storage']=4200/3600
    assert actual==scene(data)['budgets']
