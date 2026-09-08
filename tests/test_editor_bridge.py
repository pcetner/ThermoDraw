"""The editor's side of the library: `Placement.index` and `_editor`.

The editor maps a click on the page back to a field in the file. That
needs the number `ref` only says in prose, and a hit map that agrees with
the placements the checker grades. Both are pinned here on every diagram
the repository has.
"""
import json
import re
import pathlib

import pytest

from thermodraw import Diagram, DiagramBuilder, layout, symbols
from thermodraw import _editor as E
from thermodraw import model as M

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = sorted(ROOT.glob("examples/*.json")) + sorted(
    ROOT.glob("examples/gallery/*/*.json"))

pytestmark = pytest.mark.skipif(not FILES, reason="examples/ is not installed")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_every_placement_knows_its_index(path):
    d = Diagram.from_dict(load(path))
    lists = {"node": d.nodes, "branch": d.branches, "source": d.sources}
    for p in layout(d):
        if p.role == "rail":
            assert p.index is None
            continue
        assert p.index is not None, p.ref
        element = lists[p.role][p.index]
        if p.role == "node":
            assert p.ends == (element.id,)
        elif p.role == "branch":
            assert p.ends == (element.source, element.target)
        else:
            assert p.ends == (element.node,)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name + "/" + p.name)
def test_the_scene_is_json_and_its_hits_hold_their_anchors(path):
    data = load(path)
    out = E.scene(data, physics=True)
    assert "error" not in out, out.get("error")
    json.dumps(out)
    assert out["parts"].count("<") > 10
    x0, y0, x1, y1 = out["ink"]
    assert x1 > x0 and y1 > y0
    assert out["labels"] > 0
    roles = {h["role"] for h in out["hits"]}
    assert roles <= {"node", "branch", "source"}
    for h in out["hits"]:
        bx0, by0, bx1, by1 = h["bounds"]
        assert bx1 >= bx0 and by1 >= by0
        if h["element"] in ("node", "symbol"):
            assert bx0 <= h["at"][0] <= bx1 and by0 <= h["at"][1] <= by1
        lists = {"node": data["nodes"], "branch": data["branches"],
                 "source": data.get("sources", [])}
        assert 0 <= h["index"] < len(lists[h["role"]])


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.parent.name)
def test_a_symbol_hit_says_how_long_it_is(path):
    """The editor routes a wire around a dragged symbol, and the ink in
    `bounds` is not the measurement that does it: a box symbol's leads
    reach 62 for a half-length of 42."""
    by_key = {s.key: s for s in symbols.SYMBOLS}
    seen = 0
    for h in E.scene(load(path))["hits"]:
        # a hit knows its length exactly when it knows its symbol: the two
        # come from the same placement, and a label's owner is one of them
        assert ("half_len" in h) == ("kind" in h)
        if "kind" not in h:
            continue
        assert h["half_len"] == float(by_key[h["kind"]].half_len)
        seen += h["element"] == "symbol"
    assert seen, "every diagram in the suite draws at least one symbol"


def test_a_pair_between_one_node_pair_is_two_hits():
    """`ref` cannot tell them apart; `index` can."""
    d = (DiagramBuilder(R="K/W", T="K")
         .node("a", "A", 10, at=(100, 100), sub="a")
         .node("b", "B", 5, at=(400, 100), sub="b")
         .branch("a", "b", "conv", "Air", "1", via=[(200, 40), (300, 40)])
         .branch("a", "b", "rad", "Walls", "2", via=[(200, 160), (300, 160)]))
    out = E.scene(d.build().to_dict())
    symbols = [h for h in out["hits"]
               if h["role"] == "branch" and h["element"] == "symbol"]
    assert sorted(h["index"] for h in symbols) == [0, 1]
    assert {h["kind"] for h in symbols} == {"conv", "rad"}
    assert all(len(h["via"]) == 2 for h in symbols)


def test_a_hidden_form_makes_no_hit():
    d = (DiagramBuilder(R="K/W", T="K")
         .node("a", "A", 10, at=(100, 100), sub="a")
         .node("b", "B", 5, at=(500, 100), sub="b")
         .branch("a", "b", "cond", "Bolts", "4", count=8,
                 arrangement="parallel"))
    out = E.scene(d.build().to_dict())
    copies = [h for h in out["hits"] if h["element"] == "symbol"]
    assert len(copies) == 2, "the condensed form shows two"


def test_a_refusal_is_the_librarys_own_words():
    data = {"units": {"T": "K"},
            "nodes": [{"id": "x", "label": "X", "value": "1", "sub": "x"},
                      {"id": "a", "label": "A", "value": "1", "sub": "a"},
                      {"id": "b", "label": "B", "value": "1", "sub": "b"},
                      {"id": "c", "label": "C", "value": "1", "sub": "c"}],
            "branches": [{"from": "x", "to": t, "kind": "cond"}
                         for t in "abc"]}
    out = E.scene(data)
    assert "joins 3 others" in out["error"]
    assert "give every node `at`" in out["error"]
    assert "joins 3 others" in E.solve(data)["error"]


def test_solve_fills_what_was_left_out():
    data = load(ROOT / "examples" / "raptor.json")
    solved = E.solve(data)
    assert all("at" in n for n in solved["nodes"])
    assert E.scene(solved)["ink"] == E.scene(data)["ink"]


def test_the_exports_are_the_diagrams_own():
    data = load(ROOT / "examples" / "raptor.json")
    d = Diagram.from_dict(data)
    assert E.export(data, "svg") == d.svg()
    assert E.export(data, "svg", "dark", "zigzags") == d.svg(
        "dark", notation="zigzags")
    assert E.export(data, "page") == d.page()
    assert json.loads(E.export(data, "json")) == d.to_dict()
    with pytest.raises(ValueError, match="svg, page or json"):
        E.export(data, "pdf")


