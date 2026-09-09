"""Cross-API contracts found during the release engineering review."""
import copy
import json

import pytest

from thermodraw import Diagram, DiagramBuilder, assess_physics, solve_physics
from test_analysis import network


@pytest.mark.parametrize("value", ["Infinity", "-Infinity", "NaN", "1e999"])
def test_nonfinite_temperature_is_never_certified(value):
    data = network()
    data["analysis"] = {}
    data["nodes"][1]["value"] = value
    report = Diagram.from_dict(data).check(physics=True)
    assert any(f.code == "physics-not-checked" for f in report.findings)


def test_finite_inputs_that_overflow_do_not_balance():
    data = network()
    data["analysis"] = {}
    data["nodes"][1]["value"] = 1e308
    data["branches"][0]["value"] = 1e-308
    report = Diagram.from_dict(data).check(physics=True)
    assert any("numerical range" in f.message for f in report.findings)


@pytest.mark.parametrize("source", [True, False])
def test_negative_heat_input_does_not_disappear_from_balance(source):
    data = {"units": {"T": "K", "P": "W", "q": "W"},
            "nodes": [{"id": "a", "value": 300, "at": [200, 150]},
                      {"id": "b", "value": 300, "kind": "fixed", "at": [500, 150]}]}
    if source:
        data["sources"] = [{"to": "a", "value": -20}]
    else:
        data["branches"] = [{"from": "b", "to": "a", "kind": "flow", "value": -20}]
    report = Diagram.from_dict(data).check(physics=True)
    assert any(f.code == "node-does-not-balance" for f in report.findings)


@pytest.mark.parametrize("unknown", [False, True])
@pytest.mark.parametrize("arrangement", [None, "parallel", "series"])
def test_rate_magnitude_survives_endpoint_reversal(unknown, arrangement):
    data = network()
    data["units"]["q"] = "W"
    data["nodes"][1]["value"] = 360
    data["analysis"]["network"].update(unknowns=[], resistance_unknowns=[0] if unknown else [])
    branch = data["branches"][0]
    branch.update({"from": "mid", "to": "hot", "rate": 20})
    if arrangement:
        branch.update(count=2, arrangement=arrangement,
                      value=4 if arrangement == "parallel" else 1)
    original = Diagram.from_dict(data)
    result = solve_physics(original)
    assert result.status == "solved"
    assert result.components[0]["branch_rates"][0]["watts"] == pytest.approx(-20)
    applied = result.apply(original)
    assert not [f for f in applied.check(physics=True).findings
                if f.code in ("rate-does-not-match", "node-does-not-balance")]


def test_branch_ids_cannot_replace_another_unknown():
    data = network()
    data["units"]["q"] = "W"
    data["nodes"][1]["value"] = 360
    data["branches"][0]["rate"] = 20
    data["branches"][1]["id"] = "branch:0"
    data["analysis"]["network"].update(unknowns=[], resistance_unknowns=[0, 1])
    result = solve_physics(Diagram.from_dict(data))
    assert result.status == "solved"
    assert [(u["index"], u["value"]) for u in result.updates] == [(0, 2), (1, 3)]


def test_applied_scenario_retains_its_tolerance():
    original = network()
    original["nodes"][1]["value"] = 359
    original["analysis"]["network"]["unknowns"] = []
    scenario = copy.deepcopy(original)
    scenario["nodes"][1]["value"] = 358
    scenario["analysis"]["tolerance"] = {"absolute_w": 10, "relative": 0}
    result = assess_physics(original, scenario)
    assert result["status"] == "solved"
    assert result["applied"]["analysis"]["tolerance"] == scenario["analysis"]["tolerance"]
    assert assess_physics(json.loads(json.dumps(result["applied"])))["status"] == "solved"
    assert original["nodes"][1]["value"] == 359


def test_shared_tolerance_cannot_apply_to_only_one_system():
    original = network()
    original["control_volumes"] = [{"id": "cv", "generation": 0, "steady": True}]
    scenario = copy.deepcopy(original)
    scenario["analysis"]["tolerance"] = {"absolute_w": 10}
    result = assess_physics(original, scenario, ["network:hot"])
    assert result["applied"] is None
    assert any(i["status"] == "application-limited" for i in result["issues"])
    assert result["comparisons"]  # Results can still be inspected/copied.


def test_supplied_volume_uses_analysis_tolerance_but_legacy_check_does_not():
    data = {"control_volumes": [{"id": "cv", "generation": 100, "storage": 99.5}],
            "analysis": {"tolerance": {"absolute_w": 0, "relative": 0}}}
    diagram = Diagram.from_dict(data)
    result = solve_physics(diagram)
    assert result.status == "not-solved"
    assert result.volumes[0]["totals"]["tolerance"] == 0
    assert not [f for f in diagram.check(physics=True).findings
                if f.code == "control-volume-does-not-balance"]


def test_node_order_and_equivalent_units_preserve_solution():
    data = network()
    data["nodes"].reverse()
    data["units"]["R"] = "K/kW"
    for branch in data["branches"]:
        branch["value"] *= 1000
    result = solve_physics(Diagram.from_dict(data))
    assert result.status == "solved"
    assert result.updates[0]["value"] == pytest.approx(360)


def test_builder_can_express_stream_inputs():
    diagram = (DiagramBuilder(T="K", mdot="kg/s", cp="J/kgK", q="W")
               .node("inlet", value=300).node("outlet", value=310)
               .branch("inlet", "outlet", kind="stream", mdot=2, cp=1000).build())
    assert diagram.carried(diagram.branches[0], 300, 310) == pytest.approx(20000)


def test_link_to_reference_rail_can_be_checked():
    data = network()
    for i, node in enumerate(data["nodes"]):
        node["at"] = [200 + 300 * i, 150]
    data["nodes"][1]["value"] = 300
    data["rail"] = {"reference": "cold"}
    data["branches"][1] = {"from": "mid", "to": "rail", "kind": "link"}
    report = Diagram.from_dict(data).check(physics=True)
    assert not [f for f in report.findings if f.code == "link-temperatures-disagree"]


def test_analysis_report_shapes_and_stale_application():
    data = network()
    diagram = Diagram.from_dict(data)
    result = solve_physics(diagram)
    assert set(result.to_dict()) == {"status", "input_hash", "components", "volumes", "updates", "coverage"}
    assert set(result.updates[0]) == {"entity", "id", "field", "value", "unit"}
    assessment = assess_physics(diagram)
    assert set(assessment) == {"status", "input_hash", "scenario_hash", "systems", "issues",
                               "result", "effective_inputs", "applied", "changes", "comparisons"}
    diagram.analysis["tolerance"] = {"relative": .02}
    with pytest.raises(ValueError, match="stale"):
        result.apply(diagram)
