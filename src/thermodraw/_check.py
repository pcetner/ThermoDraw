"""Is this diagram any good? — answered without looking at it.

The library's premise is that you can describe a thermal network to a model
and have it emit drawable data. That was tested directly: an agent given only
`docs/schema.md` produced correct, valid diagrams on the first run with no
traceback. They were also ugly, and the only way to find that out was to
render, serve over HTTP, open a browser, screenshot, and look — five sequential
tool calls per revision. Meanwhile every golden test passed. Goldens pin bytes;
they notice that something moved and can say nothing about whether it should
have.

So this module reports the defects that round trip was finding. Two of the
ten are the executable form of a paragraph `docs/schema.md` once offered as
advice.

Nothing here re-derives the page. `compose` hands back the occupancy the
labels were actually solved against and what `core.annotate` did with each one,
because a diagnostic that rebuilds the page will eventually disagree with the
render it claims to explain, and it will be right about the rebuild.

    from thermodraw import Diagram, check
    report = check(Diagram.from_json(open("d.json").read()))
    print(report.text())

Severity is a claim about the reader, not about the geometry. An **error** is
something a reader would misread — overprinted text, a wire through a symbol,
ink off the page. A **warning** is something they would notice and mistrust. A
**note** is a habit worth having that the flagship diagram itself breaks.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import core
from . import model as M
from ._layout import layout as _layout, network, pieces
from ._render import PADDING, _wall_box, compose

# How far past its own solved clearance a label may be pushed before it is
# reported. `core.clear_offset` solves the tight placement; the push loop only
# runs when something else is in the way, and it moves in steps of 4.
ADRIFT = 8.0

# Boxes that merely touch are not overlapping. Series symbols are drawn with
# leads that meet, and the numbers arrive through trigonometry.
TOUCH = 0.5

# A wire is "through" a symbol only if it enters the body, not if it grazes an
# edge. Every branch's own leads stop exactly on its symbol's boundary.
SHAVE = 1.0

# Opposite margins may differ by this fraction of the padding before the
# drawing reads as sitting off-centre in its own frame.
FRAME_SLACK = 0.25

ORDER = {"error": 0, "warning": 1, "note": 2}
COLOUR = {"error": "\033[31m", "warning": "\033[33m", "note": "\033[36m"}
RESET = "\033[0m"


@dataclass(frozen=True)
class Finding:
    """One thing wrong, named where the author can act on it."""

    code: str
    severity: str
    where: str
    message: str
    remedy: str = ""
    at: Optional[Tuple[float, float]] = None

    def line(self, colour=False):
        """One line, ASCII only.

        This goes to a terminal, and a Windows console is cp1252 by default: an
        arrow or an em dash in a fixed string is a UnicodeEncodeError on the
        machine most likely to be running it. Node ids can still carry
        anything, which is why `__main__` also softens stdout.
        """
        head = f"{self.severity}: " if not colour else \
            f"{COLOUR[self.severity]}{self.severity}{RESET}: "
        tail = f"  -> {self.remedy}" if self.remedy else ""
        return f"{head}[{self.code}] {self.message}{tail}"


@dataclass
class Report:
    """What the checker found, and enough context to say nothing is wrong."""

    findings: List[Finding] = field(default_factory=list)
    labels: int = 0
    source: str = "diagram"

    @property
    def ok(self):
        """No error and no warning. Notes are advice, and do not fail."""
        return not any(f.severity in ("error", "warning") for f in self.findings)

    def count(self, severity):
        return sum(1 for f in self.findings if f.severity == severity)

    def worst(self):
        if not self.findings:
            return "ok"
        return min((f.severity for f in self.findings), key=ORDER.__getitem__)

    def text(self, colour=False):
        """The report as lines, opening with what went right.

        The summary line is there because an agent needs a signal that says
        *good*, not merely an absence of output — silence is also what a
        crashed checker produces.
        """
        def plural(n, word):
            return f"{n} {word}" + ("" if n == 1 else "s")

        head = (f"{self.source}: {plural(self.labels, 'label')} placed, "
                + ", ".join(plural(self.count(s), s)
                            for s in ("error", "warning", "note")))
        return "\n".join([head] + [f.line(colour) for f in self.findings])

    def to_dict(self):
        return {
            "source": self.source,
            "ok": self.ok,
            "labels": self.labels,
            "findings": [
                {"code": f.code, "severity": f.severity, "where": f.where,
                 "message": f.message, "remedy": f.remedy,
                 "at": list(f.at) if f.at else None}
                for f in self.findings],
        }


# ------------------------------------------------------------------ geometry
def _rect_of(rect):
    """A label rectangle as (centre, half)."""
    left, top, bw, bh = rect
    return (left + bw / 2, top + bh / 2), (bw / 2, bh / 2)


def _free_sides(scene, rect):
    """Which page sides this label could actually be moved to."""
    owner = rect.owner
    lab = getattr(owner, "label", None)
    if owner is None or lab is None or scene.occupancy is None:
        return ()
    left, top, bw, bh = rect
    return tuple(core.free_sides(owner.at[0], owner.at[1], owner.angle,
                                 lab.half_len, lab.half, bw, bh,
                                 scene.occupancy, owner))


def _obb_gap(c1, h1, a1, c2, h2, a2):
    """Separation between two oriented boxes.

    `core.gap` takes the first box axis-aligned, which is what the label solver
    needs and not what comparing two rotated symbols needs. Rotating the second
    into the first's frame turns one into the other.
    """
    r = math.radians(-a1)
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    local = (dx * math.cos(r) - dy * math.sin(r),
             dx * math.sin(r) + dy * math.cos(r))
    return core.gap((0.0, 0.0), h1, local, h2, a2 - a1)


def _point_rect(p, centre, half):
    dx = max(0.0, abs(p[0] - centre[0]) - half[0])
    dy = max(0.0, abs(p[1] - centre[1]) - half[1])
    return math.hypot(dx, dy)


def _point_segment(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    length = vx * vx + vy * vy
    t = 0.0 if not length else max(0.0, min(
        1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / length))
    return math.hypot(p[0] - a[0] - t * vx, p[1] - a[1] - t * vy)


def _segment_rect_gap(a, b, centre, half):
    """Clear distance between a segment and an axis-aligned rectangle.

    Zero if they touch. For two disjoint convex shapes the closest pair puts a
    vertex of one against the other, so checking both directions is exact.
    """
    if core._segment_box(a, b, centre, half):
        return 0.0
    corners = [(centre[0] + sx * half[0], centre[1] + sy * half[1])
               for sx in (-1, 1) for sy in (-1, 1)]
    return min([_point_segment(c, a, b) for c in corners]
               + [_point_rect(a, centre, half), _point_rect(b, centre, half)])


def _placement_gap(centre, half, p):
    """Clear distance from a label rectangle to one placement's geometry."""
    if p.element == "wire":
        pts = [tuple(q) for q in p.points]
        return min([_segment_rect_gap(pts[i], pts[i + 1], centre, half)
                    for i in range(len(pts) - 1)] or [float("inf")])
    if p.symbol is not None:
        return core.gap(centre, half, p.at,
                        (p.symbol.half_len, p.symbol.half), p.angle)
    if p.element == "ground":
        wc, wh, wa = _wall_box(p)
        return core.gap(centre, half, wc, wh, wa)
    return core.gap(centre, half, p.at, (p.radius, p.radius), 0.0)


