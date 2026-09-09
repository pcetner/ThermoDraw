"""Rectangular sketches and supplied energy budgets, independent of networks."""
import copy
import pytest

from thermodraw import Diagram, DiagramBuilder, DiagramError
from thermodraw._editor import scene
from thermodraw._physical import budgets, surface_geometry


def oven():
    return (DiagramBuilder()
            .region("oven", at=(100, 100), size=(300, 160), label="Oven")
            .control_volume("cv", at=(90, 90), size=(320, 180), regions=["oven"], generation=0, steady=True)
            .control_surface("in", "cv", edge="left")
            .control_surface("out", "cv", edge="right")
            .transfer("power", surface="in", kind="work", direction="in", rate=1834.53, unit="kW")
            .transfer("steel", surface="out", kind="mass", rate=1578.4, unit="kW")
            .transfer("conv", surface="out", rate=151.2, unit="kW")
            .transfer("rad", surface="out", rate=94.73, unit="kW")
            .transfer("cond", surface="out", rate=10.2, unit="kW").build())


def test_physical_only_roundtrip_and_all_outputs():
    d = oven()
    assert Diagram.from_json(d.to_json()).to_dict() == d.to_dict()
    assert budgets(d)[0]["status"] == "balanced"
    assert not [f for f in d.check(physics=True).findings if f.code.startswith("control-volume")]
    assert "<rect" in d.svg("light")
    assert "var(--" not in d.svg("light")
    assert "Oven" in d.page()
    assert d.describe().to_dict()["physical"]["regions"][0]["id"] == "oven"
    sc = scene(d.to_dict(), physics=True)
    assert "error" not in sc
    assert {h["role"] for h in sc["hits"]} == {"region", "volume", "surface", "transfer"}
    assert sc["preview"] and sc["budgets"][0]["status"] == "balanced"


def test_balance_failure_and_unchecked_are_distinct():
    d = oven()
    d.transfers[0].rate = 100
    f = [f for f in d.check(physics=True).findings if f.code == "control-volume-does-not-balance"]
    assert len(f) == 1 and "residual" in f[0].message
    d.control_volumes[0].generation = None
    b = budgets(d)[0]
    assert b["status"] == "unchecked" and b["residual"] is None
    assert "generation" in b["missing"]
    d.control_volumes[0].generation = "unknown"
    assert budgets(d)[0]["status"] == "unchecked"


def test_frost_flux_area_and_storage():
    d = (DiagramBuilder().region("frost").region("air", at=(200, 0))
         .control_volume("cv", generation=0, storage=40)
         .control_surface("face", "cv", area=10000, area_unit="cm²")
         .transfer("conv", surface="face", direction="in", flux=.004, flux_unit="W/cm²").build())
    assert budgets(d)[0]["status"] == "balanced"
    assert budgets(d)[0]["incoming"] == pytest.approx(40)
    d.control_surfaces[0].area = None
    assert budgets(d)[0]["status"] == "unchecked"
    d.control_surfaces[0].area = 10000
    d.transfers[0].direction = "out"
    d.control_volumes[0].storage = -40
    assert budgets(d)[0]["status"] == "balanced"


def test_zero_tolerance_and_units():
    d = oven()
    for t in d.transfers:
        t.rate = 0
    assert budgets(d)[0]["status"] == "balanced"
    d.transfers[0].rate = .5
    d.transfers[0].unit = "mW"
    assert budgets(d)[0]["status"] == "balanced"
    d.transfers[0].rate = 2
    assert budgets(d)[0]["status"] == "unbalanced"
    d.control_volumes[0].incomplete = True
    assert budgets(d)[0]["status"] == "unchecked"


@pytest.mark.parametrize("edge,normal", [("left", (-1, 0)), ("right", (1, 0)), ("top", (0, -1)), ("bottom", (0, 1))])
def test_surfaces_stay_on_edges_when_volume_resizes(edge, normal):
    d = oven()
    s, v = d.control_surfaces[0], d.control_volumes[0]
    s.edge = edge
    before, n = surface_geometry(s, {v.id: v})
    assert n == normal
    v.at = [190, 290]
    v.size = [640, 360]
    after, _ = surface_geometry(s, {v.id: v})
    assert after != before
    if edge in ("left", "right"):
        assert after[0][0] == after[1][0] == v.at[0] + (v.size[0] if edge == "right" else 0)
    else:
        assert after[0][1] == after[1][1] == v.at[1] + (v.size[1] if edge == "bottom" else 0)


@pytest.mark.parametrize("collection,field,value", [
    ("regions", "size", [-1, 20]), ("regions", "at", [float("inf"), 0]),
    ("control_surfaces", "edge", "diagonal"), ("control_surfaces", "volume", "absent"),
    ("control_surfaces", "start", .9), ("control_surfaces", "area", -1),
    ("transfers", "surface", "absent"), ("transfers", "rate", -1),
    ("transfers", "unit", "horsepower"), ("transfers", "direction", "sideways"),
    ("transfers", "length", float("nan")), ("control_volumes", "steady", "yes"),
    ("regions", "links", ["node:absent"]),
])
def test_invalid_physical_data_is_refused(collection, field, value):
    data = oven().to_dict()
    data[collection][0][field] = value
    with pytest.raises(DiagramError):
        Diagram.from_dict(data)


def test_conflicting_sources_and_duplicate_ids_are_refused():
    d = oven().to_dict()
    d["transfers"][0]["flux"] = 4
    with pytest.raises(DiagramError, match="rate or flux"):
        Diagram.from_dict(d)
    d = oven().to_dict()
    d["regions"].append(copy.deepcopy(d["regions"][0]))
    with pytest.raises(DiagramError, match="unique"):
        Diagram.from_dict(d)


def test_manual_labels_and_links_are_additive_not_balance_terms():
    b = (DiagramBuilder(T="K", R="K/W", P="W").node("a", "A", 100, at=(500, 100), label_offset=(12, 20))
         .node("b", "B", 20, at=(740, 100))
         .branch("a", "b", value=4, id="wall", label_offset=(0, 40))
         .source("a", value=20, id="power")
         .region("wall_region", links=["node:a", "branch:wall", "source:power"])
         .control_volume("cv", generation=0, steady=True))
    d = b.build()
    sc = scene(d.to_dict())
    h = next(h for h in sc["hits"] if h["role"] == "node" and h["index"] == 0 and h["element"] == "label")
    assert h["bounds"][:2] == [512, 120]
    assert budgets(d)[0]["status"] == "balanced"
    assert not budgets(d)[0]["terms"]
    assert Diagram.from_json(d.to_json()).to_dict() == d.to_dict()


def test_annotation_text_is_escaped_and_detached_transfer_unchecked():
    d = (DiagramBuilder().annotation("text", label="<script>bad()</script>")
         .annotation("arrow", kind="arrow", at=(0, 50), end=(100, 50))
         .transfer("loose", rate=4).build())
    assert "<script>" not in d.svg()
    assert any(f.code == "control-volume-not-checked" for f in d.check(physics=True).findings)


@pytest.mark.parametrize("name", ["oven", "frost", "wall", "hot-plate"])
def test_homework_acceptance_examples(name):
    from pathlib import Path
    p = Path(__file__).parents[1] / "examples" / "homework" / (name + ".json")
    d = Diagram.from_json(p.read_text(encoding="utf-8"))
    assert not d.check(physics=True).findings
    assert Diagram.from_json(d.to_json()).to_dict() == d.to_dict()
