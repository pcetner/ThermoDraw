"""Assignment options through real editor controls and the Python worker."""
import copy
import pytest
from test_editor_interactions import page, load, pick_value
from test_editor_ui import served, settled, stored

def wall():
    return {'units':{'T':'°C','R':'K/W','q':'W'},
            'nodes':[{'id':'a','kind':'fixed','value':70,'at':[250,250]},
                     {'id':'b','value':126,'at':[600,250]}],
            'branches':[{'id':'wall','from':'a','to':'b','value':.007}],
            'sources':[{'kind':'flow','to':'b','value':8000}],
            'analysis':{'network':{'steady':True,'unknowns':['b']}}}

def options(page,role='branch',index=0):
    page.evaluate('(s)=>select(s)',{'role':role,'index':index})
    page.locator('[data-assignment-open]').click()
    dialog=page.locator('.ed-assignment-dialog')
    dialog.wait_for(state='visible')
    return dialog

def apply(page,dialog,name):
    dialog.get_by_role('button',name=name,exact=True).click()
    dialog.wait_for(state='detached')
    settled(page)

def test_basis_conversion_review_undo_and_legacy_defaults(page):
    load(page,wall());before=stored(page)
    assert 'check_policy' not in before['analysis']
    d=options(page)
    d.get_by_text('Network basis and checking',exact=True).click()
    d.get_by_label('Network basis',exact=True).select_option('area')
    d.get_by_label('Reference size',exact=True).fill('2')
    apply(page,d,'Convert basis, preserving total heat rates')
    changed=stored(page)
    assert changed['network_basis']=={'kind':'area','value':2,'unit':'m²'}
    assert changed['branches'][0]['value']==pytest.approx(.014)
    assert changed['sources'][0]['value']==4000
    page.locator('#ed-undo').click();settled(page)
    assert stored(page)==before

def test_source_correction_is_one_undo_step(page):
    data=wall();data['sources']=[{'kind':'flow','from':'b','value':-8000}]
    load(page,data);before=stored(page)
    d=options(page,'source')
    apply(page,d,'Correct direction explicitly')
    source=stored(page)['sources'][0]
    assert source['value']==8000 and source['to']=='b' and 'from' not in source
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before

def fill_plane(d,length='.35'):
    d.get_by_label('Relation',exact=True).select_option('plane')
    d.get_by_label('Length / thickness',exact=True).fill(length)
    d.get_by_label('Thermal conductivity',exact=True).fill('50')
    d.get_by_label('Physical area',exact=True).fill('1')

def test_derivation_save_reopen_scenario_and_stale_guard(page):
    load(page,wall());d=options(page);fill_plane(d)
    apply(page,d,'Switch to selected relation')
    saved=stored(page)
    assert saved['branches'][0]['value']==pytest.approx(.007)
    assert saved['branches'][0]['derivation']['inputs']['L']['value']==.35
    load(page,saved);saved=stored(page)
    page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Solve',exact=True).click()
    pick_value(page,'branch:0:value')
    page.get_by_role('button',name='Edit derivation inputs',exact=True).click()
    d=page.locator('.ed-assignment-dialog');d.wait_for(state='visible')
    d.get_by_label('Length / thickness',exact=True).fill('.7')
    apply(page,d,'Switch to selected relation')
    assert stored(page)==saved
    assert float(page.locator('[data-physics-number]').input_value())==pytest.approx(.014)
    # Close the session without applying the scenario.
    page.locator('[data-physics-close]').click()
    page.locator('[data-session-discard]').click()
    d=options(page)
    page.evaluate("edit(d=>d.title='Newer document revision')")
    d.get_by_role('button',name='Switch to selected relation',exact=True).click()
    assert 'changed' in d.locator('[role=alert]').text_content()
    assert stored(page)['title']=='Newer document revision'
    d.get_by_role('button',name='Close',exact=True).click()

def test_formatted_labels_and_mobile_dialog_contrast(page):
    load(page,wall());page.set_viewport_size({'width':390,'height':844})
    try:
        d=options(page)
        d.get_by_text('Label formatting',exact=True).click()
        d.get_by_label('Text segment',exact=True).fill('R')
        d.get_by_role('button',name='Add text segment',exact=True).click()
        d.get_by_label('Text segment',exact=True).nth(1).fill('wall')
        d.get_by_label('Text position',exact=True).nth(1).select_option('subscript')
        bounds=d.bounding_box()
        assert bounds['x']>=0 and bounds['x']+bounds['width']<=390
        assert d.evaluate('e=>getComputedStyle(e).backgroundColor')!=d.evaluate('e=>getComputedStyle(e).color')
        assert d.evaluate('e=>e.scrollWidth<=e.clientWidth')
        apply(page,d,'Apply formatted label')
        assert stored(page)['branches'][0]['label_runs'][1]=={'text':'wall','position':'subscript'}
        assert stored(page)['branches'][0]['label']=='Rwall'
    finally:
        page.set_viewport_size({'width':1280,'height':800})


def test_formatted_normalized_diagram_exports_png(page,tmp_path):
    from pathlib import Path
    from editor_actions import action
    from thermodraw import Diagram,convert_basis
    data=convert_basis(Diagram.from_dict(wall()),{'kind':'area','value':2,'unit':'m²'}).to_dict()
    data['branches'][0]['label_runs']=[{'text':'R'},{'text':'wall','position':'subscript'},{'text':'″'}]
    load(page,data)
    action(page,'ed-export')
    try:
        page.locator('[data-export-format]').select_option('PNG')
        with page.expect_download() as download:
            page.locator('[data-export-save]').click()
        target=tmp_path/'assignment.png'
        download.value.save_as(target)
        assert target.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        assert target.stat().st_size>10000
        review=Path(__file__).resolve().parents[1]/'out/assignment-review'
        review.mkdir(parents=True,exist_ok=True)
        (review/'formatted-normalized.png').write_bytes(target.read_bytes())
    finally:
        page.locator('[data-export-close]').click()
