"""Gesture transactions, delayed responses and physical authoring in Chromium."""
import copy
import json
import pathlib

import pytest

from test_editor_ui import served, stored, settled, canvas_point

pw_api = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def page(served):
    with pw_api.sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        context.add_init_script("localStorage.setItem('thermodraw:toured','1')")
        p = context.new_page()
        def expose(route):
            response = route.fetch()
            hook = "\nObject.assign(window,{newFile,S,rpc,edit,select,removeSelected,undo,bake,setView,alignedSnap,unitsPerPixel,moveGroup,cancelGesture});"
            hook += "Object.defineProperties(window,{baking:{get:()=>baking},previewFrame:{get:()=>previewFrame}});"
            route.fulfill(response=response, body=response.text() + hook)
        p.route("**/editor/editor.js*", expose)
        errors = []
        p.on("pageerror", lambda e: errors.append(str(e)))
        p.goto(served)
        p.wait_for_selector("#ed-loading", state="hidden", timeout=180000)
        yield p
        browser.close()
        assert not errors, errors


def load(page, data):
    page.mouse.up()
    page.keyboard.up("Alt")
    page.locator("#ed-canvas").focus()  # Leave any old inspector field before switching files.
    page.evaluate("d => {newFile('Interaction test', d);}", copy.deepcopy(data))
    settled(page)
    page.evaluate("() => { S.touched=true; setView({x:0,y:0,w:1000,h:600}); }")


def pick_value(page,key):
    page.locator('#ed-solve-toolbar [data-values-open]').click()
    page.locator(f'#ed-solve-values [data-physics-value="{key}"]').click()


def nodes():
    return {"nodes": [{"id": "a", "at": [300, 250]}, {"id": "b", "at": [600, 250]}], "branches": [], "sources": []}


def test_cancel_and_undo_leave_no_unsaved_movement(page):
    load(page, nodes())
    original = stored(page)
    x, y = canvas_point(page, 300, 250)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 55, y + 55, steps=5)
    assert page.evaluate("S.preview !== null")
    assert stored(page) == original
    page.keyboard.press("Escape")
    page.mouse.up()
    assert page.evaluate("S.preview === null && S.undo.length === 0")
    assert page.evaluate("S.data") == original
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 55, y + 55, steps=5)
    page.dispatch_event("#ed-canvas", "pointercancel", {"pointerId": 1})
    page.mouse.up()
    assert page.evaluate("S.data") == original
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 55, y + 55, steps=5)
    page.mouse.up()
    settled(page)
    assert stored(page)["nodes"][0]["at"] != original["nodes"][0]["at"]
    page.keyboard.press("Control+z")
    settled(page)
    assert stored(page) == original


def test_delayed_scene_and_bake_cannot_overwrite_newer_edits(page):
    load(page, nodes())
    page.evaluate("""() => {
      window.originalRpc=rpc.call;
      window.pendingScene=null;
      rpc.call=(op,...args)=>originalRpc(op,...args).then(result=>{
        if(op==='scene' && !window.delayedOnce) {window.delayedOnce=true;return new Promise(resolve=>window.pendingScene=()=>resolve(result));}
        return result;
      });
      edit(d=>d.nodes[0].label='obsolete');
    }""")
    page.wait_for_function("window.pendingScene !== null")
    page.evaluate("() => {newFile('Other',{nodes:[{id:'other',at:[300,250],label:'current file'}]}); pendingScene();}")
    settled(page)
    assert "obsolete" not in page.locator("#ed-drawing").text_content()
    assert "current file" in page.locator("#ed-drawing").text_content()
    page.evaluate("() => {rpc.call=originalRpc;}")
    load(page, nodes())
    page.evaluate("""() => {
      window.pendingSolve=null; window.delayedSolve=false;
      rpc.call=(op,...args)=>originalRpc(op,...args).then(result=>{
        if(op==='solve' && !window.delayedSolve) {window.delayedSolve=true;return new Promise(resolve=>window.pendingSolve=()=>resolve(result));}
        return result;
      });
      delete S.data.nodes[0].at; bake();
    }""")
    page.wait_for_function("window.pendingSolve !== null")
    page.evaluate("() => {edit(d=>d.nodes[0].label='keep this edit');pendingSolve();}")
    page.wait_for_function("!baking")
    assert stored(page)["nodes"][0]["label"] == "keep this edit"
    page.evaluate("() => {rpc.call=originalRpc;}")


@pytest.mark.parametrize("dx,dy", [(160, 100), (-160, 100), (160, -100), (-160, -100)])
def test_rectangles_draw_in_every_direction_and_resize(page, dx, dy):
    load(page, {"nodes": []})
    page.click('[data-category-tab="Physical"]')
    page.click('[data-sketch="region"]')
    page.mouse.move(650, 400)
    page.mouse.down()
    page.mouse.move(650 + dx, 400 + dy, steps=5)
    page.mouse.up()
    settled(page)
    r = stored(page)["regions"][0]
    assert all(n > 0 for n in r["size"])
    assert page.locator("#ed-drawing rect").count() == 1
    assert page.locator("[data-resize]").count() == 4
    page.keyboard.press("Escape")
    before = r["size"]
    c = page.locator('[data-resize="2"]').bounding_box()
    page.mouse.move(c["x"] + c["width"] / 2, c["y"] + c["height"] / 2)
    page.mouse.down()
    page.mouse.move(c["x"] + 50, c["y"] + 50, steps=5)
    page.mouse.up()
    settled(page)
    assert stored(page)["regions"][0]["size"] != before


def test_labels_are_draggable_and_brackets_are_text(page):
    d = nodes()
    d["nodes"][0]["label"] = "A"
    load(page, d)
    label = page.locator('#ed-hits rect[data-role="node"][data-index="0"][data-element="label"]')
    box = label.bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 35, y - 50, steps=5)
    page.mouse.up()
    settled(page)
    assert "label_offset" in stored(page)["nodes"][0]
    page.evaluate("select({role:'node',index:0})")
    field = page.locator('input[data-field="label"]')
    field.fill("A")
    field.press("End")
    field.press("[")
    field.press("]")
    assert field.input_value() == "A[]"
    assert stored(page)["nodes"][0].get("angle", 0) == 0


