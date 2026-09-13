"""Visible editing controls, permanent Solve tab, and real library scrolling."""
from pathlib import Path

import pytest

from test_editor_interactions import page, load
from test_editor_ui import served, settled, stored
from test_editor_resolution import resistance
from editor_actions import action, menu


def test_visible_edit_icons_and_no_history_focus_border(page):
    load(page,resistance());before=stored(page)
    nav=page.get_by_role('navigation',name='Editor menus')
    assert nav.get_by_role('button').all_text_contents()==['File','View','Help']
    for label in ['Copy','Paste','Delete selection','Merge selected nodes']:
        button=page.get_by_role('group',name='Editing actions').get_by_role('button',name=label,exact=True)
        assert button.is_visible() and button.locator('svg').count()==1
        assert button.get_attribute('title')
    assert page.locator('#ed-copy').is_disabled() and page.locator('#ed-merge').is_disabled()
    page.evaluate("select({role:'branch',index:0})")
    page.locator('#ed-delete').click();settled(page)
    assert not stored(page)['branches']
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before
    assert page.locator('#ed-canvas').evaluate("e=>getComputedStyle(e).outlineStyle==='none'")
    page.locator('#ed-redo').click();settled(page);assert not stored(page)['branches']
    assert page.locator('#ed-canvas').evaluate("e=>getComputedStyle(e).outlineStyle==='none'")


def test_solve_is_always_third_and_preserves_selection(page):
    load(page,resistance());page.evaluate("select({role:'branch',index:0})")
    nav=page.get_by_role('navigation',name='Panel views')
    assert nav.get_by_role('button').all_text_contents()==['Components','Properties','Solve']
    before=stored(page)
    nav.get_by_role('button',name='Solve',exact=True).click()
    assert page.locator('#ed-solve-panel').is_visible()
    nav.get_by_role('button',name='Properties',exact=True).click()
    assert page.locator('#ed-popover [data-field=value]').input_value()=='10'
    nav.get_by_role('button',name='Solve',exact=True).click()
    page.locator('[data-physics-close]').click()
    assert nav.get_by_role('button').all_text_contents()==['Components','Properties','Solve']
    assert stored(page)==before


def test_examples_are_in_files_and_open_as_copies(page):
    load(page,resistance());before=stored(page)
    action(page,'ed-open-example')
    page.locator('#ed-examples li').first.wait_for(state='visible')
    assert page.locator('#ed-examples').evaluate("e=>e.closest('#ed-files-panel')!==null")
    assert page.locator('#ed-example-section').evaluate("e=>!!(document.getElementById('ed-files').compareDocumentPosition(e)&Node.DOCUMENT_POSITION_FOLLOWING)")
    menu(page,'File');assert page.get_by_label('File menu',exact=True).locator('#ed-open-example').count()==0
    page.keyboard.press('Escape')
    original_id=page.evaluate('S.file.id')
    page.locator('#ed-examples li button').first.click()
    page.wait_for_function('S.file.id!=="'+original_id+'"');settled(page)
    assert page.evaluate("id=>JSON.parse(localStorage.getItem('thermodraw:file:'+id))",original_id)==before


@pytest.mark.parametrize('width',[1280,640,390])
def test_library_scroll_reaches_last_component(page,width):
    page.set_viewport_size({'width':width,'height':800})
    try:
        load(page,resistance())
        if not page.get_by_role('navigation',name='Panel views').is_visible():page.locator('#ed-components-reopen').click()
        page.get_by_role('navigation',name='Panel views').get_by_role('button',name='Components',exact=True).click()
        page.locator('[data-category-tab="Network"]').click()
        library=page.locator('#ed-component-tools')
        assert library.evaluate('e=>e.scrollHeight>e.clientHeight && getComputedStyle(e).display!=="contents"')
        assert page.locator('.ed-card[data-key="cond"] svg').evaluate('e=>e.getBoundingClientRect().width>=100')
        box=library.bounding_box();page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2)
        page.mouse.wheel(0,4000)
        page.wait_for_function("(()=>{const e=document.getElementById('ed-component-tools');return e.scrollTop+e.clientHeight>=e.scrollHeight-2})()")
        last=page.locator('.ed-card[data-key="flux"]').bounding_box()
        assert last['y']>=box['y'] and last['y']+last['height']<=box['y']+box['height']+1
        assert page.locator('#ed-settings').evaluate('e=>e.getBoundingClientRect().right<=innerWidth')
        assert page.locator('#ed-top').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
        output=Path(__file__).parents[1]/'out'/'ui-review';output.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(output/f'component-scroll-{width}.png'))
    finally:page.set_viewport_size({'width':1280,'height':800})
