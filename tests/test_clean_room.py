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

from thermodraw import Diagram, DiagramBuilder, check, describe
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

    # `house.json` stopped exiting clean when `wire-through-wall` was
    # written, and it is right to: two of its branches arrive at a boundary
    # node from below and run through that node's hatching. The diagram is
    # evidence and is not retouched, so the expectation is named here rather
    # than the assertion weakened. Anything beyond these two still fails.
    KNOWN = {("02-building", "house.json"): [
        ("wire-through-wall", "node 'out'"),
        ("wire-through-wall", "node 'sky'"),
    ]}

    @pytest.mark.parametrize("folder,name", FILES)
    def test_it_still_exits_clean(self, folder, name):
        report = check(diagram(gallery(folder, name)))
        expected = self.KNOWN.get((folder, name), [])
        got = sorted((f.code, f.where) for f in report.findings
                     if f.severity != "note")
        assert got == sorted(expected), report.text()
        if not expected:
            assert report.ok

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


# ------------------------------------- `--physics` says what it did not check
class TestPhysicsSaysWhatItDidNotCheck:
    """02: the worst-balanced node in the house, 1.47 kW in against 693 W
    out, was absent from the report because the wall's interior junctions
    have no temperature — the idiom the schema recommends. 05: three of
    eight nodes never examined, and a reader would conclude they passed.
    Both asked for one line saying how many were checked."""

    @staticmethod
    def stack(middle=None, source="diss"):
        b = DiagramBuilder(R="K/W", T="°C", P="W", **{"q″": "W/cm²"})
        b.node("a", "Junction", "65", at=(0, 0), sub="j")
        b.node("m", "Submount base", middle, at=(260, 0))
        b.node("z", "Water", "18", kind="fixed", at=(520, 0), sub="w")
        b.branch("a", "m", "cond", "Solder", "0.0875")
        b.branch("m", "z", "cond", "Contact", "0.045")
        if source == "diss":
            b.source("a", "diss", "Waste heat", "80", sub="d")
        else:
            b.source("a", "flux", "Emitting face", "800", sub="e",
                     outward=True)
        return b

    def test_a_neighbour_with_no_temperature_is_reported_once(self):
        found = one(check(self.stack(), physics=True), "physics-not-checked")
        assert found.severity == "note"
        assert found.message.startswith("checked 0 of 2 free nodes")
        assert "a (neighbour 'm' has no temperature)" in found.message
        assert "m (it has no temperature)" in found.message

    def test_a_flux_source_is_named_as_the_reason(self):
        found = one(check(self.stack("58", "flux"), physics=True),
                    "physics-not-checked")
        assert "a (source 0 is a flux, which has no area)" in found.message
        assert "checked 1 of 2" in found.message

    def test_a_diagram_whose_nodes_were_all_checked_says_nothing(self):
        report = check(self.stack("58"), physics=True)
        assert "physics-not-checked" not in codes(report)

    def test_an_unknown_unit_is_a_note_not_silence(self):
        b = DiagramBuilder(R="furlongs", T="°C", P="W")
        b.node("a", "Hot", "50", at=(0, 0), sub="a")
        b.node("b", "Cold", "40", kind="fixed", at=(300, 0), sub="b")
        b.branch("a", "b", "cond", "Slab", "1.0")
        b.source("a", "diss", "Load", "10", sub="d")
        found = one(check(b, physics=True), "physics-not-checked")
        assert "'furlongs'" in found.message
        assert "K/W" in found.message and "mK/W" in found.message

    def test_the_balance_message_is_ascii(self):
        """Its separator was an em dash, and on a cp1252 console it printed
        as a replacement character; two agents re-captured their output
        under PYTHONIOENCODING to get a clean record."""
        report = check(self.stack("40"), physics=True)
        found = [f for f in report.findings if f.code == "node-does-not-balance"]
        assert found and all(f.line().isascii() for f in found)

    @needs_gallery
    def test_the_house_and_the_diode_say_what_their_agents_found_by_hand(self):
        house = one(check(diagram(gallery("02-building", "house.json")),
                          physics=True), "physics-not-checked")
        assert "gf (neighbour 'w1' has no temperature)" in house.message
        diode = one(check(diagram(gallery("05-laser-diode", "diode.json")),
                          physics=True), "physics-not-checked")
        assert "sm, cb (neighbour 'smb' has no temperature)" in diode.message
        assert "j (source 1 is a flux, which has no area)" in diode.message


