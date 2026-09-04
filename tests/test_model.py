"""The data layer: round trips, validation, and what layout makes of it."""
import json
import pathlib

import pytest

from thermodraw import (Diagram, DiagramBuilder, DiagramError, layout, render,
                        symbols)

HERO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "hero.json"

pytestmark = pytest.mark.skipif(
    not HERO.exists(), reason="examples/hero.json is not present")


def hero():
    return Diagram.from_json(HERO.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- round trip
def test_json_round_trip_is_stable():
    once = hero()
    twice = Diagram.from_dict(once.to_dict())
    assert once.to_dict() == twice.to_dict()


def test_round_trip_renders_the_same_bytes():
    once = render(layout(hero()))
    twice = render(layout(Diagram.from_dict(hero().to_dict())))
    assert once == twice


def test_builder_and_dict_agree():
    """Anything the builder can say must be expressible as data."""
    built = (DiagramBuilder(R="K/W", T="°C")
             .node("j", "Junction", "112", at=(0, 0), sub="j")
             .node("c", "Case", "78", at=(224, 0), sub="c")
             .branch("j", "c", "cond", "Die attach", "0.35"))
    assert DiagramBuilder.from_dict(built.to_dict()).svg() == built.svg()


# ---------------------------------------------------------------- validation
def test_missing_coordinates_are_solved_not_refused():
    """This used to refuse with "the network layer, which is not built
    yet", and the test pinned that the message named the feature rather
    than a version number. The ladder solver is that feature: a node with
    no `at` is placed, and the file is accepted."""
    d = Diagram.from_dict({"nodes": [{"id": "a"}]})
    assert d.nodes[0].at is None, "the input is not touched"
    assert render(layout(d))


def test_dangling_branch_names_the_node():
    with pytest.raises(DiagramError, match="nowhere"):
        Diagram.from_dict({
            "nodes": [{"id": "a", "at": [0, 0]}],
            "branches": [{"from": "a", "to": "nowhere", "kind": "cond"}]})


def test_duplicate_ids_are_refused():
    with pytest.raises(DiagramError, match="duplicate"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0]},
                                     {"id": "a", "at": [1, 1]}]})


def test_unknown_kind_lists_the_known_ones():
    with pytest.raises(DiagramError, match="contact"):
        Diagram.from_dict({
            "nodes": [{"id": "a", "at": [0, 0]}, {"id": "b", "at": [9, 0]}],
            "branches": [{"from": "a", "to": "b", "kind": "magic"}]})


def test_rail_branch_without_a_rail_is_refused():
    with pytest.raises(DiagramError, match="no rail"):
        Diagram.from_dict({
            "nodes": [{"id": "a", "at": [0, 0]}],
            "branches": [{"from": "a", "to": "rail", "kind": "cap"}]})


def test_every_kind_in_the_schema_is_a_real_symbol():
    """The vocabulary and the schema have to be the same list."""
    from thermodraw import model as M
    from thermodraw._layout import BRANCH_SYM
    keys = {s.key for s in symbols.SYMBOLS}
    # through the same mapping `layout` uses, not straight to the key. Node
    # kind "break" and branch kind "break" are the same word for the same
    # thing in two positions, and BY_KEY is one namespace: without the
    # indirection a branch kind could satisfy this by colliding with a node's
    # symbol, which is exactly the bug it is here to catch.
    assert {BRANCH_SYM.get(k, k) for k in M.BRANCH_KINDS} <= keys
    assert M.SOURCE_KINDS <= keys
    assert M.NODE_KINDS <= keys
    assert set(BRANCH_SYM) <= M.BRANCH_KINDS, "a mapping for no such kind"


def test_the_groups_are_the_symbol_order():
    """`GROUPS` is what the vocabulary sheet lays out and what a reader
    learns the vocabulary from, so it cannot drift from the list itself."""
    flat = [k for _, keys in symbols.GROUPS for k in keys]
    assert flat == [s.key for s in symbols.SYMBOLS]
    assert len(set(flat)) == len(flat), "a symbol in two groups"


# -------------------------------------------------------------------- units
def test_units_are_appended_from_the_table():
    d = hero()
    assert d.value_text("cond", "0.35") == "0.35 K/W"
    assert d.value_text("cap", "0.9") == "0.9 J/K"
    assert d.value_text("free", "112") == "112 °C"
    assert d.value_text("cond", None) is None


def test_numbers_do_not_gain_a_precision_they_lack():
    d = Diagram(units={"R": "K/W"})
    assert d.value_text("cond", 0.35) == "0.35 K/W"
    assert d.value_text("cond", 45.0) == "45 K/W"
    assert d.value_text("cond", "1.80") == "1.80 K/W"


# -------------------------------------------------------------------- layout
def test_layout_is_pure():
    d = hero()
    assert [str(p) for p in layout(d)] == [str(p) for p in layout(d)]


def test_a_shared_trunk_is_drawn_once():
    """Two branches routed along the same wire should not stroke it twice."""
    svg = render(layout(hero()))
    runs = svg.count("<polyline")
    assert runs == len(set(
        p for p in svg.split("<polyline")[1:]))


