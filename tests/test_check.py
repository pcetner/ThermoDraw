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

from thermodraw import Diagram, DiagramBuilder, check, core, layout
from thermodraw.check import (_inside, _obb_gap, _segment_rect_gap, cycles,
                              wire_graph)
from thermodraw.render import LabelRect, compose

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
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
             .node("d", "D", "70", at=(200, -160))
             .branch("a", "b", "cond", "Across", "0.3", at=(200, 0))
             .branch("d", "b", "conv", "Down through it", "0.4",
                     via=[(200, 0)], at=(300, 0)))
        hits = [f for f in check(b).findings if f.code == "wire-through-symbol"]
        assert {f.where for f in hits} == {"branch 0 a->b", "branch 1 d->b"}

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
        from thermodraw.check import ORDER
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
