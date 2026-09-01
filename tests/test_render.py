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


@pytest.mark.parametrize("sym", symbols.SYMBOLS, ids=lambda s: s["key"])
def test_save_round_trips_non_ascii(sym, tmp_path):
    """conv, rad and flux emit → and ″, which crash a default-encoding write."""
    svg = theme.bake(symbols.strip(sym), "light")
    path = save(svg, tmp_path / f"{sym['key']}.svg")
    assert path.read_text(encoding="utf-8").endswith(svg)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_bake_leaves_no_custom_properties(mode):
    """Word, PowerPoint and cairosvg all ignore var(); cairosvg throws."""
    assert "var(--" not in theme.bake(symbols.diagonal_demo(), mode)
