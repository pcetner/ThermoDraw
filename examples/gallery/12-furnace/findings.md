# 12-furnace — findings

One check round, zero findings, no refusal. That is a weaker result than it
looks, and most of what follows is why.

## 1. What I could not express

### 1a. The 18 W/cm² and the 3000 W cannot be related, and the library will never notice

This is the largest gap by a distance. Both numbers are the brief's:

- the flame loads the face at **18 W/cm²**;
- the three brick courses carry **3000 W**.

Per square metre of wall those are **180 kW arriving** and **3 kW leaving**.
Physically that is fine — an incident radiative load on a hot refractory face
is mostly re-radiated, and only the net crosses the wall — but **the drawing
cannot say any of that.** There is no area on a diagram, so `q″` and `q` are
two unit systems that never meet, and there is no way to mark a source as
*incident* rather than *net*.

What I did instead: drew both numbers as stated and wrote nothing to
reconcile them. **How misleading: badly.** A reader who multiplies 18 W/cm² by
a square metre and compares it with the `q = 3000 W` on the brick will
conclude the diagram is wrong by a factor of sixty, and nothing on the page
tells them otherwise.

The sharp edge is that `check --physics` is *structurally incapable* of
catching this. The schema says a free node is skipped "when it carries a
`flux` source, which has no area" — and here the flux sits on a `fixed` node,
which is not asked at all, so not even the `physics-not-checked` note fires.
**The physics report is silent, with no skip note, on a diagram containing the
one number pair that does not close.** If a run is grading "did `--physics`
stay silent" as evidence the numbers are sound, this diagram is a
counterexample: it is silent because the bad pair is invisible to it, not
because it is right.

### 1b. "Per square metre of wall" is undrawable

Every number in this diagram is per unit area — 0.06 K/W, 0.18 K/W, 0.05 K/W,
0.075 K/W and the 3000 W are all per m². The schema has no field for a basis.
I put it in `title`, which the schema itself flags as **"optional, not
drawn"**. So the qualifier that makes every value on the page meaningful does
not appear in the SVG at all. The alternative was to smuggle it into a node
`label`, which would be a lie about what a label is. I did not.

### 1c. The refractory face is not a place in this drawing

The brief distinguishes the **furnace interior** (gas at 1200 °C, held by the
burners) from **the refractory face** that the flux lands on. My ladder has
one node at that end, so the `flux` source attaches to `furn` — the drawing
says 18 W/cm² arrives at the gas reservoir, not at the brick's inner surface.

To draw the face as its own node I would need a branch between gas and face,
and the brief gives no resistance for it: the radiative load *is* that
coupling, quoted directly as a flux. So the choice was a node with no path to
it (`network-in-pieces`) or the node I used. **How misleading: mildly.** A
furnace engineer reads the arrow as landing on the wall's hot face, which is
what is meant. But the format has no way to say "this source lands on the far
end of that branch, not on this node", and that is a general gap, not a
furnace one.

### 1d. The radiation resistance's operating point

`R_rad = 0.075 K/W` holds only at a 120 °C shell radiating to a 30 °C shop.
Nothing can state that. The drawing dashes the box, which says *"this value
holds at one operating point"* without saying **which**. Here the two
temperatures happen to be on the page adjacent to the branch, so a reader can
recover it; on a symbolic diagram they could not.

### 1e. "Both matter" is asserted, not shown

The brief says the shell loses heat two ways at once and **both matter**. The
drawing shows two parallel branches; it does not show that they carry 1800 W
and 1200 W — the whole point of "both matter". `rate` on each would have said
it, and both would have passed `rate-does-not-match`.

**I deliberately left them off**, because 1800 and 1200 are numbers I derived,
not numbers the brief stated, and the brief's instruction is that the values
are the brief's. Recording the choice here rather than making it silently: the
drawing is weaker for it, and a `rate` field that could be marked "derived"
would have let me have both.

## 2. Where the documentation failed me

### 2a. The bold parallel-pair rule contradicts the solver, and following it would break another rule

`docs/schema.md` says, in bold and with a war story attached:

> "**A parallel pair needs `via` first, and then `side`.** … Setting `side`
> alone is a recipe for the error it looks like it prevents, and one reader
> lost two rounds to it."

Forty lines earlier, the Coordinates section says the opposite for a
solver-placed file:

> "Two branches between the same pair of nodes are routed one above and one
> below, 80 off the line, leaving and arriving 48 sideways of each node, and
> their labels take the outer sides"

Both are true, of different files, and **neither passage says which case it is
about.** My `shell`/`shop` pair needed no `via` and no `side`: it placed
itself, and did not even raise the `parallel-pair-same-side` note.

Worse, the bold rule is unfollowable on a solver-placed file. Its remedy is
absolute `via` coordinates, and the same document says:

> "A file that leaves node `at` out should leave those out too, or the solver
> places its nodes around waypoints written for a different layout."

So the emphatic instruction, followed literally on a file with no node `at`,
violates another of the document's own rules. It cost me nothing **only
because the brief told me to leave `via` off**. Reading the schema alone I
would have followed the bold sentence and lost a round to it. The rule needs
the words "in a file where you place the nodes yourself".

### 2b. Two different numbers for where an auto-placed source goes, and both are wrong

Sources section:

> "Leave `at` out and the source is placed along its own `angle`, about 40
> units from the node"

Coordinates section:

> "A source without `at` is placed half a run out along its `angle`"

40 units and half a run are not the same number. What actually happened:
`source 0` landed at x = 90 with `furn` at x = 200 — **110 units**. The first
run is 520 wide, so half a run is 260. The observed value is neither figure.
Two statements, disagreeing with each other and with the code.

### 2c. The default `angle` of a source is never stated

Both passages above say a source with no `at` is placed "along its own
`angle`". Neither says what the angle is when you give none. I guessed 0 and
was right, but the sentence that would have told me does not exist. The
Angles section defines `0` as the default for a *node's* `angle`; it does not
say the same of a source.

### 2d. The page cannot show that a `rate` on a counted branch is the group's

The document is clear — "On a `count`ed branch it is the whole group's, not
per item" — and the library did the right thing. But the drawn label reads:

```
Firebrick courses | R_cond = 0.06 K/W | q = 3000 W | 3 in series = 0.18 K/W
```

Three numbers, and the *per-item* resistance and the *group* rate sit next to
each other with nothing distinguishing their basis; the derived group value
arrives on the line after. A reader is invited to take `q = 3000 W` as per
course, i.e. 9000 W through the wall. This is the one place where the
library's fold rigour does not reach the page: the group value is annotated
(`3 in series =`) and the group rate is not.

## 3. What I had to guess at

| guess | outcome |
|---|---|
| Attach the `flux` to `furn` rather than invent a refractory-face node | Drew cleanly; unverifiable whether it is what a reader wants (see 1c) |
| Source with neither `at` nor `angle` defaults to angle 0, arriving from the left | **Right** — face at x = 90, arrows arriving |
| `sub` on a `flux` source is mine to choose (`q″_rad`) | **Right** |
| Three `series` copies would fit whatever run the solver chose | **Right** — solver widened that run to 520 |
| Leave `units.T` as plain `"°C"` rather than declaring `scale: absolute` | No note fired, but `rad-needs-absolute-scale` only fires on a declared *rise*, so this guess was never tested |
| `fixed` for the furnace interior, wall default `down` | **Right** — nothing arrives at `furn` from below, so no `wire-through-wall` |
| A 126-wide node label ("Brick to board interface") would not force `nodes-too-close` | **Right** — the solver sizes runs to labels |

## 4. Did `describe` confirm the drawing was the one I meant?

**Yes, and it is the most valuable command in the toolchain.** The `network`
block —

```
furn --cond x3 series-- bb
bb --cond-- shell
shell --conv/rad-- shop
source 0 --flux-> furn
```

— is four lines that verify topology, count, arrangement and source direction
without rendering anything. `--conv/rad--` on one line confirmed the parallel
pair was one pair and not two accidental chains. Nothing was `flipped`,
`pushed` or `OVERLAPS`.

