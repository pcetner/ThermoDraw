# Session transcript — 09-subsea

Verbatim transcript of the Claude Code session that produced `bottle.json`,
`bottle.svg`, `rounds.md` and `findings.md` in this folder.

- **Model:** `claude-opus-5` (Opus 5)
- **Harness:** Claude Code 2.1.255, `claude-desktop` entrypoint, Windows 10.0.19045
- **Session id:** `8844b698-922a-4052-9b9a-6806d2e1af6f`
- **Working directory:** repository root, branch `master`
- **Source:** the session's own JSONL log, converted mechanically — nothing
  written from memory, nothing edited

Assistant reasoning blocks are included and marked as such. Tool calls show
their full input; tool results are shown as returned. The log is appended to
as the session runs, so it ends partway through the final turn — the turn that
generated this very file. That cut-off is the only thing missing.

---

## User — turn 1

<sub>2026-09-02 23:04:39.785Z</sub>

Read examples/gallery/09-subsea/brief.md and do exactly what it says.

---

### Assistant

I'll read the brief first.

### Tool call — `Bash`

*Read the subsea brief*

```bash
cat "examples/gallery/09-subsea/brief.md"
```

**Result:**

````
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
````

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*List repo root and schema size*

```bash
cd "$(git rev-parse --show-toplevel)" && ls && echo "---" && wc -l docs/schema.md
```

**Result:**

```
LICENSE
NOTICE
START-HERE.txt
docs/
examples/
pyproject.toml
src/
---
571 docs/schema.md
```

### Tool call — `Bash`

*Read schema doc*

```bash
cd "$(git rev-parse --show-toplevel)" && cat docs/schema.md
```

**Result:**

````
# The diagram schema

A ThermoDraw diagram is plain data. This page is the whole format; it is
written to be pasted into a prompt.

```python
from thermodraw import Diagram, layout, render, theme

svg = theme.with_variables(render(layout(Diagram.from_json(text))))
```

From Python, `render` alone emits CSS custom properties with no fallback, so
pass its output through `theme` before saving it: `with_variables` for the
web, `bake` for Word, slides and rasterisers. Without one of them the file
draws nothing. The `thermodraw render` **command** does this for you — its
file draws as written — and so do `page` and a builder's `.svg()`. This
paragraph is about the function, and every reader who met it before the
command grepped their own SVG to find out.

## Shape

```jsonc
{
  "title":  "optional, not drawn",
  "size":   [1042, 431],
  "units":  {"R": "K/W", "C": "J/K", "T": "°C", "P": "W", "q": "W", "q″": "W/cm²"},
  "nodes":    [ ... ],
  "branches": [ ... ],
  "sources":  [ ... ],
  "rail":     { ... }
}
```

`nodes` is the only key that has to be there. `rail` is optional — a
steady-state diagram with no capacitance has nothing to hang on it — and so
are `sources`, `branches`, `size` and `title`.

Units are fixed per diagram and given once per quantity, so a diagram cannot
mix `K/W` with `mK/W`. Values are written without their unit; the unit is
appended from this table. Only give the keys you use — a diagram with no
capacitance needs no `C`, and one with no text needs no `units` at all. A
value whose quantity has no entry here is refused, so that a number never
reaches the page without its unit.

The quantities are `R`, `C`, `T`, `P`, `q` and `q″`. `radin` and `flow` are
both powers and share `q`; a heat **flux** is per unit area, so it is measured
in something else and reads `q″`.

That last key is the letter `q` followed by **U+2033 DOUBLE PRIME** (″). It is
one character, and it is not two apostrophes, not two quote marks, and not
`"`. Getting it wrong is a JSON syntax error at best and an unknown-quantity
error at worst; the error lists the keys it accepts, printing the character
as `q\u2033` where the terminal cannot show it.

`size` is `[width, height]`, and you almost never want it. Left out, the
canvas is measured from the drawing and the margins come out equal on all four
sides. Set it and the canvas is fixed instead, which is how ink ends up off the
page — the two findings `off-canvas` and `frame-off-centre` exist only for
diagrams that set it.

Every `value` is a **string**, not a number: you get exactly the digits you
typed, so `"2.10"` stays `2.10` and does not become `2.1`.

Coordinates are SVG user units with the origin at the top left, so **y
increases downward** — a node at `y: 372` is below one at `y: 150`. That is
why the reference rail, which runs along the bottom, has the largest `y`.

## Nodes

A place with a temperature.

```jsonc
{"id": "j", "label": "Junction", "sub": "j", "value": "112", "at": [200, 150]}
```

| field | meaning |
|---|---|
| `id` | referred to by branches and sources |
| `kind` | `free` (default), `fixed`, `break`, `phase`, `corner` |
| `label` | the words above the symbol — the top line, always. Optional: a node with none draws its `T` line alone, or nothing, and still counts as a label placed |
| `sub` | subscript on `T`. Identity: you choose it, it names a place |
| `value` | temperature, unit appended from `units.T` |
| `at` | `[x, y]`. **Required** until the network layer lands |
| `angle` | turns the node's label frame, in degrees. It moves the label and nothing else |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes |

`phase` is a node whose temperature a phase change holds rather than a
boundary: the constant-temperature marking, two short rules beneath, and
no wall. Condensation at 3.2 kW with no temperature drop is one node, not
two surfaces with a path between them.

`fixed` draws the boundary wall and connects to it with a short stub. `break`
draws the same wall with no stub — the visible gap is the whole distinction,
and it is topological rather than decorative. `corner` draws nothing and
exists only to route a wire.

A node with **no `value` and no `sub`** draws its label alone and no `T` at
all. Interior junctions between series layers routinely have no temperature of
their own, and a lone italic `T` states nothing. Give it a `sub` and you get
`T_mid` with no number, which is what a symbolic diagram wants; give it
neither and the symbol is simply left out. Use `corner` only when you want no
label either.

A `break` has no temperature to state, so `sub` and `value` are usually left
off and the label alone is drawn. To tie one to the thing it is bolted to,
use a `break` **branch** — the same word for the same thing in the other
position.

The wall is always drawn flat below the node, at every orientation. `angle`
does not turn it, and neither does anything else; it decides which way the
label goes and nothing more. `"side": "down"` on a boundary node aims the
label at that node's own wall, and never prints on it: on a `fixed` node the
clearance already covers the wall, and on a `break`, whose wall stands
further off, the solver pushes the label the rest of the way. The `break`
case ends up snug against the wall, so prefer `up` or an `angle` there if you
want air around the text.

Reach for `angle` when a label wants to be somewhere `side` alone cannot put
it — an `"angle": 90` on an ambient node sends that label out to the
right rather than straight up, where a branch arriving from the left would
have crowded it.

A `fixed` node may sit anywhere. Putting an ambient node at the rail's
own `y` is where a diagram's cold end belongs, and not a sign that the
two are connected — nothing requires a boundary to be on the rail line.

## Branches

A path heat takes between two nodes.

```jsonc
{"from": "j", "to": "c", "kind": "cond", "label": "Die attach", "value": "0.35"}
```

| field | meaning |
|---|---|
| `from`, `to` | node ids, or the literal `"rail"` |
| `kind` | `cond`, `conv`, `rad`, `contact`, `spread`, `pipe`, `mixed`, `cap`, `flow`, `break` |
| `label` | the words above the box |
| `sub` | yours on the kinds whose subscript the library does not set: `cap`, where it names a place; `mixed`, where it names the mechanism; `flow`. Ignored on `break`, and overridden on every resistance kind |
| `value` | unit appended from `units.R` (`units.C` for `cap`, `units.q` for `flow`). Optional: a path with no number draws its label alone. Refused on `break` |
| `rate` | what this path actually carries. Drawn as `q = 12 W` on its own line, in `units.q`, under the resistance it presents. Needs `units.q`. Refused on `flow`, whose value already is a rate, and on `break`. On a `count`ed branch it is the whole group's, not per item. Stating it opts the branch into `rate-does-not-match` under `--physics` |
| `count` | how many identical ones there are |
| `arrangement` | `parallel` or `series`. Required with `count` |
| `via` | `[[x, y], ...]` waypoints, for a path that is not a straight line |
| `at` | where the box sits. Defaults to the middle of the longest run |
| `angle` | overrides the direction taken from the wire |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes. On a horizontal run only `up` and `down` are useful: `left` and `right` put the label along the wire, into the next thing on it |

`spread` is a path whose cross-section grows as the heat goes — hatching
that fans from a point rather than running parallel. `pipe` is a near
isothermal link, a heat pipe or a vapour chamber: it still takes a small
resistance, it just stops wearing solid-conduction hatching. `mixed` has no
texture at all, which in this vocabulary is not an absence but a statement:
the mechanism is combined or deliberately unstated. A window quoted as one
number for conduction *and* convection is `mixed`.

`flow` is the odd one. It carries a **rate**, not a resistance — heat moved
from one node to another because a fluid moves, or because something pumps
it. Drawn as chevrons in the line rather than as a box, because the interior
of a box says what the heat is crossing and here nothing is crossed. It is
the only **directed** branch: `from` and `to` are the way the heat goes, and
`angle` is refused on one, since turning the symbol would let the drawing
contradict the data. Route it with `via` instead.

The subscript on a resistance is **not** yours to set: `cond`, `conv`, `rad`,
`contact`, `spread` and `pipe` each carry their own, and they name the
physics. `mixed` is the exception, being the one kind whose mechanism the
library does not know. Which conduction path this is belongs in `label`, so
nothing is named twice. On a capacitance the subscript names a place, so
`sub` is yours; on `flow` it is yours too.

`"to": "rail"` drops straight down to the reference rail from wherever the
other end is. That is how thermal mass is hung off a transient model.

### Several of the same path

`count` says there are several identical ones, and the diagram draws them —
fanned out in `parallel`, or end to end in `series`.

```jsonc
{"from": "die", "to": "fluid", "kind": "cond", "value": "0.0275",
 "count": 8, "arrangement": "parallel"}
```

**`arrangement` is required, and never inferred.** Eight 0.0275 K/W paths are
0.0034 K/W in parallel and 0.22 K/W in series — a factor of sixty-four — so a
count on its own is a wrong answer waiting to be read.

The `value` is **per item**. `R_cond = 0.0275 K/W` with `8 in parallel` under
it means eight of that, not eight sharing it. The library does no arithmetic:
values are strings so `"2.10"` stays `2.10`, and folding a count would mean
parsing them as numbers.

