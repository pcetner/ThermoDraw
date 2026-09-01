"""Every scene the golden tests cover.

The three demo scenes are the most complex compositions the library has, and
they are the ones that exposed the label and sizing problems, so they earn a
place in the suite even though they live in examples/.
"""
import render_demo
from thermodraw import symbols


def _strip(sym):
    return lambda: symbols.strip(sym)


SCENES = {f"symbol-{s.key}": _strip(s) for s in symbols.SYMBOLS}
SCENES["region-grid"] = symbols.region_grid
SCENES["diagonal-demo"] = symbols.diagonal_demo
SCENES.update({f"demo-{name}": fn for name, fn in render_demo.SCENES.items()})
