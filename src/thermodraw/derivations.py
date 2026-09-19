"""Fixed-coefficient thermal relations. Inputs use {value, unit} quantities.

All resistance helpers return total K/W, capacity returns J/K, and storage
returns joules and watts. Geometry is physical data, never drawing geometry.
"""
import copy
import math
from typing import Any, Dict, Optional
from ._units import parse_unit
from ._physical import number

FORMULAS = {
    'plane': 'L/(k*A)', 'cylinder': 'ln(r2/r1)/(2*pi*k*L)',
    'sphere': '(1/r1-1/r2)/(4*pi*k)', 'convection': '1/(h*A)',
    'contact': 'contact_resistivity/A', 'capacity': 'rho*cp*V',
}
INPUTS = {'plane': {'L':'m','k':'W/(m*K)','A':'m²'},
          'cylinder': {'r1':'m','r2':'m','k':'W/(m*K)','L':'m'},
          'sphere': {'r1':'m','r2':'m','k':'W/(m*K)'},
          'convection': {'h':'W/(m²*K)','A':'m²'},
          'contact': {'contact_resistivity':'K*m²/W','A':'m²'},
          'capacity': {'rho':'kg/m³','cp':'J/(kg*K)','V':'m³'}}


def quantity(record: Any, expected: str, field: str, *, positive: bool = True) -> float:
    if not isinstance(record,dict) or set(record)!={'value','unit'}:
        raise ValueError(f'{field}: supply value and unit')
    n=number(record['value'])
    if n is None: raise ValueError(f'{field}: a finite numeric value is required')
    factor,dim=parse_unit(record['unit'])
    if dim!=parse_unit(expected)[1]: raise ValueError(f'{field}: expected dimensions {expected}, got {record["unit"]!r}')
    result=n*factor
    if not math.isfinite(result) or (positive and result<=0):
        raise ValueError(f'{field}: a positive finite quantity is required')
    return result


def _inputs(spec: Dict[str, Any], allowed) -> Dict[str,float]:
    if not isinstance(spec,dict) or set(spec)-{'kind','inputs','source'} or spec.get('kind') not in allowed:
        raise ValueError('derivation: choose a supported kind and supply inputs and optional source')
    kind=spec['kind']; inputs=spec.get('inputs')
    if not isinstance(inputs,dict) or set(inputs)!=set(INPUTS[kind]):
        raise ValueError(f'{kind}.inputs requires exactly {", ".join(INPUTS[kind])}')
    return {name:quantity(inputs[name],unit,f'{kind}.{name}') for name,unit in INPUTS[kind].items()}


def derive_resistance(spec: Dict[str, Any]) -> float:
    """Evaluate one physical resistance in K/W, before repetition folding."""
    x=_inputs(spec, set(INPUTS)-{'capacity'}); kind=spec['kind']
    if kind in ('cylinder','sphere') and x['r2']<=x['r1']:
        raise ValueError(f'{kind}.r2 must exceed r1')
    if kind=='plane': result=x['L']/(x['k']*x['A'])
    elif kind=='cylinder': result=math.log(x['r2']/x['r1'])/(2*math.pi*x['k']*x['L'])
    elif kind=='sphere': result=(1/x['r1']-1/x['r2'])/(4*math.pi*x['k'])
    elif kind=='convection': result=1/(x['h']*x['A'])
    else: result=x['contact_resistivity']/x['A']
    if not math.isfinite(result) or result<=0: raise ValueError('resistance exceeds numerical range')
    return result


def derive_capacity(spec: Dict[str, Any]) -> float:
    """Evaluate rho*cp*V in J/K."""
    x=_inputs(spec, {'capacity'}); result=x['rho']*x['cp']*x['V']
    if not math.isfinite(result) or result<=0: raise ValueError('capacity exceeds numerical range')
    return result


def derive_storage(spec: Dict[str, Any], capacitance: Optional[float] = None) -> Dict[str,float]:
    """Finite-interval energy change and average power, not transient integration."""
    if not isinstance(spec,dict) or set(spec)-{'capacity','capacity_derivation','branch','delta_t','duration','source'}:
        raise ValueError('storage_relation: expected capacity, capacity_derivation or branch; delta_t and duration')
    if sum(key in spec for key in ('capacity','capacity_derivation','branch'))!=1:
        raise ValueError('storage_relation: choose exactly one capacity source')
    if 'capacity' in spec: c=quantity(spec['capacity'],'J/K','capacity')
    elif 'capacity_derivation' in spec: c=derive_capacity(spec['capacity_derivation'])
    elif capacitance is None: raise ValueError('storage_relation.branch: unresolved capacitance branch')
    else:
        if number(capacitance) is None: raise ValueError("storage_relation.branch: a finite capacitance is required")
        c=capacitance
    dt=quantity(spec.get('delta_t'),'K','delta_t',positive=False)
    duration=quantity(spec.get('duration'),'s','duration')
    energy=c*dt; power=energy/duration
    if c<=0 or not all(math.isfinite(v) for v in (c,energy,power)): raise ValueError('storage exceeds numerical range')
    return {'capacity_j_per_k':c,'energy_j':energy,'watts':power}


def evaluate(diagram):
    """Materialize owned values on a copy; invalid relations never use cached values."""
    from .model import QUANTITY
    from ._extensions import network_scale
    from ._units import unit_scale
    out=copy.deepcopy(diagram); reports=[]; errors=[]
    for i,b in enumerate(out.branches):
        if b.derivation is None: continue
        b.value=None
        try:
            if b.kind=='cap': value=derive_capacity(b.derivation)/unit_scale(out.units.get('C','J/K'),'C')
            elif QUANTITY.get(b.kind)=='R': value=derive_resistance(b.derivation)/network_scale(out,'R')
            else: raise ValueError('derivation requires a resistance or capacitance branch')
            b.value=value
            reports.append({'entity':'branch','index':i,'id':b.id,'formula':FORMULAS[b.derivation['kind']],
                            'inputs':copy.deepcopy(b.derivation['inputs']),'value':value,'unit':out.units.get(QUANTITY[b.kind],''),'source':b.derivation.get('source')})
        except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as exc:
            errors.append({'where':f'branch {i}', 'message':str(exc)})
    for volume in out.control_volumes:
        spec=volume.storage_relation
        if spec is None: continue
        volume.storage=None
        try:
            if volume.steady: raise ValueError('storage_relation requires finite-interval mode; remove steady state')
            c=None
            if 'branch' in spec:
                found=[b for b in out.branches if b.id==spec['branch'] and b.kind=='cap']
                if len(found)!=1 or number(found[0].value) is None: raise ValueError('storage_relation.branch must reference one resolved capacitance branch ID')
                c=number(found[0].value)*unit_scale(out.units.get('C','J/K'),'C')
                factor=out.fold('cap',1,found[0].count,found[0].arrangement)
                c*=1 if factor is None else factor
            result=derive_storage(spec,c)
            volume.storage=result['watts']/unit_scale(volume.unit,'P')
            reports.append({'entity':'volume','id':volume.id,'formula':'C*delta_t/duration',
                            'inputs':copy.deepcopy(spec),**result,'value':volume.storage,'unit':volume.unit})
        except (ValueError,KeyError,TypeError,OverflowError,ZeroDivisionError) as exc:
            errors.append({'where':f'volume {volume.id}', 'message':str(exc)})
    return out,reports,errors
