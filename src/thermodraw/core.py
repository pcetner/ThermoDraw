"""Thermal network symbols: text metrics, transforms, the solver.

Text model
----------
Every symbol carries one text block on one side of the branch, never split
across it:

    Case → Ambient          user label, semibold
    R_conv    1.80 K/W      symbol text (italic) + value (muted)

The user label is always the top line. Symbol text and value share the second
line when they fit and the value drops to a third line when they do not. One
block means the clearance solver runs once, which keeps everything tight
against the component.

Subscripts
----------
On a resistance the subscript is structural — cond, conv, rad, contact — set
by the library and naming physics. On T, C, P and q it is identity, set by the
caller and empty by default. A subscript on an R names a mechanism; a
subscript on a T names a place.
"""
import collections
import hashlib
import math
import re

from ._metrics import FALLBACK as _FALLBACK
from ._metrics import WIDTHS as _WIDTHS

SW = 1.8


def uid(prefix, *parts):
    """An element id derived from the element's own parameters.

    This was a global counter, which meant the same diagram rendered twice in
    one process produced different bytes — nothing that a golden-file test can
    survive, and noisy diffs for any committed asset. Hashing the parameters
    instead makes a render a pure function of its input, and identical
    elements collapse onto one definition for free.
    """
    key = "|".join(repr(v) for v in parts)
    return f"{prefix}-{hashlib.blake2s(key.encode(), digest_size=4).hexdigest()}"


# --------------------------------------------------------------- text metrics
# Which face each text class is drawn in, so a run is measured in the face
# that will actually render it. The user label is semibold and runs about 4%
# wider than regular — the same size as the error the measured tables remove.
CLASS_FACE = {"user": "semibold", "lbl": "italic"}


