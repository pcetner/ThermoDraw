"""Every scene the golden tests cover.

The three demo scenes are the most complex compositions the library has, and
they are the ones that exposed the label and sizing problems, so they earn a
place in the suite. They live in examples/, which is not part of the
installed package — if it is not on the path the suite still runs, with the
library's own scenes and without them.
"""
import pathlib

from thermodraw import symbols


def _strip(sym):
    return lambda: symbols.strip(sym)


SCENES = {f"symbol-{s.key}": _strip(s) for s in symbols.SYMBOLS}
SCENES["region-grid"] = symbols.region_grid
SCENES["diagonal-demo"] = symbols.diagonal_demo

# From a checkout the demo scenes must be here. If the file exists and the
# import still failed, that is an error and not a reason to go quiet: a bare
# try/except used to drop the three most complex scenes in the suite silently,
# all green, and the skip marker written to guard against it was never used.
_DEMO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "render_demo.py"
try:
    import render_demo
except ImportError:
    if _DEMO.exists():
        raise
    HAVE_DEMO = False                                # an installed package
else:
    HAVE_DEMO = True
    SCENES.update({f"demo-{name}": fn
                   for name, fn in render_demo.SCENES.items()})
