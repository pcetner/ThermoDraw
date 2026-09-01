"""The vendored faces, and their relationship to the width table.

Two generated artifacts have to agree: the width table the solver clears
against, and the subset that actually draws the text. Regenerate one without
the other and every clearance is quietly wrong, which is the failure this
whole phase existed to remove.
"""
import pytest

from thermodraw import _metrics, symbols, theme

ttLib = pytest.importorskip("fontTools.ttLib")

FACE_FILE = {f: n for f, n, _, _ in theme.FACE_FILES}


def advances(path):
    font = ttLib.TTFont(path)
    upem = font["head"].unitsPerEm
    cmap, hmtx = font.getBestCmap(), font["hmtx"]
    return {chr(c): hmtx[g][0] / upem
            for c, g in cmap.items() if g in hmtx.metrics}


@pytest.mark.parametrize("face", sorted(FACE_FILE))
def test_embedded_face_matches_the_width_table(face):
    """Every glyph the subset carries must measure what the table claims."""
    real = advances(theme.FONT_DIR / FACE_FILE[face])
    table = _metrics.WIDTHS[face]
    shared = sorted(set(real) & set(table))
    assert len(shared) > 150, "subset lost most of its glyphs"
    for ch in shared:
        assert abs(real[ch] - table[ch]) < 1e-3, (
            f"{face} {ch!r}: font says {real[ch]:.4f}, table says {table[ch]:.4f}")


@pytest.mark.parametrize("face", sorted(FACE_FILE))
def test_reserved_font_name_is_not_used(face):
    """IBM Plex is OFL-1.1 with Reserved Font Name "Plex", and a subset is a
    Modified Version under clause 3."""
    font = ttLib.TTFont(theme.FONT_DIR / FACE_FILE[face])
    names = [str(r) for r in font["name"].names]
    assert not [n for n in names if "Plex" in n], names
    assert font["name"].getDebugName(1) == theme.EMBEDDED


def test_licence_ships_with_the_fonts():
    text = (theme.FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE" in text


def test_only_the_needed_faces_are_embedded():
    """Three faces cost about 79KB, so a diagram should carry what it uses."""
    assert theme.faces_used(symbols.diagonal_demo()) == [
        "regular", "italic", "semibold"]
    no_text = '<svg><style>.a{}</style><rect/></svg>'
    assert theme.faces_used(no_text) == []
    assert "@font-face" not in theme.bake(no_text)


def test_embedding_is_deterministic():
    svg = symbols.diagonal_demo()
    assert theme.bake(svg, "light") == theme.bake(svg, "light")