def _name(p):
    """A placement, in the words the author used to write it."""
    if p is None:
        return "something on the page"
    ref = p.ref or "an unnamed element"
    if p.element == "ground":
        return f"the boundary wall of {ref}"
    if p.element == "wire":
        return f"the wire of {ref}"
    return ref


def _kind_of(p):
    """Which of the three things a placement is, for advice that differs."""
    if p is None:
        return "?"
    if p.element == "node":
        return "node"
    if p.role in ("source", "rail"):
        return p.role
    return "branch"


def _move(p, past="this label"):
    """How you move this particular thing, in the field that moves it.

    None when nothing about it moves usefully, so the remedy falls through
    to the label's own `side` or `angle`. A wire goes where its branch's
    waypoints and nodes put it, and the field that moves it depends on what
    the branch has. A source's lead has no `via` at all; the validator
    refuses `via` on a repeated branch, and its comb stands where it stands;
    a straight run between two nodes has no waypoint to move, but can be
    given one. All three were once told "move a `via` waypoint", and a
    clean-room reader hit the second three times on one branch and the
    third twice on another, each time a round lost to applying the remedy
    as written.
    """
    ref, kind = p.ref or "it", _kind_of(p)
    if p.element == "wire":
        if kind == "source":
            return f"move {ref} with `at`"
        if kind == "rail":
            return "move the rail with `rail.y`"
        if p.via:
            return (f"move a `via` waypoint on {ref} so it does not run "
                    f"past {past}")
        if p.count and p.count > 1:
            # A comb's risers stand a fixed distance out from each node, so
            # neither `via` nor moving the nodes apart takes them past a
            # label wider than that. Only the label can move.
            return None
        return f"give {ref} a `via` waypoint so it does not run past {past}"
    if p.element == "symbol":
        where = "further from its node" if kind == "source" else \
            "along its branch"
        return f"move {ref} {where} with `at`"
    return f"move {ref} with `at`"


