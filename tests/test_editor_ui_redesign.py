"""Behavior and layout contracts for the docked editor UI."""
import pytest
from pathlib import Path
from test_editor_interactions import page, load
from test_editor_ui import served, settled, stored
from test_editor_resolution import resistance
from editor_actions import action, menu


def section(page,name):
    page.get_by_role('navigation',name='Property sections').get_by_role('button',name=name,exact=True).click()

@pytest.mark.parametrize('width',[1280,640,390])
def test_inspector_has_no_horizontal_overflow(page,width):
    page.set_viewport_size({'width':width,'height':800})
    try:
        data=resistance();data['nodes'][1].update(kind='fixed',label='A long descriptive temperature boundary name')
        data['branches'][0].update(kind='conv',via=[[300,100],[600,100]])
        load(page,data);page.evaluate("select({role:'branch',index:0})")
        assert page.locator('#ed-popover').evaluate("e=>e.parentElement.id")=='ed-palette'
        for name in ['Properties','Connections','Appearance']:
            section(page,name)
            assert page.locator('#ed-popover').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
            assert page.locator('[data-inspector-section="'+name+'"]').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        assert page.locator('.ed-control-help').count()==0
        assert page.locator('[data-field=angle]').locator('..').locator('.ed-picker-button').count()==0
        page.get_by_role('button',name='Close properties',exact=True).click()
        assert page.locator('#ed-component-tools').is_visible()
    finally:page.set_viewport_size({'width':1280,'height':800})


def test_count_draft_survives_tabs_and_gates_panel_switch(page):
    load(page,resistance());before=stored(page);page.evaluate("select({role:'branch',index:0})")
    page.locator('[data-field=count]').fill('3');page.locator('[data-field=arrangement]').select_option('series')
    page.wait_for_function("!document.querySelector('[data-group-apply]').disabled")
    section(page,'Appearance');assert page.locator('[data-group-apply]').is_visible()
    page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Components',exact=True).click()
    assert page.get_by_role('button',name='Keep editing',exact=True).is_visible()
    page.get_by_role('button',name='Keep editing',exact=True).click()
    page.locator('[data-group-cancel]').click();assert stored(page)==before


def test_settings_menu_stays_open_and_help_is_separate(page):
    load(page,resistance());menu(page,'View');page.locator('#ed-theme').click()
    assert page.get_by_label('View menu',exact=True).is_visible()
    page.locator('#ed-theme').press('Escape')
    menu(page,'Help');assert page.get_by_role('menuitem',name='Interaction legend',exact=True).count()==0
    page.get_by_role('menuitem',name='Keyboard shortcuts',exact=True).click()
    dialog=page.get_by_role('dialog',name='Keyboard shortcuts');assert dialog.is_visible()
    assert dialog.locator('kbd').count()>=9
    dialog.get_by_role('button',name='Close keyboard shortcuts',exact=True).click()
    menu(page,'Help');page.get_by_role('menuitem',name='Editor guide',exact=True).click()
    guide=page.get_by_role('dialog',name='Quick start');assert guide.is_visible()
    assert guide.locator('h3').count()==5
    guide.get_by_role('button',name='Close',exact=True).click()


def test_solve_panel_switch_preserves_session(page):
    load(page,resistance());action(page,'ed-analysis')
    page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Components',exact=True).click()
    assert page.locator('#ed-component-tools').is_visible()
    page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Solve',exact=True).click()
    assert page.locator('#ed-solve-panel').is_visible()
    action(page,'ed-analysis')


def test_clean_parallel_labels_do_not_create_editor_suggestions(page):
    data=resistance();data['branches'].append({'from':'a','to':'b','kind':'conv','via':[[300,100],[600,100]]})
    load(page,data)
    assert 'parallel-pair-same-side' not in page.locator('#ed-findings').inner_text()
    assert page.locator('#ed-undo').get_attribute('aria-label')=='Undo'
    assert page.locator('#ed-undo svg').count()==1

