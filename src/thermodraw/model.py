"""A diagram as data.

This is the thing you write, an LLM emits, and a human edits. It carries no
geometry beyond the coordinates you give it, and no SVG at all: `layout` turns
it into placements and `render` turns those into a document.

The split matters for what comes next. Today `layout` reads the `at`
coordinates you supply. The network layer, when it lands, computes the ones
you leave out. The schema does not change; only that one stage gains a solver.

Every `kind` is a key from `symbols.SYMBOLS`, so the vocabulary and the schema
are the same list. See docs/schema.md.
"""
import difflib
import json
import math
from dataclasses import MISSING as _MISSING
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Sequence, Union

NODE_KINDS = {"free", "fixed", "break", "phase"}
# Kinds that existed and were removed, and what to write instead. A file
# from before the removal gets the reason and the replacement, not "unknown
# kind" beside a list it used to be on.
RETIRED_KINDS = {
    "corner": "removed in 1.0. Route the branch with `via` waypoints, or "
              "make the junction a `free` node with a `sub` and no `value` "
              "so that it has a name and states no temperature",
}
BRANCH_KINDS = {"cond", "conv", "rad", "contact", "cap", "break",
                "flow", "spread", "pipe", "mixed"}

# A branch whose quantity is a rate rather than a resistance, so which end
# is `from` and which is `to` is the direction heat travels. `angle` is
# refused on one: on a branch it overrides the direction taken from the
# wire, which would let the drawing contradict the data.
DIRECTED_KINDS = {"flow"}

# How several identical paths combine. Never inferred: eight 0.0275 K/W
# paths are 0.0034 in parallel and 0.22 in series, a factor of 64, so a
# `count` without an `arrangement` is a wrong answer waiting to be read.
ARRANGEMENTS = ("parallel", "series")

# Above this many, a repeated group draws two and an ellipsis rather than
# all of them. Three or fewer fit without crowding and read better drawn.
CONDENSE_ABOVE = 3
SOURCE_KINDS = {"diss", "radin", "flow", "flux"}

# A source written with `from` points away from its node instead of into it.
# Only `flow` and `flux` may, the two that annotate heat crossing a boundary:
# `diss` is dissipation appearing at a node and does not go anywhere, and
# `radin` is radiation *arriving*, so an outbound one would be a symbol whose
# own name contradicts it.
OUTWARD_KINDS = {"flow", "flux"}

# A subscript on an R is structural: the library sets it and it names the
# mechanism. A subscript on a C, T, P or q is identity, and the caller sets
# it. None here means "ask the branch", which is how that asymmetry is kept.
BRANCH_SUB = {"cond": "cond", "conv": "conv", "rad": "rad",
              "contact": "contact", "cap": None, "break": None,
              "flow": None, "spread": "spread", "pipe": "pipe",
              # `mixed` is the one kind whose mechanism the library does
              # not know, so its subscript is the caller's to set.
              "mixed": None}
# None means the branch names no quantity at all: a thermal break has neither
# a resistance nor a capacitance, so it carries the user's label and nothing
# else. `layout` drops the second line rather than inventing a symbol for it.
BRANCH_SYMBOL = {"cond": "R", "conv": "R", "rad": "R", "contact": "R",
                 "cap": "C", "break": None, "flow": "q",
                 "spread": "R", "pipe": "R", "mixed": "R"}
SOURCE_SYMBOL = {"diss": "P", "radin": "q", "flow": "q", "flux": "q″"}

# Which quantity each kind is measured in, so one units entry serves many.
# Each quantity is its own symbol, `q″` included: flux is per unit area, so it
# is not measured in the same thing as a heat flow and must not share the
# entry. `radin` and `flow` are both powers and do share `q`.
QUANTITY = {"cond": "R", "conv": "R", "rad": "R", "contact": "R", "cap": "C",
            "spread": "R", "pipe": "R", "mixed": "R",
            "free": "T", "fixed": "T", "break": "T", "phase": "T",
            "diss": "P", "radin": "q", "flow": "q", "flux": "q″"}

# What a `rate` on a resistance is measured in. It is a heat rate whatever
# the path's own quantity is, which is the whole point of the field.
RATE = "q"

RAIL = "rail"


class DiagramError(ValueError):
    """Raised for a diagram that cannot be laid out, with the reason."""