def _remedy(culprit, owner=None, free=(), pair=False):
    """The schema field that fixes *this* case, not a list of all of them.

    `free` is which of the four sides the occupancy says are actually
    available, from `core.free_sides`. Naming a side without asking was the
    single worst thing this function did: it told a node to try left or right
    when those were the directions its two branches left in, and on a vertical
    branch it named the two sides that lie *along* the wire. Following it
    turned warnings into errors. The checker held the object that proved the
    advice wrong at the moment it gave it.

    `angle` is only ever offered for a **node**. The schema's own tables give
    it three meanings: on a node it "moves the label and nothing else", on a
    branch it "overrides the direction taken from the wire", and on a source
    it aims the arrow. Recommending it for a branch label rotated the
    conduction box to lie diagonally across its own wire — and the checker
    then passed the result, which makes it the worst kind of bad advice: the
    kind that appears to work.

    `via` is only ever offered for a wire that has one. The clean-room run
    was told to move a waypoint on a branch with none and on a `count: 8`
    branch that cannot have one, five times between two readers, and each
    time the brief's instruction to apply the remedy literally cost a round.
    `_move` says None for those, and the option is simply not there.
    """
    options = []
    if pair:
        options.append("set `side` on one of the two")
    elif culprit is not None:
        move = _move(culprit)
        if move:
            options.append(move)

    if free:
        options.append("set `side` to "
                       + " or ".join(f'"{s}"' for s in free))
    elif owner is not None:
        # No side is free, so naming one is worse than saying nothing. What
        # is left depends on what the label belongs to.
        if _kind_of(owner) == "node":
            options.append("`angle`, which turns a node's label frame and is "
                           "the only thing that reaches a diagonal")
        else:
            move = _move(owner)
            if move:
                options.append(move + " to take its label with it")
    return ", or ".join(options) or "move the two apart with `at`"


# --------------------------------------------------------------- the network
def _round(p):
    return round(p[0], 1), round(p[1], 1)


def _ekey(a, b):
    return (a, b) if a <= b else (b, a)


def _on_segment(v, a, b, tol=0.1):
    if v == a or v == b:
        return False
    vx, vy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(vx, vy)
    if not length:
        return False
    cross = abs((v[0] - a[0]) * vy - (v[1] - a[1]) * vx) / length
    if cross > tol:
        return False
    t = ((v[0] - a[0]) * vx + (v[1] - a[1]) * vy) / (length * length)
    return tol / length < t < 1.0 - tol / length


def wire_graph(placements):
    """The drawn network as {edge: {refs}}, with the symbol gaps bridged.

    Two steps that a hand-wave misses, and without either the ladder has no
    cycles at all:

    `layout._split` cuts `2 * half_len` out of every route to make room for
    the symbol, so the drawn wire graph has a hole in every single branch. A
    synthetic edge across each symbol closes it, and its endpoints are exactly
    the points `_split` produced, so they land on vertices that already exist.

    A capacitance dropping onto the middle of the rail shares no vertex with
    it — the rail is one long segment from end to end. Every edge is therefore
    split at every vertex lying on it.
    """
    edges = defaultdict(set)

    def add(a, b, ref):
        a, b = _round(a), _round(b)
        if a != b:
            edges[_ekey(a, b)].add(ref)

    for p in placements:
        if p.element == "wire":
            pts = [tuple(q) for q in p.points]
            for i in range(len(pts) - 1):
                add(pts[i], pts[i + 1], p.ref)
        elif p.symbol is not None:
            r = math.radians(p.angle)
            ux = math.cos(r) * p.symbol.half_len
            uy = math.sin(r) * p.symbol.half_len
            add((p.at[0] - ux, p.at[1] - uy),
                (p.at[0] + ux, p.at[1] + uy), p.ref)

    verts = {v for key in edges for v in key}
    out = defaultdict(set)
    for (a, b), refs in edges.items():
        on = sorted((v for v in verts if _on_segment(v, a, b)),
                    key=lambda v: (v[0] - a[0]) ** 2 + (v[1] - a[1]) ** 2)
        chain = [a] + on + [b]
        for i in range(len(chain) - 1):
            out[_ekey(chain[i], chain[i + 1])].update(refs)
    return dict(out)


def cycles(edges):
    """Fundamental cycles of the wire graph, as vertex rings.

    A spanning forest by DFS; every edge outside it closes exactly one cycle,
    so there are `E - V + C` of them and the set is deterministic. This is not
    every cycle in the graph — a nested pair can hide one, and enumerating all
    of them is exponential — but it finds every loop a hand-drawn ladder makes,
    which is what the corridor test needs.
    """
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)

    parent, seen, tree = {}, set(), set()
    for root in sorted(adj):
        if root in seen:
            continue
        stack = [(root, None)]
        while stack:
            v, par = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            parent[v] = par
            if par is not None:
                tree.add(_ekey(par, v))
            for w in sorted(adj[v], reverse=True):
                if w not in seen:
                    stack.append((w, v))

    rings = []
    for a, b in sorted(edges):
        if _ekey(a, b) in tree:
            continue
        up_a, v = [], a
        while v is not None:
            up_a.append(v)
            v = parent[v]
        index = {v: i for i, v in enumerate(up_a)}
        up_b, v = [], b
        while v not in index:
            up_b.append(v)
            v = parent[v]
        rings.append(up_a[:index[v] + 1] + list(reversed(up_b)))
    return rings


