"""Regenerate the symbol dictionary.

    python tools/gen_dictionary.py

Dictionary.html is the page you hand someone who has never drawn a thermal
network: every symbol, what it means in plain words, and one short scenario
saying when to reach for it.

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
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from thermodraw import __version__, symbols, theme  # noqa: E402

TEMPLATE = ROOT / "docs" / "dictionary.template.html"
PAGE = ROOT / "Dictionary.html"

# What each symbol says, when to use it, and how it is written.
#
#   role  where it goes, and the `kind` that selects it
#   what  the meaning, in the fewest sentences that are still true
#   use   one concrete scenario, deliberately short
#   code  the minimal JSON, so the reader can go straight from here to a file
ENTRIES = {
    "free": dict(
        role='Node &middot; <code>"kind": "free"</code> (the default)',
        what="A place in the network that has a temperature, with nothing "
             "holding it there. Its temperature is whatever the paths meeting "
             "at it settle on, which usually makes it the thing the model "
             "exists to find. Most nodes are free ones.",
        use="The junction temperature at the top of a die stack.",
        code='{"id": "j", "label": "Junction", "sub": "j", "value": "112"}'),
    "fixed": dict(
        role='Node &middot; <code>"kind": "fixed"</code>',
        what="A temperature imposed from outside, which nothing the network "
             "does can change. The wire runs down into a hatched wall, the "
             "drafting mark for a boundary: heat may cross it in either "
             "direction, at any rate, without moving the number.",
        use="The still air a heatsink rejects into.",
        code='{"id": "amb", "kind": "fixed", "label": "Still air", '
             '"sub": "amb", "value": "40"}'),
    "break": dict(
        role='Node &middot; <code>"kind": "break"</code>',
        what="A boundary the network touches mechanically but not thermally. "
             "It is the fixed node with its connecting stub taken away, and "
             "the visible gap is the entire statement: nothing crosses here. "
             "There is no heat path, so usually no temperature to state "
             "either, and the label stands alone.",
        use="A chassis the board is bolted to through insulating standoffs.",
        code='{"id": "mnt", "kind": "break", "label": "Mounting standoff"}'),
    "phase": dict(
        role='Node &middot; <code>"kind": "phase"</code>',
        what="A temperature held constant by a change of phase rather than by "
             "a boundary, so it takes the constant-temperature marking — two "
             "short rules beneath — and no wall. While the phase change "
             "lasts, heat crosses it at no temperature rise at all, which is "
             "the whole reason two-phase cooling exists.",
        use="Coolant boiling at saturation in an immersion tank.",
        code='{"id": "sat", "kind": "phase", "label": "Boiling surface", '
             '"sub": "sat", "value": "49"}'),

    "cond": dict(
        role='Path &middot; <code>"kind": "cond"</code>',
        what="Heat crossing solid material. Section hatching is the drafting "
             "convention for solid material, so the interior says exactly "
             "what is being crossed. The resistance is thickness over "
             "conductivity times area, and it is linear in temperature.",
        use="The die-attach layer between a chip and its lead frame.",
        code='{"from": "j", "to": "c", "kind": "cond", '
             '"label": "Die attach", "value": "0.35"}'),
    "conv": dict(
        role='Path &middot; <code>"kind": "conv"</code>',
        what="Heat leaving a surface into a moving fluid. Streamlines say a "
             "fluid is passing, and they turn with the block because flow "
             "along the path is what they mean. The resistance is one over "
             "the film coefficient times the wetted area.",
        use="A heatsink giving up heat to the air a fan pushes over it.",
        code='{"from": "s", "to": "amb", "kind": "conv", '
             '"label": "Sink &rarr; Ambient", "value": "1.80"}'),
    "rad": dict(
        role='Path &middot; <code>"kind": "rad"</code>',
        what="Heat leaving a surface as thermal radiation. The box is empty "
             "and the wave arrows cross it unaided, because radiation needs "
             "no medium. The dashed outline is redundant coding for the one "
             "path that is not linear in temperature — it goes as the fourth "
             "power — so a reader notices before trusting any superposition.",
        use="A spacecraft radiator panel rejecting to deep space.",
        code='{"from": "case", "to": "space", "kind": "rad", '
             '"label": "Case &rarr; Ambient", "value": "6.40"}'),
    "contact": dict(
        role='Path &middot; <code>"kind": "contact"</code>',
        what="The resistance of two solids pressed together, which is real "
             "and often dominant. Each half is hatched in the opposite "
             "direction with a seam between them — the drafting convention "
             "for two parts meeting in section. Without the opposing hatch it "
             "would read as one solid block.",
        use="Thermal grease between a package lid and a heatsink base.",
        code='{"from": "c", "to": "s", "kind": "contact", '
             '"label": "Grease", "value": "0.15"}'),

    "spread": dict(
        role='Path &middot; <code>"kind": "spread"</code>',
        what="Conduction into a cross-section that grows as the heat goes: a "
             "small source on a much larger plate. The hatching fans from a "
             "point rather than running parallel, because the area available "
             "increases along the path. Drawn as plain conduction it would "
             "assert one-dimensional flow, which is exactly what spreading "
             "is not.",
        use="A one-millimetre laser diode on a copper-tungsten submount.",
        code='{"from": "d", "to": "sub", "kind": "spread", '
             '"label": "CuW submount", "value": "0.15"}'),
    "pipe": dict(
        role='Path &middot; <code>"kind": "pipe"</code>',
        what="A near-isothermal link: a heat pipe or a vapour chamber. Vapour "
             "travels out along one face and condensate returns along the "
             "other, which is what the opposed arrows show. It still takes a "
             "resistance, because the real device has a small one; what it "
             "stops doing is wearing solid-conduction hatching on a two-phase "
             "part.",
        use="The heat pipe carrying load from a CPU to a remote fin stack.",
        code='{"from": "evap", "to": "cnd", "kind": "pipe", '
             '"label": "Heat pipe", "value": "0.0018"}'),
    "mixed": dict(
        role='Path &middot; <code>"kind": "mixed"</code>',
        what="One number covering more than one mechanism, or a mechanism you "
             "do not wish to name. The interior is empty, and in a vocabulary "
             "where the texture names the mechanism that emptiness is a "
             "statement rather than an omission. It is the only path whose "
             "subscript you set, because it is the only one the library "
             "cannot name for you.",
        use="A window quoted by its manufacturer as a single figure.",
        code='{"from": "in", "to": "out", "kind": "mixed", '
             '"sub": "window", "label": "Double glazing", "value": "0.31"}'),
    "cap": dict(
        role='Path &middot; <code>"kind": "cap"</code>',
        what="Thermal mass: the heat a body takes in as its temperature "
             "rises, in joules per kelvin. It stores rather than conducts, so "
             "it hangs from a node down to the reference rail instead of "
             "lying between two places. It matters only while things are "
             "changing — at steady state it carries nothing.",
        use="The heat capacity of a heatsink during a power step.",
        code='{"from": "j", "to": "rail", "kind": "cap", "label": "Die", '
             '"sub": "j", "value": "0.9"}'),

    "flow-branch": dict(
        role='Path &middot; <code>"kind": "flow"</code>',
        what="Heat moved bodily from one place to another because a fluid is "
             "moving or something is pumping it. It carries a rate, not a "
             "resistance. Chevrons rather than a box: the interior of a box "
             "states what the heat is crossing, and here nothing is crossed — "
             "the medium is going. It is the only directed path, so "
             "<code>from</code> and <code>to</code> are the way the heat "
             "travels, and <code>angle</code> is refused on one.",
        use="Coolant carrying 3.2 kW out of a rack to the facility loop.",
        code='{"from": "rack", "to": "cdu", "kind": "flow", '
             '"label": "Technical water", "value": "3.2"}'),
    "break-branch": dict(
        role='Path &middot; <code>"kind": "break"</code>',
        what="A mechanical connection that carries no heat, drawn as an open "
             "circuit. Deliberately neither a plain wire, which would say "
             "heat flows, nor a resistance, which would say how much. It "
             "names no quantity, so it takes no value and gets no second line "
             "of text.",
        use="The nylon standoff holding a board off its chassis.",
        code='{"from": "pcb", "to": "case", "kind": "break", '
             '"label": "Nylon standoff"}'),

    "diss": dict(
        role='Source &middot; <code>"kind": "diss"</code>',
        what="Heat appearing at a node because something there generates it. "
             "An arrow rather than a two-terminal element, because "
             "dissipation does not travel to the node from anywhere — it "
             "simply appears. It always points inward.",
        use="Switching and conduction losses in a power transistor.",
        code='{"to": "j", "kind": "diss", "label": "Switching loss", '
             '"sub": "d", "value": "45"}'),
    "radin": dict(
        role='Source &middot; <code>"kind": "radin"</code>',
        what="Radiation arriving from outside the network, drawn with the "
             "same wave arrow the radiation path uses. Reach for it where the "
             "incoming radiation is a known load rather than something the "
             "model should solve for. Being radiation <em>arriving</em>, it "
             "also always points inward.",
        use="Solar gain on a spacecraft panel.",
        code='{"to": "panel", "kind": "radin", "label": "Solar gain", '
             '"sub": "sol", "value": "3.2"}'),
    "flow": dict(
        role='Source &middot; <code>"kind": "flow"</code>',
        what="A stated heat rate crossing into or out of one node: an "
             "annotation on the network for where you know the number and do "
             "not need to draw the path. Give it <code>to</code> for heat "
             "arriving or <code>from</code> for heat leaving, and the arrow "
             "follows what you said.",
        use="38 W leaving an enclosure through its exhaust.",
        code='{"from": "encl", "kind": "flow", "value": "38"}'),
    "flux": dict(
        role='Source &middot; <code>"kind": "flux"</code>',
        what="A heat rate per unit area entering or leaving a surface. "
             "Several arrows stand against a hatched band, because a flux is "
             "spread over an area and has no single line of action to borrow "
             "the heat-flow arrow. It is measured in its own quantity, "
             "<em>q&#8243;</em>, and never shares units with a heat rate.",
        use="1.4 W/cm&sup2; leaving the top surface of a die.",
        code='{"from": "die", "kind": "flux", "label": "Die surface", '
             '"value": "1.4"}'),
}

# The one node kind that draws nothing, and so has no `Symbol` and no card.
# It belongs in a dictionary all the same: a reader who does not find it here
# will assume it does not exist, and two acceptance readers reached for it
# when what they wanted was a labelled free node.
CORNER = dict(
    name="Corner",
    role='Node &middot; <code>"kind": "corner"</code> &middot; draws nothing',
    what="A coordinate, not a place. It draws no circle, takes no label and "
         "has no temperature; it exists only so a wire has somewhere to bend. "
         "If what you want is a junction that is named but has no temperature "
         "of its own, use a free node with a label and no value instead.",
    use="Routing a return path around a component rather than through it.",
    code='{"id": "k1", "kind": "corner", "at": [420, 260]}')

# Each group's opening line. Keyed on the group titles in `symbols.GROUPS`, so
# a regrouping there shows up here as a KeyError rather than as silent prose
# attached to the wrong set of symbols.
LEDES = {
    "Nodes":
        "A place in the network, and what — if anything — holds its "
        "temperature there.",
    "Paths: what the heat crosses":
        "Four mechanisms, four interiors. The texture names what the heat is "
        "passing through, so the outline never has to change shape.",
    "Paths: shape, phase, mechanism, storage":
        "Paths that the four mechanisms cannot say on their own: where the "
        "cross-section grows, where a phase change carries the load, where "
        "the mechanism is combined, and where nothing flows but heat is held.",
    "Paths that carry a rate, or carry nothing":
        "Boxes resist; these two do not. One carries heat bodily from one "
        "place to another, and the other carries none at all.",
    "Sources":
        "Heat crossing into or out of a single node from outside the network. "
        "An arrow, never a circled element: a source appears at a place, it "
        "is not a thing heat travels through.",
}


def entry(name, spec, figure=""):
    """One dictionary entry: the drawing, the meaning, the scenario.

    An entry with no glyph still gets a plate, empty and outlined in dashes.
    The alternative is a full-width row whose text starts where every other
    row's picture starts, and the empty frame happens to be the honest
    illustration anyway.
    """
    plate = (f"<figure>{figure}</figure>" if figure
             else '<figure class="none"><span>draws nothing</span></figure>')
    return (
        '<div class="entry">' + plate
        + f"<div><h3>{html.escape(name)}</h3>"
        f'<p class="meta">{spec["role"]}</p></div>'
        f'<p>{spec["what"]}</p>'
        f'<div><p class="use"><b>Use it for</b> &mdash; {spec["use"]}</p>'
        f'<pre>{spec["code"]}</pre></div>'
        "</div>")


def group(title, keys, by_key):
    """One titled group of entries, in the library's own order."""
    body = [f"<section><h2>{html.escape(title)}</h2>"
            f'<p class="lede">{LEDES[title]}</p>']
    for key in keys:
        sym = by_key[key]
        body.append(entry(sym.name, ENTRIES[key], symbols.card(sym,
                                                               fluid=True)))
    if title == "Nodes":
        body.append(entry(CORNER["name"], CORNER))
    body.append("</section>")
    return "".join(body)


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
            + "\nA new symbol needs a meaning and a scenario written for it.")
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
