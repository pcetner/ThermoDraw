"""Scientific unit catalogue and conversion boundaries, independent of models.

Prefix reference: https://www.bipm.org/en/measurement-units/si-prefixes
Temperature reference: NIST Handbook 44, Appendix C.
Compound temperature tokens always mean intervals, never absolute offsets.
"""
import math
import re

PREFIXES = tuple(zip(
    ('q','r','y','z','a','f','p','n','µ','m','c','d','','da','h','k','M','G','T','P','E','Z','Y','R','Q'),
    ('quecto','ronto','yocto','zepto','atto','femto','pico','nano','micro','milli','centi','deci','none','deca','hecto','kilo','mega','giga','tera','peta','exa','zetta','yotta','ronna','quetta'),
    (-30,-27,-24,-21,-18,-15,-12,-9,-6,-3,-2,-1,0,1,2,3,6,9,12,15,18,21,24,27,30)))
# mass, length, time, temperature
BASE = {'kg': (1., (1,0,0,0)), 'g': (.001,(1,0,0,0)),
        'm': (1.,(0,1,0,0)), 's': (1.,(0,0,1,0)),
        'min': (60.,(0,0,1,0)), 'h': (3600.,(0,0,1,0)),
        'K': (1.,(0,0,0,1)), '°C': (1.,(0,0,0,1)),
        '°F': (5/9,(0,0,0,1)), 'W': (1.,(1,2,-3,0)),
        'J': (1.,(1,2,-2,0))}
QUANTITIES = {'T':'K','R':'K/W','C':'J/K','P':'W','q':'W',
              'rate':'W','generation':'W','storage':'W','area':'m²',
              'flux':'W/m²','q″':'W/m²','cp':'J/(kg*K)','mdot':'kg/s'}
PRESETS = {'T':['°C','°F','K'], 'R':['K/W','°F/W','mK/W'],
           'C':['J/K','kJ/K','J/°F'], 'cp':['J/(kg·K)','kJ/(kg·K)','J/(kg·°F)'],
           'mdot':['kg/s','g/s','kg/h'], 'P':['W','kW','mW'],
           'q':['W','kW','mW'], 'q″':['W/m²','W/cm²','kW/m²'],
           'area':['m²','cm²','mm²']}
UNIT_NAMES={'°C':'degrees Celsius','°F':'degrees Fahrenheit','K':'kelvin',
            'K/W':'kelvin per watt','°F/W':'degrees Fahrenheit per watt','mK/W':'millikelvin per watt',
            'J/K':'joules per kelvin','kJ/K':'kilojoules per kelvin','J/°F':'joules per degree Fahrenheit',
            'J/(kg·K)':'joules per kilogram kelvin','kJ/(kg·K)':'kilojoules per kilogram kelvin',
            'J/(kg·°F)':'joules per kilogram degree Fahrenheit',
            'kg/s':'kilograms per second','g/s':'grams per second','kg/h':'kilograms per hour',
            'W':'watts','kW':'kilowatts','mW':'milliwatts',
            'W/m²':'watts per square metre','W/cm²':'watts per square centimetre','kW/m²':'kilowatts per square metre',
            'm²':'square metres','cm²':'square centimetres','mm²':'square millimetres'}

def temperature(value, source, target='K', scale=None):
    """Convert finite temperatures; ``rise`` denotes an interval."""
    aliases={'C':'°C','F':'°F','kelvin':'K','celsius':'°C','fahrenheit':'°F'}
    source,target=aliases.get(source,source),aliases.get(target,target)
    if source not in ('K','°C','°F') or target not in ('K','°C','°F'):
        raise ValueError('Temperature units must be °C, °F, or K')
    n=float(value)
    if not math.isfinite(n): raise ValueError('A finite temperature is required')
    if source==target: return n
    if scale=='rise':
        k=n*(5/9 if source=='°F' else 1)
        result=k*(9/5 if target=='°F' else 1)
    else:
        k=n if source=='K' else n+273.15 if source=='°C' else (n-32)*5/9+273.15
        result=k if target=='K' else k-273.15 if target=='°C' else (k-273.15)*9/5+32
    if not math.isfinite(result): raise ValueError('Temperature conversion exceeded numerical range')
    return result

def normalize_unit(text):
    text=str(text).strip().replace('\\cdot','*').replace('·','*').replace('×','*').replace('μ','µ')
    text=text.replace('²','^2').replace('³','^3').replace('⁻','-')
    text=re.sub(r'\s+','',text)
    # Established heat-capacity spelling uses the whole suffix as denominator.
    if '/' in text and '(' not in text:
        a,b=text.split('/',1);text=a+'/('+b.replace('/','*')+')'
    text=re.sub(r'(kg|g)([K])',r'\1*\2',text)
    return text

def _atom(token):
    if token in BASE: return BASE[token]
    if token in ('C','F'): return BASE['°'+token]
    for symbol,name,power in sorted(PREFIXES,key=lambda p:-max(len(p[0]),len(p[1]))):
        if not symbol: continue
        for prefix in (symbol,name,'u' if symbol=='µ' else symbol):
            if token.startswith(prefix):
                unit=token[len(prefix):]
                if unit in BASE and unit not in ('kg','°C','°F','min','h'):
                    factor,dim=BASE[unit];return factor*10.**power,dim
    raise ValueError('Unsupported unit token: '+token)

