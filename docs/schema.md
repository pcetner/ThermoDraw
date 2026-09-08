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

Resistances are drawn as textured boxes. If your readers know circuit
notation, `render(..., notation="zigzags")`, `.svg(notation="zigzags")` or
`thermodraw render --notation zigzags` draws every resistance as a zigzag
instead, with the same geometry, so labels, wires and `check` are unchanged.
Like light and dark, that is how the drawing is shown and not what it says:
nothing in this file names a notation.

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

The quantities are `R`, `C`, `T`, `P`, `q` and `q″`, plus `mdot` and `cp`,
which only a `stream` states. `radin` and `flow` are both powers and share
`q`; a heat **flux** is per unit area, so it is measured in something else and
reads `q″`.

`--physics` works in SI and needs to recognise the unit it is given, so it
knows `K/W`, `°C/W`, `C/W`, `mK/W` and `K/kW` for `R`; `W`, `kW` and `mW` for
`P` and `q`; `kg/s`, `g/s`, `kg/min` and `kg/h` for `mdot`; and `J/kg·K` or
`kJ/kg·K` for `cp`. Anything else still **draws** — the unit is text on the
page — and `check --physics` says in one note that it checked nothing rather
than guessing at a factor.

`T` may also say which scale its temperatures are on, because `K` is
byte-identical whether you mean absolute kelvin or a rise above ambient:

```jsonc
"units": {"T": {"unit": "K", "scale": "absolute"}}
```

`scale` is `absolute` or `rise`. Plain `"T": "K"` stays valid and declares
nothing. The drawing does not change; `describe` prints the declaration, and
under `--physics` a `rad` branch carrying a value on a diagram declared as a
rise gets a note, because a radiation resistance is only meaningful at
absolute temperatures. The balance check itself works on differences and
does not care.

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
| `kind` | `free` (default), `fixed`, `break`, `phase` |
| `label` | the words above the symbol — the top line, always. Optional: a node with none draws its `T` line alone, or nothing, and still counts as a label placed |
| `sub` | subscript on `T`. Identity: you choose it, it names a place |
| `value` | temperature, unit appended from `units.T` |
| `at` | `[x, y]`. Optional: left out, the node is placed by the solver, which places a chain of nodes and refuses anything else by name |
| `angle` | turns the node's label frame, in degrees. It moves the label and nothing else |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes |
| `wall` | `down` (default), `up`, `left`, `right` — which way a `fixed` or `break` node's wall faces. Refused on a node that has no wall |

`phase` is a node whose temperature a phase change holds rather than a
boundary: the constant-temperature marking, two short rules beneath, and
no wall. Condensation at 3.2 kW with no temperature drop is one node, not
two surfaces with a path between them.

`fixed` draws the boundary wall and connects to it with a short stub. `break`
draws the same wall with no stub — the visible gap is the whole distinction,
and it is topological rather than decorative.

A node with **no `value` and no `sub`** draws its label alone and no `T` at
all. Interior junctions between series layers routinely have no temperature of
their own, and a lone italic `T` states nothing. Give it a `sub` and you get
`T_mid` with no number, which is what a symbolic diagram wants; give it
neither and the symbol is simply left out. A wire that has to bend on its way
somewhere does not need a node at the bend: give the branch `via` waypoints.

A `break` has no temperature to state, so `sub` and `value` are usually left
off and the label alone is drawn. To tie one to the thing it is bolted to,
use a `break` **branch** — the same word for the same thing in the other
position.

The wall faces `wall`: `down` unless you say otherwise, and `angle` does not
turn it — `angle` decides which way the label goes and nothing more. Turn the
wall when the boundary holds something from above or beside it. A mount that
a cold mass hangs from has its wall above, `"wall": "up"`, so the strut
arrives from below through clear space instead of through the hatching;
drawn with the wall still below, `check` reports `wire-through-wall` and
names the direction that faces away from the branch. With the wall above, an
automatic label goes below, the way it goes above when the wall is below.

