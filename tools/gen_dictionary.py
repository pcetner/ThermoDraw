"""Regenerate the symbol dictionary.

    python tools/gen_dictionary.py

Dictionary.html is the page you hand someone who has never drawn a thermal
network: every symbol, what it means in plain words, one short example, and
the line of JSON that puts it in a file.

It is generated for the same reason `docs/symbol-reference.html` is. That page
was hand-assembled inline SVG and drifted from the library without anything
noticing, and a sheet showing a glyph the library cannot draw is worse than no
sheet at all. Every drawing below comes from `symbols.card`, so the picture is
whatever the library actually emits.

The prose is the part a machine cannot write, so it lives here keyed by symbol
key, and `build` refuses to run if the library grows a symbol this file has no
entry for. Adding a glyph therefore breaks this build until someone says what
it means — which is the point.

tests/test_docs.py asserts the committed page matches a fresh run.
"""
import argparse
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thermodraw import __version__, symbols, theme  # noqa: E402
from thermodraw import core as S  # noqa: E402
from thermodraw import model as M  # noqa: E402

TEMPLATE = ROOT / "docs" / "dictionary.template.html"
PAGE = ROOT / "Dictionary.html"

# The three things a symbol can be: what to call it, what it means, and which
# array of the file it is written into.
#
# This used to be a badge repeated on all nineteen entries, which said the
# same three words over and over and still never defined them. The definition
# now sits once, at the top, on the panel you pick a symbol from — and the
# entries carry no badge at all, because the sticky heading above them already
# says which group is being read.
WHERE = {"node": ("Node", "nodes", "A place that has a temperature."),
         "branch": ("Path", "branches",
                    "A route heat takes between two places."),
         "source": ("Source", "sources",
                    "Heat arriving from outside the network.")}
CATEGORIES = ("node", "branch", "source")

