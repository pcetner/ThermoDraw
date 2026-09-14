"""Regression acceptance for the revised editor interactions."""
import json
from pathlib import Path
import pytest
from test_editor_interactions import page, load
from test_editor_ui import served, stored, settled, canvas_point, drop_card
from editor_actions import action

def resistance():
    return {'units':{'R':'K/W','T':'K'},'nodes':[{'id':'a','at':[300,250]},{'id':'b','at':[600,250]}],
            'branches':[{'id':'r','from':'a','to':'b','value':10}],'sources':[]}


@pytest.mark.parametrize('vertical,left',[(False,False),(False,True),(True,False)])
def test_drop_series_on_shared_parallel_terminal(page,vertical,left):
    def point(x,y):return [y,x] if vertical else [x,y]
    data={'units':{'R':'K/W','T':'K'},'nodes':[{'id':'a','at':point(100,300)},
          {'id':'b','at':point(700,300),'kind':'fixed','label':'Boundary','value':20}],
          'branches':[{'id':'main','from':'a','to':'b','value':10,'at':point(400,300)}]}
    for i,y in enumerate([0,100,200,400,500]):
        data['branches'].append({'id':f'p{i}','kind':'conv','from':'a','to':'b','value':20+i,
            'at':point(400,y),'via':[point(180,300),point(180,y),point(620,y),point(620,300)]})
    load(page,data);before=stored(page)
    drop_card(page,'cond',*canvas_point(page,*point(140 if left else 660,300)))
    page.wait_for_function('S.data.branches.length===7')
    settled(page)
    assert page.get_by_role('dialog',name='Choose connection').count()==0
    after=stored(page);assert len(after['branches'])==7 and len(after['nodes'])==3
    inserted=after['branches'][-1];junction=next(n['id'] for n in after['nodes'] if n['id'] not in ['a','b'])
    assert set([inserted['from'],inserted['to']])=={junction,'a' if left else 'b'}
    assert 'value' not in inserted
    for old,new in zip(before['branches'],after['branches']):
        assert old['value']==new['value'] and old['id']==new['id']
        assert new['from']==(junction if left else 'a')
        assert new['to']==('b' if left else junction)
        nodes={n['id']:n['at'] for n in after['nodes']}
        route=[nodes[new['from']],*new.get('via',[]),nodes[new['to']]]
        assert all(a[0]==b[0] or a[1]==b[1] for a,b in zip(route,route[1:]))
    assert next(n for n in after['nodes'] if n['id']=='b')['value']==20
    output=Path(__file__).parents[1]/'out'/'ui-review';output.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(output/f'shared-lead-{vertical}-{left}.png'))
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before
    page.locator('#ed-redo').click();settled(page);assert stored(page)==after


@pytest.mark.parametrize('vertical',[False,True])
def test_dragged_parallel_lane_retains_right_angle_risers(page,vertical):
    def point(x,y):return [y,x] if vertical else [x,y]
    data={'units':{'R':'K/W'},'nodes':[{'id':'a','at':point(100,300)}, {'id':'b','at':point(700,300),'kind':'fixed','label':'Boundary'}],
          'branches':[{'id':'main','from':'a','to':'b','value':10},
                      {'id':'parallel','from':'a','to':'b','kind':'conv','value':20,
                       'at':point(400,100),'via':[point(180,300),point(180,100),point(620,100),point(620,300)]}]}
    load(page,data);before=stored(page)
    start=canvas_point(page,*point(400,100));end=canvas_point(page,*point(400,500))
    page.mouse.move(*start);page.mouse.down();page.mouse.move(*end,steps=12)
    page.wait_for_function('S.preview !== null && previewFrame === null')
    preview=page.evaluate('S.preview');assert preview
    route=[preview['nodes'][0]['at'],*preview['branches'][1]['via'],preview['nodes'][1]['at']]
    assert all(a[0]==b[0] or a[1]==b[1] for a,b in zip(route,route[1:]))
    page.mouse.up();settled(page)
    after=stored(page)
    assert after['nodes']==before['nodes'] and after['branches'][0]==before['branches'][0]
    assert after['branches'][1]['via']==[point(180,300),point(180,500),point(620,500),point(620,300)]
    assert after['branches'][1]['value']==20
    assert page.locator('#ed-ui .ed-hover-ink').count()==0
    output=Path(__file__).parents[1]/'out'/'ui-review';output.mkdir(parents=True,exist_ok=True)
    page.screenshot(path=str(output/f'parallel-drag-{vertical}.png'))
    # A second move uses the committed lane, without accumulating brackets.
    page.mouse.move(*end);page.mouse.down();page.mouse.move(*canvas_point(page,*point(400,120)),steps=12);page.mouse.up();settled(page)
    assert stored(page)['branches'][1]['via']==[point(180,300),point(180,120),point(620,120),point(620,300)]
    page.locator('#ed-undo').click();settled(page);assert stored(page)==after
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before

