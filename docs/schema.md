# The diagram schema

A ThermoDraw diagram is plain data. This page is the whole format; it is
written to be pasted into a prompt.

```python
from thermodraw import Diagram, render, layout

svg = render(layout(Diagram.from_json(text)))
```

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
| `kind` | `free` (default), `fixed`, `break`, `corner` |
| `label` | the words above the symbol — the top line, always |
| `sub` | subscript on `T`. Identity: you choose it, it names a place |
| `value` | temperature, unit appended from `units.T` |
| `at` | `[x, y]`. **Required in 0.2** |
| `angle` | turns the node's label frame, in degrees. It moves the label and nothing else |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes |

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
it — the hero's `"angle": 90` on its ambient node sends that label out to the
right rather than straight up, where the branch arriving from the left would
have crowded it.

A `fixed` node may sit anywhere. The hero puts its ambient node at the rail's
own `y` because that is where the diagram's cold end belongs, not because the
two are connected — nothing requires a boundary to be on the rail line.

## Branches

A path heat takes between two nodes.

```jsonc
{"from": "j", "to": "c", "kind": "cond", "label": "Die attach", "value": "0.35"}
```

| field | meaning |
|---|---|
| `from`, `to` | node ids, or the literal `"rail"` |
| `kind` | `cond`, `conv`, `rad`, `contact`, `cap`, `break` |
| `label` | the words above the box |
| `sub` | **only** for `cap`, where the subscript names a place |
| `value` | unit appended from `units.R` (or `units.C` for `cap`). Optional: a path with no number draws its label alone |
| `via` | `[[x, y], ...]` waypoints, for a path that is not a straight line |
| `at` | where the box sits. Defaults to the middle of the longest run |
| `angle` | overrides the direction taken from the wire |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes |

The subscript on a resistance is **not** yours to set: `cond`, `conv`, `rad`
and `contact` each carry their own, and they name the physics. Which
conduction path this is belongs in `label`, so nothing is named twice. On a
capacitance the subscript names a place, so `sub` is yours.

`"to": "rail"` drops straight down to the reference rail from wherever the
other end is. That is how thermal mass is hung off a transient model.

`break` is the odd one out: it draws an open circuit — wire, crossbar, gap,
crossbar, wire — for a mechanical connection that carries no heat, such as a
standoff or a mount. It names no quantity, so it takes **no `value` and no
`sub`**, and one given a value is refused. Everything else on the table works
on it. The same word is also a node `kind`, and it means the same thing there:
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

Only the two annotation kinds may point away. `diss` is dissipation
*appearing* at a node rather than travelling to it, and `radin` is radiation
*arriving* — for radiation leaving, draw a `rad` branch to a boundary node,
which is the thing that actually carries it.

`sub` names the source, as it does on a node; it is yours to choose. `radin`
and `flow` share `units.q` because both are powers. `flux` has its own, so a
diagram can carry a heat rate in `W` and a heat flux in `W/cm²` at once.

`at` is the **centre of the symbol**, not its head or its tail, exactly as it
is on a branch. `angle` is the direction the arrow points, `0` being to the
right. A lead is drawn from the symbol to the node whichever you choose, so
`at` only has to be roughly right.

Leave `at` out and the source is placed along its own `angle` with room for
its label — on the far side of the node for a `to`, so the arrow arrives, and
on the near side for a `from`, so it leaves. That is usually what you want:
`{"from": "cell", "kind": "flux", "angle": 270}` puts a hatched face on top of
the cell with the arrows rising off it, and needs no coordinates.

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

A power device losing heat to still air by two parallel paths, with the die
and sink thermal masses on the rail:

```jsonc
{
  "units": {"R": "K/W", "C": "J/K", "T": "°C", "P": "W"},
  "nodes": [
    {"id": "j",   "label": "Junction",  "sub": "j",   "value": "112", "at": [200, 150]},
    {"id": "c",   "label": "Case",      "sub": "c",   "value": "78",  "at": [424, 150]},
    {"id": "s",   "label": "Sink base", "sub": "s",   "value": "61",  "at": [648, 150]},
    {"id": "amb", "kind": "fixed", "label": "Still air", "sub": "amb",
     "value": "40", "at": [936, 372], "angle": 90}
  ],
  "branches": [
    {"from": "j", "to": "c", "kind": "cond",    "label": "Die attach", "value": "0.35"},
    {"from": "c", "to": "s", "kind": "contact", "label": "Grease",     "value": "0.15"},
    {"from": "s", "to": "amb", "kind": "conv", "label": "Fins → air", "value": "1.80",
     "via": [[696, 150], [696, 70], [936, 70]], "at": [816, 70]},
    {"from": "s", "to": "amb", "kind": "rad", "label": "Case → walls", "value": "6.40",
     "via": [[696, 150], [696, 238], [936, 238]], "at": [816, 238]},
    {"from": "j", "to": "rail", "kind": "cap", "label": "Die",  "sub": "j", "value": "0.9"},
    {"from": "s", "to": "rail", "kind": "cap", "label": "Sink", "sub": "s", "value": "86"}
  ],
  "sources": [
    {"to": "j", "kind": "diss", "label": "Switching loss", "value": "45", "sub": "d",
     "at": [96, 150]}
  ],
  "rail": {"reference": "amb", "y": 372, "span": [200, 936]}
}
```