# What each symbol says, when to use it, and how it is written.
#
#   where  node, branch or source
#   what   the meaning, in the fewest sentences that are still true
#   use    one example, and the rule for these is that a reader meeting heat
#          transfer for the first time must already know the situation. A mug,
#          a pan, a window. An earlier draft reached for junction temperatures
#          and immersion racks, which flatter the author and cost the reader a
#          second unfamiliar thing to hold while learning the first.
#   code   that same example as it appears in a diagram file, as data rather
#          than as text, so the page cannot show JSON that would not parse
#   unit   optional, and only where the library's sample unit is wrong for
#          this example. Units are per diagram in this library, so an entry
#          choosing its own is the ordinary case rather than a special one: a
#          cast-iron pan is 900 J/K, and inheriting the sample's mJ/K would
#          have printed a number a thousandfold out with a straight face.
ENTRIES = {
    "free": dict(
        where="node",
        what="A place in the network that has a temperature, with nothing "
             "holding it there. Its temperature is whatever the paths meeting "
             "at it settle on, which usually makes it the thing you are "
             "trying to work out. Most nodes are free ones, and it is the "
             "default &mdash; leave <code>kind</code> out and you get this.",
        use="The outside of a mug of tea. Nothing sets its temperature "
            "directly; it lands wherever the tea and the room leave it.",
        code={"id": "mug", "kind": "free", "label": "Mug surface",
              "sub": "s", "value": "48"}),
    "fixed": dict(
        where="node",
        what="A temperature imposed from outside, which nothing the network "
             "does can change. The wire runs down into a hatched wall, the "
             "drafting mark for a boundary: heat may cross it in either "
             "direction, at any rate, without moving the number.",
        use="The air in the room. One mug of tea cannot warm it up, so its "
            "temperature is a given rather than an answer.",
        code={"id": "room", "kind": "fixed", "label": "Room air",
              "sub": "air", "value": "20"}),
    "break": dict(
        where="node",
        what="A boundary the network touches mechanically but not thermally. "
             "It is the fixed node with its connecting stub taken away, and "
             "the visible gap is the entire statement: nothing crosses here. "
             "There is no heat path, so usually no temperature to state "
             "either, and the label stands alone.",
        use="The rubber feet under a laptop. They hold it to the desk without "
            "letting heat into it.",
        code={"id": "desk", "kind": "break", "label": "Rubber feet"}),
    "phase": dict(
        where="node",
        what="A temperature held constant by a change of phase rather than by "
             "a boundary, so it takes the constant-temperature marking &mdash; "
             "two short rules beneath &mdash; and no wall. While the phase "
             "change lasts, heat crosses it with no temperature rise at all.",
        use="A pan of boiling water. It sits at 100&nbsp;&deg;C however far "
            "you turn the hob up; the extra heat makes steam instead.",
        code={"id": "boil", "kind": "phase", "label": "Boiling water",
              "sub": "boil", "value": "100"}),

    "cond": dict(
        where="branch",
        what="Heat crossing solid material. Section hatching is the drafting "
             "convention for solid material, so the interior says exactly "
             "what is being crossed. The thicker the material and the worse "
             "it conducts, the larger the resistance.",
        use="The wall of a mug, between the tea inside and your hand outside.",
        code={"from": "tea", "to": "mug", "kind": "cond", "label": "Mug wall",
              "value": "0.35"}),
    "conv": dict(
        where="branch",
        what="Heat leaving a surface into a moving fluid. Streamlines say a "
             "fluid is passing, and they turn with the block because flow "
             "along the path is what they mean. The faster the fluid moves "
             "and the more surface it touches, the smaller the resistance.",
        use="A hot drink cooling into the air around it &mdash; and cooling "
            "faster when you blow across the top.",
        code={"from": "mug", "to": "room", "kind": "conv",
              "label": "Mug → Room air", "value": "1.80"}),
    "rad": dict(
        where="branch",
        what="Heat leaving a surface as thermal radiation. The box is empty "
             "and the wave arrows cross it unaided, because radiation needs "
             "no medium. The dashed outline is redundant coding for the one "
             "path that is not linear in temperature &mdash; it goes as the "
             "fourth power &mdash; so a reader notices before trusting any "
             "superposition.",
        use="The warmth on your face from a fire across the room, which "
            "reaches you without heating the air in between.",
        code={"from": "fire", "to": "you", "kind": "rad",
              "label": "Fire → Face", "value": "6.40"}),
    "contact": dict(
        where="branch",
        what="The resistance of two solids pressed together. No two surfaces "
             "are perfectly flat, so they touch only in places and heat is "
             "held up at the join. Each half is hatched in the opposite "
             "direction with a seam between them &mdash; the drafting "
             "convention for two parts meeting in section. Without the "
             "opposing hatch it would read as one solid block.",
        use="A saucepan sitting on a hotplate. The two never quite meet, and "
            "the gap costs you a temperature drop.",
        code={"from": "hob", "to": "pan", "kind": "contact",
              "label": "Pan on hotplate", "value": "0.15"}),

    "spread": dict(
        where="branch",
        what="Conduction into a cross-section that grows as the heat goes: a "
             "small source on a much larger sheet. The hatching fans from a "
             "point rather than running parallel, because the area available "
             "increases along the path. Drawn as plain conduction it would "
             "assert one-dimensional flow, which is exactly what spreading "
             "is not.",
        use="A small gas flame under a wide frying pan. The heat has to fan "
            "out sideways through the base before it reaches the edges.",
        code={"from": "flame", "to": "pan", "kind": "spread",
              "label": "Flame → Pan base", "value": "0.15"}),
    "pipe": dict(
        where="branch",
        what="A link so good that both ends sit at nearly the same "
             "temperature. Inside it a fluid boils at the hot end and "
             "condenses at the cold one, which is what the opposed arrows "
             "show: vapour out along one face, liquid back along the other. "
             "It still takes a resistance, because the real thing has a small "
             "one; what it stops doing is wearing solid-conduction hatching "
             "on a device that is not conducting.",
        use="The flattened copper tube inside a laptop, carrying heat from "
            "the chip out to the fan with almost no temperature drop.",
        code={"from": "chip", "to": "fins", "kind": "pipe",
              "label": "Heat pipe", "value": "0.0018"}),
    "mixed": dict(
        where="branch",
        what="One number covering more than one mechanism, or a mechanism you "
             "do not wish to name. The interior is empty, and in a vocabulary "
             "where the texture names the mechanism that emptiness is a "
             "statement rather than an omission. It is the only path whose "
             "subscript you set, because it is the only one the library "
             "cannot name for you.",
        use="A double-glazed window, sold as a single figure that already has "
            "conduction and convection rolled together.",
        code={"from": "inside", "to": "outside", "kind": "mixed",
              "sub": "window", "label": "Double glazing", "value": "0.31"}),
    "cap": dict(
        where="branch",
        what="Thermal mass: the heat a thing has to take in before its "
             "temperature will rise. It stores rather than conducts, so it "
             "hangs from a node down to the reference rail instead of lying "
             "between two places. It matters only while things are changing "
             "&mdash; once everything has settled it carries nothing.",
        use="A cast-iron pan: slow to heat up, and just as slow to cool down "
            "again.",
        unit="J/K",
        code={"from": "pan", "to": "rail", "kind": "cap",
              "label": "Cast-iron pan", "sub": "pan", "value": "900"}),

    "flow-branch": dict(
        where="branch",
        what="Heat moved bodily from one place to another because a fluid is "
             "moving and taking the heat with it. It carries a rate, not a "
             "resistance. Chevrons rather than a box: the interior of a box "
             "states what the heat is crossing, and here nothing is crossed "
             "&mdash; the medium is going. It is the only directed path, so "
             "<code>from</code> and <code>to</code> are the way the heat "
             "travels, and <code>angle</code> is refused on one.",
        use="Hot water pumped from a boiler to a radiator. The heat travels "
            "because the water does.",
        code={"from": "boiler", "to": "radiator", "kind": "flow",
              "label": "Central heating", "value": "1.5"}),
    "break-branch": dict(
        where="branch",
        what="A mechanical connection that carries no heat, drawn as an open "
             "circuit. Deliberately neither a plain wire, which would say "
             "heat flows, nor a resistance, which would say how much. It "
             "names no quantity, so it takes no value and gets no second line "
             "of text.",
        use="The plastic handle on a saucepan. It is bolted on to hold the "
            "pan, and chosen so that heat does not follow.",
        code={"from": "pan", "to": "handle", "kind": "break",
              "label": "Plastic handle"}),

    "diss": dict(
        where="source",
        what="Heat appearing at a place because something there is making it. "
             "An arrow rather than a two-terminal element, because heat "
             "generated somewhere does not travel to that place from anywhere "
             "&mdash; it simply appears. It always points inward.",
        use="A light bulb, which turns most of the power it draws straight "
            "into heat.",
        code={"to": "bulb", "kind": "diss", "label": "Bulb power",
              "sub": "in", "value": "45"}),
    "radin": dict(
        where="source",
        what="Radiation arriving from outside the network, drawn with the "
             "same wave arrow the radiation path uses. Reach for it where the "
             "incoming radiation is a number you already know rather than "
             "something to be worked out. Being radiation <em>arriving</em>, "
             "it also always points inward.",
        use="Sunlight falling on a parked car.",
        code={"to": "roof", "kind": "radin", "label": "Sunlight",
              "sub": "sun", "value": "600"}),
    "flow": dict(
        where="source",
        what="A stated heat rate going into or out of one place: an "
             "annotation for where you know the number and do not need to "
             "draw the path it took. Give it <code>to</code> for heat "
             "arriving or <code>from</code> for heat leaving, and the arrow "
             "follows what you said.",
        use="The heat carried out of a room by an extractor fan, when the "
            "figure is all you need to say.",
        code={"from": "room", "kind": "flow", "value": "38"}),
    "flux": dict(
        where="source",
        what="A heat rate per unit area going into or out of a surface. "
             "Several arrows stand against a hatched band, because a flux is "
             "spread over an area and has no single line of action to borrow "
             "the heat-flow arrow. It is measured in its own quantity, "
             "<em>q&#8243;</em>, and never shares units with a heat rate.",
        use="Sunshine on a roof, given per unit of area rather than as one "
            "total for the whole roof.",
        code={"to": "roof", "kind": "flux", "label": "Sun on roof",
              "value": "0.1"}),
}