A parallel group is drawn as a comb: a trunk out of each node, a riser square
across it, then one lane per copy. Right angles throughout.

More than three and the drawing **condenses**: two copies are drawn with an
ellipsis between them, taking the room of two rather than of sixteen. Both forms are in the file, and `thermodraw page` gives you a control
to swap between them, with the copies fading in from the middle outwards. Each
form carries its own label, so the text moves with the drawing it belongs to.

The canvas is sized for the *larger* form either way, so a condensed group
leaves the room its expansion will need. That is deliberate: expanding one
group then moves that group and nothing else on the page.

A repeated branch is drawn between its two nodes, so it cannot also take
`via`. A `series` group needs its nodes far enough apart to hold the whole
chain; `check` reports the overlap if they are not.

`break` is the odd one out: it draws an open circuit — wire, crossbar, gap,
crossbar, wire — for a mechanical connection that carries no heat, such as a
standoff or a mount. It names no quantity, so it takes **no `value` and no
`rate`**, and one given either is refused. `sub` is accepted and does
nothing, there being no symbol for it to sit under. Everything else on the
table works on it. The same word is also a node `kind`, and it means the same thing there:
a break at a boundary rather than between two nodes.

## Sources

Heat crossing into or out of a node. An arrow, not a two-terminal element.

```jsonc
{"to": "j", "kind": "diss", "label": "Switching loss", "value": "45", "sub": "d"}
```

Give it **`to`** for heat arriving at that node, or **`from`** for heat
leaving it — one or the other, exactly as a branch takes both. The arrow
points whichever way you said.

`kind` is `diss` (electrical or internal dissipation), `radin` (radiation
arriving), `flow` (a heat rate crossing the boundary) or `flux` (a rate per
unit area).

| kind | drawn as | symbol | unit taken from | may use `from` |
|---|---|---|---|---|
| `diss` | arrow | `P` | `units.P` | no |
| `radin` | wavy arrow | `q` | `units.q` | no |
| `flow` | arrow | `q` | `units.q` | **yes** |
| `flux` | several arrows leaving a hatched surface | `q″` | `units["q″"]` | **yes** |

A source also takes `count`, for several identical ones. They simply add, so
there is no `arrangement` to state; the label reads `each of 8` under a
value that is, as on a branch, per item.

Only `flow` and `flux` may point away — they annotate heat crossing a
boundary, in either direction. `diss` is dissipation
*appearing* at a node rather than travelling to it, and `radin` is radiation
*arriving* — for radiation leaving, draw a `rad` branch to a boundary node,
which is the thing that actually carries it.

`sub` names the source, as it does on a node; it is yours to choose. `radin`
and `flow` share `units.q` because both are powers. `flux` has its own, so a
diagram can carry a heat rate in `W` and a heat flux in `W/cm²` at once.

`at` is the **centre of the symbol**, not its head or its tail, exactly as it
is on a branch. `angle` is the direction the arrow points, `0` being to the
right. A lead is drawn from the symbol to the node whichever you choose — and
the lead is a wire like any other: labels are pushed around it and symbols
can be reported as crossed by it, so a source moved further out has a longer
lead, and `at` decides what that lead runs past. Three of one reader's
findings were leads.

Leave `at` out and the source is placed along its own `angle`, about 40
units from the node — on the far side of the node for a `to`, so the arrow
arrives, and on the near side for a `from`, so it leaves. That is right for
one source on a node with a short label:
`{"from": "cell", "kind": "flux", "angle": 270}` puts a hatched face on top of
the cell with the arrows rising off it, and needs no coordinates. Two sources
on one node, or a wide label, want an explicit `at` on at least one of them;
left to themselves, two auto-placed sources on adjacent diagonals overlap.

`side` moves the label, as above.

## Rail

```jsonc
{"reference": "amb", "y": 372, "span": [200, 936]}
```

The reference the capacitances return to. `span` is optional and defaults to
the extent of the nodes.

`reference` must name a node that exists, and does nothing else — it does not
move the rail, route anything, or have to be a `fixed` node. It records which
node the rail *is*, for a reader and for a later version. `y` is what actually
places the line.

A branch naming `rail` as its `to` drops straight down from the other end,
meeting the line directly below that node. Give it `via` if you want it
somewhere else: waypoints work on a capacitance exactly as they do on any
other branch, which is how you free up the space directly under a node that
already has too much attached to it.

## A whole diagram

A body losing heat to still air by one path, with the dissipation that
puts it there:

```jsonc
{
  "units": {"R": "K/W", "T": "°C", "P": "W"},
  "nodes": [
    {"id": "a",   "label": "Body",      "sub": "a",   "value": "90", "at": [200, 150]},
    {"id": "amb", "kind": "fixed", "label": "Still air", "sub": "amb",
     "value": "25", "at": [520, 150]}
  ],
  "branches": [
    {"from": "a", "to": "amb", "kind": "cond", "label": "Mounting foot",
     "value": "0.5"}
  ],
  "sources": [
    {"to": "a", "kind": "diss", "label": "Dissipation", "value": "130",
     "sub": "d", "at": [60, 150]}
  ]
}
```

That is a whole file. Two nodes, one path, one source, and numbers that
close: 65 K over 0.5 K/W is the 130 W the source puts in.

## Coordinates

Every node needs `at` for now. The library places what you give it and works
out the wire runs, the label positions and the canvas size for itself.

Solving for coordinates you leave out is the network layer, which is not
built yet. It changes one stage — `layout` — and nothing in this schema. A
diagram written today keeps working; it just stops needing the numbers.

Until then, a workable habit: heat runs left to right, hottest node on the
left, the reference rail along the bottom. Space nodes about 220 apart and put
parallel paths 80 above and below the main line.

### Angles

`angle` appears on nodes, branches and sources, and it means a different thing
on each.

On a **branch** or a **source** it turns the symbol: a source at `angle` 0
points along +x, so its arrow travels left to right into the node, and
increasing the angle swings it clockwise, because y increases downward.

On a **node** it turns nothing that is drawn. It sets the direction of an
imaginary branch through that node, and the label goes to whichever side of
that line is the upper one:

| `angle` | label lands |
|---|---|
| `0` (default) | above |
| `45` | above and to the right |
| `90` | to the right |
| `135` | above and to the left |

Any value works, not just these. Two consequences are worth knowing before
you need them. The choice is **symmetric about 180°** — `180` puts the label
above just as `0` does, and `270` puts it right just as `90` does — because a
label is never set upside down. And `side` overrides `angle` entirely.

Notice what the table does not contain. Symmetry about 180° means a node's
label reaches above, left and right and **never below**; no `angle` sends it
down. `side: "down"` is the only thing that gets there, and it is safe even on
a boundary node, whose wall is below it.

Reach for `angle` when `side` runs out. `side` offers four directions, and a
node fanning three ways with a capacitance below it and a source coming in has
five attachments for four slots. Only `angle` reaches the diagonals.

Two more details are worth copying rather than rediscovering:

- **Leave a node sideways before turning — at both ends.** A `via` that goes
  straight up from a node puts a wire exactly where that node's label wants
  to sit, and the label steps out past it — ending up nearer the branch than
  the node it names. Turning at `x = 696` for a node at `x = 648` is about
  right: give the turn 40–90 units of clearance. The same is true of the
  end a branch *arrives* at. A parallel pair dropping straight down onto a
  node gets away with it only where that node has `angle: 90` and no other
  traffic; a node with three branches and a source on it does not, and one
  reader traced four findings to arriving that way.
- **A parallel pair needs `side`.** Both branches are horizontal, so both
  labels choose "up" and the lower one lands inside the loop. Set
  `"side": "up"` on the upper branch and `"side": "down"` on the lower one.
  Three branches between one pair of nodes cannot all be satisfied: a run
  has two useful sides, so two of three share one. Put the narrowest label
  on the shared side and leave the note.

Space labels, not symbols. A box is 84 wide, but `R_cond = 0.000877 K/W` is
over twice that, and it is the label that decides how far apart two nodes have
to be. A node's label counts too: centred on its node, it needs room between
the symbols on the runs either side, and `check` says so with both numbers
when it does not fit.

The label solver is not local. It places labels in order, each one avoiding
what is already there, and a label that cannot fit is pushed until it can. So
freeing one label can let the next travel a long way — one reader watched a
label cross a 1200-wide canvas onto a different branch after an unrelated
source moved. Expect a change at one node to move a label at another, and
read the whole report each round rather than the finding you were fixing.

## Checking a diagram

The two habits above are no longer advice. They are checks, and so are eight
other things that used to need a browser:

```bash
thermodraw check diagram.json
```

```
diagram.json: 11 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 2 s->amb and branch 3 s->amb run
      between the same two nodes and both labels went to the same side
      -> set `side` to "down" on branch 3 s->amb
```

"11 labels placed" is every node except `corner` ones, plus every branch and
every source — so it is the count you can work out from the file, and a
number lower than that means a label was dropped rather than moved. It exits
0 when clean, 1 on a warning or an error, and 2 when the file could not be
read or was not a diagram. A note is advice and does not fail the run — the
report above exits 0 — unless you pass `--strict`. `--json` for a machine,
`--quiet` for findings alone. From Python it is `check(diagram)`, returning a
report with `.ok`, `.findings` and `.text()`; a `DiagramBuilder` has `.check()`
beside `.svg()`.

| code | severity | what it means |
|---|---|---|
| `label-collision` | error | text printed over something else |
| `symbols-overlap` | error | two symbols in the same place |
| `off-canvas` | error | the drawing runs past a `size` you fixed |
| `network-in-pieces` | warning | some nodes have no path of branches to the rest |
| `nodes-too-close` | warning | two nodes closer than the labels on the run between them need, with both numbers |
| `label-adrift` | warning | a label shoved out past its own clearance to get around something, and now reads as belonging to that instead |
| `label-in-a-corridor` | warning | a label inside a loop of the network, close enough to both paths to belong to either |
| `wire-through-symbol` | warning | a route crossing a symbol on another branch |
| `frame-off-centre` | warning | the `size` you fixed leaves lopsided margins |
| `parallel-pair-same-side` | note | two branches between the same two nodes, both labelled on the same side |

Every finding names the schema field that fixes it. Two are worth knowing in
advance, because they are the ones a first draft hits:

- `label-adrift` almost always means a `via` rising straight out of a node.
  Move the turn sideways first — that is the habit above, and it is what the
  finding will tell you. When a node's own label is wider than the room
  between the symbols either side of it, the finding says so with both
  numbers and names the nodes to move apart, because moving either symbol
  cannot help. A remedy names only a field the element can take: a source
  and a repeated branch are never told to use `via`, and a straight branch
  is told to gain a waypoint rather than move one.