def _fmt(value):
    """Numbers become text without inventing a precision they do not have."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return f"{value:g}"


# How a group of `count` identical paths folds into one number.
#
# It is deliberately a table and not a formula, because it is not one rule.
# Resistances in parallel divide and in series multiply; a capacitance is the
# exact dual, adding in parallel and dividing in series. Writing this as one
# expression with a sign flip is how it gets got backwards later, and a
# confidently wrong number on a drawing is worse than no number at all --
# which is the argument the original "the library does no arithmetic"
# decision was making. `q` is absent on purpose: `flow` already carries a
# rate, and what several of them come to depends on what they are.
FOLD = {
    "R": {"parallel": lambda v, n: v / n, "series": lambda v, n: v * n},
    "C": {"parallel": lambda v, n: v * n, "series": lambda v, n: v / n},
    # A rate is not a resistance and folds like neither. Four pumped loops
    # side by side carry four times the heat; four in a chain carry the same
    # heat through each link, so the group carries one loop's worth. This
    # entry is also what `--physics` reads: the checker used the per-item
    # rate raw and reported four correct 10 W loops into a 40 W sink as a
    # node that does not balance, which is a false alarm on a right answer.
    "q": {"parallel": lambda v, n: v * n, "series": lambda v, n: v},
}


def _sig(x, digits=4):
    """A derived number, to a fixed number of significant figures.

    `_fmt` exists to avoid inventing precision for a value the author typed.
    This is the opposite case: nobody typed 0.0034375, the library divided it
    out, and printing every digit of a float would say more than the input
    supports.
    """
    text = f"{x:.{digits}g}"
    return text


# ------------------------------------------------------------------ typing
# The point of validate() is that a diagram which cannot be drawn says so
# before anything tries to draw it. Checking ids and kinds but not the shape
# of a coordinate left seven ways to write a bad `at`: six died deep in the
# renderer with messages like "Unknown format code 'f' for object of type
# 'str'", naming no node and no field, and one drew the wrong picture in
# silence. These are cheap and they run first.
def _number(value, where, name):
    # bool is an int in Python, and an angle of True is not an angle. `nan`
    # and `inf` are floats, and a `nan` coordinate rendered `width="nan"` — a
    # blank document, the seventh silent way to write a bad `at`.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagramError(
            f"{where}: {name} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise DiagramError(
            f"{where}: {name} must be a finite number, got {value!r}")
    return value


def _point(value, where, name):
    if not isinstance(value, (list, tuple)):
        raise DiagramError(
            f"{where}: {name} must be a pair of numbers like [200, 150], "
            f"got {value!r}")
    if len(value) != 2:
        raise DiagramError(
            f"{where}: {name} needs exactly two numbers, got {len(value)} "
            f"in {value!r}")
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise DiagramError(
                f"{where}: {name} must be numbers, got {item!r} in {value!r}")
        if not math.isfinite(item):
            raise DiagramError(
                f"{where}: {name} must be finite numbers, got {item!r} "
                f"in {value!r}")
    return value


def _text(value, where, name):
    if value is not None and not isinstance(value, str):
        raise DiagramError(
            f"{where}: {name} must be text, got {value!r}")
    return value


def _value(value, where, name="value"):
    if value is not None and not isinstance(value, (str, int, float)):
        raise DiagramError(
            f"{where}: {name} must be a number or text, got {value!r}")
    # `json` accepts NaN and Infinity by default, and `_number` already
    # refuses them for coordinates. A value reached `_fmt`, which calls
    # `int(nan)`, and died as a ValueError with no element named.
    if isinstance(value, float) and not math.isfinite(value):
        raise DiagramError(
            f"{where}: {name} must be a finite number, got {value!r}")
    return value


# core.annotate has taken an explicit side since the occupancy work, and
# CLAUDE.md documents it as the override for the automatic choice. It was
# reachable from Python and from nowhere else: the model carried no field for
# it, so a diagram written as data could not say where its own label goes.
SIDES = ("auto", "up", "down", "left", "right")

# Which way a boundary node's wall faces. `down` is what every diagram
# before 1.0 drew, at every orientation, and it could not be turned: a mount
# that holds a cold mass from above had its hatching between itself and the
# strut, and the third clean-room run shipped the wrong arrangement because
# the honest one could not be checked. The two kinds that draw a wall take
# it; a free or phase node has no wall to turn and is refused.
WALLS = ("down", "up", "left", "right")
BOUNDARY_KINDS = {"fixed", "break"}

# What `units.T` may declare about its scale. `K` is byte-identical whether
# the author means absolute kelvin or a rise above ambient, and nothing in
# the drawing tells them apart; the declaration is the only place the
# difference can be stated, and `--physics` is the only reader that cares.
SCALES = ("absolute", "rise")


def _count(value, where):
    if isinstance(value, bool) or not isinstance(value, int):
        raise DiagramError(
            f"{where}: count must be a whole number, got {value!r}")
    if value < 1:
        raise DiagramError(f"{where}: count must be 1 or more, got {value}")
    return value


def _side(value, where):
    if value not in SIDES:
        raise DiagramError(
            f"{where}: side must be one of " + ", ".join(map(repr, SIDES))
            + f", got {value!r}")
    return value


def _wall(value, kind, where):
    if value not in WALLS:
        raise DiagramError(
            f"{where}: wall must be one of " + ", ".join(map(repr, WALLS))
            + f", got {value!r}")
    if value != "down" and kind not in BOUNDARY_KINDS:
        raise DiagramError(
            f"{where}: a `{kind}` node has no wall to turn; `wall` is for "
            + " and ".join(f"`{k}`" for k in sorted(BOUNDARY_KINDS)))
    return value


# Near-misses that difflib cannot see, because they are wrong by meaning
# rather than by spelling. These are the ones a model actually writes.
HINTS = {"name": "label", "text": "label", "title": "label",
         "type": "kind", "symbol": "kind",
         "position": "at", "pos": "at", "xy": "at", "coords": "at",
         "coordinates": "at", "point": "at", "location": "at",
         "subscript": "sub", "suffix": "sub",
         "magnitude": "value", "amount": "value", "quantity": "value",
         "source": "from", "target": "to", "start": "from", "end": "to",
         "waypoints": "via", "route": "via", "path": "via",
         "node": "nodes", "branch": "branches", "unit": "units"}


def _suggest(key, offered):
    hint = HINTS.get(key)
    if hint and hint in offered:
        return hint
    near = difflib.get_close_matches(key, offered, n=1, cutoff=0.6)
    return near[0] if near else None


def _build(cls, data, where, mapping=None):
    """Construct a dataclass from a dict, saying what is wrong with the dict.

    An unknown key used to surface as `Node.__init__() got an unexpected
    keyword argument 'name'` — a Python-internal message, the wrong exception
    type, and no hint. Near-miss keys are the likeliest thing to arrive from
    a model writing JSON, so they get the best error in the library.
    """
    if not isinstance(data, dict):
        raise DiagramError(f"{where}: expected an object, got {data!r}")
    mapping = mapping or {}
    back = {v: k for k, v in mapping.items()}
    renamed = {mapping.get(k, k): v for k, v in data.items()}
    known = {f.name for f in fields(cls)}
    offered = sorted(back.get(name, name) for name in known)

    unknown = [key for key in renamed if key not in known]
    if unknown:
        said = []
        for key in unknown:
            shown = back.get(key, key)
            near = _suggest(shown, offered)
            said.append(f"{shown!r}" +
                        (f" (did you mean {near!r}?)" if near else ""))
        raise DiagramError(f"{where}: unknown field {', '.join(said)}. "
                           f"Expected: {', '.join(offered)}")
    try:
        return cls(**renamed)
    except TypeError as exc:
        missing = sorted(
            back.get(f.name, f.name) for f in fields(cls)
            if f.default is _MISSING and f.default_factory is _MISSING
            and f.name not in renamed)
        if missing:
            raise DiagramError(
                f"{where}: missing required field "
                f"{', '.join(repr(m) for m in missing)}") from None
        raise DiagramError(f"{where}: {exc}") from None


@dataclass
class Node:
    id: str
    kind: str = "free"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    at: Optional[Sequence[float]] = None
    angle: float = 0.0
    side: str = "auto"
    wall: str = "down"                      # `fixed` and `break` only


@dataclass
class Branch:
    """A path heat takes between two nodes.

    `rate` is what this path actually carries, beside the resistance it
    presents. A cryostat heat-load budget is a list of exactly those numbers,
    and without the field they end up inside the free-text label, reading as
    part of the path's name and bypassing the units table.

    `count` with `arrangement` says there are several identical ones. Both or
    neither: eight 0.0275 K/W paths are 0.0034 in parallel and 0.22 in
    series, so an unstated arrangement is a wrong answer waiting to be read.
    """

    source: str
    target: str
    kind: str = "cond"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    rate: Union[str, float, None] = None
    count: Optional[int] = None
    arrangement: Optional[str] = None
    via: List[Sequence[float]] = field(default_factory=list)
    at: Optional[Sequence[float]] = None
    angle: Optional[float] = None
    side: str = "auto"

    @property
    def repeated(self):
        return bool(self.count and self.count > 1)

    @property
    def condensed(self):
        """Two and an ellipsis, rather than all of them."""
        return bool(self.count and self.count > CONDENSE_ABOVE)


@dataclass
class Source:
    """Heat crossing into or out of a node.

    `to` is heat arriving and `from` is heat leaving, exactly as on a branch,
    and one of them is required. The direction is which end of the arrow the
    lead attaches to and nothing else: every source glyph draws its tail at
    -half_len and its head at +half_len, so the same drawing serves both. On
    `flux` that is what makes it work — the hatch band is a surface, so
    attaching the tail puts the surface against the node with the arrows
    leaving it.

    `target` stays first and keeps its default-free position, so
    `Source("j", "diss")` still means what it always did.
    """

    target: Optional[str] = None
    kind: str = "diss"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    at: Optional[Sequence[float]] = None
    angle: float = 0.0
    side: str = "auto"
    count: Optional[int] = None             # several identical ones; they add
    source: Optional[str] = None            # `from`: heat leaving that node

    @property
    def outward(self):
        return self.source is not None

    @property
    def node(self):
        """The node this attaches to, whichever end it was written as."""
        return self.source if self.outward else self.target


@dataclass
class Rail:
    reference: str
    y: float
    span: Optional[Sequence[float]] = None


@dataclass
class Diagram:
    nodes: List[Node] = field(default_factory=list)
    branches: List[Branch] = field(default_factory=list)
    sources: List[Source] = field(default_factory=list)
    rail: Optional[Rail] = None
    units: Dict[str, str] = field(default_factory=dict)
    size: Optional[Sequence[float]] = None
    title: Optional[str] = None
    # What `units.T` is on: "absolute", "rise", or None for undeclared. It
    # is written in the file as `"T": {"unit": "K", "scale": "rise"}` and
    # split out here, so every reader of `units` sees text as it always has.
    scale: Optional[str] = None

    def node(self, node_id):
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise DiagramError(f"no node named {node_id!r}")

    def unit(self, kind):
        return self.units.get(QUANTITY.get(kind, ""), "")

    def rate_text(self, value):
        """A heat rate with its unit, or None. Always in `units.q`.

        The number and unit only. `layout` pairs it with `RATE` so it is
        drawn `q = 12 W`, because a bare quantity under a resistance is an
        unexplained second number.
        """
        text = _fmt(value)
        if text is None:
            return None
        return f"{text} {self.units.get(RATE, '')}".strip()

    def fold(self, kind, value, count, arrangement):
        """What a group of `count` of these comes to, as a number.

        None where the group has no single number: a `flow` carries a rate
        and a `break` carries nothing, and a value that is not numeric stays
        as the author typed it.
        """
        rule = FOLD.get(QUANTITY.get(kind, ""), {}).get(arrangement)
        if rule is None or count is None or count <= 1:
            return None
        try:
            number = float(str(value).strip())
        except (TypeError, ValueError, AttributeError):
            return None
        return rule(number, count)

    def effective_text(self, kind, value, count, arrangement):
        """The group's own value with its unit, or None."""
        folded = self.fold(kind, value, count, arrangement)
        if folded is None:
            return None
        return f"{_sig(folded)} {self.unit(kind)}".strip()

    def count_text(self, count, arrangement, kind=None, value=None):
        """How many, how they combine, and what they come to together.

        The last part is new, and it overturns "the library does no
        arithmetic". A group used to render `R_cond = 1.6 K/W | 4 in
        parallel` and never show the 0.4 K/W it actually presents, so a
        reader checking the page got 6.25 W where the answer was 25 W. The
        stored value stays exactly the digits the author typed; this is a
        second, derived number, and it is labelled as one by sitting after
        the arrangement rather than replacing the per-item value.
        """
        if not count or count <= 1:
            return None
        base = (f"{count} in series" if arrangement == "series"
                else f"{count} in parallel")
        effective = self.effective_text(kind, value, count, arrangement)
        return f"{base} = {effective}" if effective else base

    def source_count_text(self, count, kind=None, value=None):
        """How many of a source there are. They add; there is no arrangement.

        It borrowed the branch wording and said "8 in parallel" of eight
        processors, which is a statement about circuits, not about eight
        things that each dissipate 400 W. The value is per item, as it is on
        a branch, and this says so — and now says what they come to, since
        adding eight of them is the arithmetic a reader was left to do.
        """
        if not count or count <= 1:
            return None
        base = f"each of {count}"
        try:
            total = float(str(value).strip()) * count
        except (TypeError, ValueError, AttributeError):
            return base
        # No trailing "total": it says nothing the `=` has not, and the four
        # characters were the difference between the immersion rack checking
        # clean and its junction label being pushed 96 past its clearance.
        # The shape now matches a branch group's, `8 in parallel = 0.4 K/W`.
        return f"{base} = {_sig(total)} {self.unit(kind)}".strip()

    def value_text(self, kind, value):
        text = _fmt(value)
        if text is None:
            return None
        unit = self.unit(kind)
        return f"{text} {unit}".strip()

    def _validate_top(self):
        """The fields that are not on any element.

        Everything inside a node, a branch, a source or the rail was checked
        and these were not, so `"size": "big"` reached `_render.extent` and
        died as `could not convert string to float: 'b'`, `"nodes": 5` died
        as `'int' object is not iterable`, and both exited 1 — the code the
        command line documents as *findings*. A script gating on the exit
        status read a crash as a diagram with warnings. `"units": "K/W"`
        was worse: `dict("K/W")` raises ValueError, which `__main__` reports
        as "is not valid JSON" about a file whose JSON was perfectly good.
        """
        _text(self.title, "the diagram", "title")
        if self.size is not None:
            if (isinstance(self.size, (str, bytes))
                    or not isinstance(self.size, Sequence)
                    or len(self.size) != 2):
                raise DiagramError(
                    f"the diagram: size must be [width, height], got "
                    f"{self.size!r}")
            for i, n in enumerate(self.size):
                _number(n, "the diagram", f"size[{i}]")
            if not all(n > 0 for n in self.size):
                raise DiagramError(
                    f"the diagram: size must be positive, got {self.size!r}")
        if not isinstance(self.units, dict):
            raise DiagramError(
                f"the diagram: units must be an object of quantity to unit, "
                f"got {self.units!r}")
        for quantity, unit in self.units.items():
            if not isinstance(unit, str):
                raise DiagramError(
                    f"the diagram: the unit for {quantity!r} must be text, "
                    f"got {unit!r}")
        if self.scale is not None:
            if self.scale not in SCALES:
                raise DiagramError(
                    "the diagram: units.T scale must be one of "
                    + ", ".join(map(repr, SCALES)) + f", got {self.scale!r}")
            if "T" not in self.units:
                raise DiagramError(
                    "the diagram: a temperature scale was declared and "
                    "units has no entry for 'T' to put it on")
        for name in ("nodes", "branches", "sources"):
            got = getattr(self, name)
            if isinstance(got, (str, bytes)) or not isinstance(got, Sequence):
                raise DiagramError(
                    f"the diagram: {name} must be a list, got {got!r}")

    def validate(self):
        """Every reason a diagram cannot be drawn, reported before drawing."""
        self._validate_top()
        seen = set()
        for n in self.nodes:
            # The id is the one string other things point at, so it is
            # checked before anything can. Nothing constrains what it contains
            # beyond these two: no code parses an id back out of a string, so
            # `hot side` and `o'clock` are fine ids.
            if not isinstance(n.id, str) or not n.id:
                raise DiagramError(
                    f"node {n.id!r}: id must be non-empty text")
            if n.id == RAIL:
                raise DiagramError(
                    f"node {n.id!r}: {RAIL!r} names the reference rail, which "
                    "a branch may join as an endpoint, so a node cannot take "
                    "it. Give the node another id")
            if n.id in seen:
                raise DiagramError(f"duplicate node id {n.id!r}")
            seen.add(n.id)
            if n.kind not in NODE_KINDS:
                gone = RETIRED_KINDS.get(n.kind)
                raise DiagramError(
                    f"node {n.id!r}: unknown kind {n.kind!r}; expected one of "
                    + ", ".join(sorted(NODE_KINDS))
                    + (f". `{n.kind}` was {gone}" if gone else ""))
            if n.at is None:
                raise DiagramError(
                    f"node {n.id!r} has no coordinates. Every node needs `at` "
                    "for now; solving for the ones you leave out is the "
                    "network layer, which is not built yet.")
            where = f"node {n.id!r}"
            _point(n.at, where, "at")
            _number(n.angle, where, "angle")
            _text(n.label, where, "label")
            _text(n.sub, where, "sub")
            _value(n.value, where)
            _side(n.side, where)
            _wall(n.wall, n.kind, where)
        if self.rail:
            if self.rail.reference not in seen:
                raise DiagramError(
                    f"rail references unknown node {self.rail.reference!r}")
            _number(self.rail.y, "rail", "y")
            if self.rail.span is not None:
                _point(self.rail.span, "rail", "span")
        for b in self.branches:
            if b.kind not in BRANCH_KINDS:
                raise DiagramError(
                    f"branch {b.source}-{b.target}: unknown kind {b.kind!r}; "
                    "expected one of " + ", ".join(sorted(BRANCH_KINDS)))
            # Said here rather than left to the units check below. A break
            # carries no heat, so it has no quantity to be measured in, and
            # `QUANTITY` only holds "break" for the *node* kind — one
            # namespace, two positions. Without this the author gets "units
            # has no entry for 'T'" about a branch, which explains nothing.
            # `angle` on a branch overrides the direction taken from the
            # wire, which for a directed kind would let the arrow contradict
            # `from` and `to`. The drawing must not be able to disagree with
            # the data, so this is refused rather than silently preferred.
            if b.kind in DIRECTED_KINDS and b.angle is not None:
                raise DiagramError(
                    f"branch {b.source}-{b.target}: {b.kind!r} carries heat "
                    "from one end to the other, so its direction is `from` "
                    "and `to`. `angle` would turn the symbol against them; "
                    "route it with `via` instead")
            if b.count is not None:
                _count(b.count, f"branch {b.source}-{b.target}")
                if b.count > 1 and b.via:
                    raise DiagramError(
                        f"branch {b.source}-{b.target}: a repeated branch is "
                        "drawn as a fan between its two nodes, so it cannot "
                        "also take `via`. Drop one or the other")
                if b.count > 1 and b.arrangement not in ARRANGEMENTS:
                    raise DiagramError(
                        f"branch {b.source}-{b.target}: count {b.count} needs "
                        "an arrangement of " + " or ".join(
                            repr(a) for a in ARRANGEMENTS)
                        + ". Identical paths combine differently in each, so "
                          "it cannot be left unstated")
            elif b.arrangement is not None:
                raise DiagramError(
                    f"branch {b.source}-{b.target}: arrangement "
                    f"{b.arrangement!r} without a count says nothing")
            if b.kind == "break" and b.rate is not None:
                raise DiagramError(
                    f"branch {b.source}-{b.target} is a break, which carries "
                    f"no heat and so no rate; got {b.rate!r}")
            # The other end of the same rule. A `rate` is what a path carries
            # beside the quantity it presents, so a path that already presents
            # a rate has nothing to put beside. `flow` states `q` as its own
            # value, and a second one drew `q = 5 W` twice. Derived from the
            # tables rather than naming the kind, so a second rate-valued kind
            # is covered the day it is added.
            if QUANTITY.get(b.kind) == RATE and b.rate is not None:
                raise DiagramError(
                    f"branch {b.source}-{b.target} is a {b.kind}, whose value "
                    f"is already a rate in {RATE!r}; got a second one "
                    f"{b.rate!r}. Put the number in `value`")
            if b.rate is not None:
                _value(b.rate, f"branch {b.source}-{b.target}")
                if not self.units.get(RATE):
                    raise DiagramError(
                        f"branch {b.source}-{b.target} has the rate "
                        f"{b.rate!r} but units has no entry for {RATE!r}, so "
                        "it would render bare")
            if b.kind == "break" and b.value is not None:
                raise DiagramError(
                    f"branch {b.source}-{b.target} is a break, which carries "
                    f"no heat and so no value; got {b.value!r}")
            # A branch is a path between two places. Named the same place
            # twice it validated, laid out, rendered and checked clean while
            # drawing a stub that leaves a node and returns to it; `rail` to
            # `rail` did the same along the reference line. Neither is
            # anything an author meant, and both are easy for a model
            # emitting JSON to write.
            if b.source == b.target:
                raise DiagramError(
                    f"branch {b.source}-{b.target}: a branch joins two "
                    f"places and this names {b.source!r} twice. For heat "
                    "leaving a node and not arriving anywhere, use a source "
                    "with `from`")
            for end in (b.source, b.target):
                if end == RAIL:
                    if not self.rail:
                        raise DiagramError(
                            f"branch {b.source}-{b.target} joins the rail, "
                            "but the diagram has no rail")
                elif end not in seen:
                    raise DiagramError(
                        f"branch {b.source}-{b.target}: no node named {end!r}")
            where = f"branch {b.source}-{b.target}"
            if not isinstance(b.via, (list, tuple)):
                raise DiagramError(
                    f"{where}: via must be a list of points like "
                    f"[[696, 150], [696, 70]], got {b.via!r}")
            for i, point in enumerate(b.via):
                _point(point, where, f"via[{i}]")
            if b.at is not None:
                _point(b.at, where, "at")
            if b.angle is not None:
                _number(b.angle, where, "angle")
            _text(b.label, where, "label")
            _text(b.sub, where, "sub")
            _value(b.value, where)
            _side(b.side, where)
        known = set(QUANTITY.values())
        for quantity in self.units:
            if quantity not in known:
                raise DiagramError(
                    f"units names {quantity!r}, which is not a quantity here; "
                    "expected one of " + ", ".join(sorted(known)))
        # Before the value check below, not with the rest of the source
        # checks after it: `_valued()` yields sources, so an unknown kind
        # reached `QUANTITY[kind]` and raised a bare KeyError instead of
        # saying which kinds exist. Nodes and branches validate their kinds
        # further up, which is why only sources were exposed.
        for i, s in enumerate(self.sources):
            # Both ends, or neither, before anything reads `s.node` — which
            # `_valued()` does two loops down. `_build` cannot catch this:
            # each field has a default, so a source with no endpoint at all
            # constructs cleanly and only fails much later.
            if s.source is not None and s.target is not None:
                raise DiagramError(
                    f"source {i}: give `from` or `to`, not both. `to` is heat "
                    f"arriving at {s.target!r}; `from` is heat leaving "
                    f"{s.source!r}")
            if s.node is None:
                raise DiagramError(
                    f"source {i}: needs `to` for heat arriving at a node, or "
                    "`from` for heat leaving one")
            if s.kind not in SOURCE_KINDS:
                raise DiagramError(
                    f"source at {s.node}: unknown kind {s.kind!r}; expected "
                    "one of " + ", ".join(sorted(SOURCE_KINDS)))
            if s.outward and s.kind not in OUTWARD_KINDS:
                raise DiagramError(
                    f"source at {s.node}: {s.kind!r} points into a node and "
                    "cannot be written with `from`. "
                    + ("dissipation appears at a node rather than travelling "
                       "to it" if s.kind == "diss" else
                       "`radin` is radiation arriving; for radiation leaving, "
                       "draw a `rad` branch to a boundary node")
                    + ". For heat leaving, use `flow` or `flux`")
            # A branch's `count` goes through `_count`; a source's went
            # through nothing, so `count: 0` drew one and `count: "many"`
            # died in `layout` with a TypeError naming no source.
            if s.count is not None:
                _count(s.count, f"source {i}")
        # Units are fixed per diagram and given once per quantity, so they
        # cannot be mixed. What can still go wrong is a value with no unit
        # at all, which renders as a bare number.
        for owner, kind, value in self._valued():
            if value is not None and not self.unit(kind):
                raise DiagramError(
                    f"{owner} has the value {value!r} but units has no entry "
                    f"for {QUANTITY[kind]!r}, so it would render bare")
        for s in self.sources:
            if s.node not in seen:
                raise DiagramError(f"source: no node named {s.node!r}")
            where = f"source at {s.node}"
            if s.at is not None:
                _point(s.at, where, "at")
            _number(s.angle, where, "angle")
            _text(s.label, where, "label")
            _text(s.sub, where, "sub")
            _value(s.value, where)
            _side(s.side, where)
        return self

    def _valued(self):
        for n in self.nodes:
            yield f"node {n.id!r}", n.kind, n.value
        for b in self.branches:
            yield f"branch {b.source}-{b.target}", b.kind, b.value
        for s in self.sources:
            yield f"source at {s.node}", s.kind, s.value

    def to_dict(self):
        """JSON-shaped, using from/to rather than the Python-safe names."""
        out: Dict[str, Any] = {}
        if self.title:
            out["title"] = self.title
        if self.units:
            out["units"] = dict(self.units)
            if self.scale:
                out["units"]["T"] = {"unit": self.units["T"],
                                     "scale": self.scale}
        if self.size:
            out["size"] = list(self.size)
        out["nodes"] = [_node_dict(n) for n in self.nodes]
        if self.branches:
            out["branches"] = [_branch_dict(b) for b in self.branches]
        if self.sources:
            out["sources"] = [_source_dict(s) for s in self.sources]
        if self.rail:
            out["rail"] = _rail_dict(self.rail)
        return out

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise DiagramError(f"a diagram is an object, got {data!r}")
        extra = sorted(set(data) - {"title", "units", "size", "nodes",
                                    "branches", "sources", "rail"})
        if extra:
            top = ["title", "units", "size", "nodes", "branches",
                   "sources", "rail"]
            said = []
            for key in extra:
                near = _suggest(key, top)
                said.append(f"{key!r}" +
                            (f" (did you mean {near!r}?)" if near else ""))
            raise DiagramError(
                f"unknown top-level field {', '.join(said)}. Expected: "
                "title, units, size, nodes, branches, sources, rail")
        # These are checked here rather than in `validate` because `from_dict`
        # reads them first: a non-list `nodes` died in this comprehension and
        # a non-object `units` died in the `dict()` below, both before
        # anything could name the field.
        for name in ("nodes", "branches", "sources"):
            got = data.get(name, [])
            if isinstance(got, (str, bytes)) or not isinstance(got, list):
                raise DiagramError(
                    f"the diagram: {name} must be a list, got {got!r}")
        if not isinstance(data.get("units", {}), dict):
            raise DiagramError(
                "the diagram: units must be an object of quantity to unit, "
                f"got {data['units']!r}")
        units = dict(data.get("units", {}))
        scale = None
        # `"T": {"unit": "K", "scale": "rise"}` is the one unit that may
        # say more than its name. It is split here so the rest of the
        # library reads `units["T"]` as the text it always was.
        if isinstance(units.get("T"), dict):
            said = units["T"]
            extra = sorted(set(said) - {"unit", "scale"})
            if extra or "unit" not in said:
                raise DiagramError(
                    "the diagram: units.T as an object takes `unit` and "
                    f"`scale`, got {said!r}")
            units["T"], scale = said["unit"], said.get("scale")
        if "rail" in data and data["rail"] is not None                 and not isinstance(data["rail"], dict):
            raise DiagramError(
                f"the diagram: rail must be an object, got {data['rail']!r}")
        nodes = [_build(Node, n, f"node {i}")
                 for i, n in enumerate(data.get("nodes", []))]
        branches = [_build(Branch, b, f"branch {i}",
                           {"from": "source", "to": "target"})
                    for i, b in enumerate(data.get("branches", []))]
        sources = [_build(Source, s, f"source {i}",
                          {"to": "target", "from": "source"})
                   for i, s in enumerate(data.get("sources", []))]
        rail = _build(Rail, data["rail"], "rail") if data.get("rail") else None
        return cls(nodes=nodes, branches=branches, sources=sources, rail=rail,
                   units=units, scale=scale,
                   size=data.get("size"), title=data.get("title")).validate()

    def to_json(self, **kw):
        kw.setdefault("indent", 2)
        kw.setdefault("ensure_ascii", False)
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))


