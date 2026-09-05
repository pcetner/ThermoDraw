"""Assemble the site GitHub Pages serves, from what the repository already has.

    python tools/build_site.py OUT_DIR

Nothing here is written for the site alone. The dictionary and the symbol
reference are the two generated pages, copied. The hero and every gallery
diagram are `Diagram.page`, the library's own interactive page, on the
committed JSON. The one hand-written file is `docs/site.template.html`, the
index, which links the rest. No dependency beyond the library, no markdown
rendering: the briefs, the findings and the schema are read on GitHub.

`paths()` says what the site contains without building it, so a README link
into the site can be checked against the list, and `build` refuses to finish
if it wrote anything else.
"""
import argparse
import html
import pathlib
import shutil
import sys
from typing import List, NamedTuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thermodraw import Diagram, __version__  # noqa: E402

SITE = "https://pcetner.github.io/ThermoDraw/"
GALLERY = ROOT / "examples" / "gallery"
TEMPLATE = ROOT / "docs" / "site.template.html"

# The gallery, grouped as examples/gallery/README.md groups it: by run.
RUNS = [
    (range(1, 6), "Run 2, 2026-09-01",
     "Five agents in a clean room outside the checkout, from the schema and "
     "a brief, one commit each, transcripts committed. Their numbers do not "
     "close under <code>--physics</code>, and every agent said so."),
    (range(6, 11), "Run 3, 2026-09-02",
     "Five briefs whose numbers were solved as networks before the prose "
     "was written, in a room built by <code>tools/clean_room.py</code>. "
     "No diagram reports a balance finding."),
    (range(11, 16), "Run 4, 2026-09-03",
     "Run 3's briefs again with <code>at</code> forbidden. Four chains were "
     "placed by the solver with no coordinate in the file; the fifth is a "
     "star, was refused by name, and was placed by hand."),
]


class Entry(NamedTuple):
    name: str          # "12-furnace"
    number: int        # 12
    title: str         # the brief's first heading
    json: pathlib.Path


def entries() -> List[Entry]:
    out = []
    for d in sorted(GALLERY.iterdir()):
        if not d.is_dir() or not d.name[:2].isdigit():
            continue
        (source,) = d.glob("*.json")
        first = (d / "brief.md").read_text(encoding="utf-8").splitlines()[0]
        out.append(Entry(d.name, int(d.name[:2]), first.lstrip("# ").strip(),
                         source))
    return out


def paths() -> List[str]:
    """Every file the site holds, relative to its root, in order."""
    fixed = ["index.html", "dictionary.html", "symbol-reference.html",
             "raptor.html", "raptor.svg", "gallery/index.html", ".nojekyll"]
    per = [f"gallery/{e.name}.{ext}" for e in entries()
           for ext in ("html", "svg")]
    return fixed + per


def _gallery_index(items: List[Entry], prefix: str = "") -> str:
    """The cards, grouped by run. `prefix` is where the gallery sits
    relative to the page holding the cards: `gallery/` from the front
    page, nothing from the gallery's own index."""
    sections = []
    for numbers, heading, blurb in RUNS:
        cards = "".join(
            f'<li><a href="{prefix}{e.name}.html">'
            f'<img src="{prefix}{e.name}.svg" alt="{html.escape(e.title)}" '
            'loading="lazy">'
            f'<span><b>{e.number:02d}</b> {html.escape(e.title)}</span></a></li>'
            for e in items if e.number in numbers)
        sections.append(f"<section><h2>{heading}</h2><p>{blurb}</p>"
                        f'<ul class="gallery">{cards}</ul></section>')
    return "".join(sections)


def _page(diagram_json: pathlib.Path, title: str) -> str:
    """The library's page; an empty title lets the diagram's own stand."""
    d = Diagram.from_json(diagram_json.read_text(encoding="utf-8"))
    return d.page(title=title or None)


def _svg(diagram_json: pathlib.Path) -> str:
    d = Diagram.from_json(diagram_json.read_text(encoding="utf-8"))
    return d.svg()


def _write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build(out: pathlib.Path) -> List[str]:
    """Write the site into `out` and return what was written."""
    items = entries()
    out = pathlib.Path(out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    template = TEMPLATE.read_text(encoding="utf-8")
    index = (template.replace("{{VERSION}}", __version__)
                     .replace("{{GALLERY}}",
                              _gallery_index(items, "gallery/")))
    assert "{{" not in index, "unfilled placeholder in the site template"
    _write(out / "index.html", index)

    shutil.copyfile(ROOT / "Dictionary.html", out / "dictionary.html")
    shutil.copyfile(ROOT / "docs" / "symbol-reference.html",
                    out / "symbol-reference.html")

    raptor = ROOT / "examples" / "raptor.json"
    _write(out / "raptor.html", _page(raptor, ""))
    _write(out / "raptor.svg", _svg(raptor))

    gallery = template_gallery(items)
    _write(out / "gallery" / "index.html", gallery)
    for e in items:
        _write(out / "gallery" / f"{e.name}.html", _page(e.json, e.title))
        _write(out / "gallery" / f"{e.name}.svg", _svg(e.json))
    _write(out / ".nojekyll", "")

    written = sorted(str(p.relative_to(out)).replace("\\", "/")
                     for p in out.rglob("*") if p.is_file())
    assert written == sorted(paths()), (
        set(written) ^ set(paths()))
    return written


def template_gallery(items: List[Entry]) -> str:
    """The gallery index: the same shell as the front page, its own body."""
    template = TEMPLATE.read_text(encoding="utf-8")
    head, _, _ = template.partition("<main>")
    head = head.replace("{{VERSION}}", __version__)
    head = head.replace("<title>ThermoDraw", "<title>Gallery · ThermoDraw")
    head = head.replace('href="raptor.svg"', 'href="../raptor.svg"')
    return (head + "<main>"
            '<p class="crumb"><a href="../">ThermoDraw</a> / gallery</p>'
            "<h1>The gallery</h1>"
            "<p>Fifteen thermal networks from ten engineering domains, each "
            "drawn by an agent that had never seen this library, from "
            "<code>docs/schema.md</code> and a brief. Every one was made to "
            "pass <code>thermodraw check</code>; what that cost is in each "
            "folder's <code>rounds.md</code> and <code>findings.md</code> "
            '<a href="https://github.com/pcetner/ThermoDraw/tree/main/'
            'examples/gallery">on GitHub</a>. Click a diagram for the '
            "library's own page of it.</p>"
            + _gallery_index(items) +
            "</main></body></html>\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=pathlib.Path)
    args = ap.parse_args(argv)
    written = build(args.out)
    print(f"{len(written)} files -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