- `network-in-pieces` is the one to read carefully, because a severed network
  looks fine. A source has **one end**, so two `flow` or `flux` sources
  cannot join two nodes however suggestively you place them; heat carried
  from one node to another by a moving fluid is a `flow` **branch**, and this
  finding is what tells you the drawing did not say what you meant.
- `nodes-too-close` is the other half of that. Every finding names what is
  *nearest* the crowded label, and on a short run that is a wire — so if you
  are being told to move a `via` and it is not helping, look for this one: it
  names the two nodes, how far apart they are, and what their labels need.
- `parallel-pair-same-side` is a note rather than a warning because a
  well-drawn diagram can break it and be fine. Take it as a prompt to look, not an error.
  Its remedy names the branch and the side, derived from where the two
  labels landed; three or more branches between one pair get one note and
  no `side`, because none clears it.

Two things it does not check by default: whether the numbers are right, and
whether the network is the one you meant. It reports how the drawing reads,
not what it says.

Behind `--physics` — from Python, `check(diagram, physics=True)` — is a
prototype that asks the first of those, in the only form that needs no model
of anything: do the stated numbers agree with each other? At every `free`
node with a temperature, what arrives by sources and `flow` must leave by
resistances at `(T_here − T_there) / R`, with `count` folding a group the way
this page says a count folds, and a `corner` folded into the path through it.
Two codes, both warnings: `node-does-not-balance`, which lists every term so
you can see which one is off, and `rate-does-not-match`, for a branch whose
`rate` disagrees with what its ends imply. A fixed node is a reservoir and is
not asked; a `phase` node is holding latent heat this cannot see. A `free`
node is skipped when it has no temperature, when a **neighbour** has none —
which is what an interior junction drawn the way this page recommends does
to the nodes either side of it — when it carries a `flux` source, which has
no area, or when a value is not a number. Every skip is reported, as one
note per diagram: `physics-not-checked`, `checked 2 of 6 free nodes; not
checked: j (source 1 is a flux, which has no area); sm, cb (neighbour 'smb'
has no temperature); smb (it has no temperature)`. A diagram whose free
nodes were all checked gets no note. The units it reads are `R` in `K/W`,
`°C/W`, `C/W`, `mK/W` or `K/kW`, and `P` and `q` in `W`, `kW` or `mW`; any
other is the same note with nothing checked, not silence. `C` is never read
(steady state) and `T` is used only as differences, so `K` and `°C` both
work and `kJ/K` costs nothing.

It is opt-in, and stays so: a sketch with placeholder numbers is a diagram
too, and would fire at every node it has. Ask for it when you believe the
numbers. When it was written every diagram in this repository fired it: their
temperatures were not the results of their own power and resistances.

## Seeing what got drawn

`check` grades the drawing. It cannot tell you the drawing is the one you
meant, and a clean report is not the same as a correct diagram:

```bash
thermodraw describe diagram.json
```

```
diagram.json: canvas 582 x 135, 4 labels

placements: ground x1, node x2, symbol/cond x1, symbol/diss x1, wire x4

network:
  a --cond-- amb
  source 0 --diss-> a

nodes:
  a              free     at (200, 150)
  amb            fixed    at (520, 150)

elements:
  branch 0 a->amb        symbol/cond     (360, 150)        above          95x33   Mounting foot | R_cond = 0.5 K/W
  source 0 -> a          symbol/diss     (60, 150)         above          71x33   Dissipation | P_d = 130 W
  node 'a'               node            (200, 150)        above          65x33   Body | T_a = 90 °C
  node 'amb'             node            (520, 150)        above          78x33   Still air | T_amb = 25 °C
```

That is the real output for the file above, not an abridgement. Element
counts against what you wrote, the canvas you will get, where each symbol
sits and which way it is turned, what each label reads, and which way it
went. Three marks say where the solver had to work: `flipped` means the label
tried its automatic side, found it blocked, and took the opposite one;
`pushed N` means it was moved `N` units out along its side to get clear of
something, and `check` reports it as adrift past 8; `OVERLAPS` means the push
loop gave up and the label is printed over something — always a
`label-collision`. Two branches between one pair of nodes both going
"above" is the parallel pair `check` notes, visible directly rather than
only graded.

The **network** block is which nodes are joined to which, and by what, and
where the heat comes in and goes out.

Two mechanisms on one line, as with `s --conv/rad-- amb`, are two branches
between the same pair. A `flow` branch is written with its direction, `cb
--flow-> th`, so one written backwards reads differently. A repeated group
says how many, `j --cond x8 parallel-- ihs`. Sources have their own lines,
heat reading left to right: `source 0 --diss-> j` arrives, `th --flow->
source 1` leaves. If the drawing is in more than one piece it says so here
as well as in `network-in-pieces`.

An element carrying no text at all — a `break` branch with no `label` — still
gets a row, marked `(no label)`. `rail.reference` is documentary and does
nothing, so this is the only place it can be checked against what you meant.

It always exits 0: it reports, it does not judge. `--json` for a machine. From
Python it is `describe(diagram)`, returning a `.text()` and a `.to_dict()`.

## A page instead of a picture

`thermodraw render` writes the static SVG that Word, a README and every
rasteriser need, and that is the canonical output. What a standalone `.svg`
cannot do is let a reader expand a condensed group — not because SVG is
static, but because a *file* is.

```bash
thermodraw page diagram.json -o diagram.html
```

The same SVG, inline, in one self-contained document with the fonts embedded
and nothing fetched from anywhere, plus a control for each repeated group.
Both forms are already in the markup with stable ids, so the control flips two
`display` attributes; it does not rebuild anything. The script lives in the
page and never in the SVG.
````

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*List the target directory*

```bash
cd "$(git rev-parse --show-toplevel)" && ls examples/gallery/09-subsea/
```

**Result:**

```
brief.md
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Write first draft and check*

```bash
cd "$(git rev-parse --show-toplevel)" && cat > examples/gallery/09-subsea/bottle.json <<'EOF'
{
  "title": "Subsea electronics bottle on the seabed",
  "units": {"R": "K/W", "T": "°C", "P": "W", "q": "W"},
  "nodes": [
    {"id": "board", "label": "Power board", "sub": "b", "value": "37", "at": [200, 320]},
    {"id": "flange", "label": "Spreader flange", "sub": "f", "value": "19", "at": [480, 320]},
    {"id": "vct", "label": "Vapour chamber top", "at": [760, 160]},
    {"id": "bore", "label": "Housing bore", "sub": "h", "value": "13", "at": [1000, 160]},
    {"id": "sea", "kind": "fixed", "label": "Seawater", "sub": "sea", "value": "4", "at": [1280, 160]}
  ],
  "branches": [
    {"from": "board", "to": "flange", "kind": "spread", "label": "Board to flange", "value": "0.30", "rate": "60"},
    {"from": "flange", "to": "vct", "kind": "pipe", "label": "Vapour chamber", "value": "0.02",
     "via": [[560, 320], [560, 160]]},
    {"from": "vct", "to": "bore", "kind": "conv", "label": "Oil-filled gap", "value": "0.08"},
    {"from": "bore", "to": "sea", "kind": "mixed", "label": "Housing wall to sea", "sub": "cond+conv", "value": "0.15"}
  ],
  "sources": [
    {"to": "board", "kind": "diss", "label": "Converter stage", "value": "60", "sub": "d", "at": [60, 320]}
  ]
}
EOF
export PYTHONPATH=src PYTHONIOENCODING=utf-8
python -m thermodraw check examples/gallery/09-subsea/bottle.json; echo "EXIT=$?"
```

**Result:**

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Run describe and physics check*

```bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && python -m thermodraw describe examples/gallery/09-subsea/bottle.json; echo "EXIT=$?"; echo "=== PHYSICS ==="; python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json; echo "EXIT=$?"
```

**Result:**

```
examples/gallery/09-subsea/bottle.json: canvas 1344 x 286, 10 labels

placements: ground x1, node x5, symbol/conv x1, symbol/diss x1,
            symbol/mixed x1, symbol/pipe x1, symbol/spread x1, wire x10

network:
  board --spread-- flange
  flange --pipe-- vct
  vct --conv-- bore
  bore --mixed-- sea
  source 0 --diss-> board

nodes:
  board          free     at (200, 320)
  flange         free     at (480, 320)
  vct            free     at (760, 160)
  bore           free     at (1000, 160)
  sea            fixed    at (1280, 160)

elements:
  branch 0 board->flange symbol/spread   (340, 320)        above         111x50   Board to flange | R_spread = 0.30 K/W | q = 60 W
  branch 1 flange->vct   symbol/pipe     (660, 160)        above         100x33   Vapour chamber | R_pipe = 0.02 K/W
  branch 2 vct->bore     symbol/conv     (880, 160)        above         102x33   Oil-filled gap | R_conv = 0.08 K/W
  branch 3 bore->sea     symbol/mixed    (1140, 160)       above         127x33   Housing wall to sea | R_cond+conv = 0.15 K/W
  source 0 -> board      symbol/diss     (60, 320)         above          85x33   Converter stage | P_d = 60 W
  node 'board'           node            (200, 320)        above          68x33   Power board | T_b = 37 °C
  node 'flange'          node            (480, 320)        above          85x33   Spreader flange | T_f = 19 °C
  node 'vct'             node            (760, 160)        below         109x15   flipped   Vapour chamber top
  node 'bore'            node            (1000, 160)       above          70x33   Housing bore | T_h = 13 °C
  node 'sea'             node            (1280, 160)       above          66x33   Seawater | T_sea = 4 °C
EXIT=0
=== PHYSICS ===
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Assistant

Clean on the first round. Recording it, then rendering.

### Tool call — `Bash`

*Write rounds.md with exact outputs*

````bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && D=examples/gallery/09-subsea && python -m thermodraw check $D/bottle.json > /tmp/c1.txt 2>&1; echo "EXIT=$?" >> /tmp/c1.txt; python -m thermodraw check --physics $D/bottle.json > /tmp/p1.txt 2>&1; echo "EXIT=$?" >> /tmp/p1.txt
{
  echo '# Rounds'
  echo
  echo 'One section per round, written as it happened.'
  echo
  echo '## Round 1 — first draft, straight from `docs/schema.md`'
  echo
  echo 'The diagram written before any checking: five nodes (board, flange, an'
  echo 'untitled vapour-chamber-top junction with no temperature, housing bore,'
  echo 'seawater), four branches (`spread`, `pipe` with a two-waypoint corner,'
  echo '`conv`, `mixed`), one `diss` source.'
  echo
  echo '```'
  cat /tmp/c1.txt
  echo '```'
  echo
  echo '**Findings: none.** 0 errors, 0 warnings, 0 notes on the first run, so no'
  echo 'remedy was applied and there is nothing to report about whether a remedy'
  echo 'worked. 10 labels placed = 5 nodes + 4 branches + 1 source, which is the'
  echo 'count the file predicts, so nothing was dropped.'
  echo
  echo 'Two habits from the schema were followed in the draft rather than'
  echo 'discovered by `check`, and they are probably why round 1 was clean:'
  echo
  echo '- the `pipe` branch leaves `flange` sideways (`via` `[560, 320]`) before'
  echo '  turning up to `[560, 160]`, instead of rising straight out of the node;'
  echo '- nodes are 280 apart on the runs, not the 220 the schema suggests as a'
  echo '  minimum, because `Housing wall to sea | R_cond+conv = 0.15 K/W` is a'
  echo '  127-wide label.'
  echo
  echo 'No second round was needed. There is no round 2.'
  echo
  echo '## `check --physics` on the finished diagram'
  echo
  echo 'Pasted exactly as it came, unedited:'
  echo
  echo '```'
  cat /tmp/p1.txt
  echo '```'
  echo
  echo 'The note is left standing deliberately. Its remedy is "give the node, or'
  echo 'its neighbour, a `value`", and the node in question is the top of the'
  echo 'vapour chamber, whose temperature the brief does not state. Applying that'
  echo 'remedy literally would mean inventing a number and putting it on the'
  echo 'drawing as if it had been measured. The brief says not to adjust a number'
  echo 'to make this output quieter, so the note stays and the three unchecked'
  echo 'nodes are unchecked.'
  echo
  echo 'For the record, the numbers do close by hand, all the way down the chain,'
  echo 'at 60 W throughout:'
  echo
  echo '```'
  echo 'board  37.0'
  echo '  spread 0.30 x 60 = 18.0 K'
  echo 'flange 19.0   (stated 19)'
  echo '  pipe   0.02 x 60 =  1.2 K'
  echo 'vct    17.8   (not stated anywhere)'
  echo '  conv   0.08 x 60 =  4.8 K'
  echo 'bore   13.0   (stated 13)'
  echo '  mixed  0.15 x 60 =  9.0 K'
  echo 'sea     4.0   (stated 4)'
  echo '```'
  echo
  echo 'So the brief`s numbers agree with each other exactly. `--physics` checked'
  echo '1 of the 4 free nodes and could not see any of that.'
} > $D/rounds.md
cat $D/rounds.md
````

**Result:**

````
# Rounds

One section per round, written as it happened.

## Round 1 — first draft, straight from `docs/schema.md`

The diagram written before any checking: five nodes (board, flange, an
untitled vapour-chamber-top junction with no temperature, housing bore,
seawater), four branches (`spread`, `pipe` with a two-waypoint corner,
`conv`, `mixed`), one `diss` source.

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

**Findings: none.** 0 errors, 0 warnings, 0 notes on the first run, so no
remedy was applied and there is nothing to report about whether a remedy
worked. 10 labels placed = 5 nodes + 4 branches + 1 source, which is the
count the file predicts, so nothing was dropped.

Two habits from the schema were followed in the draft rather than
discovered by `check`, and they are probably why round 1 was clean:

- the `pipe` branch leaves `flange` sideways (`via` `[560, 320]`) before
  turning up to `[560, 160]`, instead of rising straight out of the node;
- nodes are 280 apart on the runs, not the 220 the schema suggests as a
  minimum, because `Housing wall to sea | R_cond+conv = 0.15 K/W` is a
  127-wide label.

No second round was needed. There is no round 2.

## `check --physics` on the finished diagram

Pasted exactly as it came, unedited:

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
```

The note is left standing deliberately. Its remedy is "give the node, or
its neighbour, a `value`", and the node in question is the top of the
vapour chamber, whose temperature the brief does not state. Applying that
remedy literally would mean inventing a number and putting it on the
drawing as if it had been measured. The brief says not to adjust a number
to make this output quieter, so the note stays and the three unchecked
nodes are unchecked.

For the record, the numbers do close by hand, all the way down the chain,
at 60 W throughout:

```
board  37.0
  spread 0.30 x 60 = 18.0 K
flange 19.0   (stated 19)
  pipe   0.02 x 60 =  1.2 K
vct    17.8   (not stated anywhere)
  conv   0.08 x 60 =  4.8 K
bore   13.0   (stated 13)
  mixed  0.15 x 60 =  9.0 K
sea     4.0   (stated 4)
```

So the brief`s numbers agree with each other exactly. `--physics` checked
1 of the 4 free nodes and could not see any of that.
````

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Render the SVG*

```bash
cd "$(git rev-parse --show-toplevel)" && sed -i "s/brief\`s numbers/brief's numbers/" examples/gallery/09-subsea/rounds.md && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && python -m thermodraw render examples/gallery/09-subsea/bottle.json -o examples/gallery/09-subsea/bottle.svg; echo "EXIT=$?"; ls -l examples/gallery/09-subsea/
```

**Result:**

```
examples\gallery\09-subsea\bottle.svg (9,937 bytes)
EXIT=0
total 28
-rw-r--r-- 1 Peter Cetner 197121 1194 Sep  2 19:05 bottle.json
-rw-r--r-- 1 Peter Cetner 197121 9980 Sep  2 19:06 bottle.svg
-rw-r--r-- 1 Peter Cetner 197121 4323 Sep  2 19:02 brief.md
-rw-r--r-- 1 Peter Cetner 197121 2574 Sep  2 19:06 rounds.md
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Assistant

Let me verify one documentation gap in a scratch copy before writing it up.

### Tool call — `Bash`

*Test what mixed prints with no sub*

```bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && S="/c/Users/PETERC~1/AppData/Local/Temp/claude/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f/scratchpad" && mkdir -p "$S" && python - <<'PY' > "$S/t.json"
import json,io,sys
d=json.load(open("examples/gallery/09-subsea/bottle.json",encoding="utf-8"))
for b in d["branches"]:
    if b["kind"]=="mixed": b.pop("sub")
sys.stdout.write(json.dumps(d,ensure_ascii=False))
PY
python -m thermodraw describe "$S/t.json" | grep -E "branch 3|labels"
```

**Result:**

```
C:/Users/PETERC~1/AppData/Local/Temp/claude/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f/scratchpad/t.json: canvas 1344 x 286, 10 labels
  branch 3 bore->sea     symbol/mixed    (1140, 160)       above         104x33   Housing wall to sea | R = 0.15 K/W
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Probe why the vct label flipped*

```bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && S="/c/Users/PETERC~1/AppData/Local/Temp/claude/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f/scratchpad" && python - <<'PY' > "$S/u.json"
import json,sys
d=json.load(open("examples/gallery/09-subsea/bottle.json",encoding="utf-8"))
for n in d["nodes"]:
    if n["id"]=="vct": n["side"]="up"
sys.stdout.write(json.dumps(d,ensure_ascii=False))
PY
python -m thermodraw check "$S/u.json"; echo "EXIT=$?"; python -m thermodraw describe "$S/u.json" | grep -E "node 'vct'"
```

**Result:**

```
C:/Users/PETERC~1/AppData/Local/Temp/claude/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f/scratchpad/u.json: 10 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] node 'vct': its label was pushed 44 past its own clearance to get around branch 1 flange->vct and now sits nearer that than the thing it names  -> move branch 1 flange->vct along its branch with `at`, or set `side` to "down"
EXIT=1
  node 'vct'             node            (760, 160)        above         109x15   pushed 44   Vapour chamber top
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Assistant

Confirmed the cause. Now writing findings.

### Tool call — `Bash`

*Write findings.md*

````bash
cd "$(git rev-parse --show-toplevel)" && cat > examples/gallery/09-subsea/findings.md <<'MDEOF'
# Findings — 09-subsea

Written from `docs/schema.md` and `brief.md` alone. The diagram was clean on
the first `check`, so almost nothing here is about fighting the layout
engine; it is about what the format could not be made to say.

---

## 1. What I could not express

This is the part that matters, so it is longest.

### 1.1 "It turns a corner on the way" — the corner is not in the data

The brief says the vapour chamber "runs up the length of the bottle to the
housing" and "turns a corner on the way". I drew that with waypoints:

```json
"via": [[560, 320], [560, 160]]
```

**That is a routing instruction, not a physical claim.** `via` says where the
wire goes on the page. It cannot distinguish "this component physically turns
a corner" from "the author needed to get from the lower row of the drawing to
the upper row". In this diagram both are true at once, which makes it look
like it worked, but nothing in the file records that the corner is a property
of the hardware. Delete the `via`, move `vct` down to y=320, and the diagram
says exactly the same thing about the vapour chamber while drawing a straight
line.

**How misleading:** mildly. Nothing false is drawn. But the reader cannot
recover the fact from the picture, and a second reader redrawing this from
the JSON would have no reason to keep the bend.

### 1.2 The whole physical setting is unsayable

"On the seabed at 1800 m, oil-filled, one atmosphere inside, steady state."

There is **no annotation, caption, or note element** in the schema. There are
nodes, branches, sources and a rail, and every one of them is a thing heat is
at or passes through. `title` exists and is documented as `"optional, not
drawn"`. So the depth, the internal pressure, and the fact that this is
subsea at all have exactly two possible homes: a node or branch `label`,
where they would masquerade as the name of a component, or nowhere.

I put them nowhere. **The rendered SVG is a generic five-node series chain.**
It would be a pixel-identical correct drawing of a box on a bench wired to a
bucket of 4 °C water. Everything that made this a subsea problem is gone.

I did not silently smuggle it into a label, and this is the single largest
thing the format cost here.

### 1.3 "Oil-filled gap" is prose in a label, not data

The convection branch is `"label": "Oil-filled gap"`. There is no `medium` or
`fluid` field on a `conv` branch, so the working fluid is a string a human
reads, not something the file knows. Same class of problem as 1.2, smaller.

### 1.4 I had to invent a node, and give it a name the brief never used

The brief describes flange → vapour chamber → oil gap → bore. Two resistances
in series need a node between them, so there is a place in the diagram the
brief never names: the top of the vapour chamber, where it meets the oil gap.

