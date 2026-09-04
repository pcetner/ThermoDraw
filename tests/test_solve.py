"""The ladder solver: `at` for the nodes you left out.

What it places is a chain, from the hot end, each run as wide as its labels
need; what it refuses it refuses by name. The hero with every coordinate
removed is the first test, because it is the diagram the schema quotes, and
the gallery with every coordinate removed is the last, because it is the
evidence: six of its ten are chains, and the table below says what the
solver makes of each.
"""
import copy
import json
import pathlib

import pytest

from thermodraw import (Diagram, DiagramBuilder, DiagramError, check,
                        describe, layout, render, solve)
from thermodraw.__main__ import main

ROOT = pathlib.Path(__file__).resolve().parents[1]
HERO = ROOT / "examples" / "hero.json"
GALLERY = ROOT / "examples" / "gallery"


def bare(data):
    """A diagram with every coordinate the author placed removed: node
    `at`, branch `at` and `via`, source `at`, and the `side` a routed pair
    was given. Everything else — `angle`, `wall`, values — is theirs."""
    data = json.loads(json.dumps(data))
    for n in data["nodes"]:
        n.pop("at", None)
    for b in data.get("branches", []):
        b.pop("at", None)
        b.pop("via", None)
        if b.get("side") in ("up", "down"):
            b.pop("side")
    for s in data.get("sources", []):
        s.pop("at", None)
    return data


def codes(report):
    return [f.code for f in report.findings]


def hero():
    return json.loads(HERO.read_text(encoding="utf-8"))


@pytest.mark.skipif(not HERO.exists(), reason="examples/hero.json absent")
class TestTheHeroWithoutItsNumbers:
    def test_it_checks_clean(self):
        report = check(Diagram.from_dict(bare(hero())))
        assert not report.findings, report.text()

    def test_it_is_the_same_network(self):
        placed, solved = describe(Diagram.from_dict(hero())), \
            describe(Diagram.from_dict(bare(hero())))
        assert solved.edges == placed.edges
        assert solved.sources == placed.sources
        assert solved.pieces == placed.pieces

    def test_the_chain_runs_hot_to_cold_on_one_line(self):
        d = describe(Diagram.from_dict(bare(hero())))
        assert [i for i, _, _ in d.nodes] == ["j", "c", "s", "amb"]
        ys = {a[1] for _, _, a in d.nodes}
        assert ys == {150}
        xs = [a[0] for _, _, a in d.nodes]
        assert xs == sorted(xs) and xs[0] == 200
        assert all(x % 10 == 0 for x in xs), "on the grid"

    def test_every_node_is_marked_solved(self):
        d = describe(Diagram.from_dict(bare(hero())))
        assert d.solved == ["j", "c", "s", "amb"]
        assert all(n["solved"] for n in d.to_dict()["nodes"])
        assert "  j              free     at (200, 150) solved" in d.text()

    def test_the_pair_went_above_and_below(self):
        out = solve(Diagram.from_dict(bare(hero())))
        conv = [b for b in out.branches if b.kind == "conv"][0]
        rad = [b for b in out.branches if b.kind == "rad"][0]
        assert conv.via and rad.via
        assert conv.via[1][1] < 150 < rad.via[1][1]
        assert (conv.side, rad.side) == ("up", "down")
        # leaves and arrives sideways of each node, not straight out of it
        s, amb = out.node("s").at, out.node("amb").at
        assert conv.via[0][0] == s[0] + 48 and conv.via[-1][0] == amb[0] - 48

    def test_the_input_is_never_touched(self):
        d = Diagram.from_dict(bare(hero()))
        before = copy.deepcopy(d.to_dict())
        check(d)
        describe(d)
        render(layout(d))
        assert d.to_dict() == before
        assert all(n.at is None for n in d.nodes)

    def test_a_placed_diagram_goes_through_untouched(self):
        d = Diagram.from_dict(hero())
        assert solve(d) is d