def test_supplied_import_is_one_undoable_normalization(page):
    data=json.loads((Path(__file__).parent/'fixtures/editor/Insulation.json').read_text(encoding='utf-8'))
    load(page,data)
    assert len(stored(page)['nodes'])==6
    assert len(stored(page)['branches'])==7
    page.locator('#ed-undo').click();settled(page)
    assert len(stored(page)['nodes'])==9
    page.locator('#ed-redo').click();settled(page)
    assert len(stored(page)['nodes'])==6

def test_delete_isolated_resistance_cleans_only_its_endpoints(page):
    data=resistance();data['nodes'].append({'id':'other','at':[800,400]})
    load(page,data);page.evaluate("select({role:'branch',index:0})")
    page.locator('[data-act=delete]').click();settled(page)
    assert [n['id'] for n in stored(page)['nodes']]==['other']
    assert not stored(page)['branches']
    page.locator('#ed-undo').click();settled(page)
    assert len(stored(page)['branches'])==1

def test_count_is_a_draft_and_apply_is_one_transaction(page):
    load(page,resistance());before=stored(page)
    page.evaluate("select({role:'branch',index:0})")
    page.locator('[data-field=count]').fill('2')
    assert stored(page)==before
    assert page.locator('[data-group-apply]').is_disabled()
    page.locator('[data-field=arrangement]').select_option('series')
    page.wait_for_function("!document.querySelector('[data-group-apply]').disabled")
    assert 'Combined value: 20' in page.locator('[data-group-preview]').inner_text()
    page.locator('[data-group-apply]').click();settled(page)
    after=stored(page);assert after['branches'][0].get('count')==2, page.evaluate("({data:S.data,draft:groupDraft,revision:S.revision,toast:document.querySelector('#ed-toast')?.textContent})")
    assert after['branches'][0]['value']==10
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before
    page.locator('#ed-redo').click();settled(page);assert stored(page)==after

def test_count_cancel_and_invalid_enter_leave_document_unchanged(page):
    load(page,resistance());before=stored(page);page.evaluate("select({role:'branch',index:0})")
    field=page.locator('[data-field=count]');field.fill('0');field.press('Enter')
    assert stored(page)==before
    field.fill('3');page.locator('[data-field=arrangement]').select_option('parallel')
    page.wait_for_function("!document.querySelector('[data-group-apply]').disabled")
    page.locator('[data-group-cancel]').click();assert stored(page)==before

def test_kelvin_cache_is_unchanged_by_repeated_unit_switches(page):
    data=resistance();data['nodes'][0]['value']=273.15
    load(page,data)
    result=page.evaluate("""async()=>{
      const initial=canonicalTemperatures.get('a').kelvin;
      for(let i=0;i<120;i++)await changeQuantityUnit('T',['°C','°F','K'][i%3]);
      return {same:Object.is(initial,canonicalTemperatures.get('a').kelvin),unit:S.data.units.T,value:S.data.nodes[0].value};
    }""")
    assert result=={'same':True,'unit':'K','value':273.15}

