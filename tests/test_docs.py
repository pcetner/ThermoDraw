"""The reference page must not drift from the library again.

docs/symbol-reference.html is CLAUDE.md's visual specification and had no
generator: 165KB of hand-assembled SVG that could go stale silently, and had
— it was labelled draft 5 against core.py's draft 4.
"""
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_symbol_reference_is_up_to_date():
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "gen_docs.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_symbol_appears_on_the_page():
    from thermodraw import symbols
    page = (ROOT / "docs" / "symbol-reference.html").read_text(encoding="utf-8")
    for sym in symbols.SYMBOLS:
        assert f"<h4>{sym.name}</h4>" in page, f"{sym.key} missing"
        assert sym.note in page, f"{sym.key} note missing"


class TestTheSchema:
    """docs/schema.md is prose with no generator, so it cannot be diffed
    against the code the way the two HTML pages are. What can be pinned is
    the vocabulary: every field and every kind the model has appears on the
    page, and every kind the page lists exists. A documented kind the code
    refuses is the drift this catches. A sentence with a field's rules
    backwards is not — and one sat there for a while."""

    TEXT = (ROOT / "docs" / "schema.md").read_text(encoding="utf-8")
    TOKENS = set(re.findall(r"`([^`\n]+)`", TEXT))

    def test_the_quoted_describe_output_is_the_real_thing(self):
        """The page says so about itself, and nothing checked it.

        "That is the real output for `examples/hero.json`, not an
        abridgement" -- a claim the schema makes and could not keep.
        Anything that changes what `describe` prints silently falsifies a
        worked example the page tells a reader to trust, and the clean-room
        builder regenerates this block precisely because it cannot assume it
        is current.
        """
        from thermodraw import Diagram, describe
        hero = (ROOT / "examples" / "hero.json").read_text(encoding="utf-8")
        fresh = describe(Diagram.from_json(hero), source="diagram.json").text()

        # The block after the ```bash fence that holds the command: the
        # first fence following the anchor closes that one.
        i = self.TEXT.index("thermodraw describe diagram.json")
        first = self.TEXT.index("```", i)
        opened = self.TEXT.index("```", first + 3)
        closed = self.TEXT.index(chr(10) + "```", opened + 3)
        quoted = self.TEXT[opened + 3:closed].strip(chr(10))
        assert quoted == fresh.rstrip(), (
            "docs/schema.md quotes stale `describe` output; regenerate the "
            "block under 'Seeing what got drawn'")


    def test_every_field_is_named(self):
        from dataclasses import fields

        from thermodraw import model
        json_name = {"source": "from", "target": "to"}
        for cls in (model.Node, model.Branch, model.Source, model.Rail):
            for f in fields(cls):
                name = json_name.get(f.name, f.name)
                assert name in self.TOKENS, \
                    f"{cls.__name__}.{name} is not in schema.md"

    def test_every_kind_and_quantity_is_named(self):
        from thermodraw import model
        kinds = model.NODE_KINDS | model.BRANCH_KINDS | model.SOURCE_KINDS
        for kind in kinds:
            assert kind in self.TOKENS, f"kind {kind!r} is not in schema.md"
        for quantity in set(model.QUANTITY.values()):
            assert quantity in self.TOKENS, \
                f"quantity {quantity!r} is not in schema.md"

    def test_no_kind_on_the_page_is_unknown_to_the_code(self):
        from thermodraw import model
        rows = [line for line in self.TEXT.splitlines()
                if line.startswith("| `kind` |")]
        assert len(rows) == 2, "a node row and a branch row"
        listed = set()
        for row in rows:
            listed |= set(re.findall(r"`([a-z]+)`", row.split("|", 2)[2]))
        known = model.NODE_KINDS | model.BRANCH_KINDS
        assert listed <= known, listed - known
        # the source table: one row per kind, its unit in the fourth column
        sources = set(re.findall(
            r"^\| `([a-z]+)` \| [^|]* \| `[^`]+` \| `units", self.TEXT, re.M))
        assert sources == model.SOURCE_KINDS


