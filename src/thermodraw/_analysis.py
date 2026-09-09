"""Explicit, dependency-free steady energy analysis. Never invokes drawing layout."""
import copy
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, NoReturn, Set, TYPE_CHECKING, Union, cast

from ._analysis_types import PhysicsUpdate, PhysicsReport
if TYPE_CHECKING:
    from .model import Diagram
    from .builder import DiagramBuilder

from ._physical import POWER, AREA, FLUX, number, budgets


def validate(diagram):
    from .model import DiagramError
    a = diagram.analysis
    def fail(message) -> NoReturn:
        raise DiagramError("analysis: " + message)
    if not isinstance(a, dict) or set(a) - {"network", "volumes", "tolerance", "provenance"}:
        fail("expected network, volumes, tolerance or provenance")
    net = a.get("network", {})
    if not isinstance(net, dict) or set(net) - {"steady", "unknowns", "resistance_unknowns"}:
        fail("network accepts steady, unknowns and resistance_unknowns")
    if "steady" in net and not isinstance(net["steady"], bool):
        fail("steady must be boolean")
    unknowns = net.get("unknowns", [])
    nodes = {n.id: n for n in diagram.nodes}
    if not isinstance(unknowns, list) or any(not isinstance(n, str) or n not in nodes or nodes[n].kind != "free" for n in unknowns):
        fail("network unknowns must identify free-node temperatures")
    if len(unknowns) != len(set(unknowns)):
        fail("duplicate network unknown")
    from .model import QUANTITY
    targets = net.get('resistance_unknowns', [])
    if not isinstance(targets, list):
        fail('resistance_unknowns must be a list of branch IDs or indices')
    indices = []
    for target in targets:
        index = resistance_index(diagram, target)
        if index is None or QUANTITY.get(diagram.branches[index].kind) != 'R':
            fail('resistance unknown must identify an existing resistance branch')
        indices.append(index)
    if len(set(indices)) != len(indices):
        fail('duplicate resistance unknown')
    volumes = a.get("volumes", {})
    if not isinstance(volumes, dict):
        fail("volumes must map volume IDs to one target each")
    vs = {v.id: v for v in diagram.control_volumes}
    ts = {t.id: t for t in diagram.transfers}
    ss = {s.id: s for s in diagram.control_surfaces}
    for vid, target in volumes.items():
        if vid not in vs or not isinstance(target, dict) or set(target) != {"entity", "id", "field"}:
            fail("each volume needs an existing ID and an entity/id/field target")
        role, ident, name = target["entity"], target["id"], target["field"]
        if not all(isinstance(x, str) for x in (role, ident, name)):
            fail("target references must be text")
        if role == "volume":
            if ident != vid or name not in ("generation", "storage"):
                fail("volume target must be its generation or storage")
            if name == "storage" and vs[vid].steady:
                fail("steady state already fixes storage at zero")
        elif role == "transfer":
            t = ts.get(ident)
            if t is None or t.surface not in ss or ss[t.surface].volume != vid or name not in ("rate", "flux"):
                fail("transfer target must belong to the selected volume")
            if name == "flux" and t.kind != "heat":
                fail("only heat transfers have flux")
            if (name == "rate" and t.flux is not None) or (name == "flux" and t.rate is not None):
                fail("remove the alternate rate/flux source before selecting the unknown")
        else:
            fail("target entity must be volume or transfer")
    tol = a.get("tolerance", {})
    if not isinstance(tol, dict) or set(tol) - {"absolute_w", "relative"}:
        fail("tolerance accepts absolute_w and relative")
    for value in tol.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            fail("tolerances must be finite nonnegative numbers")
    if "provenance" in a and not isinstance(a["provenance"], dict):
        fail("provenance must be an object")


def fingerprint(diagram):
    data = diagram.to_dict()
    data.get("analysis", {}).pop("provenance", None)
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def resistance_index(diagram, target):
    if type(target) is int:
        return target if 0 <= target < len(diagram.branches) else None
    if isinstance(target, str):
        return next((i for i, b in enumerate(diagram.branches) if b.id == target), None)
    return None


