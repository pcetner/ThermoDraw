"""The editor, driven: the built site in headless Chromium.

Skipped unless Playwright is importable. CI's `editor` job installs it and
runs this file alone; the bridge and the site have their own tests in the
ordinary suite. One test, a handful of assertions, one browser: it proves
the page boots the library, that the two ways of adding a symbol and the
handle that connects two nodes write the file the schema describes, that a
drag lands on the grid, that an export is the library's SVG, and that a
share link round-trips.
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
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(served)
        # the library boots in a worker; a cold CDN fetch can take a while
        page.wait_for_selector("#ed-loading", state="hidden", timeout=180_000)

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
        card = page.locator('.ed-card[data-key="free"]')
        box = card.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(900, 400, steps=8)
        page.mouse.up()
        page.wait_for_selector("#ed-popover:not([hidden])")
        page.fill('#ed-popover input[data-field="label"]', "Junction")
        page.fill('#ed-popover input[data-field="value"]', "80")
        page.keyboard.press("Escape")

        settled(page, "node", 1)
        d = stored(page)
        assert [n.get("kind", "free") for n in d["nodes"]] == ["fixed", "free"]
        assert all(v % 10 == 0 for n in d["nodes"] for v in n["at"])
        assert d["nodes"][0]["label"] == "Ambient"

        # connect: select the free node, drag its handle onto the fixed one
        free_at, fixed_at = d["nodes"][1]["at"], d["nodes"][0]["at"]
        fx, fy = canvas_point(page, *free_at)
        page.mouse.click(fx, fy)
        settled(page)
        page.wait_for_selector("#ed-ui .ed-handle")
        handle = page.locator("#ed-ui .ed-handle").bounding_box()
        page.mouse.move(handle["x"] + handle["width"] / 2,
                        handle["y"] + handle["height"] / 2)
        page.mouse.down()
        tx, ty = canvas_point(page, *fixed_at)
        page.mouse.move(tx, ty, steps=10)
        page.mouse.up()
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
        page.mouse.move(fx, fy)
        page.mouse.down()
        page.mouse.move(fx, fy + 90, steps=6)
        page.mouse.up()
        settled(page)
        d2 = stored(page)
        assert d2["nodes"][1]["at"][1] > free_at[1]
        assert d2["nodes"][1]["at"][1] % 10 == 0
        assert d2["nodes"][0]["at"] == fixed_at

        # the findings strip reports what the checker says, in its words
        summary = page.text_content("#ed-findings-count")
        assert "labels placed" in summary

        # export is the library's own SVG, with both labels in it
        with page.expect_download() as dl:
            page.click("#ed-export")
            page.click('#ed-menu button[data-x="svg-light"]')
        svg = pathlib.Path(dl.value.path()).read_text(encoding="utf-8")
        assert svg.startswith("<?xml") or svg.startswith("<svg")
        assert "Ambient" in svg and "Junction" in svg
        assert "var(--" not in svg, "light export is baked"

        # a share link carries the diagram to a second page
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
