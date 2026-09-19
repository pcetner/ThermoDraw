"""Additive assignment workflows; legacy drawing and numeric meanings remain intact."""
import copy
import math
from typing import TYPE_CHECKING, Any, Dict
if TYPE_CHECKING:
    from .model import Diagram
from ._units import parse_unit, unit_scale
from ._physical import number


def policy(d):
    if d.analysis.get('check_policy', 'legacy') == 'legacy':
        return .15, 0.0
    tol = d.analysis.get('tolerance', {})
    return tol.get('relative', .01), tol.get('absolute_w', .001)


def basis(d):
    b = d.network_basis
    kind = b.get('kind', 'total')
    if kind == 'total':
        return kind, 1.0
    value = number(b.get('value'))
    expected = 'm²' if kind == 'area' else 'm'
    factor, dim = parse_unit(b.get('unit', ''))
    if dim != parse_unit(expected)[1] or value is None or value <= 0:
        raise ValueError(f'network_basis: positive reference value in {expected} required')
    result = value * factor
    if not math.isfinite(result) or result <= 0:
        raise ValueError('network_basis: reference exceeds numerical range')
    return kind, result


def network_scale(d, quantity):
    kind, reference = basis(d)
    suffix = {'total': '', 'area': '*m^2', 'length': '*m'}[kind]
    expected = 'K'+suffix+'/W' if quantity == 'R' else ('W' if not suffix else 'W/('+suffix[1:]+')')
    unit = d.units.get(quantity, 'K/W' if quantity == 'R' else 'W')
    scale, dim = parse_unit(unit)
    if dim != parse_unit(expected)[1]:
        raise ValueError(f'units.{quantity}: {unit!r} has incompatible dimensions; expected {expected} for {kind} basis')
    return scale / reference if quantity == 'R' else scale * reference


def validate_extensions(d):
    from .model import DiagramError, QUANTITY
    def fail(message):
        raise DiagramError(message)
    try:
        if not isinstance(d.network_basis, dict) or set(d.network_basis)-{'kind','value','unit'}:
            fail('network_basis accepts kind, value and unit')
        if d.network_basis.get('kind','total') not in ('total','area','length'):
            fail('network_basis.kind must be total, area or length')
        basis(d)
        opts = d.layout_options
        if not isinstance(opts, dict) or set(opts)-{'max_width','wrap','stack','starts'}:
            fail('layout_options accepts max_width, wrap, stack and starts')
        if 'max_width' in opts and (isinstance(opts['max_width'], (str, bool)) or number(opts['max_width']) is None or float(opts['max_width']) <= 0):
            fail('layout_options.max_width must be positive')
        for flag in ('wrap','stack'):
            if flag in opts and not isinstance(opts[flag],bool): fail(f'layout_options.{flag} must be boolean')
        ids = {n.id for n in d.nodes}
        starts = opts.get('starts', [])
        if not isinstance(starts,list) or any(not isinstance(n,str) or n not in ids for n in starts) or len(starts)!=len(set(starts)):
            fail('layout_options.starts must list distinct existing endpoint node IDs')
        if not isinstance(d.cases, list): fail('cases must be a list')
        membership = {}
        names = set()
        for group in d.cases:
            if not isinstance(group,dict) or set(group)-{'id','label','nodes'} or not isinstance(group.get('id'),str) or not group['id'] or group['id'] in names:
                fail('cases require unique IDs, optional label, and nodes')
            names.add(group['id'])
            if not isinstance(group.get('nodes'),list) or not group['nodes']: fail('cases.nodes must be nonempty')
            for node in group['nodes']:
                if not isinstance(node,str) or node not in ids or node in membership: fail('case nodes must exist and belong to only one case')
                membership[node]=group['id']
        for branch in d.branches:
            if branch.rate_convention not in (None,'signed'): fail('rate_convention must be signed or omitted')
            if branch.rate_convention and QUANTITY.get(branch.kind)!='R': fail('signed rate_convention requires a resistance branch')
            if branch.source in membership and branch.target in membership and membership[branch.source]!=membership[branch.target]: fail('a branch cannot cross case groups')
            if branch.derivation is not None and not isinstance(branch.derivation,dict): fail('derivation must be an object')
        for obj in [*d.nodes,*d.branches,*d.sources,*d.regions,*d.control_volumes,*d.control_surfaces,*d.transfers,*d.annotations]:
            for flag in ('show_label','label_inside'):
                value=getattr(obj,flag,None)
                if value is not None and not isinstance(value,bool): fail(f'{flag} must be boolean')
            runs=getattr(obj,'label_runs',None)
            if runs is not None and (not isinstance(runs,list) or any(not isinstance(r,dict) or set(r)-{'text','position'} or not isinstance(r.get('text'),str) or r.get('position','normal') not in ('normal','subscript','superscript') for r in runs)):
                fail('label_runs requires text and normal/subscript/superscript position')
        if d.temperature_reference is not None and not isinstance(d.temperature_reference,str): fail('temperature_reference must be text')
    except (ValueError, TypeError, OverflowError) as exc:
        fail(str(exc))