_ENT = re.compile(r"&(#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def text_w(s, size, face="regular"):
    s = _ENT.sub("\u2033", s)
    table, fallback = _WIDTHS[face], _FALLBACK[face]
    return sum(table.get(c, fallback) for c in s) * size


def measure(s, size, face="regular"):
    """Width of a run that may contain one smaller <tspan> subscript."""
    if "<tspan" not in s:
        return text_w(s, size, face)
    base, _, rest = s.partition("<tspan")
    inner = rest.partition(">")[2].partition("</tspan>")[0]
    return text_w(base, size, face) + text_w(inner, size * 0.7, face)


def sym_text(base, subscript=None):
    if not subscript:
        return base
    return f'{base}<tspan dy="4" font-size="0.7em">{subscript}</tspan>'


# ------------------------------------------------------------------ transform
def xf(x, y, a, mirror=False):
    m = " scale(1,-1)" if mirror else ""
    return f"translate({x:.2f},{y:.2f}) rotate({a:.2f}){m}"


def flips(a):
    return 90 < (a % 360) < 270


def normals(a):
    r = math.radians(a)
    return (math.sin(r), -math.cos(r)), (-math.sin(r), math.cos(r))


# ------------------------------------------------------------- block solver
def gap(pc, ph, oc, oh, a):
    """Separation between an axis-aligned box and an oriented one.

    Positive is the width of the clear space between them; zero is touching;
    negative is how far one has to move to stop penetrating. The value is the
    largest separation over the four separating axes, which is the standard
    SAT quantity: a single axis with daylight on it is enough to prove no
    overlap, so the best axis is the informative one.

    `_overlap` is this function's sign, and says so in one line. A checker
    that wants to rank collisions by how bad they are needs the magnitude, and
    a second copy of the formula would drift from the one the solver uses —
    which is the drift CLAUDE.md keeps warning about, arriving as a diagnostic
    that disagrees with the decision it claims to explain.
    """
    r = math.radians(a)
    u = (math.cos(r), math.sin(r))
    v = (-math.sin(r), math.cos(r))
    d = (oc[0] - pc[0], oc[1] - pc[1])
    worst = None
    for ax in ((1, 0), (0, 1), u, v):
        ra = ph[0] * abs(ax[0]) + ph[1] * abs(ax[1])
        rb = (oh[0] * abs(ax[0] * u[0] + ax[1] * u[1]) +
              oh[1] * abs(ax[0] * v[0] + ax[1] * v[1]))
        sep = abs(d[0] * ax[0] + d[1] * ax[1]) - (ra + rb)
        worst = sep if worst is None else max(worst, sep)
    return worst


def _overlap(pc, ph, oc, oh, a):
    return gap(pc, ph, oc, oh, a) < 0.0


def box_bounds(centre, half, angle=0.0, offset=(0.0, 0.0)):
    """Axis-aligned bounds of an oriented box: (x0, y0, x1, y1).

    `offset` is where the box's centre sits in the local frame, in local
    units. A boundary wall needs it: the wall hangs off its anchor point
    rather than straddling it, so its bounds are not symmetric about `centre`
    and reserving them as if they were is exactly the over-reservation this
    exists to end.
    """
    r = math.radians(angle)
    u = (math.cos(r), math.sin(r))
    v = (-math.sin(r), math.cos(r))
    cx = centre[0] + offset[0] * u[0] + offset[1] * v[0]
    cy = centre[1] + offset[0] * u[1] + offset[1] * v[1]
    ex = half[0] * abs(u[0]) + half[1] * abs(v[0])
    ey = half[0] * abs(u[1]) + half[1] * abs(v[1])
    return cx - ex, cy - ey, cx + ex, cy + ey


def segment_box(a, b, centre, half, angle=0.0):
    """Does the segment a-b touch the oriented box at `centre`?

    Rotates the segment into the box's frame rather than the box into the
    page's, so the slab test underneath stays the axis-aligned one the label
    solver already uses.
    """
    if not angle:
        return _segment_box(a, b, centre, half)
    r = math.radians(-angle)
    cos_r, sin_r = math.cos(r), math.sin(r)

    def local(p):
        dx, dy = p[0] - centre[0], p[1] - centre[1]
        return (dx * cos_r - dy * sin_r, dx * sin_r + dy * cos_r)

    return _segment_box(local(a), local(b), (0.0, 0.0), half)


def support(a, side, half_len, half_h):
    """How far the symbol's oriented box reaches along `side`."""
    r = math.radians(a)
    u = (math.cos(r), math.sin(r))
    v = (-math.sin(r), math.cos(r))
    return (half_len * abs(side[0] * u[0] + side[1] * u[1])
            + half_h * abs(side[0] * v[0] + side[1] * v[1]))


def clear_offset(cx, cy, a, side, half_len, half_h, bw, bh, gap):
    """Distance from the symbol centre to the near edge of the text block.

    Solved from the oriented box's support distance rather than walked up
    from a guess. Walking overshoots badly at diagonals: the block's
    axis-aligned bounding box clips the rotated symbol's corner long before
    the glyphs themselves would, so the search kept pushing. A narrowed test
    box catches real collisions without paying for empty corners.
    """
    d = support(a, side, half_len, half_h) + gap
    for _ in range(24):
        px = cx + side[0] * (d + bh / 2)
        py = cy + side[1] * (d + bh / 2)
        if not _overlap((px, py), (bw * 0.36, bh / 2),
                        (cx, cy), (half_len, half_h), a):
            return d
        d += 1.2
    return d


# ------------------------------------------------------------- occupancy
PAGE_SIDES = {"up": (0.0, -1.0), "down": (0.0, 1.0),
              "left": (-1.0, 0.0), "right": (1.0, 0.0)}


def _segment_box(a, b, centre, half):
    """Does the segment a-b touch the axis-aligned box at centre?

    Liang-Barsky against the four slabs. A label landing on a wire is the
    second half of the collision problem; the first half, clearing the
    symbol the label belongs to, is what clear_offset already does.
    """
    x0, y0 = a[0] - centre[0], a[1] - centre[1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 + half[0]), (dx, half[0] - x0),
                 (-dy, y0 + half[1]), (dy, half[1] - y0)):
        if p == 0:
            if q < 0:
                return False
            continue
        r = q / p
        if p < 0:
            if r > t1:
                return False
            t0 = max(t0, r)
        else:
            if r < t0:
                return False
            t1 = min(t1, r)
    return t0 <= t1


