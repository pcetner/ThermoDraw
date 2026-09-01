"""A diagram as data.

This is the thing you write, an LLM emits, and a human edits. It carries no
geometry beyond the coordinates you give it, and no SVG at all: `layout` turns
it into placements and `render` turns those into a document.

The split matters for what comes next. In 0.2 `layout` reads the `at`
coordinates you supply. In 0.3 it computes the ones you leave out. The schema
does not change; only that one stage gains a solver.

Every `kind` is a key from `symbols.SYMBOLS`, so the vocabulary and the schema
are the same list. See docs/schema.md.
"""
import difflib
import json
from dataclasses import MISSING as _MISSING
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Sequence, Union

NODE_KINDS = {"free", "fixed", "break", "corner"}
BRANCH_KINDS = {"cond", "conv", "rad", "contact", "cap"}
SOURCE_KINDS = {"diss", "radin", "flow", "flux"}

# A subscript on an R is structural: the library sets it and it names the
# mechanism. A subscript on a C, T, P or q is identity, and the caller sets
# it. None here means "ask the branch", which is how that asymmetry is kept.
BRANCH_SUB = {"cond": "cond", "conv": "conv", "rad": "rad",
              "contact": "contact", "cap": None}
BRANCH_SYMBOL = {"cond": "R", "conv": "R", "rad": "R", "contact": "R",
                 "cap": "C"}
SOURCE_SYMBOL = {"diss": "P", "radin": "q", "flow": "q", "flux": "q"}

# Which quantity each kind is measured in, so one units entry serves many.
QUANTITY = {"cond": "R", "conv": "R", "rad": "R", "contact": "R", "cap": "C",
            "free": "T", "fixed": "T", "break": "T",
            "diss": "P", "radin": "q", "flow": "q", "flux": "q"}

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


# ------------------------------------------------------------------ typing
# The point of validate() is that a diagram which cannot be drawn says so
# before anything tries to draw it. Checking ids and kinds but not the shape
# of a coordinate left seven ways to write a bad `at`: six died deep in the
# renderer with messages like "Unknown format code 'f' for object of type
# 'str'", naming no node and no field, and one drew the wrong picture in
# silence. These are cheap and they run first.
def _number(value, where, name):
    # bool is an int in Python, and an angle of True is not an angle
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiagramError(
            f"{where}: {name} must be a number, got {value!r}")
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
    return value


def _text(value, where, name):
    if value is not None and not isinstance(value, str):
        raise DiagramError(
            f"{where}: {name} must be text, got {value!r}")
    return value


def _value(value, where):
    if value is not None and not isinstance(value, (str, int, float)):
        raise DiagramError(
            f"{where}: value must be a number or text, got {value!r}")
    return value


# core.annotate has taken an explicit side since the occupancy work, and
# CLAUDE.md documents it as the override for the automatic choice. It was
# reachable from Python and from nowhere else: the model carried no field for
# it, so a diagram written as data could not say where its own label goes.
SIDES = ("auto", "up", "down", "left", "right")


def _side(value, where):
    if value not in SIDES:
        raise DiagramError(
            f"{where}: side must be one of " + ", ".join(map(repr, SIDES))
            + f", got {value!r}")
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


@dataclass
class Branch:
    source: str
    target: str
    kind: str = "cond"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    via: List[Sequence[float]] = field(default_factory=list)
    at: Optional[Sequence[float]] = None
    angle: Optional[float] = None
    side: str = "auto"


