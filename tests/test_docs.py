"""The reference page must not drift from the library again.

docs/symbol-reference.html is CLAUDE.md's visual specification and had no
generator: 165KB of hand-assembled SVG that could go stale silently, and had
— it was labelled draft 5 against core.py's draft 4.
"""
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_symbol_reference_is_up_to_date():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_docs.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_symbol_appears_on_the_page():
    from thermodraw import symbols
    page = (ROOT / "docs" / "symbol-reference.html").read_text(encoding="utf-8")
    for sym in symbols.SYMBOLS:
        assert f"<h4>{sym.name}</h4>" in page, f"{sym.key} missing"
        assert sym.note in page, f"{sym.key} note missing"


class TestTheDictionary:
    """Dictionary.html is the page for someone who has not drawn one of these
    before: every symbol, what it means, and when to reach for it.

    Same guarantee as the reference sheet, for the same reason. The prose is
    written by hand and the pictures are not, so what has to be pinned is that
    the two describe the same eighteen symbols.
    """

    def test_the_page_is_up_to_date(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_dictionary.py"),
             "--check"], capture_output=True, text=True, cwd=ROOT)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_every_symbol_has_a_meaning_and_a_scenario(self):
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        for sym in symbols.SYMBOLS:
            spec = gen_dictionary.ENTRIES.get(sym.key)
            assert spec is not None, f"{sym.key} has no entry"
            assert spec["use"], f"{sym.key} has no scenario"

    def test_a_new_symbol_stops_the_build(self):
        """The one check that matters: adding a glyph must not quietly ship a
        dictionary that does not mention it."""
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        extra = symbols.Symbol(key="unwritten", name="Unwritten",
                               draw=lambda a: "", half=5, half_len=5)
        original = symbols.SYMBOLS
        symbols.SYMBOLS = original + [extra]
        try:
            with pytest.raises(SystemExit) as exc:
                gen_dictionary.build()
            assert "unwritten" in str(exc.value)
        finally:
            symbols.SYMBOLS = original

    def test_every_symbol_is_drawn_on_it(self):
        from thermodraw import symbols
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        for sym in symbols.SYMBOLS:
            assert f"<h3>{sym.name}</h3>" in page, f"{sym.key} missing"
        # `corner` draws nothing and so has no Symbol at all. It is still a
        # node kind, and a reader who cannot find it here will assume it is
        # not one — which is what two acceptance readers did.
        assert "<h3>Corner</h3>" in page

    def test_a_card_is_one_glyph_at_one_scale(self):
        """Cards share a width, so they share a scale. Heights differ, which
        is what keeps a free node out of a thermal break's empty frame."""
        from thermodraw import symbols
        widths = {re.search(r'viewBox="0 0 ([\d.]+)', symbols.card(s)).group(1)
                  for s in symbols.SYMBOLS}
        assert widths == {str(symbols.DW)}
        heights = {re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)',
                             symbols.card(s)).group(1)
                   for s in symbols.SYMBOLS}
        assert len(heights) > 1

    def test_a_card_draws_the_symbol_inside_its_own_frame(self):
        """The frame is solved from the ink and the label, so nothing it
        shows may fall outside it — a clipped glyph on a page whose whole job
        is showing glyphs."""
        from thermodraw import core as S, symbols
        for sym in symbols.SYMBOLS:
            svg = symbols.card(sym)
            h = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)', svg).group(1))
            body = []
            _, top, _, bh = S.annotate(symbols.DCX, 0.0, 0, body,
                                       user=sym.user, name=sym.text,
                                       value=sym.value, half=sym.half,
                                       half_len=sym.half_len)
            cy = symbols.DPAD - min(-sym.ink[1], top)
            assert cy - sym.ink[1] >= -0.01, f"{sym.key} ink above the frame"
            assert cy + sym.ink[1] <= h + 0.01, f"{sym.key} ink below it"
            assert cy + top >= -0.01, f"{sym.key} label above the frame"
            assert cy + top + bh <= h + 0.01, f"{sym.key} label below it"
