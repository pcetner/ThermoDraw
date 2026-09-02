# Subsea electronics bottle on the seabed

Draw this thermal network as a ThermoDraw diagram.

## The system

A one-atmosphere electronics pressure vessel on the seabed at 1800 m,
oil-filled, in steady state.

- A **power board** inside dissipates **60 W** from its converter stage. The
  board runs at **37 C**.
- The board is bolted to a **spreader flange**. The heat leaves a small
  footprint and enters a much larger one, and the path is quoted as
  **0.30 K/W** for the spreading. It carries the whole **60 W**.
- The **flange** is at **19 C**.
- From the flange a **vapour chamber** runs up the length of the bottle to
  the housing. It is very nearly isothermal — **0.02 K/W** — and it turns a
  corner on the way.
- At the top the heat crosses the **oil-filled gap** to the housing bore by
  convection, **0.08 K/W**.
- The **housing bore** is at **13 C**.
- The **housing wall to the sea** is quoted by the vendor as a single number
  covering the steel and the outside water film together: **0.15 K/W**. Which
  part is conduction and which is convection is not broken out anywhere, and
  the drawing should not pretend otherwise.
- The **seawater** at that depth is **4 C**.

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
python -m thermodraw check    examples/gallery/09-subsea/bottle.json
python -m thermodraw describe examples/gallery/09-subsea/bottle.json
python -m thermodraw render   examples/gallery/09-subsea/bottle.json -o examples/gallery/09-subsea/bottle.svg
```

Write the diagram to `examples/gallery/09-subsea/bottle.json`.

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

Append to `examples/gallery/09-subsea/rounds.md` **as you go**, one section per
round: the exact `check` output, and for each finding whether the remedy it
named cleared it when applied literally. Do not write this up at the end from
memory.

Write `examples/gallery/09-subsea/findings.md` at the end, covering:

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
