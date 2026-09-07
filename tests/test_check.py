"""The checks, and the remedies they recommend.

Every class here is one defect the browser round trip was finding by eye. The
pattern throughout is the same, and it is the point of the file: build the bad
diagram, assert the finding; then apply the remedy the finding names, and
assert it goes away. A check whose remedy is untested is a check that gives
bad advice with authority.
"""
import math
import pathlib

import pytest

from thermodraw import (Diagram, DiagramBuilder, DiagramError, check, core,
                        layout)
from thermodraw._check import (_inside, _obb_gap, _segment_rect_gap, cycles,
                              wire_graph)
from thermodraw._render import LabelRect, compose

HERO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "hero.json"


def codes(report):
    return [f.code for f in report.findings]


def one(report, code):
    """The single finding with this code, or a readable failure."""
    hits = [f for f in report.findings if f.code == code]
    assert len(hits) == 1, f"expected one {code}, got {codes(report)}"
    return hits[0]


# ------------------------------------------------- defect 1: a label adrift
class TestLabelAdrift:
    """A label shoved so far out it reads as belonging to something else.

    `annotate` tries the other side of the branch before it pushes, so a single
    obstruction is handled and never reported. Both sides have to be blocked,
    which is what a waypoint rising straight out of the node it leaves does.
    """

    @staticmethod
    def boxed_in(x=212):
        b = DiagramBuilder(R="K/W", T="°C")
        b.node("h", "Hot pipe", "150", at=(200, 150))
        b.node("c", "Ambient", "25", kind="fixed", at=(560, 150))
        b.branch("h", "c", "conv", "Convection", "0.013",
                 via=[(x, 150), (x, 70), (470, 70), (470, 150)], at=(340, 70))
        b.branch("h", "c", "rad", "Radiation", "0.015",
                 via=[(x, 150), (x, 230), (470, 230), (470, 150)], at=(340, 230))
        return b

    def test_a_via_beside_its_node_strands_the_label(self):
        found = one(check(self.boxed_in()), "label-adrift")
        assert found.where == "node 'h'"
        assert "branch 0 h->c" in found.message
        assert "`side`" in found.remedy or "`via`" in found.remedy

    def test_moving_the_waypoint_is_the_fix_it_recommends(self):
        """The remedy in the message, applied, clears the finding."""
        assert "label-adrift" not in codes(check(self.boxed_in(x=290)))

    def test_a_neighbours_boundary_wall_is_named_as_the_culprit(self):
        """The wall used to be invisible: a label could be placed on it."""
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0))
             .node("b", "B", "50", at=(300, 0))
             .node("w", "Sink", "25", kind="fixed", at=(150, 40))
             .branch("a", "b", "cond", "Across the wall", "0.3",
                     at=(150, 0), side="down"))
        messages = [f.message for f in check(b).findings
                    if f.code == "label-adrift"]
        assert any("boundary wall of node 'w'" in m for m in messages)

    def test_a_roomy_ladder_says_nothing(self):
        """Silence has to mean something, so it must not be rare."""
        def cramped(spacing):
            b = DiagramBuilder(R="K/W", T="°C")
            for i in range(5):
                b.node(f"n{i}", f"Stage number {i}", f"{120 - 9 * i}",
                       at=(i * spacing, 0), sub=f"{i}")
            for i in range(4):
                b.branch(f"n{i}", f"n{i+1}", "cond", f"Interface {i}", "0.35")
            return b

        assert "label-adrift" in codes(check(cramped(150)))
        for spacing in (180, 220, 300):
            assert not codes(check(cramped(spacing))), f"noisy at {spacing}"


class TestNodesTooClose:
    """The cause, where every other finding could only name the symptom.

    On a short run the thing nearest a crowded label is a wire, so
    `label-adrift` correctly named a wire and told the author to move a
    `via` — which cannot fix it. An acceptance reader followed that advice
    into a dead end. `docs/schema.md` had always said the right thing in
    prose; this is that sentence with the numbers in it.
    """

    @staticmethod
    def ladder(spacing):
        b = DiagramBuilder(R="K/W", T="°C")
        for i in range(4):
            b.node(f"n{i}", f"Stage number {i}", f"{120 - 9 * i}",
                   at=(i * spacing, 0), sub=f"{i}")
        for i in range(3):
            b.branch(f"n{i}", f"n{i+1}", "cond", f"Interface {i}", "0.35")
        return b

    @staticmethod
    def crowded(spacing):
        return [f for f in check(TestNodesTooClose.ladder(spacing).build())
                .findings if f.code == "nodes-too-close"]

    def test_a_squeezed_ladder_is_told_what_is_actually_wrong(self):
        found = self.crowded(130)
        assert len(found) == 3, "one per run, and all three are too short"
        assert found[0].severity == "warning"
        assert "node 'n0' and node 'n1' are 130 apart" in found[0].message
        assert "come to 187" in found[0].message

    def test_the_remedy_names_at_and_says_the_symbol_is_not_the_problem(self):
        remedy = self.crowded(130)[0].remedy
        assert "`at`" in remedy and "`via`" not in remedy
        assert "only 84 wide" in remedy, "the box, against 187 of label"

    def test_moving_them_apart_is_the_fix_it_recommends(self):
        assert not codes(check(self.ladder(200)))

    def test_the_arithmetic_alone_would_over_report(self):
        """Which is why the trigger is a push, not the sum.

        Labels stack at different heights, so their spans along the run can
        overlap without the blocks ever touching. At 180 the labels sum to
        187 against a span of 180 and the drawing is completely clean; a
        check that fired on the sum would condemn it.
        """
        assert "nodes-too-close" not in codes(check(self.ladder(180)))

    def test_a_push_from_something_else_is_not_called_a_spacing_problem(self):
        """A waypoint rising out of a node crowds the label just as badly,
        and moving the nodes apart would not help. The sum has to exceed the
        span as well, and here it does not."""
        report = check(TestLabelAdrift.boxed_in())
        assert "label-adrift" in codes(report)
        assert "nodes-too-close" not in codes(report)

    def test_a_routed_branch_is_measured_against_its_route_not_the_line(self):
        """With waypoints there is more room along the path than the straight
        line between the nodes, so the sum would be checked against the wrong
        number. Straight runs only."""
        b = self.ladder(130)
        b.diagram.branches[0].via = [(40, -120), (90, -120)]
        assert "nodes-too-close" not in [
            f.code for f in check(b).findings if f.where == "branch 0 n0->n1"]