# The one node kind that draws nothing, and so has no `Symbol` and no card.
# It belongs in a dictionary all the same: a reader who does not find it here
# will assume it does not exist, and two acceptance readers reached for it
# when what they wanted was a labelled free node.
CORNER = dict(
    key="corner",
    name="Corner",
    where="node",
    what="A coordinate, not a place. It draws no circle, takes no label and "
         "has no temperature; it exists only so that a line has somewhere to "
         "bend. If what you want is a junction that is named but has no "
         "temperature of its own, use a free node with a label and no value "
         "instead.",
    use="Taking a path around something on the page instead of straight "
        "through it.",
    code={"id": "k1", "kind": "corner", "at": [420, 260]})

# Each group's opening line. Keyed on the group titles in `symbols.GROUPS`, so
# a regrouping there shows up here as a KeyError rather than as silent prose
# attached to the wrong set of symbols.
LEDES = {
    "Nodes":
        "A place, and what &mdash; if anything &mdash; holds its temperature "
        "there.",
    "Paths: what the heat crosses":
        "Four mechanisms, four interiors. The pattern inside the box names "
        "what the heat is passing through.",
    "Paths: shape, phase, mechanism, storage":
        "Paths the four basic mechanisms cannot describe on their own.",
    "Paths that carry a rate, or carry nothing":
        "Boxes resist; these two do not.",
    "Sources":
        "Heat entering or leaving one place, from outside the network.",
}

