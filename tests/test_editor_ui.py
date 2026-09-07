"""The editor, driven: the built site in headless Chromium.

Skipped unless Playwright is importable. CI's `editor` job installs it and
runs this file alone; the bridge and the site have their own tests in the
ordinary suite. One test, a handful of assertions, one browser: it proves
the page boots the library, that the two ways of adding a symbol and the
handle that connects two nodes write the file the schema describes, that a
drag lands on the grid and on its neighbour's line, that one drop makes a
whole path, that a red dot joins a loose end and only ever onto a node,
that `[` and `]` turn what is selected, that an export is the library's
SVG, and that a share link round-trips.
"""
import functools
import http.server
import json
import pathlib
import socket
import sys
import threading

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

playwright = pytest.importorskip("playwright.sync_api")

pytestmark = pytest.mark.skipif(
    not (ROOT / "examples" / "gallery").exists(),
    reason="examples/ is not installed")


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    import build_site
    site = tmp_path_factory.mktemp("site")
    build_site.build(site)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(site))
    handler.log_message = lambda *a, **k: None  # type: ignore[assignment]
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}/editor/"
    server.shutdown()


def stored(page):
    """The diagram the editor keeps for the open file."""
    return page.evaluate(
        "JSON.parse(localStorage.getItem('thermodraw:file:' + "
        "localStorage.getItem('thermodraw:last')))")


def settled(page, role=None, index=None):
    """The drawing lags an edit by a library round trip; wait for the
    editor to be idle, and for the element's hit rectangle, before
    pointing at anything."""
    page.wait_for_selector("body:not([data-busy])")
    if role is not None:
        page.wait_for_selector(
            f'#ed-hits rect[data-role="{role}"][data-index="{index}"]')


def drop_card(page, key, x, y):
    """Drag a palette card onto the drawing, as a hand does."""
    box = page.locator(f'.ed-card[data-key="{key}"]').bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.mouse.move(x, y, steps=8)
    page.mouse.up()


def codes(page):
    """The finding codes the strip is showing, in its own words."""
    return page.eval_on_selector_all(
        "#ed-findings-list .ed-code", "els => els.map((e) => e.textContent)")


def loose(page):
    """The red dots: where each one is drawn and whose end it is."""
    return page.eval_on_selector_all(
        "#ed-ui .ed-loose",
        "els => els.map((e) => [+e.getAttribute('cx'), "
        "+e.getAttribute('cy'), e.dataset.node])")


def canvas_point(page, x, y):
    """Screen coordinates of a page point, from the canvas's own matrix."""
    return page.evaluate(
        "([x, y]) => { const m = document.getElementById('ed-canvas')"
        ".getScreenCTM(); const p = new DOMPoint(x, y).matrixTransform(m);"
        " return [p.x, p.y]; }", [x, y])