I created it as `vct`, labelled **"Vapour chamber top"**, with no `value` and
no `sub` — which `docs/schema.md` explicitly endorses ("Interior junctions
between series layers routinely have no temperature of their own").

**But the words "Vapour chamber top" are mine, not the brief's, and they are
printed on the drawing.** That is the only text on the page the brief did not
supply. The alternative was `kind: "corner"`, which "draws nothing and exists
only to route a wire" — but this junction is not a routing artefact, it is a
real thermal location where one mechanism hands off to another, and calling
it a `corner` would have understated it. I took the label. Flagging it
because a reader could reasonably assume the name came from the source.

The cost of this node is not cosmetic — see §5.

### 1.5 "It carries the whole 60 W" — sayable once, and then misleading

The brief states the throughput for the spreading path only. I put `"rate":
"60"` on that branch and on no other, because that is what the brief states.

The result reads as though the spread path's throughput is known and the
other three paths' throughput is not. **That is false.** It is a series chain
with one source; every branch carries 60 W by inspection. There is no way to
say "and everything downstream of this carries the same" once. The two
available options were:

- state it once (what I did) — implies the rest are unknown;
- repeat `"rate": "60"` on all four — implies four independent statements of
  throughput where the brief made one, and opts all four branches into
  `rate-does-not-match`.

Neither is honest. I chose the one that adds no numbers the brief did not
give.

### 1.6 "Should not pretend otherwise" — `mixed` is right, its subscript is a judgement call

> "Which part is conduction and which is convection is not broken out
> anywhere, and the drawing should not pretend otherwise."

`mixed` is exactly this and the schema says so almost verbatim: "A window
quoted as one number for conduction *and* convection is `mixed`." **This is
the schema's best moment in the whole exercise** — the vocabulary had a word
for the thing the brief was worried about.

The subscript was the judgement call. On `mixed`, `sub` is mine and "names
the mechanism". I wrote `"sub": "cond+conv"`, which renders as:

```
Housing wall to sea | R_cond+conv = 0.15 K/W
```

I tested the alternative (omitting `sub`), which renders a bare
`R = 0.15 K/W`. I kept `cond+conv` on the grounds that what is *unknown* here
is the split, not the mechanisms — both are present, they are lumped, and no
share is assigned. A reader who parses `R_cond+conv` as "R_cond + R_conv" is
not misled: it is their sum, with both addends unstated.

**Residual risk, stated plainly:** if a reader takes the subscript as a claim
that the two parts *were* separated somewhere, that is wrong. A bare `R`
would be immune to that reading and would say less. This is the one place I
could have gone either way.

### 1.7 No provenance

The brief twice distinguishes vendor-quoted numbers ("the path is quoted as",
"quoted by the vendor as a single number") from the temperatures. There is no
field for where a number came from. All eight numbers render identically.
Low cost here; it is a real absence.

---

## 2. Where the documentation failed me

`docs/schema.md` is unusually good — round 1 was clean, which is mostly its
doing. Three real gaps:

**2.1 It never says what a `mixed` branch prints with no `sub`.** The text is:

> "`mixed`, where it names the mechanism"

It says the field is mine and what it is for. It does not say whether
omitting it yields a bare `R`, drops the subscript row, or is refused. Since
§1.6 was the brief's central worry, I needed to know, and the only way to
find out was to write a throwaway file and run `describe` on it. One sentence
would have saved that.

**2.2 `describe`'s `flipped` mark names the symptom and not the cause.** The
doc says:

> "`flipped` means the label tried its automatic side, found it blocked, and
> took the opposite one"

`describe` reported `node 'vct' ... below ... flipped`. Nothing in the output
says *what* blocked it, and from the coordinates alone there is nothing
obviously above that node. I only established the cause by forcing
`"side": "up"` in a scratch copy, which produced:

> `warning: [label-adrift] node 'vct': its label was pushed 44 past its own
> clearance to get around branch 1 flange->vct`

So it was the vapour chamber's own branch label. The solver did the right
thing silently and I could not tell that from `describe`. `check` names
blockers; `describe` does not. That asymmetry is undocumented, and it means
`flipped` is unactionable information — you know the solver worked, not what
it worked around.

**2.3 Nothing says there is no annotation element.** §1.2 is a hole you find
by searching for a section that is not there. The doc lists what exists; it
never says "a diagram carries no free text besides labels", so I spent time
confirming a negative.

**2.4 (minor, and the doc gets this right)** The `PYTHONIOENCODING` and the
`render` vs `theme` warnings both read as scar tissue from earlier readers,
and both were accurate. I used the CLI, so the theme trap never fired. The
`q″` U+2033 warning was three paragraphs for a key I did not need. That
proportion is a bit off, but it is a fair guess at where people fall in.

---

## 3. What I guessed, and whether the guess held

| Guess | Held? |
|---|---|
| An interior junction with no `value` and no `sub` is the right way to draw the vapour-chamber/oil-gap handoff | **Yes** — doc endorses it explicitly. But it cost §5. |
| `sub: "cond+conv"` is a legal subscript string and renders literally | **Yes** — `R_cond+conv` |
| 280 units between nodes (doc suggests "about 220") | **Yes** — no `nodes-too-close`. 220 would probably have failed on the 127-wide `Housing wall to sea` label |
| 80 units of sideways clearance before the `via` turn (doc says 40–90) | **Yes** — no `label-adrift` |
| Omitting `rail` entirely is legal for a steady-state diagram with no capacitance | **Yes** — doc says so, and `describe` still lists `ground x1` |
| `diss` source with explicit `at` left of the node and default `angle` points into it | **Yes** — copied the doc's worked example |
| `pipe` is the right kind for a vapour chamber | **Yes** — doc names vapour chambers specifically |
| Nothing needed `side` overrides | **Yes** — the one flip resolved itself correctly |

Nothing I guessed turned out wrong. That is a compliment to the doc, not to
me — every one of those was answered somewhere in it.

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Largely yes.** The network block is the right tool and did the job:

```
board --spread-- flange
flange --pipe-- vct
vct --conv-- bore
bore --mixed-- sea
source 0 --diss-> board
```

That is the chain from the brief, in order, with the mechanism on each link
and the dissipation arriving at the right end. It confirmed the topology, and
`symbol/mixed` in the placements line confirmed that §1.6 landed.

**What it should have said and did not:**

1. **Nothing about `via`.** The single feature I was least confident in — the
   corner — is the one thing `describe` is silent on. It gives the symbol
   centre `(660, 160)`, from which a determined reader can infer that branch 1
   is not a straight line between `(480, 320)` and `(760, 160)`, but the
   waypoints are never listed and the branch is never marked as routed. A
   corner at the wrong height would produce identical `describe` output. **If
   you cannot open the SVG, `via` is unverifiable.**
2. **`flipped` without a blocker.** See §2.2.
3. **Throughput is not in the network block.** `q = 60 W` appears inside
   branch 0's label text and nowhere else. Fine by accident here; in a diagram
   with several `rate`s you would be reading them out of label strings.
4. It does not echo `title`, which is documented as undrawn but is still the
   only place the diagram's subject is written down.

---

## 5. Was `check --physics` silent?

**No.** Exact output is in `rounds.md`. It said:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange,
bore (neighbour 'vct' has no temperature); vct (it has no temperature)
```

It found **no disagreement** — no `node-does-not-balance`, no
`rate-does-not-match`. It checked the board: 60 W in from the source, and
`(37 − 19) / 0.30` = 60 W out. That balances exactly.

**But it only checked one node of four, and this is the sharpest finding in
this report.** The numbers in the brief agree with each other perfectly, all
the way down, at 60 W throughout:

```
board  37.0  →(0.30)→ flange 19.0 →(0.02)→ vct 17.8 →(0.08)→ bore 13.0 →(0.15)→ sea 4.0
        18.0 K          1.2 K            4.8 K            9.0 K
```

`--physics` verified one link of four. It was blinded by `vct` — the
untemperatured interior junction that the **same document** tells you to
draw ("Interior junctions between series layers routinely have no temperature
of their own"), and whose consequence the `--physics` section then describes
as normal ("which is what an interior junction drawn the way this page
recommends does to the nodes either side of it").

So the recommended modelling idiom and the numeric checker are in direct
conflict, and the doc knows it and shrugs. Two resistances in series carrying
a known current through an unknown intermediate temperature is arithmetically
determinate — `(T_flange − T_bore) / (R_pipe + R_conv)` is 60 W and needs no
model of anything. The checker gives up instead.

**The note is left standing.** Its remedy is "give the node, or its
neighbour, a `value`". Applying that literally means inventing 17.8 °C and
printing it on the drawing as though it had been measured. The brief forbids
adjusting numbers to quieten this output, so it stays.

---

## 6. Features the library lacks, ranked by what they cost here

1. **`--physics` cannot propagate through an untemperatured junction.**
   Cost: 3 of 4 nodes unverified, on a diagram whose numbers are exactly
   consistent, and a note in the shipped output that cannot honestly be
   cleared. It defeats itself on the idiom its own documentation recommends.
2. **No annotation / caption / free-text element.** Cost: 1800 m, one
   atmosphere, oil-filled and steady-state are all absent from the drawing.
   The picture is context-free. (§1.2)
3. **`via` is routing only; no way to say a path physically bends.** Cost:
   "it turns a corner on the way" is not recoverable from the file. (§1.1)
4. **`describe` does not report `via` waypoints.** Cost: the one thing I most
   wanted to verify without opening the SVG is the one thing it will not tell
   me. (§4.1)
5. **`describe`'s `flipped` does not name the blocker**, though `check`'s
   warnings do. Cost: one scratch-file experiment to learn something the tool
   already knew. (§2.2)
6. **No way to state throughput for a chain rather than a branch.** Cost:
   three branches read as unknown-throughput when they are not. (§1.5)
7. **No `medium`/`fluid` on `conv`, no provenance on any value.** Cost: low
   here, but the brief drew both distinctions deliberately and neither
   survives into the data. (§1.3, §1.7)
8. **Every node still needs `at`.** Cost: near zero at five nodes. The doc is
   upfront that the network layer is not built.

---

## 7. Two things worth saying in the library's favour

- **`mixed` exists and is documented for exactly this case.** A vendor lumping
  conduction and convection into one number is a common, awkward thing to
  draw, and the format has a word for it that refuses to guess. That is the
  brief's hardest requirement and it was the easiest thing to satisfy.
- **The two layout habits in the doc are real.** Leaving `flange` sideways
  before turning up, and spacing for label width rather than symbol width,
  were the whole reason round 1 was clean. Both are stated plainly and both
  were correct.
MDEOF
wc -l examples/gallery/09-subsea/findings.md
````

**Result (error):**

```
Exit code 2
/usr/bin/bash: -c: line 165: unexpected EOF while looking for matching `''
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Assistant

Heredoc parsing choked; using the Write tool for this one file.

### Tool call — `Write`

Write `C:\Users\Peter Cetner\Documents\GitHub\ThermoDraw-cleanroom-run3\examples\gallery\09-subsea\findings.md`

````
# Findings — 09-subsea

Written from `docs/schema.md` and `brief.md` alone. The diagram was clean on
the first `check`, so almost nothing here is about fighting the layout
engine; it is about what the format could not be made to say.

---

## 1. What I could not express

This is the part that matters, so it is longest.

### 1.1 "It turns a corner on the way" — the corner is not in the data

The brief says the vapour chamber "runs up the length of the bottle to the
housing" and "turns a corner on the way". I drew that with waypoints:

```json
"via": [[560, 320], [560, 160]]
```

**That is a routing instruction, not a physical claim.** `via` says where the
wire goes on the page. It cannot distinguish "this component physically turns
a corner" from "the author needed to get from the lower row of the drawing to
the upper row". In this diagram both are true at once, which makes it look
like it worked, but nothing in the file records that the corner is a property
of the hardware. Delete the `via`, move `vct` down to y=320, and the diagram
says exactly the same thing about the vapour chamber while drawing a straight
line.

**How misleading:** mildly. Nothing false is drawn. But the reader cannot
recover the fact from the picture, and a second reader redrawing this from
the JSON would have no reason to keep the bend.

### 1.2 The whole physical setting is unsayable

"On the seabed at 1800 m, oil-filled, one atmosphere inside, steady state."

There is **no annotation, caption, or note element** in the schema. There are
nodes, branches, sources and a rail, and every one of them is a thing heat is
at or passes through. `title` exists and is documented as `"optional, not
drawn"`. So the depth, the internal pressure, and the fact that this is
subsea at all have exactly two possible homes: a node or branch `label`,
where they would masquerade as the name of a component, or nowhere.

I put them nowhere. **The rendered SVG is a generic five-node series chain.**
It would be a pixel-identical correct drawing of a box on a bench wired to a
bucket of 4 °C water. Everything that made this a subsea problem is gone.

I did not silently smuggle it into a label, and this is the single largest
thing the format cost here.

### 1.3 "Oil-filled gap" is prose in a label, not data

The convection branch is `"label": "Oil-filled gap"`. There is no `medium` or
`fluid` field on a `conv` branch, so the working fluid is a string a human
reads, not something the file knows. Same class of problem as 1.2, smaller.

### 1.4 I had to invent a node, and give it a name the brief never used

The brief describes flange → vapour chamber → oil gap → bore. Two resistances
in series need a node between them, so there is a place in the diagram the
brief never names: the top of the vapour chamber, where it meets the oil gap.

I created it as `vct`, labelled **"Vapour chamber top"**, with no `value` and
no `sub` — which `docs/schema.md` explicitly endorses ("Interior junctions
between series layers routinely have no temperature of their own").

**But the words "Vapour chamber top" are mine, not the brief's, and they are
printed on the drawing.** That is the only text on the page the brief did not
supply. The alternative was `kind: "corner"`, which "draws nothing and exists
only to route a wire" — but this junction is not a routing artefact, it is a
real thermal location where one mechanism hands off to another, and calling
it a `corner` would have understated it. I took the label. Flagging it
because a reader could reasonably assume the name came from the source.

The cost of this node is not cosmetic — see §5.

### 1.5 "It carries the whole 60 W" — sayable once, and then misleading

The brief states the throughput for the spreading path only. I put
`"rate": "60"` on that branch and on no other, because that is what the brief
states.

The result reads as though the spread path's throughput is known and the
other three paths' throughput is not. **That is false.** It is a series chain
with one source; every branch carries 60 W by inspection. There is no way to
say "and everything downstream of this carries the same" once. The two
available options were:

- state it once (what I did) — implies the rest are unknown;
- repeat `"rate": "60"` on all four — implies four independent statements of
  throughput where the brief made one, and opts all four branches into
  `rate-does-not-match`.

Neither is honest. I chose the one that adds no numbers the brief did not
give.

### 1.6 "Should not pretend otherwise" — `mixed` is right, its subscript is a judgement call

> "Which part is conduction and which is convection is not broken out
> anywhere, and the drawing should not pretend otherwise."

`mixed` is exactly this, and the schema says so almost verbatim: "A window
quoted as one number for conduction *and* convection is `mixed`." **This is
the schema's best moment in the whole exercise** — the vocabulary had a word
for the thing the brief was worried about.

The subscript was the judgement call. On `mixed`, `sub` is mine and "names
the mechanism". I wrote `"sub": "cond+conv"`, which renders as:

```
Housing wall to sea | R_cond+conv = 0.15 K/W
```

I tested the alternative (omitting `sub`), which renders a bare
`R = 0.15 K/W`. I kept `cond+conv` on the grounds that what is *unknown* here
is the split, not the mechanisms — both are present, they are lumped, and no
share is assigned. A reader who parses `R_cond+conv` as "R_cond + R_conv" is
not misled: it is their sum, with both addends unstated.

**Residual risk, stated plainly:** if a reader takes the subscript as a claim
that the two parts *were* separated somewhere, that is wrong. A bare `R`
would be immune to that reading and would say less. This is the one place I
could have gone either way.

### 1.7 No provenance

The brief twice distinguishes vendor-quoted numbers ("the path is quoted as",
"quoted by the vendor as a single number") from the temperatures. There is no
field for where a number came from. All eight numbers render identically.
Low cost here; it is a real absence.

---

## 2. Where the documentation failed me

`docs/schema.md` is unusually good — round 1 was clean, which is mostly its
doing. Three real gaps:

**2.1 It never says what a `mixed` branch prints with no `sub`.** The text is:

> "`mixed`, where it names the mechanism"

It says the field is mine and what it is for. It does not say whether
omitting it yields a bare `R`, drops the subscript row, or is refused. Since
§1.6 was the brief's central worry, I needed to know, and the only way to
find out was to write a throwaway file and run `describe` on it. One sentence
would have saved that.

**2.2 `describe`'s `flipped` mark names the symptom and not the cause.** The
doc says:

> "`flipped` means the label tried its automatic side, found it blocked, and
> took the opposite one"

`describe` reported `node 'vct' ... below ... flipped`. Nothing in the output
says *what* blocked it, and from the coordinates alone there is nothing
obviously above that node. I only established the cause by forcing
`"side": "up"` in a scratch copy, which produced:

> `warning: [label-adrift] node 'vct': its label was pushed 44 past its own
> clearance to get around branch 1 flange->vct`

So it was the vapour chamber's own branch label. The solver did the right
thing silently, and I could not tell that from `describe`. `check` names
blockers; `describe` does not. That asymmetry is undocumented, and it means
`flipped` is unactionable information — you learn that the solver worked, not
what it worked around.

**2.3 Nothing says there is no annotation element.** §1.2 is a hole you find
by searching for a section that is not there. The doc lists what exists; it
never says "a diagram carries no free text besides labels", so I spent time
confirming a negative.

**2.4 (minor, and the doc gets this right)** The `PYTHONIOENCODING` and the
`render` vs `theme` warnings both read as scar tissue from earlier readers,
and both were accurate. I used the CLI, so the theme trap never fired. The
`q″` U+2033 warning was three paragraphs for a key I did not need. That
proportion is a little off, but it is a fair guess at where people fall in.

---

## 3. What I guessed, and whether the guess held

| Guess | Held? |
|---|---|
| An interior junction with no `value` and no `sub` is the right way to draw the vapour-chamber / oil-gap handoff | **Yes** — doc endorses it explicitly. But it cost §5. |
| `sub: "cond+conv"` is a legal subscript string and renders literally | **Yes** — `R_cond+conv` |
| 280 units between nodes (doc suggests "about 220") | **Yes** — no `nodes-too-close`. 220 would likely have failed on the 127-wide `Housing wall to sea` label |
| 80 units of sideways clearance before the `via` turn (doc says 40–90) | **Yes** — no `label-adrift` |
| Omitting `rail` entirely is legal for a steady-state diagram with no capacitance | **Yes** — doc says so, and `describe` still lists `ground x1` |
| `diss` source with explicit `at` left of the node and default `angle` points into it | **Yes** — copied the doc's worked example |
| `pipe` is the right kind for a vapour chamber | **Yes** — doc names vapour chambers specifically |
| Nothing needed a `side` override | **Yes** — the one flip resolved itself correctly |

Nothing I guessed turned out wrong. That is a compliment to the doc, not to
me — every one of those was answered somewhere in it.

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Largely yes.** The network block is the right tool and did the job:

```
board --spread-- flange
flange --pipe-- vct
vct --conv-- bore
bore --mixed-- sea
source 0 --diss-> board
```

That is the chain from the brief, in order, with the mechanism on each link
and the dissipation arriving at the right end. It confirmed the topology, and
`symbol/mixed` in the placements line confirmed that §1.6 landed.

**What it should have said and did not:**

1. **Nothing about `via`.** The single feature I was least confident in — the
   corner — is the one thing `describe` is silent on. It gives the symbol
   centre `(660, 160)`, from which a determined reader can infer that branch 1
   is not a straight line between `(480, 320)` and `(760, 160)`, but the
   waypoints are never listed and the branch is never marked as routed. A
   corner at the wrong height would produce identical `describe` output.
   **If you cannot open the SVG, `via` is unverifiable.**
2. **`flipped` without a blocker.** See §2.2.
3. **Throughput is not in the network block.** `q = 60 W` appears inside
   branch 0's label text and nowhere else. Fine by accident here; in a diagram
   with several `rate`s you would be reading them out of label strings.
4. It does not echo `title`, which is documented as undrawn but is still the
   only place the diagram's subject is written down.

---

## 5. Was `check --physics` silent?

**No.** The exact output is in `rounds.md`. It said:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange,
bore (neighbour 'vct' has no temperature); vct (it has no temperature)
```

It found **no disagreement** — no `node-does-not-balance`, no
`rate-does-not-match`. It checked the board: 60 W in from the source, and
`(37 − 19) / 0.30` = 60 W out. That balances exactly.

**But it only checked one node of four, and this is the sharpest finding in
this report.** The numbers in the brief agree with each other perfectly, all
the way down, at 60 W throughout:

```
board  37.0 -(0.30)- flange 19.0 -(0.02)- vct 17.8 -(0.08)- bore 13.0 -(0.15)- sea 4.0
        18.0 K              1.2 K            4.8 K             9.0 K
```

`--physics` verified one link of four. It was blinded by `vct` — the
untemperatured interior junction that the **same document** tells you to draw
("Interior junctions between series layers routinely have no temperature of
their own"), and whose consequence the `--physics` section then describes as
routine ("which is what an interior junction drawn the way this page
recommends does to the nodes either side of it").

So the recommended modelling idiom and the numeric checker are in direct
conflict, and the doc knows it and shrugs. Two resistances in series carrying
a known current through an unknown intermediate temperature is
arithmetically determinate — `(T_flange − T_bore) / (R_pipe + R_conv)` is
60 W and needs no model of anything. The checker gives up instead.

**The note is left standing.** Its remedy is "give the node, or its
neighbour, a `value`". Applying that literally means inventing 17.8 °C and
printing it on the drawing as though it had been measured. The brief forbids
adjusting numbers to quieten this output, so it stays.

---

## 6. Features the library lacks, ranked by what they cost here

1. **`--physics` cannot propagate through an untemperatured junction.**
   Cost: 3 of 4 nodes unverified, on a diagram whose numbers are exactly
   consistent, plus a note in the shipped output that cannot honestly be
   cleared. It defeats itself on the idiom its own documentation recommends.
2. **No annotation / caption / free-text element.** Cost: 1800 m, one
   atmosphere, oil-filled and steady-state are all absent from the drawing.
   The picture is context-free. (§1.2)
3. **`via` is routing only; no way to say a path physically bends.** Cost:
   "it turns a corner on the way" is not recoverable from the file. (§1.1)
4. **`describe` does not report `via` waypoints.** Cost: the one thing I most
   wanted to verify without opening the SVG is the one thing it will not tell
   me. (§4.1)
5. **`describe`'s `flipped` does not name the blocker**, though `check`'s
   warnings do. Cost: one scratch-file experiment to learn something the tool
   already knew. (§2.2)
6. **No way to state throughput for a chain rather than a branch.** Cost:
   three branches read as unknown-throughput when they are not. (§1.5)
7. **No `medium`/`fluid` on `conv`, no provenance on any value.** Cost: low
   here, but the brief drew both distinctions deliberately and neither
   survives into the data. (§1.3, §1.7)
8. **Every node still needs `at`.** Cost: near zero at five nodes. The doc is
   upfront that the network layer is not built.

---

## 7. Two things worth saying in the library's favour

- **`mixed` exists and is documented for exactly this case.** A vendor lumping
  conduction and convection into one number is a common, awkward thing to
  draw, and the format has a word for it that refuses to guess. That was the
  brief's hardest requirement and it was the easiest thing to satisfy.
- **The two layout habits in the doc are real.** Leaving `flange` sideways
  before turning up, and spacing for label width rather than symbol width,
  are the whole reason round 1 was clean. Both are stated plainly and both
  were correct.
````

**Result:**

```
File created successfully at: C:\Users\Peter Cetner\Documents\GitHub\ThermoDraw-cleanroom-run3\examples\gallery\09-subsea\findings.md (file state is current in your context — no need to Read it back)
```

### Tool call — `Bash`

*Final verification*

```bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && python -m thermodraw check examples/gallery/09-subsea/bottle.json; echo "EXIT=$?"; ls -l examples/gallery/09-subsea/
```

**Result:**

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
total 44
-rw-r--r-- 1 Peter Cetner 197121  1194 Sep  2 19:05 bottle.json
-rw-r--r-- 1 Peter Cetner 197121  9980 Sep  2 19:06 bottle.svg
-rw-r--r-- 1 Peter Cetner 197121  4323 Sep  2 19:02 brief.md
-rw-r--r-- 1 Peter Cetner 197121 14905 Sep  2 19:10 findings.md
-rw-r--r-- 1 Peter Cetner 197121  2574 Sep  2 19:06 rounds.md
```

### Assistant

Done. Four files in [examples/gallery/09-subsea/](examples/gallery/09-subsea/): `bottle.json`, `bottle.svg`, `rounds.md`, `findings.md`.

**The diagram** — a five-node series chain: board (`diss` 60 W in) → `spread` 0.30 with `rate` 60 → flange → `pipe` 0.02 with a two-waypoint corner → an untemperatured vapour-chamber-top junction → `conv` 0.08 → bore → `mixed` 0.15 → seawater (`fixed`).

**check**: clean on the first round — 10 labels placed, 0 errors, 0 warnings, 0 notes, exit 0. No findings fired, so there were no remedies to apply and no round 2. `rounds.md` says that rather than inventing a struggle.

**check --physics**: not silent. One note, pasted verbatim into `rounds.md`:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)
```

It found no disagreement, and the brief's numbers in fact close exactly at 60 W down the whole chain — but it only verified the board. Its remedy ("give the node, or its neighbour, a `value`") would mean inventing 17.8 °C for a place the brief never measures, so the note stands, with the reason written down.

The three findings I'd point at first:

1. **`--physics` is defeated by the idiom the schema recommends.** An interior junction with no temperature is what `docs/schema.md` tells you to draw for a series handoff; it also blinds the checker on both neighbours. Two series resistances with a known throughput are arithmetically determinate — nothing was checked anyway.
2. **The setting is unsayable.** No annotation element exists, and `title` is documented as not drawn. 1800 m, one atmosphere, oil-filled, steady state are nowhere on the page. The SVG would serve equally as a bench rig next to a bucket of cold water. I did not smuggle any of it into a label.
3. **`via` is routing, not physics, and `describe` won't show it.** "It turns a corner on the way" is drawn but not recorded — and the waypoints are the one thing `describe` never prints, so it's the only part of the drawing I could not confirm without opening the SVG, which the brief forbade.

Two smaller ones: the doc never says what `mixed` prints with no `sub` (I had to test — it's a bare `R`), and `describe`'s `flipped` mark names the symptom but not the blocker, unlike `check`'s warnings.

## User — turn 2

<sub>2026-09-02 23:42:23.457Z</sub>

Save the whole transcript of this session as <that brief's folder>/transcript.md, put the model and harness on the first line of rounds.md, run `PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics` on the final diagram and paste its output at the end of rounds.md, and commit everything under that folder as one commit.

---

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Look for session transcript files*

```bash
ls -la "/c/Users/Peter Cetner/.claude/projects/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/" 2>&1 | head -30
```

**Result:**

```
total 1444
drwxr-xr-x 1 Peter Cetner 197121      0 Sep  2 19:04 ./
drwxr-xr-x 1 Peter Cetner 197121      0 Sep  2 19:04 ../
-rw-r--r-- 1 Peter Cetner 197121 277468 Sep  2 19:42 8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl
-rw-r--r-- 1 Peter Cetner 197121 228668 Sep  2 19:42 91585270-66c9-4060-866a-2e4f1a363459.jsonl
-rw-r--r-- 1 Peter Cetner 197121 299491 Sep  2 19:42 a4eaf000-aa80-487d-9579-2c52e7c92355.jsonl
-rw-r--r-- 1 Peter Cetner 197121 262734 Sep  2 19:42 c7905529-7518-41e5-a2f7-5a746a04f7d6.jsonl
-rw-r--r-- 1 Peter Cetner 197121 392032 Sep  2 19:42 f970e87c-7552-4b69-a906-652cc31fad94.jsonl
drwxr-xr-x 1 Peter Cetner 197121      0 Sep  2 19:04 memory/
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Inspect transcript jsonl structure*

```bash
cd "$(git rev-parse --show-toplevel)" && F="/c/Users/Peter Cetner/.claude/projects/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl" && wc -l "$F" && python - <<'PY'
import json
F=r"C:\Users\Peter Cetner\.claude\projects\C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3\8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl"
rows=[json.loads(l) for l in open(F,encoding='utf-8') if l.strip()]
print(len(rows))
from collections import Counter
print(Counter(r.get('type') for r in rows))
print(sorted(rows[0].keys()))
for r in rows[:3]:
    print('---', r.get('type'), r.get('timestamp'), str(r)[:300])
PY
```

**Result:**

```
97 /c/Users/Peter Cetner/.claude/projects/C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3/8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl
97
Counter({'assistant': 33, 'attachment': 22, 'user': 16, 'last-prompt': 5, 'bridge-session': 5, 'ai-title': 5, 'atis-latch': 5, 'queue-operation': 4, 'custom-title': 1, 'system': 1})
['content', 'operation', 'sessionId', 'timestamp', 'type']
--- queue-operation 2026-09-02T23:04:39.668Z {'type': 'queue-operation', 'operation': 'enqueue', 'timestamp': '2026-09-02T23:04:39.668Z', 'sessionId': '8844b698-922a-4052-9b9a-6806d2e1af6f', 'content': 'Read examples/gallery/09-subsea/brief.md and do exactly what it says.'}
--- queue-operation 2026-09-02T23:04:39.760Z {'type': 'queue-operation', 'operation': 'dequeue', 'timestamp': '2026-09-02T23:04:39.760Z', 'sessionId': '8844b698-922a-4052-9b9a-6806d2e1af6f'}
--- user 2026-09-02T23:04:39.785Z {'parentUuid': None, 'isSidechain': False, 'promptId': '4998af70-c96d-412b-b0af-a533b1683c81', 'type': 'user', 'message': {'role': 'user', 'content': 'Read examples/gallery/09-subsea/brief.md and do exactly what it says.'}, 'uuid': '7e6ef1ab-245c-453b-9b77-4de12f92dfc1', 'timestamp': '2026-09-02T23:
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Inspect content block types*

```bash
cd "$(git rev-parse --show-toplevel)" && python - <<'PY'
import json
from collections import Counter
F=r"C:\Users\Peter Cetner\.claude\projects\C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3\8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl"
rows=[json.loads(l) for l in open(F,encoding='utf-8') if l.strip()]
c=Counter()
for r in rows:
    if r.get('type') in ('user','assistant'):
        m=r.get('message',{}); ct=m.get('content')
        if isinstance(ct,str): c[(r['type'],'str')]+=1
        else:
            for b in ct: c[(r['type'],b.get('type'))]+=1
print(c)
for r in rows:
    if r.get('type')=='attachment':
        print('ATTACH keys', sorted(r.keys()), str(r)[:400]); break
for r in rows:
    if r.get('type')=='system':
        print('SYS', str(r)[:400]); break
PY
```

**Result:**

```
Counter({('assistant', 'tool_use'): 16, ('user', 'tool_result'): 15, ('assistant', 'thinking'): 13, ('assistant', 'text'): 6, ('user', 'str'): 2})
ATTACH keys ['attachment', 'cwd', 'entrypoint', 'gitBranch', 'isSidechain', 'parentUuid', 'sessionId', 'timestamp', 'type', 'userType', 'uuid', 'version'] {'parentUuid': '7e6ef1ab-245c-453b-9b77-4de12f92dfc1', 'isSidechain': False, 'attachment': {'type': 'deferred_tools_delta', 'addedNames': ['CronCreate', 'CronDelete', 'CronList', 'DesignSync', 'EnterPlanMode', 'EnterWorktree', 'ExitPlanMode', 'ExitWorktree', 'ListPlugins', 'ListSkills', 'Monitor', 'NotebookEdit', 'PushNotification', 'RemoteTrigger', 'SearchPlugins', 'SearchSkills', 'SendMessage', 
SYS {'parentUuid': 'c658350b-513a-448e-addf-021614f689b8', 'isSidechain': False, 'type': 'system', 'subtype': 'stop_hook_summary', 'hookCount': 2, 'hookInfos': [{'command': 'callback'}, {'command': 'callback'}], 'hookErrors': [], 'hookAdditionalContext': [], 'preventedContinuation': False, 'stopReason': '', 'hasOutput': False, 'level': 'suggestion', 'timestamp': '2026-09-02T23:10:20.950Z', 'uuid': '23
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Extract model and harness version*

```bash
cd "$(git rev-parse --show-toplevel)" && python - <<'PY'
import json
F=r"C:\Users\Peter Cetner\.claude\projects\C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3\8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl"
rows=[json.loads(l) for l in open(F,encoding='utf-8') if l.strip()]
print({r['message'].get('model') for r in rows if r.get('type')=='assistant'})
print({r.get('version') for r in rows if r.get('version')})
print({r.get('entrypoint') for r in rows if r.get('entrypoint')})
print({r.get('gitBranch') for r in rows if r.get('gitBranch')})
PY
python -c "import platform,sys;print(platform.platform());print(sys.version)"
```

**Result:**

```
{'claude-opus-5'}
{'2.1.255'}
{'claude-desktop'}
{'master'}
Windows-10-10.0.19045-SP0
3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Add header line and append physics re-run to rounds.md*

````bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && D=examples/gallery/09-subsea && python -m thermodraw check --physics $D/bottle.json > /tmp/p2.txt 2>&1; echo "EXIT=$?" > /tmp/p2exit.txt; cat /tmp/p2.txt /tmp/p2exit.txt && python - <<'PY'
import io
p='examples/gallery/09-subsea/rounds.md'
t=open(p,encoding='utf-8').read()
head=("Model: claude-opus-5 (Opus 5) | Harness: Claude Code 2.1.255, claude-desktop entrypoint, "
      "Windows 10.0.19045, Python 3.11.9, `thermodraw` from `src/` on branch `master`.\n\n")
assert t.startswith('# Rounds')
out=open('/tmp/p2.txt',encoding='utf-8').read().rstrip('\n')
tail=("\n\n## `check --physics` re-run on the final diagram\n\n"
      "Re-run after the diagram was finalised and rendered, exactly as invoked:\n\n"
      "```\n"
      "PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json\n"
      "```\n\n"
      "Output, pasted exactly as it came:\n\n"
      "```\n" + out + "\nEXIT=0\n```\n\n"
      "Identical to the run recorded above; the diagram did not change between them.\n"
      "The note is still standing, for the reason given in that section.\n")
open(p,'w',encoding='utf-8').write(head+t.rstrip('\n')+tail)
print(open(p,encoding='utf-8').read()[:200])
PY
````

**Result (error):**

```
Exit code 1
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
Traceback (most recent call last):
  File "<stdin>", line 7, in <module>
FileNotFoundError: [Errno 2] No such file or directory: '/tmp/p2.txt'
```

### Assistant — reasoning

<details><summary>internal reasoning</summary>

```

```

</details>

### Tool call — `Bash`

*Add header line and append physics re-run to rounds.md*

````bash
cd "$(git rev-parse --show-toplevel)" && export PYTHONPATH=src PYTHONIOENCODING=utf-8 && python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json > .p2.txt 2>&1; echo "physics exit=$?" && python - <<'PY'
p='examples/gallery/09-subsea/rounds.md'
t=open(p,encoding='utf-8').read()
head=("Model: claude-opus-5 (Opus 5) | Harness: Claude Code 2.1.255, claude-desktop entrypoint, "
      "Windows 10.0.19045, Python 3.11.9, `thermodraw` run from `src/` on branch `master`.\n\n")
assert t.startswith('# Rounds')
out=open('.p2.txt',encoding='utf-8').read().rstrip('\n')
tail=("\n\n## `check --physics` re-run on the final diagram\n\n"
      "Re-run after the diagram was finalised and rendered, exactly as invoked:\n\n"
      "```\n"
      "PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json\n"
      "```\n\n"
      "Output, pasted exactly as it came:\n\n"
      "```\n" + out + "\n```\n\n"
      "Exit code 0. Identical to the run recorded above; the diagram did not change\n"
      "between them. The note is still standing, for the reason given in that section.\n")
open(p,'w',encoding='utf-8').write(head+t.rstrip('\n')+tail)
PY
rm -f .p2.txt && head -4 examples/gallery/09-subsea/rounds.md && echo '...' && tail -20 examples/gallery/09-subsea/rounds.md
````

**Result:**

````
physics exit=0
Model: claude-opus-5 (Opus 5) | Harness: Claude Code 2.1.255, claude-desktop entrypoint, Windows 10.0.19045, Python 3.11.9, `thermodraw` run from `src/` on branch `master`.

# Rounds

...
So the brief's numbers agree with each other exactly. `--physics` checked
1 of the 4 free nodes and could not see any of that.

## `check --physics` re-run on the final diagram

Re-run after the diagram was finalised and rendered, exactly as invoked:

```
PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json
```

Output, pasted exactly as it came:

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
```

Exit code 0. Identical to the run recorded above; the diagram did not change
between them. The note is still standing, for the reason given in that section.
````

### Assistant

Now the transcript.

### Tool call — `Bash`

*Convert session JSONL to transcript.md*

````bash
cd "$(git rev-parse --show-toplevel)" && cat > .mktranscript.py <<'PY'
import json, datetime

SRC = r"C:\Users\Peter Cetner\.claude\projects\C--Users-Peter-Cetner-Documents-GitHub-ThermoDraw-cleanroom-run3\8844b698-922a-4052-9b9a-6806d2e1af6f.jsonl"
DST = "examples/gallery/09-subsea/transcript.md"

rows = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
rows = [r for r in rows if r.get("type") in ("user", "assistant")]

def fence(text, lang=""):
    text = text.rstrip("\n")
    tick = "```"
    while tick in text:
        tick += "`"
    return f"{tick}{lang}\n{text}\n{tick}\n"

def ts(r):
    t = r.get("timestamp", "")
    return t.replace("T", " ").replace("Z", "Z")

out = []
w = out.append

w("# Session transcript — 09-subsea\n")
w("Verbatim transcript of the Claude Code session that produced `bottle.json`,")
w("`bottle.svg`, `rounds.md` and `findings.md` in this folder.\n")
w("- **Model:** `claude-opus-5` (Opus 5)")
w("- **Harness:** Claude Code 2.1.255, `claude-desktop` entrypoint, Windows 10.0.19045")
w("- **Session id:** `8844b698-922a-4052-9b9a-6806d2e1af6f`")
w("- **Working directory:** repository root, branch `master`")
w("- **Source:** the session's own JSONL log, converted mechanically — nothing")
w("  written from memory, nothing edited")
w("")
w("Assistant reasoning blocks are included and marked as such. Tool calls show")
w("their full input; tool results are shown as returned. The log is appended to")
w("as the session runs, so it ends partway through the final turn — the turn that")
w("generated this very file. That cut-off is the only thing missing.\n")
w("---\n")

n_user = n_asst = n_tool = 0
for r in rows:
    typ = r["type"]
    msg = r.get("message", {})
    content = msg.get("content")
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not content:
        continue

    if typ == "user":
        # a turn that is only tool_results belongs with the tool call above it
        kinds = {b.get("type") for b in content}
        if kinds == {"tool_result"}:
            for b in content:
                c = b.get("content")
                if isinstance(c, list):
                    c = "\n".join(x.get("text", "") for x in c if isinstance(x, dict))
                c = c if isinstance(c, str) else json.dumps(c, ensure_ascii=False, indent=2)
                err = " (error)" if b.get("is_error") else ""
                w(f"**Result{err}:**\n")
                w(fence(c))
            continue
        n_user += 1
        w(f"## User — turn {n_user}\n")
        w(f"<sub>{ts(r)}</sub>\n")
        for b in content:
            if b.get("type") == "text":
                w(b["text"].strip() + "\n")
        w("---\n")
        continue

    # assistant
    for b in content:
        k = b.get("type")
        if k == "thinking":
            n_asst += 1
            w("### Assistant — reasoning\n")
            w("<details><summary>internal reasoning</summary>\n")
            w(fence(b.get("thinking", "")))
            w("</details>\n")
        elif k == "text":
            t = b.get("text", "").strip()
            if t:
                w("### Assistant\n")
                w(t + "\n")
        elif k == "tool_use":
            n_tool += 1
            name = b.get("name")
            inp = b.get("input", {})
            w(f"### Tool call — `{name}`\n")
            if name in ("Bash", "PowerShell") and "command" in inp:
                if inp.get("description"):
                    w(f"*{inp['description']}*\n")
                w(fence(inp["command"], "bash"))
            elif name == "Write" and "content" in inp:
                w(f"Write `{inp.get('file_path','')}`\n")
                w(fence(inp["content"]))
            else:
                w(fence(json.dumps(inp, ensure_ascii=False, indent=2), "json"))

w("\n---\n")
w(f"*{n_user} user turns, {n_tool} tool calls, {n_asst} reasoning blocks.*")

open(DST, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print(DST, n_user, "user turns,", n_tool, "tool calls")
PY
python .mktranscript.py && rm -f .mktranscript.py && wc -l examples/gallery/09-subsea/transcript.md
````


---

*2 user turns, 20 tool calls, 16 reasoning blocks.*