def _inside(pt, ring):
    """Even-odd ray cast: is the point enclosed by this ring?"""
    x, y = pt
    inside = False
    for i, (x0, y0) in enumerate(ring):
        x1, y1 = ring[(i + 1) % len(ring)]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            inside = not inside
    return inside


# ----------------------------------------------------------------- the checks
def _label_lookup(rects):
    """Which occupancy box is which label, by the geometry it was added with."""
    return {(_rect_of(r)[0], _rect_of(r)[1]): r for r in rects}


def _collisions(scene, out):
    """Text printed over something else.

    Two ways in. Either the rectangle overlaps a record the solver could see,
    which now includes the boundary wall; or the push loop ran its forty steps
    and accepted an overlap rather than dropping the label, which it has always
    been able to do without saying so.

    The remedy names `angle` as well as `side`, because `side` offers four
    directions and a node can have all four taken. A ladder node has two
    branches and two free sides, so `side` is always enough there; a node
    fanning three ways with a capacitance below and a source coming in has
    five attachments for four slots, and only `angle` reaches the diagonals.
    """
    labels = _label_lookup(scene.rects)
    seen = set()
    for rect in scene.rects:
        centre, half = _rect_of(rect)
        hit = scene.occupancy.blocker(centre, half, owner=rect.owner)
        if hit is None and rect.clear:
            continue
        culprit, is_pair = (hit.owner if hit else None), False
        if hit is None:
            what = "something it could not get clear of"
        elif hit.kind == "box" and (hit.detail[0], hit.detail[1]) in labels:
            # Two labels on top of each other is one problem, and both of them
            # find the other. Report the pair once.
            other = labels[(hit.detail[0], hit.detail[1])]
            pair = frozenset((id(rect), id(other)))
            if pair in seen:
                continue
            seen.add(pair)
            what = f"the label on {_name(other.owner)}"
            is_pair = True
        else:
            what = _name(hit.owner)
        out.append(Finding(
            "label-collision", "error", rect.ref or "a label",
            f"{rect.ref}: its label is printed over {what}",
            remedy=_remedy(culprit, rect.owner, _free_sides(scene, rect),
                           pair=is_pair),
            at=centre))


def _adrift(scene, placements, out):
    """A label shoved so far out it no longer reads as belonging to anything.

    The trigger is exact and costs nothing: `core.annotate` reports both the
    offset it solved and the offset it took, and they differ only when the push
    loop ran. Attribution is the part worth doing — "this moved" is not
    actionable, "this moved to get around that" is.
    """
    for rect in scene.rects:
        if rect.used - rect.solved <= ADRIFT:
            continue
        centre, half = _rect_of(rect)
        # Everything not belonging to the label's own element, boundary walls
        # included: a node's own wall shares its ref and is skipped by that
        # alone, so a neighbour's wall can still be named as the culprit.
        others = [(_placement_gap(centre, half, p), p) for p in placements
                  if p.ref != rect.ref]
        others = [o for o in others if o[0] < float("inf")]
        if not others:
            continue
        near, culprit = min(others, key=lambda o: o[0])
        own = min([_placement_gap(centre, half, p) for p in placements
                   if p.ref == rect.ref] or [float("inf")])
        closer = (" and now sits nearer that than the thing it names"
                  if near < own else "")
        wide = _too_wide(rect, half, culprit, placements)
        if wide is not None:
            out.append(wide)
            continue
        out.append(Finding(
            "label-adrift", "warning", rect.ref or "a label",
            f"{rect.ref}: its label was pushed {rect.used - rect.solved:.0f} "
            f"past its own clearance to get around {_name(culprit)}{closer}",
            remedy=_remedy(culprit, rect.owner,
                           _free_sides(scene, rect)),
            at=centre))