@dataclass
class PhysicsResult:
    status: str
    input_hash: str
    components: List[Dict[str, Any]] = field(default_factory=list)
    volumes: List[Dict[str, Any]] = field(default_factory=list)
    updates: List[PhysicsUpdate] = field(default_factory=list)
    coverage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> PhysicsReport:
        return cast(PhysicsReport, copy.deepcopy(self.__dict__))

    def apply(self, diagram: "Diagram") -> "Diagram":
        from .model import DiagramError
        if fingerprint(diagram) != self.input_hash:
            raise DiagramError("physics result is stale; solve the current diagram again")
        out = copy.deepcopy(diagram)
        for u in self.updates:
            if u['entity'] == 'branch':
                out.branches[u['index']].value = u['value']
                continue
            entries = cast(List[Any], {"node": out.nodes, "volume": out.control_volumes, "transfer": out.transfers}[u["entity"]])
            obj = next(x for x in entries if x.id == u["id"])
            setattr(obj, u["field"], u["value"])
        out.analysis["provenance"] = {"input_hash": self.input_hash, "calculated": copy.deepcopy(self.updates)}
        return out.validate()


def _linear(rows, rhs, columns):
    """Scaled elimination, including rectangular systems and contradictory rows."""
    a = []
    for row, b in zip(rows, rhs):
        scale = max((abs(v) for v in row), default=0) or 1
        a.append([v / scale for v in row] + [b / scale])
    pivots: List[int] = []
    for col in range(columns):
        r = len(pivots)
        if r >= len(a):
            break
        best = max(range(r, len(a)), key=lambda i: abs(a[i][col]))
        if abs(a[best][col]) < 1e-12:
            continue
        a[r], a[best] = a[best], a[r]
        div = a[r][col]
        a[r] = [v / div for v in a[r]]
        for i in range(len(a)):
            if i != r:
                factor = a[i][col]
                a[i] = [x - factor*y for x, y in zip(a[i], a[r])]
        pivots.append(col)
    for row in a:
        if max((abs(v) for v in row[:-1]), default=0) < 1e-10 and abs(row[-1]) > 1e-7:
            return "inconsistent", []
    if len(pivots) < columns:
        return "underdetermined", []
    result = [0.0]*columns
    for i, col in enumerate(pivots):
        result[col] = a[i][-1]
    if not all(math.isfinite(x) for x in result):
        return "numerically-unreliable", []
    return "solved", result