def test_stationary_labels_do_not_jump_during_case_drag(page):
    d = json.loads((pathlib.Path(__file__).parents[1] / "examples/hero.json").read_text(encoding="utf-8"))
    d["nodes"][1]["at"] = [372, 150]
    load(page, d)
    before = page.evaluate("S.scene.preview.filter(p=>p.element==='label'&&p.role==='node'&&p.index===0).map(p=>p.markup).join('')")
    x, y = canvas_point(page, 372, 150)
    page.mouse.move(x, y)
    page.mouse.down()
    page.keyboard.down("Alt")
    page.mouse.move(x + 8, y, steps=3)
    page.wait_for_function("S.preview !== null && previewFrame === null")
    assert page.evaluate("s=>document.getElementById('ed-drawing').innerHTML.includes(s)", before)
    page.keyboard.up("Alt")
    page.mouse.up()
    settled(page)


def test_physical_surface_budget_and_deletion(page):
    load(page, {"nodes": [], "control_volumes": [{"id": "cv", "at": [300, 200], "size": [300, 200], "generation": 0, "steady": True}]})
    page.evaluate("select({role:'volume',index:0},false)")
    page.click('[data-category-tab="Physical"]')
    page.click('[data-sketch="surface"]')
    x, y = canvas_point(page, 600, 300)
    page.mouse.click(x, y)
    settled(page)
    assert stored(page)["control_surfaces"][0]["edge"] == "right"
    page.keyboard.press("Escape")
    page.click('[data-category-tab="Physical"]')
    page.click('[data-sketch="transfer"]')
    page.mouse.click(x, y)
    settled(page)
    assert stored(page)["transfers"][0]["surface"] == stored(page)["control_surfaces"][0]["id"]
    page.fill('[data-physical="rate"]', "100")
    page.locator('[data-physical="rate"]').press("Tab")
    settled(page)
    assert page.evaluate("S.scene.budgets[0].status") == "unbalanced"
    page.evaluate("select({role:'surface',index:0},false);removeSelected()")
    settled(page)
    assert not stored(page)["transfers"][0].get("surface")
    assert page.evaluate("S.scene.budgets[0].status") == "unchecked"
    page.evaluate("undo()")
    settled(page)
    assert stored(page)["transfers"][0]["surface"]


def test_connected_detour_preview_and_cancellation(page):
    d = nodes()
    d["nodes"].append({"id": "c", "at": [800, 250]})
    d["branches"] = [{"from": "a", "to": "b", "kind": "cond"}, {"from": "b", "to": "c", "kind": "cond"}]
    load(page, d)
    x, y = canvas_point(page, 450, 250)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x, y + 60, steps=5)
    page.wait_for_function("S.preview !== null && previewFrame === null")
    assert len(page.evaluate("S.preview.branches[0].via")) == 2
    assert page.locator('#ed-drawing g[data-routed] polyline').count() == 2
    page.mouse.move(x, y + 32, steps=3)
    page.wait_for_function("previewFrame === null")
    assert len(page.evaluate("S.preview.branches[0].via")) == 2
    page.mouse.move(x, y + 20, steps=3)
    page.wait_for_function("previewFrame === null")
    assert not page.evaluate("S.preview.branches[0].via")
    page.keyboard.press("Escape")
    page.mouse.up()
    assert stored(page)["branches"] == d["branches"]


@pytest.mark.parametrize("width", [500, 1500])
def test_alignment_hysteresis_and_alt_at_zoom(page, width):
    load(page, nodes())
    page.evaluate("w=>setView({x:0,y:0,w,h:600})", width)
    x, y = canvas_point(page, 300, 250)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 30, y + 11, steps=4)
    page.wait_for_function("S.preview !== null && previewFrame === null")
    assert page.evaluate("S.preview.nodes[0].at[1]") == 250
    page.mouse.move(x + 35, y + 19, steps=3)
    page.wait_for_function("previewFrame === null")
    assert page.evaluate("S.preview.nodes[0].at[1]") == 250
    page.mouse.move(x + 35, y + 23, steps=3)
    page.wait_for_function("previewFrame === null")
    assert page.evaluate("S.preview.nodes[0].at[1]") != 250
    page.keyboard.down("Alt")
    page.mouse.move(x + 33, y + 11, steps=3)
    page.wait_for_function("previewFrame === null")
    assert page.evaluate("S.preview.nodes[0].at[1]") != 250
    page.keyboard.up("Alt")
    page.keyboard.press("Escape")
    page.mouse.up()


def test_group_translation_preserves_routes_and_shared_region_ownership(page):
    d = nodes()
    d.update(branches=[{"from":"a", "to":"b", "kind":"cond", "via":[[300,350],[600,350]], "at":[450,350]}],
             sources=[{"to":"a", "kind":"heat", "at":[200,250]}],
             regions=[{"id":"r1", "at":[100,100], "size":[50,50]}, {"id":"r2", "at":[150,100], "size":[50,50]}],
             control_volumes=[{"id":"cv", "at":[90,90], "size":[120,80], "regions":["r1","r2"]}])
    load(page,d)
    page.evaluate("edit(()=>moveGroup([{role:'node',index:0},{role:'node',index:1},{role:'region',index:0},{role:'region',index:1}],20,30))")
    settled(page)
    moved=stored(page)
    assert moved["branches"][0]["via"] == [[320,380],[620,380]]
    assert moved["sources"][0]["at"] == [220,280]
    assert moved["control_volumes"][0]["at"] == [110,120]
    page.evaluate("undo()")
    settled(page)
    assert stored(page)["control_volumes"][0]["at"] == [90,90]


def test_pinch_interrupts_preview_without_committing(page):
    load(page,nodes())
    x,y=canvas_point(page,300,250)
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+40,y+40,steps=4)
    page.wait_for_function("S.preview !== null")
    page.dispatch_event("#ed-canvas","pointerdown",{"pointerId":22,"pointerType":"touch","clientX":700,"clientY":500})
    assert page.evaluate("S.preview === null && S.undo.length === 0")
    page.dispatch_event("#ed-canvas","pointerup",{"pointerId":22,"pointerType":"touch","clientX":700,"clientY":500})
    page.mouse.up()
    assert stored(page)["nodes"][0]["at"] == [300,250]