def test_rename_enter_and_direct_units(page):
    load(page,resistance());page.locator('#ed-file').click()
    page.locator('[data-rn=name]').fill('A readable diagram name saved with Enter')
    page.locator('[data-rn=name]').press('Enter')
    assert page.locator('#ed-file').inner_text()=='A readable diagram name saved with Enter'
    assert page.locator('#ed-settings').is_visible()
    page.locator('#ed-settings').click()
    page.locator('[data-field="unit:T"]').select_option('°F')
    page.wait_for_function("S.data.units.T==='°F'")
    assert page.locator('[data-field=display-mode]').is_visible()

def test_fit_suppresses_a_wheel_burst(page):
    load(page,resistance());page.evaluate('fitFromCommand()')
    original=page.locator('#ed-canvas').get_attribute('viewBox')
    page.locator('#ed-canvas').dispatch_event('wheel',{'deltaY':100,'clientX':400,'clientY':300})
    assert page.locator('#ed-canvas').get_attribute('viewBox')==original
    page.wait_for_timeout(170)
    page.locator('#ed-canvas').dispatch_event('wheel',{'deltaY':100,'clientX':400,'clientY':300})
    assert page.locator('#ed-canvas').get_attribute('viewBox')!=original

def test_export_dialog_and_units_remain_accessible_on_mobile(page):
    load(page,resistance());page.set_viewport_size({'width':390,'height':760})
    try:
        assert page.locator('#ed-settings').is_visible()
        action(page,'ed-export')
        dialog=page.locator('#ed-export-dialog');box=dialog.bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=390
        page.locator('[data-export-format]').select_option('PNG')
        assert page.locator('[data-export-save]').inner_text()=='Save PNG'
        page.locator('[data-export-close]').click()
    finally:page.set_viewport_size({'width':1280,'height':800})


@pytest.mark.parametrize('theme,background',[('light','rgb(255, 255, 255)'),('dark','rgb(15, 17, 21)')])
def test_export_preview_uses_export_theme_instead_of_editor_theme(page,theme,background):
    load(page,resistance());action(page,'ed-export')
    page.locator('[data-export-theme]').select_option(theme)
    page.wait_for_function("!document.querySelector('[data-export-save]').disabled")
    assert page.locator('[data-export-preview]').evaluate('(el)=>getComputedStyle(el).backgroundColor')==background
    page.locator('[data-export-close]').click()


@pytest.mark.parametrize('initial_count,initial_arrangement,count,arrangement,combined',[
    (1,None,2,'series',20),(1,None,2,'parallel',5),
    (2,'series',3,'series',30),(3,'parallel',2,'parallel',5),
    (2,'series',2,'parallel',5),(2,'parallel',2,'series',20),
    (2,'series',1,None,None), (2,'parallel',1,None,None),
])
def test_count_transition_table(page,initial_count,initial_arrangement,count,arrangement,combined):
    data=resistance()
    if initial_count>1:data['branches'][0].update(count=initial_count,arrangement=initial_arrangement)
    data['branches'][0]['via']=[[300,100],[600,100]]
    load(page,data);before=stored(page)
    page.evaluate("select({role:'branch',index:0})")
    page.locator('[data-field=count]').fill(str(count))
    if arrangement:page.locator('[data-field=arrangement]').select_option(arrangement)
    page.wait_for_function("document.querySelector('[data-group-apply]') && !document.querySelector('[data-group-apply]').disabled")
    assert stored(page)==before
    if combined is not None:assert f'Combined value: {combined}' in page.locator('[data-group-preview]').inner_text()
    page.locator('[data-field=count]').press('Enter');settled(page)
    after=stored(page);branch=after['branches'][0]
    assert branch.get('count',1)==count
    assert branch.get('arrangement')==arrangement
    assert branch['value']==10 and branch['id']=='r'
    assert (branch['from'],branch['to'])==('a','b')
    assert len(branch['via'])==2
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before
    page.locator('#ed-redo').click();settled(page);assert stored(page)==after


