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
import json
from dataclasses import dataclass, field
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


@dataclass
class Node:
    id: str
    kind: str = "free"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    at: Optional[Sequence[float]] = None
    angle: float = 0.0


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


@dataclass
class Source:
    target: str
    kind: str = "diss"
    label: Optional[str] = None
    sub: str = ""
    value: Union[str, float, None] = None
    at: Optional[Sequence[float]] = None
    angle: float = 0.0


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
        if self.rail and self.rail.reference not in seen:
            raise DiagramError(
                f"rail references unknown node {self.rail.reference!r}")
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
        for s in self.sources:
            if s.kind not in SOURCE_KINDS:
                raise DiagramError(
                    f"source at {s.target}: unknown kind {s.kind!r}; expected "
                    "one of " + ", ".join(sorted(SOURCE_KINDS)))
            if s.target not in seen:
                raise DiagramError(f"source: no node named {s.target!r}")
        return self

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
        nodes = [Node(**_rename(n)) for n in data.get("nodes", [])]
        branches = [Branch(**_rename(b, {"from": "source", "to": "target"}))
                    for b in data.get("branches", [])]
        sources = [Source(**_rename(s, {"to": "target"}))
                   for s in data.get("sources", [])]
        rail = Rail(**_rename(data["rail"])) if data.get("rail") else None
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
