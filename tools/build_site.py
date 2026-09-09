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
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import List, NamedTuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thermodraw import Diagram, __version__  # noqa: E402
from thermodraw import _editor  # noqa: E402

SITE = "https://pcetner.github.io/ThermoDraw/"
GALLERY = ROOT / "examples" / "gallery"
TEMPLATE = ROOT / "docs" / "site.template.html"
EDITOR = ROOT / "docs" / "editor"

# The editor runs the library in the page through Pyodide, loaded from
# jsDelivr at this version. Bump deliberately: the spike that chose it is in
# the commit that added the editor, with its timings.
PYODIDE = "314.0.6"
WHEEL = f"thermodraw-{__version__}-py3-none-any.whl"

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


def editor_revision() -> str:
    return hashlib.sha256(b"".join(p.read_bytes() for p in sorted(
        list((ROOT / "src" / "thermodraw").glob("*.py")) + list(EDITOR.glob("*.*"))))).hexdigest()[:16]


def paths() -> List[str]:
    """Every file the site holds, relative to its root, in order."""
    fixed = ["index.html", "site.css", "dictionary.html",
             "symbol-reference.html",
             "raptor.html", "raptor.svg", "raptor.json", "hero.json",
             "gallery/index.html", ".nojekyll",
             "editor/index.html", "editor/editor.css", "editor/editor.js",
             "editor/worker.js", f"editor/{editor_revision()}/{WHEEL}", "editor/examples.json"]
    per = [f"gallery/{e.name}.{ext}" for e in entries()
           for ext in ("html", "svg", "json")]
    return fixed + per + [f"{folder}/{p.name}" for folder in ("homework", "analysis", "features") for p in sorted((ROOT / "examples" / folder).glob("*.json"))]


def examples() -> List[dict]:
    """The four answered HW2 problems, in submission order."""
    return json.loads((EDITOR / "examples.catalog.json").read_text(encoding="utf-8"))


def _palette_markup() -> str:
    """The twenty cards, drawn by the library, grouped as it groups them,
    baked into the page so the palette is there before Python is."""
    out = []
    groups = [("Temperature nodes", ("free", "fixed", "break", "phase")),
              ("Thermal resistances", ("cond", "conv", "rad", "contact", "spread", "pipe", "mixed")),
              ("Other connections", ("cap", "flow-branch", "break-branch", "link", "stream")),
              ("Sources", ("diss", "radin", "flow", "flux"))]
    entries = {e["key"]: e for e in _editor.palette()}
    names = {"pipe": "Heat-pipe resistance", "mixed": "Mixed resistance", "stream": "Mass-flow stream", "flow-branch": "Heat-flow connection", "flow": "Heat-flow source", "break-branch": "Inline thermal break"}
    for heading, keys in groups:
        out.append(f'<section data-component-group data-category="Network"><h3>{heading}</h3><div class="ed-cards">')
        for key in keys:
            e = entries[key]
            svg = re.sub(r'(id="|url\(#)clip-', lambda m: m.group(1) + f'pal-{key}-clip-', e["svg"])
            name = names.get(key, e["name"])
            aliases = "resistor resistance" if key in groups[1][1] else "boundary" if key in ("fixed", "break") else "heat input power" if e["role"] == "source" else ""
            out.append(f'<div class="ed-component-row" data-search="{html.escape(name + " " + key + " " + aliases)}">'
                       f'<button type="button" class="ed-card" data-key="{key}" data-role="{e["role"]}" data-kind="{e["kind"]}" title="{html.escape(e["note"] or name)}">'
                       f'{svg}<span>{html.escape(name)}</span></button>'
                       f'<button type="button" class="ed-component-help" aria-label="About {html.escape(name)}" aria-expanded="false" aria-controls="ed-definition-{key}" data-component-note>?</button><p class="ed-component-definition" id="ed-definition-{key}" hidden>{html.escape(e["note"] or name)}</p></div>')
        out.append('</div></section>')
    for category, entries in [("Physical", [("region", "Region rectangle", "A rectangular material layer or spatial region. It defines geometry, not an energy balance."), ("volume", "Control-volume rectangle", "A region of space chosen for an energy balance. Heat, work and mass can cross its boundary."), ("surface", "Control surface", "A segment of a control-volume boundary through which energy or mass can pass."), ("transfer", "Energy transfer", "Heat, work or energy carried by mass across a control surface. The direction sets whether energy enters or leaves.")]), ("Annotations", [("text", "Text", "A label, assumption or equation placed independently on the drawing."), ("line", "Line", "A line used for dimensions, boundaries or callouts. It creates no thermal connection."), ("arrow", "Arrow", "An arrow used to indicate direction or identify a feature. It contributes no energy to a balance.")])]:
        out.append(f'<section data-component-group data-category="{category}" hidden><h3>{category}</h3><div class="ed-cards">')
        for key, name, note in entries:
            out.append(f'<div class="ed-component-row" data-search="{name.lower()}"><button type="button" class="ed-shape-card" data-sketch="{key}">{name}</button><button type="button" class="ed-component-help" aria-label="About {name}" aria-expanded="false" aria-controls="ed-definition-{key}" data-component-note>?</button><p class="ed-component-definition" id="ed-definition-{key}" hidden>{note}</p></div>')
        out.append('</div></section>')
    return "".join(out)


