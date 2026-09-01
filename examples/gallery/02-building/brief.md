# Two-zone house with a ground-coupled slab

Draw this thermal network as a ThermoDraw diagram.

## The system

A two-storey house on a winter design day. Outdoor air is **-4 C** and the
effective sky temperature is **-15 C**.

- **Ground-floor zone air** at **21 C**, with an air thermal mass of
  **2.1 MJ/K**. **Upper-floor zone air** at **23 C**, **1.8 MJ/K**.
- **Internal gains** (occupants, lighting, appliances) put **600 W** into the
  ground-floor zone.
- The **external wall** is a layered assembly, and each layer is its own
  conduction path in series: gypsum board **0.011 K/W**, mineral wool
  **0.185 K/W**, OSB sheathing **0.014 K/W**, brick outer leaf **0.008 K/W**.
  The outer face then meets outdoor air by convection, **0.012 K/W**.
- A **steel lintel** above the windows bridges the insulation, running in
  parallel with the whole wall assembly at **0.42 K/W** from zone air to
  outdoor air. It is the dominant heat loss per unit area.
- A **double-glazed window**: conduction and convection through the glazing at
  **0.31 K/W** to outdoor air, plus **850 W** of solar gain arriving through it
  into the ground-floor zone.
- **Infiltration**: air leaks in at 0.5 air changes per hour, carrying outdoor
  air straight into the ground-floor zone. This is worth **185 W** of heat loss
  at the design condition. It is not a conduction or convection resistance -
  it is air physically moving from outside to inside.
- The **ground-floor slab** conducts down into deep ground held at **10 C**,
  **0.6 K/W**.
- **Between the two zones**: the intermediate floor conducts at **0.09 K/W**,
  and an **open stairwell** carries warm air upward, worth **240 W** of
  transport from the lower zone to the upper.
- The **roof** at **8 C** loses heat two ways in parallel: convection to
  outdoor air **0.14 K/W**, and radiation to the cold sky **0.22 K/W**.


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
PYTHONPATH=src python -m thermodraw check    examples/gallery/02-building/house.json
PYTHONPATH=src python -m thermodraw describe examples/gallery/02-building/house.json
PYTHONPATH=src python -m thermodraw render   examples/gallery/02-building/house.json -o examples/gallery/02-building/house.svg
```

Write the diagram to `examples/gallery/02-building/house.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/02-building/rounds.md` **as you go**, one section per round: the exact
`check` output, and for each finding whether the remedy it named cleared it
when applied literally. Do not write this up at the end from memory.

Write `examples/gallery/02-building/findings.md` at the end, covering:

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
