"""Diagram-aware label placement.

`clear_offset` solves a label against its own symbol and is good at it. What
it cannot see is every other label and every wire, which is how a dissipation
label came to overprint a conduction one and an ambient label came to sit on
a wire. Both were fixed by hand in the demo, by moving coordinates and
inflating a clearance parameter that means something else.
"""
import pytest

from thermodraw import DiagramBuilder, layout, render
from thermodraw.core import Occupancy, _segment_box
from thermodraw.render import draw


def rects(diagram_builder):
    return draw(layout(diagram_builder.build()))[1]


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw <= bx or bx + bw <= ax
                or ay + ah <= by or by + bh <= ay)


def cramped(spacing):
    """Nodes packed close enough that untreated labels would collide."""
    b = DiagramBuilder(R="K/W", T="°C")
    for i in range(5):
        b.node(f"n{i}", f"Stage number {i}", f"{120 - 9 * i}",
               at=(i * spacing, 0), sub=f"{i}")
    for i in range(4):
        b.branch(f"n{i}", f"n{i+1}", "cond", f"Interface {i}", "0.35")
    return b


# --------------------------------------------------------------- the outcome
@pytest.mark.parametrize("spacing", [150, 180, 220, 300])
def test_labels_do_not_overlap_each_other(spacing):
    placed = rects(cramped(spacing))
    assert len(placed) >= 9
    clashes = [(a, b) for i, a in enumerate(placed)
               for b in placed[i + 1:] if overlap(a, b)]
    assert not clashes, f"{len(clashes)} overlapping labels at {spacing}px"


def test_labels_stay_off_the_wires():
    """The ambient label used to land on the drop wire into the rail."""
    b = (DiagramBuilder(R="K/W", C="J/K", T="°C")
         .node("j", "Junction", "112", at=(0, 0), sub="j")
         .node("amb", "Still air", "40", at=(360, 220), kind="fixed", sub="amb")
         .rail("amb", y=220, span=(0, 360))
         .branch("j", "rail", "cap", "Die", "0.9", sub="j"))
    placements = layout(b.build())
    placed = draw(placements)[1]
    occupied = Occupancy()
    for p in placements:
        if p.element == "wire":
            for i in range(len(p.points) - 1):
                occupied.add_segment(p.points[i], p.points[i + 1])
    for left, top, bw, bh in placed:
        centre = (left + bw / 2, top + bh / 2)
        assert occupied.free(centre, (bw / 2, bh / 2)), \
            f"label at {centre} sits on a wire"


def test_crowding_moves_a_label_rather_than_dropping_it():
    """Every label must still be drawn, however tight the diagram."""
    loose = rects(cramped(300))
    tight = rects(cramped(150))
    assert len(loose) == len(tight)
    moved = sum(1 for a, b in zip(loose, tight) if a[1] != b[1])
    assert moved, "crowding the diagram changed nothing, so nothing was avoided"


# ---------------------------------------------------------------- the levers
def test_side_can_be_overridden():
    from thermodraw import core

    out_up, out_down = [], []
    core.annotate(0, 0, 0, out_up, user="Label", name="R", value="1 K/W",
                  half=16, half_len=42, side="up")
    core.annotate(0, 0, 0, out_down, user="Label", name="R", value="1 K/W",
                  half=16, half_len=42, side="down")
    y_up = float(out_up[0].split('y="')[1].split('"')[0])
    y_down = float(out_down[0].split('y="')[1].split('"')[0])
    assert y_up < 0 < y_down


def test_auto_is_unchanged_when_nothing_is_in_the_way():
    """The tight placement CLAUDE.md prizes must survive the new machinery."""
    from thermodraw import core

    bare, watched = [], []
    core.annotate(0, 0, 0, bare, user="Label", name="R", value="1 K/W",
                  half=16, half_len=42)
    core.annotate(0, 0, 0, watched, user="Label", name="R", value="1 K/W",
                  half=16, half_len=42, occupied=Occupancy())
    assert bare == watched


# ------------------------------------------------------------- the primitive
def test_segment_box_hits_and_misses():
    box, half = (0.0, 0.0), (10.0, 5.0)
    assert _segment_box((-20, 0), (20, 0), box, half)      # straight through
    assert _segment_box((0, -20), (0, 20), box, half)      # and the other way
    assert _segment_box((-20, -20), (20, 20), box, half)   # diagonal
    assert not _segment_box((-20, 20), (20, 20), box, half)   # passes below
    assert not _segment_box((-40, 0), (-20, 0), box, half)    # stops short


