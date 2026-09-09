"""Rectangular physical sketches and explicit control-volume energy budgets.

Drawing lengths are page coordinates, never inferred physical dimensions.
Network links are descriptive and never counted in an energy budget.
"""
import math
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Sequence, Union

Number = Union[str, float, None]


@dataclass
class Region:
    id: str
    at: Sequence[float] = (0, 0)
    size: Sequence[float] = (200, 120)
    label: Optional[str] = None
    label_offset: Optional[Sequence[float]] = None
    links: List[str] = field(default_factory=list)


@dataclass
class ControlVolume:
    id: str
    at: Sequence[float] = (0, 0)
    size: Sequence[float] = (240, 160)
    label: Optional[str] = None
    regions: List[str] = field(default_factory=list)
    generation: Number = None
    storage: Number = None
    steady: bool = False
    unit: str = "W"
    label_offset: Optional[Sequence[float]] = None
    links: List[str] = field(default_factory=list)
    incomplete: bool = False


@dataclass
class ControlSurface:
    id: str
    volume: str
    edge: str = "right"
    start: float = 0.25
    end: float = 0.75
    area: Number = None
    area_unit: str = "m²"
    label: Optional[str] = None
    label_offset: Optional[Sequence[float]] = None
    links: List[str] = field(default_factory=list)


@dataclass
class Transfer:
    id: str
    surface: Optional[str] = None
    kind: str = "heat"
    direction: str = "out"
    rate: Number = None
    flux: Number = None
    unit: str = "W"
    flux_unit: str = "W/m²"
    length: float = 80
    label: Optional[str] = None
    at: Sequence[float] = (0, 0)  # fallback for a detached arrow
    label_offset: Optional[Sequence[float]] = None
    links: List[str] = field(default_factory=list)


@dataclass
class Annotation:
    id: str
    kind: str = "text"
    at: Sequence[float] = (0, 0)
    end: Sequence[float] = (100, 0)
    label: Optional[str] = None
    label_offset: Optional[Sequence[float]] = None
    links: List[str] = field(default_factory=list)


COLLECTIONS = {"regions": Region, "control_volumes": ControlVolume,
               "control_surfaces": ControlSurface, "transfers": Transfer,
               "annotations": Annotation}
ROLES = dict(zip(COLLECTIONS, ("region", "volume", "surface", "transfer", "annotation")))
POWER = {"W": 1.0, "kW": 1000.0, "mW": .001}
AREA = {"m²": 1.0, "cm²": .0001, "mm²": .000001}
FLUX = {"W/m²": 1.0, "W/cm²": 10000.0, "kW/m²": 1000.0}