# `json.dumps(indent=2)` breaks every array over three lines, which turns a
# coordinate pair into a paragraph. Nothing else in an entry is an array.
_PAIR = re.compile(r"\[\s*(-?[\d.]+),\s*(-?[\d.]+)\s*\]")


def written_as(spec):
    """The example, as it appears in a file, and which array it goes in.

    A bare object with nothing above it was the part of the first draft
    readers could not place: correct JSON, no clue what to do with it. The
    caption ties it to the example rather than to the drawing on purpose —
    the drawing is the library's own reference sample and carries the
    library's own words, so a reader told this was "the drawing above" would
    be looking for a mug in a plate that says Die attach.
    """
    _, array, _ = WHERE[spec["where"]]
    body = _PAIR.sub(r"[\1, \2]",
                     json.dumps(spec["code"], indent=2, ensure_ascii=False))
    return (f'<div class="written"><p class="cap">As a component in '
            f'<code>"{array}"</code></p>'
            f"<pre>{html.escape(body)}</pre></div>")


def plate(sym, spec):
    """The glyph, labelled with this entry's own example.

    The words come from the example so that the drawing, the sentence and the
    JSON are one story instead of three — a plate reading "Die attach" over an
    example about a mug is the jargon this page exists to avoid.

    What is *not* invented here is the notation. The letter and its subscript
    are read from the same tables `layout` reads, so the plate cannot show a
    symbol the pipeline would not produce, and the unit comes off the
    library's own sample value, which is where it lives. That is also what
    fixes the thermal break: its sample carries `q = 0 W`, which no break node
    can ever draw, because a node's quantity is T.
    """
    code, where = spec["code"], spec["where"]
    kind = code.get("kind", "free")
    if where == "source":
        base, sub = M.SOURCE_SYMBOL[kind], code.get("sub")
    elif where == "branch":
        base, sub = M.BRANCH_SYMBOL[kind], M.BRANCH_SUB[kind] or code.get("sub")
    else:
        base, sub = "T", code.get("sub")

    value = code.get("value")
    if value is not None:
        unit = spec.get("unit")
        if unit is None:
            if sym.value is None or " " not in sym.value:
                raise SystemExit(f"{sym.key}: no sample unit to take from "
                                 f"{sym.value!r}, but the example states a "
                                 f"value. Give the entry a `unit`.")
            unit = sym.value.split(" ", 1)[1]
        value = f"{value} {unit}"
    # The same rule `layout` applies: a bare letter with no number and no
    # subscript states nothing, so it is left out rather than drawn.
    name = S.sym_text(base, sub) if base and (value or sub) else None
    return symbols.card(sym, fluid=True, user=code.get("label"), name=name,
                        value=value)


def entry(key, name, spec, figure=""):
    """One dictionary entry: the name, the drawing, the meaning, an example.

    The name comes first and the drawing second. A reader scanning for a
    symbol they have seen elsewhere is matching the picture; a reader looking
    one up is matching the name, and that is the more common way in.

    An entry with no glyph still gets a plate, empty and outlined in dashes.
    The alternative is a full-width row whose text starts where every other
    row's picture starts, and the empty frame happens to be the honest
    illustration anyway.
    """
    plate = (f"<figure>{figure}</figure>" if figure
             else '<figure class="none"><span>draws nothing</span></figure>')
    return (
        f'<article class="entry" id="sym-{key}">'
        f"<h3>{html.escape(name)}</h3>"
        + plate
        + f'<div class="entry-body"><p>{spec["what"]}</p>'
        f'<p class="example"><b>Example:</b> {spec["use"]}</p>'
        + written_as(spec)
        + "</div></article>")


