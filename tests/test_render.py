"""Properties the render must hold whatever the symbols look like."""
import re
import xml.etree.ElementTree as ET

import pytest

from scenes import SCENES
from thermodraw import DiagramBuilder, core, save, symbols, theme


@pytest.mark.parametrize("name", sorted(SCENES))
def test_every_scene_is_well_formed_xml(name):
    """Word, cairosvg and librsvg are conforming XML parsers. A document one
    of them refuses is not an SVG, however it looks in a browser."""
    ET.fromstring(SCENES[name]())


HOSTILE = 'Fins & fans <b>12" wide</b> </svg><script>alert(1)</script>'


def _hostile():
    return (DiagramBuilder(R="K/W", T="°C")
            .node("a", HOSTILE, 20, at=(100, 100), sub="a&b")
            .node("b", "Case", 80, at=(400, 100), sub="b")
            .branch("a", "b", "cond", HOSTILE, "0.35"))


class TestALabelIsTextNotMarkup:
    """The premise is that a model writes the diagram. Whatever it writes
    into a label reaches the document as character data, never as markup —
    an `&` is ordinary in a thermal label, and it used to produce a file no
    conforming parser would open."""

    def test_a_hostile_label_still_makes_a_well_formed_document(self):
        ET.fromstring(_hostile().svg("light"))

    def test_the_text_arrives_escaped_and_the_markup_intact(self):
        svg = _hostile().svg("light")
        assert "<script" not in svg
        assert "&lt;script&gt;" in svg
        assert "Fins &amp; fans" in svg
        assert "12&quot; wide" in svg
        # the subscript is escaped inside the library's own tspan...
        assert ">a&amp;b</tspan>" in svg
        # ...and that tspan is the markup a label legitimately carries
        assert svg.count("<tspan") == svg.count("</tspan>") > 0

    def test_what_is_measured_is_what_is_drawn(self):
        """An escaped `&` is one glyph on the page, so it is one glyph to the
        solver — not five characters, and not a double prime."""
        assert core.text_w("&amp;", 13) == core.text_w("&", 13)
        assert core.text_w("&lt;b&gt;", 13) == core.text_w("<b>", 13)


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


class TestBakeTouchesOnlyTheStylesheet:
    def test_a_label_that_reads_like_a_variable_is_left_alone(self):
        """`bake` used to substitute over the whole document, so a label
        reading "var(--ink)" came out as a hex triplet."""
        d = (DiagramBuilder(T="°C")
             .node("a", "Sink var(--ink) at 5", 20, at=(0, 0), sub="a"))
        svg = d.svg("light")
        assert "Sink var(--ink) at 5" in svg
        assert "var(--" not in svg.partition("</style>")[0]

    def test_a_variable_the_palette_does_not_know_is_an_error(self):
        """Not `#000`. A renamed key used to come out black-on-black in dark
        mode while the variables path stayed correct."""
        with pytest.raises(ValueError, match=r"var\(--nope\)"):
            theme.bake('<svg><style>.x{fill:var(--nope)}</style></svg>')

    def test_every_variable_the_stylesheet_uses_has_a_colour(self):
        """Also enforced at import, which is what makes a rename fail the
        suite rather than a reader's eyes."""
        used = set(theme._VAR_RE.findall(symbols.CSS))
        for mode, pal in theme.PALETTES.items():
            assert used <= set(pal), mode


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