# -------------------------------------------- a counted source says "each of"
class TestACountedSourceSaysEachOf:
    """04: `describe` printed "8 in parallel" for eight processors, borrowing
    the branch wording for a quantity the schema says has no arrangement."""

    def test_the_label_reads_each_of_eight(self):
        from thermodraw import describe
        b = DiagramBuilder(R="K/W", T="°C", P="W")
        b.node("j", "Junction", "72", at=(0, 0), sub="j")
        b.node("s", "Sink", "40", kind="fixed", at=(300, 0), sub="s")
        b.branch("j", "s", "cond", "Path", "0.5")
        b.source("j", "diss", "Processor dissipation", "400", sub="p", count=8)
        says = [l.says for l in describe(b).lines if l.ref.startswith("source")]
        assert says == ["Processor dissipation | P_p = 400 W "
                        "| each of 8 = 3200 W"]
        assert not any("in parallel" in s for s in says)


# ------------------------------------- the network block shows what matters
class TestTheNetworkBlockShowsSourcesAndDirection:
    """All four agents that used `flow` said `coil --flow-branch-- tw` was
    the one thing they most wanted confirmed and could not be; three said a
    source on the wrong node would leave the block byte-identical; one
    could not see eight paths in `j --cond-- ihs`."""

    @staticmethod
    def tec(reverse=False):
        b = DiagramBuilder(R="K/W", T="°C", P="W", q="W")
        b.node("cb", "Cooler body", "41", at=(0, 0), sub="cb")
        b.node("th", "TEC hot face", "48", at=(260, 0), sub="h")
        b.node("amb", "Air", "25", kind="fixed", at=(520, 0), sub="amb")
        b.node("w", "Water", "18", kind="fixed", at=(0, 200), sub="w")
        if reverse:
            b.branch("th", "cb", "flow", "TEC pumps heat", "60", sub="pump")
        else:
            b.branch("cb", "th", "flow", "TEC pumps heat", "60", sub="pump")
        b.branch("th", "amb", "conv", "Baseplate", "0.23")
        b.branch("cb", "w", "cond", "Channels", "0.045", count=4,
                 arrangement="parallel")
        b.source("cb", "diss", "Waste heat", "80", sub="d")
        b.source("th", "flow", "Rejected", "100", sub="r", outward=True)
        return b

    @staticmethod
    def block(b):
        from thermodraw import describe
        text = describe(b).text()
        return text.split("network:\n")[1].split("\n\n")[0].splitlines()

    def test_a_flow_branch_carries_an_arrow(self):
        assert "  cb --flow-> th" in self.block(self.tec())

    def test_written_backwards_it_reads_differently(self):
        assert "  th --flow-> cb" in self.block(self.tec(reverse=True))
        assert self.block(self.tec()) != self.block(self.tec(reverse=True))

    def test_sources_are_listed_with_their_direction(self):
        lines = self.block(self.tec())
        assert "  source 0 --diss-> cb" in lines
        assert "  th --flow-> source 1" in lines

    def test_a_counted_branch_says_how_many(self):
        assert "  cb --cond x4 parallel-- w" in self.block(self.tec())

    def test_the_json_carries_the_same(self):
        from thermodraw import describe
        d = describe(self.tec()).to_dict()
        flow = next(e for e in d["edges"] if e["kind"] == "flow")
        assert flow["directed"] and flow["from"] == "cb"
        cond = next(e for e in d["edges"] if e["kind"] == "cond")
        assert (cond["count"], cond["arrangement"]) == (4, "parallel")
        assert d["sources"] == [
            {"index": 0, "node": "cb", "kind": "diss", "outward": False},
            {"index": 1, "node": "th", "kind": "flow", "outward": True}]