Blocker = collections.namedtuple("Blocker", "kind owner detail")
Blocker.__doc__ = """Why a rectangle was rejected.

`kind` is "box" or "segment"; `owner` is whatever was passed to the add call,
which for a rendered diagram is the `Placement` that put it there; `detail` is
the geometry, `(centre, half, angle)` or `(a, b)`.
"""


class Occupancy:
    """What is already on the page, so the next label can avoid it.

    clear_offset solves a label against its own symbol and knows nothing
    else, which is how a dissipation label came to overprint a conduction
    one and an ambient label came to sit on a wire. Both were fixed by hand,
    by moving coordinates and inflating a clearance parameter. This is the
    thing that should have known.
    """

    def __init__(self):
        self.boxes = []       # (centre, half, angle, owner)
        self.segments = []    # (a, b, owner)

    def add_box(self, centre, half, angle=0.0, owner=None):
        self.boxes.append((tuple(centre), tuple(half), angle, owner))

    def add_rect(self, left, top, bw, bh, owner=None):
        self.add_box((left + bw / 2, top + bh / 2), (bw / 2, bh / 2), 0.0, owner)

    def add_segment(self, a, b, owner=None):
        self.segments.append((tuple(a), tuple(b), owner))

    def blocker(self, centre, half, owner=None):
        """The first record that rejects this rectangle, or None if it fits.

        `free` is this function's sign. Reporting the blocker from inside the
        same loop is what keeps a diagnostic honest: reconstructing it from
        outside means a second implementation of the skip rule and the
        iteration order, and it will eventually name something the solver
        never even considered.
        """
        for oc, oh, angle, own in self.boxes:
            if own is not None and own is owner:
                continue
            if _overlap(centre, half, oc, oh, angle):
                return Blocker("box", own, (oc, oh, angle))
        for a, b, own in self.segments:
            if own is not None and own is owner:
                continue
            if _segment_box(a, b, centre, half):
                return Blocker("segment", own, (a, b))
        return None

    def free(self, centre, half, owner=None):
        """Is this rectangle clear of everything but its own symbol?"""
        return self.blocker(centre, half, owner) is None


RUN_GAP = 6
LINE_LEAD = 1.34
WRAP_AT = 168


def _line_w(line):
    return (sum(measure(t, s, CLASS_FACE.get(c, "regular")) for t, s, c in line)
            + RUN_GAP * (len(line) - 1))


def _line_h(line):
    return max(s for _, s, _ in line) * LINE_LEAD


def build_block(user=None, name=None, value=None,
                size=13, vsize=13, usize=11.5):
    """Lay the three texts into lines. User label always first.

    Symbol text and value are joined by an equals sign and set at the same
    size and weight, because that is what they are: two sides of one
    statement. Only the italic marks the variable.
    """
    lines = []
    if user:
        lines.append([(user, usize, "user")])
    if name and value:
        eq = [(name, size, "lbl"), ("=", size, "eq"), (value, vsize, "val")]
        if _line_w(eq) > WRAP_AT:
            lines.append([eq[0]])
            lines.append([eq[1], eq[2]])
        else:
            lines.append(eq)
    elif name:
        lines.append([(name, size, "lbl")])
    elif value:
        lines.append([(value, vsize, "val")])
    return lines


def _sides(a, side):
    """Candidate directions, best first.

    Auto keeps the original choice and adds its opposite as a fallback, so a
    blocked label steps across the branch rather than drifting away from it.
    """
    if side and side != "auto":
        return [PAGE_SIDES[side]]
    n1, n2 = normals(a)
    up, down = (n1, n2) if n1[1] <= n2[1] else (n2, n1)
    first = up if abs(up[1]) >= 0.35 else (up if up[0] > 0 else down)
    return [first, down if first is up else up]