`side` aimed at the wall — `down` on a wall that faces down, `up` on one
that faces up — puts the label beyond that node's own wall, and never prints
on it: on a `fixed` node the clearance already covers the wall, and on a
`break`, whose wall stands further off, the solver pushes the label the rest
of the way. The `break` case ends up snug against the wall, and above an
upward wall the push is far enough to be reported, so prefer another side or
an `angle` there if you want air around the text.

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
| `kind` | `cond`, `conv`, `rad`, `contact`, `spread`, `pipe`, `mixed`, `cap`, `flow`, `break`, `link`, `stream` |
| `label` | the words above the box |
| `sub` | yours on the kinds whose subscript the library does not set: `cap`, where it names a place; `mixed`, where it names the part — `R_wall` — since the mechanism is what `mixed` declines to say, and it may be left off; `flow`; `stream`, where it names the medium, so `ṁ_w`. Ignored on `break`, and overridden on every resistance kind |
| `value` | unit appended from `units.R` (`units.C` for `cap`, `units.q` for `flow`). Optional: a path with no number draws its label alone. Refused on `break` |
| `rate` | what this path actually carries. Drawn as `q = 12 W` on its own line, in `units.q`, under the resistance it presents. Needs `units.q`. Refused on `flow`, whose value already is a rate, and on `break`. On a `count`ed branch it is the whole group's, not per item. Stating it opts the branch into `rate-does-not-match` under `--physics` |
| `mdot` | `stream` only: mass flow rate, in `units.mdot`. With `cp` or neither |
| `cp` | `stream` only: specific heat, in `units.cp`. With `mdot` or neither |
| `count` | how many identical ones there are |
| `arrangement` | `parallel` or `series`. Required with `count` |
| `via` | `[[x, y], ...]` waypoints, for a path that is not a straight line |
| `at` | where the box sits. Defaults to the middle of the longest run |
| `angle` | overrides the direction taken from the wire |
| `side` | `auto` (default), `up`, `down`, `left`, `right` — where the label goes. On a horizontal run only `up` and `down` are useful: `left` and `right` put the label along the wire, into the next thing on it |

`cond` is conduction through a solid: a die attach, a brick course, a
jelly roll. `conv` is heat crossing into a fluid: a wall to the air or the
coolant beside it, a fin to the wind. `rad` is radiation to a surface it
can see, and its value holds at the pair of temperatures it was taken at.
`contact` is the join between two solids pressed together — a thermal pad,
a bolted flange, an interface material — and hatches its two halves in
opposite directions. `spread` is a path whose cross-section grows as the heat goes — hatching
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
it means eight of that, not eight sharing it. The stored value is still
exactly the digits you typed — values are strings, so `"2.10"` stays `2.10` —
and the group's own value is drawn beside the count as a second, derived
number: `8 in parallel = 0.003438 K/W`. Without it a reader checking the
arithmetic on the page divides the wrong way round, or not at all.

The fold follows the quantity, not the word. Resistances in parallel divide
and in series multiply; a capacitance is the dual, adding in parallel and
dividing in series. A `flow` carries a rate rather than a resistance, and a
rate folds like one: four loops side by side carry four times the heat, `4 in
parallel = 40 W`, and four in a chain pass the same heat through every link,
so the group carries one loop's worth. A `break` carries nothing and states
no group value, and a `value` that is not a number is left as you wrote it.
`--physics` reads the same table, so the number on the page and the number
in the report cannot disagree. A counted **source** shows its total
the same way — `each of 8 = 3200 W` — since sources simply add.

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

`link` is the other end of that thought: two nodes that are **one place**,
drawn twice because the reader needs both names. A bolted flange quoted as
having no resistance worth stating, a baseplate that is the part the reader
counts but not a separate temperature. It draws a plain wire — which is
exactly what a `break` declines to be, since a wire says heat flows, and
here it flows with nothing in the way — and like `break` it names no
quantity, so it takes **no `value` and no `rate`** and its label stands
alone.

It is a claim, not a decoration. Under `--physics` the two ends are merged
into one place before anything is summed, so heat arriving at either name
arrives at the same balance; and if the two ends state different
temperatures, that is `link-temperatures-disagree` — a contradiction rather
than a disagreement, so no tolerance is allowed for it.


`stream` is a medium moving through the drawing — a steel strip through an
oven, water through a coil. It is a path and not a node, because it has two
ends: it enters at the temperature of the node it comes `from` and leaves at
the temperature of the node it goes `to`, and the difference *is* the heat it
carries away. It states a mass flow and a specific heat, and the library works
out the rest.

```jsonc
{"units": {"T": "K", "P": "kW", "q": "kW", "mdot": "kg/s", "cp": "kJ/kg·K"},
 "nodes": [{"id": "in", "kind": "fixed", "label": "Strip in", "value": "300"},
           {"id": "out", "label": "Strip out", "value": "1250"}],
 "branches": [{"from": "in", "to": "out", "kind": "stream",
               "label": "Steel strip", "mdot": "2.5", "cp": "0.665"}],
 "sources": [{"to": "out", "kind": "diss", "label": "Oven", "value": "1579.4"}]}
```