class TestTheChainRule:
    @staticmethod
    def build(nodes, branches, sources=()):
        return Diagram.from_dict({
            "units": {"R": "K/W", "T": "K", "P": "W"},
            "nodes": nodes, "branches": branches, "sources": list(sources)})

    def test_a_node_joining_three_is_refused_by_name(self):
        with pytest.raises(DiagramError, match="node 'hub' joins 3 others"):
            layout(self.build(
                [{"id": "hub"}, {"id": "a"}, {"id": "b"}, {"id": "c"}],
                [{"from": "hub", "to": x, "kind": "cond"} for x in "abc"]))

    def test_the_refusal_says_what_to_do_and_it_works(self):
        """It said "give node 'hub' `at`" once, and run 4's PV reader gave
        it `at`, then `via` too, and got the same message back both times:
        one unplaced node anywhere sends the whole file here. What clears
        it is every node placed, so that is what it says."""
        nodes = [{"id": "hub"}, {"id": "a"}, {"id": "b"}, {"id": "c"}]
        branches = [{"from": "hub", "to": x, "kind": "cond"} for x in "abc"]
        with pytest.raises(DiagramError) as caught:
            layout(self.build(nodes, branches))
        assert "give every node `at` yourself" in str(caught.value)
        assert "`via`" in str(caught.value)
        nodes[0]["at"] = [400, 150]                 # the named node alone
        with pytest.raises(DiagramError):
            layout(self.build(nodes, branches))
        for n, at in zip(nodes[1:], ([200, 150], [400, 40], [600, 150])):
            n["at"] = at                            # every node, as it says
        assert layout(self.build(nodes, branches))

    def test_two_pieces_are_refused(self):
        with pytest.raises(DiagramError, match="no path of branches"):
            layout(self.build(
                [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}],
                [{"from": "a", "to": "b", "kind": "cond"},
                 {"from": "c", "to": "d", "kind": "cond"}]))

    def test_a_loop_is_refused(self):
        with pytest.raises(DiagramError, match="form a loop"):
            layout(self.build(
                [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                [{"from": "a", "to": "b", "kind": "cond"},
                 {"from": "b", "to": "c", "kind": "cond"},
                 {"from": "c", "to": "a", "kind": "cond"}]))

    def test_a_placed_node_is_refused_the_same_way(self):
        """A hub with `at` and three unplaced neighbours is still not a
        chain; the solver does not guess where the other two go."""
        with pytest.raises(DiagramError, match="joins 3 others"):
            layout(self.build(
                [{"id": "hub", "at": [400, 150]}, {"id": "a"}, {"id": "b"},
                 {"id": "c"}],
                [{"from": "hub", "to": x, "kind": "cond"} for x in "abc"]))

    def test_the_rail_and_sources_do_not_count_as_joins(self):
        """Two capacitances to the rail and a source, on a three-node
        chain: still a chain, and clean."""
        d = DiagramBuilder(R="K/W", C="J/K", T="K", P="W")
        d.node("a", "A", "300", sub="a").node("b", "B", "200", sub="b")
        d.node("c", "C", "100", kind="fixed", sub="c")
        d.branch("a", "b", "cond", "One", "1").branch("b", "c", "cond", "Two", "1")
        d.rail("c", y=372)
        d.branch("a", "rail", "cap", "Mass", "5", sub="a")
        d.branch("b", "rail", "cap", "Mass", "5", sub="b")
        d.source("a", "diss", "Load", "10", sub="d")
        assert check(d).ok, check(d).text()

    def test_a_source_above_and_a_source_below_turn_the_label_too(self):
        """13: the shield's `radin` turned to arrive from above and its
        outbound `flow` turned to leave below, and its label was reported
        adrift between the two leads."""
        d = DiagramBuilder(R="K/W", T="K", P="W", q="W")
        d.node("v", "Vessel", "300", kind="fixed", sub="v")
        d.node("sh", "Shield", "40", sub="sh")
        d.node("he", "Bath", "4.2", kind="phase", sub="he")
        d.branch("v", "sh", "cond", "Straps", "50")
        d.branch("sh", "he", "cond", "Leads", "179")
        d.source("sh", "radin", "Through MLI", "30", sub="mli")
        d.source("sh", "flow", "Cold head", "35", sub="cc", outward=True)
        assert check(d).ok, check(d).text()
        assert solve(d.build()).node("sh").angle == 45

    def test_a_source_above_and_a_capacitance_below_turns_the_label(self):
        """The label has the source's lead above it and the capacitance's
        wire below, and the run on either side; only a diagonal clears all
        three. The solver put the source there, so the solver turns the
        frame — to 45, and only where the author left it at 0."""
        d = DiagramBuilder(R="K/W", C="J/K", T="K", P="W")
        d.node("a", "A", "300", sub="a").node("b", "B", "200", sub="b")
        d.node("c", "C", "100", kind="fixed", sub="c")
        d.branch("a", "b", "cond", "One", "1").branch("b", "c", "cond", "Two", "1")
        d.rail("c", y=372)
        d.branch("b", "rail", "cap", "Mass", "5", sub="b")
        d.source("b", "diss", "Load", "10", sub="d")
        assert check(d).ok, check(d).text()
        assert solve(d.build()).node("b").angle == 45
        d.diagram.node("b").angle = 135
        assert solve(d.build()).node("b").angle == 135, "the author's is kept"

    def test_one_node_is_a_chain_of_one(self):
        d = describe(self.build([{"id": "a", "label": "Alone"}], []))
        assert d.nodes == [("a", "free", (200, 150))]


class TestTheHotEnd:
    @staticmethod
    def chain(**values):
        nodes = [{"id": i, "label": i.upper(), "sub": i,
                  **({"value": values[i]} if i in values else {})}
                 for i in "abc"]
        return {"units": {"R": "K/W", "T": "K", "P": "W"}, "nodes": nodes,
                "branches": [{"from": "a", "to": "b", "kind": "cond"},
                             {"from": "b", "to": "c", "kind": "cond"}]}

    @staticmethod
    def order(data):
        """Node ids left to right, which is the solver's order; `describe`
        lists nodes in the file's order."""
        nodes = describe(Diagram.from_dict(data)).nodes
        return [i for i, _, _ in sorted(nodes, key=lambda n: n[2][0])]

    def test_the_hotter_end_is_first(self):
        assert self.order(self.chain(a="10", c="300")) == ["c", "b", "a"]
        assert self.order(self.chain(a="300", c="10")) == ["a", "b", "c"]

    def test_temperature_picks_the_end_and_only_the_end(self):
        """A heater in the middle: the chain order stays a chain."""
        assert self.order(self.chain(a="100", b="500", c="10")) \
            == ["a", "b", "c"]

    def test_then_the_end_a_source_arrives_at(self):
        data = self.chain()
        data["sources"] = [{"to": "c", "kind": "diss", "value": "10"}]
        assert self.order(data) == ["c", "b", "a"]

    def test_then_the_one_written_first(self):
        assert self.order(self.chain()) == ["a", "b", "c"]

    def test_nodes_are_listed_in_file_order_whichever_end_is_hot(self):
        """`describe` keeps the file's order for its nodes block; the
        solver's order shows in the coordinates, not in the listing."""
        d = describe(Diagram.from_dict(self.chain(a="10", c="300")))
        assert [i for i, _, _ in d.nodes] == ["a", "b", "c"]
        xs = {i: a[0] for i, _, a in d.nodes}
        assert xs["c"] < xs["b"] < xs["a"]


class TestWhatIsKeptAndWhatIsMeasured:
    def test_an_explicit_node_keeps_its_place_and_the_next_is_measured_from_it(self):
        out = solve(Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "label": "A", "value": "300", "sub": "a"},
                      {"id": "b", "label": "B", "value": "200", "sub": "b",
                       "at": [600, 150]},
                      {"id": "c", "label": "C", "value": "100", "sub": "c"}],
            "branches": [{"from": "a", "to": "b", "kind": "cond", "value": "1"},
                         {"from": "b", "to": "c", "kind": "cond", "value": "1"}]}))
        assert out.node("a").at == [200, 150]
        assert out.node("b").at == [600, 150]
        assert out.node("c").at[0] > 600 + 200

    def test_a_run_is_as_wide_as_its_labels_need(self):
        wide = "A label so long that two hundred and twenty is nowhere near"
        d = Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "label": "A", "value": "300", "sub": "a"},
                      {"id": "b", "label": "B", "value": "200", "sub": "b"}],
            "branches": [{"from": "a", "to": "b", "kind": "cond",
                          "label": wide, "value": "1"}]})
        out = solve(d)
        assert out.node("b").at[0] - out.node("a").at[0] > 220
        assert "nodes-too-close" not in codes(check(d))
        assert check(d).ok, check(d).text()

    def test_a_series_comb_gets_the_run_its_boxes_need(self):
        d = Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "label": "A", "value": "300", "sub": "a"},
                      {"id": "b", "label": "B", "value": "200", "sub": "b"}],
            "branches": [{"from": "a", "to": "b", "kind": "cond",
                          "label": "Course", "value": "1", "count": 3,
                          "arrangement": "series"}]})
        out = solve(d)
        assert out.node("b").at[0] - out.node("a").at[0] >= 3 * 84
        assert check(d).ok, check(d).text()

    def test_the_habit_is_the_floor(self):
        d = Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "sub": "a"}, {"id": "b", "sub": "b"}],
            "branches": [{"from": "a", "to": "b", "kind": "cond"}]})
        assert solve(d).node("b").at == [420, 150]


