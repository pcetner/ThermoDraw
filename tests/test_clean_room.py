"""What the clean-room run found, reproduced and then fixed.

Five agents drew five diagrams from `docs/schema.md` alone and applied every
remedy the checker named, literally, before trying anything else — that was
the brief. Seven of the thirty-one could not be applied as written, and the
transcripts in `examples/gallery/*/transcript.md` say which. Each class here
is one of those, rebuilt as the smallest diagram that produces it, with the
house rule applied: assert the remedy, then apply it, then assert it worked.

The gallery-derived cases need `examples/`, which is not part of the
installed package; they are skipped without it and fail if it is present but
unreadable, the way `tests/scenes.py` treats the demo scenes.
"""
import copy
import json
import pathlib

import pytest

from thermodraw import Diagram, DiagramBuilder, check
from thermodraw._check import _remedy
from thermodraw._layout import Placement

GALLERY = pathlib.Path(__file__).resolve().parents[1] / "examples" / "gallery"
needs_gallery = pytest.mark.skipif(not GALLERY.exists(),
                                   reason="examples/gallery is not here")


def codes(report):
    return [f.code for f in report.findings]


def one(report, code):
    hits = [f for f in report.findings if f.code == code]
    assert len(hits) == 1, f"expected one {code}, got {codes(report)}"
    return hits[0]


def gallery(folder, name):
    return json.loads((GALLERY / folder / name).read_text(encoding="utf-8"))


def diagram(d):
    return Diagram.from_json(json.dumps(d))


# ------------------------------------ `via` named on something that has none
class TestViaIsOnlyNamedWhereItCanGo:
    """04, rounds 1, 3 and 4: "move a `via` waypoint on branch 0 j->ihs",
    three times, on a `count: 8` branch the validator refuses `via` on.
    01, round 8: "route it around with `via`" for a source's lead, and the
    source table has no such field."""

    @staticmethod
    def rack(angle=None):
        """The immersion rack's hot end as its agent first drew it: eight
        processors in parallel, and the junction's label crowded by the
        comb's riser, which stands a fixed distance out from the node
        whatever the spacing — so neither `via` nor `at` on the nodes can
        clear it, and only the label can move."""
        b = DiagramBuilder(R="K/W", T="°C", P="W")
        b.node("j", "Processor junction, each", "72", at=(200, 160), sub="j",
               **({} if angle is None else {"angle": angle}))
        b.node("ihs", "Heat spreader", "61", at=(460, 160), sub="ihs")
        b.node("amb", "Ambient", "25", kind="fixed", at=(720, 160), sub="amb")
        b.branch("j", "ihs", "cond", "TIM, each", "0.0275", count=8,
                 arrangement="parallel")
        b.branch("ihs", "amb", "conv", "Air", "0.5")
        b.source("j", "diss", "Processor dissipation", "400", sub="p", count=8,
                 angle=270)
        return b

    def test_a_repeated_branch_is_not_told_to_move_a_waypoint(self):
        found = one(check(self.rack()), "label-adrift")
        assert found.where == "node 'j'"
        assert "wire of branch 0 j->ihs" in found.message
        assert "`via`" not in found.remedy
        assert "`at`" not in found.remedy
        assert found.remedy.startswith("`angle`")

    def test_turning_the_label_as_it_says_clears_it(self):
        assert "label-adrift" not in codes(check(self.rack(angle=135)))

    def test_a_straight_wire_is_told_to_gain_a_via_not_move_one(self):
        wire = Placement("wire", ref="branch 0 a->b", role="branch",
                         ends=("a", "b"))
        assert "give branch 0 a->b a `via`" in _remedy(wire)

    def test_a_wire_with_a_via_is_told_to_move_it(self):
        wire = Placement("wire", ref="branch 0 a->b", role="branch",
                         ends=("a", "b"), via=((10.0, 10.0),))
        assert "move a `via` waypoint on branch 0 a->b" in _remedy(wire)

    def test_the_rail_is_not_told_to_gain_a_via(self):
        rail = Placement("wire", ref="rail", role="rail")
        assert "`via`" not in _remedy(rail)
        assert "`rail.y`" in _remedy(rail)

    @needs_gallery
    def test_a_source_lead_through_a_symbol_names_the_source(self):
        """01, round 8, rebuilt from the committed file: the capacitance
        with its `via` and no `at`, so its symbol sits where the Earth-IR
        lead crosses."""
        d = gallery("01-spacecraft", "satellite.json")
        cap = next(b for b in d["branches"] if b["to"] == "rail")
        cap.pop("at")
        found = one(check(diagram(d)), "wire-through-symbol")
        assert "source 1 -> panel runs straight through" in found.message
        assert "`via`" not in found.remedy
        assert found.remedy.startswith("move source 1 -> panel with `at`")
        assert "move the symbol along its branch with `at`" in found.remedy
        # the second option, which is what its agent did
        cap["at"] = [440, 350]
        assert "wire-through-symbol" not in codes(check(diagram(d)))