What it carries is `ṁ c_p (T_to − T_from)`, drawn under the two numbers it
states, and `--physics` balances against the same figure — it is worked out
once, so the drawing and the check cannot disagree. Above, 2.5 kg/s of steel
at 0.665 kJ/kg·K over a 950 K rise comes to 1579 kW, and the oven states
1578.4; change either and the outlet node is reported. The same furnace drawn
as two `fixed` nodes with a source between them reports nothing at any firing
rate at all, because a fixed node is a reservoir and is never asked to balance.

It is **directed**: `from` is the inlet and `to` is the outlet, so `angle` is
refused as it is on `flow`. What it carries is taken away at the outlet, which
is where the medium leaves; nothing is asked of the inlet, which is where it
arrives from outside the drawing. A stream that is *cooled* needs no different
statement — its number comes out negative, and heat arrives at the outlet
instead.

**Heat is added by cutting the run into segments, not by a field.** Two stream
branches from `in` through `mid` to `out` each ask their own outlet for their
own share, so a preheater on `mid` and a main zone on `out` balance
separately. That is how a distributed transfer is drawn: as the number of
lumps you are willing to defend, each one visible.

It states the two together or neither: a mass flow with no specific heat says
nothing about heat, and a stream with neither draws its label alone, as any
path with no number does. It states no `value` and no `rate` — its number is
worked out, and stating a result as an input is how the two come to disagree —
and it does not take `count`, since a group would be drawn with no number
under it. Write the strands out.

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

The hatched face belongs to the **source**, not to the node, and it sits at
the source's own `at` whichever direction the arrows go: with `from` they
leave that face and travel away, and with `to` they leave it and travel to
the node. `{"to": "furn", "kind": "flux", "at": [60, 200], "angle": 0}` puts
the face to the left of the node with its arrows arriving.

`at` is the **centre of the symbol**, not its head or its tail, exactly as it
is on a branch. `angle` is the direction the arrow points, `0` being to the
right. A lead is drawn from the symbol to the node whichever you choose — and
the lead is a wire like any other: labels are pushed around it and symbols
can be reported as crossed by it, so a source moved further out has a longer
lead, and `at` decides what that lead runs past. Three of one reader's
findings were leads.

Leave `at` out and the source is placed along its own `angle` — 0 if you
give none, which is along +x — 110 units from the node, half the narrowest
run: on the far side of the node for a `to`, so the arrow travels in the
direction the angle names and arrives, and on the near side for a `from`, so
it leaves. `{"to": "sh", "kind": "radin", "angle": 90}` puts the source
above its node with the arrow pointing down into it. That is right for
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
places the line, and it is optional: left out, the rail goes 222 below the
lowest node, which for a solved ladder on `y = 150` is the 372 above.

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
    {"id": "j",   "label": "Junction",  "sub": "j",   "value": "126", "at": [200, 150]},
    {"id": "c",   "label": "Case",      "sub": "c",   "value": "110", "at": [424, 150]},
    {"id": "s",   "label": "Sink base", "sub": "s",   "value": "103", "at": [648, 150]},
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

That file is `examples/hero.json`, the worked example this page and the
tests use.

## Coordinates

`at` is optional on a node. Leave it out and the library places the node;
give it and the node goes exactly there. Within a chain the two mix: a node
with `at` keeps it, and the solver measures the next one from it. A network
that is not a chain is refused whole the moment any node lacks `at` — the
solver does not place part of it — so give every node `at` there, as the
refusal says. Wire runs, label positions and the canvas size are worked out
either way.

What is solved is a **ladder**: the nodes form one chain, each joined to at
most two others by branches (`rail` and sources do not count). Heat runs left
to right from the hot end — the end with the higher stated temperature, or
failing numbers the end a source arrives at, or failing that the one written
first — along one line at `y = 150`, and each run is as wide as the labels on
it need and never narrower than 220. Two branches between the same pair of
nodes are routed one above and one below, 80 off the line, leaving and
arriving 48 sideways of each node, and their labels take the outer sides; a
third between the same pair keeps the straight run, and a repeated branch
always does. A source without `at` is placed 110 out along its `angle`, half
the narrowest run, and an `angle` of 0 on any node but the hot end is turned to arrive
from above, because on the line "from the left" is the branch, and one
leaving is turned to leave downward. A node with a source above it and a
wire below it — a capacitance, or a source leaving — gets `angle: 45` for
its label, since above is the lead, below is the wire and beside is the run;
an `angle` you wrote is kept.

