# GEO communications satellite payload panel

Draw this thermal network as a ThermoDraw diagram.

## The system

A north-facing equipment panel on a geostationary communications satellite,
in sunlight (not eclipse).

- A **travelling-wave tube amplifier (TWTA)** bolted to the panel dissipates
  **220 W** of waste heat. Its baseplate sits at **78 C**.
- The TWTA baseplate meets the panel through a **filled silicone gasket**,
  a contact resistance of **0.05 K/W**.
- The **equipment panel** is aluminium honeycomb at **45 C**. It has a thermal
  mass of **18 kJ/K**, which matters when the satellite enters eclipse.
- **Constant-conductance heat pipes** are embedded in the panel and carry the
  heat out to the radiator. A heat pipe is very nearly isothermal: the
  temperature drop along it is about **0.4 K** at this load.
- The **radiator** is at **22 C**. Its outer face is a second-surface mirror
  with emissivity 0.80, radiating to **deep space at -269 C**. That radiative
  path is **1.15 K/W**.
- The rest of the panel is covered by a **multi-layer insulation (MLI)
  blanket** with an effective emissivity of 0.02, also facing deep space. That
  path is **26 K/W** - nearly but not perfectly insulating.
- **Solar flux** falls on the radiator at grazing incidence: **45 W** absorbed.
- **Earth infrared** onto the panel adds **12 W**.
- A **survival heater** on the panel supplies **30 W** when the thermostat
  calls for it. It is off in this condition, but must appear on the diagram.


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
PYTHONPATH=src python -m thermodraw check    examples/gallery/01-spacecraft/satellite.json
PYTHONPATH=src python -m thermodraw describe examples/gallery/01-spacecraft/satellite.json
PYTHONPATH=src python -m thermodraw render   examples/gallery/01-spacecraft/satellite.json -o examples/gallery/01-spacecraft/satellite.svg
```

Write the diagram to `examples/gallery/01-spacecraft/satellite.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/01-spacecraft/rounds.md` **as you go**, one section per round: the exact
`check` output, and for each finding whether the remedy it named cleared it
when applied literally. Do not write this up at the end from memory.

Write `examples/gallery/01-spacecraft/findings.md` at the end, covering:

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
