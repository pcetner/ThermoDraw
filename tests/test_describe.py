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
from thermodraw._describe import side_word
from thermodraw._render import compose

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
        lines = describe(d).lines
        assert len([l for l in lines if l.label_at]) ==             len(compose(layout(d)).rects) == 11
        # Twelve rows for eleven labels: the boundary wall carries no text of
        # its own and still gets one, because where it landed is the thing
        # nothing else could report.
        assert len(lines) == 12
        wall = [l for l in lines if l.kind == "ground"]
        assert [l.ref for l in wall] == ["wall of node 'amb'"]
        assert wall[0].at == (936.0, 384.0) and wall[0].label_at is None

    def test_it_says_where_each_element_sits(self):
        """The label's position is not the element's, and for a source which
        way it points is the whole of its meaning."""
        at = {l.ref: (l.at, l.angle) for l in describe(hero()).lines}
        assert at["branch 4 j->rail"] == ((200.0, 278.0), 90.0)
        assert at["source 0 -> j"] == ((96.0, 150.0), 0.0)
        text = describe(hero()).text()
        assert "symbol/cap      (200, 278) a90" in text
        assert "symbol/cond     (312, 150)   " in text, "angle 0 not printed"

    def test_an_element_with_no_label_still_gets_a_row(self):
        """`compose` skips a label with nothing to say, so a row keyed on
        labels made an unlabelled element vanish into the counts.

        A `break` branch names no quantity by design — leave its `label` off
        and it is exactly this case.
        """
        d = (DiagramBuilder(T="C")
             .node("a", "Cell", "44", at=(0, 0))
             .node("b", "Chassis", "30", at=(340, 0))
             .branch("a", "b", "break").build())
        line = [l for l in describe(d).lines if l.ref.startswith("branch")][0]
        assert line.kind == "symbol/break-branch" and line.at == (170.0, 0.0)
        assert line.label_at is None and line.says == ""
        assert "(no label)" in line.text()
        assert describe(d).text().splitlines()[0].endswith("2 labels")

    def test_it_gives_the_nodes_their_kinds_and_places(self):
        assert ("amb", "fixed", (936, 372)) in describe(hero()).nodes

    def test_it_says_what_each_label_reads(self):
        """The geometry cannot tell a mass on the right node from one on the
        wrong node: both draw the same box, and only the words differ.

        Found by the acceptance test — with positions alone, hanging the
        41 J/K capacitance off the wrong node gave byte-identical output.
        """
        says = {l.ref: l.says for l in describe(hero()).lines}
        assert says["branch 4 j->rail"] == "Die | C_j = 0.9 J/K"
        assert says["node 'amb'"] == "Still air | T_amb = 40 °C"
        assert says["source 0 -> j"] == "Switching loss | P_d = 45 W"

    def test_a_subscript_is_read_back_rather_than_left_as_markup(self):
        from thermodraw._describe import label_text
        from thermodraw._layout import Label
        assert label_text(Label(user="Die", name='C<tspan dy="4">j</tspan>',
                                value="0.9 J/K")) == "Die | C_j = 0.9 J/K"
        # A label is text, not markup: an entity the author typed is reported
        # as typed, because that is what the drawing shows too.
        assert label_text(Label(user="Fins &#8594; air")) == "Fins &#8594; air"
        assert label_text(None) == ""

    def test_it_says_where_the_rail_is(self):
        """`rail.reference` does nothing but record which node the rail is,
        so this is the only place it can ever be checked against intent."""
        assert describe(hero()).rail == ("amb", 372, (200, 936))
        assert "rail: y 372, span (200, 936), reference 'amb'" \
            in describe(hero()).text()

    def test_a_diagram_with_no_rail_says_nothing_about_one(self):
        d = DiagramBuilder(T="C").node("a", "Only", "20", at=(0, 0)).build()
        assert describe(d).rail is None
        assert "rail:" not in describe(d).text()

    def test_an_absent_span_is_reported_as_the_one_that_will_be_drawn(self):
        d = (DiagramBuilder(T="C", C="J/K")
             .node("a", "A", "20", at=(0, 0))
             .node("b", "B", "30", at=(400, 0))
             .rail("a", 300)
             .branch("a", "rail", "cap", "Mass", "5").build())
        assert describe(d).rail == ("a", 300, (0, 400))

    def test_the_parallel_pair_is_visible_rather_than_only_graded(self):
        """The note `check` raises, readable straight off the description."""
        sides = {l.ref: l.side for l in describe(hero()).lines}
        assert sides["branch 2 s->amb"] == sides["branch 3 s->amb"] == "above"


class TestItReadsInATerminal:
    def test_the_fixed_text_is_ascii(self):
        """Same rule as the report: a Windows console is cp1252.

        The diagram's own words are the diagram's own, exactly as node ids
        are in a finding — quoting them is the job. What must not carry an
        em dash is the scaffolding, which is what this asserts by using a
        diagram whose every label and unit is ASCII.
        """
        d = (DiagramBuilder(R="K/W", T="C")
             .node("a", "Hot", "120", at=(0, 0))
             .node("b", "Cold", "40", kind="fixed", at=(300, 0))
             .source("a", "diss", "Loss", at=(-120, 0))
             .branch("a", "b", "cond", "Slab", "0.35").build())
        assert describe(d).text().isascii()

    def test_a_diagram_that_is_not_ascii_still_describes(self):
        """`__main__` softens stdout, so the text itself need not be."""
        assert "Fins → air" in describe(hero()).text()

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
        assert {l["ref"] for l in data["elements"]} >= {"node 'j'"}


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


class TestWhatOnePointZeroAdded:
    """Where a wall landed was the one thing nothing could report, and
    whether `K` meant absolute or a rise was the other."""

    @staticmethod
    def mount(wall="down", scale=None):
        units = {"R": "K/W", "T": "K" if scale is None
                 else {"unit": "K", "scale": scale}}
        return Diagram.from_dict({
            "units": units,
            "nodes": [{"id": "body", "label": "Cold mass", "value": "4",
                       "at": [400, 300]},
                      {"id": "mount", "kind": "fixed", "label": "Mount",
                       "value": "300", "at": [400, 80], "wall": wall}],
            "branches": [{"from": "body", "to": "mount", "kind": "cond",
                          "label": "Strut", "value": "50"}]})

    def test_a_turned_wall_is_said_on_the_node_row(self):
        text = describe(self.mount("up")).text()
        assert "  mount          fixed    at (400, 80) wall up" in text
        assert "wall of node 'mount'   ground          (400, 68) faces up" in text

    def test_a_wall_facing_down_is_not_remarked_on(self):
        assert "wall" not in [w for l in describe(self.mount()).text()
                              .splitlines() if l.startswith("  mount")
                              for w in l.split()]

    def test_the_scale_is_said_when_declared(self):
        text = describe(self.mount(scale="rise")).text()
        assert "\ntemperatures: rise above ambient, in K\n" in text
        text = describe(self.mount(scale="absolute")).text()
        assert "\ntemperatures: absolute, in K\n" in text

    def test_and_not_when_it_is_not(self):
        assert "temperatures:" not in describe(self.mount()).text()

    def test_both_reach_the_json(self):
        out = describe(self.mount("left", "absolute")).to_dict()
        assert out["scale"] == "absolute"
        assert [n.get("wall") for n in out["nodes"]] == [None, "left"]
