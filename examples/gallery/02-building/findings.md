# Findings: two-zone house with a ground-coupled slab

Written from `docs/schema.md` and the brief alone. Eight `check` runs, of which
four were spent applying the checker's own remedies literally. Final state:
23 labels placed, 0 errors, 0 warnings, 0 notes; rendered to `house.svg`.

**Disclosure.** The harness injected `CLAUDE.md` into my context automatically,
before I was given the brief, so I saw it without choosing to. I did not open
it, `README.md`, `src/`, `tests/`, or any other file under `examples/`. What I
could have taken from it: that the network layer and region enclosures are
unbuilt, and that colour is unused. None of that changed a coordinate. All the
schema knowledge below came from `docs/schema.md` and from running the tools.

---

## 1. What I could not express

### 1.1 Advection between two nodes. This is the big one.

Two of the ten heat paths in the brief are air physically moving, not a
resistance:

- infiltration, 0.5 ACH carrying outdoor air into the ground-floor zone, worth
  185 W of loss ("It is not a conduction or convection resistance - it is air
  physically moving from outside to inside")
- the open stairwell, worth 240 W of transport from the lower zone to the upper

The schema's only construct for a bare power is a **source**, and a source has
exactly one end: "Give it **`to`** for heat arriving at that node, or
**`from`** for heat leaving it". There is no two-ended power. There is no
branch `kind` that carries a `q` instead of an `R`.

What I drew:

| brief | drawn as | what the page does not say |
|---|---|---|
| infiltration, `out` -> `zg`, 185 W | `{"from": "zg", "kind": "flow", "value": "185"}` | that the heat goes to the outdoor air, or that it is carried by air arriving from `out`. `out` appears nowhere in it. |
| stairwell, `zg` -> `zu`, 240 W | `{"to": "zu", "kind": "flow", "value": "240"}` | that it comes from `zg`. Only the words "Stairwell from lower zone" say so. |

**How misleading: badly, and in a way a careful reader will act on.** The
stairwell version breaks the energy balance on the page. 240 W appears at `zu`
out of nothing, and the same 240 W does not leave `zg`. Anyone who sums the
arrows at the ground-floor zone - 600 W gains, 850 W solar, 185 W infiltration
out - over-counts its net input by 240 W. Choosing `{"from": "zg"}` instead
just moves the hole to `zu`. There is no placement that balances both nodes.

Two alternatives I rejected, and why:

- **Two sources, one at each end, both 240 W.** Prints "240 W" twice on the
  page and reads as 480 W of transport. Worse.
- **Convert to a resistance.** The arithmetic is available: infiltration is
  25 K / 185 W = 0.135 K/W, the stairwell 2 K / 240 W = 0.0083 K/W. But the
  brief explicitly says infiltration is not a conduction or convection
  resistance, and the resistance subscript "is **not** yours to set", so the
  page would read `R_conv = 0.135 K/W` and name physics that is not happening.
  I did not do this, and I would flag it if I saw someone else do it - it is
  exactly the kind of silent substitution that looks fine and is wrong.

### 1.2 A path that is two mechanisms at once

The window is "conduction and convection through the glazing at 0.31 K/W". The
steel lintel runs "from zone air to outdoor air", so it too includes both
surface films. `kind` takes exactly one mechanism, and the subscript follows
from it and cannot be overridden.

Both are drawn as `cond`, so the page reads `R_cond = 0.31 K/W` and
`R_cond = 0.42 K/W`, with section hatching, for paths that are substantially
convective. **How misleading: moderately.** The numbers are right and the
topology is right; what is wrong is the claimed mechanism, and a reader who
trusts the interior texture will assume both are linear in T and insensitive to
wind, which is not true of either. There is no `kind` for a lumped or
combined-U path, and no way to blank the mechanism subscript.

### 1.3 A junction with no temperature

The external wall is four layers in series plus a surface film, so it has four
interior interfaces. The brief gives no temperature for any of them - they are
outputs of the model, not inputs.

A `free` node with **no `label`, no `sub` and no `value` at all** still renders
a lone italic `T`. From `describe`:

```
  node 'w1'              node            (1160, 620)       above           7x17   T
```

There is no way to write "this node exists and I do not know its temperature".
I used `"kind": "corner"`, which prints nothing. **How misleading: mildly, but
it loses something real.** The series chain still reads correctly - five boxes
in a row - but the four interfaces are no longer objects on the page. Nobody
can point at "the wool/OSB interface", nothing can be attached to it later, and
the label count silently drops from 27 to 23, so the number the schema tells
you to check against your file no longer matches your file.

### 1.4 The wall assembly is not a thing

The brief says the lintel runs "in parallel with the whole wall assembly". The
diagram can only put it in parallel with a chain of five boxes; there is no way
to draw a box round those five and call it "External wall". Nothing in
`docs/schema.md` offers grouping, regions, or any non-electrical annotation.
The relationship survives as topology and dies as emphasis.

### 1.5 A capacitance in MJ/K

Zone air masses are 2.1 and 1.8 MJ/K. Units are one string per quantity, so I
set `"C": "MJ/K"` and wrote `"2.1"`. It worked - `describe` shows
`C_gf = 2.1 MJ/K`. But see section 3: this was a guess, because the schema
names no legal unit strings.

### 1.6 A dangling sub-network, unremarked

The brief gives the roof a temperature and two parallel paths out, and no
resistance from either zone to it. So `roof` is wired only to `out` and `sky`
and has no path to the rest of the network. That is faithful to the brief. It
is also exactly what a misread brief would look like, and neither `check` nor
`describe` mentioned it. I would have wanted to be told.

---

## 2. Where the documentation failed

**The checker's remedies. Quoted claim:** "Every finding names the schema field
that fixes it." Three of the four remedies I applied literally were wrong.

1. *"move a `via` waypoint on source 2 zg -> so it does not run past this
   label"* - **sources have no `via`.** The library rejects it:
   `source 2: unknown field 'via'. Expected: angle, at, from, kind, label,
   side, sub, to, value`. The remedy is branch wording emitted for a source
   blocker. There is no possible literal action.

2. *"set `side` to one of the two the solver does not try (it tries only the
   sides of the branch)"* - on a **vertical** branch the two untried sides are
   `up` and `down`, which lie along the wire. Applying it put the label on the
   branch's own wire and turned one warning into an error plus a warning. The
   remedy does not know the branch's orientation, and for any vertical branch
   it is guaranteed to be wrong.