def _network(d, result, check_supplied=False):
    from .model import R_SCALE, P_SCALE, QUANTITY, Node
    from ._physics import _folded
    config = d.analysis["network"]
    unknowns = set(config.get("unknowns", []))
    unknown_resistances = {resistance_index(d, t) for t in config.get('resistance_unknowns', [])}
    parent = {n.id: n.id for n in d.nodes}
    def root(x):
        while parent[x] != x:
            x = parent[x]
        return x
    def merge(a, b):
        parent[root(b)] = root(a)
    if d.rail:
        parent["rail"] = "rail"
    for b in d.branches:
        if b.kind == "link":
            merge(b.source, b.target)
    groups: Dict[str, List[Any]] = {}
    for n in d.nodes:
        groups.setdefault(root(n.id), []).append(n)
    if d.rail:
        reference = next(n for n in d.nodes if n.id == d.rail.reference)
        groups.setdefault(root("rail"), []).append(Node("rail", kind="fixed", value=None if reference.id in unknowns else reference.value))
    graph: Dict[str, Set[str]] = {g: set() for g in groups}
    for b in d.branches:
        if b.kind not in ("cap", "break"):
            a, c = root(b.source), root(b.target)
            graph[a].add(c); graph[c].add(a)
    pending = set(groups)
    while pending:
        first = next(g for g in groups if g in pending)
        component, todo = set(), [first]
        while todo:
            g = todo.pop()
            if g not in component:
                component.add(g); todo.extend(graph[g] - component)
        pending -= component
        ordered = [g for g in groups if g in component]
        report: Dict[str, Any] = {"nodes": [n.id for g in ordered for n in groups[g]], "status": "solved", "diagnostics": [], "assumptions": ["steady state; supplied resistances are constant"], "temperatures": {}, "branch_rates": [], "boundary_reactions": {}, "equations": []}
        result.components.append(report)
        missing, unsupported, known, fixed = [], [], {}, set()
        if not config.get("steady"):
            missing.append("declare steady state for network analysis")
        unit = d.units.get("T")
        if unit not in ("K", "°C", "C"):
            missing.append("temperature unit must be K or °C")
        offset = 273.15 if unit in ("°C", "C") and d.scale != "rise" else 0
        for g in ordered:
            vals = [number(n.value) for n in groups[g] if n.id not in unknowns]
            if any(v is None for v in vals):
                missing.append(f"{g}: supply temperature or mark it unknown")
            nums = [v+offset for v in vals if v is not None]
            if nums:
                known[g] = nums[0]
                if max(nums)-min(nums) > 1e-8:
                    report["status"] = "inconsistent"
                    report["diagnostics"].append(f"{g}: linked temperatures disagree")
            if any(n.kind == "fixed" for n in groups[g]) or d.rail and root("rail") == g:
                fixed.add(g)
                if g not in known:
                    missing.append(f"{g}: boundary temperature is required")
            if any(n.kind not in ("free", "fixed") for n in groups[g]):
                unsupported.append(f"{g}: phase-change or break node requires another physical model")
        power = {g: 0.0 for g in ordered}
        paths: List[Any] = []
        unknown_paths = {}
        for i, b in enumerate(d.branches):
            a, c = root(b.source), root(b.target)
            if a not in component and c not in component:
                continue
            ref = b.id or f"branch:{i}"
            if b.kind in ("cap", "break"):
                report["assumptions"].append(f"{ref}: zero steady heat rate")
                continue
            if b.kind == "link":
                report["branch_rates"].append({"id": ref, "watts": None, "reason": "ideal-link temperature constraint; individual link rate is not resolved"})
                continue
            if QUANTITY.get(b.kind) == "R":
                if i in unknown_resistances:
                    unknown_paths[i] = (i, b)
                    paths.append((a, c, None, i))
                    continue
                r = _folded(d, b)
                scale = R_SCALE.get(d.units.get("R", "K/W"))
                if r is None or r <= 0 or scale is None or not math.isfinite(r*scale) or r*scale <= 0:
                    missing.append(f"{ref}: positive resistance in supported units required")
                else:
                    paths.append((a, c, r*scale, i))
            elif b.kind == "flow":
                q = _folded(d, b)
                scale = P_SCALE.get(d.units.get("q", "W"))
                if q is None or scale is None:
                    missing.append(f"{ref}: numeric heat rate required")
                else:
                    power[a] -= q*scale; power[c] += q*scale
                    report["branch_rates"].append({"id": ref, "watts": q*scale})
            else:
                unsupported.append(f"{ref}: {b.kind} is unsupported in network solving")
        for i, s in enumerate(d.sources):
            g = root(s.node)
            if g not in component:
                continue
            if s.kind == "flux":
                unsupported.append(f"source:{i}: network flux has no physical area")
                continue
            q = number(s.value)
            scale = P_SCALE.get(d.units.get("P" if s.kind == "diss" else "q", "W"))
            if q is None or scale is None:
                missing.append(f"source:{i}: numeric power and supported unit required")
            else:
                power[g] += q*scale*(s.count or 1)*(-1 if s.outward else 1)
        if missing or unsupported or report["status"] != "solved":
            if report["status"] == "solved":
                report["status"] = "unsupported" if unsupported else "missing-inputs"
            report["diagnostics"] += missing + unsupported
            continue
        variables = [g for g in ordered if g not in known]
        rate_refs = list(unknown_paths)
        rows, rhs = [], []
        for g in ordered:
            if g in fixed:
                continue
            coeff = {j: 0.0 for j in ordered}
            rate_coeff = {ref: 0.0 for ref in rate_refs}
            for a, c, r, ref in paths:
                if a == c:
                    continue
                if r is None:
                    if g == a: rate_coeff[ref] += 1
                    if g == c: rate_coeff[ref] -= 1
                    continue
                if g in (a, c):
                    other = c if g == a else a
                    coeff[g] += 1/r; coeff[other] -= 1/r
            value = power[g]-sum(coeff[j]*known[j] for j in known)
            rows.append([coeff[j] for j in variables]+[rate_coeff[j] for j in rate_refs]); rhs.append(value)
            report["equations"].append({"node": g, "coefficients_w_per_k": coeff, "rate_coefficients": {f"branch:{i}": v for i, v in rate_coeff.items()}, "net_input_w": power[g], "known_temperatures_k": dict(known)})
        for ref, (index, branch) in unknown_paths.items():
            if branch.rate is not None:
                stated, qscale = number(branch.rate), P_SCALE.get(d.units.get('q', 'W'))
                if stated is None or qscale is None:
                    missing.append(f'{ref}: supply a numeric heat rate in supported units')
                    continue
                # The stable branch rate field is the whole group heat rate.
                row = [0.0]*(len(variables)+len(rate_refs))
                row[len(variables)+rate_refs.index(ref)] = 1
                # Supplied rate is a magnitude. Direction follows known temperatures;
                # otherwise conservation must resolve it, without guessing a sign.
                a, c = root(branch.source), root(branch.target)
                if a in known and c in known:
                    rows.append(row)
                    rhs.append(stated*qscale*(-1 if known[a] < known[c] else 1))
                elif stated == 0:
                    rows.append(row)
                    rhs.append(0.0)
        if missing:
            report['status'] = 'missing-inputs'; report['diagnostics'] += missing
            continue
        status, answer = ("solved", []) if check_supplied and not variables and not rate_refs else _linear(rows, rhs, len(variables)+len(rate_refs))
        report["status"] = status
        if status != "solved":
            report["diagnostics"].append("Conflicting temperatures or energy inputs" if status == "inconsistent" else "No unique temperature/heat-rate solution. Supply an additional independent temperature or branch heat rate; total heat alone cannot separate parallel unknown resistances." if rate_refs else "No unique, reliable temperature solution; check boundary temperatures and independent equations")
            continue
        temps = {**known, **dict(zip(variables, answer[:len(variables)]))}
        rates = dict(zip(rate_refs, answer[len(variables):]))
        resistance_updates: List[PhysicsUpdate] = []
        resolved_paths = []
        for a, c, r, ref in paths:
            if r is None:
                q, drop = rates[ref], temps[a]-temps[c]
                if q == 0:
                    report['status'] = 'underdetermined' if abs(drop) < 1e-10 else 'inconsistent'
                    report['diagnostics'].append(f'{ref}: resistance is indeterminate (zero heat rate and temperature drop)' if abs(drop) < 1e-10 else f'{ref}: nonzero temperature drop with zero heat rate has no finite resistance solution')
                    continue
                r = drop/q
                if not math.isfinite(r) or r <= 0:
                    report['status'] = 'inconsistent'
                    report['diagnostics'].append(f'{ref}: calculated resistance is nonpositive; check heat direction and supplied temperatures')
                    continue
                index, branch = unknown_paths[ref]
                scale = R_SCALE.get(d.units.get('R', 'K/W'))
                if scale is None:
                    report['status'] = 'missing-inputs';report['diagnostics'].append(f'{ref}: supported resistance units required');continue
                factor = d.fold(branch.kind, 1.0, branch.count, branch.arrangement) or 1.0
                per_item = r/scale/factor
                if not math.isfinite(per_item) or per_item <= 0:
                    report['status'] = 'numerically-unreliable';report['diagnostics'].append(f'{ref}: resistance exceeds reliable numerical range');continue
                resistance_updates.append({'entity':'branch', 'id':branch.id or f'branch:{ref}', 'index':index, 'field':'value', 'value':per_item, 'unit':d.units.get('R','K/W')})
            resolved_paths.append((a, c, r, ref))
        if report['status'] != 'solved':
            continue
        paths = resolved_paths
        outgoing = {g: 0.0 for g in ordered}
        sides = {g: [max(power[g], 0), max(-power[g], 0)] for g in ordered}
        for a, c, r, ref in paths:
            q = (temps[a]-temps[c])/r
            outgoing[a] += q; outgoing[c] -= q
            sides[a][1 if q >= 0 else 0] += abs(q)
            sides[c][0 if q >= 0 else 1] += abs(q)
            report["branch_rates"].append({"id": d.branches[ref].id or f"branch:{ref}", "index": ref, "watts": q, "temperature_difference_k": temps[a]-temps[c], "resistance_k_per_w": r})
        residuals = {g: power[g]-outgoing[g] for g in ordered if g not in fixed}
        report["residuals_w"] = residuals
        scale = max([1.0]+[abs(x) for x in outgoing.values()]+[abs(x) for x in power.values()])
        tol = d.analysis.get("tolerance", {})
        limits = {g: max(tol.get("absolute_w", .001), tol.get("relative", .01)*max(sides[g])) if check_supplied and not variables and not rate_refs else 1e-8*scale for g in residuals}
        report["tolerances_w"] = limits
        if any(not math.isfinite(v) or abs(v) > limits[g] for g, v in residuals.items()):
            report["status"] = "inconsistent" if check_supplied and not variables else "numerically-unreliable"
            report["diagnostics"].append("Supplied values do not balance within tolerance" if check_supplied and not variables else "Computed solution failed the energy residual check")
            continue
        if d.scale != "rise" and any(t < 0 for t in temps.values()):
            report["status"] = "inconsistent"
            report["diagnostics"].append("Calculated absolute temperature is below zero kelvin")
            continue
        report["boundary_reactions"] = {g: outgoing[g]-power[g] for g in fixed}
        report["overall_residual_w"] = sum(power.values())+sum(report["boundary_reactions"].values())
        for i, b in enumerate(d.branches):
            if b.rate is None or QUANTITY.get(b.kind) != "R" or root(b.source) not in component:
                continue
            stated = number(b.rate)
            qscale = P_SCALE.get(d.units.get("q", "W"))
            resistance = next((r for a, c, r, ref in paths if ref == i), None)
            if stated is None or qscale is None or resistance is None:
                report["status"] = "missing-inputs"
                report["diagnostics"].append(f"branch:{i}: supplied rate assertion must be numeric in supported units")
                continue
            # The rate label is the whole group, as in the legacy checker.
            calculated = abs(temps[root(b.source)]-temps[root(b.target)])/resistance
            tol = d.analysis.get("tolerance", {})
            if abs(stated*qscale-calculated) > max(tol.get("absolute_w", .001), tol.get("relative", .01)*max(abs(stated*qscale), abs(calculated))):
                report["status"] = "inconsistent"
                report["diagnostics"].append(f"branch:{i}: supplied rate disagrees with the temperature drop and resistance")
        if report["status"] != "solved":
            continue
        report["temperatures"] = {n.id: temps[g]-offset for g in ordered for n in groups[g]}
        report["temperature_unit"] = unit
        result.updates.extend(resistance_updates)
        for n in report["nodes"]:
            if n in unknowns:
                result.updates.append({"entity": "node", "id": n, "field": "value", "value": report["temperatures"][n], "unit": unit})