Anything that is not a chain is refused, naming the node that joins three
others: give that node `at`, and `via` to the branches that leave it
sideways. Nothing is drawn badly in silence. A general placer is the network
layer proper; a chain is the shape nearly every network in this notation has,
placed the way the gallery's authors placed theirs by hand.

`via`, and `at` on a branch or a source, are absolute coordinates. A file
that leaves node `at` out should leave those out too, or the solver places
its nodes around waypoints written for a different layout.

`thermodraw solve diagram.json` writes the file back with every node placed,
which is how to start from the solver's numbers and move what you would have
put elsewhere. `describe` marks a node the solver placed with `solved` on its
row, and a `check` remedy that says to move such a node with `at` means give
it one: the row says what number to start from.

Whether you place nodes or the solver does, the habit is the same: heat runs
left to right, hottest node on the left, the reference rail along the bottom.
Space nodes about 220 apart and put parallel paths 80 above and below the
main line.

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
a boundary node whose wall is below it.

Reach for `angle` when `side` runs out. `side` offers four directions, and a
node fanning three ways with a capacitance below it and a source coming in has
five attachments for four slots. Only `angle` reaches the diagonals.

Two more details are worth copying rather than rediscovering:

- **Leave a node sideways before turning — at both ends.** A `via` that goes
  straight up from a node puts a wire exactly where that node's label wants
  to sit, and the label steps out past it — ending up nearer the branch than
  the node it names. The hero turns at `x = 696` for a node at `x = 648`.
  Give the turn 40–90 units of clearance. The same is true of the end a
  branch *arrives* at: the hero's parallel pair drops straight down onto its
  ambient node and gets away with it only because that node has `angle: 90`
  and no other traffic. A node with three branches and a source on it does
  not, and one reader traced four findings to copying the hero's arrival.
- **In a file where you place the nodes yourself, a parallel pair needs
  `via` first, and then `side`.** (Leave `at` off the nodes and the solver
  routes the pair for you, as the Coordinates section says.) Two branches
  between one pair of nodes share a single straight run, and both their
  symbols are drawn at the same point on it — which is a `symbols-overlap`
  error, not a label problem. `side` moves labels; it does not make the
  second wire. So give one of the pair a `via` that carries it clear —
  `[[x0, y], [x1, y]]` at 80 or so off the main line — and *then* set
  `"side": "up"` on the upper branch and `"side": "down"` on the lower one.
  Setting `side` alone is a recipe for the error it looks like it prevents,
  and one reader lost two rounds to it.
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

The two habits above are no longer advice. They are checks, and so are ten
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

"11 labels placed" is every node, plus every branch and every source — so it
is the count you can work out from the file, and a
number lower than that means a label was dropped rather than moved. It exits
0 when clean, 1 on a warning or an error, and 2 when the file could not be
read or was not a diagram. A note is advice and does not fail the run — the
report above exits 0 — unless you pass `--strict`. `--json` for a machine,
`--quiet` for findings alone. From Python it is `check(diagram)`, returning a
report with `.ok`, `.findings` and `.text()`; a `DiagramBuilder` has `.check()`
beside `.svg()`.

Exit 1 means findings and only findings. A diagram that cannot be drawn is
refused before drawing and exits 2, and so does anything else that stops the
tool answering, so a script may gate on the status alone.

**A finding's `where` is positional, and so is every id built from it.**
Branches and sources have no id in this schema, so they are named by
position — `branch 2 j->c`, `source 0 -> j` — and that is also what the
`td-…` element ids in a `page` are hashed from. Insert a branch above and
every later name shifts. Ids are stable within one revision of a file, which
is what a page toggling a group needs, and not across edits: anything
diffing `--json` output or scripting against a saved page has to key on
something of its own.

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
| `wire-through-wall` | warning | a route passing through a boundary node's hatching, which is drawn below the node and cannot be turned |
| `symbol-off-its-run` | warning | a branch's box placed with `at` off the line its own wire takes, so the run jogs out to it and back |
| `frame-off-centre` | warning | the `size` you fixed leaves lopsided margins |
| `run-off-axis` | note | a run within 15 degrees of square but not on it, so its wire and its box are drawn on a slant. A branch with `via` is exempt; so is a diagonal meant as one |
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
- `parallel-pair-same-side` is a note rather than a warning because the hero
  diagram breaks it and is fine. Take it as a prompt to look, not an error.
  Its remedy names the branch and the side, derived from where the two
  labels landed; three or more branches between one pair get one note and
  no `side`, because none clears it.

Two things it does not check by default: whether the numbers are right, and
whether the network is the one you meant. It reports how the drawing reads,
not what it says.