def test_group_repeated_draft_changes_and_selection_gate(page):
    load(page,resistance());before=stored(page);page.evaluate("select({role:'branch',index:0})")
    page.locator('[data-field=count]').fill('3');page.locator('[data-field=arrangement]').select_option('series')
    page.wait_for_function("!document.querySelector('[data-group-apply]').disabled")
    first=page.evaluate('JSON.stringify(groupDraft.proposal.document)')
    page.locator('[data-field=arrangement]').select_option('parallel')
    page.locator('[data-field=arrangement]').select_option('series')
    page.wait_for_function("!document.querySelector('[data-group-apply]').disabled")
    assert page.evaluate('JSON.stringify(groupDraft.proposal.document)')==first
    page.evaluate("select({role:'node',index:0})")
    assert page.locator('[data-leave-keep]').is_visible()
    page.locator('[data-leave-keep]').click();assert stored(page)==before
    page.locator('[data-field=count]').press('Escape');assert stored(page)==before


def test_reverse_twice_restores_manual_route_and_explicit_angle(page):
    data=resistance();data['branches'][0].update(kind='rad',angle=45,via=[[300,100],[600,100]],at=[450,100])
    load(page,data);before=stored(page);page.evaluate("select({role:'branch',index:0})")
    page.get_by_role('navigation',name='Property sections').get_by_role('button',name='Connections',exact=True).click()
    page.locator('[data-act=swap]').click();settled(page)
    assert stored(page)['branches'][0]['via']==list(reversed(before['branches'][0]['via']))
    page.locator('[data-act=swap]').click();settled(page);assert stored(page)==before
    page.get_by_role('navigation',name='Property sections').get_by_role('button',name='Appearance',exact=True).click()
    page.locator('[data-act=unpin]').click();settled(page)
    assert stored(page)['branches'][0]['via']==before['branches'][0]['via']
    assert 'at' not in stored(page)['branches'][0]


def test_add_junction_reuses_supplied_existing_node(page):
    data=json.loads((Path(__file__).parent/'fixtures/editor/Just-Ice-Cream.json').read_text(encoding='utf-8'))
    load(page,data)
    page.evaluate("select({role:'branch',index:0})")
    page.get_by_role('navigation',name='Property sections').get_by_role('button',name='Connections',exact=True).click()
    page.locator('[data-act=via-add]').click()
    page.mouse.click(*canvas_point(page,100,10));settled(page)
    after=stored(page)
    assert len(after['nodes'])==5 and len(after['branches'])==5, page.evaluate("({toast:document.querySelector('#ed-toast')?.textContent, busy:document.body.dataset.busy,revision:S.revision})")
    assert after['branches'][0]['from']=='n4'
    assert after['branches'][-1]['kind']=='link'
    assert all(b.get('value') is None for b in after['branches'])


def test_picker_inserts_at_selection_and_documents_prefixes(page):
    load(page,resistance());page.evaluate("select({role:'branch',index:0})")
    label=page.locator('[data-field=label]');label.fill('abcd')
    label.evaluate('(el)=>{el.focus();el.setSelectionRange(1,3)}')
    label.locator('..').locator('.ed-picker-button').click()
    page.get_by_role('button',name='alpha',exact=True).click();settled(page)
    assert stored(page)['branches'][0]['label']=='aαd'
    page.locator('#ed-settings').click()
    unit=page.locator('[data-field="unit:R"]')
    unit.locator('..').locator('.ed-picker-button').click()
    assert page.get_by_role('button',name='milli — 10⁻³',exact=True).is_visible()
    page.locator('.ed-mini-picker').get_by_role('button',name='Close',exact=True).click()


@pytest.mark.parametrize('kind',['free','fixed','phase','break'])
def test_drag_empty_node_exactly_onto_target_preserves_target(page,kind):
    data=resistance();data['nodes'][0].update(kind=kind,label='Target',value=300)
    data['nodes'].append({'id':'empty','at':[450,420]})
    load(page,data);before=stored(page)
    start=canvas_point(page,450,420);end=canvas_point(page,300,250)
    page.mouse.move(*start);page.mouse.down();page.mouse.move(*end,steps=10);page.mouse.up();settled(page)
    after=stored(page)
    assert len(after['nodes'])==2
    assert after['nodes'][0]==before['nodes'][0]
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


