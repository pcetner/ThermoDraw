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


def _wall_scene(kind, wall):
    """A boundary with its wall turned, and a branch arriving from the far
    side — the arrangement `wall` exists for. Through the pipeline, because
    a wall's direction is a layout fact and the symbol sheets do not have it.
    `down` is the drawing every diagram before 1.0 had and needs no scene.

    The upward scenes put the label to the right: on a vertical run a break
    node's label has the wire on one side and the wall on the other, and
    the solver pushes it up the wire into a collision. That is true of a
    strut arriving from above onto a wall that faces down too, and it is
    what `side` is for; a golden is a drawing, not a finding."""
    def scene():
        from thermodraw import Diagram, layout, render
        far = {"up": (300, 220), "left": (520, 0), "right": (80, 0)}[wall]
        return render(layout(Diagram.from_dict({
            "units": {"R": "K/W", "T": "K"},
            "nodes": [{"id": "a", "label": "Cold mass", "value": "4",
                       "sub": "m", "at": list(far)},
                      {"id": "b", "kind": kind, "label": "Mount",
                       "value": "300", "sub": "b", "at": [300, 0],
                       "wall": wall,
                       "side": "right" if wall == "up" else "auto"}],
            "branches": [{"from": "a", "to": "b", "kind": "cond",
                          "label": "Strut", "value": "50"}]})))
    return scene


for _kind in ("fixed", "break"):
    for _facing in ("up", "left", "right"):
        SCENES[f"wall-{_kind}-{_facing}"] = _wall_scene(_kind, _facing)


def _solved_hero():
    """The hero with every coordinate removed and solved. Pins the solver's
    geometry — its pitch, its pair routing, where it puts a source — the
    way the other goldens pin the label solver's."""
    import json
    from thermodraw import Diagram, layout, render
    data = json.loads(_HERO.read_text(encoding="utf-8"))
    for n in data["nodes"]:
        n.pop("at", None)
    for b in data["branches"]:
        b.pop("at", None)
        b.pop("via", None)
    for s in data["sources"]:
        s.pop("at", None)
    return render(layout(Diagram.from_dict(data)))


def _zigzag_hero():
    """The hero in circuit notation: the option's one golden, so the zigzag
    glyph and the unchanged geometry around it are both pinned."""
    from thermodraw import Diagram, layout, render
    d = Diagram.from_json(_HERO.read_text(encoding="utf-8"))
    return render(layout(d), notation="zigzags")


_HERO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "hero.json"
if _HERO.exists():
    SCENES["solved-hero"] = _solved_hero
    SCENES["zigzag-hero"] = _zigzag_hero

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