Behind `--physics` — from Python, `check(diagram, physics=True)` — is a
check that asks the first of those, in the only form that needs no model
of anything: do the stated numbers agree with each other? At every `free`
node with a temperature, what arrives by sources and `flow` must leave by
resistances at `(T_here − T_there) / R`, with `count` folding a group the way
this page says a count folds.
Two codes, both warnings: `node-does-not-balance`, which lists every term so
you can see which one is off, and `rate-does-not-match`, for a branch whose
`rate` disagrees with what its ends imply. One note beside them:
`rad-needs-absolute-scale`, when `units.T` declares a rise and a `rad` branch
carries a value, since a radiation resistance holds at a pair of absolute
temperatures the page then cannot state. A fixed node is a reservoir and is
not asked; a `phase` node is holding latent heat this cannot see. A `free`
node is skipped when it has no temperature, when a **neighbour** has none —
which is what an interior junction drawn the way this page recommends does
to the nodes either side of it; `rail` is not a neighbour, and a capacitance
to it blinds nothing — when it carries a `flux` source, which has
no area, or when a value is not a number. Every skip is reported, as one
note per diagram: `physics-not-checked`, `checked 2 of 6 free places; not
checked: j (source 1 is a flux, which has no area); sm, cb (neighbour 'smb'
has no temperature); smb (it has no temperature)`. A diagram whose free
nodes were all checked gets no note. The units it reads are `R` in `K/W`,
`°C/W`, `C/W`, `mK/W` or `K/kW`, and `P` and `q` in `W`, `kW` or `mW`; any
other is the same note with nothing checked, not silence. `C` is never read
(steady state) and `T` is used only as differences, so `K` and `°C` both
work and `kJ/K` costs nothing.

It is opt-in, and stays so: a sketch with placeholder numbers is a diagram
too, and would fire at every node it has. Ask for it when you believe the
numbers. When it was written every diagram in this repository fired it, the
hero included — its temperatures were not the results of its own power and
resistances, and now are. The gallery is left as its agents drew it.

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

rail: y 372, span (200, 936), reference 'amb'

network:
  j --cond-- c
  c --contact-- s
  s --conv/rad-- amb
  j --cap-- rail
  s --cap-- rail
  source 0 --diss-> j

nodes:
  j              free     at (200, 150)
  c              free     at (424, 150)
  s              free     at (648, 150)
  amb            fixed    at (936, 372)

elements:
  branch 0 j->c          symbol/cond     (312, 150)        above         103x33   Die attach | R_cond = 0.35 K/W
  branch 1 c->s          symbol/contact  (536, 150)        above         113x33   Grease | R_contact = 0.15 K/W
  branch 2 s->amb        symbol/conv     (816, 70)         above         102x33   Fins → air | R_conv = 1.80 K/W
  branch 3 s->amb        symbol/rad      (816, 238)        above          97x33   Case → walls | R_rad = 6.40 K/W
  branch 4 j->rail       symbol/cap      (200, 278) a90    right          72x33   Die | C_j = 0.9 J/K
  branch 5 s->rail       symbol/cap      (648, 278) a90    right          70x33   Sink | C_s = 86 J/K
  source 0 -> j          symbol/diss     (96, 150)         above          77x33   Switching loss | P_d = 45 W
  node 'j'               node            (200, 150)        above          70x33   Junction | T_j = 126 °C
  node 'c'               node            (424, 150)        above          72x33   Case | T_c = 110 °C
  node 's'               node            (648, 150)        above          72x33   Sink base | T_s = 103 °C
  node 'amb'             node            (936, 372) a90    right          78x33   Still air | T_amb = 40 °C
  wall of node 'amb'     ground          (936, 384) faces down (no label)
```

That is the real output for `examples/hero.json`, not an abridgement. Element
counts against what you wrote, the canvas you will get, where each symbol
sits and which way it is turned, what each label reads, and which way it
went. The turn is printed as `a90` after the position and **only when there
is one**: a row with no `a` marker is at angle 0, not unreported. Printing
`a0` on every row of a flat ladder would bury the one source that is turned. Three marks say where the solver had to work: `flipped` means the label
tried its automatic side, found it blocked, and took the opposite one;
`pushed N` means it was moved `N` units out along its side to get clear of
something, and `check` reports it as adrift past 8; `OVERLAPS` means the push
loop gave up and the label is printed over something — always a
`label-collision`. Above, `branch 2` and `branch 3` both went "above", which
is the parallel pair `check` notes, visible directly rather than only graded.

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