@dataclass
class Source:
    target: str
    kind: str = "diss"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    at: Optional[Sequence[float]] = None
    angle: float = 0.0
    side: str = "auto"


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

    def node(self, node_id):
        for n in self.nodes:
            if n.id == node_id:
                return n
        raise DiagramError(f"no node named {node_id!r}")

    def unit(self, kind):
        return self.units.get(QUANTITY.get(kind, ""), "")

    def value_text(self, kind, value):
        text = _fmt(value)
        if text is None:
            return None
        unit = self.unit(kind)
        return f"{text} {unit}".strip()

    def validate(self):
        """Every reason a diagram cannot be drawn, reported before drawing."""
        seen = set()
        for n in self.nodes:
            if n.id in seen:
                raise DiagramError(f"duplicate node id {n.id!r}")
            seen.add(n.id)
            if n.kind not in NODE_KINDS:
                raise DiagramError(
                    f"node {n.id!r}: unknown kind {n.kind!r}; expected one of "
                    + ", ".join(sorted(NODE_KINDS)))
            if n.at is None:
                raise DiagramError(
                    f"node {n.id!r} has no coordinates. 0.2 places what you "
                    "supply; solving for the ones you leave out arrives with "
                    "the network layer in 0.3.")
            where = f"node {n.id!r}"
            _point(n.at, where, "at")
            _number(n.angle, where, "angle")
            _text(n.label, where, "label")
            _text(n.sub, where, "sub")
            _value(n.value, where)
            _side(n.side, where)
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
        # Units are fixed per diagram and given once per quantity, so they
        # cannot be mixed. What can still go wrong is a value with no unit
        # at all, which renders as a bare number.
        for owner, kind, value in self._valued():
            if value is not None and not self.unit(kind):
                raise DiagramError(
                    f"{owner} has the value {value!r} but units has no entry "
                    f"for {QUANTITY[kind]!r}, so it would render bare")
        for s in self.sources:
            if s.kind not in SOURCE_KINDS:
                raise DiagramError(
                    f"source at {s.target}: unknown kind {s.kind!r}; expected "
                    "one of " + ", ".join(sorted(SOURCE_KINDS)))
            if s.target not in seen:
                raise DiagramError(f"source: no node named {s.target!r}")
            where = f"source at {s.target}"
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
            if n.kind != "corner":
                yield f"node {n.id!r}", n.kind, n.value
        for b in self.branches:
            yield f"branch {b.source}-{b.target}", b.kind, b.value
        for s in self.sources:
            yield f"source at {s.target}", s.kind, s.value

    def to_dict(self):
        """JSON-shaped, using from/to rather than the Python-safe names."""
        out: Dict[str, Any] = {}
        if self.title:
            out["title"] = self.title
        if self.units:
            out["units"] = dict(self.units)
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
        nodes = [_build(Node, n, f"node {i}")
                 for i, n in enumerate(data.get("nodes", []))]
        branches = [_build(Branch, b, f"branch {i}",
                           {"from": "source", "to": "target"})
                    for i, b in enumerate(data.get("branches", []))]
        sources = [_build(Source, s, f"source {i}", {"to": "target"})
                   for i, s in enumerate(data.get("sources", []))]
        rail = _build(Rail, data["rail"], "rail") if data.get("rail") else None
        return cls(nodes=nodes, branches=branches, sources=sources, rail=rail,
                   units=dict(data.get("units", {})),
                   size=data.get("size"), title=data.get("title")).validate()

    def to_json(self, **kw):
        kw.setdefault("indent", 2)
        kw.setdefault("ensure_ascii", False)
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))


def _keep(out, obj, names):
    for name in names:
        value = getattr(obj, name)
        if value in (None, "", [], ()) or value == 0.0:
            continue
        out[name] = list(value) if isinstance(value, tuple) else value
    return out


def _node_dict(n):
    out = {"id": n.id}
    if n.kind != "free":
        out["kind"] = n.kind
    return _keep(out, n, ("label", "sub", "value", "at", "angle"))


def _branch_dict(b):
    out = {"from": b.source, "to": b.target, "kind": b.kind}
    return _keep(out, b, ("label", "sub", "value", "via", "at", "angle"))


def _source_dict(s):
    out = {"to": s.target, "kind": s.kind}
    return _keep(out, s, ("label", "sub", "value", "at", "angle"))


def _rail_dict(r):
    out = {"reference": r.reference, "y": r.y}
    return _keep(out, r, ("span",))


def _rename(data, mapping=None):
    mapping = mapping or {}
    return {mapping.get(k, k): v for k, v in data.items()}