def number(value: object) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        n = float(value) if isinstance(value, (str, int, float)) else float("nan")
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def validate(diagram):
    from .model import DiagramError, _point

    def fail(message):
        raise DiagramError(message)

    ids = set()
    network = set()
    for role, entries in (("node", diagram.nodes), ("branch", diagram.branches), ("source", diagram.sources)):
        local = set()
        for obj in entries:
            ident = getattr(obj, "id", None)
            if ident is not None:
                if not isinstance(ident, str) or not ident or ident in local:
                    fail(f"{role}: id must be a unique nonempty string")
                local.add(ident)
                network.add(f"{role}:{ident}")
            offset = getattr(obj, "label_offset", None)
            if offset is not None:
                _point(offset, role, "label_offset")
    for key, cls in COLLECTIONS.items():
        entries = getattr(diagram, key)
        if not isinstance(entries, list):
            fail(f"{key} must be a list")
        for obj in entries:
            if not isinstance(obj, cls):
                fail(f"{key} must contain {cls.__name__} objects")
            if not isinstance(obj.id, str) or not obj.id or obj.id in ids:
                fail(f"{key}: id must be a unique nonempty string")
            ids.add(obj.id)
            if obj.label is not None and not isinstance(obj.label, str):
                fail(f"{obj.id}: label must be text")
            if obj.label_offset is not None:
                _point(obj.label_offset, obj.id, "label_offset")
            if not isinstance(obj.links, list) or any(not isinstance(s, str) or s not in network for s in obj.links):
                fail(f"{obj.id}: links must name node:id, branch:id or source:id")
            for name in ("at", "size", "end"):
                if hasattr(obj, name) and not (name == "end" and isinstance(obj, ControlSurface)):
                    _point(getattr(obj, name), obj.id, name)
            if hasattr(obj, "size") and any(v <= 0 for v in obj.size):
                fail(f"{obj.id}: rectangle size must be positive")
            for name in ("rate", "flux", "area", "generation", "storage"):
                if not hasattr(obj, name):
                    continue
                val = getattr(obj, name)
                if val is None:
                    continue
                if isinstance(val, bool) or not isinstance(val, (str, float, int)):
                    fail(f"{obj.id}: {name} must be a number or symbolic text")
                n = number(val)
                if not isinstance(val, str) and n is None:
                    fail(f"{obj.id}: {name} must be finite")
                if n is not None and name in ("rate", "flux", "area") and (n < 0 or name == "area" and n == 0):
                    fail(f"{obj.id}: {name} must be {'positive' if name == 'area' else 'nonnegative'}")
    regions = {r.id for r in diagram.regions}
    volumes = {v.id for v in diagram.control_volumes}
    surfaces = {s.id for s in diagram.control_surfaces}
    for v in diagram.control_volumes:
        if not isinstance(v.regions, list) or any(not isinstance(r, str) or r not in regions for r in v.regions):
            fail(f"{v.id}: regions must reference existing regions")
        if not isinstance(v.steady, bool) or not isinstance(v.incomplete, bool):
            fail(f"{v.id}: steady and incomplete must be booleans")
        if not isinstance(v.unit, str) or v.unit not in POWER:
            fail(f"{v.id}: unit must be W, kW or mW")
        if v.steady and v.storage is not None and number(v.storage) != 0:
            fail(f"{v.id}: steady state contradicts nonzero or unknown storage")
    for s in diagram.control_surfaces:
        if not isinstance(s.volume, str) or s.volume not in volumes:
            fail(f"{s.id}: volume must reference an existing control volume")
        if s.edge not in ("left", "right", "top", "bottom"):
            fail(f"{s.id}: edge must be left, right, top or bottom")
        a, b = number(s.start), number(s.end)
        if not isinstance(s.start, (int, float)) or not isinstance(s.end, (int, float)) or a is None or b is None or not 0 <= a < b <= 1:
            fail(f"{s.id}: surface requires 0 <= start < end <= 1")
        if not isinstance(s.area_unit, str) or s.area_unit not in AREA:
            fail(f"{s.id}: area_unit must be m², cm² or mm²")
    for t in diagram.transfers:
        if t.surface is not None and (not isinstance(t.surface, str) or t.surface not in surfaces):
            fail(f"{t.id}: surface must reference an existing control surface")
        if t.kind not in ("heat", "work", "mass") or t.direction not in ("in", "out"):
            fail(f"{t.id}: expected heat/work/mass and in/out")
        if t.rate is not None and t.flux is not None:
            fail(f"{t.id}: supply rate or flux, not both")
        if t.flux is not None and t.kind != "heat":
            fail(f"{t.id}: only heat transfers accept flux")
        if not isinstance(t.unit, str) or not isinstance(t.flux_unit, str) or t.unit not in POWER or t.flux_unit not in FLUX:
            fail(f"{t.id}: unsupported rate or flux unit")
        length = number(t.length)
        if not isinstance(t.length, (int, float)) or length is None or length <= 0:
            fail(f"{t.id}: length must be positive")
    for a in diagram.annotations:
        if a.kind not in ("text", "line", "arrow"):
            fail(f"{a.id}: annotation kind must be text, line or arrow")


def surface_geometry(surface, volumes):
    v = volumes[surface.volume]
    x, y = v.at
    w, h = v.size
    if surface.edge in ("left", "right"):
        x += w if surface.edge == "right" else 0
        return [(x, y + h * surface.start), (x, y + h * surface.end)], ((1, 0) if surface.edge == "right" else (-1, 0))
    y += h if surface.edge == "bottom" else 0
    return [(x + w * surface.start, y), (x + w * surface.end, y)], ((0, 1) if surface.edge == "bottom" else (0, -1))


