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
mix `K/W` with `mK/W`. Values are written without their unit; the unit is
appended from this table.

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
| `angle` | rotates the node's own frame, in degrees |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes |

`fixed` draws the boundary wall and connects to it. The wall is always drawn
flat below the node; `angle` does not turn it. `break` stops short of the
wall — the visible gap is the whole distinction. `corner` draws nothing and
exists only to route a wire.

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

Two details are worth copying rather than rediscovering:

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