class TestNetworkInPieces:
    """A drawing can be severed in half and pass everything else.

    Two of the first gallery run's diagrams were: a two-phase loop whose halves are
    joined only by a `flow` annotation at each end, and a stack whose Peltier
    stage is drawn the same way. Nothing in either file relates the two
    arrows except that the same number was typed twice.
    """

    @staticmethod
    def two_halves(join=None):
        b = (DiagramBuilder(R="K/W", T="C", q="W")
             .node("hot", "Hot", "70", at=(0, 0))
             .node("warm", "Warm", "50", at=(300, 0))
             .node("mid", "Middle", "40", at=(600, 0))
             .node("cool", "Cool", "30", at=(1000, 0))
             .node("cold", "Cold", "20", at=(1300, 0))
             .branch("hot", "warm", "cond", "Stack", "0.4")
             .branch("warm", "mid", "cond", "Plate", "0.3")
             .branch("cool", "cold", "conv", "Air", "0.9"))
        if join:
            b.branch("mid", "cool", join, "Carried", "0.2")
        return b

    def test_two_halves_joined_by_nothing_are_reported(self):
        found = one(check(self.two_halves()), "network-in-pieces")
        assert found.severity == "warning"
        assert "nothing joins 'cold', 'cool'" in found.message
        assert found.where == "node 'cold'", "the orphan, not the main body"

    def test_the_remedy_names_why_a_source_cannot_join_them(self):
        """Which is the actual gap those two diagrams ran into."""
        found = one(check(self.two_halves()), "network-in-pieces")
        assert "a source has one end" in found.remedy

    def test_a_branch_between_them_clears_it(self):
        assert "network-in-pieces" not in codes(check(self.two_halves("cond")))

    def test_a_break_branch_also_clears_it(self):
        """It carries no heat, and it is still an explicit statement about
        this pair. Excluding it would warn about every standoff ever drawn,
        which is a rule an author learns to ignore."""
        b = (DiagramBuilder(T="C")
             .node("cell", "Cell", "44", at=(0, 0))
             .node("case", "Case", "30", at=(340, 0))
             .branch("cell", "case", "break", "Nylon standoff"))
        assert "network-in-pieces" not in codes(check(b))

    def test_the_hero_is_not_condemned_by_its_own_wire_graph(self):
        """The obvious formulation is barred. The hero's wire graph is in two
        pieces — a source's lead and a node's boundary stub are legitimately
        separate ink — so this has to be a question about nodes and branches.
        """
        d = Diagram.from_json(HERO.read_text(encoding="utf-8"))
        placements = layout(d)
        edges = wire_graph(placements)
        adj = {}
        for a, b in edges:
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        seen, parts = set(), 0
        for v in adj:
            if v in seen:
                continue
            stack, group = [v], set()
            while stack:
                u = stack.pop()
                if u in group:
                    continue
                group.add(u)
                stack += [w for w in adj[u] if w not in group]
            seen |= group
            parts += 1
        assert parts == 2, "the premise of this test"
        assert "network-in-pieces" not in codes(check(d))

    @pytest.mark.parametrize("weird", ["a->b", "hot side", "o'clock"])
    def test_a_node_id_is_data_not_a_string_to_parse(self, weird):
        """A node called `a->b` used to sever its own branches: this finding
        and `describe` both recovered the endpoints by splitting the ref
        string, and reported a connected diagram as two pieces with the
        confidence of a tool that had checked. The placement now carries its
        ends as data, and one builder serves both."""
        from thermodraw import describe
        b = (DiagramBuilder(R="K/W", T="C")
             .node(weird, "Left", "20", at=(0, 0))
             .node("c", "Right", "80", at=(300, 0))
             .branch(weird, "c", "cond", "Path", "0.35"))
        assert "network-in-pieces" not in codes(check(b))
        d = describe(b)
        assert d.edges == [(weird, "c", "cond")]
        assert d.pieces == [sorted([weird, "c"])]


class TestLabelCollision:
    """The push loop can give up, and always could, without saying so.

    `core.annotate` walks out in forty steps of four and then places the block
    wherever it got to, overlap and all. Nothing in the output distinguishes
    that from a deliberate placement, which is what `report["clear"]` is for.
    """

    @staticmethod
    def trapped():
        """A serpentine wire filling the whole 160 units the loop can walk."""
        via = []
        for i in range(34):
            y = -8 - i * 8
            via += [(-260, y), (260, y)] if i % 2 == 0 else [(260, y), (-260, y)]
        return (DiagramBuilder(R="K/W", T="°C")
                .node("h", "Trapped", "150", at=(0, 0), side="up")
                .node("c", "Far", "20", at=(900, 0))
                .branch("h", "c", "cond", "Serpentine", "0.3",
                        via=via, at=(700, 0)))

    def test_the_solver_giving_up_is_reported(self):
        found = one(check(self.trapped()), "label-collision")
        assert found.severity == "error"
        assert found.where == "node 'h'"
        assert "branch 0 h->c" in found.message

    def test_and_the_scene_admits_it(self):
        rect = [r for r in compose(layout(self.trapped().build())).rects
                if r.ref == "node 'h'"][0]
        assert rect.clear is False
        assert rect.used - rect.solved == 160.0, "40 steps of 4"

    def test_a_label_with_room_is_marked_clear(self):
        for rect in compose(layout(parallel_pair(80).build())).rects:
            assert rect.clear is True

    def test_a_label_with_room_is_not_reported(self):
        """The negative this class lacked: `check` itself, not the scene."""
        assert "label-collision" not in codes(check(parallel_pair(80)))

    def test_two_labels_on_each_other_are_one_finding_naming_the_pair(self):
        """Two nodes at one spot, both trapped: each label is printed over
        the other, and each finds the other. Reported once, as a pair, with
        the remedy that fits a pair — the branch of `_collisions` no test
        had reached."""
        via = []
        for i in range(34):
            y = -8 - i * 8
            via += [(-260, y), (260, y)] if i % 2 == 0 else [(260, y), (-260, y)]
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("h", "Trapped", "150", at=(0, 0), side="up")
             .node("g", "Also trapped", "140", at=(0, 0), side="up")
             .node("c", "Far", "20", at=(900, 0))
             .branch("h", "c", "cond", "Serpentine", "0.3",
                     via=via, at=(700, 0)))
        found = one(check(b), "label-collision")
        assert "the label on node" in found.message
        assert "set `side` on one of the two" in found.remedy


class TestParallelPairSameSide:
    """A note, because the hero fires it and is fine. What was missing was
    the negative: proof that putting the labels on opposite sides — which is
    what the remedy says to do — actually clears it."""

    def test_labels_on_opposite_sides_are_not_reported(self):
        assert "parallel-pair-same-side" not in \
            codes(check(parallel_pair(80, "down")))

    def test_and_on_the_same_side_they_are(self):
        assert "parallel-pair-same-side" in codes(check(parallel_pair(80)))


# --------------------------------------------- defect 2: a label in a corridor
def parallel_pair(dy, side="auto"):
    """Two paths between the same nodes, `2 * dy` apart."""
    b = DiagramBuilder(R="K/W", T="°C")
    b.node("h", "Hot", "150", at=(200, 150))
    b.node("c", "Cold", "25", kind="fixed", at=(560, 150))
    b.branch("h", "c", "conv", "Convection", "0.013", side="up",
             via=[(290, 150), (290, 150 - dy), (470, 150 - dy), (470, 150)],
             at=(380, 150 - dy))
    b.branch("h", "c", "rad", "Radiation", "0.015", side=side,
             via=[(290, 150), (290, 150 + dy), (470, 150 + dy), (470, 150)],
             at=(380, 150 + dy))
    return b


class TestLabelInACorridor:
    """Nothing overprints, and a reader still cannot tell whose label it is."""

    def test_a_tight_pair_traps_the_lower_label(self):
        found = one(check(parallel_pair(40)), "label-in-a-corridor")
        assert found.where == "branch 1 h->c"
        assert "`side`" in found.remedy

    def test_side_down_is_the_fix_it_recommends(self):
        assert "label-in-a-corridor" not in codes(check(parallel_pair(40, "down")))

    def test_the_known_limit_is_pinned_rather_than_papered_over(self):
        """A loose pair is not caught, and this records that on purpose.

        Every formulation that flagged a pair 160 apart also flagged the hero's
        own capacitance label, which is fine where it is.
        `parallel-pair-same-side` is the threshold-free companion that catches
        this case, and it is a note.
        """
        report = check(parallel_pair(80))
        assert codes(report) == ["parallel-pair-same-side"]
        assert report.ok


# ------------------------------------------------------- defect 3: the frame
class TestFrame:
    def test_an_oversized_canvas_reads_as_off_centre(self):
        report = check(parallel_pair(80), size=(1400, 900))
        assert "frame-off-centre" in codes(report)
        assert not report.ok

    def test_an_undersized_canvas_clips_and_says_so(self):
        found = one(check(parallel_pair(80), size=(300, 200)), "off-canvas")
        assert "right" in found.message and "bottom" in found.message

    def test_the_measured_canvas_is_never_off_centre(self):
        """Which is the whole reason `size` is optional."""
        assert not [f for f in check(parallel_pair(80)).findings
                    if f.code in ("frame-off-centre", "off-canvas")]