class TestPairsAndSources:
    @staticmethod
    def pair(third=False, repeated=False):
        branches = [{"from": "a", "to": "b", "kind": "conv", "label": "Air",
                     "value": "1"},
                    {"from": "a", "to": "b", "kind": "rad", "label": "Walls",
                     "value": "6"}]
        if third:
            branches.append({"from": "a", "to": "b", "kind": "cond",
                             "label": "Strap", "value": "2"})
        if repeated:
            branches[0].update(count=4, arrangement="parallel")
        return Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "label": "A", "value": "300", "sub": "a"},
                      {"id": "b", "label": "B", "value": "200", "sub": "b",
                       "kind": "fixed"}],
            "branches": branches})

    def test_a_third_branch_keeps_the_straight_run(self):
        out = solve(self.pair(third=True))
        assert [bool(b.via) for b in out.branches] == [True, True, False]
        assert [b.side for b in out.branches] == ["up", "down", "auto"]

    def test_a_repeated_branch_keeps_the_run_and_the_plain_one_goes_round(self):
        out = solve(self.pair(repeated=True))
        assert not out.branches[0].via and out.branches[1].via
        assert out.branches[1].side == "up"
        assert check(self.pair(repeated=True)).ok

    def test_an_authored_side_is_kept(self):
        d = self.pair()
        d.branches[0].side = "left"
        assert solve(d).branches[0].side == "left"

    def test_a_pair_the_author_routed_is_left_alone(self):
        d = self.pair()
        d.branches[0].via = [[248, 150], [248, 60], [372, 60], [372, 150]]
        d.branches[1].via = []
        out = solve(d)
        assert out.branches[0].via == d.branches[0].via
        assert not out.branches[1].via

    @staticmethod
    def sourced(node, **source):
        nodes = [{"id": i, "label": i.upper(), "value": v, "sub": i}
                 for i, v in (("a", "300"), ("b", "200"), ("c", "100"))]
        return Diagram.from_dict({
            "units": {"R": "K/W", "T": "K", "P": "W", "q": "W"},
            "nodes": nodes,
            "branches": [{"from": "a", "to": "b", "kind": "cond", "value": "1"},
                         {"from": "b", "to": "c", "kind": "cond", "value": "1"}],
            "sources": [dict({"kind": "diss", "label": "Load", "value": "5",
                              "sub": "d"}, **source)]})

    def test_a_source_on_the_hot_end_stays_on_the_left(self):
        out = solve(self.sourced("a", to="a"))
        s = out.sources[0]
        assert s.angle == 0 and s.at == [200 - 110, 150]

    def test_a_source_on_an_interior_node_comes_from_above(self):
        out = solve(self.sourced("b", to="b"))
        s, b = out.sources[0], out.node("b").at
        assert s.angle == 90 and s.at == [b[0], b[1] - 110]
        assert check(self.sourced("b", to="b")).ok

    def test_heat_leaving_an_interior_node_leaves_downward(self):
        """It left upward once, which put an outbound source's symbol above
        the node — on top of an inbound one turned to arrive from above.
        Heat in at the top, out at the bottom, as run 4's cryostat drew."""
        d = self.sourced("b", **{"from": "b", "kind": "flow"})
        out = solve(d)
        s, b = out.sources[0], out.node("b").at
        assert s.angle == 90 and s.at == [b[0], b[1] + 110]

    def test_an_authored_angle_is_kept(self):
        out = solve(self.sourced("b", to="b", angle=45))
        assert out.sources[0].angle == 45

    def test_an_authored_source_position_is_kept(self):
        out = solve(self.sourced("b", to="b", at=[1, 2]))
        assert out.sources[0].at == [1, 2]