def _default(cls, name):
    """What this field is when the author did not set it."""
    for f in fields(cls):
        if f.name != name:
            continue
        if f.default is not _MISSING:
            return f.default
        if f.default_factory is not _MISSING:
            return f.default_factory()
    return _MISSING


def _keep(out, obj, names):
    """Every field the author set, and none they did not.

    This used to skip anything falsy — `value in (None, "", [], ()) or
    value == 0.0`. Two of those are wrong. A node at 0 °C has a temperature,
    and a branch with `angle: 0` is saying "draw it flat whatever the wire
    does", which is not the same as saying nothing; both came back absent.
    What "did not set it" actually looks like is the field still holding its
    own default, so that is what is skipped.

    `Branch.angle` defaults to None precisely so that 0 is expressible, and
    the old rule threw away the distinction the dataclass took care to make.
    """
    for name in names:
        value = getattr(obj, name)
        if value is None:
            continue
        default = _default(type(obj), name)
        if default is not _MISSING and value == default:
            continue
        out[name] = list(value) if isinstance(value, tuple) else value
    return out


# The order is the schema's, so a written file reads like a documented one.
def _node_dict(n):
    out = {"id": n.id}
    if n.kind != "free":
        out["kind"] = n.kind
    return _keep(out, n, ("label", "sub", "value", "at", "angle", "side",
                          "wall"))


def _branch_dict(b):
    out = {"from": b.source, "to": b.target, "kind": b.kind}
    return _keep(out, b, ("label", "sub", "value", "rate", "count",
                          "arrangement", "via", "at", "angle", "side"))


def _source_dict(s):
    out = {"from": s.source} if s.outward else {"to": s.target}
    out["kind"] = s.kind
    return _keep(out, s, ("label", "sub", "value", "count", "at", "angle",
                          "side"))


def _rail_dict(r):
    out = {"reference": r.reference, "y": r.y}
    return _keep(out, r, ("span",))


def _rename(data, mapping=None):
    mapping = mapping or {}
    return {mapping.get(k, k): v for k, v in data.items()}
