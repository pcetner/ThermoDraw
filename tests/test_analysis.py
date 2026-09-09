"""Physical solutions are independent of layout and never mutate input."""
import copy
import json
from pathlib import Path

import pytest

from thermodraw import Diagram, DiagramError, DiagramBuilder, solve_physics
from thermodraw.__main__ import main


def network():
    return {"units": {"T": "K", "R": "K/W", "P": "W"},
            "nodes": [{"id": "hot", "kind": "fixed", "value": 400},
                      {"id": "mid"}, {"id": "cold", "kind": "fixed", "value": 300}],
            "branches": [{"from": "hot", "to": "mid", "value": 2},
                         {"from": "mid", "to": "cold", "value": 3}],
            "analysis": {"network": {"steady": True, "unknowns": ["mid"]}}}


def run(data):
    d = Diagram.from_dict(data)
    before = d.to_dict()
    result = solve_physics(d)
    assert d.to_dict() == before
    json.dumps(result.to_dict(), allow_nan=False)
    return result


def test_network_rates_reactions_and_apply():
    data = network()
    result = run(data)
    assert result.status == "solved"
    c = result.components[0]
    assert c["temperatures"]["mid"] == pytest.approx(360)
    assert [b["watts"] for b in c["branch_rates"]] == pytest.approx([20, 20])
    assert c["boundary_reactions"] == pytest.approx({"hot": 20, "cold": -20})
    d = Diagram.from_dict(data)
    applied = result.apply(d)
    assert applied.nodes[1].value == pytest.approx(360)
    assert d.nodes[1].value is None
    assert Diagram.from_json(applied.to_json()).analysis == applied.analysis
    d.nodes[0].value = 450
    with pytest.raises(DiagramError, match="stale"):
        result.apply(d)


def test_homework():
    root = Path(__file__).parents[1] / "examples" / "homework"
    hot = json.loads((root / "hot-plate.json").read_text(encoding="utf-8"))
    hot["analysis"] = {"network": {"steady": True, "unknowns": ["plate"]}}
    assert run(hot).updates[0]["value"] == pytest.approx(199.94220612564274)
    oven = json.loads((root / "oven.json").read_text(encoding="utf-8"))
    oven["analysis"] = {"volumes": {"cv": {"entity": "transfer", "id": "electrical", "field": "rate"}}}
    oven["transfers"][0].pop("rate")
    assert run(oven).updates[0]["value"] == pytest.approx(1834.53)


@pytest.mark.parametrize("change,status", [
    (lambda d: d["analysis"]["network"].update(steady=False), "missing-inputs"),
    (lambda d: d["analysis"]["network"].update(unknowns=[]), "missing-inputs"),
    (lambda d: d["branches"][0].update(value="R"), "missing-inputs"),
    (lambda d: d["nodes"][1].update(kind="phase"), "validation"),
])
def test_missing_is_not_unknown(change, status):
    d = network(); change(d)
    if status == "validation":
        with pytest.raises(DiagramError):
            run(d)
    else:
        r = run(d)
        assert r.components[0]["status"] == status
        assert not r.updates


def test_conflict_floating_and_partial_components():
    d = network()
    d["analysis"]["network"]["unknowns"] = []
    d["nodes"][1]["value"] = 350
    assert run(d).components[0]["status"] == "inconsistent"
    d = network()
    d["nodes"] += [{"id": "float1"}, {"id": "float2"}]
    d["branches"] += [{"from": "float1", "to": "float2", "value": 1}]
    d["analysis"]["network"]["unknowns"] += ["float1", "float2"]
    r = run(d)
    assert r.status == "partial"
    assert r.components[1]["status"] == "underdetermined"
    assert [u["id"] for u in r.updates] == ["mid"]


def test_loop_parallel_count_and_link():
    d = network()
    d["branches"][0].update(count=2, arrangement="parallel")
    d["branches"].append({"from": "hot", "to": "cold", "value": 10})
    assert run(d).updates[0]["value"] == pytest.approx(375)
    d["branches"][0] = {"from": "hot", "to": "mid", "kind": "link"}
    r = run(d)
    assert r.updates[0]["value"] == pytest.approx(400)
    assert r.components[0]["branch_rates"][0]["watts"] is None