def group(title, keys, by_key):
    """One titled group of entries, in the library's own order.

    The heading and its opening line ride together in a sticky block, so
    whichever group a reader is in stays named at the top of the window until
    the next one takes over. That is what replaced the badge on every entry:
    the question "what am I looking at" is answered continuously rather than
    nineteen times.
    """
    body = [f'<section id="grp-{_slug(title)}">'
            f'<div class="section-head"><h2>{html.escape(title)}</h2>'
            f'<p class="lede">{LEDES[title]}</p></div>']
    for key in keys:
        sym = by_key[key]
        body.append(entry(key, sym.name, ENTRIES[key],
                          plate(sym, ENTRIES[key])))
    if title == "Nodes":
        body.append(entry(CORNER["key"], CORNER["name"], CORNER))
    body.append("</section>")
    return "".join(body)


def _slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def index(by_key):
    """Contents, as one table per category, side by side.

    It does two jobs at once on purpose. Nineteen entries is past the point
    where a reader can be expected to scroll for one, and the three words the
    whole page is organised around have to be defined somewhere — so the
    definition sits on the panel whose symbols it covers, which is where a
    reader is already looking when the question occurs to them.

    Categories are read off each entry's own `where`, not off a second list of
    group titles, so regrouping `symbols.GROUPS` cannot leave this behind.
    """
    order = [k for _, keys in symbols.GROUPS for k in keys]
    order.append(CORNER["key"])
    specs = dict(ENTRIES, **{CORNER["key"]: CORNER})
    names = dict({k: by_key[k].name for k in by_key},
                 **{CORNER["key"]: CORNER["name"]})

    out = ['<nav class="index" aria-label="Contents">']
    for where in CATEGORIES:
        label, _, definition = WHERE[where]
        keys = [k for k in order if specs[k]["where"] == where]
        links = "".join(f'<li><a href="#sym-{k}">{html.escape(names[k])}</a>'
                        f"</li>" for k in keys)
        wide = " wide" if len(keys) > 6 else ""
        out.append(f'<div class="cat{wide}"><h4>{label}</h4>'
                   f'<p class="def">{definition}</p><ul>{links}</ul></div>')
    out.append("</nav>")
    return "".join(out)


BANNER = "\n".join([
    "<!-- Generated by tools/gen_dictionary.py. Do not edit this file.",
    "     The prose lives in the generator, the page shell in",
    "     docs/dictionary.template.html, and every drawing comes from the",
    "     library itself. Run: python tools/gen_dictionary.py -->",
])


def build():
    by_key = {s.key: s for s in symbols.SYMBOLS}
    missing = sorted(set(by_key) - set(ENTRIES))
    if missing:
        raise SystemExit(
            "tools/gen_dictionary.py has no entry for: " + ", ".join(missing)
            + "\nA new symbol needs a meaning and an example written for it.")
    extra = sorted(set(ENTRIES) - set(by_key))
    if extra:
        raise SystemExit("entries for symbols that no longer exist: "
                         + ", ".join(extra))

    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("{{VERSION}}", __version__)
    page = page.replace("{{STACK}}", theme.STACK)
    page = page.replace("{{FACES}}",
                        "".join(theme.font_face(f)
                                for f in ("regular", "italic", "semibold")))
    page = page.replace("<!DOCTYPE html>", "<!DOCTYPE html>\n" + BANNER, 1)
    page = page.replace("{{INDEX}}", index(by_key))
    page = page.replace("{{ENTRIES}}",
                        "\n".join(group(t, k, by_key)
                                  for t, k in symbols.GROUPS))
    return page


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="exit non-zero if the page is out of date")
    args = ap.parse_args(argv)

    fresh = build()
    if args.check:
        current = PAGE.read_text(encoding="utf-8") if PAGE.exists() else ""
        if current != fresh:
            print("Dictionary.html is stale; run tools/gen_dictionary.py")
            return 1
        print("Dictionary.html is up to date")
        return 0
    with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
        f.write(fresh)
    n = len(symbols.SYMBOLS) + 1
    print(f"{n} entries -> {PAGE} ({len(fresh):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