# ------------------------------------------- symbols and wires on top of each other
class TestGeometryCollisions:
    def test_two_symbols_on_one_spot(self):
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
             .branch("a", "b", "cond", "One", "0.3", at=(200, 0))
             .branch("a", "b", "conv", "Two", "0.4", at=(210, 0)))
        found = one(check(b), "symbols-overlap")
        assert found.severity == "error"
        assert "overlap by 32" in found.message

    def test_a_wire_crossing_a_symbol_it_does_not_own(self):
        """One branch trespassing on another, which is one thing to fix."""
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
             .node("d", "D", "70", at=(200, -160))
             .branch("a", "b", "cond", "Across", "0.3", at=(200, 0))
             .branch("d", "b", "conv", "Down past it", "0.4",
                     via=[(200, 0)], at=(200, -80)))
        found = one(check(b), "wire-through-symbol")
        assert found.where == "branch 0 a->b"
        assert "branch 1 d->b runs straight through" in found.message

    def test_two_branches_laid_across_each_other_are_one_finding(self):
        """Both directions are true — each one's wire really is inside the
        other's box — and they are one place on the page, cleared by moving
        either. It used to be reported twice, once from each end.
        """
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
             .node("d", "D", "70", at=(200, -160))
             .branch("a", "b", "cond", "Across", "0.3", at=(200, 0))
             .branch("d", "b", "conv", "Down", "0.4",
                     via=[(200, 0)], at=(300, 0)))
        found = one(check(b), "wire-through-symbol")
        assert found.where == "branch 0 a->b"
        assert "cross each other" in found.message
        assert "clears both" in found.remedy

    def test_a_route_crossing_with_two_segments_is_one_finding(self):
        """Reported per offender, not per segment: one problem, one line."""
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
             .node("d", "D", "70", at=(120, -160))
             .branch("a", "b", "cond", "Across", "0.3", at=(200, 0))
             .branch("d", "b", "conv", "Through", "0.4",
                     via=[(120, 0), (280, 0)], at=(340, 0)))
        hits = [f for f in check(b).findings
                if f.code == "wire-through-symbol" and f.where == "branch 0 a->b"]
        assert len(hits) == 1

    def test_a_plain_ladder_has_neither(self):
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(300, 0))
             .node("c", "C", "20", at=(600, 0))
             .branch("a", "b", "cond", "One", "0.3")
             .branch("b", "c", "conv", "Two", "0.4"))
        assert not [f for f in check(b).findings
                    if f.code in ("symbols-overlap", "wire-through-symbol")]


# ------------------------------------------------------ defect 4: the break node
class TestBreakNode:
    """`g_break` was unreachable from data: a break laid out as a bare circle.

    CLAUDE.md calls the gap "topological rather than decorative", and it was
    rendering as nothing at all — the same output as a free node.
    """

    @staticmethod
    def one_node(kind):
        b = DiagramBuilder(T="°C").node("a", "A", "20", at=(0, 0), kind=kind)
        return layout(b.build())

    def test_a_break_draws_a_wall(self):
        assert [p.element for p in self.one_node("break")] == ["node", "ground"]

    def test_and_no_stub_reaching_it(self):
        assert not [p for p in self.one_node("break") if p.element == "wire"]

    def test_a_fixed_node_reaches_its_wall_and_a_break_does_not(self):
        fixed = [p.element for p in self.one_node("fixed")]
        assert fixed == ["node", "wire", "ground"]
        assert fixed != [p.element for p in self.one_node("break")]

    def test_a_break_no_longer_renders_the_same_as_a_free_node(self):
        from thermodraw import render
        assert render(self.one_node("break")) != render(self.one_node("free"))

    def test_the_wall_is_g_breaks_own_size(self):
        """Not render.ground's. The two symbols are drawn at different scales."""
        wall = [p for p in self.one_node("break") if p.element == "ground"][0]
        assert wall.wall == (22, 13)

    def test_the_glyph_draws_what_the_pipeline_draws(self):
        """The symbol sheet is the visual specification, and it was lying.

        `g_break` showed a crossbar and a wall standing *across* the branch,
        with no node circle at all. The pipeline draws circle, gap, wall
        below. Neither `g_break` nor `g_fixed_node` is reachable from
        `layout` — `render.place` runs only for `element == "symbol"` — so
        the two arrangements drifted apart with nothing to say so. This is
        the thing that says so.
        """
        import xml.etree.ElementTree as ET

        from thermodraw._layout import BREAK_GAP, BREAK_WALL, BY_KEY

        glyph = ET.fromstring("<svg>" + BY_KEY["break"].draw(0) + "</svg>")
        half, depth = BREAK_WALL

        # a node circle at the origin, where the pipeline places its node
        assert [(c.get("cx"), c.get("cy"), c.get("r"))
                for c in glyph.iter("circle")] == [("0", "0", "5.5")]

        # the wall, at the pipeline's gap below it and at the pipeline's size
        wall = glyph.find("g")
        assert wall.get("transform") == f"translate(0,{BREAK_GAP}) rotate(90)"
        assert wall[0].get("y2") == str(half)
        assert float(next(glyph.iter("rect")).get("width")) == depth

        # and no stub: the one line outside the wall is the lead coming in
        # flat, never a segment dropping towards the boundary
        assert [(l.get("y1"), l.get("y2")) for l in glyph.findall("line")] \
            == [("0", "0")]


class TestASourceGivenNoPlace:
    """`layout` put every source at `half_len + 5.5` from its node.

    That considers how long the symbol is and never how tall, which suits the
    three arrow kinds and does not suit `flux`, a 52 x 48 block. At that
    offset the flux body blocked the node's label from below while the
    source's own label blocked it from above, so both candidate sides were
    gone and `annotate` pushed instead of flipping.
    """

    @staticmethod
    def one(kind, label="Switching loss"):
        return (DiagramBuilder(T="°C", P="W", q="W", **{"q″": "W/cm²"})
                .node("a", "Junction", "110", at=(0, 0))
                .source("a", kind, label, "45").build())

    @pytest.mark.parametrize("kind", ["diss", "radin", "flow", "flux"])
    @pytest.mark.parametrize("label", ["Q", "Switching loss",
                                       "Total switching and conduction loss"])
    def test_every_kind_checks_clean_where_layout_puts_it(self, kind, label):
        report = check(self.one(kind, label))
        assert report.ok, f"{kind}: {codes(report)}"

    def test_the_tight_offset_is_what_it_was_fixing(self):
        """The old rule, applied by hand, still fails — so this is the fix."""
        d = (DiagramBuilder(T="°C", **{"q″": "W/cm²"})
             .node("a", "Junction", "110", at=(0, 0))
             .source("a", "flux", "Die surface", "1.4",
                     at=(-(26 + 5.5), 0)).build())
        assert "label-adrift" in codes(check(d))

    def test_the_arrow_kinds_did_not_move(self):
        """Nothing that was already right is disturbed to fix `flux`."""
        from thermodraw._layout import BY_KEY, _source_offset
        for kind in ("diss", "flow"):
            sym = BY_KEY[kind]
            assert _source_offset(sym) == sym.half_len + 5.5


class TestASourceWireMeetsItsNode:
    """The wire stops on the circle, on the line it is travelling along.

    It is trimmed by 5.5, the node's radius, so that it ends on the circle
    rather than under it. That 5.5 used to be measured along the source's
    `angle`, which is the direction the wire runs only while the source
    stands on its node's axis. A source dragged off that axis in the editor
    keeps its `angle`, and the trim then went sideways: an arrow at angle 270
    placed to the left of its node ended 5.5 straight *down* from the centre,
    off its own line and on top of a fixed node's stub. `.node-open` is
    filled, so what the reader saw was a wire stopping short of the node it
    joins.
    """

    @staticmethod
    def wire(**kw):
        d = (DiagramBuilder(T="°C", P="W")
             .node("a", "Steel Out", "1250", kind="fixed", at=(400, 240))
             .source("a", "diss", "P", "45", **kw).build())
        hits = [p for p in layout(d)
                if p.element == "wire" and p.role == "source"]
        assert len(hits) == 1, "the source draws one wire"
        return hits[0].points

    @staticmethod
    def gap(point, node=(400, 240)):
        return math.dist(point, node)

    @pytest.mark.parametrize("at,angle", [((70, 310), 270), ((70, 310), 90),
                                          ((700, 40), 180), ((240, 500), 0)])
    def test_the_far_end_lands_on_the_circle(self, at, angle):
        end, edge = self.wire(at=at, angle=angle)
        assert self.gap(edge) == pytest.approx(5.5), "on the circle"
        # and on the wire's own line, which is what `angle` could not say
        assert math.dist(end, edge) + 5.5 == pytest.approx(self.gap(end))

    def test_it_stops_short_rather_than_crossing_the_node(self):
        """The old rule put the endpoint past the centre for this one."""
        end, edge = self.wire(at=(70, 310), angle=270)
        assert self.gap(edge) < self.gap(end), "not out the far side"
        assert edge[0] < 400 and edge[1] < 310, "on the arrow's side"

    @pytest.mark.parametrize("at,angle,want", [
        ((400, 100), 90, (400, 234.5)), ((400, 400), 270, (400, 245.5)),
        ((100, 240), 0, (394.5, 240)), ((700, 240), 180, (405.5, 240))])
    def test_a_source_on_its_axis_did_not_move(self, at, angle, want):
        """Nothing already right is disturbed: `angle` and the line agree.

        Which is why no golden moved. The two rules differ only where the
        author — or a drag — put the symbol somewhere `angle` does not point.
        """
        assert self.wire(at=at, angle=angle)[1] == pytest.approx(want)

    def test_a_source_left_where_layout_puts_it_still_draws_no_wire(self):
        """An arrow's tail already touches the circle; a gap of 0 is no wire.

        `_source_offset` is `half_len + 5.5` for the arrows, so `end` lands
        exactly on the circle and there is nothing between it and `edge`.
        """
        d = (DiagramBuilder(T="°C", P="W")
             .node("a", "Junction", "110", at=(0, 0))
             .source("a", "diss", "Switching loss", "45").build())
        assert not [p for p in layout(d)
                    if p.element == "wire" and p.role == "source"]