class TestTheDictionary:
    """Dictionary.html is the page for someone who has not drawn one of these
    before: every symbol, what it means, and when to reach for it.

    Same guarantee as the reference sheet, for the same reason. The prose is
    written by hand and the pictures are not, so what has to be pinned is that
    the two describe the same eighteen symbols.
    """

    def test_the_page_is_up_to_date(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "gen_dictionary.py"),
             "--check"], capture_output=True, text=True, cwd=ROOT)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_every_symbol_has_a_meaning_and_a_scenario(self):
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        for sym in symbols.SYMBOLS:
            spec = gen_dictionary.ENTRIES.get(sym.key)
            assert spec is not None, f"{sym.key} has no entry"
            assert spec["use"], f"{sym.key} has no scenario"

    def test_a_new_symbol_stops_the_build(self):
        """The one check that matters: adding a glyph must not quietly ship a
        dictionary that does not mention it."""
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        extra = symbols.Symbol(key="unwritten", name="Unwritten",
                               draw=lambda a: "", half=5, half_len=5)
        original = symbols.SYMBOLS
        symbols.SYMBOLS = original + [extra]
        try:
            with pytest.raises(SystemExit) as exc:
                gen_dictionary.build()
            assert "unwritten" in str(exc.value)
        finally:
            symbols.SYMBOLS = original

    def test_every_symbol_is_drawn_on_it(self):
        from thermodraw import symbols
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        for sym in symbols.SYMBOLS:
            assert f"<h3>{sym.name}</h3>" in page, f"{sym.key} missing"
        # `corner` had an entry here with no drawing, because it drew
        # nothing. The kind is gone, and so is the entry.
        assert "<h3>Corner</h3>" not in page

    def test_a_card_is_one_glyph_at_one_scale(self):
        """Cards share a width, so they share a scale. Heights differ, which
        is what keeps a free node out of a thermal break's empty frame."""
        from thermodraw import symbols
        widths = {re.search(r'viewBox="0 0 ([\d.]+)', symbols.card(s)).group(1)
                  for s in symbols.SYMBOLS}
        assert widths == {str(symbols.DW)}
        heights = {re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)',
                             symbols.card(s)).group(1)
                   for s in symbols.SYMBOLS}
        assert len(heights) > 1

    def test_a_card_draws_the_symbol_inside_its_own_frame(self):
        """The frame is solved from the ink and the label, so nothing it
        shows may fall outside it — a clipped glyph on a page whose whole job
        is showing glyphs."""
        from thermodraw import core as S, symbols
        for sym in symbols.SYMBOLS:
            svg = symbols.card(sym)
            h = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)', svg).group(1))
            body = []
            _, top, _, bh = S.annotate(symbols.DCX, 0.0, 0, body,
                                       user=sym.user, name=sym.text,
                                       value=sym.value, half=sym.half,
                                       half_len=sym.half_len)
            cy = symbols.DPAD - min(-sym.ink[1], top)
            assert cy - sym.ink[1] >= -0.01, f"{sym.key} ink above the frame"
            assert cy + sym.ink[1] <= h + 0.01, f"{sym.key} ink below it"
            assert cy + top >= -0.01, f"{sym.key} label above the frame"
            assert cy + top + bh <= h + 0.01, f"{sym.key} label below it"

    def test_a_plate_says_what_its_example_says(self):
        """The drawing, the sentence and the JSON are one story.

        A plate reading "Die attach" over an example about a mug is exactly
        the jargon the page exists to avoid, and it was the first draft.
        """
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        by_key = {s.key: s for s in symbols.SYMBOLS}
        for key, spec in gen_dictionary.ENTRIES.items():
            label = spec["code"].get("label")
            if label is None:                       # a bare annotation
                continue
            svg = gen_dictionary.plate(by_key[key], spec)
            assert label in svg, f"{key}: plate does not say {label!r}"
            assert by_key[key].user not in svg or by_key[key].user == label, (
                f"{key}: plate still carries the library's sample words")

    def test_a_plate_cannot_show_notation_the_pipeline_would_not(self):
        """`break`'s sample carries `q = 0 W`, and no break node can draw it:
        a node's quantity is T. Taking the letter from the same tables
        `layout` reads is what keeps the page honest."""
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        by_key = {s.key: s for s in symbols.SYMBOLS}
        svg = gen_dictionary.plate(by_key["break"],
                                   gen_dictionary.ENTRIES["break"])
        assert "0 W" not in svg and ">q<" not in svg
        assert "Rubber feet" in svg

    def test_an_example_stating_a_value_must_have_a_unit(self):
        """Units are per diagram, so an entry may set its own — but it may
        not print a bare number, which is the one thing `model` refuses."""
        from thermodraw import symbols
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        by_key = {s.key: s for s in symbols.SYMBOLS}
        for key, spec in gen_dictionary.ENTRIES.items():
            if "value" not in spec["code"]:
                continue
            svg = gen_dictionary.plate(by_key[key], spec)
            unit = spec.get("unit") or by_key[key].value.split(" ", 1)[1]
            assert f'{spec["code"]["value"]} {unit}'.split()[-1] in svg

    def test_the_contents_defines_each_category_once(self):
        """The three words the page is organised around are defined on the
        panel whose symbols they cover. They used to be a badge on all
        nineteen entries, which repeated the words and defined none of them.
        """
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        for where in gen_dictionary.CATEGORIES:
            label, _, definition = gen_dictionary.WHERE[where]
            assert page.count(f"<h4>{label}</h4>") == 1, label
            assert definition in page, label
        assert 'class="badge"' not in page

    def test_every_symbol_is_listed_under_exactly_one_category(self):
        from thermodraw import symbols
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        keys = [s.key for s in symbols.SYMBOLS]
        for key in keys:
            assert page.count(f'<a href="#sym-{key}">') == 1, key

    def test_each_group_heading_can_pin_itself(self):
        """The heading stays named at the top of the window for as long as its
        own group is being read, which is what replaced the badges."""
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        from thermodraw import symbols
        # One per symbol group, plus the "Boxes and arrows" primer, which is
        # a section in its own right rather than a note under the contents.
        assert page.count('<div class="section-head">') == \
            len(symbols.GROUPS) + 1
        assert "position:sticky" in page

    def test_the_reading_rule_gets_its_own_section(self):
        """A box resists and an arrow carries is what the other nineteen
        entries are downstream of. It spent a revision as one line under the
        contents, which is not the weight it earns."""
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        assert "<h2>What the shapes mean</h2>" in page
        assert page.count('<div class="shape">') == len(gen_dictionary.SHAPES)

    def test_the_primer_places_its_shapes_inside_the_categories(self):
        """A box *is* a path and an arrow *is* a source, so the primer must
        say which. Headed "Boxes, arrows and chevrons" it read as a fourth
        classification beside node, path and source, and the first reader
        asked why boxes were covered separately from paths.
        """
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        for key, head, _ in gen_dictionary.SHAPES:
            assert "path" in head.lower() or "source" in head.lower(), \
                f"{key}: heading does not say which category it is"

    def test_the_primer_admits_the_shapes_it_does_not_show(self):
        """Three panels are not the whole vocabulary: a capacitance draws two
        plates and a break draws an open circuit, and both are paths. Left
        unsaid, the panels claim every path is a box or a chevron."""
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        shown = {k for k, _, _ in gen_dictionary.SHAPES}
        note = gen_dictionary.SHAPES_NOTE.lower()
        assert "cap" not in shown and "break-branch" not in shown
        assert "capacitance" in note and "break" in note

    def test_a_symbol_with_nothing_to_say_still_gets_a_frame(self):
        """The primer draws its glyphs bare, so `annotate` places no block
        and returns no rectangle. `card` used to unpack that None."""
        from thermodraw import symbols
        for sym in symbols.SYMBOLS:
            svg = symbols.card(sym, user=None, name=None, value=None)
            h = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)', svg).group(1))
            assert h >= 2 * sym.ink[1], sym.key
            assert "<text" not in svg, sym.key

    def test_no_em_dash_reaches_the_reader(self):
        """House style for this page. The prose is for someone meeting heat
        transfer for the first time, and a dash is usually standing in for a
        sentence that was not finished."""
        page = (ROOT / "Dictionary.html").read_text(encoding="utf-8")
        body = re.sub(r"<script>.*?</script>", "",
                      page.split("</style>", 1)[1], flags=re.S)
        assert "\u2014" not in body and "&mdash;" not in body

    def test_the_primer_answers_its_own_pictures(self):
        """Each panel has to explain the drawing beside it. The first draft
        showed a hatched box without saying why it was hatched, never said
        what a rate is, and left chevrons out of a vocabulary that has
        them."""
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        text = " ".join(b for _, _, b in gen_dictionary.SHAPES).lower()
        assert "hatching" in text, "the box is hatched and nothing says why"
        assert "watts" in text, "a rate is never defined"
        assert any(k == "flow-branch" for k, _, _ in gen_dictionary.SHAPES), \
            "chevrons are a third of the shapes and go unmentioned"

    def test_the_source_definition_admits_outbound_heat(self):
        """The category panel is the first definition a reader meets, and it
        said heat arrives. `flow` and `flux` may point away, and the Sources
        lede further down already said so, so the prominent one was the wrong
        one."""
        from thermodraw import model as M
        sys.path.insert(0, str(ROOT / "tools"))
        import gen_dictionary

        assert M.OUTWARD_KINDS, "no outbound source kinds left to describe"
        definition = gen_dictionary.WHERE["source"][2].lower()
        assert "leaving" in definition or "out of" in definition, definition
