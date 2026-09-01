"""Do the numbers on the page agree with each other? — a prototype, behind a flag.

Every check in `_check` is about how the drawing reads. None is about what it
says. `model` holds every number a thermal network needs — temperatures,
resistances, powers, rates — and until this nothing read one for consistency.

This does the one thing that needs no model of anything: Kirchhoff at a node.
Heat that arrives at a free node by sources and flows must leave it, and what
leaves by a resistance is `(T_here - T_there) / R`, straight from the stated
values. A box that stands for several identical paths is folded by `count`
and `arrangement`, which is what those fields are for.

It fires only on a diagram whose own numbers disagree. That is the
discrimination the design record demands of a finding: its recorded objection
to physics checks is to ones that would fire on every instance of a symbol,
and this is not one of those.

    thermodraw check --physics diagram.json

Steady state throughout. A capacitance carries nothing, a break carries
nothing, a fixed node is a reservoir and is not asked to balance, and a
phase-change node is holding latent heat that this cannot see, so it is not
asked either. A `flux` source is per unit area with no area to hand, so a node
carrying one is skipped rather than guessed at.
"""
from typing import Dict, List, Optional, Tuple

from . import model as M
from ._check import Finding

# Relative disagreement a node may carry before it is reported. Temperatures
# on real diagrams are whole degrees, and a degree on a seven-degree drop is
# fourteen percent, so this is loose on purpose.
SLACK = 0.15

# Scale to K/W and W. A unit not here makes the check skip the diagram, not
# guess.
R_SCALE = {"K/W": 1.0, "°C/W": 1.0, "C/W": 1.0, "mK/W": 1e-3, "K/kW": 1e-3}
P_SCALE = {"W": 1.0, "kW": 1e3, "mW": 1e-3}

RESISTANCES = {k for k, q in M.QUANTITY.items()
               if q == "R" and k in M.BRANCH_KINDS}


def _num(value) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _effective(b, r: float) -> float:
    """Resistance of the whole group `count` and `arrangement` describe."""
    if not b.repeated:
        return r
    return r / b.count if b.arrangement == "parallel" else r * b.count


def _fmt(x: float) -> str:
    return f"{x:,.3g}" if abs(x) < 1e6 else f"{x:.2e}"


class _Net:
    """The network with its numbers read, corners folded away."""

    def __init__(self, diagram):
        self.temps: Dict[str, Optional[float]] = {
            n.id: _num(n.value) for n in diagram.nodes}
        self.kinds: Dict[str, str] = {n.id: n.kind for n in diagram.nodes}
        if diagram.rail:
            # `rail.reference` "records which node the rail is, for a reader
            # and for a later version". This is the later version.
            self.temps[M.RAIL] = self.temps.get(diagram.rail.reference)
            self.kinds[M.RAIL] = "fixed"
        r_scale = R_SCALE[diagram.units.get("R", "K/W")]
        # (a, b, R, label) for every resistance path, then corners folded
        self.paths: List[Tuple[str, str, Optional[float], str]] = []
        self.flows: List[Tuple[str, str, Optional[float], str]] = []
        for i, b in enumerate(diagram.branches):
            label = f"branch {i} {b.source}->{b.target}"
            if b.kind in RESISTANCES:
                r = _num(b.value)
                r = None if r is None else _effective(b, r * r_scale)
                self.paths.append((b.source, b.target, r, label))
            elif b.kind == "flow":
                q = _num(b.value)
                self.flows.append((b.source, b.target, q, label))
        self._fold_corners()

    def _fold_corners(self):
        """A chain of resistances through a corner is one resistance."""
        changed = True
        while changed:
            changed = False
            for node, kind in self.kinds.items():
                if kind != "corner":
                    continue
                here = [p for p in self.paths if node in (p[0], p[1])]
                others = [f for f in self.flows if node in (f[0], f[1])]
                if len(here) != 2 or others:
                    continue
                (a1, b1, r1, l1), (a2, b2, r2, l2) = here
                far1 = b1 if a1 == node else a1
                far2 = b2 if a2 == node else a2
                r = None if r1 is None or r2 is None else r1 + r2
                self.paths = [p for p in self.paths if p not in here]
                self.paths.append((far1, far2, r, f"{l1} + {l2}"))
                changed = True
                break