class TestTheRemedyNamesTheField:
    """A finding that lists every field leaves the author to guess.

    Both label findings carried one fixed string offering `side`, `angle` and
    `via` whatever was in the way. For a source crowding its node the answer
    is `at`, and it was not in the list at all.
    """

    @staticmethod
    def remedy(diagram, code="label-adrift"):
        return one(check(diagram), code).remedy

    def test_a_wire_culprit_names_via(self):
        text = self.remedy(TestLabelAdrift.boxed_in())
        assert "`via`" in text and "`at`" not in text

    def test_a_source_culprit_names_at_and_says_which_way(self):
        d = (DiagramBuilder(T="°C", **{"q″": "W/cm²"})
             .node("a", "Junction", "110", at=(0, 0))
             .source("a", "flux", "Die surface", "1.4",
                     at=(-(26 + 5.5), 0)).build())
        text = self.remedy(d)
        assert "move source 0 -> a further from its node with `at`" in text

    def test_a_branch_symbol_culprit_names_at_too(self):
        d = (DiagramBuilder(T="°C", R="K/W")
             .node("a", "A very long label here", "110", at=(0, 0))
             .node("b", "Another long label", "60", at=(120, 0))
             .node("c", "C", "40", at=(0, -200))
             .branch("a", "b", "cond", "L", "0.4")
             .branch("a", "c", "cond", "M", "0.4").build())
        texts = [f.remedy for f in check(d).findings if f.code == "label-adrift"]
        assert any("along its branch with `at`" in t for t in texts)

    def test_two_labels_are_moved_apart_with_side(self):
        """The pair case, which needs no culprit to be named."""
        from thermodraw._check import _remedy
        assert _remedy(None, pair=True) == "set `side` on one of the two"

    def test_side_is_not_offered_once_the_solver_has_tried_both(self):
        """It is advice already taken, and `angle` is what is left.

        Not keyed on `report["flipped"]`: when the flip fails too, `annotate`
        falls back to the first candidate and leaves that False, so the case
        where this matters most is the one it does not mark.
        """
        b = DiagramBuilder(T="°C", R="K/W").node("a", "Junction", "110",
                                                 at=(0, 0))
        for x, y, n in [(300, 0, "e"), (-300, 0, "w"),
                        (0, 300, "s"), (0, -300, "n")]:
            b.node(n, f"Side {n}", "60", at=(x, y))
            b.branch("a", n, "cond", f"Path {n}", "0.4")
        text = self.remedy(b.build())
        assert "`angle`" in text
        assert "set `side` on this label" not in text

    def test_every_remedy_it_can_write_is_ascii(self):
        """Fixed text goes to a cp1252 console. An em dash is a crash there."""
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        for element in ("wire", "symbol", "ground", "node"):
            for ref, role in (("branch 0 a->b", "branch"),
                              ("source 0 -> a", "source"),
                              ("node 'a'", "node")):
                p = Placement(element, ref=ref, role=role)
                for owner in (None, Placement("node", ref="node 'a'",
                                              role="node"), p):
                    for free in ((), ("up", "left")):
                        assert _remedy(p, owner, free).isascii()
        assert _remedy(None, pair=True).isascii()


class TestTheRemedyDoesNotGiveAdviceThatCannotWork:
    """Five agents applied these literally. Six of eighteen worked.

    Every fault below was in the change that claimed each finding "names the
    schema field that fixes it", and three agents hit them independently.
    """

    def test_a_source_is_never_told_to_move_a_via(self):
        """A source's lead is a wire carrying the source's ref, and a source
        has no `via` at all — the validator refuses the field outright."""
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        text = _remedy(Placement("wire", ref="source 1 -> panel",
                                 role="source", ends=("panel",)))
        assert "`via`" not in text
        assert "move source 1 -> panel with `at`" in text

    def test_a_branch_is_still_told_to_move_a_via(self):
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        assert "`via`" in _remedy(Placement("wire", ref="branch 0 a->b",
                                            role="branch", ends=("a", "b")))

    @pytest.mark.parametrize("ref,role", [("branch 0 a->b", "branch"),
                                          ("source 0 -> a", "source")])
    def test_angle_is_never_offered_for_a_label_that_is_not_a_nodes(
            self, ref, role):
        """The schema gives `angle` three meanings. On a branch it "overrides
        the direction taken from the wire", so following this advice laid a
        conduction box diagonally across its own wire — and the checker then
        passed the result."""
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        owner = Placement("symbol", ref=ref, role=role)
        assert "`angle`" not in _remedy(None, owner, free=())

    def test_angle_is_offered_for_a_node_with_nowhere_left(self):
        """Which is the one element where it means what the remedy says."""
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        text = _remedy(None, Placement("node", ref="node 'a'", role="node"),
                       free=())
        assert "`angle`" in text and "label frame" in text

    def test_only_sides_the_occupancy_says_are_free_are_named(self):
        from thermodraw._check import _remedy
        from thermodraw._layout import Placement
        text = _remedy(None, Placement("node", ref="node 'a'", role="node"),
                       free=("up", "left"))
        assert 'set `side` to "up" or "left"' in text
        assert '"down"' not in text and '"right"' not in text

    def test_a_node_hemmed_in_by_its_own_branches_is_not_sent_into_them(self):
        """The case that turned a warning into an error. A node fanning four
        ways has every side taken, and the checker held the occupancy that
        proved it while recommending two of them."""
        b = DiagramBuilder(R="K/W", T="°C").node("a", "Junction", "110",
                                                 at=(0, 0))
        for x, y, n in [(300, 0, "e"), (-300, 0, "w"),
                        (0, 300, "s"), (0, -300, "n")]:
            b.node(n, f"Side {n}", "60", at=(x, y))
            b.branch("a", n, "cond", f"Path {n}", "0.4")
        for f in check(b).findings:
            if f.where == "node 'a'":
                assert "set `side`" not in f.remedy, f.remedy
                assert "`angle`" in f.remedy