def _wheel(into: pathlib.Path) -> None:
    """Build the wheel the editor loads, from this checkout."""
    with tempfile.TemporaryDirectory() as tmp:
        # Setuptools writes build/ and egg-info beside its sources. Keep site
        # builds isolated from simultaneous tests and stale build artifacts.
        project = pathlib.Path(tmp) / "project"
        project.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE", "NOTICE"):
            shutil.copyfile(ROOT / name, project / name)
        shutil.copytree(ROOT / "src" / "thermodraw", project / "src" / "thermodraw",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        run = subprocess.run([sys.executable, "-m", "build", "--wheel",
                              "--outdir", tmp, str(project)],
                             capture_output=True, text=True)
        if run.returncode:
            sys.exit("the wheel did not build (is `build` installed? it is "
                     "in the dev extra):\n" + run.stdout + run.stderr)
        built = pathlib.Path(tmp) / WHEEL
        if not built.exists():
            sys.exit(f"build made no {WHEEL} in {tmp}: "
                     f"{sorted(p.name for p in pathlib.Path(tmp).iterdir())}")
        into.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, into)


def _editor_pages(out: pathlib.Path) -> None:
    revision = editor_revision()
    template = (EDITOR / "editor.template.html").read_text(encoding="utf-8")
    page = (template.replace("{{VERSION}}", __version__)
                    .replace("{{REVISION}}", revision)
                    .replace("{{WHEEL}}", f"{revision}/{WHEEL}")
                    .replace("{{PYODIDE}}", PYODIDE)
                    .replace("{{PALETTE}}", _palette_markup()))
    assert "{{" not in page, "unfilled placeholder in the editor template"
    _write(out / "editor" / "index.html", page)
    for name in ("editor.css", "editor.js", "worker.js"):
        shutil.copyfile(EDITOR / name, out / "editor" / name)
    _write(out / "editor" / "examples.json",
           json.dumps(examples(), indent=1, ensure_ascii=False) + "\n")
    _wheel(out / "editor" / revision / WHEEL)


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
    # Empty it rather than remove it: a server may be sitting in it, and
    # on Windows a directory another process holds cannot be deleted.
    if out.exists():
        for child in out.iterdir():
            shutil.rmtree(child) if child.is_dir() else child.unlink()
    out.mkdir(parents=True, exist_ok=True)

    template = TEMPLATE.read_text(encoding="utf-8")
    index = (template.replace("{{VERSION}}", __version__)
                     .replace("{{GALLERY}}",
                              _gallery_index(items, "gallery/")))
    assert "{{" not in index, "unfilled placeholder in the site template"
    _write(out / "index.html", index)

    shutil.copyfile(ROOT / "docs" / "site.css", out / "site.css")
    shutil.copyfile(ROOT / "Dictionary.html", out / "dictionary.html")
    shutil.copyfile(ROOT / "docs" / "symbol-reference.html",
                    out / "symbol-reference.html")

    raptor = ROOT / "examples" / "raptor.json"
    _write(out / "raptor.html", _page(raptor, ""))
    _write(out / "raptor.svg", _svg(raptor))
    shutil.copyfile(raptor, out / "raptor.json")
    shutil.copyfile(ROOT / "examples" / "hero.json", out / "hero.json")

    gallery = template_gallery(items)
    _write(out / "gallery" / "index.html", gallery)
    for e in items:
        _write(out / "gallery" / f"{e.name}.html", _page(e.json, e.title))
        _write(out / "gallery" / f"{e.name}.svg", _svg(e.json))
        shutil.copyfile(e.json, out / "gallery" / f"{e.name}.json")
    _editor_pages(out)
    for p in sorted((ROOT / "examples" / "homework").glob("*.json")):
        (out / "homework").mkdir(exist_ok=True)
        shutil.copyfile(p, out / "homework" / p.name)
    for p in sorted((ROOT / "examples" / "analysis").glob("*.json")):
        (out / "analysis").mkdir(exist_ok=True)
        shutil.copyfile(p, out / "analysis" / p.name)
    for p in sorted((ROOT / "examples" / "features").glob("*.json")):
        (out / "features").mkdir(exist_ok=True)
        shutil.copyfile(p, out / "features" / p.name)
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
    head = head.replace('href="site.css"', 'href="../site.css"')
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