def test_narrow_sketch_and_document_preview(page):
    load(page,{"nodes":[],"regions":[{"id":"r","at":[300,200],"size":[200,100]}]})
    page.set_viewport_size({"width":375,"height":720})
    page.click("#ed-more")
    page.click('[data-go="ed-sketch"]')
    page.click('[data-category-tab="Physical"]')
    assert page.locator('[data-sketch="region"]').is_visible()
    page.keyboard.press("Escape")
    page.click("#ed-more")
    page.click('[data-go="ed-export"]')
    page.click('[data-x="document"]')
    page.wait_for_function("document.querySelector('#ed-document-preview img')?.naturalWidth > 0")
    assert page.locator("#ed-document-preview img").count() == 1
    assert not page.locator("#ed-document-preview .ed-sel").count()
    assert page.locator("#ed-save-svg").is_visible()
    page.keyboard.press("Escape")
    page.set_viewport_size({"width":1280,"height":800})


def test_palette_cancel_and_source_attachment(page):
    from test_editor_ui import drop_card
    load(page,nodes())
    page.locator('[data-category-tab="Network"]').click()
    page.locator('.ed-card[data-key="diss"]').scroll_into_view_if_needed()
    box=page.locator('.ed-card[data-key="diss"]').bounding_box()
    page.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
    page.mouse.down();page.mouse.move(600,350,steps=5)
    page.keyboard.press("Escape");page.mouse.up()
    assert not stored(page)["sources"]
    x,y=canvas_point(page,300,250)
    drop_card(page,"diss",x,y)
    settled(page)
    assert len(stored(page)["nodes"]) == 2
    assert stored(page)["sources"][0]["to"] == "a"


def test_endpoint_click_and_drag_preserve_other_node_ids(page):
    d=nodes()
    d["nodes"].append({"id":"c","at":[600,450]})
    for n in d["nodes"]: n["label"]=n["id"]
    d["branches"]=[{"from":"a","to":"b"}]
    load(page,d)
    page.evaluate("select({role:'branch',index:0},false)")
    page.click('[data-endpoint="to"]')
    x,y=canvas_point(page,600,450);page.mouse.click(x,y)
    settled(page)
    assert stored(page)["branches"][0]["to"] == "c"
    assert len(stored(page)["nodes"]) == 3
    page.evaluate("select({role:'branch',index:0},false)")
    box=page.locator('[data-endpoint="to"]').bounding_box()
    page.mouse.move(box["x"]+box["width"]/2,box["y"]+box["height"]/2)
    page.mouse.down();x,y=canvas_point(page,600,250);page.mouse.move(x,y,steps=5);page.mouse.up()
    settled(page)
    assert stored(page)["branches"][0]["to"] == "b"
    assert len(stored(page)["nodes"]) == 3


def test_delayed_scene_after_undo_cannot_restore_undone_label(page):
    load(page,nodes())
    page.evaluate("""() => {
      window.originalRpc=rpc.call;window.pendingScene=null;window.held=false;
      rpc.call=(op,...args)=>originalRpc(op,...args).then(result=>{
        if(op==='scene' && !held) {held=true;return new Promise(resolve=>pendingScene=()=>resolve(result));}
        return result;
      });
      edit(d=>d.nodes[0].label='undone label');
    }""")
    page.wait_for_function("pendingScene !== null")
    page.evaluate("() => {undo();pendingScene();}")
    settled(page)
    assert not stored(page)["nodes"][0].get("label")
    assert "undone label" not in page.locator("#ed-drawing").text_content()
    page.evaluate("() => {rpc.call=originalRpc;}")


def test_quick_add_requires_intent_and_slash_respects_text(page):
    load(page,nodes())
    page.evaluate("select({role:'node',index:0})")
    x,y=canvas_point(page,800,100)
    page.mouse.click(x,y)
    assert page.evaluate("S.sel === null")
    assert page.locator("#ed-quick").is_hidden()
    assert page.locator("#ed-popover").is_hidden()
    page.mouse.click(x,y,button="right")
    assert page.locator("#ed-quick-input").evaluate("e=>e===document.activeElement")
    page.keyboard.press("Escape")
    page.locator("#ed-canvas").focus()
    page.mouse.move(x+30,y)
    page.keyboard.press("/")
    assert page.locator("#ed-quick-input").evaluate("e=>e===document.activeElement")
    assert page.locator("#ed-quick-input").input_value() == ""
    page.keyboard.type("/")
    assert page.locator("#ed-quick-input").input_value() == "/"
    page.keyboard.press("Escape")
    page.evaluate("select({role:'node',index:0})")
    label=page.locator('input[data-field="label"]')
    label.fill("A");label.press("End");label.press("/")
    assert label.input_value() == "A/"
    assert page.locator("#ed-quick").is_hidden()
    page.keyboard.press("Escape")


@pytest.mark.parametrize("interrupt", [None,"move","cancel","pinch"])
def test_touch_quick_add_hold_and_interruptions(page,interrupt):
    load(page,nodes())
    x,y=canvas_point(page,450,450)
    cdp=page.context.new_cdp_session(page)
    point={"x":x,"y":y,"id":1}
    cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[point]})
    if interrupt=="move":
        cdp.send("Input.dispatchTouchEvent",{"type":"touchMove","touchPoints":[{**point,"x":x+30}]})
    elif interrupt=="cancel":
        cdp.send("Input.dispatchTouchEvent",{"type":"touchCancel","touchPoints":[]})
    elif interrupt=="pinch":
        cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[point,{"x":x+60,"y":y,"id":2}]})
    if interrupt is None:
        page.wait_for_selector("#ed-quick:not([hidden])")
    else:
        page.wait_for_timeout(650)  # Past the 500 ms hold deadline: no deferred menu.
        assert page.locator("#ed-quick").is_hidden()
    if interrupt != "cancel":
        cdp.send("Input.dispatchTouchEvent",{"type":"touchEnd","touchPoints":[]})
    if interrupt is None:
        assert page.locator("#ed-quick-input").evaluate("e=>e===document.activeElement")
        page.keyboard.press("Escape")
    cdp.detach()