3. *"`angle` for a direction between those four"* - this is the **node**
   remedy. On a branch, `angle` "overrides the direction taken from the wire",
   i.e. it rotates the symbol. Applying it cleared the finding and left the
   slab's conduction box lying at 45 degrees across a vertical wire
   (`describe`: `branch 7 zg->grd symbol/cond (760, 880) a135`). `check` then
   reported the diagram clean. **This is the worst of the three, precisely
   because it appears to work.** A finding whose remedy exits 0 while breaking
   the drawing is worse than no remedy.

   Round 6 is the honourable case: remedy 1 applied cleanly to a branch
   blocker, and traded `label-adrift` for `wire-through-symbol`. The slab
   label's x-band (920-1080) and the gypsum symbol's (988-1072) overlap, so no
   turn clears both. Locally correct, globally impossible; the finding cannot
   see that, and should probably not pretend to.

**Rail landing points. Quoted:** *"`"to": "rail"` drops straight down to the
reference rail from wherever the other end is"* and *"Give it `via` if you want
it somewhere else: waypoints work on a capacitance exactly as they do on any
other branch, which is how you free up the space directly under a node that
already has too much attached to it."*

That is exactly the situation I was in, and I read it wrong. A single waypoint
`"via": [[480, 380]]` moved the wire sideways but **not** the point where it
meets the rail, which stayed directly under the node, so the last leg became a
long diagonal - `describe`: `symbol/cap (480, 1200) a81.8699`. `check` said
nothing. You need **two** waypoints, the second on the rail line:
`[[480, 380], [480, 1420]]`. The doc should say the rail landing x is the
node's x unless a waypoint lands on the rail line itself.

**Unlabelled nodes.** Nothing says what a node with no `label` renders as. It
renders a bare `T`.

**Unit strings.** *"A value whose quantity has no entry here is refused, so
that a number never reaches the page without its unit."* This says the
*quantity* is validated. It does not say whether the unit *string* is checked
against a list. There is no list. `"MJ/K"` was a guess.

**Attachment budget.** The best sentence in the document is *"a node fanning
three ways with a capacitance below it and a source coming in has five
attachments for four slots. Only `angle` reaches the diagonals."* It was still
not enough: `zg` here has six wires and three sources. Nothing tells you how to
plan a node that dense, and the answer I converged on - push the capacitance
into its own column with a two-waypoint `via`, and put both label-bearing
sources on the one clear side - took four rounds to find.

---

## 3. What I guessed at, and whether it was right

