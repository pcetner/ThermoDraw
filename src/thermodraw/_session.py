"""Pure scenario assessment: numeric edits on a copy, never on the source."""
import copy
import math
from typing import Any, Dict, List, Optional, Union, cast
from ._analysis_types import AssessmentReport, ValidAssessmentReport

from ._analysis import fingerprint, solve_physics, resistance_index
from .model import Diagram, DiagramError, R_SCALE, P_SCALE, CP_SCALE, MDOT_SCALE
from ._physical import POWER, AREA, FLUX, number

EDITABLE = {"nodes": {"value"}, "branches": {"value", "rate", "mdot", "cp"},
            "sources": {"value"}, "control_volumes": {"generation", "storage", "steady"},
            "transfers": {"rate", "flux"}, "control_surfaces": {"area"}}


def convert_value(value, source_unit, target_unit, quantity, scale=None):
    """Normalize a per-value override to the diagram's declared unit."""
    n = number(value)
    if n is None:
        raise DiagramError("A unit override requires a finite numeric value")
    if quantity == "T":
        if source_unit not in ("K", "C", "°C") or target_unit not in ("K", "C", "°C"):
            raise DiagramError("Temperature overrides support K and °C")
        offset = lambda u: 273.15 if u in ("C", "°C") and scale != "rise" else 0
        result = n + offset(source_unit) - offset(target_unit)
    else:
        tables: Dict[str, Dict[str, float]] = {"R": R_SCALE, "P": P_SCALE, "q": P_SCALE, "rate": POWER,
                  "generation": POWER, "storage": POWER, "area": AREA,
                  "flux": FLUX, "q″": FLUX, "cp": CP_SCALE,
                  "mdot": MDOT_SCALE, "C": {"J/K": 1, "kJ/K": 1000}}
        table = tables.get(quantity, {})
        if source_unit not in table or target_unit not in table:
            raise DiagramError("Unsupported unit conversion for " + quantity)
        result = n * table[source_unit] / table[target_unit]
    if not math.isfinite(result):
        raise DiagramError("Unit conversion exceeded numerical range")
    return result


def _data(value):
    return value.to_dict() if isinstance(value, Diagram) else copy.deepcopy(value)


