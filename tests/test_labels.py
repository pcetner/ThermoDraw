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