def _too_wide(rect, half, culprit, placements):
    """A node label that does not fit between the symbols either side of it.

    `label-adrift` names whatever is nearest, and on a node between two
    short runs that is the symbol on one of them. Move that symbol away and
    the label is pushed by the one on the other side, by exactly the same
    amount, and the finding blames that one instead. A clean-room reader
    spent two rounds proving the named remedy had no effect: the label was
    192 wide and the room between the two symbols was 176, and no `at` on
    either neighbour changes what a label centred on the node needs.
    `nodes-too-close` speaks in those terms and did not fire, because it
    sums the labels *along* a run and a node label sits across its node,
    half in each. This is that arithmetic for the node.
    """
    owner = rect.owner
    if (owner is None or owner.element != "node" or not owner.ends
            or culprit.symbol is None or culprit.role != "branch"
            or owner.ends[0] not in culprit.ends):
        return None
    node = owner.ends[0]
    axis = 0 if half[0] >= half[1] else 1          # the label's long axis
    beside = [p for p in placements
              if p.symbol is not None and p.role == "branch"
              and node in p.ends and p.copy in (None, 0)
              and abs(math.sin(math.radians(p.angle - 90 * axis))) < 0.01]
    x = owner.at[axis]
    before = [(p.at[axis] + p.symbol.half_len, p)
              for p in beside if p.at[axis] < x]
    after = [(p.at[axis] - p.symbol.half_len, p)
             for p in beside if p.at[axis] > x]
    if not before or not after:
        return None
    (lo, pa), (hi, pb) = max(before), min(after)
    room, width = hi - lo, 2 * half[axis]
    if width <= room:
        return None
    others = [f"node '{e}'" for p in (pa, pb) for e in p.ends
              if e != node and e != M.RAIL]
    centre = (rect[0] + rect[2] / 2, rect[1] + rect[3] / 2)
    return Finding(
        "label-adrift", "warning", rect.ref or "a label",
        f"{rect.ref}: its label is {width:.0f} wide and the room between "
        f"{pa.ref} and {pb.ref} is {room:.0f}, so moving either of them "
        "along its branch cannot clear it",
        remedy=f"move {' and '.join(others)} further from {owner.ref} with "
               "`at`; it is the labels that set the spacing",
        at=centre)


def _crowded_run(scene, placements, out):
    """Two nodes closer together than the labels along the run between them.

    Every other finding names whatever is *nearest* the crowded label, and on
    a short run that is a wire — so the author is told to move a `via` when
    what is actually wrong is the spacing, and can spend an afternoon routing
    around a problem that routing cannot fix. An acceptance reader did
    exactly that. `docs/schema.md` has always said the right thing in prose —
    "it is the label that decides how far apart two nodes have to be" — and
    this is that sentence with the numbers filled in.

    Two conditions, and both are load-bearing:

    The arithmetic alone over-reports. Labels stack at different heights, so
    their spans along the run can overlap without the blocks ever touching: a
    four-stage ladder at 180 has labels summing to 187 and is completely
    clean. So the trigger is a label having actually been pushed, which is a
    fact the scene reports, and the widths are only the explanation.

    The push alone under-explains. A label pushed by a waypoint rising out of
    its node is not a spacing problem, and saying so would be worse advice
    than the wire it replaces. So the sum has to exceed the span as well.

    Straight runs only. A branch with waypoints has more room along its route
    than the straight line between its nodes, and the sum would be measured
    against the wrong number.
    """
    rects = {id(r.owner): r for r in scene.rects if r.owner is not None}
    nodes = {p.ends[0]: p for p in placements
             if p.element == "node" and p.role == "node"}

    for p in placements:
        if p.symbol is None or p.role != "branch":
            continue
        if p.copy not in (None, 0):     # one pass per group, not per copy
            continue
        na, nb = (nodes.get(e) for e in p.ends)
        if na is None or nb is None:
            continue
        a, b = tuple(na.at), tuple(nb.at)
        span = math.dist(a, b)
        if span < 1:
            continue

        # straight run: the symbol and every wire point sit on the segment
        route = [tuple(q) for w in placements
                 if w.ref == p.ref and w.element == "wire" for q in w.points]
        if any(_point_segment(q, a, b) > 1.0 for q in route + [tuple(p.at)]):
            continue

        ux = abs(b[0] - a[0]) / span
        uy = abs(b[1] - a[1]) / span
        owners = (na, nb, p)
        if not any((r := rects.get(id(o))) is not None
                   and r.used - r.solved > ADRIFT for o in owners):
            continue
        needed = 0.0
        for owner in owners:
            r = rects.get(id(owner))
            if r is None:
                continue
            # the two node labels sit at the ends and only half of each is in
            # the way; the branch label is between them and all of it is
            needed += (ux * r[2] + uy * r[3]) * (1.0 if owner is p else 0.5)
        if needed <= span:
            continue

        out.append(Finding(
            "nodes-too-close", "warning", p.ref,
            f"{na.ref} and {nb.ref} are {span:.0f} apart, and the labels "
            f"along that run come to {needed:.0f}",
            remedy="move them apart with `at`. It is the labels that set the "
                   f"spacing, not the symbol, which is only "
                   f"{2 * p.symbol.half_len:.0f} wide",
            at=tuple(p.at)))