def trust_findings(d):
    from ._check import Finding
    out=[]
    for i,s in enumerate(d.sources):
        n=number(s.value)
        if n is not None and n<0:
            out.append(Finding('source-direction-conflict','warning',f'source {i}',
                f'source {i}: negative magnitude reverses the drawn arrow',
                remedy='Explicitly reverse the endpoint direction and use a positive magnitude; convert to an outward flow if the source kind requires it.'))
    if d.units.get('R')=='mK/W':
        out.append(Finding('unit-spelling-clarification','note','units.R',
            'mK/W means millikelvin per watt (0.001 K/W), not metre-kelvin per watt.',
            remedy='Use m*K/W or m·K/W with a length network_basis for resistance per length.'))
    if any(b.kind=='cap' and b.value is not None for b in d.branches):
        try: unit_scale(d.units.get('C',''),'C')
        except (ValueError,KeyError,OverflowError):
            out.append(Finding('capacitance-unit-invalid','warning','units.C',
                f"{d.units.get('C')!r} is not energy per temperature; capacitance calculations are unchecked.",
                remedy='Supply capacitance in J/K or dimensionally equivalent units.'))
    return out


def total_network(d):
    """Convert only network data to actual watts/K per declared reference, on a copy."""
    if d.network_basis.get('kind','total')=='total': return d
    from .model import QUANTITY
    out=copy.deepcopy(d)
    if any(b.kind=='stream' for b in d.branches): raise ValueError('normalized stream analysis is unsupported; use a total network')
    scales={q:network_scale(d,q) for q in ({'R','q'} | ({'P'} if any(s.kind=='diss' for s in d.sources) else set()))}
    for b in out.branches:
        q=QUANTITY.get(b.kind)
        if q in scales and number(b.value) is not None: b.value=number(b.value)*scales[q]
        if number(b.rate) is not None: b.rate=number(b.rate)*scales['q']
    for s in out.sources:
        q='P' if s.kind=='diss' else 'q'
        if s.kind=='flux':
            if d.network_basis.get('kind')!='area': raise ValueError('network flux requires an area basis')
            factor=unit_scale(d.units.get('q″','W/m²'),'flux')*basis(d)[1]
            s.kind='flow'
        else: factor=scales[q]
        if number(s.value) is not None: s.value=number(s.value)*factor
    out.units.update(R='K/W',q='W',P='W')
    out.network_basis={}
    return out


def convert_basis(d: 'Diagram', target: Dict[str, Any]) -> 'Diagram':
    """Return a value-preserving basis conversion; physical volume budgets are untouched."""
    from .model import QUANTITY
    from .derivations import evaluate
    out,_,errors=evaluate(d)
    if errors: raise ValueError('Resolve invalid derivations before converting network basis')
    out.control_volumes=copy.deepcopy(d.control_volumes)
    if any(b.kind=='stream' for b in d.branches):
        raise ValueError('Normalized stream conversion is unsupported; use a total network')
    out.network_basis=copy.deepcopy(target)
    kind,_=basis(out)
    r,q={'total':('K/W','W'),'area':('K*m²/W','W/m²'),'length':('K*m/W','W/m')}[kind]
    needed={'R','q'} | ({'P'} if any(s.kind=='diss' for s in d.sources) else set())
    old={name:network_scale(d,name) for name in needed}
    out.units.update(R=r,q=q,P=q)
    new={name:network_scale(out,name) for name in ('R','q','P')}
    def converted(value, quantity, field):
        if value is None: return None
        n=number(value)
        if n is None: raise ValueError(f'{field}: symbolic values require an explicit numeric value before basis conversion')
        result=n*old[quantity]/new[quantity]
        if not math.isfinite(result): raise ValueError(f'{field}: conversion exceeds numerical range')
        return result
    for i,b in enumerate(out.branches):
        quantity=QUANTITY.get(b.kind)
        if quantity in old: b.value=converted(b.value,quantity,f'branch {i}.value')
        b.rate=converted(b.rate,'q',f'branch {i}.rate')
    for i,source in enumerate(out.sources):
        if source.kind=='flux': raise ValueError('convert network flux to an explicit flow before changing its basis')
        quantity='P' if source.kind=='diss' else 'q'
        source.value=converted(source.value,quantity,f'source {i}.value')
    return out.validate()