def test_clipboard_network_keyboard_paste_and_undo(page):
    page.context.grant_permissions(["clipboard-read","clipboard-write"])
    d=nodes();d["branches"]=[{"id":"r","from":"a","to":"b","via":[[300,350],[600,350]],"label_offset":[0,20]}]
    load(page,d)
    page.evaluate("select({role:'branch',index:0},false)")
    page.keyboard.press("Control+c")
    page.keyboard.press("Control+v")
    page.wait_for_function("S.data.branches.length===2")
    settled(page)
    copied=stored(page)
    assert len(copied["nodes"]) == 4
    assert copied["branches"][1]["from"] == copied["nodes"][2]["id"] != "a"
    assert copied["branches"][1]["to"] == copied["nodes"][3]["id"] != "b"
    assert copied["branches"][1]["via"] == [[320,370],[620,370]]
    assert copied["branches"][1]["label_offset"] == [0,20]
    page.keyboard.press("Control+z");settled(page)
    assert len(stored(page)["branches"]) == 1


def test_clipboard_physical_references_remap_together(page):
    d={"nodes":[],"regions":[{"id":"r","at":[100,100],"size":[100,100]}],
       "control_volumes":[{"id":"cv","at":[90,90],"size":[120,120],"regions":["r"],"steady":True,"generation":0}],
       "control_surfaces":[{"id":"s","volume":"cv"}],"transfers":[{"id":"q","surface":"s","rate":0}]}
    load(page,d)
    page.evaluate("select({role:'volume',index:0},false)")
    page.keyboard.press("Control+c");page.keyboard.press("Control+v")
    page.wait_for_function("S.data.control_volumes.length===2")
    settled(page)
    data=stored(page)
    assert data["control_volumes"][1]["regions"] == [data["regions"][1]["id"]]
    assert data["control_surfaces"][1]["volume"] == data["control_volumes"][1]["id"]
    assert data["transfers"][1]["surface"] == data["control_surfaces"][1]["id"]
    assert page.evaluate("S.scene.budgets.every(b=>b.status==='balanced')")


def test_text_clipboard_remains_native(page):
    load(page,nodes())
    page.evaluate("select({role:'node',index:0})")
    field=page.locator('input[data-field="label"]')
    field.fill("ordinary text");field.press("Control+a");field.press("Control+c")
    field.fill("");field.press("Control+v")
    assert field.input_value() == "ordinary text"
    assert len(stored(page)["nodes"]) == 2


@pytest.mark.parametrize("edge,dx,dy,dimension",[("right",45,0,0),("bottom",0,45,1)])
def test_shift_selected_regions_resize_together(page,edge,dx,dy,dimension):
    d={"nodes":[],"regions":[{"id":"a","at":[200,200],"size":[150,100]},
                              {"id":"b","at":[500,200],"size":[200,140]},
                              {"id":"c","at":[800,200],"size":[100,100]}]}
    load(page,d)
    page.keyboard.down("Shift")
    page.mouse.click(*canvas_point(page,300,260))
    page.mouse.click(*canvas_point(page,600,260));page.keyboard.up("Shift")
    assert page.evaluate("S.selection.length") == 2
    box=page.locator(f'[data-resize-edge="{edge}"]').bounding_box()
    x,y=box["x"]+box["width"]/2,box["y"]+box["height"]/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y+dy,steps=5)
    page.wait_for_function("S.preview !== null && previewFrame===null")
    assert stored(page)["regions"] == d["regions"]
    preview=page.evaluate("S.preview.regions")
    delta=preview[0]["size"][dimension]-d["regions"][0]["size"][dimension]
    assert delta > 0
    assert preview[1]["size"][dimension]-d["regions"][1]["size"][dimension] == delta
    assert preview[0]["size"][1-dimension] == d["regions"][0]["size"][1-dimension]
    assert preview[2] == d["regions"][2]
    page.mouse.up();settled(page)
    assert page.evaluate("S.undo.length") == 1
    page.keyboard.press("Control+z");settled(page)
    assert stored(page)["regions"] == d["regions"]


def test_shared_resize_clamps_and_escape_restores_all(page):
    d={"nodes":[],"regions":[{"id":"a","at":[200,200],"size":[50,100]},
                              {"id":"b","at":[500,200],"size":[150,100]}]}
    load(page,d)
    page.keyboard.down("Shift")
    page.mouse.click(*canvas_point(page,225,260));page.mouse.click(*canvas_point(page,600,260))
    page.keyboard.up("Shift")
    box=page.locator('[data-resize-edge="left"]').bounding_box()
    x,y=box["x"]+box["width"]/2,box["y"]+box["height"]/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+100,y,steps=6)
    page.wait_for_function("S.preview !== null && previewFrame===null")
    preview=page.evaluate("S.preview.regions")
    assert preview[0]["size"] == [10,100]
    assert preview[1]["size"] == [110,100]
    assert preview[0]["at"][0]+preview[0]["size"][0] == 250
    assert preview[1]["at"][0]+preview[1]["size"][0] == 650
    page.keyboard.press("Escape");page.mouse.up()
    assert stored(page)["regions"] == d["regions"]
    assert page.evaluate("S.undo.length") == 0


def physics_network():
    return {"units": {"T": "K", "R": "K/W"}, "nodes": [
        {"id": "hot", "kind": "fixed", "value": 400, "at": [200, 300]},
        {"id": "mid", "at": [420, 300]},
        {"id": "cold", "kind": "fixed", "value": 300, "at": [640, 300]}],
        "branches": [{"from": "hot", "to": "mid", "value": 2},
                     {"from": "mid", "to": "cold", "value": 3}]}