class TestHeatLeavingANode:
    """`from` against `to`, which is the direction the arrow points.

    The acceptance reader was asked for the flux leaving a cell's top face
    and could only draw arrows pointing into it. Every source glyph already
    draws its tail at -half_len and its head at +half_len, so this needed no
    new geometry at all: put the symbol on the near side and join the tail.
    """

    @staticmethod
    def one(end, kind="flux", **kw):
        return Diagram.from_dict({
            "units": {"T": "C", "q″": "W/cm2", "q": "W"},
            "nodes": [{"id": "cell", "label": "Cell", "value": "44",
                       "at": [300, 300]}],
            "sources": [dict({end: "cell", "kind": kind, "label": "Top face",
                              "value": "0.9"}, **kw)]})

    def test_the_symbol_moves_to_the_other_side_of_the_node(self):
        """Same glyph, same rotation. Only which end meets the node."""
        out = [p for p in layout(self.one("from")) if p.symbol is not None][0]
        into = [p for p in layout(self.one("to")) if p.symbol is not None][0]
        assert out.angle == into.angle == 0.0
        assert out.at[0] > 300 > into.at[0], "not on opposite sides"
        assert out.at[0] - 300 == 300 - into.at[0], "not the same distance"

    def test_the_lead_joins_the_tail_rather_than_the_head(self):
        """Which is what makes the arrows leave instead of arrive."""
        placements = layout(self.one("from"))
        symbol = [p for p in placements if p.symbol is not None][0]
        wire = [p for p in placements if p.element == "wire"][0]
        far = max(q[0] for q in wire.points)
        assert far == pytest.approx(symbol.at[0] - symbol.symbol.half_len)
        assert min(q[0] for q in wire.points) == pytest.approx(300 + 5.5)

    def test_flux_stands_its_surface_against_the_node(self):
        """The hatch band is a surface, and it is at the glyph's tail.

        So joining the tail puts the surface on the node with the arrows
        leaving it, which is what "flux off this face" means. The glyph's
        own note has said "several arrows leaving a surface" all along.
        """
        symbol = [p for p in layout(self.one("from"))
                  if p.symbol is not None][0]
        hatch_x = symbol.at[0] - 23          # g_flux draws its band at -23
        assert abs(hatch_x - 300) < abs(symbol.at[0] + 28 - 300), \
            "the arrowheads are nearer the node than the surface"

    @pytest.mark.parametrize("angle", [0, 90, 180, 270])
    def test_it_checks_clean_at_every_quarter_turn(self, angle):
        assert check(self.one("from", angle=angle)).ok

    def test_the_default_place_follows_the_angle(self):
        """It used to go left whatever the angle, so `angle` without an `at`
        put the symbol beside the node and the lead across the page."""
        symbol = [p for p in layout(self.one("from", angle=270))
                  if p.symbol is not None][0]
        assert symbol.at[0] == 300 and symbol.at[1] < 300, "not above it"

    def test_the_ref_says_which_way_it_goes(self):
        assert [p.ref for p in layout(self.one("from")) if p.symbol][0] \
            == "source 0 cell ->"
        assert [p.ref for p in layout(self.one("to")) if p.symbol][0] \
            == "source 0 -> cell"

    @pytest.mark.parametrize("kind", ["diss", "radin"])
    def test_a_kind_that_names_its_own_direction_is_refused(self, kind):
        """And the message says what to reach for instead."""
        with pytest.raises(DiagramError) as exc:
            self.one("from", kind=kind, angle=0).validate()
        assert "cannot be written with `from`" in str(exc.value)
        assert "`flow` or `flux`" in str(exc.value)
        if kind == "radin":
            assert "`rad` branch to a boundary" in str(exc.value)

    def test_both_ends_at_once_is_refused(self):
        with pytest.raises(DiagramError) as exc:
            Diagram.from_dict({
                "nodes": [{"id": "a", "at": [0, 0]}],
                "sources": [{"to": "a", "from": "a", "kind": "flow"}]}
            ).validate()
        assert "not both" in str(exc.value)

    def test_and_so_is_neither(self):
        with pytest.raises(DiagramError) as exc:
            Diagram.from_dict({
                "nodes": [{"id": "a", "at": [0, 0]}],
                "sources": [{"kind": "flow"}]}).validate()
        assert "needs `to`" in str(exc.value)

    def test_it_round_trips_through_json(self):
        d = self.one("from")
        assert d.to_dict()["sources"][0]["from"] == "cell"
        assert "to" not in d.to_dict()["sources"][0]
        assert Diagram.from_json(d.to_json()).to_dict() == d.to_dict()

    def test_the_builder_can_say_it_too(self):
        b = (DiagramBuilder(T="C", q="W")
             .node("cell", "Cell", "44", at=(300, 300))
             .source("cell", "flow", "Conducted away", "38", outward=True))
        assert b.build().sources[0].outward
        assert b.build().to_dict()["sources"][0]["from"] == "cell"


class TestABoundaryNodesOwnLabel:
    """`side: "down"` on a boundary node aims the label at its own wall.

    An acceptance reader called that a trap and avoided it. It is not one:
    a boundary node's `half` is a clearance number, and it already reserves
    the wall's depth. The page now says so, so this pins it.
    """

    @staticmethod
    def diagram(kind, side, wall="down"):
        # The branch arrives from the side opposite the wall, which is the
        # arrangement `wall` exists for.
        far = (600, 0) if wall == "left" else (0, 0)
        return (DiagramBuilder(T="C", R="K/W")
                .node("a", "Hot", "120", at=far)
                .node("b", "Cold", "40", kind=kind, at=(300, 0), side=side,
                      wall=wall)
                .branch("a", "b", "cond", "Slab", "0.35"))

    @classmethod
    def wall_and_label(cls, kind, side, wall="down"):
        placements = layout(cls.diagram(kind, side, wall).build())
        scene = compose(placements)
        rect = [r for r in scene.rects if r.ref == "node 'b'"][0]
        ground = [p for p in placements if p.element == "ground"][0]
        return rect, ground

    # The two kinds differ, and the difference is worth pinning. A `fixed`
    # node's half of 22 already covers a wall that ends at 25, so the label is
    # solved clear of it and never pushed. A `break`'s wall stands further
    # off and ends at 37, so the solver pushes the label the last 8 units.
    #
    # 8 is exactly ADRIFT, and the finding triggers on strictly more, so this
    # sits one hair under the threshold and is reported by nothing. That is
    # the right answer — it is legible, and a rule that fired here would fire
    # on every break node anyone draws — but it is an accident of two
    # constants, so it is written down rather than left to be rediscovered.
    #
    # Turned, the wall keeps those numbers on three sides. Above is the
    # exception: the push loop steps by 4, and a block placed above a box
    # touches it at a floating-point epsilon the one below does not, so the
    # break's label takes one step more, 12, and that one is reported.
    # Sideways the label frame's two clearances swap, which is why a fixed
    # wall to the side clears by 5 and a break's by 1: the along-frame
    # number was 19 and 22 where the across-frame one was 22 and 22.
    @pytest.mark.parametrize("kind,wall,gap,push", [
        ("fixed", "down", 4.0, 0.0), ("break", "down", 0.0, 8.0),
        ("fixed", "up", 4.0, 0.0), ("break", "up", 4.0, 12.0),
        ("fixed", "left", 5.0, 0.0), ("break", "left", 1.0, 8.0),
        ("fixed", "right", 5.0, 0.0), ("break", "right", 1.0, 8.0)])
    def test_the_label_lands_beyond_the_wall_not_on_it(self, kind, wall,
                                                       gap, push):
        from thermodraw._render import bounds
        rect, ground = self.wall_and_label(kind, wall, wall)
        x, y, w, h = rect
        wx0, wy0, wx1, wy1 = bounds(ground)
        between = {"down": y - wy1, "up": wy0 - (y + h),
                   "left": wx0 - (x + w), "right": x - wx1}[wall]
        assert between == pytest.approx(gap, abs=0.2)
        assert rect.clear, "printed over the wall"
        assert rect.used - rect.solved == pytest.approx(push, abs=0.2)

    @pytest.mark.parametrize("kind,wall", [
        (k, w) for k in ("fixed", "break")
        for w in ("down", "up", "left", "right")])
    def test_and_the_checker_agrees(self, kind, wall):
        """Aimed at its own wall, the label is reported by nothing — except a
        break's label aimed above, which is the one case the push loop's
        step size carries past ADRIFT."""
        found = codes(check(self.diagram(kind, wall, wall)))
        if (kind, wall) == ("break", "up"):
            assert found == ["label-adrift"]
        else:
            assert not found

    @pytest.mark.parametrize("kind", ["fixed", "break"])
    def test_an_automatic_label_goes_away_from_an_upward_wall(self, kind):
        """With the wall below, the automatic side is above, away from it.
        With the wall above, away is below; a default that sat beyond the
        hatching would be the aimed-at-the-wall case nobody asked for."""
        from thermodraw import describe
        b = self.diagram(kind, "auto", "up")
        assert not codes(check(b))
        row = [l for l in describe(b).lines if l.ref == "node 'b'"][0]
        assert row.side == "below"

    def test_the_wall_is_a_stub_away_in_the_direction_it_faces(self):
        for wall, step in (("down", (0, 12)), ("up", (0, -12)),
                           ("left", (-12, 0)), ("right", (12, 0))):
            _, ground = self.wall_and_label("fixed", "auto", wall)
            assert ground.at == (300 + step[0], 0 + step[1]), wall