What it should have said and did not:

- **It does not distinguish `rate` from `value`.** Both arrive inside one
  label string. I could not confirm from `describe` that 3000 W had been read
  as the group's rate; I had to trust the prose in the schema. A field-level
  row — `rate 3000 W (group)` — would have closed 2d as well.
- **A ground row's facing is an angle, not a word.** `wall of node 'furn'
  ground (200, 162) a90` requires decoding `a90` into "faces down". The
  library's own vocabulary has the words `down`/`up`/`left`/`right` for this;
  the report does not use them.
- **The `units` block is never echoed.** The only evidence that `q″` parsed as
  U+2033 rather than being rejected is that the label text came out reading
  `q″_rad = 18 W/cm²`. That is inference, not confirmation. Given how loudly
  the schema warns about that one character, `describe` should print the
  units it read.
- It does not print `title`, so the one place I recorded the per-m² basis is
  invisible to every tool as well as to the page.

## 5. Was `check --physics` silent?

**Completely** — no findings and, notably, **no `physics-not-checked` note**,
so both free nodes (`bb`, `shell`) were genuinely checked rather than skipped.
They balance on the brief's unaltered numbers: 3000 W in and out at `bb`, and
3000 W in against 1800 + 1200 W out at `shell`.

No number was adjusted to get this. But see 1a: the silence covers only the
resistance ladder. The flux is on a `fixed` node and carries no area, so the
one pair of numbers in this brief that do **not** reconcile is outside the
check entirely, and the report gives no hint that anything went unexamined.
**A silent `--physics` should not be read as "the numbers close"; it means
"the numbers it can see close".** For this diagram those are different claims.

## 6. Features the library lacks, ranked by what they cost here

1. **An area basis** — per-diagram or per-element. Without it a `q″` and a `q`
   on the same page cannot be compared, `--physics` must skip any node with a
   flux, and "per square metre" is unsayable. Cost: the central defect of this
   diagram (1a, 1b).
2. **A drawn caption line.** `title` exists and is "not drawn". One drawn line
   of prose would have fixed 1b honestly and cheaply, without abusing a label.
3. **A source that attaches to an end of a branch**, i.e. to a surface rather
   than to a reservoir node (1c).
4. **An operating point on a `rad` branch** — the dashing means "holds at one
   operating point", and there is no way to state which (1d).
5. **A `rate` that reads as the group's on the page**, and a way to mark a
   rate as derived rather than quoted (1e, 2d).
6. **Incident vs net on a source.** A general version of 1a: two numbers that
   are the same quantity measured differently, with no way to say so.

Nothing in the *symbol* vocabulary was missing. Every element of this system
had a symbol: `cond`, `conv`, `rad`, `fixed`, `flux`, `count`/`series`. The
gaps are all in what the format can **state about** the numbers, not in what
it can **draw**.

## 7. Were the solver's coordinates ones I would have chosen?

Largely yes, and I moved nothing.

```
furn (200, 150)   bb (720, 150)   shell (1040, 150)   shop (1340, 150)
```

Hottest on the left, heat running left to right, the parallel pair symmetric
at y = 70 and y = 230, the flux face outboard at x = 90. That is the layout I
would have drawn by hand.

The one thing I would have changed and could not: **the runs are unequal —
520, 320, 300 — and the widest one is not the largest resistance.** The
firebrick run is widest because three series boxes have to fit in it, but the
brick group and the fibre board are *both* 0.18 K/W. A reader who takes
horizontal distance as proportional to thermal resistance — and in a wall
cross-section, which this drawing strongly resembles, that is a natural
reading — gets the brick wrong. I did not fix it: equalising runs means
giving every node `at`, which this brief forbids, and even then the three
boxes set a floor on that run. Worth knowing that a `series` count silently
distorts the only spatial cue the drawing has.

Two smaller ones, both left alone because the brief forbids `at` on a source
or a branch: I would have pushed the flux face another 30–40 units left for
air around `q″_rad = 18 W/cm²`, and I would have nudged the brick group's
label left of its symbol block rather than centred over three boxes, where it
reads as belonging to the middle course.
