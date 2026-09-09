import copy
import json

import pytest

from thermodraw import Diagram, DiagramError, assess_physics
from thermodraw._session import convert_value
from test_analysis import network, volume


def test_override_comparison_and_complete_application():
    original = network()
    original['nodes'][1]['value'] = 360
    scenario = copy.deepcopy(original)
    scenario['nodes'][0]['value'] = 450
    before = copy.deepcopy(original)
    result = assess_physics(original, scenario)
    assert original == before
    assert scenario['nodes'][1]['value'] == 360
    assert result['comparisons'][0]['value'] == pytest.approx(390)
    assert result['comparisons'][0]['difference'] == pytest.approx(30)
    assert result['applied']['nodes'][0]['value'] == 450
    assert result['applied']['nodes'][1]['value'] == pytest.approx(390)
    assert any(c['field'] == 'value' and c['before'] == 400 for c in result['changes'])
    Diagram.from_dict(result['applied']).validate()


def test_all_known_check_uses_stated_tolerance():
    data = network()
    data['analysis']['network']['unknowns'] = []
    data['nodes'][1]['value'] = 360.01
    report = assess_physics(data)
    assert report['status'] == 'solved'
    assert not report['applied']
    assert report['result']['components'][0]['tolerances_w']
    data['nodes'][1]['value'] = 350
    assert assess_physics(data)['status'] == 'not-solved'


def test_partial_application_carries_only_successful_system_inputs():
    data = network()
    data['nodes'] += [{'id':'x'}, {'id':'y'}]
    data['branches'] += [{'from':'x','to':'y','value':1}]
    data['analysis']['network']['unknowns'] += ['x','y']
    scenario = copy.deepcopy(data)
    scenario['nodes'][0]['value'] = 450
    scenario['branches'][2]['value'] = 5
    result = assess_physics(data, scenario)
    assert result['status'] == 'partial'
    assert result['applied']['branches'][2]['value'] == 1
    assert result['applied']['nodes'][0]['value'] == 450
    assert result['applied']['nodes'][1]['value'] == pytest.approx(390)
    selected = assess_physics(data, scenario, ['network:hot'])
    assert selected['status'] == 'solved'
    assert len(selected['result']['components']) == 1
    assert not assess_physics(data, scenario, [])['applied']
    with pytest.raises(DiagramError, match='whole system'):
        assess_physics(data, scenario, ['mid'])


def test_volume_override_area_and_storage_proposal():
    data = volume('flux')
    scenario = copy.deepcopy(data)
    scenario['control_surfaces'][0]['area'] = 4
    result = assess_physics(data, scenario)
    assert result['comparisons'][0]['value'] == pytest.approx(25)
    assert result['applied']['control_surfaces'][0]['area'] == 4
    assert data['control_surfaces'][0]['area'] == 2


def test_invalid_topology_and_references_are_explicit():
    data = network()
    scenario = copy.deepcopy(data)
    scenario['branches'][0]['to'] = 'cold'
    assert assess_physics(data, scenario)['status'] == 'invalid'
    data['branches'][0]['to'] = 'gone'
    report = assess_physics(data)
    assert report['status'] == 'invalid' and report['issues']
    assert report['applied'] is None


@pytest.mark.parametrize('value,source,target,q,expected', [
    (2,'kW','W','P',2000), (1000,'mW','W','rate',1),
    (20000,'cm²','m²','area',2), (2,'W/cm²','W/m²','flux',20000),
    (0,'°C','K','T',273.15), (273.15,'K','°C','T',0),
])
def test_per_value_unit_normalization(value,source,target,q,expected):
    assert convert_value(value,source,target,q) == pytest.approx(expected)


def test_bad_conversion_and_shared_unit_application_refused():
    with pytest.raises(DiagramError):
        convert_value('symbolic','kW','W','P')
    with pytest.raises(DiagramError):
        convert_value(1,'kg','W','P')
    data=network();scenario=copy.deepcopy(data);scenario['units']['R']='K/kW'
    assert assess_physics(data,scenario)['status']=='invalid'
    assert convert_value(10,'°C','K','T','rise') == 10


def test_cli_scenario_does_not_write_inputs(tmp_path,capsys):
    from thermodraw.__main__ import main
    data=network();scenario=copy.deepcopy(data);scenario['nodes'][0]['value']=450
    original=tmp_path/'original.json';draft=tmp_path/'scenario.json'
    original.write_text(json.dumps(data));draft.write_text(json.dumps(scenario))
    assert main(['solve-physics',str(original),'--scenario',str(draft),'--json'])==0
    result=json.loads(capsys.readouterr().out)
    assert result['comparisons'][0]['value']==pytest.approx(390)
    assert json.loads(original.read_text())==data
    assert json.loads(draft.read_text())==scenario
