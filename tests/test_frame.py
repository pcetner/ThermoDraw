"""The drawing sits square in its own canvas.

This is the test the goldens could not be. A golden pins bytes: when the hero
sat 17 units high in its frame, every golden passed, because the frame had
always been wrong and the bytes had never changed. Finding it took rendering
the file, serving it, opening a browser and measuring the white space by eye.

What follows is a property, so it holds for diagrams nobody has drawn yet.
It pins the invariant — the canvas is derived from the ink, on all four sides
— and not the ink measurement itself. That is pinned by the numbers on
`Symbol.reach` and `render.WALL_HALF/WALL_DEPTH`, and the case that motivated
them is the last test here.
"""
import math
import re
import xml.etree.ElementTree as ET

import pytest

from thermodraw import Diagram, DiagramBuilder, layout, render, symbols
# by name: the package rebinds `thermodraw.render` to the render function
from thermodraw.render import (PADDING, WALL_DEPTH, WALL_HALF, bounds,
                               compose)

from test_check import HERO, parallel_pair


def ladder(kind="cond", n=4, spacing=220):
    b = DiagramBuilder(R="K/W", C="J/K", T="°C", P="W")
    for i in range(n):
        b.node(f"n{i}", f"Stage {i}", f"{120 - 9 * i}", at=(i * spacing, 0),
               sub=f"{i}")
    for i in range(n - 1):
        b.branch(f"n{i}", f"n{i+1}", kind, f"Interface {i}", "0.35")
    return b


def hero():
    return layout(Diagram.from_json(HERO.read_text(encoding="utf-8")))


DIAGRAMS = {
    "hero": hero(),
    "ladder": layout(ladder().build()),
    "ladder of radiation": layout(ladder("rad").build()),
    "ladder of capacitance": layout(ladder("cap").build()),
    "parallel pair": layout(parallel_pair(80).build()),
    "diagonal": layout(
        DiagramBuilder(R="K/W", T="°C")
        .node("a", "Hot", "120", at=(0, 0))
        .node("b", "Cold", "20", kind="fixed", at=(300, 300))
        .branch("a", "b", "conv", "Diagonal", "1.2").build()),
    "one fixed node": layout(
        DiagramBuilder(T="°C")
        .node("w", "Ambient", "25", kind="fixed", at=(0, 0)).build()),
    "one break": layout(
        DiagramBuilder(T="°C")
        .node("w", "Standoff", "25", kind="break", at=(0, 0)).build()),
}


@pytest.mark.parametrize("name", sorted(DIAGRAMS))
def test_opposite_margins_agree(name):
    """Every side gets the same padding, so nothing sits off-centre."""
    scene = compose(DIAGRAMS[name])
    ix0, iy0, ix1, iy1 = scene.ink
    bx0, by0, bx1, by1 = scene.box
    assert ix0 - bx0 == pytest.approx(bx1 - ix1, abs=1.0), "left against right"
    assert iy0 - by0 == pytest.approx(by1 - iy1, abs=1.0), "top against bottom"


@pytest.mark.parametrize("name", sorted(DIAGRAMS))
def test_the_margin_is_the_padding_on_all_four_sides(name):
    scene = compose(DIAGRAMS[name])
    ink, box = scene.ink, scene.box
    for i, side in enumerate(("left", "top")):
        assert ink[i] - box[i] == pytest.approx(PADDING, abs=0.01), side
    for i, side in ((2, "right"), (3, "bottom")):
        assert box[i] - ink[i] == pytest.approx(PADDING, abs=0.01), side


@pytest.mark.parametrize("name", sorted(DIAGRAMS))
def test_every_placement_is_inside_the_canvas(name):
    """`extent` aggregates `bounds`, so this catches the two disagreeing."""
    placements = DIAGRAMS[name]
    bx0, by0, bx1, by1 = compose(placements).box
    for p in placements:
        x0, y0, x1, y1 = bounds(p)
        assert bx0 <= x0 and x1 <= bx1, f"{p.ref} runs past the sides"
        assert by0 <= y0 and y1 <= by1, f"{p.ref} runs past the top or bottom"