def _volumes(d, result):
    for vid, target in d.analysis.get("volumes", {}).items():
        work = copy.deepcopy(d)
        objects = work.transfers if target["entity"] == "transfer" else work.control_volumes
        obj = next(o for o in objects if o.id == target["id"])
        setattr(obj, target["field"], 0)
        zero = next(b for b in budgets(work, tolerance=d.analysis.get("tolerance")) if b["id"] == vid)
        report = {"id": vid, "target": target, "status": "solved", "equation": "incoming - outgoing + generation - storage = 0", "diagnostics": []}
        result.volumes.append(report)
        if zero["missing"]:
            report.update(status="missing-inputs", diagnostics=zero["missing"])
            continue
        if target["entity"] == "volume":
            coefficient = POWER[obj.unit] * (-1 if target["field"] == "storage" else 1)
        else:
            coefficient = POWER[obj.unit]
            if target["field"] == "flux":
                surface = next(s for s in work.control_surfaces if s.id == obj.surface)
                area = number(surface.area)
                assert area is not None  # Missing areas were reported by budgets above.
                coefficient = FLUX[obj.flux_unit] * area * AREA[surface.area_unit]
            coefficient *= 1 if obj.direction == "in" else -1
        if not coefficient or not math.isfinite(coefficient):
            report.update(status="numerically-unreliable", diagnostics=["Unknown has no resolvable coefficient; check area and units"])
            continue
        value = -zero["residual"]/coefficient
        if not math.isfinite(value):
            report.update(status="numerically-unreliable", diagnostics=["Calculated value is not finite"])
            continue
        if target["entity"] == "transfer" and value < 0:
            report.update(status="direction-conflict", diagnostics=["Calculated magnitude is negative; review the declared transfer direction"])
            continue
        setattr(obj, target["field"], value)
        final = next(b for b in budgets(work, tolerance=d.analysis.get("tolerance")) if b["id"] == vid)
        tolerance = final["tolerance"]
        if abs(final["residual"]) > tolerance:
            report.update(status="numerically-unreliable", diagnostics=["Calculated balance failed residual verification"])
            continue
        unit = getattr(obj, "flux_unit", "") if target["field"] == "flux" else obj.unit
        report.update(value=value, unit=unit, coefficient_w=coefficient, known_residual_w=zero["residual"], totals=final, tolerance_w=tolerance)
        result.updates.append({**target, "value": value, "unit": unit})