# What the solver makes of the gallery with every coordinate removed. Six of
# the ten are chains. Four of those check clean; the immersion rack's
# junction label is aimed by its authored `angle: 135` at the spot the solver
# put the source, and the cryostat's two sources on one node carry angles
# chosen for a different placement — both are the author's fields, kept, and
# both are what `check` is for. The dewar has three branches between each
# pair of its nodes and three sources on its middle one, which is not a
# ladder: it solves, and what it reports is labels and a diagonal source's
# lead across a routed leg — never a wire through a wall, two symbols on one
# run, or a run too narrow.
GALLERY = {
    "01-spacecraft": ("refused", "node 'panel' joins 3 others"),
    "02-building": ("refused", "node 'gf' joins 4 others"),
    "03-cryogenic": ("findings", None),
    "04-immersion": ("findings", ["label-adrift"]),
    "05-laser-diode": ("refused", "node 'cb' joins 3 others"),
    "06-battery": ("ok", None),
    "07-furnace": ("ok", None),
    "08-cryostat": ("findings", ["label-adrift"]),
    "09-subsea": ("ok", None),
    "10-pv": ("refused", "node 'cell' joins 3 others"),
}
NEVER = {"wire-through-wall", "symbols-overlap", "nodes-too-close",
         "symbol-off-its-run", "off-canvas"}