@pytest.mark.parametrize("name", sorted(DIAGRAMS))
def test_the_canvas_is_the_extent(name):
    """What the SVG declares is what was measured, not a rounding of it."""
    import re

    placements = DIAGRAMS[name]
    bx0, by0, bx1, by1 = compose(placements).box
    svg = render(placements)
    w, h = (float(v) for v in
            re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg).groups())
    assert (w, h) == (round(bx1 - bx0, 1), round(by1 - by0, 1))


def test_a_boundary_wall_reserves_what_it_draws():
    """The 17 units that started this.

    `extent` reserved a flat 30 units in every direction around a ground, for
    a wall that draws 13 deep on one side only and nothing at all on the
    other. Measured against the geometry rather than against `bounds`, so it
    fails if `bounds` learns the same wrong number.
    """
    placements = layout(DiagramBuilder(T="°C")
                        .node("w", "Ambient", "25", kind="fixed",
                              at=(0, 0)).build())
    wall = [p for p in placements if p.element == "ground"][0]
    x0, y0, x1, y1 = bounds(wall)

    # ground() at angle 90 draws its line across the anchor and hatches below.
    assert (x0, x1) == pytest.approx((-WALL_HALF, WALL_HALF))
    assert (y0, y1) == pytest.approx((wall.at[1], wall.at[1] + WALL_DEPTH))
    assert y1 - y0 == pytest.approx(WALL_DEPTH), "the wall is 13 deep"
    assert WALL_DEPTH < 30, "back to reserving a fixed 30 around it"


def test_a_symbol_at_the_end_of_a_run_keeps_its_leads():
    """`half_len` is clearance; a box symbol draws LEAD past it either end.

    Mid-route the leads lie over wire the canvas already counts, so sizing to
    the clearance box looked right everywhere it was tried. At the end of a
    run it silently clips them off.
    """
    from thermodraw import symbols

    cond = [s for s in symbols.SYMBOLS if s.key == "cond"][0]
    assert cond.ink == (cond.half_len + symbols.LEAD, cond.half)

    placements = layout(
        DiagramBuilder(R="K/W", T="°C")
        .node("a", "A", "100", at=(0, 0)).node("b", "B", "50", at=(400, 0))
        # off the end of the wire, where nothing else covers the leads
        .branch("a", "b", "cond", "Overhanging", "0.3", at=(560, 0)).build())
    symbol = [p for p in placements if p.symbol is not None][0]
    box = compose(placements).box
    assert bounds(symbol)[2] == pytest.approx(560 + cond.half_len
                                              + symbols.LEAD)
    assert box[2] >= bounds(symbol)[2] + PADDING