# -------------------------------------- the parallel-pair remedy is derived
class TestParallelPairRemedyIsDerived:
    """02, rounds 1–2: `set side to "down" on the lower of the two`, on a
    pair that both already had `"side": "down"`, where the lower one was
    the lower one. Applied literally it changed nothing, and the note
    survived. 03, round 2, and 02, round 3: with three branches between one
    pair of nodes the same remedy only rotates which pair is reported."""

    @staticmethod
    def pair(upper="down", lower="down"):
        b = DiagramBuilder(R="K/W", T="°C", q="W")
        b.node("a", "Zone", "20", at=(200, 150), sub="a")
        b.node("b", "Outside", "-5", kind="fixed", at=(600, 150), sub="b")
        b.branch("a", "b", "mixed", "Glazing", "0.31", sub="glz", side=upper)
        b.branch("a", "b", "flow", "Infiltration", "185", sub="inf",
                 via=[(240, 150), (240, 260), (560, 260), (560, 150)],
                 at=(400, 260), side=lower)
        return b

    def test_both_already_down_names_the_upper_one_and_up(self):
        found = one(check(self.pair()), "parallel-pair-same-side")
        assert found.remedy == 'set `side` to "up" on branch 0 a->b'

    def test_applying_it_clears_the_note(self):
        assert "parallel-pair-same-side" not in codes(
            check(self.pair(upper="up")))

    def test_both_up_names_the_lower_one_and_down(self):
        found = one(check(self.pair("up", "up")), "parallel-pair-same-side")
        assert found.remedy == 'set `side` to "down" on branch 1 a->b'
        assert "parallel-pair-same-side" not in codes(
            check(self.pair("up", "down")))

    @staticmethod
    def three():
        b = DiagramBuilder(R="K/W", T="°C")
        b.node("a", "Vessel", "300", kind="fixed", at=(200, 340), sub="v")
        b.node("b", "Shield", "40", at=(760, 340), sub="sh")
        b.branch("a", "b", "rad", "MLI", "289",
                 via=[(260, 340), (260, 100), (700, 100), (700, 340)],
                 at=(480, 100))
        b.branch("a", "b", "cond", "Current leads", "1720")
        b.branch("a", "b", "cond", "Struts", "433",
                 via=[(260, 340), (260, 580), (700, 580), (700, 340)],
                 at=(480, 580))
        return b

    def test_three_between_two_nodes_is_one_note_with_no_side(self):
        report = check(self.three())
        assert codes(report).count("parallel-pair-same-side") == 1
        found = one(report, "parallel-pair-same-side")
        assert "branch 0 a->b, branch 1 a->b, branch 2 a->b" in found.message
        assert "two of them share one" in found.message
        assert '"down"' not in found.remedy and '"up"' not in found.remedy
        assert "safe to leave" in found.remedy


# ------------------------------------------------ the five, as they stand
@needs_gallery
class TestTheFiveDiagramsAsTheirAgentsLeftThem:
    """Every remedy on the committed set names a field the element can take.
    This is the test that would have failed on each of the seven remedies
    the run could not apply as written."""

    FILES = [("01-spacecraft", "satellite.json"),
             ("02-building", "house.json"),
             ("03-cryogenic", "dewar.json"),
             ("04-immersion", "rack.json"),
             ("05-laser-diode", "diode.json")]

    @pytest.mark.parametrize("folder,name", FILES)
    def test_it_still_exits_clean(self, folder, name):
        assert check(diagram(gallery(folder, name))).ok

    @pytest.mark.parametrize("folder,name", FILES)
    def test_no_remedy_names_a_via_the_branch_cannot_have(self, folder, name):
        d = gallery(folder, name)
        for state in perturbed(d):
            for f in check(diagram(state)).findings:
                assert_via_is_possible(f.remedy, state)

    @pytest.mark.parametrize("folder,name", FILES)
    def test_no_pair_note_names_down_on_a_group_of_three(self, folder, name):
        for f in check(diagram(gallery(folder, name))).findings:
            if f.code == "parallel-pair-same-side" and "," in f.message:
                assert '"down"' not in f.remedy


def perturbed(d):
    """The committed diagram, then the same with every `at` and `side` the
    author added to sources and nodes taken away again — roughly what the
    first draft looked like, and where the impossible remedies came from."""
    yield d
    rough = copy.deepcopy(d)
    for s in rough.get("sources", []):
        s.pop("at", None)
        s.pop("side", None)
    for n in rough.get("nodes", []):
        n.pop("side", None)
        n.pop("angle", None)
    yield rough


def assert_via_is_possible(remedy, state):
    """A remedy that says `via` must be talking about a branch that has one
    or can take one. Refs are parsed here, in a test, and nowhere else."""
    import re
    for option in remedy.split(", or "):
        if "`via`" not in option:
            continue
        assert "source " not in option and "rail" not in option, remedy
        for m in re.finditer(r"branch (\d+) ", option):
            b = state["branches"][int(m.group(1))]
            assert not (b.get("count", 1) > 1), \
                f"`via` on a repeated branch: {remedy}"
            if option.startswith("move a `via` waypoint"):
                assert b.get("via"), f"no waypoint to move: {remedy}"
