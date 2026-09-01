# Liquid-helium dewar with a two-stage pulse-tube cryocooler

Draw this thermal network as a ThermoDraw diagram.

## The system

A superconducting magnet in a cryostat, cooled by a two-stage pulse-tube
cryocooler. Three nested temperature levels.

- The **vacuum vessel** is the outer boundary at **300 K**, held there by the
  laboratory.
- A **radiation shield** sits at **40 K** between the vessel and the cold mass.
- The **cold mass** - the magnet itself - is at **4.2 K**, with a heat capacity
  of **900 J/K**.
- **MLI between the vessel and the shield** passes **0.9 W** by radiation;
  that path is **289 K/W**.
- **MLI between the shield and the cold mass** passes **0.02 W** by radiation;
  **1790 K/W**.
- **G10 support struts** hold the shield off the vessel by conduction,
  **433 K/W**, carrying **0.6 W**. A second set holds the cold mass off the
  shield, **716 K/W**, carrying **0.05 W**.
- **High-temperature superconducting current leads** run from the vessel down
  to the shield. They conduct **1720 K/W**, and they also generate **1.2 W** of
  Joule heating that is deposited at the shield.
- **Instrumentation wiring** adds a further **0.15 W** conducted to the cold
  mass from the shield, **239 K/W**.
- The cryocooler removes heat actively at both stages: **stage 1 removes 35 W
  at the shield**, and **stage 2 removes 1.5 W at the cold mass**. This is heat
  being taken away, not arriving.


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
cd "C:/Users/Peter Cetner/Documents/GitHub/ThermoDraw"
PYTHONPATH=src python -m thermodraw check    examples/gallery/03-cryogenic/dewar.json
PYTHONPATH=src python -m thermodraw describe examples/gallery/03-cryogenic/dewar.json
PYTHONPATH=src python -m thermodraw render   examples/gallery/03-cryogenic/dewar.json -o examples/gallery/03-cryogenic/dewar.svg
```

Write the diagram to `examples/gallery/03-cryogenic/dewar.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/03-cryogenic/rounds.md` **as you go**, one section per round: the exact
`check` output, and for each finding whether the remedy it named cleared it
when applied literally. Do not write this up at the end from memory.

Write `examples/gallery/03-cryogenic/findings.md` at the end, covering:

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
