"""What got drawn, in words.

`check` grades the drawing and cannot say whether it is the one you meant.
Both acceptance agents asked for this, independently and unprompted, having
been given only `docs/schema.md`: element counts, canvas size, which way each
label went — enough to confirm intent without a browser.

These pin the two things the output is for. It has to be *readable*, because
the reader is a terminal and sometimes a cp1252 one; and it has to be *true*,
because a description that drifts from the render is worse than none — which
is why it reads `render.compose`'s own Scene rather than rebuilding the page.
"""
import json
import math
import pathlib

import pytest

from thermodraw import Diagram, DiagramBuilder, describe, layout
from thermodraw.describe import side_word
from thermodraw.render import compose

HERO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "hero.json"


def hero():
    return Diagram.from_json(HERO.read_text(encoding="utf-8"))


def ladder():
    return (DiagramBuilder(R="K/W", T="°C")
            .node("a", "Hot", "120", at=(0, 0))
            .node("b", "Cold", "40", kind="fixed", at=(300, 0))
            .branch("a", "b", "cond", "Slab", "0.35").build())


class TestItSaysWhatIsThere:
    def test_the_canvas_is_the_one_render_uses(self):
        """Not a recomputation of it: the same Scene, or it will drift."""
        d = hero()
        box = compose(layout(d), size=d.size).box
        assert describe(d).canvas == (round(box[2] - box[0], 1),
                                      round(box[3] - box[1], 1))

    def test_it_counts_placements_by_what_they_are(self):
        counts = describe(hero()).counts
        assert counts["symbol/cap"] == 2 and counts["symbol/cond"] == 1
        assert counts["node"] == 4 and counts["ground"] == 1

    def test_it_lists_every_label_the_render_placed(self):
        d = hero()
        assert len(describe(d).lines) == len(compose(layout(d)).rects) == 11

    def test_it_gives_the_nodes_their_kinds_and_places(self):
        assert ("amb", "fixed", (936, 372)) in describe(hero()).nodes

    def test_the_parallel_pair_is_visible_rather_than_only_graded(self):
        """The note `check` raises, readable straight off the description."""
        sides = {l.ref: l.side for l in describe(hero()).lines}
        assert sides["branch 2 s->amb"] == sides["branch 3 s->amb"] == "above"


class TestItReadsInATerminal:
    def test_the_text_is_ascii(self):
        """Same reason as the report: a Windows console is cp1252."""
        assert describe(ladder()).text().isascii()

    def test_no_line_is_padded_past_its_content(self):
        assert not [l for l in describe(hero()).text().splitlines()
                    if l != l.rstrip()]

    def test_the_first_line_says_the_size_and_the_count(self):
        head = describe(hero(), source="hero").text().splitlines()[0]
        assert head == "hero: canvas 1042 x 431, 11 labels"

    def test_one_label_is_not_pluralised(self):
        d = DiagramBuilder(T="°C").node("a", "Only", "20", at=(0, 0)).build()
        assert describe(d).text().splitlines()[0].endswith("1 label")

    def test_the_placements_line_wraps_under_itself(self):
        lines = describe(hero()).text().splitlines()
        head = [i for i, l in enumerate(lines) if l.startswith("placements:")][0]
        assert lines[head + 1].startswith(" " * len("placements: "))
        assert max(len(l) for l in lines[head:head + 3]) <= 78

    def test_a_builder_describes_itself(self):
        """Symmetry with `.check()` and `.svg()`, which take the same size."""
        b = (DiagramBuilder(R="K/W", T="°C")
             .node("a", "Hot", "120", at=(0, 0))
             .node("b", "Cold", "40", kind="fixed", at=(300, 0))
             .branch("a", "b", "cond", "Slab", "0.35"))
        assert b.describe().to_dict() == describe(b.build()).to_dict()

    def test_it_is_json_when_asked(self):
        data = json.loads(json.dumps(describe(hero()).to_dict()))
        assert data["canvas"] == [1041.7, 430.8]
        assert {l["ref"] for l in data["labels"]} >= {"node 'j'"}


class TestItSaysHowTheLabelLanded:
    def test_a_direction_becomes_a_word(self):
        assert side_word((0.0, -1.0)) == "above"
        assert side_word((1.0, 0.0)) == "right"
        assert side_word((0.7071, 0.7071)) == "below right"

    def test_a_direction_between_the_eight_is_given_in_degrees(self):
        """`side` is a vector, not one of the four `PAGE_SIDES` names, so
        an `angle` on the branch can point it anywhere."""
        word = side_word((math.cos(math.radians(20)),
                          math.sin(math.radians(20))))
        assert word == "20 deg"

    def test_a_pushed_label_says_so(self):
        d = (DiagramBuilder(T="°C")
             .node("a", "A rather long node label", "110", at=(0, 0),
                   side="up")
             .node("b", "Another long node label", "60", at=(20, 0),
                   side="up").build())
        pushed = [l for l in describe(d).lines if l.pushed]
        assert pushed and "pushed" in pushed[0].text()

    def test_a_clean_drawing_says_nothing_extra(self):
        for line in describe(ladder()).lines:
            assert line.text().rstrip() == line.text()
            assert "pushed" not in line.text()