# ------------------------------------------- reach, against the real markup
# `Symbol.reach` is nine hand-read numbers: someone opened each drawing
# function, worked out how far it goes, and typed the answer. Nothing checked
# it, and the failure mode is silent — a symbol at the end of a run loses the
# part that was not declared, and no golden moves, because the canvas was
# derived from the wrong number in the first place.
#
# So this measures the markup instead. The only real difficulty is clipping:
# `core.hatch` emits rules far larger than the area they fill and relies on a
# clip path, so a group carrying one is worth exactly its clip rectangle.
def _nums(text):
    return [float(v) for v in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", text)]


def _apply(transform, points):
    """One `transform` attribute — translate, rotate and scale — applied.

    `transform="translate(0,24) rotate(90)"` composes as T·R, so a point is
    rotated *first* and then translated. Applying them left to right instead
    put the boundary wall of every `translate(...) rotate(90)` glyph in the
    wrong place, and read the fixed node's wall as 12 deep against the 24 it
    draws — under-measuring, which is the direction that fails silently.
    """
    for kind, arg in reversed(
            re.findall(r"(translate|rotate|scale)\(([^)]*)\)", transform or "")):
        v = _nums(arg)
        if kind == "translate":
            dx, dy = (v + [0.0])[:2]
            points = [(x + dx, y + dy) for x, y in points]
        elif kind == "rotate":
            r = math.radians(v[0])
            cos, sin = math.cos(r), math.sin(r)
            points = [(x * cos - y * sin, x * sin + y * cos) for x, y in points]
        elif kind == "scale":
            sx = v[0]
            sy = v[1] if len(v) > 1 else sx
            points = [(x * sx, y * sy) for x, y in points]
    return points


def _corners(x, y, w, h):
    return [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]


def _points_of(el):
    if el.tag == "line":
        return [(float(el.get("x1")), float(el.get("y1"))),
                (float(el.get("x2")), float(el.get("y2")))]
    if el.tag in ("polyline", "polygon"):
        v = _nums(el.get("points"))
        return list(zip(v[::2], v[1::2]))
    if el.tag == "rect":
        return _corners(*(float(el.get(k))
                          for k in ("x", "y", "width", "height")))
    if el.tag == "circle":
        cx, cy, r = (float(el.get(k)) for k in ("cx", "cy", "r"))
        return _corners(cx - r, cy - r, 2 * r, 2 * r)
    return []


def _walk(el, clips, out, stack):
    clip = el.get("clip-path")
    if clip:
        cid = clip[clip.find("#") + 1:].rstrip(")")
        if cid in clips:                     # worth its clip rect, no more
            points = clips[cid]
            for t in reversed(stack + [el.get("transform")]):
                points = _apply(t, points)
            out.extend(points)
            return
    points = _points_of(el)
    if points:
        for t in reversed(stack + [el.get("transform")]):
            points = _apply(t, points)
        out.extend(points)
    if el.tag != "defs":                     # definitions are not drawn
        for kid in el:
            _walk(kid, clips, out, stack + [el.get("transform")])


def drawn_ink(sym):
    """How far `sym.draw(0)` actually marks, as (along, across)."""
    root = ET.fromstring(f"<svg>{sym.draw(0)}</svg>")
    clips = {c.get("id"): _corners(*(float(c[0].get(k))
                                     for k in ("x", "y", "width", "height")))
             for c in root.iter("clipPath")}
    points = []
    _walk(root, clips, points, [])
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (max(abs(min(xs)), abs(max(xs))), max(abs(min(ys)), abs(max(ys))))


@pytest.mark.parametrize("sym", symbols.SYMBOLS, ids=lambda s: s.key)
def test_no_symbol_draws_outside_what_it_reserves(sym):
    """The clipping failure is silent, so it needs a test that is not."""
    along, across = drawn_ink(sym)
    assert sym.ink[0] >= along - 0.01, "clipped along the branch"
    assert sym.ink[1] >= across - 0.01, "clipped across the branch"


@pytest.mark.parametrize("sym", symbols.SYMBOLS, ids=lambda s: s.key)
def test_reach_is_set_where_and_only_where_it_is_needed(sym):
    """`reach` exists to correct `half`/`half_len`, not to restate them."""
    if sym.reach is None:
        return
    clearance = (sym.half_len, sym.half)
    assert sym.reach != clearance, "reach repeats the clearance; drop it"
    assert drawn_ink(sym) > clearance or sym.reach > clearance


@pytest.mark.parametrize("angle", [0, 30, 45, 90, 135, 180, 270])
def test_a_rotated_symbol_reserves_its_own_shape(angle):
    """Anisotropically, and turning with the symbol.

    `extent` used to reserve `hypot(half_len, half)` in every direction — 44.9
    around a conduction box that draws 16 across — so a flat ladder carried
    three times the vertical slack it needed, at every angle equally.
    """
    b = (DiagramBuilder(R="K/W", T="°C")
         .node("a", "A", "100", at=(0, 0))
         .node("b", "B", "50", at=(300 * math.cos(math.radians(angle)),
                                   300 * math.sin(math.radians(angle))))
         .branch("a", "b", "cond", "Turned", "0.3"))
    symbol = [p for p in layout(b.build()) if p.symbol is not None][0]
    x0, y0, x1, y1 = bounds(symbol)
    along, across = symbol.symbol.ink
    cos, sin = (abs(f(math.radians(angle))) for f in (math.cos, math.sin))

    # the exact axis-aligned hull of a rotated rectangle, both ways
    assert (x1 - x0) / 2 == pytest.approx(along * cos + across * sin)
    assert (y1 - y0) / 2 == pytest.approx(along * sin + across * cos)
    # and flat, that is the box itself rather than its circumscribed circle
    if angle % 180 == 0:
        assert (y1 - y0) / 2 == pytest.approx(across)
        assert across < math.hypot(along, across)
