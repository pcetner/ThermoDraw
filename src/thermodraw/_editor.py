"""What the browser editor asks the library, as JSON in and JSON out.

The editor at `docs/editor/` runs this package in the page through Pyodide
and calls nothing else. Every function here takes and returns only what
`json.dumps` can carry, so one conversion each way is the whole boundary,
and every drawing and every export is the library's own: the canvas shows
`compose`'s parts, a click lands on a hit built from the same placements
and label rectangles the checker grades, and an exported file is
`Diagram.svg` or `Diagram.page` unchanged. The editor cannot draw what
the library cannot.

Private. The editor is built from the same commit as the wheel it loads,
so nothing here is a promise to anyone else.
"""
import difflib
import json
from typing import Any, Dict, List, Optional, Sequence

from . import _check, _render, _solve, core, symbols, theme
from ._layout import layout
from .model import (BRANCH_KINDS, NODE_KINDS, SOURCE_KINDS, Diagram,
                    DiagramError)

__version__ = __import__("thermodraw").__version__

# The one geometric fact the editor needs that no placement states: a wire
# is a stroke, and a stroke needs a thickness to be clicked.
WIRE_REACH = 6.0


def _refuse(exc: Exception) -> Dict[str, Any]:
    return {"error": str(exc)}


def _hit(p, element: str, bounds: Sequence[float]) -> Dict[str, Any]:
    x0, y0, x1, y1 = bounds
    out: Dict[str, Any] = {
        "role": p.role, "index": p.index, "element": element,
        "at": [float(p.at[0]), float(p.at[1])], "angle": float(p.angle),
        "bounds": [float(x0), float(y0), float(x1), float(y1)],
        "ends": list(p.ends), "ref": p.ref,
    }
    if p.symbol is not None:
        out["kind"] = p.symbol.key
        # How far the wire is cut back either side of the symbol. `bounds`
        # cannot stand in for it: that is the ink, which on a box symbol
        # reaches 62 for leads the symbol is only 42 long. An editor routing
        # a wire around a dragged symbol needs the 42.
        out["half_len"] = float(p.symbol.half_len)
    if element == "symbol" and p.role == "branch" and p.via:
        out["via"] = [[float(x), float(y)] for x, y in p.via]
    return out


def _hits(placements, scene) -> List[Dict[str, Any]]:
    """One clickable box per thing on the page, hidden forms left out."""
    hits = []
    for p in placements:
        if not p.shown or p.role is None or p.role == "rail":
            continue
        if p.element == "wire":
            for a, b in zip(p.points, p.points[1:]):
                x0, x1 = sorted((a[0], b[0]))
                y0, y1 = sorted((a[1], b[1]))
                hits.append(_hit(p, "wire", (x0 - WIRE_REACH, y0 - WIRE_REACH,
                                             x1 + WIRE_REACH, y1 + WIRE_REACH)))
        elif p.element in ("symbol", "node", "ground", "phase", "ellipsis",
                           "stream"):
            hits.append(_hit(p, p.element, _render.bounds(p)))
    for rect in scene.rects:
        owner = rect.owner
        if owner is None or owner.role is None or owner.role == "rail":
            continue
        left, top, bw, bh = rect
        hits.append(_hit(owner, "label", (left, top, left + bw, top + bh)))
    return hits


def scene(data: Dict[str, Any], notation: str = "boxes",
          physics: bool = False) -> Dict[str, Any]:
    """The drawing, its hit map and its findings, from one layout.

    `parts` is the page in page coordinates with no wrapper: the editor
    puts it inside an `<svg>` whose viewBox is its own viewport. `ink` is
    what the drawing covers, for fitting. A diagram that cannot be drawn
    comes back as `{"error": message}`, the library's own words.
    """
    try:
        diagram = Diagram.from_dict(data)
        placements = layout(diagram)
    except DiagramError as exc:
        return _refuse(exc)
    drawn = _render.in_notation(placements, notation)
    composed = _render.compose(drawn)
    report = _check.check(diagram, physics=physics) if physics else \
        _check.check(placements)
    return {
        "parts": "".join(composed.parts),
        "ink": [float(v) for v in composed.ink],
        "labels": len(composed.rects),
        "hits": _hits(drawn, composed),
        "findings": report.to_dict()["findings"],
    }


