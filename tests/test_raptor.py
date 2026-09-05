"""The README hero, held to the library's own standard.

`examples/raptor.json` is what a visitor sees first, and the README makes
three claims about it: the file holds no coordinates, `check --physics`
reports nothing, and a wrong number would be caught. Each is tested here so
the page cannot drift from the file.
"""
import json
import pathlib

import pytest

from thermodraw import Diagram, check

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAPTOR = ROOT / "examples" / "raptor.json"

pytestmark = pytest.mark.skipif(not RAPTOR.exists(),
                                reason="examples/ is not installed")


def data():
    return json.loads(RAPTOR.read_text(encoding="utf-8"))


def test_nothing_in_the_file_is_placed_by_hand():
    d = data()
    assert all("at" not in n for n in d["nodes"])
    assert all("at" not in b and "via" not in b for b in d["branches"])
    assert all("at" not in s for s in d["sources"])
    assert "rail" not in d


def test_it_is_clean_and_its_numbers_agree():
    report = check(Diagram.from_dict(data()), physics=True, source="raptor")
    assert report.findings == []
    assert report.labels == 9
    assert report.text().isascii()


def test_a_wrong_number_is_caught():
    """The README changes the gas-side convection to 0.20 K/W and quotes
    what happens. The hot face then takes 38 % more than it passes on."""
    d = data()
    conv = d["branches"][0]
    assert conv["kind"] == "conv" and conv["value"] == "0.283"
    conv["value"] = "0.20"
    report = check(Diagram.from_dict(d), physics=True, source="raptor")
    assert [f.code for f in report.findings] == [
        "node-does-not-balance", "rate-does-not-match"]
    assert "node 'hw'" in report.findings[0].message


def test_every_number_is_an_estimate_and_says_so():
    """The title carries the disclaimer, and the sources file exists."""
    d = data()
    assert "not SpaceX data" in d["title"]
    assert (ROOT / "examples" / "raptor.md").exists()
