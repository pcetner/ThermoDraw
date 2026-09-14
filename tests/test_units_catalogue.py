"""Independent decimal references for temperature boundaries and SI parsing."""
from decimal import Decimal, localcontext
import math
import pytest
from thermodraw._units import PREFIXES, temperature, unit_scale, parse_unit
from thermodraw._session import convert_value

@pytest.mark.parametrize('fahrenheit',[-459.67,-40,32,212,123.456789,1e10,-1e10])
def test_fahrenheit_decimal_reference(fahrenheit):
    with localcontext() as context:
        context.prec=60
        expected=float((Decimal(str(fahrenheit))-32)*5/9+Decimal('273.15'))
    kelvin=temperature(fahrenheit,'°F')
    assert abs(kelvin-expected)<=max(1e-10,8*math.ulp(expected))
    recovered=temperature(temperature(kelvin,'K','°F'),'°F','K')
    assert abs(recovered-kelvin)<=max(1e-10,8*math.ulp(kelvin))

def test_temperature_intervals_and_compound_units():
    assert temperature(18,'°F','K','rise')==10
    assert convert_value(18,'°F/W','K/W','R')==10
    assert convert_value(1,'J/(kg*°F)','J/(kg*K)','cp')==pytest.approx(1.8)
    assert temperature(-40,'°F','°C')==pytest.approx(-40)

@pytest.mark.parametrize('unit',['kJ/(kg*K)','kJ/kg/K','kJ/kg·K',r'kJ/kg\cdot K'])
def test_heat_capacity_aliases(unit):
    assert unit_scale(unit,'cp')==1000

def test_all_prefixes_and_dimensions():
    assert len(PREFIXES)==25
    for symbol,name,power in PREFIXES:
        assert unit_scale(symbol+'W','P')==pytest.approx(10.**power)
        if symbol: assert unit_scale(name+'W','P')==pytest.approx(10.**power)
    assert unit_scale('µW','P')==unit_scale('uW','P')==unit_scale('μW','P')
    assert unit_scale('cm²','area')==.0001
    assert unit_scale('mg/s','mdot')==1e-6
    with pytest.raises(ValueError):unit_scale('kg','R')
    with pytest.raises(ValueError):parse_unit('kkg')

def test_display_conversion_does_not_modify_canonical_value():
    canonical=temperature(123.456789,'°F')
    original=canonical.hex()
    for i in range(4000):
        temperature(canonical,'K',('°C','°F','K')[i%3])
    assert canonical.hex()==original


@pytest.mark.parametrize('quantity,unit,values',[
    ('area','m²',[1e-12,1e-6,.0001,1,1e6]),
    ('mdot','kg/s',[0,-1e-9,.001,1000]),
    ('cp','J/(kg*K)',[1e-9,1000,-2e6]),
    ('R','K/W',[1e-12,.01,1000,1e33]),
])
def test_formatted_prefixes_retain_physical_value(quantity,unit,values):
    from thermodraw._units import format_quantity
    for value in values:
        for mode in ('automatic','scientific'):
            displayed,shown_unit=format_quantity(value,unit,quantity,mode).split(' ',1)
            actual=float(displayed)*unit_scale(shown_unit,quantity)
            assert actual==pytest.approx(value*unit_scale(unit,quantity),rel=5e-6,abs=1e-40)


@pytest.mark.parametrize('unit', ['K','°C','°F'])
def test_solver_uses_the_same_kelvin_physics_for_all_temperature_displays(unit):
    from thermodraw import Diagram,solve_physics
    data={'units':{'T':{'unit':unit,'scale':'absolute'},'R':'K/W'},
          'nodes':[{'id':'hot','kind':'fixed','value':temperature(400,'K',unit)},
                   {'id':'mid'}, {'id':'cold','kind':'fixed','value':temperature(300,'K',unit)}],
          'branches':[{'from':'hot','to':'mid','value':2},{'from':'mid','to':'cold','value':3}],
          'analysis':{'network':{'steady':True,'unknowns':['mid']}}}
    result=solve_physics(Diagram.from_dict(data))
    assert result.status=='solved'
    component=result.components[0]
    assert temperature(component['temperatures']['mid'],unit)==pytest.approx(360,abs=1e-10)
    assert [b['watts'] for b in component['branch_rates']]==pytest.approx([20,20])


def test_picker_catalogue_is_documented_and_dimensionally_valid():
    from thermodraw._catalogue import catalogue
    c=catalogue()
    assert len(c['prefixes'])==25
    for entry in c['units']:
        assert entry['name'] and entry['help']
        assert unit_scale(entry['symbol'],entry['quantity'])>0
    for entry in c['symbols']:
        assert entry['name'] and entry['contexts'] and entry['help']
    for entry in c['interactions']:
        assert all(entry[k] for k in ('id','name','when','action','changes','cancel'))