def _islands(placements, out):
    """Whether the network is actually one network.

    A two-phase loop drawn with a `flow` annotation at each end looks joined
    and is not: nothing in the file relates the two arrows except that the
    same number was typed twice. The drawing came back clean with its network
    severed in half, and a house left its roof wired to nothing indoors. Both
    passed every other check here.

    Over **nodes joined by branches**, not over wire segments. The hero's own
    wire graph is in two pieces — sizes 3 and 24 — because a source's lead and
    a node's boundary stub are legitimately separate bits of ink, so a check
    on wire connectivity would condemn the flagship. Connectivity is a
    question about the network, and the network is nodes and branches.

    A `break` branch **does** count, though it carries no heat. It was
    tempting to exclude it — the two sides of a standoff really are thermally
    apart — but that is the wrong question. This finding exists to catch a
    path the author meant to draw and did not. A break is the opposite: an
    explicit statement that nothing flows here. Excluding it warns about every
    standoff ever drawn, which is a rule an author learns to ignore.
    """
    # The network itself comes from `_layout.network`, which `describe` also
    # prints, so the two cannot disagree about what is joined to what.
    ids = [p.ends[0] for p in placements
           if p.element == "node" and p.role == "node"]
    if len(ids) < 2:
        return
    groups = pieces(network(placements), ids)
    if len(groups) < 2:
        return

    for group in groups[1:]:
        named = ", ".join(f"{v!r}" for v in group)
        out.append(Finding(
            "network-in-pieces", "warning", f"node '{group[0]}'",
            f"nothing joins {named} to the rest of the network",
            remedy="connect it with a branch. If a `flow` or `flux` source is "
                   "standing in for a path that carries heat between two "
                   "nodes, it cannot join them: a source has one end",
            at=None))


def _corridor(scene, edges, rings, out):
    """A label sitting in the gap between two wires that go the same way.

    Correct in the sense that nothing overprints, and wrong in the sense that
    a reader cannot tell which path it belongs to. The label solver has no
    concept of a loop: it clears its own symbol, then avoids what is already
    placed, and the middle of a corridor satisfies both.

    The threshold is honest rather than tight, and here is the limit. The
    hero's capacitance label is inside the ladder's main loop with its owner on
    the boundary, and it is fine where it is — its nearest foreign edge is 94
    away against a label 33 tall. A pair of parallel paths 160 apart leaves 42,
    which is also not flagged. Four formulations were tried and every one that
    caught the loose pair also condemned the hero. `parallel-pair-same-side` is
    the threshold-free companion that catches the loose case.
    """
    for rect in scene.rects:
        centre, half = _rect_of(rect)
        bh = half[1] * 2
        for ring in rings:
            ring_edges = [_ekey(ring[i], ring[(i + 1) % len(ring)])
                          for i in range(len(ring))]
            refs = set().union(*(edges.get(e, set()) for e in ring_edges))
            if rect.ref not in refs or not _inside(centre, ring):
                continue
            foreign = [_segment_rect_gap(e[0], e[1], centre, half)
                       for e in ring_edges if rect.ref not in edges.get(e, ())]
            if not foreign or min(foreign) >= bh:
                continue
            out.append(Finding(
                "label-in-a-corridor", "warning", rect.ref or "a label",
                f"{rect.ref}: its label sits inside a loop of the network, "
                f"{min(foreign):.0f} from the opposite path and {bh:.0f} tall, "
                "so it reads as belonging to either",
                remedy="set `side` to send it outside the loop",
                at=centre))
            break


def _symbols_overlap(placements, out):
    """Two symbols sharing the same page space.

    Measured on the drawn body, not on `Symbol.ink`: the leads either side of a
    box are meant to run into the next symbol's leads, and reporting that would
    condemn every ladder in the library.
    """
    boxes = []
    for p in placements:
        if p.symbol is not None:
            boxes.append((p, p.at, (p.symbol.half_len, p.symbol.half), p.angle))
        elif p.element == "ground":
            boxes.append((p,) + _wall_box(p))
    for i, (pa, ca, ha, aa) in enumerate(boxes):
        for pb, cb, hb, ab in boxes[i + 1:]:
            if pa.ref is not None and pa.ref == pb.ref:
                continue
            clear = _obb_gap(ca, ha, aa, cb, hb, ab)
            if clear < -TOUCH:
                out.append(Finding(
                    "symbols-overlap", "error", pa.ref or "a symbol",
                    f"{_name(pa)} and {_name(pb)} overlap by "
                    f"{-clear:.0f}", remedy="move one of them with `at`",
                    at=tuple(ca)))


