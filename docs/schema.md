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
  "units":  {"R": "K/W", "C": "J/K", "T": "°C", "P": "W", "q": "W"},
  "nodes":    [ ... ],
  "branches": [ ... ],
  "sources":  [ ... ],
  "rail":     { ... }
}
```

Units are fixed per diagram and given once per quantity, so a diagram cannot
mix `K/W` with `mK/W`. `q` is shared by all three of `radin`, `flow` and
`flux`, so a diagram carrying both a heat flow in `W` and a heat flux in
`W/cm²` cannot label them correctly — pick the one you need. Values are written without their unit; the unit is
appended from this table. Only give the keys you use — a diagram with no
capacitance needs no `C`, and one with no text needs no `units` at all. A
quantity used without its unit declared simply draws the bare number.

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

A `break` has no temperature to state, so `sub` and `value` are usually left
off and the label alone is drawn. It also **stands alone**: every branch kind
draws a resistance or a capacitance, and there is no plain-wire branch, so
there is no way to run a bare wire to one. Place it near what it is bolted to
and leave it unconnected — which is honest, since no heat flows through it.

The wall is always drawn flat below the node, at every orientation. `angle`
does not turn it, and neither does anything else; it decides which way the
label goes and nothing more. The hero's `"angle": 90` on its ambient node
sends that label out to the right instead of straight up, where the branch
arriving from the left would have crowded it. Reach for it when a label wants
to be somewhere `side` alone cannot put it.

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
| `kind` | `cond`, `conv`, `rad`, `contact`, `cap` |
| `label` | the words above the box |
| `sub` | **only** for `cap`, where the subscript names a place |
| `value` | unit appended from `units.R` (or `units.C` for `cap`) |
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

## Sources

Heat appearing at a node. An arrow, not a two-terminal element.

```jsonc
{"to": "j", "kind": "diss", "label": "Switching loss", "value": "45", "sub": "d"}
```

`kind` is `diss` (electrical or internal dissipation), `radin` (radiation
arriving), `flow` (a heat rate crossing the boundary) or `flux` (a rate per
unit area).

| kind | drawn as | symbol | unit taken from |
|---|---|---|---|
| `diss` | arrow into the node | `P` | `units.P` |
| `radin` | wavy arrow into the node | `q` | `units.q` |
| `flow` | arrow into the node | `q` | `units.q` |
| `flux` | several arrows | `q` | `units.q` |

`sub` names the source, as it does on a node; it is yours to choose. Note that
`radin`, `flow` and `flux` all read `units.q`, so a diagram that mixes a heat
rate with a heat flux has one `q` unit to spend between them.

`at` and `angle` place the arrow; by default it comes in horizontally from the
left and its head lands on the node. `side` moves its label, as above.

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

The two habits above are no longer advice. They are checks, and so are six
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
- `parallel-pair-same-side` is a note rather than a warning because the hero
  diagram breaks it and is fine. Take it as a prompt to look, not an error.

Two things it does not check: whether the numbers are right, and whether the
network is the one you meant. It reports how the drawing reads, not what it
says.
