# High-power laser diode bar on a microchannel cooler

Draw this thermal network as a ThermoDraw diagram.

## The system

A conduction-cooled laser diode bar, where the heat comes off a very small area
and has to spread out before it can be removed.

- The **diode bar** is a 10 mm x 100 um active stripe. It emits 120 W of light
  and dumps **80 W** as waste heat. The **junction** is at **65 C**.
- The waste heat leaves the junction as a **heat flux of 800 W/cm2** through
  the emitting face - an extremely high flux over a very small area.
- The junction conducts down through the semiconductor to the **AuSn solder
  joint** at **58 C**: **0.0875 K/W**.
- The solder joint meets a **CuW submount** at **51 C**. The contact resistance
  is **0.0125 K/W**.
- Inside the submount the heat **spreads** from that 100 um-wide line source out
  to the full 10 mm width. This spreading is worth **0.15 K/W**, and it is the
  single largest resistance in the stack. It is not a plain one-dimensional
  conduction path: the cross-section the heat flows through grows as it goes.
- The submount is joined to a **copper microchannel cooler** by an **indium**
  layer, **0.008 K/W** contact.
- The **microchannel cooler body** is at **41 C**, and water flowing through the
  channels at **18 C** takes the heat by convection: **0.045 K/W**.
- Beneath the cooler sits a **thermoelectric (Peltier) cooler**. It **pumps
  60 W out of the cooler body**, moving heat from the cold side to the hot side
  against the temperature gradient, and consumes **40 W** of electrical power in
  doing so - so **100 W** leaves its hot face.
- The TEC hot face is at **48 C** and meets a **baseplate**, which loses heat by
  convection to **ambient air at 25 C** at **0.23 K/W**.


## How to work

Your only documentation is `docs/schema.md` in this repository. Read that, and
this brief, and nothing else.

Do **not** read anything under `src/`, and do not read `CLAUDE.md`,
`README.md`, `CHANGELOG.md`, anything under `tests/`, or any other file under
`examples/`. Do not open an existing `.json` diagram. If you find yourself
wanting to, that is exactly the gap this exercise is measuring - write it down
in your findings and carry on from the schema alone.

Work from the repository root, and use the **Bash** tool (Git Bash), not
PowerShell, for these:

```
cd "$(git rev-parse --show-toplevel)"
PYTHONPATH=src python -m thermodraw check    examples/gallery/05-laser-diode/diode.json
PYTHONPATH=src python -m thermodraw describe examples/gallery/05-laser-diode/diode.json
PYTHONPATH=src python -m thermodraw render   examples/gallery/05-laser-diode/diode.json -o examples/gallery/05-laser-diode/diode.svg
```

Write the diagram to `examples/gallery/05-laser-diode/diode.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/05-laser-diode/rounds.md` **as you go**, one section per round: the exact
`check` output, and for each finding whether the remedy it named cleared it
when applied literally. Do not write this up at the end from memory.

Write `examples/gallery/05-laser-diode/findings.md` at the end, covering:

1. **Anything you could not express.** This matters most. Where the schema had
   no way to say something, record what you wanted, what you did instead, and
   how misleading the result is. Do **not** silently substitute something that
   looks similar - if you approximated, say so and say how badly.
2. **Where the documentation failed you** - missing, ambiguous, or wrong.
   Quote the sentence.
3. **What you had to guess at**, and whether the guess turned out right.
4. **Whether `describe` let you confirm the drawing was the one you meant**,
   and what it should have said that it did not.
5. **Features the library lacks**, ranked by what they cost you here.

Be blunt and specific. This is a test of the documentation and the library,
not of you. A clean diagram with an honest list of what it could not say is a
better result than a clean diagram alone.