def _wire_through_symbol(placements, out):
    """A wire crossing a symbol it has nothing to do with.

    Deduped by segment first, and each segment carries every branch that
    routed along it: two branches sharing a trunk both emit it, and only one of
    them owns whatever symbol sits on it.
    """
    segs = defaultdict(set)
    for p in placements:
        if p.element != "wire":
            continue
        pts = [tuple(q) for q in p.points]
        for i in range(len(pts) - 1):
            segs[(pts[i], pts[i + 1])].add(p.ref)

    # One finding per (victim, offender), not per segment: a route crossing a
    # box usually does it with two of its segments, and saying so twice reads
    # as two problems.
    hits = {}
    for p in placements:
        if p.symbol is None:
            continue
        half = (max(0.0, p.symbol.half_len - SHAVE),
                max(0.0, p.symbol.half - SHAVE))
        for (a, b), refs in segs.items():
            if p.ref in refs:
                continue
            if not core.segment_box(a, b, p.at, half, p.angle):
                continue
            for other in sorted(str(r) for r in refs):
                hits.setdefault((str(p.ref), other), p)

    # Two branches laid across each other satisfy this twice, once each way,
    # and both are true: each one's wire really does cross the other's box.
    # They are one place on the page and one thing to fix, though, and moving
    # either branch clears both — so say it once, as a crossing rather than
    # as two trespasses.
    # The remedy names what the offending wire can actually do. A source's
    # lead and a repeated branch have no `via`; a straight run between two
    # nodes has none to move. "Route it around with `via`" was offered for
    # a source's lead, and the reader had to notice the source table has no
    # such field.
    wires = {}
    for p in placements:
        if p.element == "wire" and p.ref not in wires:
            wires[str(p.ref)] = p

    def reroute(ref):
        w = wires.get(ref)
        return _move(w, past="it") if w is not None else None

    def routable(ref):
        w = wires.get(ref)
        return (w is not None and _kind_of(w) == "branch"
                and not (w.count and w.count > 1))

    seen = set()
    for (victim, offender), p in sorted(hits.items()):
        if (offender, victim) in hits:
            pair = frozenset((victim, offender))
            if pair in seen:
                continue
            seen.add(pair)
            first, second = sorted(pair)
            if routable(first) and routable(second):
                moves = ["route either of them around with `via`, which "
                         "clears both"]
            else:
                moves = [m for m in (reroute(first), reroute(second)) if m]
            out.append(Finding(
                "wire-through-symbol", "warning", first,
                f"{first} and {second} cross each other, each one's wire "
                "running through the other's symbol",
                remedy=", or ".join(
                    moves + ["move one symbol along its branch with `at`"]),
                at=tuple(p.at)))
            continue
        symbol = (f"move {p.ref} with `at`" if _kind_of(p) == "source"
                  else "move the symbol along its branch with `at`")
        out.append(Finding(
            "wire-through-symbol", "warning", victim or "a symbol",
            f"{offender} runs straight through {_name(p)}",
            remedy=", or ".join(m for m in (reroute(offender), symbol) if m),
            at=tuple(p.at)))


def _frame(scene, padding, out):
    """Whether the drawing sits square in the canvas it was given.

    Unreachable unless a `size` was passed, because the measured path derives
    the canvas from the ink and cannot be off-centre by construction. That is
    the point: a caller who supplies dimensions is guessing, and this is what
    tells them the guess was wrong.
    """
    ix0, iy0, ix1, iy1 = scene.ink
    bx0, by0, bx1, by1 = scene.box
    over = {"left": bx0 - ix0, "right": ix1 - bx1,
            "top": by0 - iy0, "bottom": iy1 - by1}
    spill = {k: v for k, v in over.items() if v > TOUCH}
    if spill:
        out.append(Finding(
            "off-canvas", "error", "the canvas",
            "the drawing runs off the "
            + ", ".join(f"{k} by {v:.0f}" for k, v in sorted(spill.items())),
            remedy="drop `size` and let the canvas measure itself, "
                   "or make it larger"))
        return
    margins = {"left": ix0 - bx0, "right": bx1 - ix1,
               "top": iy0 - by0, "bottom": by1 - iy1}
    for a, b in (("left", "right"), ("top", "bottom")):
        if abs(margins[a] - margins[b]) > padding * FRAME_SLACK:
            out.append(Finding(
                "frame-off-centre", "warning", "the canvas",
                f"{margins[a]:.0f} of margin on the {a} against "
                f"{margins[b]:.0f} on the {b}",
                remedy="drop `size` and let the canvas measure itself"))