def test_physics_configure_review_apply_and_undo(page):
    load(page, physics_network())
    page.locator('#ed-analysis').click()
    page.locator('[data-set-time]').click()
    page.locator('[data-analysis-steady]').select_option('steady')
    pick_value(page,'node:1:value')
    page.locator('[data-physics-mode="unknown"]').click()
    configured = stored(page)
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert stored(page) == configured
    assert '360' in page.locator('#ed-solve-panel').inner_text()
    page.locator('[data-physics-apply]').click()
    page.locator('[data-session-commit]').click()
    settled(page)
    assert stored(page)['nodes'][1]['value'] == pytest.approx(360)
    page.evaluate('undo()')
    settled(page)
    assert stored(page) == configured


def test_physics_delayed_result_cannot_apply_after_edit_or_switch(page):
    for switch in (False, True):
        d = physics_network()
        d['analysis'] = {'network': {'steady': True, 'unknowns': ['mid']}}
        load(page, d)
        page.locator('#ed-analysis').click()
        page.wait_for_function("!document.querySelector('[data-physics-run]').disabled")
        page.evaluate("""() => {window.realPhysicsCall=rpc.call;rpc.call=(op,...args)=>op==='physics_session'?new Promise(resolve=>{window.finishPhysics=()=>realPhysicsCall(op,...args).then(resolve)}):realPhysicsCall(op,...args)}""")
        page.locator('#ed-analysis').click()
        page.locator('[data-physics-run]').click()
        if switch:
            page.evaluate("newFile('Other', {nodes:[]})")
        else:
            page.evaluate("edit(d=>d.nodes[0].value=500)")
        expected=stored(page)
        page.evaluate('async () => {await finishPhysics();rpc.call=realPhysicsCall}')
        settled(page)
        page.locator('#ed-analysis').click()
        assert page.locator('[data-physics-apply]').count() == 0
        assert stored(page) == expected


def test_physics_volume_unknown_control(page):
    d={"control_volumes":[{"id":"cv","at":[200,200],"size":[250,150],"generation":0,"steady":True}],
       "control_surfaces":[{"id":"s","volume":"cv","area":2}],
       "transfers":[{"id":"in","surface":"s","direction":"in","rate":100},{"id":"out","surface":"s"}]}
    load(page,d)
    page.locator('#ed-analysis').click()
    pick_value(page,'transfer:1:rate')
    page.locator('[data-physics-mode="unknown"]').click()
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    page.locator('[data-physics-apply]').click()
    page.locator('[data-session-commit]').click()
    settled(page)
    assert stored(page)['transfers'][1]['rate']==pytest.approx(100)


def test_simple_canvas_selection_known_edit_and_export(page):
    load(page, physics_network())
    before = stored(page)
    page.locator('#ed-analysis').click()
    page.locator('.ed-physics-marks [data-physics-pick="node:1:value"]').last.click()
    assert page.locator('#ed-solve-value').is_visible()
    assert stored(page) == before
    editor_box=page.locator('#ed-solve-value').bounding_box()
    body_box=page.locator('#ed-canvas').bounding_box()
    assert editor_box['y'] >= body_box['y']
    page.locator('[data-physics-mode="unknown"]').click()
    assert page.locator('[data-physics-cycle="node:1:value"]').get_attribute('data-state')=='unknown'
    pick_value(page,'node:0:value')
    page.locator('[data-physics-number]').fill('410')
    page.locator('[data-physics-number]').press('Tab')
    assert stored(page)['nodes'][0]['kind'] == 'fixed'
    assert float(stored(page)['nodes'][0]['value']) == 400
    assert page.locator('[data-physics-cycle="node:0:value"]').get_attribute('data-state')=='override'
    assert page.locator('[data-physics-mode="unknown"]').is_disabled()
    svg = page.evaluate("async () => rpc.call('export',S.data,'svg','light',S.notation)")
    assert 'ed-physics-marks' not in svg and 'data-physics-pick' not in svg
    page.locator('[data-physics-close]').click()
    page.locator('[data-session-discard]').click()
    assert page.locator('.ed-physics-marks').inner_html() == ''
    assert page.locator('#ed-component-tools').is_visible()


def test_simple_missing_area_and_one_unknown_guidance(page):
    d={"control_volumes":[{"id":"cv","generation":0,"steady":True,"at":[200,200],"size":[250,150]}],
       "control_surfaces":[{"id":"s","volume":"cv"}],
       "transfers":[{"id":"in","surface":"s","direction":"in","flux":100},{"id":"out","surface":"s"}]}
    load(page,d)
    page.locator('#ed-analysis').click()
    pick_value(page,'transfer:1:rate')
    page.locator('[data-physics-mode="unknown"]').click()
    pick_value(page,'transfer:0:flux')
    assert page.locator('[data-physics-mode="unknown"]').is_disabled()
    assert 'Another value is unknown' in page.locator('#ed-solve-value').inner_text()
    pick_value(page,'surface:0:area')
    assert page.locator('[data-physics-number]').get_attribute('aria-invalid')=='true'
    page.locator('[data-physics-number]').fill('2')
    page.locator('[data-physics-number]').press('Tab')
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert '200' in page.locator('.ed-answer').inner_text()


def test_simple_narrow_dark_scroll_and_close(page):
    load(page,physics_network())
    page.locator('#ed-analysis').click()
    page.evaluate("document.documentElement.dataset.theme='dark'")
    assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == 'dark'
    assert page.locator('.ed-solve-body').evaluate("e=>getComputedStyle(e).scrollbarColor") != 'auto'
    page.set_viewport_size({'width':375,'height':812})
    assert page.locator('#ed-solve-panel').is_visible()
    page.locator('.ed-solve-body').evaluate('e=>e.scrollTop=e.scrollHeight')
    box=page.locator('[data-physics-run]').bounding_box()
    assert 0 <= box['y'] < 812-box['height']
    page.keyboard.press('Escape')
    assert page.locator('#ed-solve-panel').is_hidden()
    page.set_viewport_size({'width':1280,'height':800})
    page.evaluate("document.documentElement.dataset.theme='light'")


