# EV battery module on a liquid cold plate

Draw this thermal network as a ThermoDraw diagram.

## The system

One module of an electric-vehicle traction battery, at the end of a sustained
fast charge, in steady state.

- The module holds **eight prismatic cells**. Each dissipates **25 W** of
  ohmic and entropic heat at this current.
- The hottest point is the **cell core**, at **108 C**.
- Heat leaves the core through the **jelly roll and out to the can floor**,
  a conduction path of **0.24 K/W**. That path carries the module's whole
  **200 W**.
- The **can floor** sits at **60 C**.
- The cans are pressed onto the cold plate through a **compressible thermal
  pad**. That is a contact resistance of **0.10 K/W**.
- The **cold plate** wall is at **40 C**.
- Inside the plate, **milled microchannels** carry the coolant. The wall to
  fluid convection is **0.05 K/W**.
- The **coolant film** is at **30 C**.
- The **pumped glycol loop** carries the **200 W** away to the chiller. The
  **chiller supply** is held at **25 C**.
- Two thermal masses matter when the charge current steps: the **cells**,
  **4200 J/K**, and the **cold plate**, **1800 J/K**. Both are referred to
  the chiller supply.

## How to work

Your only documentation is `docs/schema.md` in this repository. Read that, and
this brief, and nothing else.

Do **not** read anything under `src/`, and do not read `CLAUDE.md`,
`README.md`, `CHANGELOG.md`, anything under `tests/`, or any other file under
`examples/`. Do not open an existing `.json` diagram. If you find yourself
wanting to, that is exactly the gap this exercise is measuring - write it down
in your findings and carry on from the schema alone.

Work from the repository root, and use the **Bash** tool (Git Bash), not
PowerShell, for these. `PYTHONIOENCODING=utf-8` is not optional: without it a
Windows console prints some of the output as backslash-u escapes, and two
readers of the last run had to re-capture theirs.

```
cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src PYTHONIOENCODING=utf-8
python -m thermodraw check    examples/gallery/06-battery/pack.json
python -m thermodraw describe examples/gallery/06-battery/pack.json
python -m thermodraw render   examples/gallery/06-battery/pack.json -o examples/gallery/06-battery/pack.svg
```

Write the diagram to `examples/gallery/06-battery/pack.json`.

Iterate until `check` exits 0 with no errors and no warnings. Notes are advice
and need not be cleared, but say why if you leave one standing. **Apply the
remedy each finding names, literally, before trying anything else** - whether
those remedies actually work is one of the things being measured. Do not open
a browser, and do not render an image in order to look at it.

Run `check --physics` on the finished diagram and paste its output into
`rounds.md` exactly as it came, whatever it says. Do not adjust a number from
this brief to make that output quieter: the values are the brief's, and
whether they agree with each other is one of the things being measured.

Render the SVG once it is clean.

## What to record

Append to `examples/gallery/06-battery/rounds.md` **as you go**, one section per
round: the exact `check` output, and for each finding whether the remedy it
named cleared it when applied literally. Do not write this up at the end from
memory.

Write `examples/gallery/06-battery/findings.md` at the end, covering:

1. **Anything you could not express.** This matters most. Where the schema had
   no way to say something, record what you wanted, what you did instead, and
   how misleading the result is. Do **not** silently substitute something that
   looks similar - if you approximated, say so and say how badly.
2. **Where the documentation failed you** - missing, ambiguous, or wrong.
   Quote the sentence.
3. **What you had to guess at**, and whether the guess turned out right.
4. **Whether `describe` let you confirm the drawing was the one you meant**,
   and what it should have said that it did not.
5. **Whether `check --physics` was silent**, and if not, what it said.
6. **Features the library lacks**, ranked by what they cost you here.

Be blunt and specific. This is a test of the documentation and the library,
not of you. A clean diagram with an honest list of what it could not say is a
better result than a clean diagram alone.