def _parallel_pairs(placements, scene, out):
    """Two branches between the same two nodes, labelled on the same side.

    Threshold-free, and a note rather than a warning on purpose: it fires on
    the hero's own convection/radiation pair, which is the published README
    image. A rule that condemns the flagship is a rule an author learns to
    ignore, and then ignores when it is right.

    It used to skip any pair where neither label was `auto`, on the reasoning
    that an explicit side is the author's decision. The effect was that
    setting `side` — which is exactly what this finding tells you to do —
    removed the pair from the check whether or not it had helped, so the
    documented remedy bought a clean report either way. A false clean is worse
    than a missing check, and a note is already something you are free to
    ignore. What matters is where the labels actually landed, not how.

    The remedy is derived from where the two labels landed and which branch
    is lower on the page, so it names the branch and the side. It used to be
    the fixed sentence "set `side` to down on the lower of the two", which a
    clean-room reader applied to a pair that already had `"side": "down"` on
    both and watched the note survive. Three or more branches between one
    pair of nodes get one note for the group, and no `side` at all: a run
    has two label sides, so two of three must share one, and the old remedy
    only rotated which pair was reported — two readers each proved the
    two-state cycle before leaving the note standing.
    """
    by_rect = {id(r.owner): r for r in scene.rects}   # Placement is unhashable
    pairs = defaultdict(list)
    for p in placements:
        if p.symbol is None or p.role != "branch":
            continue
        pairs[frozenset(p.ends)].append(p)

    for group in pairs.values():
        labelled = [(p, by_rect.get(id(p))) for p in group]
        labelled = [(p, r) for p, r in labelled if r is not None]
        sides = [r.side for _, r in labelled]
        if len(labelled) < 2 or len(set(sides)) == len(sides):
            continue
        if len(labelled) > 2:
            refs = ", ".join(p.ref for p, _ in labelled)
            out.append(Finding(
                "parallel-pair-same-side", "note", labelled[0][0].ref,
                f"{refs} run between the same two nodes, and a run has two "
                "label sides, so two of them share one",
                remedy="put the branch with the narrowest label on the "
                       "shared side; no `side` clears this, and the note is "
                       "safe to leave",
                at=tuple(labelled[0][0].at)))
            continue
        (pa, ra), (pb, rb) = labelled
        sx, sy = ra.side
        if abs(sy) >= abs(sx):
            lower = max((pa, pb), key=lambda p: p.at[1])
            upper = min((pa, pb), key=lambda p: p.at[1])
            who, new = (lower, "down") if sy < 0 else (upper, "up")
        else:
            right = max((pa, pb), key=lambda p: p.at[0])
            left = min((pa, pb), key=lambda p: p.at[0])
            who, new = (right, "right") if sx < 0 else (left, "left")
        out.append(Finding(
            "parallel-pair-same-side", "note", pa.ref,
            f"{pa.ref} and {pb.ref} run between the same two nodes "
            "and both labels went to the same side",
            remedy=f'set `side` to "{new}" on {who.ref}',
            at=tuple(pa.at)))


# -------------------------------------------------------------------- the API
def _placements(diagram):
    if isinstance(diagram, (list, tuple)):
        return list(diagram)
    if hasattr(diagram, "build"):                       # a DiagramBuilder
        diagram = diagram.build()
    return _layout(diagram)


def check(diagram, size=None, padding=PADDING, source="diagram",
          physics=False):
    """Everything wrong with this diagram, as a `Report`.

    Takes a `Diagram`, a `DiagramBuilder`, or a list of `Placement`. `size`
    defaults to the diagram's own, so what is checked is what `.svg()` draws.

    `physics` adds the prototype in `_physics`: whether the stated numbers
    close at each node. Off by default while it is being judged on real
    diagrams; it needs the diagram, so a list of placements cannot ask for it.
    """
    if size is None:
        size = getattr(diagram, "size", None) or \
            getattr(getattr(diagram, "diagram", None), "size", None)
    if physics and isinstance(diagram, (list, tuple)):
        raise ValueError("physics=True needs a Diagram, not placements: the "
                         "numbers are on the diagram")
    model = diagram.build() if hasattr(diagram, "build") else diagram
    placements = _placements(diagram)
    scene = compose(placements, size, padding)

    findings = []
    _collisions(scene, findings)
    _adrift(scene, placements, findings)
    _crowded_run(scene, placements, findings)
    _islands(placements, findings)
    edges = wire_graph(placements)
    _corridor(scene, edges, cycles(edges), findings)
    _symbols_overlap(placements, findings)
    _wire_through_symbol(placements, findings)
    _frame(scene, padding, findings)
    _parallel_pairs(placements, scene, findings)
    if physics:
        from ._physics import balance          # imports Finding from here
        findings += balance(model)

    findings.sort(key=lambda f: (ORDER[f.severity], f.code, f.where or ""))
    return Report(findings=findings, labels=len(scene.rects), source=source)