def test_issue_click_reveals_all_targets_without_resizing_canvas(page):
    data=resistance()
    data['nodes'][0].update(label='Boundary A',label_offset=[0,-80])
    data['nodes'][1].update(label='Boundary B',label_offset=[-300,-80])
    load(page,data)
    issues=page.evaluate("S.scene.findings.filter(f=>f.code==='label-collision')")
    assert issues and len(issues[0]['targets'])>=2
    dimensions=page.locator('#ed-canvas').bounding_box()
    page.locator('#ed-findings-toggle').click()
    assert page.locator('.ed-issue-detail').is_visible()
    assert len(page.evaluate('S.selection'))>=2
    assert page.locator('#ed-canvas').bounding_box()==dimensions
    assert page.locator('.ed-issue-detail details').get_attribute('open') is None
    focused=page.evaluate('document.activeElement.dataset.issueKey||null')
    page.evaluate('edit(d=>{d.nodes[0].value=100})');settled(page)
    assert page.locator('.ed-issue-detail').is_visible()
    assert page.evaluate('document.activeElement.dataset.issueKey||null')==focused


def test_menu_keyboard_navigation_and_notation_checkmark(page):
    load(page,resistance());menu(page,'View')
    page.locator('#ed-notation').click();settled(page)
    assert page.locator('#ed-notation').get_attribute('aria-checked')==str(page.evaluate("S.notation==='zigzags'")).lower()
    page.locator('#ed-notation').press('ArrowRight')
    assert page.get_by_label('Help menu',exact=True).is_visible()
    page.keyboard.press('Escape')
    assert page.get_by_label('Help menu',exact=True).is_hidden()
    assert page.get_by_role('navigation',name='Editor menus').get_by_role('button',name='Help',exact=True).evaluate('e=>e===document.activeElement')


def test_multiple_selection_delete_names_its_scope(page):
    load(page,resistance());before=stored(page)
    page.evaluate("S.selection=[{role:'node',index:0},{role:'node',index:1}];select({role:'node',index:1},false)")
    page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Properties',exact=True).click()
    page.get_by_role('button',name='Delete 2 selected objects',exact=True).click();settled(page)
    assert len(stored(page)['branches'])==1
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


def test_legacy_waypoint_edit_is_undoable(page):
    data=resistance();data['branches'][0]['via']=[[300,100],[600,100]]
    load(page,data);before=stored(page);page.evaluate("select({role:'branch',index:0})")
    section(page,'Appearance')
    page.locator('[data-inspector-section="Appearance"] details summary').click()
    coordinate=page.get_by_role('spinbutton',name='Waypoint 1 x',exact=True)
    coordinate.fill('320');coordinate.press('Tab')
    page.wait_for_function('S.data.branches[0].via[0][0]===320');settled(page)
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


@pytest.mark.parametrize('width,theme',[(1280,'light'),(1280,'dark'),(390,'light'),(640,'dark')])
def test_visual_review_scenarios(page,width,theme):
    page.set_viewport_size({'width':width,'height':800})
    try:
        data=resistance()
        data['nodes'][0].update(label='Outer surface of the insulating container',label_offset=[0,-80])
        data['nodes'][1].update(kind='fixed',label='Fixed reference boundary with a long descriptive name',label_offset=[-300,-80])
        data['branches'][0].update(kind='conv',via=[[320,250],[320,100],[580,100],[580,250]])
        load(page,data)
        if page.locator('html').get_attribute('data-theme')!=theme:
            action(page,'ed-theme');page.keyboard.press('Escape')
        page.evaluate("select({role:'branch',index:0})")
        section(page,'Appearance')
        page.locator('[data-inspector-section="Appearance"] details summary').click()
        page.locator('#ed-findings-toggle').click()
        assert page.locator('#ed-popover').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        assert page.locator('#ed-physics-said').is_visible()
        assert page.locator('#ed-canvas-header').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        assert page.locator('#ed-top').evaluate('e=>e.getBoundingClientRect().top>=0')
        assert page.locator('#ed-findings').evaluate('e=>e.getBoundingClientRect().bottom<=innerHeight')
        output=Path(__file__).parents[1]/'out'/'ui-review';output.mkdir(parents=True,exist_ok=True)
        (output/f'{theme}-{width}.json').write_text(__import__('json').dumps(page.evaluate("({y:scrollY,h:innerHeight,body:document.body.scrollHeight,rows:getComputedStyle(document.body).gridTemplateRows,boxes:['ed-top','ed-canvas','ed-findings','ed-palette'].map(id=>({id,box:document.getElementById(id).getBoundingClientRect().toJSON()}))})")),encoding='utf-8')
        page.screenshot(path=str(output/f'{theme}-{width}.png'))
    finally:
        page.set_viewport_size({'width':1280,'height':800})
