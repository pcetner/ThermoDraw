"""Every scene the golden tests cover.

The three demo scenes are the most complex compositions the library has, and
they are the ones that exposed the label and sizing problems, so they earn a
place in the suite. They live in examples/, which is not part of the
installed package — if it is not on the path the suite still runs, with the
library's own scenes and without them.
"""
import pytest

from thermodraw import symbols


def _strip(sym):
    return lambda: symbols.strip(sym)


SCENES = {f"symbol-{s.key}": _strip(s) for s in symbols.SYMBOLS}
SCENES["region-grid"] = symbols.region_grid
SCENES["diagonal-demo"] = symbols.diagonal_demo

try:
    import render_demo
except ImportError:                                  # examples/ not on path
    HAVE_DEMO = False
else:
    HAVE_DEMO = True
    SCENES.update({f"demo-{name}": fn
                   for name, fn in render_demo.SCENES.items()})

needs_examples = pytest.mark.skipif(
    not HAVE_DEMO, reason="examples/ is not on the path")
