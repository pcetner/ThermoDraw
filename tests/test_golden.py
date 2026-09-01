"""Golden-file comparison.

The symbols are settled, so these are not here to catch a bad glyph. They are
here because the label solver's output moves whenever a metric or a constant
changes, and without a golden there is no way to see what moved.
"""
import pathlib

import pytest

from scenes import SCENES

GOLDEN = pathlib.Path(__file__).parent / "golden"


@pytest.mark.parametrize("name", sorted(SCENES))
def test_matches_golden(name, request):
    svg = SCENES[name]()
    path = GOLDEN / f"{name}.svg"

    if request.config.getoption("--update-goldens"):
        GOLDEN.mkdir(exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        pytest.skip(f"updated {path.name}")

    assert path.exists(), f"no golden for {name}; run pytest --update-goldens"
    assert svg == path.read_text(encoding="utf-8"), (
        f"{name} changed. Review the diff, then run pytest --update-goldens.")
