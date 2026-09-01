"""Turning placements into a document.

Pure and deterministic: the same placements always produce the same bytes.
This is where the plumbing the demo had to invent for itself lives — wires,
nodes, boundary grounds, and placing a symbol at a point and an angle.

Labels go on last so they sit above the geometry, and they are placed through
`core.annotate`, which still solves each block against its own symbol. It now
reports the rectangle it used, which is what lets the canvas size itself.
"""
import math

from . import core as S
from . import symbols as SY

PADDING = 24


def wire(points):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline class="w" points="{d}"/>'


def node(x, y, r=5.5):
    return f'<circle class="node-open" cx="{x:.1f}" cy="{y:.1f}" r="{r}"/>'


def ground(x, y, angle=90, half=24, depth=13):
    """A hatched boundary band. angle=90 lays it flat, hatch below."""
    return (f'<g transform="{S.xf(x, y, angle)}">'
            f'{S.hatched_wall(0, half, depth)}</g>')


def place(sym, x, y, angle=0.0):
    """Boundary symbols mirror past vertical rather than arriving upside down."""
    mirror = sym.mirror and S.flips(angle)
    return f'<g transform="{S.xf(x, y, angle, mirror)}">{sym.draw(angle)}</g>'


def _segments(points):
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _key(seg):
    """Segments match regardless of which way round they were routed."""
    a, b = ((round(p[0], 1), round(p[1], 1)) for p in seg)
    return (a, b) if a <= b else (b, a)


def draw(placements):
    """Markup and the rectangles the labels occupy.

    Wires come first so symbols sit over them, labels last so they sit over
    everything. Identical segments are drawn once: two branches sharing a
    trunk both route along it, and stroking it twice is waste.
    """
    wires, glyphs, nodes, labels = [], [], [], []
    rects, seen = [], set()

    for p in placements:
        if p.element != "wire":
            continue
        for seg in _segments([tuple(q) for q in p.points]):
            key = _key(seg)
            if key in seen or seg[0] == seg[1]:
                continue
            seen.add(key)
            wires.append(wire(seg))

    for p in placements:
        if p.element == "symbol":
            glyphs.append(place(p.symbol, p.at[0], p.at[1], p.angle))
        elif p.element == "ground":
            glyphs.append(ground(p.at[0], p.at[1], p.angle))
        elif p.element == "node":
            nodes.append(node(p.at[0], p.at[1], p.radius))

    # What is already on the page, so each label can avoid it. A label's own
    # symbol is registered against it as owner and skipped: clear_offset
    # solves that clearance, and solves it tighter than a bounding box can.
    occupied = S.Occupancy()
    for p in placements:
        if p.element == "wire":
            for a, b in _segments([tuple(q) for q in p.points]):
                occupied.add_segment(a, b)
        elif p.symbol is not None:
            occupied.add_box(p.at, (p.symbol.half_len, p.symbol.half),
                             p.angle, owner=p)
        elif p.element == "node":
            occupied.add_box(p.at, (p.radius, p.radius), 0.0, owner=p)

    for p in placements:
        lab = p.label
        if lab is None or not (lab.user or lab.value or lab.name):
            continue
        rect = S.annotate(p.at[0], p.at[1], p.angle, labels, user=lab.user,
                          name=lab.name, value=lab.value,
                          half=lab.half, half_len=lab.half_len,
                          side=lab.side, occupied=occupied, owner=p)
        if rect:
            rects.append(rect)

    return wires + glyphs + nodes + labels, rects


def extent(placements, rects, padding=PADDING):
    """What the drawing actually covers, labels included."""
    xs, ys = [], []
    for p in placements:
        if p.element == "wire":
            xs += [q[0] for q in p.points]
            ys += [q[1] for q in p.points]
            continue
        reach = p.radius
        if p.symbol is not None:
            reach = math.hypot(p.symbol.half_len, p.symbol.half)
        elif p.element == "ground":
            reach = 30.0
        xs += [p.at[0] - reach, p.at[0] + reach]
        ys += [p.at[1] - reach, p.at[1] + reach]
    for left, top, bw, bh in rects:
        xs += [left, left + bw]
        ys += [top, top + bh]
    if not xs:
        return 0.0, 0.0, 0.0, 0.0
    return (min(xs) - padding, min(ys) - padding,
            max(xs) + padding, max(ys) + padding)


def render(placements, size=None, padding=PADDING):
    """A complete SVG, sized to its contents unless told otherwise.

    `canvas` took dimensions the caller invented, and anything placed outside
    them was clipped with no warning at all. Measuring what was emitted
    removes the guess; passing `size` keeps the old behaviour.
    """
    parts, rects = draw(placements)
    body = "".join(parts)
    if size is not None:
        return SY.canvas(size[0], size[1], body)
    x0, y0, x1, y1 = extent(placements, rects, padding)
    shifted = f'<g transform="translate({-x0:.1f},{-y0:.1f})">{body}</g>'
    return SY.canvas(round(x1 - x0, 1), round(y1 - y0, 1), shifted)
