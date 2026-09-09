"""Do the numbers on the page agree with each other? Behind a flag, by choice.

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
import math
from typing import Dict, List, Optional, Tuple
from ._physical import number

from . import model as M
from ._check import Finding

# Relative disagreement a node may carry before it is reported. Temperatures
# on real diagrams are whole degrees, and a degree on a seven-degree drop is
# fourteen percent, so this is loose on purpose.
SLACK = 0.15

# Scale to K/W and W. A unit not in one makes the check skip the diagram,
# not guess. They live in `model` because a stream's label states the number
# this check balances against, and one table is what stops the two from
# disagreeing; re-exported here, where every reader of them already looks.
R_SCALE, P_SCALE = M.R_SCALE, M.P_SCALE

RESISTANCES = {k for k, q in M.QUANTITY.items()
               if q == "R" and k in M.BRANCH_KINDS}


def _num(value) -> Optional[float]:
    return number(value)


def _folded(diagram, b) -> Optional[float]:
    """What the whole group presents, or the item's own value if it is one.

    `model.FOLD` is the single table, so the number this check works from and
    the number drawn on the page cannot disagree. There used to be a second
    copy here that knew about resistances and not about rates, and a `flow`
    branch's per-item value went in raw.
    """
    folded = diagram.fold(b.kind, b.value, b.count, b.arrangement)
    return _num(b.value) if folded is None else number(folded)


def _fmt(x: float) -> str:
    return f"{x:,.3g}" if abs(x) < 1e6 else f"{x:.2e}"


class _Net:
    """The network with its numbers read, and its links merged.

    A `link` says its two ends are one place. Kirchhoff is written about a
    place, not about a name for one, so the merge happens here — before
    anything is summed — and every endpoint below is a *representative*: the
    member of the group written first, which keeps the messages stable and
    names the group something the author will recognise.
    """

    def __init__(self, diagram):
        rank = {n.id: i for i, n in enumerate(diagram.nodes)}
        parent = {n.id: n.id for n in diagram.nodes}
        if diagram.rail:
            rank[M.RAIL], parent[M.RAIL] = len(rank), M.RAIL

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for b in diagram.branches:
            if b.kind != "link":
                continue
            ra, rb = find(b.source), find(b.target)
            if ra != rb:
                # The one written first wins, so the group is named after the
                # node the author introduced it by.
                first, second = sorted((ra, rb), key=lambda i: rank[i])
                parent[second] = first
        self.rep: Dict[str, str] = {k: find(k) for k in parent}
        self.group: Dict[str, List[str]] = {}
        for node_id in sorted(parent, key=lambda i: rank[i]):
            self.group.setdefault(self.rep[node_id], []).append(node_id)

        stated = {n.id: _num(n.value) for n in diagram.nodes}
        if diagram.rail:
            # `rail.reference` "records which node the rail is, for a reader
            # and for a later version". This is the later version.
            stated[M.RAIL] = stated.get(diagram.rail.reference)
        kind_of = {n.id: n.kind for n in diagram.nodes}
        if diagram.rail:
            kind_of[M.RAIL] = "fixed"
        # A group's temperature is the first one any of its members states,
        # and its kind is free only if every member is: one boundary in a
        # group makes the whole place a reservoir, which is what a link to a
        # wall means.
        self.temps: Dict[str, Optional[float]] = {}
        self.kinds: Dict[str, str] = {}
        for rep, members in self.group.items():
            temp = next((stated[m] for m in members
                         if stated[m] is not None), None)
            anchored = next((kind_of[m] for m in members
                             if kind_of[m] != "free"), None)
            for m in members:
                self.temps[m] = temp
                self.kinds[m] = anchored or "free"

        r_scale = R_SCALE[diagram.units.get("R", "K/W")]
        # (a, b, R, label) for every resistance path
        self.paths: List[Tuple[str, str, Optional[float], str]] = []
        self.flows: List[Tuple[str, str, Optional[float], str]] = []
        # A stream is a rate like a flow, but one it works out rather than
        # states, and it acts at one end only — so it is its own list.
        self.streams: List[Tuple[str, str, Optional[float], str]] = []
        for i, b in enumerate(diagram.branches):
            label = f"branch {i} {b.source}->{b.target}"
            ends = (self.rep[b.source], self.rep[b.target])
            if b.kind in RESISTANCES:
                r = _folded(diagram, b)
                self.paths.append((*ends,
                                   None if r is None else number(r * r_scale), label))
            elif b.kind == "flow":
                self.flows.append((*ends, _folded(diagram, b), label))
            elif b.kind == "stream":
                # Worked out here, where both ends' temperatures are already
                # resolved, and by the diagram's own method, so this is the
                # same number the box states.
                self.streams.append((
                    *ends,
                    diagram.carried(b, self.temps.get(self.rep[b.source]),
                                    self.temps.get(self.rep[b.target])),
                    label))


def _grouped(skipped) -> str:
    """`a, b (reason); c (other reason)`, in the order first met."""
    by_reason: Dict[str, List[str]] = {}
    for who, why in skipped:
        by_reason.setdefault(why, []).append(who)
    return "; ".join(f"{', '.join(who)} ({why})"
                     for why, who in by_reason.items())


def balance(diagram) -> List[Finding]:
    """Findings for every free node whose stated numbers do not close.

    And one `note` saying which free nodes it could not ask, and why. Every
    skip used to be silent, and the worst one was invisible from the file:
    a free node beside a node with no temperature was dropped, and the
    node with no temperature is the idiom `docs/schema.md` recommends for
    an interior junction. One clean-room reader's worst-balanced node was
    absent from the report; another counted three of eight nodes never
    examined, and both asked for one line saying so.
    """
    out: List[Finding] = []
    units = diagram.units
    # `mdot` and `cp` only where a stream actually uses them: a diagram
    # without one has no entry to check, and demanding a default would be
    # asking every drawing about a quantity it does not state.
    streaming = any(b.kind == "stream" for b in diagram.branches)
    gates = [("R", R_SCALE, "K/W"), ("P", P_SCALE, "W"), ("q", P_SCALE, "W")]
    if streaming:
        gates += [(M.MDOT, M.MDOT_SCALE, ""), (M.CP, M.CP_SCALE, "")]
    for quantity, table, default in gates:
        unit = units.get(quantity, default)
        if unit not in table:
            out.append(Finding(
                "physics-not-checked", "note", "the diagram",
                f"nothing was checked: `units` gives {quantity!r} as "
                f"{unit!r}, and the check knows only "
                + ", ".join(table),
                remedy="state it in one of those, or read the diagram as "
                       "unchecked"))
            return out
    p_scale, q_scale = P_SCALE[units.get("P", "W")], P_SCALE[units.get("q", "W")]
    net = _Net(diagram)

    # A link claims its two ends are the same place. Two different numbers on
    # one place is a contradiction rather than a disagreement, so this is not
    # measured against SLACK: that tolerance exists because temperatures are
    # quoted in whole degrees, and no rounding makes 48 and 51 the same
    # reading.
    t_unit = units.get("T", "")
    for i, b in enumerate(diagram.branches):
        if b.kind != "link":
            continue
        def stated_temperature(node_id):
            if node_id == M.RAIL:
                node_id = diagram.rail.reference
            return _num(diagram.node(node_id).value)
        ta, tb = stated_temperature(b.source), stated_temperature(b.target)
        if ta is None or tb is None or abs(ta - tb) <= 1e-9:
            continue
        out.append(Finding(
            "link-temperatures-disagree", "warning",
            f"branch {i} {b.source}->{b.target}",
            # `:g`, not `_fmt`: that is tuned for watts, which run to seven
            # figures, and it printed a 1520 K wall as `1.52e+03 K`.
            f"branch {i} {b.source}->{b.target} is a link, so {b.source!r} "
            f"and {b.target!r} are one place, and they state "
            f"{ta:g} {t_unit} and {tb:g} {t_unit}".rstrip(),
            remedy="give both ends the same temperature, or if heat drops "
                   "between them, say what carries it: a link states that "
                   "nothing does",
            at=tuple(b.at) if b.at else None))

    # One balance per place, not per name: a linked group is one node here,
    # represented by the member written first.
    free = [diagram.node(rep) for rep in net.group
            if rep != M.RAIL and net.kinds.get(rep) == "free"]
    skipped: List[Tuple[str, str]] = []

    for n in free:
        joined = [m for m in net.group[n.id] if m != n.id]
        # Named as the author will recognise it: the group's own name, and
        # the other names it answers to. The skip list does not quote its
        # subjects and the findings do, so both forms are kept rather than
        # changing the wording of a message this work is not about.
        linked = (" (linked to " + ", ".join(map(repr, joined)) + ")"
                  if joined else "")
        who, plain = f"'{n.id}'" + linked, n.id + linked
        here = net.temps.get(n.id)
        if here is None:
            skipped.append((plain, "it has no temperature"))
            continue
        arrive, leave, said = 0.0, 0.0, []
        why = None

        for i, s in enumerate(diagram.sources):
            # Through the merge: heat arriving at any name for this place
            # arrives at this place.
            if net.rep[s.node] != n.id:
                continue
            if s.kind == "flux":
                why = f"source {i} is a flux, which has no area"
                break
            v = _num(s.value)
            if v is None:
                why = f"source {i} has no numeric value"
                break
            v *= (p_scale if s.kind == "diss" else q_scale) * (s.count or 1)
            inward = -v if s.outward else v
            if inward < 0:
                leave += -inward
                said.append(f"{_fmt(-inward)} W out by source {i}")
            else:
                arrive += inward
                said.append(f"{_fmt(inward)} W in by source {i}")

        for a, b, q, label in net.flows:
            if why or n.id not in (a, b):
                continue
            if q is None:
                why = f"{label} has no numeric value"
                break
            q *= q_scale
            outward = q if a == n.id else -q
            if outward >= 0:
                leave += outward
                said.append(f"{_fmt(outward)} W out by {label}")
            else:
                arrive += -outward
                said.append(f"{_fmt(-outward)} W in by {label}")

        for a, b, q, label in net.streams:
            if why or n.id not in (a, b):
                continue
            if q is None:
                why = (f"{label} is a stream and one of its ends states no "
                       "temperature, so what it carries is not worked out")
                break
            # The sign, in one place. A stream is not a conductance: a
            # conductance carries heat from hot to cold, and a stream carries
            # it from inlet to outlet, up the gradient, because the mass is
            # doing the carrying. What it takes away, it takes away where it
            # leaves — nothing happens at the inlet, which is where the
            # medium arrives from outside the drawing. A cooled stream needs
            # no second rule: its `q` is negative and the same line adds heat
            # to the outlet, which is what a hot fluid does to what it meets.
            if b != n.id:
                continue
            q *= q_scale
            # Split on the sign and add a positive number, as the flows and
            # paths loops above already do. `leave += q` with a negative `q`
            # read correctly in the sum and then broke the test of it:
            # `biggest = max(arrive, leave)` takes both for non-negative, so
            # a cooled stream drove `leave` below zero, `biggest` came out 0
            # and the node was skipped in silence -- the check passing
            # because it never ran. A cooled stream delivers; hot water
            # arriving at a radiator is not carrying off a negative amount.
            if q >= 0:
                leave += q
                said.append(f"{_fmt(q)} W carried off by {label}")
            else:
                arrive += -q
                said.append(f"{_fmt(-q)} W delivered by {label}")

        for a, b, r, label in net.paths:
            if why or n.id not in (a, b):
                continue
            if a == b:
                # A resistance whose two ends a link has merged. What it
                # carries is not determined by the stated values — an ideal
                # short across it decides that — so it is left out of the sum
                # rather than counted as zero at both ends.
                continue
            other = b if a == n.id else a
            there = net.temps.get(other)
            if r is None:
                why = f"{label} has no numeric value"
                break
            if there is None:
                why = f"neighbour '{other}' has no temperature"
                break
            if r <= 0:
                why = f"{label} has a resistance of zero"
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
        if not all(math.isfinite(v) for v in (arrive, leave)):
            why = "energy calculation exceeded numerical range"
        if why is None and not said:
            why = "nothing is attached to it"
        if why:
            skipped.append((plain, why))
            continue

        biggest = max(arrive, leave)
        if biggest == 0 or abs(arrive - leave) <= SLACK * biggest:
            continue
        out.append(Finding(
            "node-does-not-balance", "warning", f"node {who}",
            f"node {who}: {_fmt(arrive)} W arrives and {_fmt(leave)} W "
            f"leaves at the stated values: " + "; ".join(said),
            remedy="check the values. If one box stands for several identical "
                   "paths, give it `count` and `arrangement`; if a temperature "
                   "is a limit rather than a result, or a flow is a capacity "
                   "rather than a load, say so in the `label`",
            at=tuple(n.at) if n.at else None))

    # A branch that states what it carries, beside what its ends imply.
    r_scale = R_SCALE[units.get("R", "K/W")]
    def unchecked_rate(index, reason):
        out.append(Finding("physics-not-checked", "note", f"branch {index}",
                           f"branch {index}: rate not checked: {reason}",
                           remedy="Supply finite temperatures, a positive resistance and a finite rate in supported units."))
    for i, b in enumerate(diagram.branches):
        if b.rate is None or b.kind not in RESISTANCES:
            continue
        rate, r = _num(b.rate), _num(b.value)
        ta, tb = net.temps.get(b.source), net.temps.get(b.target)
        if rate is None or r is None or ta is None or tb is None or r <= 0:
            unchecked_rate(i, "missing or nonfinite numeric inputs")
            continue
        r_eff = (_folded(diagram, b) or r) * r_scale
        if not math.isfinite(r_eff) or r_eff <= 0:
            unchecked_rate(i, "resistance exceeded numerical range")
            continue
        implied = abs(ta - tb) / r_eff
        stated = rate * q_scale
        if not all(math.isfinite(v) for v in (implied, stated)):
            unchecked_rate(i, "rate calculation exceeded numerical range")
            continue
        if abs(implied - stated) <= SLACK * max(implied, stated, 1e-12):
            continue
        out.append(Finding(
            "rate-does-not-match", "warning", f"branch {i} {b.source}->{b.target}",
            f"branch {i} {b.source}->{b.target} says it carries "
            f"{_fmt(stated)} W, and its ends imply {_fmt(implied)} W "
            f"({_fmt(abs(ta - tb))} K over {_fmt(r_eff)} K/W)",
            remedy="one of `rate`, `value` or an end temperature is wrong",
            at=tuple(b.at) if b.at else None))

    if skipped:
        checked = len(free) - len(skipped)
        out.append(Finding(
            "physics-not-checked", "note", "the diagram",
            # "places" rather than "nodes": a linked group is one of these
            # and answers to several names.
            f"checked {checked} of {len(free)} free places; not checked: "
            + _grouped(skipped),
            remedy="give the node, or its neighbour, a `value`, or read "
                   "those nodes as unchecked"))

    # The balance above uses differences, so it is the same on either
    # scale. A radiation resistance is not: it is linearised at a pair of
    # absolute temperatures, and a diagram that declares its temperatures
    # as a rise above ambient has no absolute temperature anywhere on the
    # page to have taken it at. Only a declared rise fires it; an
    # undeclared scale is exactly that, and a note on every `rad` would be
    # a footnote wearing a severity.
    if diagram.scale == "rise":
        for i, b in enumerate(diagram.branches):
            if b.kind == "rad" and _num(b.value) is not None:
                out.append(Finding(
                    "rad-needs-absolute-scale", "note",
                    f"branch {i} {b.source}->{b.target}",
                    f"branch {i} {b.source}->{b.target} is a radiation "
                    "path with a value, and the temperatures are declared "
                    "as a rise above ambient: a radiation resistance holds "
                    "at a pair of absolute temperatures this diagram "
                    "cannot state",
                    remedy="declare `units.T` as absolute and give absolute "
                           "temperatures, or read the value as linearised "
                           "at an operating point the page does not show",
                    at=tuple(b.at) if b.at else None))
    return out