def placements(diagram):
    from ._layout import Placement, Label
    volumes = {v.id: v for v in diagram.control_volumes}
    surfaces = {s.id: s for s in diagram.control_surfaces}
    out = []
    for key, role in ROLES.items():
        for i, obj in enumerate(getattr(diagram, key)):
            points = []
            at = tuple(getattr(obj, "at", (0, 0)))
            geometry: Dict[str, Any] = {}
            value = None
            if role in ("region", "volume"):
                geometry["size"] = list(obj.size)
            elif role == "surface":
                points, normal = surface_geometry(obj, volumes)
                at = tuple((a + b) / 2 for a, b in zip(*points))
                geometry["normal"] = normal
            elif role == "transfer":
                normal = (1, 0)
                if obj.surface:
                    edge, normal = surface_geometry(surfaces[obj.surface], volumes)
                    at = tuple((a + b) / 2 for a, b in zip(*edge))
                points = [(at[0] - normal[0] * obj.length / 2, at[1] - normal[1] * obj.length / 2),
                          (at[0] + normal[0] * obj.length / 2, at[1] + normal[1] * obj.length / 2)]
                if obj.direction == "in":
                    points.reverse()
                geometry["arrow"] = True
                if obj.rate is not None:
                    value = f"{obj.rate} {obj.unit}"
                elif obj.flux is not None:
                    value = f"{obj.flux} {obj.flux_unit}"
            elif obj.kind != "text":
                points = [at, tuple(obj.end)]
                geometry["arrow"] = obj.kind == "arrow"
            label = Label(user=obj.label or obj.id, value=value)
            if role in ("region", "volume", "annotation"):
                label.offset = obj.label_offset
                label.preferred = (8, 8)
            else:
                label.offset = obj.label_offset
            out.append(Placement(role, at=at, points=points, geometry=geometry,
                                 role=role, index=i, ref=f"{role} '{obj.id}'", label=label))
    return out


def budgets(diagram, *, tolerance=None):
    surfaces = {s.id: s for s in diagram.control_surfaces}
    result = []
    for v in diagram.control_volumes:
        missing = ["boundary terms removed; review and acknowledge"] if v.incomplete else []
        generation = number(v.generation)
        storage = 0.0 if v.steady else number(v.storage)
        if generation is None:
            missing.append("generation")
        if storage is None:
            missing.append("storage or steady state")
        incoming = outgoing = 0.0
        terms = []
        for t in diagram.transfers:
            s = surfaces.get(t.surface)
            if s is None or s.volume != v.id:
                continue
            rate = number(t.rate)
            if t.flux is not None:
                flux, area = number(t.flux), number(s.area)
                rate = None if flux is None or area is None else flux * FLUX[t.flux_unit] * area * AREA[s.area_unit]
            elif rate is not None:
                rate *= POWER[t.unit]
            if rate is None:
                missing.append(f"{t.id}: rate or flux and surface area")
                continue
            if t.direction == "in":
                incoming += rate
            else:
                outgoing += rate
            terms.append({"id": t.id, "kind": t.kind, "direction": t.direction, "watts": rate})
        g = (generation or 0) * POWER[v.unit]
        st = (storage or 0) * POWER[v.unit]
        residual = incoming - outgoing + g - st
        lhs = incoming + max(g, 0) + max(-st, 0)
        rhs = outgoing + max(-g, 0) + max(st, 0)
        settings = tolerance or {}
        limit = max(settings.get("absolute_w", .001), settings.get("relative", .01) * max(lhs, rhs))
        if not all(math.isfinite(x) for x in (incoming, outgoing, g, st, residual, limit)):
            missing.append("energy calculation exceeded numerical range")
        result.append({"id": v.id, "incoming": incoming, "outgoing": outgoing,
                       "generation": None if generation is None else g,
                       "storage": None if storage is None else st,
                       "residual": None if missing else residual, "tolerance": limit,
                       "status": "unchecked" if missing else "balanced" if abs(residual) <= limit else "unbalanced",
                       "missing": missing, "terms": terms})
    return result


def findings(diagram):
    from ._check import Finding
    out = []
    for v, budget in zip(diagram.control_volumes, budgets(diagram)):
        if budget["status"] == "balanced":
            continue
        unchecked = budget["status"] == "unchecked"
        message = ("not checked: " + "; ".join(budget["missing"])) if unchecked else (
            f"{budget['incoming']:g} W in - {budget['outgoing']:g} W out + "
            f"{budget['generation']:g} W generation - {budget['storage']:g} W storage "
            f"= {budget['residual']:g} W residual (tolerance {budget['tolerance']:g} W)")
        out.append(Finding("control-volume-not-checked" if unchecked else "control-volume-does-not-balance",
                           "note" if unchecked else "warning", f"control volume '{v.id}'", message,
                           remedy="Supply missing terms, check transfer directions and units, and review generation and storage.",
                           at=tuple(v.at)))
    for t in diagram.transfers:
        if t.surface is None:
            out.append(Finding("control-volume-not-checked", "note", f"transfer '{t.id}'",
                               "detached transfer is not included in a control-volume balance",
                               remedy="Attach it to a control surface.", at=tuple(t.at)))
    return out