# ------------------------------------------------------- the side override
# `core.annotate` has taken an explicit side since the occupancy work, and
# `layout.Label` has carried the field, but the model had nowhere to write it:
# the override existed in Python and was unreachable from a diagram written as
# data. A parallel pair is where it is missed — both branches are horizontal,
# so both labels choose "up", which puts the lower one inside the loop.
def parallel_pair(side_low):
    b = DiagramBuilder(R="K/W", T="°C")
    b.node("h", "Hot", "150", at=(200, 150))
    b.node("c", "Cold", "25", kind="fixed", at=(560, 150))
    b.branch("h", "c", "conv", "Convection", "0.013", side="up",
             via=[(290, 150), (290, 70), (470, 70), (470, 150)], at=(380, 70))
    b.branch("h", "c", "rad", "Radiation", "0.015", side=side_low,
             via=[(290, 150), (290, 230), (470, 230), (470, 150)],
             at=(380, 230))
    return b


def _label_top(builder, needle):
    for placement in layout(builder.build()):
        lab = placement.label
        if lab is not None and lab.user == needle:
            return placement
    raise AssertionError(needle)


def test_side_reaches_the_renderer_from_the_model():
    assert _label_top(parallel_pair("down"), "Radiation").label.side == "down"


def test_side_down_puts_the_label_below_its_box():
    """auto sends both labels up; the override sends the lower one out."""
    box_y = 230
    auto = [r for r in rects(parallel_pair("auto"))]
    forced = [r for r in rects(parallel_pair("down"))]
    # exactly one rectangle moves, and it moves from above the box to below it
    moved = [(a, f) for a, f in zip(auto, forced) if a != f]
    assert len(moved) == 1
    before, after = moved[0]
    assert before[1] + before[3] < box_y < after[1]


def test_a_bad_side_is_named_and_listed():
    from thermodraw import Diagram, DiagramError
    with pytest.raises(DiagramError, match="side must be one of.*'down'"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0],
                                      "side": "downwards"}]})


class TestARateStatesItsQuantity:
    """`rate` shipped drawing a bare number and had no test at all.

    A path carrying 12 W drew `12 W` directly under `R_cond = 0.35 K/W` --
    same style, no symbol, nothing to say which of the two was specified and
    which is what the path turned out to carry. Every other quantity on the
    page is written `symbol = value`, and `model.RATE` already named this one;
    it was only ever used to look the unit up.
    """

    def diagram(self, **kw):
        from thermodraw import Diagram
        from thermodraw.model import Branch, Node
        return Diagram(
            nodes=[Node(id="a", at=[150, 120], value="80", sub="a"),
                   Node(id="b", at=[500, 120], value="40", sub="b")],
            branches=[Branch(source="a", target="b", kind="cond",
                             label="Base plate", value="0.35", **kw)],
            units={"R": "K/W", "T": "\u00b0C", "q": "W"})

    def says(self, **kw):
        from thermodraw.describe import describe, label_text
        d = self.diagram(**kw)
        d.validate()
        describe(d)
        for placement in layout(d):
            if placement.label is not None and placement.label.user:
                return label_text(placement.label)
        raise AssertionError("no labelled placement")

    def test_a_rate_is_drawn_with_its_symbol(self):
        assert self.says(rate="12").endswith("q = 12 W")

    def test_the_rate_is_not_a_bare_number(self):
        """The defect itself, pinned: `12 W` alone is not a statement."""
        parts = self.says(rate="12").split(" | ")
        assert "12 W" not in parts, parts

    def test_the_rate_line_reaches_the_drawing(self):
        svg = render(layout(self.diagram(rate="12")))
        assert ">12 W<" in svg and svg.count(">q<") == 1

    def test_a_path_with_no_rate_gains_no_line(self):
        assert self.says() == "Base plate | R_cond = 0.35 K/W"

    def test_prose_extras_stay_prose(self):
        """`count` names itself, so it is not dressed as a quantity."""
        said = self.says(count=4, arrangement="parallel")
        assert said.endswith("4 in parallel")
        assert "= 4 in parallel" not in said

    def test_a_rate_and_a_count_are_both_kept_and_ordered(self):
        said = self.says(rate="12", count=4, arrangement="parallel")
        assert said.split(" | ")[-2:] == ["q = 12 W", "4 in parallel"]

    def test_the_rate_uses_the_q_unit_whatever_the_path_is(self):
        """A resistance is in K/W and what it carries is in W. That is the
        whole point of the field, and `RATE` is why it does not read
        `units.R`."""
        assert "q = 12 W" in self.says(rate="12")

    def test_one_wrap_rule_serves_both_lines(self):
        """`_stated` is shared, so a long rate wraps the way a long value
        does rather than running off the block."""
        from thermodraw.core import WRAP_AT, _line_w, build_block
        wide = build_block(name="q", value="1234567890 mW", extra=[])
        pair = build_block(extra=[("q", "1234567890 mW")])
        assert [len(l) for l in wide] == [len(l) for l in pair]
        assert all(_line_w(l) <= WRAP_AT for l in pair)