| guess | right? |
|---|---|
| `"C": "MJ/K"` as a unit string | **Yes** - accepted, renders `2.1 MJ/K` |
| `corner` nodes as silent series junctions, excluded from the label count | **Yes** - count went 27 -> 23, exactly four |
| `cond` for the window's combined conduction+convection | **No** - it draws, but names the wrong physics (1.2) |
| `flow` source as the least-bad advection | Right that it is the only option; wrong to think it was adequate (1.1) |
| Two waypoints to land a capacitance drop off the node's column | **Wrong first time** - one waypoint gives a diagonal (round 4) |
| Wall nodes 260 apart with 110-wide labels | **Yes** - `nodes-too-close` never fired |
| Lintel `side: up`, glazing `side: down` for the parallel pair | **Yes** - `parallel-pair-same-side` never fired |
| `out` can take four branches with only three free sides (its wall occupies below), so the lintel and glazing share the last 160 units of wire into it | **Unconfirmed.** Nothing checks overlapping collinear wire, and the brief forbids opening the SVG. I do not know whether that reads as a clean merge or as a mistake. |
| `rail.reference: "out"` naming a node not on the rail | **Yes** - explicitly permitted, and `describe` echoes it so I could check it |

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Partly, and it was by far the most valuable tool here.** It caught two
defects `check` passed clean: the slab box rotated off its wire (round 4) and
the bare `T` on the wall nodes (round 7). Without it I would have shipped both,
because `check` exited 0 on both.

What it gave me that I relied on:

- the exact text of every label, so `R_cond = 0.185 K/W` and `C_gf = 2.1 MJ/K`
  could be read rather than assumed
- symbol orientation (`a90`, `a135`, `a81.8699`) - the only way I found either
  rotation bug
- which side each label went, with `flipped` and `pushed N`
- element counts per kind, checkable against the file

What it should have said and did not:

1. **The topology.** It lists nodes, and it lists elements by index, and it
   never once states what is connected to what, which nodes share a loop, or
   which are unreachable. `roof` is wired to nothing indoors and `describe` is
   silent. The stairwell source floats free of `zg` and `describe` is silent
   about that too. The one question `describe` exists to answer - "is this the
   network I meant?" - is the one it does not answer; I can only re-read my own
   `from`/`to` pairs, which is the labour it was meant to replace. A
   connectivity block (degree per node, connected components, and which node
   each source attaches to) would fix this.
2. **Wire geometry.** `wire x34`, and not one path. Every routing decision -
   nine `via` chains, the shared approach into `out`, whether a stub crosses a
   symbol - is invisible. The only wire fact I ever got was *inferred* from a
   symbol's angle.
3. **The label's rectangle.** It gives the symbol centre, the label size and
   the side, but not the label's actual box. I had to compute label extents by
   hand to plan around them, and got it wrong twice.
4. **A units line.** They appear inline in all 23 labels; one header line would
   let a reader check the diagram's units without reading all of them.
5. `describe` is not console-safe. `check`'s report is documented as ASCII
   because a Windows console is cp1252. `describe` prints `T_roof = 8 ?C` on
   that same terminal, and it is the command you run more often.

---

## 5. Features the library lacks, ranked by what they cost here

1. **Two-ended advection** - a `flow` branch, or a source accepting both `from`
   and `to`. Two of ten paths are drawn with one end missing, and the page does
   not conserve energy at `zg`. Nothing else on this list changes what the
   diagram *claims*.
2. **A combined-mechanism resistance**, or an override for the mechanism
   subscript. The window and the lintel are labelled `R_cond` for paths that
   are not pure conduction.
3. **A node that is a junction with no temperature.** Four wall-layer
   interfaces had to become invisible `corner`s to avoid printing a bare `T`.
4. **Remedies that know the element kind and the wire's orientation.** Three
   rounds spent, one of which silently broke the drawing while turning the
   report green.
5. **Topology in `describe`, and an unreachable-sub-network check.** I still
   cannot confirm from the tools that this is the network the brief describes.
   I can only confirm that it draws well - which is exactly the distinction the
   schema draws between `check` and `describe`, and `describe` does not yet
   close it.
6. **Region enclosures.** "The external wall assembly" is not an object, so
   "the lintel bridges the whole assembly" survives only as wire topology.
7. **The network layer.** Ten nodes, nine `via` chains and four source
   positions placed by hand over eight rounds. The only reason it was eight and
   not thirty is that the wall is a straight line; the moment two paths had to
   share a column, the coordinates became the whole job.