def assess_physics(original: Union[Diagram, Dict[str, Any]],
                   scenario: Optional[Union[Diagram, Dict[str, Any]]] = None,
                   systems: Optional[List[str]] = None) -> AssessmentReport:
    """Assess independent systems and return a validated complete-scenario proposal.

    ``scenario`` is a full document copy with numeric/analysis changes only.
    ``systems`` selects whole system IDs from a previous assessment. Results
    never mutate either argument. A caller must guard input_hash before applying.
    """
    base_data = _data(original)
    effective_data = _data(scenario) if scenario is not None else copy.deepcopy(base_data)
    try:
        base = Diagram.from_dict(base_data)
        effective = Diagram.from_dict(effective_data)
        if base.units != effective.units or base.scale != effective.scale:
            raise DiagramError("Preserve document units; normalize individual overrides to those units")
        # Stable order is the session reference for legacy entities without IDs.
        a, b = base.to_dict(), effective.to_dict()
        for data in (a, b):
            data.pop("analysis", None)
            data.pop("units", None)
            for collection, fields in EDITABLE.items():
                for obj in data.get(collection, []):
                    for field in fields:
                        obj.pop(field, None)
        if a != b:
            raise DiagramError("A solve session may change values and assumptions, not topology or geometry")
    except DiagramError as exc:
        return {"status": "invalid", "issues": [{"status": "invalid", "message": str(exc)}],
                "systems": [], "result": None, "applied": None, "changes": [], "comparisons": []}
    if effective.nodes and "network" not in effective.analysis:
        effective.analysis["network"] = {"steady": False, "unknowns": []}
    result = solve_physics(effective, check_supplied=True)
    reports = [("network:" + c["nodes"][0], c) for c in result.components]
    reports += [("volume:" + v["id"], v) for v in result.volumes]
    if systems is not None and (not isinstance(systems, list) or any(s not in dict(reports) for s in systems)):
        raise DiagramError("Select whole system IDs returned by assessment")
    selected = set(systems) if systems is not None else {key for key, _ in reports}
    summary = [{"id": key, "selected": key in selected, "status": r["status"],
                "nodes": r.get("nodes", []), "diagnostics": r["diagnostics"]} for key, r in reports]
    result.components = [c for key, c in reports if key.startswith("network:") and key in selected]
    result.volumes = [c for key, c in reports if key.startswith("volume:") and key in selected]
    good_nodes = {n for c in result.components if c["status"] == "solved" for n in c["nodes"]}
    good_volumes = {v["id"] for v in result.volumes if v["status"] in ("solved", "balanced")}
    surfaces = {s.id: s.volume for s in effective.control_surfaces}
    transfers = {t.id: surfaces.get(t.surface) if t.surface is not None else None for t in effective.transfers}
    result.updates = [u for u in result.updates if
                      (u['entity'] == 'branch' and effective.branches[u['index']].source in good_nodes) or
                      (u["entity"] == "node" and u["id"] in good_nodes) or
                      (u["entity"] == "volume" and u["id"] in good_volumes) or
                      (u["entity"] == "transfer" and transfers.get(u["id"]) in good_volumes)]
    states = [r["status"] for r in result.components + result.volumes]
    result.status = ("not-configured" if not states else "solved" if all(s in ("solved", "balanced") for s in states)
                     else "partial" if any(s in ("solved", "balanced") for s in states) else "not-solved")
    calculated = result.apply(effective) if result.updates else copy.deepcopy(effective)
    proposal = copy.deepcopy(base)
    issues = [{"system": key, "status": r["status"], "message": message, "nodes": r.get("nodes", []), "volume": r.get("id")}
              for key, r in reports if key in selected for message in r["diagnostics"]]
    # Global unit/steady declarations cannot be applied to just part of a network.
    global_change = base.units != effective.units or base.scale != effective.scale or base.analysis.get("network", {}).get("steady") != effective.analysis.get("network", {}).get("steady")
    all_network_good = all(key in selected and r["status"] == "solved" for key, r in reports if key.startswith("network:"))
    if global_change and not all_network_good:
        good_nodes = set()
        issues.append({"status": "application-limited", "message": "Network results can be copied, but applying shared units or steady assumptions requires all network components to succeed."})
    if all_network_good:
        proposal.units = copy.deepcopy(effective.units)
        proposal.scale = effective.scale
    tolerance_changed = base.analysis.get("tolerance", {}) != effective.analysis.get("tolerance", {})
    all_systems_good = bool(reports) and all(
        key in selected and r["status"] in ("solved", "balanced") for key, r in reports)
    if tolerance_changed:
        if all_systems_good:
            if "tolerance" in effective.analysis:
                proposal.analysis["tolerance"] = copy.deepcopy(effective.analysis["tolerance"])
            else:
                proposal.analysis.pop("tolerance", None)
        else:
            good_nodes, good_volumes = set(), set()
            issues.append({"status": "application-limited", "message":
                           "Applying shared tolerances requires every system to be selected and successful. Results remain available for copying."})
    changes = []
    for collection, fields in EDITABLE.items():
        for index, (old, new) in enumerate(zip(getattr(proposal, collection), getattr(calculated, collection))):
            if collection == "nodes":
                allowed = old.id in good_nodes
            elif collection == "branches":
                ends = {old.source, old.target}
                allowed = ends <= good_nodes
            elif collection == "sources":
                allowed = old.node in good_nodes
            elif collection == "control_volumes":
                allowed = old.id in good_volumes
            elif collection == "control_surfaces":
                allowed = old.volume in good_volumes
            else:
                allowed = transfers.get(old.id) in good_volumes
            if not allowed:
                continue
            for field in fields:
                before, after = getattr(old, field), getattr(new, field)
                if before != after:
                    changes.append({"collection": collection, "id": getattr(old, "id", None),
                                    "index": index, "field": field,
                                    "before": before, "after": after})
                    setattr(old, field, after)
    if good_nodes and "network" in effective.analysis:
        net = copy.deepcopy(proposal.analysis.get("network", {}))
        net["steady"] = effective.analysis["network"].get("steady", False)
        net["unknowns"] = [n for n in net.get("unknowns", []) if n not in good_nodes] + [n for n in effective.analysis["network"].get("unknowns", []) if n in good_nodes]
        def good_branch(target):
            index = resistance_index(effective, target)
            return index is not None and effective.branches[index].source in good_nodes
        targets = [t for t in net.get('resistance_unknowns', []) if not good_branch(t)] + [t for t in effective.analysis['network'].get('resistance_unknowns', []) if good_branch(t)]
        if targets or 'resistance_unknowns' in net:
            net['resistance_unknowns'] = targets
        proposal.analysis["network"] = net
    for vid in good_volumes:
        target = effective.analysis.get("volumes", {}).get(vid)
        if target:
            proposal.analysis.setdefault("volumes", {})[vid] = copy.deepcopy(target)
        else:
            proposal.analysis.get("volumes", {}).pop(vid, None)
    for field in ("units", "scale", "analysis"):
        if getattr(base, field) != getattr(proposal, field):
            changes.append({"collection": "diagram", "field": field,
                            "before": copy.deepcopy(getattr(base, field)), "after": copy.deepcopy(getattr(proposal, field))})
    comparisons = []
    for u in result.updates:
        if u['entity'] == 'branch':
            before = base.branches[u['index']].value
            numeric_before = number(before)
            comparisons.append({**u, 'original': before, 'difference': None if numeric_before is None else u['value']-numeric_before})
            continue
        objects = cast(List[Any], {"node": base.nodes, "volume": base.control_volumes, "transfer": base.transfers}[u["entity"]])
        before = getattr(next(o for o in objects if o.id == u["id"]), u["field"])
        numeric_before = number(before)
        comparisons.append({**u, "original": before, "difference": None if numeric_before is None else u["value"] - numeric_before})
    proposal.validate()
    if changes:
        proposal.analysis["provenance"] = {"input_hash": fingerprint(base), "scenario_hash": fingerprint(effective), "calculated": result.updates}
    report: ValidAssessmentReport = {"status": result.status, "input_hash": fingerprint(base), "scenario_hash": fingerprint(effective),
            "systems": summary, "issues": issues, "result": result.to_dict(),
            "effective_inputs": effective.to_dict(), "applied": proposal.to_dict() if changes else None,
            "changes": changes, "comparisons": comparisons}
    return report