def test_examples_show_only_answered_homework(page):
    load(page,physics_network())
    page.locator('#ed-open-example').click()
    page.locator('#ed-examples li[data-path]').first.wait_for(state='visible')
    assert page.locator('#ed-examples li[data-path]:visible').count() == 4
    assert page.locator('#ed-examples summary').count() == 0
    for slug, title in [('oven', 'HW2 1.44 - Annealing oven'), ('frost', 'HW2 1.51 - Melting frost'), ('wall', 'HW2 1.57a - Oven wall'), ('hot-plate', 'HW2 1.60a - Hot plate')]:
        page.locator(f'#ed-examples li[data-path="../homework/{slug}.json"] button').click()
        page.wait_for_function("title => S.data.title === title", arg=title)
        assert page.evaluate('S.data.regions.length') > 0
        page.locator('#ed-open-example').click()
    page.locator('#ed-open-example').click()


def test_session_override_unit_reset_and_discard_preserves_document(page):
    d=physics_network();d['nodes'][1]['value']=360
    d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);before=stored(page)
    page.locator('#ed-analysis').click()
    pick_value(page,'node:1:value')
    page.locator('[data-physics-mode="unknown"]').click()
    pick_value(page,'branch:0:value')
    page.locator('[data-physics-number]').fill('3000')
    page.locator('[data-physics-number]').press('Tab')
    page.locator('[data-physics-unit]').select_option('K/kW')
    page.locator('[data-physics-unit]').press('Tab')
    page.wait_for_function("document.querySelector('[data-physics-number]')?.value==='3'")
    assert stored(page)==before
    assert page.evaluate('S.undo.length')==0
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert '350' in page.locator('.ed-answer').inner_text()
    assert 'Drawing: 360' in page.locator('.ed-answer').inner_text()
    assert stored(page)==before
    page.locator('[data-session-reset-field]').click()
    assert page.locator('[data-physics-number]').input_value()=='2'
    page.locator('[data-physics-number]').fill('5')
    page.locator('[data-physics-number]').press('Tab')
    page.locator('[data-physics-close]').click()
    page.locator('[data-session-keep]').click()
    assert page.locator('#ed-solve-panel').is_visible()
    page.locator('[data-physics-close]').click()
    page.locator('[data-session-discard]').click()
    assert stored(page)==before
    assert page.evaluate('S.undo.length')==0


def test_session_underlying_edit_requires_restart(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d)
    page.locator('#ed-analysis').click()
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    page.evaluate('edit(d=>d.nodes[0].value=450)')
    assert page.locator('[data-physics-run]').is_disabled()
    assert page.locator('[data-physics-apply]').count()==0
    page.locator('[data-session-restart]').click()
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert '390' in page.locator('.ed-answer').inner_text()


def test_session_complete_scenario_applies_inputs_and_result_together(page):
    d=physics_network();d['nodes'][1]['value']=360
    d['analysis']={'network':{'steady':True,'unknowns':[]}}
    load(page,d);before=stored(page)
    page.locator('#ed-analysis').click()
    assert page.locator('[data-physics-run]').is_disabled()
    assert page.locator('[data-physics-check]').inner_text()=='Check supplied values'
    pick_value(page,'node:1:value')
    page.locator('[data-physics-mode="unknown"]').click()
    pick_value(page,'node:0:value')
    page.locator('[data-physics-number]').fill('450')
    page.locator('[data-physics-number]').press('Tab')
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    page.locator('[data-physics-apply]').click()
    assert stored(page)==before
    assert page.locator('[data-session-commit]').is_visible()
    page.locator('[data-session-commit]').click()
    settled(page)
    data=stored(page)
    assert float(data['nodes'][0]['value'])==450
    assert data['nodes'][1]['value']==pytest.approx(390)
    assert page.evaluate('S.undo.length')==1
    page.evaluate('undo()');settled(page)
    assert stored(page)==before


def test_session_auto_placement_invalidates_snapshot(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d)
    page.locator('#ed-analysis').click()
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    # Exercise the automatic placement path, which does not add an undo entry.
    page.evaluate('async () => {delete S.data.nodes[1].at;await bake()}')
    assert page.locator('[data-session-restart]').is_visible()
    assert page.locator('[data-physics-apply]').count()==0


def test_session_assistive_input_commits_on_blur(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);before=stored(page)
    page.locator('#ed-analysis').click()
    pick_value(page,'node:0:value')
    field=page.locator('[data-physics-number]');field.focus()
    field.evaluate("e=>{e.value='450';e.dispatchEvent(new Event('input',{bubbles:true}))}")
    page.locator('[data-physics-unit]').click()
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert '390' in page.locator('.ed-answer').inner_text()
    assert stored(page)==before



def test_solve_badges_cycle_and_preview_restores_saved_drawing(page):
    d=physics_network();d['nodes'][1]['value']=360
    d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);before=stored(page)
    page.locator('#ed-analysis').click()
    badge=page.locator('[data-physics-cycle="node:1:value"]')
    assert badge.get_attribute('data-state')=='known'
    badge.click()
    assert badge.get_attribute('data-state')=='unknown'
    badge.click()
    assert badge.get_attribute('data-state')=='known'  # Override mode alone does not change the input.
    page.locator('[data-physics-number]').fill('375')
    page.locator('[data-physics-number]').press('Tab')
    page.wait_for_function("document.querySelector('#ed-drawing').textContent.includes('375')")
    assert stored(page)==before
    assert page.evaluate('S.undo.length')==0
    svg=page.evaluate("async()=>rpc.call('export',S.data,'svg','light',S.notation)")
    assert '375' not in svg
    badge.click()
    assert badge.get_attribute('data-state')=='known'
    page.wait_for_function("!document.querySelector('#ed-drawing').textContent.includes('375')")
    page.locator('[data-physics-close]').click()
    assert page.locator('#ed-solve-panel').is_hidden()
    assert stored(page)==before