def test_canvas_sizes_itself_to_its_contents():
    """Everything in page coordinates must land inside the box render chose.

    Symbol interiors are drawn in their own frame — a box edge is at x=-42
    whatever the page coordinates are — so only the placements can be checked
    against the viewBox, not every number in the file.
    """
    import re

    from thermodraw._render import extent

    placements = layout(hero())
    svg = render(placements)
    w, h = (float(v) for v in
            re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    x0, y0, x1, y1 = extent(placements, [])
    assert w >= x1 - x0 and h >= y1 - y0

    dx, dy = (float(v) for v in
              re.search(r'translate\(([-\d.]+),([-\d.]+)\)', svg).groups())
    for p in placements:
        for x, y in (p.points or [p.at]):
            assert -1 <= x + dx <= w + 1, f"{x} outside 0..{w}"
            assert -1 <= y + dy <= h + 1, f"{y} outside 0..{h}"


def test_explicit_size_still_works():
    svg = render(layout(hero()), size=(1060, 470))
    assert 'viewBox="0 0 1060 470"' in svg


def test_a_value_without_a_unit_is_refused():
    """Units are fixed per diagram; a bare number is the failure to catch."""
    with pytest.raises(DiagramError, match="render bare"):
        Diagram.from_dict({
            "units": {"T": "°C"},
            "nodes": [{"id": "a", "at": [0, 0]}, {"id": "b", "at": [220, 0]}],
            "branches": [{"from": "a", "to": "b", "kind": "cond",
                          "value": "0.35"}]})


def test_unknown_quantity_in_units_is_refused():
    with pytest.raises(DiagramError, match="not a quantity"):
        Diagram.from_dict({"units": {"Z": "m"}, "nodes": []})


# ---------------------------------------------------------- the 1.0 fields
def test_a_turned_wall_survives_the_round_trip():
    d = Diagram.from_dict({
        "units": {"R": "K/W", "T": "K"},
        "nodes": [{"id": "a", "at": [0, 0], "value": "4"},
                  {"id": "m", "kind": "fixed", "at": [0, -200],
                   "value": "300", "wall": "up"}],
        "branches": [{"from": "a", "to": "m", "kind": "cond", "value": "1"}]})
    out = d.to_dict()
    assert out["nodes"][1]["wall"] == "up"
    assert "wall" not in out["nodes"][0], "the default is not written"
    assert Diagram.from_dict(out).to_dict() == out


def test_the_temperature_scale_survives_the_round_trip():
    """Written as `"T": {"unit": ..., "scale": ...}`; read into `units["T"]`
    as the text it always was, plus `scale`; written back nested."""
    d = Diagram.from_dict({
        "units": {"R": "K/W", "T": {"unit": "K", "scale": "rise"}},
        "nodes": [{"id": "a", "at": [0, 0], "value": "20"}]})
    assert d.units["T"] == "K" and d.scale == "rise"
    out = d.to_dict()
    assert out["units"]["T"] == {"unit": "K", "scale": "rise"}
    assert Diagram.from_dict(out).to_dict() == out


def test_a_plain_temperature_unit_declares_nothing():
    d = Diagram.from_dict({"units": {"T": "K"},
                           "nodes": [{"id": "a", "at": [0, 0], "value": "20"}]})
    assert d.scale is None
    assert d.to_dict()["units"] == {"T": "K"}


# ------------------------------------------------ the outputs, on the data
class TestTheDiagramHasTheBuildersOutputs:
    """A diagram read from JSON needed `layout`, `render` and `theme` by hand
    to reach a file the builder reached in one call. The five outputs are
    the `Diagram`'s, and the builder delegates, so there is one of each."""

    @staticmethod
    def both():
        b = (DiagramBuilder(R="K/W", T="°C", P="W")
             .node("j", "Junction", "112", at=(200, 150), sub="j")
             .node("c", "Case", "78", at=(424, 150), sub="c")
             .branch("j", "c", "cond", "Die attach", "0.35")
             .source("j", "diss", "Switching loss", "45", sub="d"))
        return b, Diagram.from_dict(b.to_dict())

    def test_svg_is_the_same_from_either(self):
        b, d = self.both()
        assert d.svg() == b.svg()
        assert d.svg("light") == b.svg("light")
        assert d.svg().startswith("<svg") and "var(--" in d.svg()
        assert "var(--" not in d.svg("dark")

    def test_check_describe_and_page_agree(self):
        b, d = self.both()
        assert d.check().to_dict() == b.check().to_dict()
        assert d.describe().text() == b.describe().text()
        assert d.page() == b.page()
        assert d.check(physics=True).ok == b.check(physics=True).ok

    def test_a_notebook_shows_the_drawing(self):
        b, d = self.both()
        assert d._repr_svg_() == d.svg()
        assert b._repr_svg_() == b.svg()

    def test_the_model_imports_alone(self):
        """The methods import lazily: `model` is what the pipeline imports,
        and a top-level import back would be a cycle. Checked in a fresh
        interpreter, where a cycle actually fails."""
        import subprocess
        import sys
        got = subprocess.run(
            [sys.executable, "-c",
             "import thermodraw.model as m; print(m.Diagram.__name__)"],
            capture_output=True, text=True,
            cwd=str(pathlib.Path(__file__).resolve().parents[1]),
            env={**__import__("os").environ, "PYTHONPATH": "src"})
        assert got.returncode == 0, got.stderr
        assert got.stdout.strip() == "Diagram"
