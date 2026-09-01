"""Render every symbol at every 45°, plus the worked example.

    python examples/render_reference.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from thermodraw import symbols, theme  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "build"


def main():
    OUT.mkdir(exist_ok=True)
    for sym in symbols.SYMBOLS:
        svg = symbols.strip(sym)
        (OUT / f"{sym['key']}.svg").write_text(theme.with_variables(svg))
    for mode in ("light", "dark"):
        (OUT / f"example-{mode}.svg").write_text(
            theme.bake(symbols.diagonal_demo(), mode))
    print(f"wrote {len(symbols.SYMBOLS) + 2} files to {OUT}")


if __name__ == "__main__":
    main()
