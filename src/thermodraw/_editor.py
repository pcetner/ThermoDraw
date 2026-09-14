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
import hashlib
import re
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
        out["terminal_half"] = float(p.symbol.terminals[1][0])
        out["terminals"] = [list(t) for t in p.symbol.terminals]
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
        elif p.element in ("symbol", "node", "ground", "phase", "ellipsis", "region", "volume", "surface", "transfer", "annotation"):
            hits.append(_hit(p, p.element, _render.bounds(p)))
    for rect in scene.rects:
        owner = rect.owner
        if owner is None or owner.role is None or owner.role == "rail":
            continue
        left, top, bw, bh = rect
        hits.append(_hit(owner, "label", (left, top, left + bw, top + bh)))
    return hits


def scene(data: Dict[str, Any], notation: str = "boxes",
          physics: bool = False, adornments=None, display=None) -> Dict[str, Any]:
    """The drawing, its hit map and its findings, from one layout.

    `parts` is the page in page coordinates with no wrapper: the editor
    puts it inside an `<svg>` whose viewBox is its own viewport. `ink` is
    what the drawing covers, for fitting. A diagram that cannot be drawn
    comes back as `{"error": message}`, the library's own words.
    """
    try:
        diagram = Diagram.from_dict(data)
        diagram.display = display or {}
        placements = layout(diagram)
    except DiagramError as exc:
        return _refuse(exc)
    drawn = _render.in_notation(placements, notation)
    reserved = {(a['role'], a['index']): (float(a['width']), float(a['height'])) for a in (adornments or [])}
    composed = _render.compose(drawn, label_adornments=reserved)
    report = _check.check(diagram, physics=physics, _scene=composed, _placements_override=drawn)
    from ._physical import budgets
    hit_map = _hits(drawn, composed)
    findings = report.to_dict()['findings']
    for finding in findings:
        targets = {(h['role'],h['index']) for h in hit_map
                   if h['index'] is not None and (h['ref'] == finding['where'] or re.search(re.escape(h['ref']) + r'(?![\w-])', finding['message']))}
        finding['targets'] = [{'role':role,'index':index} for role,index in sorted(targets)]
        titles = {
            'label-collision': 'Labels overlap', 'label-on-wire': 'A label overlaps a connection',
            'wire-through-label': 'A connection crosses a label',
            'off-canvas': 'Part of the drawing is outside the canvas',
            'network-in-pieces': 'The network has disconnected parts',
            'label-in-a-corridor': 'A label needs more space',
        }
        finding['title'] = titles.get(finding['code'], finding['code'].replace('-', ' ').capitalize())
        explanations = {
            'label-collision': 'Text overlaps another label or drawing element, making the diagram harder to read. Move the affected label or create more space.',
            'label-in-a-corridor': 'This label is squeezed between connections. Move it to a clearer side or increase the spacing.',
            'network-in-pieces': 'Some objects have no connection to the rest of the network. Connect them if they belong to the same thermal system.',
            'nodes-too-close': 'The nodes leave too little room for their connected components. Increase their spacing.',
            'symbols-overlap': 'Component symbols overlap. Separate them so each component and connection is readable.',
            'wire-through-symbol': 'A connection passes through a component symbol. Adjust its route or separate the objects.',
            'wire-through-wall': 'A connection crosses a boundary symbol. Add a straight lead before turning around that boundary.',
            'off-canvas': 'Some drawing content falls outside the defined canvas. Increase the canvas size or move that content inside.',
        }
        finding['explanation'] = explanations.get(finding['code'], 'Inspect the affected objects and their supplied values. Technical details contain the original check and suggested remedy.')
        identity = finding['code'] + ':' + finding['where'] + ':' + str(sorted(targets))
        finding['key'] = hashlib.sha256(identity.encode()).hexdigest()[:16]
        if not targets:
            finding['action'] = 'units' if 'unit' in finding['code'] else 'explain'
    return {
        "parts": "".join(composed.parts),
        "ink": [float(v) for v in composed.ink],
        "labels": len(composed.rects),
        "hits": hit_map,
        "findings": findings,
        "preview": composed.preview,
        "adornments": [{"role": r.owner.role, "index": r.owner.index,
                         "bounds": r.adornment, "clear": r.clear}
                        for r in composed.rects if r.adornment],
        "budgets": budgets(diagram),
    }


def solve(data: Dict[str, Any]) -> Dict[str, Any]:
    """The diagram with every coordinate the author left out filled in."""
    try:
        return _solve.solve(Diagram.from_dict(data)).to_dict()
    except DiagramError as exc:
        return _refuse(exc)


def export(data: Dict[str, Any], what: str = "svg",
           mode: Optional[str] = None, notation: str = "boxes", display=None) -> str:
    """A file the editor hands the user: `svg`, `page` or `json`."""
    diagram = Diagram.from_dict(data)
    diagram.display = display or {}
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
    from ._catalogue import catalogue
    return {
        "units": catalogue(),
        "css": symbols.CSS,
        "vars": theme._VARS,
        "faces": [theme.font_face(f) for f in ("regular", "italic", "semibold")],
        "pitch": float(_solve.PITCH),
        "version": __version__,
    }


def _model_kind(key: str, heading: str) -> Dict[str, str]:
    """Which element and which `kind` a palette entry makes.

    Use stable symbol keys, independently of display group headings: `break` is a node kind and a branch
    kind, `flow` a branch kind and a source kind, and the two in-line
    glyphs carry a `-branch` suffix so the symbol keys stay distinct."""
    kind = key.removesuffix("-branch")
    role = ("node" if key in {"free", "fixed", "break", "phase"} else
            "source" if key in {"diss", "radin", "flow", "flux"} else "branch")
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


def physics(data):
    """Pure analysis plus a reviewable copy; caller guards document revisions."""
    from ._analysis import solve_physics
    from .model import Diagram
    diagram = Diagram.from_dict(data)
    result = solve_physics(diagram)
    return {"result": result.to_dict(), "applied": result.apply(diagram).to_dict() if result.updates else None}


def physics_session(original, scenario, systems=None):
    from ._session import assess_physics
    return assess_physics(original, scenario, systems)


def physics_convert(value, source_unit, target_unit, quantity, scale=None):
    from ._session import convert_value
    return convert_value(value, source_unit, target_unit, quantity, scale)
