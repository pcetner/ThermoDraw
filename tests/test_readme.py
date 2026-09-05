"""The README quotes the tools and links the tree, and nothing checked it.

Its `check` output was stale for a release: the remedy's wording changed
and the page kept the old one. The quoted blocks here are compared with the
real output, and every link on the page has to go somewhere.
"""
import json
import pathlib
import re
import sys

import pytest

from thermodraw import Diagram, check, describe

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
RAPTOR = ROOT / "examples" / "raptor.json"
SITE = "https://pcetner.github.io/ThermoDraw/"

pytestmark = pytest.mark.skipif(not README.exists(),
                                reason="not a checkout")

TEXT = README.read_text(encoding="utf-8") if README.exists() else ""


FENCES = [(m.start(), m.group(1), m.group(2))
          for m in re.finditer(r"```(\w*)\n(.*?)\n```", TEXT, re.S)]


def fence_after(marker):
    """The first unlabelled fenced block after `marker`: the command sits
    in a ```bash fence, and its output is the plain fence that follows."""
    i = TEXT.index(marker)
    for start, lang, body in FENCES:
        if start > i and lang == "":
            return body
    raise AssertionError(f"no output block after {marker!r}")


def words(s):
    """The page wraps a long finding by hand; the words are what is pinned."""
    return " ".join(s.split())


def raptor():
    return json.loads(RAPTOR.read_text(encoding="utf-8"))


class TestTheQuotedOutputIsReal:
    def test_the_clean_check(self):
        quoted = fence_after("thermodraw check --physics examples/raptor.json")
        real = check(Diagram.from_dict(raptor()), physics=True,
                     source="examples/raptor.json").text()
        assert words(quoted) == words(real)

    def test_the_broken_check(self):
        d = raptor()
        conv = d["branches"][0]
        assert conv["value"] == "0.283", "the page says 0.283"
        conv["value"] = "0.20"
        quoted = fence_after("and run it again:")
        real = check(Diagram.from_dict(d), physics=True,
                     source="examples/raptor.json").text()
        assert words(quoted) == words(real)

    def test_the_describe_head(self):
        quoted = fence_after("thermodraw describe examples/raptor.json")
        real = describe(Diagram.from_dict(raptor()),
                        source="examples/raptor.json").text()
        head = real.split("\n\n")[:2]
        assert quoted.strip("\n") == "\n\n".join(head)


class TestEveryLinkGoesSomewhere:
    targets = (re.findall(r"\]\(([^)\s]+)\)", TEXT)
               + re.findall(r'(?:src|srcset|href)="([^"]+)"', TEXT))

    def test_something_was_found(self):
        assert len(self.targets) > 10

    @pytest.mark.parametrize("target", sorted(set(targets)))
    def test_it_resolves(self, target):
        if target.startswith(SITE):
            sys.path.insert(0, str(ROOT / "tools"))
            import build_site
            rel = target[len(SITE):] or "index.html"
            if rel.endswith("/"):
                rel += "index.html"
            assert rel in build_site.paths(), target
        elif target.startswith("http"):
            assert "github.com/pcetner/ThermoDraw" in target \
                or "pypi.org/project/thermodraw" in target \
                or "img.shields.io" in target, target
        else:
            assert (ROOT / target).exists(), target