def test_the_editor_draws_what_is_drawn_into_it(served):
    with playwright.sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1280, "height": 800},
                                      permissions=["clipboard-read",
                                                   "clipboard-write"])
        page = context.new_page()
        errors, dialogs = [], []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        page.goto(served)
        # the library boots in a worker; a cold CDN fetch can take a while
        page.wait_for_selector("#ed-loading", state="hidden", timeout=180_000)

        # a first visit is met by the tour, and it advances by doing the
        # step rather than by clicking Next
        page.wait_for_selector("#ed-tour:not([hidden])")
        assert "Step 1 of 4" in page.text_content("#ed-tour")
        drop_card(page, "cond", 700, 400)
        page.wait_for_function(
            "() => document.getElementById('ed-tour')"
            ".textContent.includes('Step 2 of 4')")
        page.keyboard.press("Escape")   # closes the new path's card
        page.click('#ed-tour button[data-tour="end"]')
        page.wait_for_selector("#ed-tour", state="hidden")
        names = page.evaluate("JSON.parse(localStorage.getItem("
                              "'thermodraw:index')).map(f => f.name)")
        assert "Tour" not in names, "a skipped tour leaves nothing behind"

        # quick add: tap empty space, type, Enter
        page.mouse.click(700, 400)
        page.fill("#ed-quick-input", "fixed")
        page.wait_for_selector("#ed-quick-list li")
        page.keyboard.press("Enter")
        page.wait_for_selector("#ed-popover:not([hidden])")
        page.fill('#ed-popover input[data-field="label"]', "Ambient")
        page.fill('#ed-popover input[data-field="value"]', "25")
        page.keyboard.press("Escape")

        # the palette: drag a free node onto the drawing
        drop_card(page, "free", 900, 400)
        page.wait_for_selector("#ed-popover:not([hidden])")
        # the card belongs beside what it edits. It opens before the hit
        # rectangles exist, so it used to sit in the corner for good.
        settled(page, "node", 1)
        pop = page.locator("#ed-popover").bounding_box()
        assert abs(pop["x"] - 900) < 400 and abs(pop["y"] - 400) < 400, pop
        page.fill('#ed-popover input[data-field="label"]', "Junction")
        page.fill('#ed-popover input[data-field="value"]', "80")
        page.keyboard.press("Escape")

        settled(page, "node", 1)
        d = stored(page)
        assert [n.get("kind", "free") for n in d["nodes"]] == ["fixed", "free"]
        assert all(v % 10 == 0 for n in d["nodes"] for v in n["at"])
        assert d["nodes"][0]["label"] == "Ambient"

        # connect: double-click the free node, then click the fixed one
        free_at, fixed_at = d["nodes"][1]["at"], d["nodes"][0]["at"]
        fx, fy = canvas_point(page, *free_at)
        page.mouse.dblclick(fx, fy)
        page.wait_for_selector("#ed-mode:not([hidden])")
        assert "Connecting from" in page.text_content("#ed-mode")
        tx, ty = canvas_point(page, *fixed_at)
        page.mouse.move(tx, ty, steps=6)
        assert page.locator("#ed-ui .ed-rubber").count() == 1
        page.mouse.click(tx, ty)
        page.wait_for_selector("#ed-mode", state="hidden")
        page.wait_for_selector("#ed-popover:not([hidden])")
        page.fill('#ed-popover input[data-field="value"]', "0.5")
        page.keyboard.press("Escape")
        settled(page, "branch", 0)
        d = stored(page)
        assert len(d["branches"]) == 1
        assert {d["branches"][0]["from"], d["branches"][0]["to"]} == {
            d["nodes"][0]["id"], d["nodes"][1]["id"]}
        assert d["branches"][0]["value"] == "0.5"

        # drag the free node down; it lands on the grid and only it moves
        settled(page, "node", 1)
        free_at, fixed_at = d["nodes"][1]["at"], d["nodes"][0]["at"]
        fx, fy = canvas_point(page, *free_at)
        page.mouse.move(fx, fy)
        page.mouse.down()
        page.mouse.move(fx, fy + 90, steps=6)
        page.mouse.up()
        settled(page)
        d2 = stored(page)
        assert d2["nodes"][1]["at"][1] > free_at[1]
        assert d2["nodes"][1]["at"][1] % 10 == 0
        assert d2["nodes"][0]["at"] == fixed_at

        # A path dragged off its run takes the run with it. `at` alone is
        # used by the library exactly as written, so the wire used to jog
        # out to meet the box and the checker said so.
        settled(page, "branch", 0)
        d = stored(page)
        sx, sy = canvas_point(page, *[(a + b) / 2 for a, b in
                                      zip(d["nodes"][0]["at"], d["nodes"][1]["at"])])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx, sy - 170, steps=8)
        page.mouse.up()
        settled(page)
        b = stored(page)["branches"][0]
        assert len(b.get("via", [])) == 2, b
        assert b["at"] == [(b["via"][0][i] + b["via"][1][i]) / 2 for i in (0, 1)]
        assert "symbol-off-its-run" not in codes(page), codes(page)

        # and dragged back onto it, the run straightens again
        bx, by = canvas_point(page, *b["at"])
        page.mouse.move(bx, by)
        page.mouse.down()
        page.mouse.move(sx, sy, steps=8)
        page.mouse.up()
        settled(page)
        b = stored(page)["branches"][0]
        assert "via" not in b, b
        assert "symbol-off-its-run" not in codes(page), codes(page)

        # Delete removes what is selected. It used to reach an input the
        # card had put the cursor in, and do nothing at all.
        page.mouse.click(*canvas_point(page, *b["at"]))
        settled(page)
        page.keyboard.press("Delete")
        settled(page)
        assert stored(page)["branches"] == []
        page.keyboard.press("Control+z")
        settled(page, "branch", 0)
        assert len(stored(page)["branches"]) == 1

        # One drop makes a whole path: two places with the box between
        # them, laid along the run. A path card used to make nothing at all
        # — it turned the drag into a mode and threw the drop point away.
        was = len(stored(page)["nodes"])
        drop_card(page, "rad", 520, 640)
        page.wait_for_selector("#ed-popover:not([hidden])")
        settled(page)

        # The card a drop opens parks the caret in the label box, and the
        # turn keys reach the drawing from there: the moment a component
        # most wants turning is the moment it has just landed lying flat.
        # `]` used to put a `]` in the label and turn nothing at all, and
        # this test never saw it because it dismissed the card first.
        lying = [n["at"] for n in stored(page)["nodes"][-2:]]
        page.keyboard.press("]")
        settled(page)
        upright = [n["at"] for n in stored(page)["nodes"][-2:]]
        assert upright[0][0] == upright[1][0], upright
        assert page.input_value('#ed-popover input[data-field="label"]') == ""
        page.keyboard.press("[")
        settled(page)
        assert [n["at"] for n in stored(page)["nodes"][-2:]] == lying

        # and the caret survives the turn, so a name being typed is not the
        # price of squaring the thing being named
        page.keyboard.type("Sky")
        page.keyboard.press("]")
        settled(page)
        page.keyboard.type("view")
        settled(page)
        assert stored(page)["branches"][-1]["label"] == "Skyview"
        page.keyboard.press("[")
        settled(page)
        page.keyboard.press("Escape")
        settled(page)
        d = stored(page)
        assert len(d["nodes"]) == was + 2, d["nodes"]
        assert d["branches"][-1]["kind"] == "rad"
        a, c = [n["at"] for n in d["nodes"][-2:]]
        assert a[1] == c[1] and c[0] > a[0], (a, c)

        # both its ends join nothing, and both say so. The named nodes of
        # the drawing it landed beside are nobody's loose end.
        assert sorted(x[2] for x in loose(page)) == sorted(
            n["id"] for n in d["nodes"][-2:]), loose(page)

        # `]` turns the component. A path loose at both ends swings its whole
        # run, which is what standing a dropped path upright means; writing
        # an angle onto the box would leave the wire lying where it was.
        page.mouse.click(*canvas_point(
            page, *[(a[i] + c[i]) / 2 for i in (0, 1)]))
        settled(page)
        page.keyboard.press("]")
        settled(page)
        turned = [n["at"] for n in stored(page)["nodes"][-2:]]
        assert turned[0][0] == turned[1][0], turned
        page.keyboard.press("[")
        settled(page)
        assert [n["at"] for n in stored(page)["nodes"][-2:]] == [a, c]

        # A red dot let go over empty space does nothing whatever: no
        # half-made state, no mode left armed.
        before = json.dumps(stored(page))
        x, y, _ = loose(page)[0]
        sx, sy = canvas_point(page, x, y)
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(sx, sy + 280, steps=8)
        page.mouse.up()
        settled(page)
        assert json.dumps(stored(page)) == before

        # Dropped on a node, the loose place becomes that place: the branch
        # is rewired and the spare node goes.
        d = stored(page)
        target = d["nodes"][0]
        x, y, went = loose(page)[0]
        sx, sy = canvas_point(page, x, y)
        tx, ty = canvas_point(page, *target["at"])
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(tx, ty, steps=10)
        page.mouse.up()
        settled(page)
        d2 = stored(page)
        assert len(d2["nodes"]) == len(d["nodes"]) - 1
        assert not any(n["id"] == went for n in d2["nodes"])
        assert target["id"] in (d2["branches"][-1]["from"],
                                d2["branches"][-1]["to"]), d2["branches"][-1]

        # A node dropped near another's line takes that line exactly. Two
        # nodes placed by eye differ by a few units, `_layout` reads a
        # branch's angle off its endpoints, and the wire came out at 6.58
        # degrees with nothing in the checker to say so.
        line = d2["nodes"][0]["at"][1]
        drop_card(page, "free", 1000, canvas_point(page, 0, line)[1] + 8)
        page.wait_for_selector("#ed-popover:not([hidden])")
        page.keyboard.press("Escape")
        settled(page)
        assert stored(page)["nodes"][-1]["at"][1] == line

        # the findings strip reports what the checker says, in its words
        summary = page.text_content("#ed-findings-count")
        assert "labels placed" in summary or "label placed" in summary
        assert "1 labels" not in summary

        # every component is reachable without scrolling the palette
        over = page.evaluate("() => { const p = document.getElementById("
                             "'ed-palette'); return p.scrollHeight - p.clientHeight; }")
        assert over <= 0, f"the palette overflows by {over}px"

        # renaming happens in the page, not in a browser dialog
        page.click("#ed-file")
        page.wait_for_selector('#ed-popover input[data-rn="name"]')
        page.fill('#ed-popover input[data-rn="name"]', "Die to air")
        page.check('#ed-popover input[data-rn="drawn"]')
        page.click('#ed-popover button[data-rn="ok"]')
        settled(page)
        assert page.text_content("#ed-file") == "Die to air"
        assert stored(page)["title"] == "Die to air"
        assert "Die to air" in page.title()
        assert dialogs == [], "renaming opened a browser dialog"

        # the files panel lists the file, and the help panel opens
        assert page.locator("#ed-files li.ed-current").count() == 1
        page.click("#ed-help")
        assert page.is_visible("#ed-help-panel")
        page.keyboard.press("Escape")
        assert not page.is_visible("#ed-help-panel")

        # a phone gets one row of chrome, not four
        page.set_viewport_size({"width": 375, "height": 812})
        page.wait_for_timeout(200)
        bar = page.locator("#ed-top").bounding_box()
        assert bar["height"] < 60, bar
        page.set_viewport_size({"width": 1280, "height": 800})
        page.wait_for_timeout(200)

        # export is the library's own SVG, with both labels in it
        with page.expect_download() as dl:
            page.click("#ed-export")
            page.click('#ed-menu button[data-x="svg-light"]')
        svg = pathlib.Path(dl.value.path()).read_text(encoding="utf-8")
        assert svg.startswith("<?xml") or svg.startswith("<svg")
        assert "Ambient" in svg and "Junction" in svg
        assert "var(--" not in svg, "light export is baked"

        # a share link carries the diagram to a second page, as it stands
        d2 = stored(page)
        page.click("#ed-share")
        page.wait_for_timeout(500)
        link = page.evaluate("navigator.clipboard.readText()")
        assert "#d=" in link or "#j=" in link
        other = context.new_page()
        other.goto(link)
        other.wait_for_selector("#ed-loading", state="hidden", timeout=180_000)
        other.wait_for_timeout(500)
        shared = stored(other)
        assert shared["nodes"] == d2["nodes"]
        assert shared["branches"] == d2["branches"]

        assert errors == [], errors
        browser.close()