def parse_unit(text):
    text=normalize_unit(text)
    tokens=re.findall(r'[A-Za-zµ°]+|\^|[-+]?\d+|[()*/]',text)
    if ''.join(tokens)!=text or not tokens: raise ValueError('Unsupported unit expression: '+text)
    pos=0
    def expression():
        nonlocal pos
        factor=1.;dim=[0,0,0,0];sign=1;expect_atom=True
        while pos<len(tokens) and tokens[pos]!=')':
            token=tokens[pos];pos+=1
            if token in ('*','/'):
                if expect_atom: raise ValueError('A unit is required beside each operator')
                expect_atom=True
                sign=-1 if token=='/' else 1;continue
            if not expect_atom: raise ValueError('Separate unit tokens with multiplication or division')
            if token=='(':
                value,d=expression()
                if pos>=len(tokens) or tokens[pos]!=')': raise ValueError('Unclosed unit parentheses')
                pos+=1
            else: value,d=_atom(token)
            exponent=1
            if pos<len(tokens) and tokens[pos]=='^':
                pos+=1
                if pos>=len(tokens) or not re.fullmatch(r'[-+]?\d+',tokens[pos]): raise ValueError('Unit exponent must be an integer')
                exponent=int(tokens[pos]);pos+=1
                if abs(exponent)>12: raise ValueError('Unit exponent is too large')
            exponent*=sign
            factor*=value**exponent
            dim=[a+b*exponent for a,b in zip(dim,d)]
            sign=1;expect_atom=False
        if expect_atom: raise ValueError('Incomplete unit expression')
        return factor,tuple(dim)
    result=expression()
    if pos!=len(tokens): raise ValueError('Unexpected closing unit parentheses')
    if not math.isfinite(result[0]) or result[0]<=0: raise ValueError('Unit scale is outside numerical range')
    return result

def unit_scale(unit, quantity):
    scale,dim=parse_unit(unit)
    _,expected=parse_unit(QUANTITIES[quantity])
    if dim!=expected: raise ValueError(f'{unit} is not a unit of {quantity}; expected dimensions of {QUANTITIES[quantity]}')
    return scale

class UnitScales(dict):
    """Backward-compatible scale table with dimensionally checked SI prefixes."""
    def __init__(self, quantity, entries):
        super().__init__(entries);self.quantity=quantity
    def __missing__(self, key):
        try: return unit_scale(key,self.quantity)
        except (ValueError,KeyError,OverflowError,ZeroDivisionError): raise KeyError(key) from None
    def get(self,key,default=None):
        try:return self[key]
        except KeyError:return default
    def __contains__(self,key):
        return self.get(key) is not None

def catalogue():
    return {'prefixes':[{'symbol':s,'name':n,'exponent':p,
                         'help':f'{n}: multiply the selected unit by 10^{p}. Undo restores the previous unit.'}
                        for s,n,p in PREFIXES],
            'presets':PRESETS,
            'units':[{'symbol':s,'name':UNIT_NAMES[s],'quantity':q,
                      'help':f'A supported {q} unit. Insert at the caret; a unit change preserves the physical value. Undo restores the previous unit.'}
                     for q,items in PRESETS.items() for s in items],
            'quantities':QUANTITIES,'temperature':['°C','°F','K']}

def format_quantity(value, unit, quantity, mode='automatic', scale=None):
    """Six significant figures from original numeric data, never a saved edit."""
    if value is None: return None
    try: n=float(value)
    except (ValueError,TypeError): return f'{value} {unit}'.strip()
    if not math.isfinite(n): return f'{value} {unit}'.strip()
    original_unit=unit
    if quantity=='T':
        if mode=='scientific': n=temperature(n,unit,'K',scale);unit='K'
    else:
        try:
            n*=unit_scale(unit,quantity)
            unit=QUANTITIES[quantity].replace('*','·')
        except (ValueError,KeyError):return f'{n:.6g} {unit}'.strip()
    if not math.isfinite(n):return f'{value} {original_unit}'.strip()
    if mode=='scientific':
        if n==0:return f'0 {unit}'
        mantissa,exponent_text=f'{n:.5e}'.split('e');exponent=int(exponent_text)
        digits=mantissa.rstrip('0').rstrip('.')
        return f'{digits}{"e"+str(exponent) if exponent else ""} {unit}'
    if quantity!='T' and n:
        mass=unit.startswith('kg');base=n*1000 if mass else n
        exponent=2 if unit.startswith('m²') else 1
        power=3*math.floor(math.log10(abs(base))/(3*exponent))
        prefixes={p:s for s,_,p in PREFIXES if p%3==0}
        if power in prefixes:
            n=base/10.**(power*exponent)
            # Rounding at a prefix boundary must not print 1000 of the
            # smaller unit when the next engineering prefix is available.
            if abs(float(f'{n:.6g}'))>=10.**(3*exponent) and power+3 in prefixes:
                power+=3;n=base/10.**(power*exponent)
            unit=prefixes[power]+(unit[1:] if mass else unit)
    return f'{n:.6g} {unit}'.strip()