def solve_physics(diagram: Union["Diagram", "DiagramBuilder"], *, check_supplied: bool = False) -> PhysicsResult:
    from .builder import DiagramBuilder
    d = diagram.build() if isinstance(diagram, DiagramBuilder) else diagram
    d.validate()
    result = PhysicsResult("not-configured", fingerprint(d))
    if "network" in d.analysis:
        _network(d, result, check_supplied=check_supplied)
    _volumes(d, result)
    for budget in budgets(d, tolerance=d.analysis.get("tolerance")):
        if budget["id"] not in d.analysis.get("volumes", {}):
            result.volumes.append({"id": budget["id"], "status": budget["status"],
                                   "diagnostics": budget["missing"], "totals": budget,
                                   "mode": "check-supplied", "equation": "incoming - outgoing + generation - storage = 0"})
    result.coverage = {"network_configured": "network" in d.analysis,
                       "unselected_volumes": [v.id for v in d.control_volumes if v.id not in d.analysis.get("volumes", {})],
                       "detached_transfers": [t.id for t in d.transfers if t.surface is None],
                       "limits": "Constant resistances, including identifiable resistance unknowns; no transient, nonlinear radiation, material-law or mass-flow derivation. Network links are descriptive associations."}
    # Never serialize NaN/Infinity as apparently usable physical results.
    def clean(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items()}
        if isinstance(value, list):
            return [clean(v) for v in value]
        return value
    for reports in (result.components, result.volumes):
        for i, report in enumerate(reports):
            try:
                json.dumps(report, allow_nan=False)
            except ValueError:
                report["status"] = "numerically-unreliable"
                report["diagnostics"].append("Values exceed reliable numerical range; rescale supplied units or magnitudes")
                reports[i] = clean(report)
    successful_nodes = {n for c in result.components if c["status"] == "solved" for n in c["nodes"]}
    successful_targets = [v.get("target") for v in result.volumes if v["status"] == "solved"]
    result.updates = [u for u in result.updates if (u["entity"] == 'branch' and d.branches[u['index']].source in successful_nodes) or (u["entity"] == "node" and u["id"] in successful_nodes) or
                      {k: u[k] for k in ("entity", "id", "field")} in successful_targets]
    statuses = [r["status"] for r in result.components+result.volumes]
    if statuses:
        result.status = "solved" if all(s in ("solved", "balanced") for s in statuses) else "partial" if any(s in ("solved", "balanced") for s in statuses) else "not-solved"
    return result