# ---------------------------------------- a label that is simply too wide
class TestALabelWiderThanItsRoom:
    """04, rounds 2–4: `sat`'s label was pushed 48 to get around the box on
    one side; move that box and it was pushed 48 to get around the box on
    the other side; `angle` made it 84. The label was 192 wide between two
    runs of 260, and no finding said so."""

    @staticmethod
    def rack(gap=260):
        """The rack's middle: a phase node with a wide label, a capacitance
        hanging below it so the label cannot flip, two short runs."""
        b = DiagramBuilder(R="K/W", T="°C", C="J/K")
        b.node("ihs", "Heat spreader", "61", at=(200, 160), sub="ihs")
        b.node("sat", "Saturated fluid, boiling and condensing", "49",
               kind="phase", at=(200 + gap, 160), sub="sat")
        b.node("coil", "Condenser coil", "40", kind="fixed",
               at=(200 + 2 * gap, 160), sub="coil")
        b.branch("ihs", "sat", "conv", "Boiling", "0.00375")
        b.branch("sat", "coil", "conv", "Condensing", "0.0028")
        b.branch("sat", "rail", "cap", "Fluid inventory", "240000", sub="f")
        b.rail("coil", y=320)
        return b

    def test_it_says_the_width_and_the_room_and_names_both_nodes(self):
        found = one(check(self.rack()), "label-adrift")
        assert found.where == "node 'sat'"
        assert "wide and the room between branch 0 ihs->sat and " \
               "branch 1 sat->coil is" in found.message
        assert "cannot clear it" in found.message
        assert found.remedy.startswith(
            "move node 'ihs' and node 'coil' further from node 'sat' with `at`")

    def test_moving_the_nodes_apart_clears_it(self):
        assert "label-adrift" not in codes(check(self.rack(gap=360)))

    @needs_gallery
    def test_the_rack_at_its_first_spacing_says_192_against_176(self):
        d = gallery("04-immersion", "rack.json")
        back = {"sat": -100, "coil": -200, "tw": -200, "fw": -200, "amb": -200}
        for n in d["nodes"]:
            n["at"][0] += back.get(n["id"], 0)
        for b in d["branches"]:
            if b.get("from") == "tw" and "at" in b:
                b["at"][0] -= 200
            if b.get("from") == "sat" and b.get("to") == "rail" and "at" in b:
                b["at"][0] -= 100
        d["rail"]["span"] = [180, 1840]
        found = one(check(diagram(d)), "label-adrift")
        assert "its label is 192 wide and the room between branch 1 " \
               "ihs->sat and branch 2 sat->coil is 176" in found.message


# ============================================================ the third run
# `examples/gallery/FINDINGS-run-3.md`. Same house rule: assert the remedy,
# apply it literally, assert it worked.


# ------------------------------ two symbols on one run are told to use `via`
class TestTwoSymbolsOnOneRunAreToldToRoute:
    """07, rounds 1 and 2: `symbols-overlap` said "move one of them with
    `at`", which cannot clear it. Both boxes sit on the single run between
    one pair of nodes, so sliding one trades overlap for near-overlap, and
    the agent's literal application took the overlap from 32 to 4 with the
    error standing and a `wire-through-symbol` warning added."""

    @staticmethod
    def pair(via=None):
        """A shell losing heat to the shop by convection and radiation, the
        parallel pair every steady-state diagram ends with."""
        d = {"units": {"R": "K/W", "T": "°C"},
             "nodes": [{"id": "shell", "label": "Steel shell",
                        "value": "120", "at": [400, 200]},
                       {"id": "shop", "kind": "fixed", "label": "Shop air",
                        "value": "30", "at": [760, 200]}],
             "branches": [
                 {"from": "shell", "to": "shop", "kind": "conv",
                  "label": "Natural convection", "value": "0.05",
                  "side": "up"},
                 {"from": "shell", "to": "shop", "kind": "rad",
                  "label": "Radiation to shop", "value": "0.075",
                  "side": "down"}]}
        if via:
            d["branches"][1]["via"] = via
        return diagram(d)

    def test_the_remedy_names_via_and_not_at(self):
        found = one(check(self.pair()), "symbols-overlap")
        assert "`via`" in found.remedy
        assert "with `at`" not in found.remedy

    def test_applying_it_literally_clears_it(self):
        """Routed clear and brought back to the node's own line, which is
        what the remedy says and what the schema's arrival rule has always
        said. Dropping straight onto `shop` from underneath instead puts the
        wire through that node's wall -- see the class below."""
        report = check(self.pair(via=[[400, 320], [700, 320], [700, 200]]))
        assert report.ok, report.text()

    def test_dropping_onto_the_boundary_from_below_is_caught(self):
        """The half-applied version. Worth pinning: it is why the remedy
        names the arrival and not only the routing."""
        assert "wire-through-wall" in codes(
            check(self.pair(via=[[400, 320], [760, 320]])))

    def test_a_symbol_against_a_wall_still_says_at(self):
        """The fallback is not lost: two things that do *not* share a run
        have nothing to route around each other, and `at` is the field."""
        d = {"units": {"R": "K/W", "T": "°C"},
             "nodes": [{"id": "a", "kind": "fixed", "label": "Hot",
                        "value": "200", "at": [200, 200]},
                       {"id": "b", "label": "Mid", "value": "100",
                        "at": [420, 200]}],
             "branches": [{"from": "a", "to": "b", "kind": "cond",
                           "label": "Wall", "value": "0.5", "count": 3,
                           "arrangement": "series"}]}
        found = one(check(diagram(d)), "symbols-overlap")
        assert found.remedy == "move one of them with `at`"


