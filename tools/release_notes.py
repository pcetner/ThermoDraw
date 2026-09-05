"""One version's section of the changelog, for the GitHub Release.

    python tools/release_notes.py 1.0.0

Prints everything between `## [1.0.0] - <date>` and the next `## ` heading,
exactly as written, so the Release's notes are the changelog's entry and
not a second account of the same release. Exits 1 naming the version if
the changelog has no such section, which is also what
tests/test_release.py demands of a version before it can be tagged.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHANGELOG = ROOT / "CHANGELOG.md"


def section(version: str, text: str) -> str:
    heading = re.compile(rf"^## \[{re.escape(version)}\] - .*$", re.M)
    m = heading.search(text)
    if not m:
        raise KeyError(version)
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    return body.strip("\n") + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    try:
        notes = section(argv[0], CHANGELOG.read_text(encoding="utf-8"))
    except KeyError:
        print(f"CHANGELOG.md has no section for {argv[0]}", file=sys.stderr)
        return 1
    sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