That file is `examples/hero.json`, and it renders the diagram at the top of
the README.

## Coordinates

Every node needs `at` in 0.2. The library places what you give it and works
out the wire runs, the label positions and the canvas size for itself.

Solving for coordinates you leave out is the network layer, in 0.3. It changes
one stage — `layout` — and nothing in this schema. A diagram written today
keeps working; it just stops needing the numbers.

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

- **Leave a node sideways before turning.** A `via` that goes straight up from
  a node puts a wire exactly where that node's label wants to sit, and the
  label steps out past it — ending up nearer the branch than the node it
  names. The hero turns at `x = 696` for a node at `x = 648`. Give the turn
  40–90 units of clearance.
- **A parallel pair needs `side`.** Both branches are horizontal, so both
  labels choose "up" and the lower one lands inside the loop. Set
  `"side": "up"` on the upper branch and `"side": "down"` on the lower one.

Space labels, not symbols. A box is 84 wide, but `R_cond = 0.000877 K/W` is
over twice that, and it is the label that decides how far apart two nodes have
to be.

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
      -> set `side` to "down" on the lower of the two
```

"11 labels placed" is every node except `corner` ones, plus every branch and
every source — so it is the count you can work out from the file, and a
number lower than that means a label was dropped rather than moved. It exits
0 when clean, 1 when it found something, and 2 when the file could not be
read. `--json` for a machine, `--strict` to fail on notes too,
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
  finding will tell you.
- `network-in-pieces` is the one to read carefully, because a severed network
  looks fine. A source has **one end**, so a `flow` or `flux` annotation
  cannot join two nodes however suggestively you place two of them: heat
  carried from one node to another by a moving fluid has no branch kind yet,
  and this finding is what tells you the drawing did not say what you meant.
- `nodes-too-close` is the other half of that. Every finding names what is
  *nearest* the crowded label, and on a short run that is a wire — so if you
  are being told to move a `via` and it is not helping, look for this one: it
  names the two nodes, how far apart they are, and what their labels need.
- `parallel-pair-same-side` is a note rather than a warning because the hero
  diagram breaks it and is fine. Take it as a prompt to look, not an error.

Two things it does not check: whether the numbers are right, and whether the
network is the one you meant. It reports how the drawing reads, not what it
says.

## Seeing what got drawn

`check` grades the drawing. It cannot tell you the drawing is the one you
meant, and a clean report is not the same as a correct diagram:

```bash
thermodraw describe diagram.json
```

```
diagram.json: canvas 1042 x 431, 11 labels

placements: ground x1, node x4, symbol/cap x2, symbol/cond x1,
            symbol/contact x1, symbol/conv x1, symbol/diss x1, symbol/rad x1,
            wire x15

nodes:
  j              free     at (200, 150)
  ...

rail: y 372, span (200, 936), reference 'amb'

nodes:
  j              free     at (200, 150)
  ...

elements:
  branch 0 j->c    symbol/cond   (312, 150)       above   103x33  Die attach | R_cond = 0.35 K/W
  branch 2 s->amb  symbol/conv   (816, 70)        above   102x33  Fins → air | R_conv = 1.80 K/W
  branch 3 s->amb  symbol/rad    (816, 238)       above    97x33  Case → walls | R_rad = 6.40 K/W
  branch 4 j->rail symbol/cap    (200, 278) a90   right    72x33  Die | C_j = 0.9 J/K
  ...
```

Element counts against what you wrote, the canvas you will get, where each
symbol sits and which way it is turned, what each label reads, and which way
it went — including `flipped` and `pushed N` where the solver had to work for
it. Above, `branch 2` and `branch 3` both went "above", which is the parallel
pair `check` notes, visible directly rather than only graded.

An element carrying no text at all — a `break` branch with no `label` — still
gets a row, marked `(no label)`. `rail.reference` is documentary and does
nothing, so this is the only place it can be checked against what you meant.

It always exits 0: it reports, it does not judge. `--json` for a machine. From
Python it is `describe(diagram)`, returning a `.text()` and a `.to_dict()`.