def balance(diagram) -> List[Finding]:
    """Findings for every free node whose stated numbers do not close."""
    out: List[Finding] = []
    units = diagram.units
    if (units.get("R", "K/W") not in R_SCALE
            or units.get("P", "W") not in P_SCALE
            or units.get("q", "W") not in P_SCALE):
        return out
    p_scale, q_scale = P_SCALE[units.get("P", "W")], P_SCALE[units.get("q", "W")]
    net = _Net(diagram)

    for n in diagram.nodes:
        here = net.temps.get(n.id)
        if n.kind != "free" or here is None:
            continue
        arrive, leave, said, known = 0.0, 0.0, [], True

        for i, s in enumerate(diagram.sources):
            if s.node != n.id:
                continue
            if s.kind == "flux":
                known = False
                break
            v = _num(s.value)
            if v is None:
                known = False
                break
            v *= (p_scale if s.kind == "diss" else q_scale) * (s.count or 1)
            if s.outward:
                leave += v
                said.append(f"{_fmt(v)} W out by source {i}")
            else:
                arrive += v
                said.append(f"{_fmt(v)} W in by source {i}")
        if not known:
            continue

        for a, b, q, label in net.flows:
            if n.id not in (a, b):
                continue
            if q is None:
                known = False
                break
            q *= q_scale
            if a == n.id:
                leave += q
                said.append(f"{_fmt(q)} W out by {label}")
            else:
                arrive += q
                said.append(f"{_fmt(q)} W in by {label}")
        if not known:
            continue

        for a, b, r, label in net.paths:
            if n.id not in (a, b):
                continue
            other = b if a == n.id else a
            there = net.temps.get(other)
            if r is None or there is None or r <= 0:
                known = False
                break
            q = (here - there) / r
            if q >= 0:
                leave += q
                said.append(f"{_fmt(q)} W out by {label} "
                            f"({_fmt(here - there)} K over {_fmt(r)} K/W)")
            else:
                arrive += -q
                said.append(f"{_fmt(-q)} W in by {label} "
                            f"({_fmt(there - here)} K over {_fmt(r)} K/W)")
        if not known or not said:
            continue

        biggest = max(arrive, leave)
        if biggest == 0 or abs(arrive - leave) <= SLACK * biggest:
            continue
        out.append(Finding(
            "node-does-not-balance", "warning", f"node '{n.id}'",
            f"node '{n.id}': {_fmt(arrive)} W arrives and {_fmt(leave)} W "
            f"leaves at the stated values — " + "; ".join(said),
            remedy="check the values. If one box stands for several identical "
                   "paths, give it `count` and `arrangement`; if a temperature "
                   "is a limit rather than a result, or a flow is a capacity "
                   "rather than a load, say so in the `label`",
            at=tuple(n.at) if n.at else None))

    # A branch that states what it carries, beside what its ends imply.
    r_scale = R_SCALE[units.get("R", "K/W")]
    for i, b in enumerate(diagram.branches):
        if b.rate is None or b.kind not in RESISTANCES:
            continue
        rate, r = _num(b.rate), _num(b.value)
        ta, tb = net.temps.get(b.source), net.temps.get(b.target)
        if rate is None or r is None or ta is None or tb is None or r <= 0:
            continue
        r_eff = _effective(b, r * r_scale)
        implied = abs(ta - tb) / r_eff
        stated = rate * q_scale
        if abs(implied - stated) <= SLACK * max(implied, stated, 1e-12):
            continue
        out.append(Finding(
            "rate-does-not-match", "warning", f"branch {i} {b.source}->{b.target}",
            f"branch {i} {b.source}->{b.target} says it carries "
            f"{_fmt(stated)} W, and its ends imply {_fmt(implied)} W "
            f"({_fmt(abs(ta - tb))} K over {_fmt(r_eff)} K/W)",
            remedy="one of `rate`, `value` or an end temperature is wrong",
            at=tuple(b.at) if b.at else None))
    return out