def test_solve_multiple_network_unknowns_and_visible_limits(page):
    d=physics_network();d['nodes'][1]['value']=360
    d['nodes'].insert(2,{'id':'second','value':330,'at':[530,300]})
    d['branches']=[{'from':'hot','to':'mid','value':2},
                   {'from':'mid','to':'second','value':2},
                   {'from':'second','to':'cold','value':2}]
    d['analysis']={'network':{'steady':True,'unknowns':[]}}
    load(page,d);page.locator('#ed-analysis').click()
    for index in (1,2):
        page.locator(f'[data-physics-cycle="node:{index}:value"]').click()
    page.wait_for_function("document.querySelector('.ed-solve-status')?.textContent.includes('2 unknown')")
    page.wait_for_function("document.querySelector('.ed-solve-status')?.textContent.includes('Ready to solve')")
    assert page.locator('#ed-palette').bounding_box()['width']>=340
    page.locator('[data-physics-run]').click()
    page.locator('[data-physics-apply]').wait_for()
    assert page.locator('.ed-answer').count()==2
    pick_value(page,'node:0:value')
    assert 'fixed node stays a boundary' in page.locator('#ed-solve-value').inner_text()
    assert page.locator('[data-physics-mode="unknown"]').is_disabled()


def test_solve_second_volume_unknown_explains_without_replacing(page):
    d={'control_volumes':[{'id':'cv','generation':0,'steady':True,'at':[200,200],'size':[250,150]}],
       'control_surfaces':[{'id':'left','volume':'cv','edge':'left'}, {'id':'right','volume':'cv','edge':'right'}],
       'transfers':[{'id':'in','surface':'left','direction':'in','rate':100},
                    {'id':'out','surface':'right','rate':100}]}
    load(page,d);page.locator('#ed-analysis').click()
    page.locator('[data-physics-cycle="transfer:0:rate"]').click()
    page.locator('[data-physics-cycle="transfer:1:rate"]').click()
    assert page.locator('[data-physics-cycle="transfer:0:rate"]').get_attribute('data-state')=='unknown'
    assert page.locator('[data-physics-cycle="transfer:1:rate"]').get_attribute('data-state')=='known'
    assert 'Only one unknown' in page.locator('#ed-solve-value').inner_text()
    assert page.locator('#ed-solve-value [role="alert"]').is_visible()



def test_auto_label_restores_side_and_preserves_manual_until_requested(page):
    d=nodes();d['nodes'][0].update(label='Manual label',side='down',label_offset=[40,40])
    load(page,d);before=stored(page)
    page.locator('#ed-analysis').click()
    page.locator('[data-physics-close]').click()
    assert stored(page)==before
    page.evaluate("select({role:'node',index:0})")
    assert 'Label position: Manual' in page.locator('#ed-popover').inner_text()
    page.locator('[data-act="auto-label"]').click();settled(page)
    assert 'label_offset' not in stored(page)['nodes'][0]
    assert stored(page)['nodes'][0]['side']=='auto'
    page.evaluate('undo()');settled(page)
    assert stored(page)==before


def test_solve_delayed_schematic_preview_cannot_return_after_close(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);before=page.locator('#ed-drawing').inner_html()
    page.evaluate("""()=>{
      window.oldSceneRpc=rpc.call;window.releaseSolveScene=null;
      rpc.call=(op,...args)=>oldSceneRpc(op,...args).then(result=>op==='scene'
        ?new Promise(resolve=>window.releaseSolveScene=()=>resolve(result)):result);
    }""")
    page.locator('#ed-analysis').click()
    page.wait_for_function('window.releaseSolveScene!==null')
    page.locator('[data-physics-close]').click()
    page.evaluate('async()=>{releaseSolveScene();rpc.call=oldSceneRpc;await new Promise(r=>setTimeout(r,50))}')
    assert page.locator('#ed-drawing').inner_html()==before
    assert page.locator('.ed-physics-marks').inner_html()==''



def test_solve_semantic_color_and_floating_navigator(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);page.locator('#ed-analysis').click()
    page.wait_for_function("document.querySelector('.ed-solve-status')?.classList.contains('ed-solve-success')")
    assert page.locator('#ed-solve-panel [data-physics-number]').count()==0
    assert page.locator('#ed-solve-panel .ed-value-list').count()==0
    assert page.locator('[data-physics-run]').evaluate('e=>e.getBoundingClientRect().height')>=44
    assert page.locator('[data-physics-run]').evaluate('e=>getComputedStyle(e).backgroundColor')=='rgb(33, 99, 59)'
    page.locator('#ed-solve-toolbar [data-values-open]').click()
    page.locator('[data-value-search]').fill('mid')
    page.locator('[data-value-filter]').select_option('unknown')
    assert page.locator('#ed-solve-values tbody tr').count()==1
    page.locator('#ed-solve-values [data-physics-value]').click()
    assert page.locator('#ed-solve-values').is_hidden()
    assert page.locator('#ed-solve-value').is_visible()
    page.keyboard.press('Escape')
    assert page.locator('#ed-solve-value').is_hidden()
    assert page.locator('#ed-solve-panel').is_visible()


def test_override_mode_is_not_a_change_and_close_uses_modal(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);before=stored(page);page.locator('#ed-analysis').click()
    pick_value(page,'node:0:value')
    page.locator('[data-physics-mode="override"]').click()
    assert page.locator('[data-physics-cycle="node:0:value"]').get_attribute('data-state')=='known'
    page.locator('[data-physics-close]').click()
    assert page.locator('#ed-solve-panel').is_hidden()
    assert not page.locator('#ed-solve-close').is_visible()
    page.locator('#ed-analysis').click();pick_value(page,'node:0:value')
    page.locator('[data-physics-number]').fill('410');page.locator('[data-physics-number]').press('Tab')
    page.locator('[data-physics-close]').click()
    assert page.locator('#ed-solve-close').is_visible()
    assert page.locator('[data-session-keep]').evaluate('e=>e===document.activeElement')
    page.keyboard.press('Escape')
    assert page.locator('#ed-solve-close').is_hidden()
    assert page.locator('#ed-solve-panel').is_visible()
    page.locator('[data-physics-close]').click();page.locator('[data-session-discard]').click()
    assert stored(page)==before



