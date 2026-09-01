"""The diagram as a page, not a picture.

`render` stays canonical: Word, the README and every rasteriser need a static
SVG, and none of them run script. What a standalone `.svg` cannot do is let a
reader expand a condensed group — not because SVG is static, but because a
*file* is. Inline SVG in a page is fully scriptable by its host, so the page
is where the controls live and the picture stays a picture.
"""
import pathlib
import re

import pytest

from thermodraw import Diagram, DiagramBuilder, layout, page
from thermodraw.page import groups
from thermodraw.render import variant_id

HERO = pathlib.Path(__file__).resolve().parents[1] / "examples" / "hero.json"


def repeated(n=8, arrangement="parallel"):
    return (DiagramBuilder("Immersion rack", R="K/W", T="C")
            .node("a", "Junction", "72", at=(0, 0))
            .node("b", "Spreader", "61", at=(760, 0))
            .branch("a", "b", "cond", "Die attach", "0.0275",
                    count=n, arrangement=arrangement).build())


class TestItIsOnePage:
    def test_nothing_is_fetched_from_anywhere(self):
        """Self-contained, or it is not a document you can send someone."""
        html = page(repeated())
        assert "<link" not in html and "src=" not in html
        assert "@font-face" in html, "the faces the solver measured"

    def test_the_svg_is_inline_rather_than_referenced(self):
        html = page(repeated())
        assert "<svg" in html and "<img" not in html

    def test_it_carries_the_diagram_title(self):
        assert "<title>Immersion rack</title>" in page(repeated())
        assert "<h1>Kettle</h1>" in page(repeated(), title="Kettle")

    def test_a_title_from_the_file_is_escaped(self):
        d = Diagram.from_dict({"title": "A <script> & co",
                               "nodes": [{"id": "a", "at": [0, 0]}]})
        html = page(d)
        assert "<script> & co" not in html
        assert "&lt;script&gt; &amp; co" in html


class TestTheControls:
    def test_a_repeated_group_gets_a_button(self):
        html = page(repeated(8))
        buttons = re.findall(r"<button[^>]*>([^<]*)</button>", html)
        assert buttons == ["Show all 8"]

    def test_the_button_names_the_two_forms_by_their_stable_ids(self):
        html = page(repeated(8))
        assert f'data-shows="{variant_id("branch 0 a->b", "full")}"' in html
        assert f'data-hides="{variant_id("branch 0 a->b", "condensed")}"' in html

    def test_the_hidden_form_is_in_the_file_already(self):
        """Which is what makes the swap two attributes and not a rebuild."""
        html = page(repeated(8))
        assert f'<g id="{variant_id("branch 0 a->b", "full")}" ' \
               'display="none">' in html

    def test_a_group_small_enough_to_draw_gets_no_button(self):
        assert "<button" not in page(repeated(3))

    def test_a_diagram_with_no_repetition_gets_no_controls(self):
        html = page(Diagram.from_json(HERO.read_text(encoding="utf-8")))
        assert "<button" not in html
        assert '<div class="controls"' not in html

    def test_a_group_with_only_one_form_is_not_offered_a_control(self):
        """Three or fewer draw every copy: there is no condensed form to
        swap to, so hiding the middle one would leave a gap."""
        assert groups(layout(repeated(3))) == []

    @pytest.mark.parametrize("n,offered", [(2, False), (3, False),
                                           (4, True), (16, True)])
    def test_a_control_appears_only_above_three(self, n, offered):
        found = groups(layout(repeated(n)))
        assert bool(found) is offered
        assert not found or found[0]["shown"] == "condensed"

    def test_groups_are_read_off_the_placements_not_the_diagram(self):
        """Same reason `check` reads the scene: the ids here have to be the
        ids `render` actually wrote."""
        found = groups(layout(repeated(8)))
        assert found == [{"ref": "branch 0 a->b", "n": 8,
                          "shown": "condensed"}]


class TestTheScriptStaysOutOfTheSvg:
    """A library whose first line is "emits SVG, no runtime dependencies"
    should not put a widget inside every picture it draws — and half its
    documented targets could not run one."""

    def test_the_rendered_svg_has_no_script(self):
        from thermodraw import render
        assert "<script" not in render(layout(repeated(8)))

    def test_the_page_has_exactly_one(self):
        assert page(repeated(8)).count("<script") == 1

    def test_the_script_is_after_the_markup_it_drives(self):
        html = page(repeated(8))
        assert html.index("<button") < html.index("<script")