@pytest.mark.parametrize('solve,collapsed',[(False,False),(False,True),(True,False),(True,True)])
def test_present_restores_panel_and_solve_state_when_fullscreen_refused(page,solve,collapsed):
    load(page,resistance())
    if collapsed:page.locator('#ed-components-close').click()
    if solve:action(page,'ed-analysis')
    before=page.evaluate('JSON.stringify(S.view)')
    page.evaluate("() => {document.documentElement.requestFullscreen=()=>Promise.reject(new Error('refused'))}")
    action(page,'ed-present')
    page.wait_for_function("document.body.classList.contains('ed-present')")
    page.wait_for_timeout(70)
    box=page.locator('#ed-stage').bounding_box()
    viewport=page.viewport_size
    assert box['width']>=viewport['width']-2 and box['height']>=viewport['height']-2
    page.keyboard.press('Escape')
    page.wait_for_function("!document.body.classList.contains('ed-present')")
    page.wait_for_timeout(70)
    assert page.locator('#ed-solve-panel').is_visible()==solve
    assert page.evaluate('JSON.stringify(S.view)')==before
    if solve:action(page,'ed-analysis')
    if collapsed:
        from editor_actions import menu
        menu(page,'View');page.get_by_label('View menu',exact=True).get_by_role('menuitemcheckbox',name='Components',exact=True).click()


def test_deleting_reference_node_keeps_capacitance_with_detached_rail_end(page):
    data=resistance();data['units']['C']='J/K';data['rail']={'reference':'a','y':500}
    data['branches'].append({'id':'cap','kind':'cap','from':'b','to':'rail','value':2})
    load(page,data);before=stored(page)
    page.evaluate("select({role:'node',index:0})")
    page.locator('[data-act=delete]').click();settled(page)
    after=stored(page);assert 'rail' not in after
    assert len(after['branches'])==2
    assert all(b['to']!='rail' for b in after['branches'])
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


@pytest.mark.parametrize('where,parallel',[(450,True),(330,False)])
def test_palette_resistance_insertion_preserves_original_and_undo(page,where,parallel):
    load(page,resistance());before=stored(page)
    drop_card(page,'conv',*canvas_point(page,where,250));settled(page)
    after=stored(page);assert len(after['branches'])==2
    assert after['branches'][0]['value']==10
    assert after['branches'][1].get('value') is None
    if parallel:
        assert (after['branches'][1]['from'],after['branches'][1]['to'])==('a','b')
        assert after['branches'][0]==before['branches'][0]
    else:
        assert after['nodes'][0]['at']==[300,250]
        assert after['nodes'][1]['at'][0]>600
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


def test_moving_isolated_resistance_in_parallel_keeps_its_value(page):
    data=resistance();data['nodes'] += [{'id':'c','at':[600,430]},{'id':'d','at':[820,430]}]
    data['branches'].append({'id':'moved','from':'c','to':'d','kind':'rad','value':20})
    load(page,data);before=stored(page)
    page.mouse.move(*canvas_point(page,710,430));page.mouse.down()
    page.mouse.move(*canvas_point(page,450,250),steps=10);page.mouse.up();settled(page)
    after=stored(page);assert len(after['nodes'])==2
    assert [b['value'] for b in after['branches']]==[10,20]
    assert after['branches'][1]['id']=='moved'
    assert after['branches'][0]==before['branches'][0]
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before


