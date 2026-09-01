"""Properties the render must hold whatever the symbols look like."""
import re

import pytest

from scenes import SCENES
from thermodraw import save, symbols, theme


@pytest.mark.parametrize("name", sorted(SCENES))
def test_render_is_deterministic(name):
    """Same input, same bytes — including across other renders in between."""
    first = SCENES[name]()
    symbols.diagonal_demo()
    assert SCENES[name]() == first


@pytest.mark.parametrize("name", sorted(SCENES))
def test_element_ids_are_unique(name):
    ids = re.findall(r'\sid="([^"]+)"', SCENES[name]())
    assert len(ids) == len(set(ids)), "duplicate id in one document"


@pytest.mark.parametrize("sym", symbols.SYMBOLS, ids=lambda s: s.key)
def test_save_round_trips_non_ascii(sym, tmp_path):
    """conv, rad and flux emit → and ″, which crash a default-encoding write."""
    svg = theme.bake(symbols.strip(sym), "light")
    path = save(svg, tmp_path / f"{sym.key}.svg")
    assert path.read_text(encoding="utf-8").endswith(svg)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_bake_leaves_no_custom_properties(mode):
    """Word, PowerPoint and cairosvg all ignore var(); cairosvg throws."""
    assert "var(--" not in theme.bake(symbols.diagonal_demo(), mode)


def test_save_only_declares_xml_on_svg(tmp_path):
    """save() is the library's one file writer, so it gets used for JSON too.

    It used to prepend an XML declaration to anything, which turned a written
    diagram-as-data file into invalid JSON.
    """
    import json

    svg = save(symbols.diagonal_demo(), tmp_path / "d.svg")
    assert svg.read_text(encoding="utf-8").startswith("<?xml")

    data = save('{"nodes": []}', tmp_path / "d.json")
    assert json.loads(data.read_text(encoding="utf-8")) == {"nodes": []}

    plain = save("just words", tmp_path / "d.txt")
    assert plain.read_text(encoding="utf-8") == "just words"


def test_save_writes_lf_not_crlf(tmp_path):
    path = save("a\nb", tmp_path / "d.txt")
    assert path.read_bytes() == b"a\nb"