def solve(data: Dict[str, Any]) -> Dict[str, Any]:
    """The diagram with every coordinate the author left out filled in."""
    try:
        return _solve.solve(Diagram.from_dict(data)).to_dict()
    except DiagramError as exc:
        return _refuse(exc)


def export(data: Dict[str, Any], what: str = "svg",
           mode: Optional[str] = None, notation: str = "boxes") -> str:
    """A file the editor hands the user: `svg`, `page` or `json`."""
    diagram = Diagram.from_dict(data)
    if what == "svg":
        return diagram.svg(mode, notation=notation)
    if what == "page":
        return diagram.page(notation=notation)
    if what == "json":
        return diagram.to_json()
    raise ValueError(f"export what? svg, page or json, not {what!r}")


def head() -> Dict[str, Any]:
    """What the page supplies once so no render has to carry it: the
    symbol stylesheet, the palette variables, the three faces.

    `pitch` is the solver's own spacing between two nodes on a run. The
    editor lays a dropped path out at it, and a hand-placed ladder that
    follows it is the one `_solve` would have produced, so it is sent
    from here rather than written down a second time in the page.
    """
    return {
        "css": symbols.CSS,
        "vars": theme._VARS,
        "faces": [theme.font_face(f) for f in ("regular", "italic", "semibold")],
        "pitch": float(_solve.PITCH),
        "version": __version__,
    }


def _model_kind(key: str, heading: str) -> Dict[str, str]:
    """Which element and which `kind` a palette entry makes.

    Read off the group, not the key: `break` is a node kind and a branch
    kind, `flow` a branch kind and a source kind, and the two in-line
    glyphs carry a `-branch` suffix so the symbol keys stay distinct."""
    kind = key.removesuffix("-branch")
    role = ("node" if heading == "Nodes" else
            "source" if heading == "Sources" else "branch")
    assert kind in {"node": NODE_KINDS, "branch": BRANCH_KINDS,
                    "source": SOURCE_KINDS}[role], key
    return {"role": role, "kind": kind}


def palette() -> List[Dict[str, Any]]:
    """The twenty symbols as the editor's palette, drawn by the library,
    grouped as `symbols.GROUPS` groups them."""
    by_key = {s.key: s for s in symbols.SYMBOLS}
    out = []
    for heading, keys in symbols.GROUPS:
        for key in keys:
            sym = by_key[key]
            out.append({"key": key, "name": sym.name, "group": heading,
                        "note": sym.note,
                        "svg": symbols.card(sym, fluid=True),
                        **_model_kind(key, heading)})
    return out


def quick_add(text: str) -> List[Dict[str, Any]]:
    """What typing `text` on the canvas could mean, best first: symbols
    whose key or name starts with it, then near misses, as `model._suggest`
    finds them."""
    text = text.strip().lower()
    if not text:
        return []
    entries = palette()
    names = {e["name"].lower(): e for e in entries}
    keys = {e["key"]: e for e in entries}
    kinds = {e["kind"]: e for e in entries}
    ranked: List[Dict[str, Any]] = []
    seen = set()

    def take(e):
        if e["key"] not in seen:
            seen.add(e["key"])
            ranked.append({k: e[k] for k in ("key", "name", "role", "kind")})

    for e in entries:
        if e["key"].startswith(text) or e["name"].lower().startswith(text):
            take(e)
    for e in entries:
        if text in e["name"].lower():
            take(e)
    for near in difflib.get_close_matches(
            text, list(names) + list(keys) + list(kinds), n=4, cutoff=0.6):
        take(names.get(near) or keys.get(near) or kinds[near])
    return ranked


def _selftest() -> None:
    """Everything a caller gets back must survive `json.dumps`."""
    for value in (head(), palette(), quick_add("con")):
        json.dumps(value)