# ------------------------------------- a wire through a boundary node's wall
class TestAWireThroughABoundaryWall:
    """08: the magnet hangs from its mount, so the honest drawing puts the
    mount above it. A boundary wall is always drawn *below* its node, so the
    strut then leaves through its own boundary's hatching -- and `check`
    passed that in silence, which is why the agent shipped the arrangement it
    could verify instead of the one it wanted."""

    @staticmethod
    def hung(mount_y):
        """A body on a strut to a mount. `mount_y` above the body is the
        arrangement that puts the wall in the way."""
        return diagram({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "body", "label": "Cold mass", "value": "4",
                       "at": [400, 300]},
                      {"id": "mount", "kind": "fixed", "label": "Mount",
                       "value": "300", "at": [400, mount_y]}],
            "branches": [{"from": "body", "to": "mount", "kind": "cond",
                          "label": "Strut", "value": "50"}]})

    def test_a_branch_arriving_from_below_is_reported(self):
        found = one(check(self.hung(mount_y=80)), "wire-through-wall")
        assert found.severity == "warning"
        assert found.where == "node 'mount'"
        assert "runs through the boundary wall of node 'mount'" in found.message

    def test_the_remedy_names_at_and_not_angle(self):
        found = one(check(self.hung(mount_y=80)), "wire-through-wall")
        assert "move node 'mount' with `at`" in found.remedy
        # `angle` on a node moves its label and nothing else; the wall does
        # not turn, so offering it would be the advice that appears to work.
        assert "`angle`" not in found.remedy

    def test_putting_the_boundary_below_clears_it(self):
        report = check(self.hung(mount_y=560))
        assert "wire-through-wall" not in codes(report), report.text()

    def test_a_nodes_own_stub_is_not_reported(self):
        """Every `fixed` node has a stub running into its own wall. That is
        the one wire that is supposed to be there."""
        d = diagram({
            "units": {"R": "K/W", "T": "°C"},
            "nodes": [{"id": "a", "label": "Body", "value": "90",
                       "at": [200, 150]},
                      {"id": "amb", "kind": "fixed", "label": "Air",
                       "value": "25", "at": [520, 150]}],
            "branches": [{"from": "a", "to": "amb", "kind": "cond",
                          "label": "Foot", "value": "0.5"}]})
        assert "wire-through-wall" not in codes(check(d))

    @needs_gallery
    def test_it_finds_the_two_in_the_house(self):
        """Run 2's `house.json` has the real thing in it, twice, undetected
        until this rule was written. The diagram is evidence and is not
        retouched."""
        found = [f for f in check(diagram(gallery("02-building", "house.json"))
                                  ).findings if f.code == "wire-through-wall"]
        assert sorted(f.where for f in found) == ["node 'out'", "node 'sky'"]


