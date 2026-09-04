"""`docs/stability.md` is held to the code.

The promise is only worth making if a change to what it covers fails a
test. Three things are checked mechanically: the public names are exactly
the ones the document lists, every finding code in the source is in the
document and every code in the document is in the source, and the keys the
two JSON reports carry are the ones it names.
"""
import json
import pathlib
import re

import thermodraw
from thermodraw import Diagram, check, describe

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = (ROOT / "docs" / "stability.md").read_text(encoding="utf-8")
SRC = ROOT / "src" / "thermodraw"

# Pinned literally: adding a name is a deliberate edit here and in the
# document; removing one is a major version.
ALL = [
    "Diagram", "Node", "Branch", "Source", "Rail", "DiagramError",
    "solve", "layout", "render", "Placement", "DiagramBuilder",
    "check", "Report", "Finding",
    "describe", "Description",
    "page",
    "Symbol", "SYMBOLS",
    "save", "theme",
    "symbols", "core", "model", "io",
]


def backticked(section):
    """Every `name` in one section of the document."""
    start = DOC.index(section)
    end = DOC.index("\n**", start + len(section)) if "\n**" in DOC[
        start + len(section):] else len(DOC)
    return set(re.findall(r"`([^`]+)`", DOC[start:end]))


def test_the_public_names_are_the_ones_promised():
    assert thermodraw.__all__ == ALL
    listed = backticked("**The public names.**")
    assert set(ALL) <= listed, set(ALL) - listed


def test_every_finding_code_is_promised_and_every_promised_code_exists():
    pattern = r'"([a-z]+(?:-[a-z]+)+)", "(?:error|warning|note)"'
    in_code = set()
    for name in ("_check.py", "_physics.py"):
        in_code |= set(re.findall(pattern, (SRC / name).read_text(
            encoding="utf-8")))
    promised = {c for c in backticked("**`check`'s report.**")
                if re.fullmatch(r"[a-z]+(?:-[a-z]+)+", c)}
    assert in_code == promised, (in_code ^ promised)


def test_the_report_shapes_are_the_ones_promised():
    d = Diagram.from_json((ROOT / "examples" / "hero.json").read_text(
        encoding="utf-8"))
    report = check(d).to_dict()
    assert set(report) == {"source", "ok", "labels", "findings"}
    finding = report["findings"][0]
    assert set(finding) == {"code", "severity", "where", "message",
                            "remedy", "at"}
    for key in report:
        assert f"`{key}`" in DOC
    for key in finding:
        assert f"`{key}`" in DOC
    told = describe(d).to_dict()
    for key in told:
        assert f"`{key}`" in DOC, key
    for key in told["nodes"][0]:
        assert f"`{key}`" in DOC, key
    for key in told["edges"][0]:
        assert f"`{key}`" in DOC, key


def test_the_json_round_trip_is_the_schema():
    """The schema is promised additive: a 1.0 file reads back as itself."""
    d = json.loads((ROOT / "examples" / "hero.json").read_text(
        encoding="utf-8"))
    assert Diagram.from_dict(d).to_dict() == d