def _corner(cx, cy, side, d, bw, bh):
    px, py = cx + side[0] * d, cy + side[1] * d
    if abs(side[0]) > 0.5:                       # block sits left or right
        return (px + 3 if side[0] > 0 else px - 3 - bw), py - bh / 2
    return px - bw / 2, (py - bh - 2 if side[1] < 0 else py + 2)


def annotate(cx, cy, a, out, user=None, name=None, value=None, half=10,
             half_len=None, gap=5, size=13, vsize=13, usize=11.5,
             side="auto", occupied=None, owner=None, report=None):
    """Place one text block and return the rectangle it took.

    `occupied` is consulted for labels already placed and wires already
    drawn; the block's own symbol is skipped through `owner`, because
    clear_offset has already solved that clearance and solved it tighter
    than a bounding box would.

    `report`, if given, is a dict updated in place with what happened — the
    same out-parameter idiom `out` already uses, so nothing that consumes the
    return value has to change. It carries:

        side     the unit direction chosen, as a vector
        solved   the offset clear_offset asked for
        used     the offset actually taken; more than `solved` means the
                 block was pushed out past its own symbol to clear something
        flipped  True when the label crossed to the other side of the branch
        clear    False when the push loop ran out of steps and accepted an
                 overlap anyway

    That last one is the point of the whole parameter. The loop below has
    always been able to give up silently, and a label printed over a wire is
    indistinguishable in the output from one placed deliberately.
    """
    lines = build_block(user, name, value, size, vsize, usize)
    if not lines:
        return None
    hl = half if half_len is None else half_len
    bw = max(_line_w(l) for l in lines)
    bh = sum(_line_h(l) for l in lines)

    chosen, left, top = None, None, None
    solved = used = 0.0
    clear = True
    candidates = _sides(a, side)
    for cand in candidates:
        d = clear_offset(cx, cy, a, cand, hl, half, bw, bh, gap)
        x, y = _corner(cx, cy, cand, d, bw, bh)
        if occupied is None or occupied.free(
                (x + bw / 2, y + bh / 2), (bw / 2, bh / 2), owner):
            chosen, left, top = cand, x, y
            solved = used = d
            break

    if chosen is None:                # nowhere clear: push out on the first
        chosen = candidates[0]
        d = clear_offset(cx, cy, a, chosen, hl, half, bw, bh, gap)
        solved = d
        for _ in range(40):
            left, top = _corner(cx, cy, chosen, d, bw, bh)
            if occupied.free((left + bw / 2, top + bh / 2),
                             (bw / 2, bh / 2), owner):
                break
            d += 4
        else:
            left, top = _corner(cx, cy, chosen, d, bw, bh)
            clear = False
        used = d

    if report is not None:
        report.update(side=chosen, solved=solved, used=used, clear=clear,
                      flipped=chosen is not candidates[0])

    y = top
    for line in lines:
        lh = _line_h(line)
        base = y + max(s for _, s, _ in line) * 0.80
        x = left + (bw - _line_w(line)) / 2
        for txt, sz, cls in line:
            out.append(f'<text class="{cls}" x="{x:.1f}" y="{base:.1f}" '
                       f'text-anchor="start">{txt}</text>')
            x += measure(txt, sz, CLASS_FACE.get(cls, "regular")) + RUN_GAP
        y += lh
    if occupied is not None:
        occupied.add_rect(left, top, bw, bh, owner=owner)
    return left, top, bw, bh


# ------------------------------------------------------------------ textures
BW, BH = 84, 32


def clip_rect(w, h, x=None, y=None):
    x = -w / 2 if x is None else x
    y = -h / 2 if y is None else y
    i = uid("clip", w, h, x, y)
    return i, (f'<clipPath id="{i}"><rect x="{x}" y="{y}" '
               f'width="{w}" height="{h}"/></clipPath>')