# --------------------------------------------- a boundary wall gets a row
class TestDescribeGivesTheWallARow:
    """08 again, the other half: `describe` counted grounds on the
    `placements:` line and gave them no row, so the tool whose question is
    "is this the drawing you meant" could not answer it for the one element
    whose position was in doubt."""

    @staticmethod
    def one_wall():
        return diagram({
            "units": {"R": "K/W", "T": "°C"},
            "nodes": [{"id": "a", "label": "Body", "value": "90",
                       "at": [200, 150]},
                      {"id": "amb", "kind": "fixed", "label": "Air",
                       "value": "25", "at": [520, 150]}],
            "branches": [{"from": "a", "to": "amb", "kind": "cond",
                          "label": "Foot", "value": "0.5"}]})

    def test_the_wall_has_its_own_row(self):
        rows = [l for l in describe(self.one_wall()).lines
                if l.kind == "ground"]
        assert len(rows) == 1
        assert rows[0].label_at is None, "a wall carries no text of its own"

    def test_it_is_not_keyed_the_same_as_its_node(self):
        """A ground carries its node's `ref`, so two rows under one key lose
        one of the two -- and the one lost was the node's."""
        lines = describe(self.one_wall()).lines
        refs = [l.ref for l in lines]
        assert len(refs) == len(set(refs)), refs
        assert "wall of node 'amb'" in refs

    def test_it_says_which_side_of_the_node_the_wall_landed(self):
        rows = {l.ref: l for l in describe(self.one_wall()).lines}
        node, wall = rows["node 'amb'"], rows["wall of node 'amb'"]
        assert wall.at[1] > node.at[1], "the wall is drawn below its node"
        assert "wall of node 'amb'" in describe(self.one_wall()).text()


# ------------------------------------- a group says what it comes to
class TestAGroupSaysWhatItComesTo:
    """10: the clip group rendered `R_cond = 1.6 K/W | 4 in parallel` and
    never showed the 0.4 K/W it presents, so a reader checking the page got
    6.25 W where the answer was 25 W."""

    @staticmethod
    def units():
        return diagram({"units": {"R": "K/W", "C": "J/K", "T": "°C",
                                  "P": "W", "q": "W"},
                        "nodes": [{"id": "a", "at": [0, 0]}]})

    def test_resistances_divide_in_parallel(self):
        assert self.units().count_text(4, "parallel", "cond", "1.6") == \
            "4 in parallel = 0.4 K/W"

    def test_resistances_multiply_in_series(self):
        assert self.units().count_text(3, "series", "cond", "0.06") == \
            "3 in series = 0.18 K/W"

    def test_a_capacitance_is_the_dual(self):
        """The case most likely to be got backwards later. Capacitances add
        in parallel and divide in series, which is the opposite of a
        resistance, and one expression with a sign flip is how that comes to
        be written the wrong way round."""
        d = self.units()
        assert d.count_text(4, "parallel", "cap", "50") == \
            "4 in parallel = 200 J/K"
        assert d.count_text(2, "series", "cap", "50") == \
            "2 in series = 25 J/K"

    def test_changing_the_count_changes_the_value(self):
        d = self.units()
        assert d.count_text(2, "parallel", "cond", "1.6").endswith("0.8 K/W")
        assert d.count_text(8, "parallel", "cond", "1.6").endswith("0.2 K/W")

    def test_a_rate_and_a_break_state_no_group_value(self):
        """`flow` carries a rate rather than a resistance, and `break`
        carries nothing. Neither has a single number to fold."""
        d = self.units()
        assert d.count_text(4, "parallel", "flow", "12") == "4 in parallel"
        assert d.count_text(4, "parallel", "break", None) == "4 in parallel"

    def test_a_value_that_is_not_a_number_is_left_alone(self):
        assert self.units().count_text(4, "parallel", "cond", "about 2") == \
            "4 in parallel"

    def test_the_per_item_value_is_untouched(self):
        """The stored value is still exactly the digits that were typed; the
        group value is a second, derived number sitting after the
        arrangement."""
        d = self.units()
        assert d.value_text("cond", "2.10") == "2.10 K/W"
        assert "= 4 in parallel" not in d.count_text(4, "parallel", "cond",
                                                     "2.10")

    def test_a_counted_source_says_its_total(self):
        assert self.units().source_count_text(8, "diss", "400") == \
            "each of 8 = 3200 W"

    @needs_gallery
    def test_the_clips_say_nought_point_four(self):
        d = gallery("10-pv", "array.json")
        says = [l.says for l in describe(diagram(d)).lines
                if "Mounting clips" in l.says]
        assert says == ["Mounting clips | R_cond = 1.6 K/W "
                        "| 4 in parallel = 0.4 K/W"]