@pytest.mark.parametrize('existing',[False,True])
def test_crossing_leads_require_an_explicit_connection_choice(page,existing):
    data=resistance();data['nodes'] += [{'id':'c','at':[450,100]},{'id':'d','at':[450,400]}]
    data['branches']=[{'from':'a','to':'b','kind':'link','label':'Horizontal'},
                      {'from':'c','to':'d','kind':'link','label':'Vertical'}]
    if existing:data['nodes'].append({'id':'moving','at':[700,430]})
    load(page,data);before=stored(page)
    if existing:
        page.mouse.move(*canvas_point(page,700,430));page.mouse.down()
        page.mouse.move(*canvas_point(page,450,250),steps=10);page.mouse.up()
    else:drop_card(page,'free',*canvas_point(page,450,250))
    dialog=page.get_by_role('dialog',name='Choose connection');assert dialog.is_visible()
    assert stored(page)==before
    dialog.get_by_role('button',name='Vertical',exact=False).click()
    page.wait_for_function('S.data.branches.length===3');settled(page)
    after=stored(page);assert after['branches'][0]==before['branches'][0]
    assert len(after['nodes'])==5 and len(after['branches'])==3
    assert after['branches'][1]['from'] not in ['a','b']
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before

def test_parallel_drop_clears_insulation_endpoint_labels(page):
    data=json.loads((Path(__file__).parent/'fixtures/editor/Insulation.json').read_text(encoding='utf-8'))
    load(page,data);before=stored(page)
    target=page.evaluate("S.scene.hits.find(h=>h.role==='branch'&&h.element==='symbol'&&S.data.branches[h.index].kind==='conv'&&S.data.nodes.find(n=>n.id===S.data.branches[h.index].from)?.label==='Inner wall of insulation')")
    assert target
    drop_card(page,'cond',*canvas_point(page,*target['at']));settled(page)
    after=stored(page);assert len(after['branches'])==len(before['branches'])+1
    labels=page.evaluate("S.scene.hits.filter(h=>h.element==='label'&&h.role==='node').map(h=>h.bounds)")
    nodes={n['id']:n['at'] for n in after['nodes']};branch=after['branches'][-1]
    assert len(branch['via'])==4
    assert nodes[branch['to']][0]>next(n['at'][0] for n in before['nodes'] if n['id']==branch['to'])
    assert branch['via'][0][1]==nodes[branch['from']][1]
    assert branch['via'][-1][1]==nodes[branch['to']][1]
    assert branch['via'][0][0]>nodes[branch['from']][0]
    assert branch['via'][-1][0]<nodes[branch['to']][0]
    route=[nodes[branch['from']],*branch['via'],nodes[branch['to']]]
    for x,y,xx,yy in labels:
        for a,b in zip(route,route[1:]):
            assert not (a[0]==b[0] and x<a[0]<xx and max(a[1],b[1])>y and min(a[1],b[1])<yy)
            assert not (a[1]==b[1] and y<a[1]<yy and max(a[0],b[0])>x and min(a[0],b[0])<xx)
    assert [{k:v for k,v in b.items() if k not in ['at','via']} for b in after['branches'][:-1]]==[{k:v for k,v in b.items() if k not in ['at','via']} for b in before['branches']]
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before

def test_parallel_expands_before_turning_clear_of_fixed_node_ground(page):
    data=resistance();data['nodes'][1].update(kind='fixed',sub='test')
    data['branches'].append({'from':'a','to':'b','kind':'conv','at':[450,100],'via':[[300,100],[600,100]]})
    load(page,data);before=stored(page)
    drop_card(page,'cond',*canvas_point(page,450,250));settled(page)
    after=stored(page);new=after['branches'][-1]
    assert len(new.get('via',[]))==4, {'after':after,'toast':page.locator('#ed-toast').inner_text()}
    assert after['nodes'][1]['at'][0]>before['nodes'][1]['at'][0]
    ground=page.evaluate("S.scene.hits.find(h=>h.element==='ground').bounds")
    assert new['via'][-1][0]<ground[0]-10
    assert new['via'][-1][1]==after['nodes'][1]['at'][1]
    assert new['via'][1][1]>after['nodes'][1]['at'][1]
    assert after['branches'][0]['value']==10
    page.locator('#ed-undo').click();settled(page);assert stored(page)==before
    page.locator('#ed-redo').click();settled(page);assert stored(page)==after
