"""Repository fixtures checked against equations independent of the evaluator."""
import math
from pathlib import Path
import pytest
from thermodraw import Diagram, solve, solve_physics

ROOT=Path(__file__).resolve().parents[1]/'examples'/'assignment'

def example(name):
    return Diagram.from_json((ROOT/(name+'.json')).read_text(encoding='utf-8'))

@pytest.mark.parametrize('name',['wall-sign','windows','storage','dorm-wall','composite-wall','wire','sphere'])
def test_assignment_fits_without_collision_and_preserves_placed_orientation(name):
    d=example(name)
    assert Diagram.from_json(d.to_json()).to_dict()==d.to_dict()
    placed=solve(d)
    report=placed.check()
    assert placed.describe().canvas[0]<=640 or any(f.code=='layout-width-exceeded' for f in report.findings)
    assert not [f for f in report.findings if f.severity in ('error','warning')]
    positions=[n.at for n in placed.nodes]
    for n in placed.nodes:
        if n.value is not None:n.value=-float(n.value)
    assert [n.at for n in solve(placed).nodes]==positions

def test_independent_expected_assignment_values():
    result=solve_physics(example('wall-sign'))
    assert result.components[0]['temperatures']['n1']==pytest.approx(126)
    assert result.components[0]['status']=='direction-conflict'
    glass=example('windows')
    assert not any(f.code=='rate-does-not-match' for f in glass.check(physics=True).findings)
    assert any(f.code=='rate-does-not-match' for f in glass.check(physics=True,check_policy='analysis').findings)
    assert solve_physics(example('storage')).updates[0]['value']==pytest.approx(1000*4200/3600)
    for component,expected in zip(solve_physics(example('dorm-wall')).components,[22/(.2+.3+1/30),22/(.2+2.3+1/30)]):
        assert abs(component['branch_rates'][0]['watts'])==pytest.approx(expected*2)
    q=2300/sum([.04,.000652,.05,.001455,.001])
    assert solve_physics(example('composite-wall')).components[0]['branch_rates'][0]['watts']==pytest.approx(q*2)
    wire=solve_physics(example('wire')).components[0]
    assert wire['temperatures']['n0']==pytest.approx(20+7.373*(.03183+1.0373+3.0315))
    assert wire['branch_rates'][0]['watts']==pytest.approx(22.119)
    q=80/((1/2-1/2.25)/(4*math.pi*.06)+1/(6*4*math.pi*2.25**2))
    assert solve_physics(example('sphere')).components[0]['branch_rates'][0]['watts']==pytest.approx(q)
