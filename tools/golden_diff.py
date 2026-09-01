"""What actually changed in the goldens, element by element.

    python tools/golden_diff.py [scene ...] [--verbose]

A golden is one long line of SVG, so `git diff` marks the whole file changed
whether a constant moved by 17 units or every symbol moved by 200. That makes
`pytest --update-goldens` a rubber stamp: the diff is unreadable, so nobody
reads it, so the goldens stop being a review and become a record of whatever
happened.

This splits both sides into element tokens and says how many were added,
removed and moved. "Moved" is an element whose shape is unchanged and whose
numbers are not — the ordinary result of a layout constant changing, and the
only kind of churn that should ever be waved through in bulk.

Read-only, stdlib only. Exits non-zero if anything differs, so it also works
as a pre-commit gate.

The rule that makes it worth having, from CLAUDE.md: no commit runs
`--update-goldens` without this output for every changed scene in its message,
and a sentence saying why each element moved.
"""
import argparse
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for extra in ("src", "examples", "tests"):
    sys.path.insert(0, str(ROOT / extra))

from scenes import SCENES  # noqa: E402

GOLDEN = ROOT / "tests" / "golden"

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_VIEWBOX = re.compile(r'viewBox="([\d.\- ]+)"')


def tokens(svg):
    """The document as elements: split between a `>` and the next `<`."""
    return [t for t in re.split(r"(?<=>)(?=<)", svg) if t]


def shape(token):
    """The token with its numbers blanked — what it is, not where it is."""
    return _NUM.sub("#", token)


def canvas(svg):
    m = _VIEWBOX.search(svg)
    if not m:
        return None
    return tuple(float(v) for v in m.group(1).split())[2:]


def compare(golden, fresh):
    """(added, removed, moved) as lists of (token, token-or-None)."""
    only_g = collections.Counter(tokens(golden))
    only_f = collections.Counter(tokens(fresh))
    removed, added = only_g - only_f, only_f - only_g

    by_shape = collections.defaultdict(list)
    for token, n in removed.items():
        by_shape[shape(token)] += [token] * n

    moved, gone = [], []
    for token, n in added.items():
        pool = by_shape[shape(token)]
        for _ in range(n):
            moved.append((pool.pop(), token)) if pool else gone.append(token)
    left = [t for pool in by_shape.values() for t in pool]
    return gone, left, moved


def report(name, golden, fresh, verbose=False):
    """One scene, in three lines at most. Returns True if it differs."""
    if golden == fresh:
        return False
    gc, fc = canvas(golden), canvas(fresh)
    head = f"{name:<18}"
    if gc != fc:
        dw, dh = fc[0] - gc[0], fc[1] - gc[1]
        delta = ", ".join(f"{k} {v:+.1f}" for k, v in
                          (("width", dw), ("height", dh)) if v)
        print(f"{head} canvas {gc[0]:g}x{gc[1]:g} -> {fc[0]:g}x{fc[1]:g}   "
              f"({delta})")
    else:
        print(f"{head} canvas {gc[0]:g}x{gc[1]:g}, unchanged")

    added, removed, moved = compare(golden, fresh)
    print(f"{'':<18} {len(added)} elements added, {len(removed)} removed, "
          f"{len(moved)} moved")
    if verbose:
        for was, now in moved:
            print(f"{'':<20} - {was}\n{'':<20} + {now}")
        for token in added:
            print(f"{'':<20} + {token}")
        for token in removed:
            print(f"{'':<20} - {token}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scene", nargs="*", help="scenes to check; default all")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="print every differing element")
    args = ap.parse_args(argv)

    names = args.scene or sorted(SCENES)
    unknown = [n for n in names if n not in SCENES]
    if unknown:
        ap.error("no such scene: " + ", ".join(unknown))

    changed = 0
    for name in names:
        path = GOLDEN / f"{name}.svg"
        if not path.exists():
            print(f"{name:<18} no golden on disk")
            changed += 1
            continue
        if report(name, path.read_text(encoding="utf-8"), SCENES[name](),
                  args.verbose):
            changed += 1
    if not changed:
        print(f"{len(names)} scenes, all identical")
    return 1 if changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
