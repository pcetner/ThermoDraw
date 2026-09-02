# Industrial furnace wall, steady state

Draw this thermal network as a ThermoDraw diagram.

## The system

A section of the side wall of a gas-fired reheat furnace, running at
temperature, per square metre of wall.

- The **furnace interior** is held at **1200 C** by the burners.
- The flame and the hot gas load the inner face radiatively. That load is
  quoted the way a furnace designer quotes it, as a **heat flux of
  18 W/cm2** on the refractory face.
- The wall is built up from the inside out. First **three courses of
  identical firebrick**, laid one behind the other. Each course is
  **0.06 K/W**, and the three together carry **3000 W**.
- Behind the brick is the **brick to board interface**, at **660 C**.
- Then a layer of **ceramic fibre board**, **0.18 K/W**.
- The **steel shell** on the outside is at **120 C**.
- The shell loses heat to the shop two ways at once, and both matter:
  **natural convection** off the plate at **0.05 K/W**, and **radiation**
  to the surrounding shop at **0.075 K/W**.
- The **shop air** is at **30 C**.

There is no thermal mass in this picture. The furnace has been at temperature
for two days.

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
python -m thermodraw check    examples/gallery/07-furnace/wall.json
python -m thermodraw describe examples/gallery/07-furnace/wall.json
python -m thermodraw render   examples/gallery/07-furnace/wall.json -o examples/gallery/07-furnace/wall.svg
```

Write the diagram to `examples/gallery/07-furnace/wall.json`.

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

Append to `examples/gallery/07-furnace/rounds.md` **as you go**, one section per
round: the exact `check` output, and for each finding whether the remedy it
named cleared it when applied literally. Do not write this up at the end from
memory.

Write `examples/gallery/07-furnace/findings.md` at the end, covering:

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
