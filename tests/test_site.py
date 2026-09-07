"""The site is built from the checkout, and holds what it says it holds.

`tools/build_site.py` is what GitHub Pages serves. It is not committed, so
the only place it can be wrong is here and in the Pages workflow's log; a
gallery page that failed to build would be found by a visitor.
"""
import html
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import build_site  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ROOT / "examples" / "gallery").exists(),
    reason="examples/ is not installed")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    written = build_site.build(out)
    return out, written


def test_it_writes_exactly_what_it_says(site):
    out, written = site
    assert sorted(written) == sorted(build_site.paths())
    for rel in build_site.paths():
        assert (out / rel).is_file(), rel


def test_the_gallery_is_all_fifteen_with_their_titles(site):
    out, _ = site
    items = build_site.entries()
    assert [e.number for e in items] == list(range(1, 16))
    index = (out / "gallery" / "index.html").read_text(encoding="utf-8")
    for e in items:
        assert html.escape(e.title) in index, e.name
        assert f'href="{e.name}.html"' in index
        page = (out / "gallery" / f"{e.name}.html").read_text(encoding="utf-8")
        assert f"<h1>{html.escape(e.title)}</h1>" in page
        assert "<svg" in page


def test_the_copies_are_the_generated_pages(site):
    out, _ = site
    assert ((out / "dictionary.html").read_bytes()
            == (ROOT / "Dictionary.html").read_bytes())
    assert ((out / "symbol-reference.html").read_bytes()
            == (ROOT / "docs" / "symbol-reference.html").read_bytes())


def test_the_index_carries_the_version_and_the_hero(site):
    from thermodraw import __version__
    out, _ = site
    index = (out / "index.html").read_text(encoding="utf-8")
    assert f"Version {__version__}." in index
    assert "{{" not in index
    assert 'src="raptor.svg"' in index and 'href="raptor.html"' in index
    assert "<svg" in (out / "raptor.html").read_text(encoding="utf-8")


def test_every_link_and_image_on_both_indexes_resolves(site):
    """The front page's cards used to point beside itself instead of into
    gallery/, and rendered as fifteen alt texts."""
    import re
    out, _ = site
    for page in ("index.html", "gallery/index.html"):
        text = (out / page).read_text(encoding="utf-8")
        for target in re.findall(r'(?:href|src)="([^"#]+)"', text):
            if target.startswith("http"):
                continue
            path = (out / page).parent / target
            assert path.exists() or (path / "index.html").exists(), (
                f"{page} -> {target}")


def test_the_editor_is_on_the_site_with_its_wheel(site):
    from thermodraw import __version__
    out, _ = site
    wheel = f"thermodraw-{__version__}-py3-none-any.whl"
    assert (out / "editor" / wheel).stat().st_size > 100_000
    page = (out / "editor" / "index.html").read_text(encoding="utf-8")
    assert wheel in page and build_site.PYODIDE in page
    assert "{{" not in page
    assert page.count('class="ed-card"') == 20
    examples = json.loads((out / "editor" / "examples.json").read_text(
        encoding="utf-8"))
    assert len(examples) == 17
    for e in examples:
        target = (out / "editor" / e["path"]).resolve()
        assert target.is_file(), e
        json.loads(target.read_text(encoding="utf-8"))