_DEFS = re.compile(r"<defs>(.*?)</defs>", re.S)


def hoist_defs(body):
    """Move every <defs> block to the front, keeping one copy of each.

    Ids are content-addressed, so two identical clip rects now produce the
    same id by design. Emitting each definition once keeps ids unique in the
    document — duplicates are invalid SVG even when renderers tolerate them —
    and drops the repeated boilerplate.
    """
    seen = dict.fromkeys(_DEFS.findall(body))
    if not seen:
        return body
    return f'<defs>{"".join(seen)}</defs>' + _DEFS.sub("", body)


def _rules(R, step, angle):
    n = int(2 * R / step) + 1
    lines = "".join(
        f'<line x1="{-R:.1f}" y1="{-R + i*step:.1f}" x2="{R:.1f}" '
        f'y2="{-R + i*step:.1f}"/>' for i in range(n))
    return f'<g transform="rotate({angle:.2f})">{lines}</g>'


def hatch(w, h, angle=45, step=7, cls="tex", x=None, y=None):
    cid, defs = clip_rect(w, h, x, y)
    cx = 0 if x is None else x + w / 2
    cy = 0 if y is None else y + h / 2
    R = math.hypot(w, h) / 2 + step
    return (f'<defs>{defs}</defs><g class="{cls}" clip-path="url(#{cid})">'
            f'<g transform="translate({cx},{cy})">{_rules(R, step, angle)}</g></g>')


def streamlines(w, h, n=3, cls="tex"):
    cid, defs = clip_rect(w, h)
    out = []
    for i in range(n):
        y = -h / 2 + h * (i + 1) / (n + 1)
        pts = [f"{-w/2 + (k/24)*w:.1f},{y + 3.2*math.sin(2*math.pi*(k/24) + i):.1f}"
               for k in range(25)]
        out.append(f'<polyline points="{" ".join(pts)}"/>')
    return (f'<defs>{defs}</defs><g class="{cls}" clip-path="url(#{cid})">'
            f'{"".join(out)}</g>')


def tapered_wave(x0, x1, amp=5.0, periods=2.5, taper=0.45, y=0.0, n=72):
    """A·sin(x) with A ramping linearly to zero at x1.

    The shaft therefore arrives on a horizontal tangent and meets the
    arrowhead flush, instead of butting into it at maximum slope.
    """
    L = x1 - x0
    hold = 1.0 - taper
    pts = []
    for k in range(n + 1):
        t = k / n
        env = 1.0 if t <= hold else max(0.0, 1.0 - (t - hold) / taper)
        pts.append(f"{x0 + t*L:.2f},{y + amp*env*math.sin(2*math.pi*periods*t):.2f}")
    return f'<polyline points="{" ".join(pts)}"/>'


def wave_arrow(x0, x1, amp=5.0, periods=2.5, head=11.0, y=0.0,
               taper=0.45, cls=None, size=6.0):
    """Wavy shaft plus head, spanning exactly x0..x1 so it can be centred."""
    shaft = tapered_wave(x0, x1 - head, amp, periods, taper, y)
    poly = (f'<polygon points="{x1-head},{y-size} {x1},{y} '
            f'{x1-head},{y+size}"/>')
    if cls:
        return f'<g class="{cls}">{shaft}{poly}</g>'
    return shaft + f'<polygon class="fillsym" points="{x1-head},{y-size} ' \
                   f'{x1},{y} {x1-head},{y+size}"/>'


def arrowhead(x, y=0.0, size=6.5, length=12.0):
    return (f'<polygon class="fillsym" points="{x-length},{y-size} '
            f'{x},{y} {x-length},{y+size}"/>')


def hatched_wall(x, half_h, depth=12, angle=45, step=4.5):
    return (f'<line class="w" x1="{x}" y1="{-half_h}" x2="{x}" y2="{half_h}"/>'
            + hatch(depth, 2 * half_h, angle, step, x=x, y=-half_h))
