"""The reference page must not drift from the library again.

docs/symbol-reference.html is CLAUDE.md's visual specification and had no
generator: 165KB of hand-assembled SVG that could go stale silently, and had
— it was labelled draft 5 against core.py's draft 4.
"""
import pathlib
import subprocess
import sys

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