def test_the_head_carries_the_faces_and_the_variables():
    h = E.head()
    assert len(h["faces"]) == 3
    assert all(f.startswith("@font-face") for f in h["faces"])
    assert ":root{" in h["vars"] and 'data-theme="dark"' in h["vars"]
    assert "var(--sym)" in h["css"]
    from thermodraw import __version__
    assert h["version"] == __version__
    json.dumps(h)


def test_the_palette_is_the_twenty_symbols_in_their_groups():
    from thermodraw import symbols
    p = E.palette()
    assert [e["key"] for e in p] == [s.key for s in symbols.SYMBOLS]
    assert {e["role"] for e in p} == {"node", "branch", "source"}
    by_key = {e["key"]: e for e in p}
    assert by_key["flow-branch"] == {**by_key["flow-branch"],
                                     "role": "branch", "kind": "flow"}
    assert by_key["flow"]["role"] == "source"
    assert by_key["break"]["role"] == "node"
    assert by_key["break-branch"]["role"] == "branch"
    assert all(e["svg"].startswith("<svg") for e in p)
    json.dumps(p)


@pytest.mark.parametrize("typed, first", [
    ("con", "cond"), ("conv", "conv"), ("Radiation", "rad"),
    ("fixed", "fixed"), ("cap", "cap"), ("heat flux", "flux"),
    ("convecshun", "conv"), ("diss", "diss"),
])
def test_quick_add_ranks_what_was_meant_first(typed, first):
    got = E.quick_add(typed)
    assert got and got[0]["key"] == first, got[:3]
    assert E.quick_add("") == []


def test_the_editor_offers_exactly_the_kinds_the_model_has():
    """`docs/editor/editor.js` writes all three kind sets out by hand.

    The palette is generated from the library, so a new kind is droppable the
    day it lands; the inspector's Kind dropdown is this literal, so it was
    the one place a new kind could go missing with every test green. Nothing
    compared the two until `link` and `stream` were added and both were
    droppable and unselectable at once.
    """
    import re

    from thermodraw import model

    src = (ROOT / "docs" / "editor" / "editor.js").read_text(encoding="utf-8")
    block = re.search(r"const KINDS = \{(.*?)\n\};", src, re.S)
    assert block, "editor.js no longer declares KINDS as one literal"
    listed = {role: set(re.findall(r'"([a-z-]+)"', body))
              for role, body in re.findall(r"(\w+): \[(.*?)\],",
                                           block.group(1))}
    assert listed == {"node": model.NODE_KINDS,
                      "branch": model.BRANCH_KINDS,
                      "source": model.SOURCE_KINDS}


@pytest.mark.parametrize("kind", sorted(M.BRANCH_KINDS))
def test_every_branch_kind_can_be_dropped_and_still_draws(kind):
    """`dropPath` writes `{from, to, kind}` and nothing else, so every kind
    has to be drawable with no numbers on it. A `stream` that demanded
    `mdot` and `cp` broke the canvas outright the moment it was dropped,
    which is the one thing an editor gesture may never do."""
    scene = E.scene({
        "nodes": [{"id": "n1", "at": [100, 100]},
                  {"id": "n2", "at": [320, 100]}],
        "branches": [{"from": "n1", "to": "n2", "kind": kind}]})
    assert "error" not in scene, scene.get("error")
    assert scene["parts"]


def test_every_unit_the_editor_can_ask_for_can_also_be_set():
    """The branch card prints `<quantity>, <unit>` and offers a box for the
    number; the units card is the only place the unit itself is typed. A
    quantity in the first and not the second is a dead end -- the card asks
    for a mass flow, validation refuses it for having no unit, and the
    editor has nowhere to give it one. That is what `mdot` and `cp` were.
    """
    js = (pathlib.Path("docs/editor/editor.js")
          .read_text(encoding="utf-8"))
    # the loop over the plain quantities, plus any written out on their own
    loop = re.search(r'for \(const q of \[([^\]]*)\]\) h \+= field\('
                     r'`Unit of', js)
    assert loop, "the units card's quantity loop moved"
    settable = set(re.findall(r'"([^"]+)"', loop.group(1)))
    settable |= set(re.findall(r'text\("unit:([A-Za-z″]+)"', js))
    wanted = set(M.QUANTITY.values()) | {M.MDOT, M.CP}
    assert wanted <= settable, f"no way to set units for {wanted - settable}"


def test_a_new_diagram_starts_with_every_unit_the_model_has():
    """`BLANK` defaults `R`, `C`, `T`, `P`, `q` and `q″` whether the
    diagram uses them or not, so a card never shows "no unit" over a field
    that refuses a number without one. `mdot` and `cp` were the exception,
    seeded only when a stream was made, so the units card offered them as a
    grey suggestion and an opened file got neither."""
    js = (pathlib.Path("docs/editor/editor.js")
          .read_text(encoding="utf-8"))
    blank = re.search(r"const BLANK = \(\) => \(\{\s*units: \{(.*?)\}",
                      js, re.S)
    assert blank, "BLANK's units moved"
    started = set(re.findall(r'(?:"([^"]+)"|(\w+)):', blank.group(1)))
    started = {a or b for a, b in started}
    wanted = set(M.QUANTITY.values()) | {M.MDOT, M.CP}
    assert wanted <= started, f"a new diagram has no unit for {wanted - started}"

