# Roof-mounted photovoltaic module at noon

Draw this thermal network as a ThermoDraw diagram.

## The system

One framed silicon module on a flat commercial roof, clear sky, light wind,
in steady state at solar noon.

- Of the sunlight the module absorbs, **900 W** ends up as heat in the
  **cell layer**. (The electrical output has already been taken off this
  number; 900 W is the heat, not the irradiance.)
- The **cell layer** runs at **65 C**.
- The glass front radiates to the sky. The path is **0.2 K/W** and it carries
  **275 W**. The **effective sky temperature** is **10 C**.
- Wind over the glass carries away **600 W** by convection, a path of
  **0.05 K/W**. The **ambient air** is at **35 C**.
- The rest goes out the back. Through the **encapsulant and backsheet**,
  **0.4 K/W**, to the **backsheet** at **55 C**.
- The module is held down by **four identical mounting clips**, side by side.
  Each clip is **1.6 K/W**.
- The **roof deck** under the module is at **45 C**.

The module is mounted at a tilt. Nothing in the drawing has to be tilted, but
the reader should be able to tell the sky path from the roof path at a glance.

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
python -m thermodraw check    examples/gallery/15-pv/array.json
python -m thermodraw describe examples/gallery/15-pv/array.json
python -m thermodraw render   examples/gallery/15-pv/array.json -o examples/gallery/15-pv/array.svg
```

Write the diagram to `examples/gallery/15-pv/array.json`.

**Give no node `at`.** Leave `at` off every node, and leave `via`, and `at` on
a branch or a source, off as well: the library places a chain of nodes for
you. If it refuses the file, it names one node. Give that node `at`, and
`via` to the branches that leave it sideways, and nothing else; then carry
on. Record in `rounds.md` whether it refused, what it said, and what you did.

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

Append to `examples/gallery/15-pv/rounds.md` **as you go**, one section per
round: the exact `check` output, and for each finding whether the remedy it
named cleared it when applied literally. Do not write this up at the end from
memory.

Write `examples/gallery/15-pv/findings.md` at the end, covering:

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
7. **Whether the coordinates the library chose were ones you would have
   chosen.** Say what you would have moved, and whether you did.

Be blunt and specific. This is a test of the documentation and the library,
not of you. A clean diagram with an honest list of what it could not say is a
better result than a clean diagram alone.