def volume(field="rate"):
    return {"control_volumes": [{"id": "cv", "generation": 0, "steady": True}],
            "control_surfaces": [{"id": "s", "volume": "cv", "area": 2}],
            "transfers": [{"id": "in", "surface": "s", "direction": "in", "rate": 100},
                          {"id": "out", "surface": "s"}],
            "analysis": {"volumes": {"cv": {"entity": "transfer", "id": "out", "field": field}}}}


def test_cv_rate_flux_storage_generation_and_directions():
    assert run(volume()).updates[0]["value"] == pytest.approx(100)
    assert run(volume("flux")).updates[0]["value"] == pytest.approx(50)
    d = volume(); d["transfers"][1]["direction"] = "in"
    assert run(d).volumes[0]["status"] == "direction-conflict"
    d = volume(); d["transfers"][1]["rate"] = 150
    d["control_volumes"][0].update(steady=False)
    d["analysis"]["volumes"]["cv"] = {"entity": "volume", "id": "cv", "field": "storage"}
    assert run(d).updates[0]["value"] == pytest.approx(-50)
    d["control_volumes"][0].update(steady=True)
    d["analysis"]["volumes"]["cv"]["field"] = "generation"
    assert run(d).updates[0]["value"] == pytest.approx(50)


def test_missing_area_generation_and_zero():
    d = volume("flux"); del d["control_surfaces"][0]["area"]
    assert run(d).volumes[0]["status"] == "missing-inputs"
    d = volume(); del d["control_volumes"][0]["generation"]
    assert run(d).volumes[0]["status"] == "missing-inputs"
    d = volume(); d["transfers"][0]["rate"] = 0
    assert run(d).updates[0]["value"] == 0


def test_large_cv_coefficient_and_units():
    d = volume("flux")
    d["transfers"][0].update(rate=1e20, unit="kW")
    d["control_surfaces"][0].update(area=20000, area_unit="cm²")
    d["transfers"][1]["flux_unit"] = "kW/m²"
    assert run(d).updates[0]["value"] == pytest.approx(5e19)


def test_invalid_references_and_builder():
    d = volume(); d["analysis"]["volumes"]["cv"]["id"] = "gone"
    with pytest.raises(DiagramError, match="analysis"):
        run(d)
    b = DiagramBuilder().analysis()
    assert b.solve_physics().status == "not-configured"


def test_cli(tmp_path, capsys):
    source = tmp_path / "in.json"; out = tmp_path / "out.json"
    source.write_text(json.dumps(network()))
    assert main(["solve-physics", str(source), "--json", "--apply", "-o", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "solved"
    assert Diagram.from_json(out.read_text(encoding="utf-8")).nodes[1].value == pytest.approx(360)
    assert json.loads(source.read_text(encoding="utf-8"))["nodes"][1] == {"id": "mid"}


def test_rail_and_outward_repeated_sources():
    d = network()
    d["rail"] = {"reference": "cold"}
    d["branches"][1]["to"] = "rail"
    d["sources"] = [{"from": "mid", "kind": "flow", "value": 5, "count": 2}]
    d["units"]["q"] = "W"
    assert run(d).updates[0]["value"] == pytest.approx(348)


def test_steady_zero_branches_and_unsupported_flux():
    d = network()
    d["branches"] += [{"from": "hot", "to": "cold", "kind": "cap", "value": 100},
                      {"from": "hot", "to": "cold", "kind": "break"}]
    d["units"]["C"] = "J/K"
    r = run(d)
    assert r.updates[0]["value"] == pytest.approx(360)
    assert len(r.components[0]["assumptions"]) == 3
    d["sources"] = [{"to": "mid", "kind": "flux", "value": 1}]
    d["units"]["q″"] = "W/cm²"
    assert run(d).components[0]["status"] == "unsupported"


def test_rate_assertions_and_below_absolute_zero():
    d = network(); d["branches"][0]["rate"] = 200
    d["units"]["q"] = "W"
    assert run(d).components[0]["status"] == "inconsistent"
    d = network(); d["sources"] = [{"from": "mid", "kind": "flow", "value": 1000}]
    d["units"]["q"] = "W"
    assert run(d).components[0]["status"] == "inconsistent"


def test_all_worked_analysis_examples():
    folder = Path(__file__).parents[1] / "examples" / "analysis"
    for path in folder.glob("*.json"):
        d = Diagram.from_json(path.read_text(encoding="utf-8"))
        result = solve_physics(d)
        assert result.status == "solved", (path.name, result.to_dict())
        assert result.updates
        result.apply(d).validate()