class TestRepeatedBranches:
    """`count` draws the repetition, and condenses it above three.

    Each form is a complete, independently centred drawing of the group, so
    the condensed one is genuinely smaller rather than the full one with
    holes in it. The canvas is still sized to the larger of the two, which is
    what keeps the motion isolated: expanding a group moves that group and
    nothing else on the page.
    """

    @staticmethod
    def group(n, arrangement="parallel", span=720):
        return (DiagramBuilder(R="K/W", T="C")
                .node("a", "Junction", "72", at=(0, 0))
                .node("b", "Spreader", "61", at=(span, 0))
                .branch("a", "b", "cond", "Die attach", "0.0275",
                        count=n, arrangement=arrangement).build())

    @pytest.mark.parametrize("n", [2, 3, 4, 8, 16])
    def test_every_copy_is_drawn_in_the_full_form(self, n):
        syms = [p for p in layout(self.group(n))
                if p.symbol is not None and p.variant in (None, "full")]
        assert len(syms) == n
        assert len({p.copy for p in syms}) == n, "copies are not distinguished"

    @pytest.mark.parametrize("n", [4, 8, 16])
    def test_the_condensed_form_draws_two(self, n):
        syms = [p for p in layout(self.group(n))
                if p.symbol is not None and p.variant == "condensed"]
        assert len(syms) == 2

    @pytest.mark.parametrize("n,condensed", [(2, False), (3, False),
                                             (4, True), (16, True)])
    def test_above_three_condenses(self, n, condensed):
        placements = layout(self.group(n))
        marks = [p for p in placements if p.element == "ellipsis"]
        assert bool(marks) is condensed
        hidden = [p for p in placements if not p.shown]
        assert bool(hidden) is condensed

    def test_the_condensed_form_is_smaller(self):
        """The point of condensing: sixteen shown as two should take the room
        of two, not of sixteen."""
        from thermodraw._render import bounds

        def height(variant):
            box = [bounds(p) for p in layout(self.group(16))
                   if p.element == "symbol" and p.variant == variant]
            return max(b[3] for b in box) - min(b[1] for b in box)

        assert height("condensed") < height("full") / 4

    def test_the_canvas_still_fits_the_larger_form(self):
        """Which is what keeps the motion local. Expanding a group must not
        reflow everything else on the page, so the room is already there.

        This used to `continue` past every `anchor`, which is the placement
        that carries a group's label -- so it asserted the room was there for
        the copies while the expanded form's text sat above the canvas top,
        clipped by the root `<svg>` the moment a reader expanded it.
        """
        from thermodraw._render import bounds
        placements = layout(self.group(16))
        box = compose(placements).box
        for p in placements:
            x0, y0, x1, y1 = bounds(p)
            assert box[1] <= y0 and y1 <= box[3], f"{p.ref} {p.variant}"

    def test_every_line_of_both_labels_is_inside_the_canvas(self):
        """The bug the test above could not reach, measured where a reader
        meets it: on the page, after the group transform."""
        import re
        from thermodraw import render
        svg = render(layout(self.group(16)))
        vb = [float(v) for v in
              re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
        tx, ty = (float(v) for v in
                  re.search(r"translate\(([-\d.]+),([-\d.]+)\)", svg).groups())
        ys = [float(y) + ty
              for y in re.findall(r'<text[^>]*y="([-\d.]+)"', svg)]
        assert ys, "the drawing has text"
        assert min(ys) >= vb[1] and max(ys) <= vb[1] + vb[3], (
            "text outside the canvas: "
            f"{[y for y in ys if y < vb[1] or y > vb[1] + vb[3]]}")

    def test_the_hidden_label_takes_no_room_from_a_visible_one(self):
        """It is solved against the page so it does not overprint, and it
        does not claim a place on it, because a reader cannot see it."""
        scene = compose(layout(self.group(16)))
        owners = [box[3] for box in scene.occupancy.boxes]
        assert all(o is None or o.shown for o in owners),             "an invisible label would push a visible one"

    def test_each_form_carries_its_own_label(self):
        """Solved against its own extent, so a condensed group's text sits
        against the two copies it shows and not the sixteen it does not."""
        from thermodraw import render
        assert render(layout(self.group(16))).count("Die attach") == 2

    def test_both_forms_ship_with_stable_ids(self):
        from thermodraw import render
        from thermodraw._render import variant_id
        svg = render(layout(self.group(16)))
        full = variant_id("branch 0 a->b", "full")
        assert f'<g id="{full}" class="td-form" display="none">' in svg
        assert f'<g id="{variant_id("branch 0 a->b", "condensed")}"'                ' class="td-form">' in svg

    def test_an_id_does_not_move_when_the_diagram_does(self):
        """A page holds these ids in its markup, so they must survive
        anything unrelated changing around the group. That is what
        content-addressing the ref buys — and what comparing a pure function
        with itself, as this test once did, could not show."""
        from thermodraw import render
        from thermodraw._render import variant_id
        wanted = f'id="{variant_id("branch 0 a->b", "full")}"'
        assert wanted in render(layout(self.group(16)))
        moved = (DiagramBuilder(R="K/W", T="C")
                 .node("a", "Junction", "72", at=(0, 0))
                 .node("b", "Spreader", "61", at=(720, 0))
                 .node("z", "Elsewhere", "9", at=(2000, 900))
                 .branch("a", "b", "cond", "Die attach", "0.0275",
                         count=16, arrangement="parallel").build())
        assert wanted in render(layout(moved))
        assert variant_id("branch 0 a->b", "full") != \
            variant_id("branch 1 a->b", "full")

    def test_the_hidden_form_is_kept_out_of_the_occupancy(self):
        """The label is solved against what is on show, not against both.
        This used to compute the set of owners and then never look at it,
        so it could not tell exclusion from a label that happened to fit."""
        scene = compose(layout(self.group(16)))
        owners = ([box[3] for box in scene.occupancy.boxes]
                  + [seg[2] for seg in scene.occupancy.segments])
        assert owners, "the occupancy holds the drawing"
        assert all(o is None or o.shown for o in owners), \
            "a hidden-form placement reached the occupancy"
        assert any(o is not None and o.variant == "condensed" for o in owners)
        rect = [r for r in scene.rects if r.ref == "branch 0 a->b"][0]
        assert rect.clear and rect.used == rect.solved

    @pytest.mark.parametrize("n", [2, 3, 4, 8, 16])
    @pytest.mark.parametrize("arrangement", ["parallel", "series"])
    def test_the_default_drawing_checks_clean(self, n, arrangement):
        """A fan radiating straight out of a node crossed its own label, so
        every default-placed group reported `label-adrift`. The trunk either
        side is what fixed it."""
        assert check(self.group(n, arrangement, span=900)).ok

    def test_one_label_speaks_for_the_group(self):
        rects = compose(layout(self.group(8))).rects
        assert len([r for r in rects if r.ref == "branch 0 a->b"]) == 1

    def test_the_label_says_how_many_and_how_they_combine(self):
        from thermodraw._describe import describe
        says = {l.ref: l.says for l in describe(self.group(8)).lines}
        assert "8 in parallel" in says["branch 0 a->b"]
        series = {l.ref: l.says
                  for l in describe(self.group(20, "series")).lines}
        assert "20 in series" in series["branch 0 a->b"]

    def test_a_repeated_branch_cannot_also_be_routed(self):
        with pytest.raises(DiagramError, match="via"):
            (DiagramBuilder(R="K/W", T="C")
             .node("a", "A", "72", at=(0, 0)).node("b", "B", "61", at=(720, 0))
             .branch("a", "b", "cond", "X", "0.3", count=8,
                     arrangement="parallel", via=[(300, 120)]).build())


class TestPhaseNode:
    """A node whose temperature a phase change holds.

    The same trap `g_break` fell into: a node glyph the sheet draws and the
    pipeline does not, drifting apart with nothing to say so. The marking is
    three numbers, and both paths use them.
    """

    @staticmethod
    def one():
        return (DiagramBuilder(T="°C")
                .node("boil", "Boiling surface", "49", kind="phase",
                      sub="sat", at=(0, 0)).build())

    def test_the_pipeline_draws_the_marking(self):
        assert [p.element for p in layout(self.one())] == ["node", "phase"]

    def test_the_glyph_and_the_pipeline_use_the_same_numbers(self):
        from thermodraw import render as _r, symbols as _s
        from thermodraw._render import PHASE_HALF, PHASE_Y1, PHASE_Y2
        assert (PHASE_HALF, PHASE_Y1, PHASE_Y2) ==             (_s.PHASE_HALF, _s.PHASE_Y1, _s.PHASE_Y2)
        glyph = _s.g_phase_node(0)
        for dy in (PHASE_Y1, PHASE_Y2):
            assert f'y1="{dy}" x2="{PHASE_HALF}" y2="{dy}"' in glyph

    def test_it_draws_differently_from_a_free_node(self):
        from thermodraw import render
        free = (DiagramBuilder(T="°C")
                .node("boil", "Boiling surface", "49", sub="sat",
                      at=(0, 0)).build())
        assert render(layout(self.one())) != render(layout(free))

    def test_the_marking_is_registered_against_the_label_solver(self):
        """The wall was invisible to it once, and a label landed on it."""
        scene = compose(layout(self.one()))
        rect = [r for r in scene.rects if r.ref == "node 'boil'"][0]
        assert rect.clear


class TestBreakBranch:
    """A break you can connect something to.

    The node kind leaves a wall floating: an acceptance agent drawing a
    fibreglass standoff got a labelled boundary with nothing tying it to the
    thing it was bolted to, because every branch kind drew a resistance or a
    capacitance. This is the open circuit — wire, crossbar, gap, crossbar,
    wire — which is the one reading a plain wire cannot give, since a wire
    says heat flows.
    """

    @staticmethod
    def standoff(**kw):
        return (DiagramBuilder(T="°C")
                .node("cell", "Cell stack", "85", at=(0, 0))
                .node("case", "Case", "30", at=(340, 0))
                .branch("cell", "case", "break", "Nylon standoff", **kw))

    def test_it_connects_its_two_nodes(self):
        placements = layout(self.standoff().build())
        symbol = [p for p in placements if p.symbol is not None][0]
        assert symbol.symbol.key == "break-branch"
        assert symbol.ref == "branch 0 cell->case"

    def test_the_wire_stops_either_side_of_it(self):
        """The gap is the whole content of the symbol, so it must be real."""
        placements = layout(self.standoff().build())
        runs = [p for p in placements if p.element == "wire"]
        assert len(runs) == 2, "one run each side, not one straight through"
        left = max(q[0] for q in runs[0].points)
        right = min(q[0] for q in runs[1].points)
        assert right - left == pytest.approx(2 * 12)

    def test_it_names_no_quantity(self):
        """No R and no C: a break has neither, so there is no second line."""
        symbol = [p for p in layout(self.standoff().build())
                  if p.symbol is not None][0]
        assert symbol.label.user == "Nylon standoff"
        assert symbol.label.name is None and symbol.label.value is None

    def test_a_value_on_one_is_refused_and_says_why(self):
        with pytest.raises(DiagramError) as exc:
            self.standoff(value="0.4").build().validate()
        assert "carries no heat" in str(exc.value)

    def test_and_the_drawing_passes_its_own_checker(self):
        assert check(self.standoff().build()).ok

    def test_the_node_kind_and_the_branch_kind_are_different_symbols(self):
        """One namespace, two positions. The collision is the hazard."""
        from thermodraw._layout import BRANCH_SYM, BY_KEY
        assert BY_KEY["break"] is not BY_KEY[BRANCH_SYM["break"]]


# ---------------------------------------------------------------- quantities
class TestFluxIsItsOwnQuantity:
    """`q` for a power and `q″` for a flux are not the same measurement.

    They shared one units entry, so a diagram carrying both could only give
    one of them a unit — and `docs/symbol-reference.html` had been showing
    `q″` and `W/cm²` for years, which the pipeline could not produce.
    """

    @staticmethod
    def both():
        return (DiagramBuilder(T="°C", P="W", q="W", **{"q″": "W/cm²"})
                .node("a", "Die", "110", at=(0, 0))
                .source("a", "flow", "Conducted away", "38", at=(-160, -70))
                .source("a", "flux", "Surface", "1.4", at=(-160, 70)))

    def test_they_carry_different_units(self):
        d = self.both().build()
        assert d.value_text("flow", "38") == "38 W"
        assert d.value_text("flux", "1.4") == "1.4 W/cm²"

    def test_the_symbol_matches_the_quantity(self):
        from thermodraw import model as M
        assert M.SOURCE_SYMBOL["flux"] == M.QUANTITY["flux"] == "q″"
        assert M.SOURCE_SYMBOL["flow"] == M.SOURCE_SYMBOL["radin"] == "q"

    def test_the_accepted_units_keys_follow_the_table(self):
        """`known` is derived, so nothing had to be edited twice."""
        with pytest.raises(DiagramError) as exc:
            Diagram(units={"nonsense": "W"}).validate()
        assert "q″" in str(exc.value)

    def test_an_unknown_source_kind_with_a_value_says_so(self):
        """It used to reach QUANTITY[kind] and raise a bare KeyError.

        `_valued()` yields sources, and the bare-value check ran before the
        source-kind check. Nodes and branches validate their kinds earlier,
        so sources were the one exposed case.
        """
        d = DiagramBuilder(P="W").node("a", "A", None, at=(0, 0)).build()
        d.sources.append(__import__("thermodraw").model.Source(
            target="a", kind="conduction", value="5"))
        with pytest.raises(DiagramError) as exc:
            d.validate()
        assert "unknown kind 'conduction'" in str(exc.value)


# ------------------------------------------------------------------- the hero
class TestTheHero:
    """The flagship diagram, held to the library's own standard."""

    @staticmethod
    def report():
        return check(Diagram.from_json(HERO.read_text(encoding="utf-8")),
                     source="hero")

    def test_it_passes(self):
        assert self.report().ok

    def test_its_one_note_is_pinned(self):
        """It breaks the parallel-pair habit, which is why that is a note."""
        report = self.report()
        assert codes(report) == ["parallel-pair-same-side"]
        assert report.labels == 11

    def test_the_summary_says_so_out_loud(self):
        text = self.report().text()
        assert text.startswith("hero: 11 labels placed, 0 errors, 0 warnings")
        assert text.isascii(), "the report goes to a cp1252 console"


# -------------------------------------------------------------- the primitives
class TestPrimitives:
    def test_gap_is_signed_and_is_the_sign_of_overlap(self):
        near = core.gap((0, 0), (10, 10), (30, 0), (10, 10), 0)
        assert near == pytest.approx(10.0)
        assert core.gap((0, 0), (10, 10), (15, 0), (10, 10), 0) == \
            pytest.approx(-5.0)
        for dx in range(0, 40, 3):
            a = core.gap((0, 0), (10, 5), (dx, 2), (8, 4), 30)
            assert (a < 0) == core._overlap((0, 0), (10, 5), (dx, 2), (8, 4), 30)

    def test_box_bounds_with_and_without_an_offset(self):
        assert core.box_bounds((0, 0), (10, 4)) == (-10, -4, 10, 4)
        # a quarter turn swaps the extents
        x0, y0, x1, y1 = core.box_bounds((0, 0), (10, 4), 90)
        assert (round(x1), round(y1)) == (4, 10)
        # offset hangs the box off its anchor rather than straddling it
        assert core.box_bounds((0, 0), (5, 20), 0, offset=(5, 0)) == \
            (0, -20, 10, 20)

    def test_segment_box_respects_the_angle(self):
        centre, half = (0.0, 0.0), (40.0, 5.0)
        assert core.segment_box((0, -30), (0, 30), centre, half, 0)
        assert not core.segment_box((20, -30), (20, 30), centre, half, 90)
        assert core.segment_box((20, -30), (20, 30), centre, half, 0)

    def test_blocker_and_free_agree(self):
        occ = core.Occupancy()
        marker = object()
        occ.add_box((0, 0), (10, 10), 0.0, owner=marker)
        occ.add_segment((100, -50), (100, 50))
        assert occ.blocker((5, 0), (2, 2)).owner is marker
        assert occ.free((5, 0), (2, 2), owner=marker)
        assert occ.blocker((100, 0), (2, 2)).kind == "segment"
        assert occ.free((300, 300), (2, 2))
        assert occ.blocker((300, 300), (2, 2)) is None

    def test_label_rect_still_unpacks_as_four(self):
        rect = LabelRect((1.0, 2.0, 3.0, 4.0), owner=None,
                         report={"used": 9.0, "clear": False})
        left, top, bw, bh = rect
        assert (left, top, bw, bh) == (1.0, 2.0, 3.0, 4.0)
        assert rect == (1.0, 2.0, 3.0, 4.0)          # and compares equal
        assert rect.used == 9.0 and rect.clear is False

    def test_annotate_reports_what_it_did(self):
        out, report = [], {}
        core.annotate(0, 0, 0, out, user="Label", name="R", value="1 K/W",
                      half=16, half_len=42, report=report)
        assert set(report) == {"side", "solved", "used", "clear", "flipped"}
        assert report["used"] == report["solved"] and report["clear"]

    def test_a_concave_ring_is_tested_correctly(self):
        ring = [(0, 0), (100, 0), (100, 100), (60, 100),
                (60, 40), (40, 40), (40, 100), (0, 100)]
        assert _inside((20, 20), ring)               # in the base
        assert not _inside((50, 80), ring)           # up the notch
        assert _inside((80, 80), ring)               # in the right arm

    def test_two_rotated_boxes_separate_on_their_own_axes(self):
        """A test `core.gap` alone cannot do: neither box is axis-aligned."""
        assert _obb_gap((0, 0), (40, 5), 45, (100, 100), (40, 5), 45) > 0
        assert _obb_gap((0, 0), (40, 5), 45, (10, 10), (40, 5), 45) < 0

    def test_segment_to_rectangle_distance(self):
        assert _segment_rect_gap((0, 50), (100, 50), (50, 0), (10, 10)) == \
            pytest.approx(40.0)
        assert _segment_rect_gap((0, 0), (100, 0), (50, 0), (10, 10)) == 0.0


class TestTheWireGraph:
    """The corridor check is only as good as the network it reconstructs."""

    @staticmethod
    def hero_graph():
        placements = layout(Diagram.from_json(
            HERO.read_text(encoding="utf-8")))
        return placements, wire_graph(placements)

    def test_every_symbol_gap_is_bridged(self):
        """`layout._split` puts a hole in every branch; without closing them
        the ladder has almost no cycles at all."""
        placements, edges = self.hero_graph()
        for p in placements:
            if p.symbol is None:
                continue
            r = math.radians(p.angle)
            hl = p.symbol.half_len
            ends = tuple(sorted(
                (round(p.at[0] + s * math.cos(r) * hl, 1),
                 round(p.at[1] + s * math.sin(r) * hl, 1)) for s in (-1, 1)))
            assert ends in edges, f"{p.ref} left a hole in the graph"

    def test_the_ladder_closes_a_loop(self):
        """Proves both the bridging and the T-junction splitting: the
        capacitance drops onto the middle of the rail and shares no vertex
        with it until every edge is split at every vertex lying on it."""
        _, edges = self.hero_graph()
        assert cycles(edges), "the hero's ladder found no loop at all"

    def test_cycle_count_is_the_graph_invariant(self):
        """E - V + C. The hero has two components, not one: a source arrow
        stops short of the node it points at, so its shaft never joins."""
        _, edges = self.hero_graph()
        verts = {v for e in edges for v in e}

        adjacent, seen, components = {v: set() for v in verts}, set(), 0
        for a, b in edges:
            adjacent[a].add(b)
            adjacent[b].add(a)
        for root in verts:
            if root in seen:
                continue
            components += 1
            stack = [root]
            while stack:
                v = stack.pop()
                if v not in seen:
                    seen.add(v)
                    stack += list(adjacent[v])

        assert components == 2
        assert len(cycles(edges)) == len(edges) - len(verts) + components

    def test_a_ring_of_edges_is_one_cycle(self):
        square = {((0, 0), (10, 0)): {"a"}, ((10, 0), (10, 10)): {"a"},
                  ((0, 10), (10, 10)): {"a"}, ((0, 0), (0, 10)): {"a"}}
        rings = cycles(square)
        assert len(rings) == 1 and len(rings[0]) == 4


class TestTheDocumentedAngleTable:
    """`docs/schema.md` states what `angle` does to a node's label.

    It is the field a fan-out node has to reach for when `side` runs out of
    directions, and it was previously documented only as "rotates the node's
    own frame" — from which a reader inferred a plain clockwise rotation and
    was wrong about half the circle. These pin the table on the page.
    """

    @staticmethod
    def side(angle):
        got = core._sides(angle, "auto")[0]
        return round(got[0], 2), round(got[1], 2)

    @pytest.mark.parametrize("angle,expected,words", [
        (0, (0.0, -1.0), "above"),
        (45, (0.71, -0.71), "above and to the right"),
        (90, (1.0, -0.0), "to the right"),
        (135, (-0.71, -0.71), "above and to the left"),
    ])
    def test_the_table(self, angle, expected, words):
        assert self.side(angle) == expected, words

    def test_it_is_symmetric_about_180(self):
        """A label is never set upside down, so the choice repeats."""
        for angle in (0, 45, 90, 135):
            assert self.side(angle) == self.side(angle + 180)

    def test_side_overrides_angle(self):
        assert core._sides(90, "down") == [core.PAGE_SIDES["down"]]

    def test_angle_reaches_a_diagonal_that_side_cannot(self):
        """Which is the whole reason the finding text names it."""
        diagonals = {self.side(a) for a in (45, 135, 225, 315)}
        assert not diagonals & {tuple(v) for v in core.PAGE_SIDES.values()}


class TestTheReport:
    def test_notes_do_not_fail_a_run_but_warnings_do(self):
        assert check(parallel_pair(80)).ok           # note only
        assert not check(parallel_pair(40)).ok       # warning

    def test_worst_names_the_top_severity(self):
        assert check(parallel_pair(80)).worst() == "note"
        assert check(parallel_pair(40)).worst() == "warning"
        assert check(parallel_pair(80), size=(300, 200)).worst() == "error"

    def test_to_dict_round_trips_through_json(self):
        import json
        data = json.loads(json.dumps(check(parallel_pair(40)).to_dict()))
        assert data["ok"] is False
        assert {f["code"] for f in data["findings"]} == set(
            codes(check(parallel_pair(40))))

    def test_the_builder_can_check_itself(self):
        builder = parallel_pair(40)
        assert codes(builder.check()) == codes(check(builder))

    def test_findings_come_out_worst_first(self):
        from thermodraw._check import ORDER
        found = check(parallel_pair(40), size=(300, 200)).findings
        assert [ORDER[f.severity] for f in found] == \
            sorted(ORDER[f.severity] for f in found)


def test_check_takes_a_diagram_a_builder_or_placements():
    builder = parallel_pair(40)
    diagram = builder.build()
    assert codes(check(builder)) == codes(check(diagram)) \
        == codes(check(layout(diagram)))


def test_compose_hands_back_the_occupancy_the_labels_were_solved_against():
    """Not a rebuild of it. A rebuilt page forgets whatever the first forgot."""
    placements = layout(parallel_pair(40).build())
    scene = compose(placements)
    assert scene.occupancy is not None
    assert len(scene.rects) == 4
    for rect in scene.rects:
        assert rect.owner in placements
        assert rect.ref == rect.owner.ref