def test_value_blur_does_not_swallow_close_click(page):
    d=physics_network();d['analysis']={'network':{'steady':True,'unknowns':['mid']}}
    load(page,d);page.locator('#ed-analysis').click();pick_value(page,'node:0:value')
    page.locator('[data-physics-number]').fill('410')
    page.locator('[data-value-close]').click()
    assert page.locator('#ed-solve-value').is_hidden()
    assert page.locator('[data-physics-cycle="node:0:value"]').get_attribute('data-state')=='override'
    assert float(stored(page)['nodes'][0]['value'])==400



def test_no_unknown_check_is_not_a_failed_solve(page):
    d=physics_network();d['nodes'][1]['value']=350
    d['analysis']={'network':{'steady':True,'unknowns':[]}}
    load(page,d);page.locator('#ed-analysis').click()
    assert 'No unknown selected' in page.locator('.ed-solve-status').inner_text()
    assert page.locator('[data-physics-run]').is_disabled()
    page.locator('[data-physics-check]').click()
    page.wait_for_function("document.querySelector('[data-physics-check]').textContent==='Check again'")
    assert 'Supplied values do not balance' in page.locator('#ed-solve-panel').inner_text()
    assert 'not solved' not in page.locator('#ed-solve-panel').inner_text()
    assert page.locator('[data-physics-run]').is_disabled()
    assert 'Recalculate' not in page.locator('[data-physics-run]').inner_text()


def test_editor_resistance_unknown_and_apply(page):
    d=physics_network();d['nodes'][1]['value']=360;d['branches'][0]['value']=99
    d['analysis']={'network':{'steady':True,'unknowns':[]}}
    load(page,d);before=stored(page);page.locator('#ed-analysis').click()
    pick_value(page,'branch:0:value');page.locator('[data-physics-mode="unknown"]').click()
    page.locator('[data-physics-run]').click();page.locator('[data-physics-apply]').wait_for()
    assert 'Calculated: 2 ' in page.locator('.ed-answer').inner_text()
    page.locator('[data-physics-apply]').click();page.locator('[data-session-commit]').click();settled(page)
    assert stored(page)['branches'][0]['value']==pytest.approx(2)
    page.evaluate('undo()');settled(page);assert stored(page)==before


def test_all_labels_auto_is_one_undoable_action(page):
    d=physics_network()
    for n in d['nodes']:n.update(label_offset=[30,30],side='down')
    load(page,d);before=stored(page)
    page.locator('#ed-auto-labels').click();settled(page)
    assert all('label_offset' not in n and n['side']=='auto' for n in stored(page)['nodes'])
    assert page.evaluate('S.undo.length')==1
    page.evaluate('undo()');settled(page);assert stored(page)==before


def test_component_library_search_and_prerequisites(page):
    load(page, nodes())
    page.locator('#ed-component-search').fill('resistor')
    assert page.locator('.ed-card:visible').count()==7
    page.locator('#ed-component-search').fill('no-such-part')
    assert page.locator('#ed-component-empty').is_visible()
    page.locator('#ed-component-clear').click()
    page.locator('[data-category-tab="Physical"]').click()
    page.locator('.ed-shape-card[data-sketch="surface"]').click()
    assert 'Add a control volume first' in page.locator('#ed-component-note').inner_text()
    page.locator('#ed-component-note [data-sketch="volume"]').click()
    assert page.evaluate('S.mode')=='sketch'
    assert page.locator('.ed-shape-card[data-sketch="volume"]').get_attribute('aria-pressed')=='true'
    page.keyboard.press('Escape')
    page.locator('[data-category-tab="Network"]').click()
    page.locator('.ed-card[data-key="free"]').focus()
    page.keyboard.press('Enter')
    assert page.evaluate('S.mode')=='place'
    page.keyboard.press('Escape')


def test_relationship_picker_and_geometry_validation(page):
    d={'nodes':[], 'regions':[{'id':'material','label':'Insulation','at':[100,100],'size':[100,100]}],
       'control_volumes':[{'id':'cv','at':[300,100],'size':[200,200]}]}
    load(page,d)
    page.evaluate("select({role:'volume',index:0})")
    page.locator('[data-relationship="regions"]').check()
    assert stored(page)['control_volumes'][0]['regions']==['material']
    width=page.locator('[data-physical="width"]')
    width.fill('-1');width.press('Tab')
    assert width.get_attribute('aria-invalid')=='true'
    assert stored(page)['control_volumes'][0]['size']==[200,200]
    width.fill('240');width.press('Tab')
    assert stored(page)['control_volumes'][0]['size']==[240,200]
    page.keyboard.press('Escape')


def test_transfer_input_representation_is_exclusive(page):
    d={'nodes':[], 'control_volumes':[{'id':'cv','at':[300,100],'size':[200,200]}],
       'control_surfaces':[{'id':'face','volume':'cv','area':1}],
       'transfers':[{'id':'heat','surface':'face','rate':40}]}
    load(page,d);page.evaluate("select({role:'transfer',index:0})")
    page.locator('[data-transfer-input]').select_option('flux')
    page.locator('[data-physical="flux"]').fill('40')
    page.locator('[data-physical="flux"]').press('Tab')
    transfer=stored(page)['transfers'][0]
    assert 'rate' not in transfer and float(transfer['flux'])==40
    assert not page.locator('[data-physical="rate"]').count()
    page.keyboard.press('Escape')


def test_component_help_expands_below_its_own_row(page):
    load(page,nodes())
    page.locator('[data-category-tab="Network"]').click()
    help_button=page.locator('.ed-component-help[aria-controls="ed-definition-free"]')
    help_button.click()
    definition=page.locator('#ed-definition-free')
    assert definition.is_visible()
    assert 'temperature node' in definition.inner_text()
    card=page.locator('.ed-card[data-key="free"]').bounding_box()
    assert definition.bounding_box()['y'] >= card['y']+card['height']
    assert help_button.get_attribute('aria-expanded')=='true'
    assert page.locator('#ed-component-note').is_hidden()
    help_button.click()
    assert definition.is_hidden()
    page.locator('[data-category-tab="Physical"]').click()
    page.locator('.ed-component-help[aria-controls="ed-definition-volume"]').click()
    assert page.locator('#ed-definition-volume').is_visible()
    assert page.evaluate('S.mode')=='idle'