@pytest.mark.skipif(not (ROOT / "examples" / "gallery").exists(),
                    reason="the gallery is not present")
@pytest.mark.parametrize("folder", sorted(GALLERY))
def test_the_gallery_without_its_coordinates(folder):
    path = next((ROOT / "examples" / "gallery" / folder).glob("*.json"))
    data = bare(json.loads(path.read_text(encoding="utf-8")))
    outcome, detail = GALLERY[folder]
    if outcome == "refused":
        with pytest.raises(DiagramError, match=detail):
            layout(Diagram.from_dict(data))
        return
    report = check(Diagram.from_dict(data))
    assert not (set(codes(report)) & NEVER), report.text()
    if outcome == "ok":
        assert report.ok, report.text()
    else:
        assert not report.ok
        if detail is not None:
            assert codes(report) == detail, report.text()


def test_the_cli_writes_the_diagram_back_placed(tmp_path, capsys):
    path = tmp_path / "bare.json"
    path.write_text(json.dumps({
        "units": {"R": "K/W", "T": "K"},
        "nodes": [{"id": "a", "label": "A", "value": "300", "sub": "a"},
                  {"id": "b", "label": "B", "value": "200", "sub": "b"}],
        "branches": [{"from": "a", "to": "b", "kind": "cond", "value": "1"}]}),
        encoding="utf-8")
    assert main(["solve", str(path)]) == 0
    out = tmp_path / "bare.solved.json"
    assert out.exists()
    placed = json.loads(out.read_text(encoding="utf-8"))
    assert placed["nodes"][0]["at"] == [200, 150]
    x, y = placed["nodes"][1]["at"]
    assert y == 150 and x >= 420 and x % 10 == 0
    assert main(["solve", str(path), "-o", "-"]) == 0
    assert '"at"' in capsys.readouterr().out
