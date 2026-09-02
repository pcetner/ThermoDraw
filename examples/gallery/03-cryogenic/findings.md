# Findings — 03-cryogenic

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent).
Read `docs/schema.md` and `brief.md` only. Three rounds to a clean `check`
(0 errors, 0 warnings, 2 notes, exit 0).

---

## 1. Things I could not express

Ranked by how badly the drawing now misrepresents the brief.

### 1.1 The cryocooler does not exist in the diagram — worst of these

The brief's central object is **one machine with two stages**. What I could
draw is two unrelated arrows: a `flow` source with `from: "shield"` valued 35,
and a `flow` source with `from: "cold"` valued 1.5. Nothing in the file says
they are the same cold head, and nothing says the 1.5 W lifted at 4.2 K is
rejected *into* the 40 K stage on its way out. The schema is blunt that this
cannot be fixed: "A source has **one end**, so a `flow` or `flux` annotation
cannot join two nodes however suggestively you place two of them: heat carried
from one node to another by a moving fluid has no branch kind yet".

**How misleading:** substantially. A reader sees two heat sinks of independent
capacity, when in fact stage 2's lift is a load on stage 1 and the two
capacities trade against each other along the cooler's load line. I did not
substitute anything — I deliberately placed the two arrows on different sides
of their nodes (stage 1 straight down from the shield, stage 2 out to the right
of the cold mass) so they do not *look* like a matched pair, rather than lining
them up and implying a link the data does not contain.

What I wanted: an active-cooling element with two terminals and a direction,
along the lines of `{"from": "cold", "to": "shield", "kind": "cooler"}`, or,
failing that, any way at all to group two sources under one name.

### 1.2 There is no way to say "this is a capacity, not a load"

35 W and 1.5 W are what the stages *can* remove at 40 K and 4.2 K. They are not
what is arriving. The brief says "removes", so I wrote them as removed heat,
and `check --physics` immediately and correctly reports that neither node
balances: 2.85 W arrives at the shield against 35 W leaving, and 0.22 W at the
cold mass against 1.5 W leaving.

The physics check's own remedy is *"if a temperature is a limit rather than a
result, or a flow is a capacity rather than a load, say so in the `label`"* —
that is, write prose into a text field, and the check goes on failing anyway.
It is not a schema feature, it is a note to the human. There is no
`kind: "capacity"`, no boolean, nothing the checker can act on.

**I left the diagram alone.** The numbers are the brief's; making the drawing
pass by rewriting them would be falsifying data to please a tool.

### 1.3 The rail reference is a lie I was forced to tell

`rail.reference` "must name a node that exists". The 900 J/K of cold mass is
referenced to **absolute zero**, not to any node in this diagram. My three
nodes are the vessel, the shield and the cold mass; none of them is the
reference for a heat capacity. I wrote `"reference": "vessel"` because the
field must name an existing node and the vessel is the only fixed one. The
schema says `reference` "is documentary and does nothing", so nothing computes
wrongly — but `describe` prints `reference 'vessel'`, and that sentence is
false.

What I wanted: to omit `reference`, or to name something that is not a node.

### 1.4 The three temperature levels are not nested in the drawing

Physically this is a vessel *containing* a shield *containing* a cold mass —
concentric. The schema's whole vocabulary is a one-dimensional chain from hot
to cold, and containment has no representation. `fixed` draws "the boundary
wall" for the vessel, the closest thing available, but the shield, which is
also a physical enclosure around the cold mass, draws as a plain `free` node
identical to a junction in a heatsink stack. A reader cannot tell from the
drawing that the 40 K shield wraps the 4.2 K mass.

**How misleading:** moderately. The thermal network is right; the geometry of
the object is entirely absent. I did not fake it.

### 1.5 The HTS leads are one physical object doing two things

The leads conduct (1720 K/W, vessel to shield) *and* dissipate 1.2 W at the
shield. That is one component. In the file they are `branch 1` and `source 0`,
with no relationship recorded, and the source hangs off the shield rather than
off the lead. I labelled it "HTS lead Joule heating" so a human can connect
them by reading; the data does not.

I could not put the `diss` source **on the branch** — sources attach to nodes
only. There is no distributed dissipation along a resistance, which is exactly
what a current lead is.

### 1.6 The leads' conducted heat is unstated and I could not mark it unknown

The brief gives a rate for five of the six branches but not for the HTS leads.
So `branch 1` has a `value` and no `rate`, which reads as "nobody measured it"
— and reads identically to "this path carries nothing worth saying".
`check --physics` in fact computed it (0.151 W) from the two end temperatures
and printed it, which is more than the drawing does. There is no way to write
"unknown" or "derived" in a `rate`.

### 1.7 MLI is not really a resistance and the schema cannot hedge

Radiation through multilayer insulation is a `rad` branch with
`R_rad = 289 K/W` — a linear resistance between 300 K and 40 K. Real radiation
goes as the fourth power of temperature, so a single K/W number is valid only
at these two temperatures. There is no way to say "this resistance is
linearised about this operating point"; `mixed` exists for an unstated
mechanism, but that would *lose* information (that it is radiation) rather than
add the caveat. I used `rad` and accepted the approximation, which is what the
brief's own numbers already assume.

---

## 2. Where the documentation failed me

### 2.1 "Leave `at` out and the source is placed ... with room for its label"

Quoted in full: *"Leave `at` out and the source is placed along its own `angle`
with room for its label — on the far side of the node for a `to`, so the arrow
arrives, and on the near side for a `from`, so it leaves. That is usually what
you want."*

It is **38 units** from the node. `describe` on round 1: `shield` at (620, 340),
source 0 at (593, 367). For a 123-wide label that is not "room". Two sources on
one node overlapped by 1 pixel — an **error** — and both labels were shoved
130+ units. The sentence should say that automatic placement assumes one source
per node, and that a node with two sources needs an explicit `at` on at least
one of them.

### 2.2 The corridor metric is undocumented, and is not what the wording implies

`label-in-a-corridor` says *"its label sits inside a loop of the network, 48
from the opposite path"*. I read "the opposite path" as the other branch of the
loop — the far horizontal lane, 240 units away. It is not. Working backwards
from the numbers: the label was 164 wide centred at x = 830, spanning 748 to
912; the loop's vertical riser was at x = 700; 748 minus 700 is 48. The
measurement is the **horizontal** clearance to the loop's riser, and the
threshold is roughly the label's own height. Once I worked that out the fix was
obvious — widen the loops, put the narrowest label on the middle lane — and it
worked first time. Nothing in the docs would have got me there.

### 2.3 "Leave a node sideways before turning" is stated only for the departure end

Quoted: *"A `via` that goes straight up from a node puts a wire exactly where
that node's label wants to sit ... The hero turns at `x = 696` for a node at
`x = 648`."*

Both examples are the end the branch *leaves*. The hero's parallel pair then
drops **straight down onto** `amb` at x = 936, and the hero survives that only
because `amb` has `angle: 90` and no other traffic. I copied the hero faithfully
and it was the single cause of four of my round-1 and round-2 findings. The real
rule is: **do not put a wire on any cardinal side of a node whose label needs
that side, arrival end included.** That sentence is not in the doc, and the hero
is a misleading model for any node with more than two branches.

### 2.4 The `parallel-pair-same-side` remedy is written for exactly two branches

The remedy reads: set `side` to "down" on the lower of the two. With three
parallel branches it is circular — it only renames which pair is reported
(verified in round 2: the note moved from the pair (0,1) to the pair (1,2)). And
the one escape, `side: "right"`, is actively harmful: on a horizontal branch it
pushes the label along the wire into the next node, and `check` then tells you
to set it back (verified in round 3b: 2 errors, 4 warnings). Neither the note
nor the `side` table warns that "left" and "right" are meaningless on a
horizontal run.

### 2.5 The theme step is documented as mandatory, and the CLI does it for you

Quoted: *"`render` alone emits CSS custom properties with no fallback, so pass
its output through `theme` before saving it ... Without one of them the file
draws nothing."*

`thermodraw render -o file.svg` writes a `:root{--sym:#1b1b1f; ...}` block. The
CLI already applies it. As written, the doc had me expecting to need a flag that
does not exist, or to abandon the CLI for the Python API. The paragraph should
say it applies to the Python `render()` function only.

### 2.6 `check` corrupts its own output on a Windows console

The `--physics` report contains an em dash and prints as a replacement character
under cp1252. It is cosmetic on stdout, but it means the tool writes non-ASCII
without forcing an encoding, which would be a data bug under `--json` on the
same terminal.

### 2.7 Nothing says which units the physics pass accepts

*"a unit the check does not know skips the diagram rather than guessing"* — but
there is no list. I guessed `"T": "K"` (the hero uses degrees Celsius) and it
worked. Had it not, the failure mode is *silence*: I would have read a clean
run as a pass when the physics pass had simply declined to run.

---

## 3. What I had to guess at, and whether the guess was right

| guess | right? |
|---|---|
| `"T": "K"` is a unit the physics pass knows | **yes** — it computed dT over R correctly and reported in W |
| heat *removed* is a `flow` source with `from`, not a negative `diss` | **yes** — `diss` refuses `from`, and the physics pass counted my `from` sources as "leaves", which is what I meant |
| a `cap` branch to `rail` is how you state 900 J/K | **yes** — it draws, and the physics pass ignores it in steady state, which is correct |
| the leads' Joule heating is `diss`, not `radin` or `flow` | **yes**, by the schema's own definition of `diss` as dissipation *appearing* at a node |
| `title` is accepted and not drawn | **yes** — no 14th label appeared |
| omitting `size` is safe | **yes** — canvas came out 1397 x 801, measured from the drawing |
| omitting `rail.span` is safe | **yes** — defaulted to (200, 1320), the node extent |
| `via` may double back to rejoin the main line before the node | **yes**, and this turned out to be the key move of the whole exercise |
| a source's `angle` may be any number, not a multiple of 45 | **yes** — `angle: 55` renders and `describe` reports `a55` |
| leaving `at` off a source is fine | **no** — see 2.1 |
| the hero's vertical-arrival routing generalises | **no** — see 2.3 |

I did not open `examples/hero.json`; the schema quotes it whole, so I did not
need to. What I *did* want and could not have was a **second** worked example —
one with more than two parallel branches, and one with two sources on a single
node. Every layout problem I hit lives in that gap, and the hero has neither.

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

**Partly. It was the most useful command available, and it is not enough.**

What it confirmed: the network block reads

```
  vessel --rad/cond/cond-- shield
  shield --rad/cond/cond-- cold
  cold --cap-- rail
```

which is exactly the topology I intended, and it proved the network was in one
piece. The 13-label count matched what I could compute from the file by hand.
The per-element rows gave me label widths and `pushed N` distances, which is the
only reason I could reason about the layout at all: `check` reports symptoms,
`describe` reports state. I would not have got past round 1 without it.

What it should have said and did not:

1. **Sources do not appear in the network block at all.** My two cryocooler
   stages and the Joule heating are 3 of 13 labels and they are the entire point
   of the brief, yet the topology summary is silent about them and `shield`
   reads as a passive junction. Lines along the lines of `shield <-diss- 1.2 W`
   and `shield -flow-> 35 W` would have let me verify every arrow's direction
   without rendering anything.
2. **Direction is nearly invisible.** `flow` is "the only **directed** branch",
   and sources have direction too — that is the whole difference between 35 W
   arriving and 35 W leaving, and it is the thing I was most likely to get
   backwards. `describe` does encode it in the element rows, as
   `source 1 shield ->` versus `source 0 -> shield`; but the network block,
   where you would actually look, uses `--` for everything.
3. **No `rate` in the element rows.** They print label *text*, which happens to
   include `q = 0.9 W`, so I got it by luck. A branch with a `rate` and no
   `label` would show nothing.
4. **Nothing about physical sense.** It never observes that 300 to 40 to 4.2 K
   is monotonic, or that the shield lies between the other two. That is what
   `--physics` is for, and `--physics` only checks balance.

Between `describe` and `check` I am confident the *drawing* is the one I meant.
Neither tells me the *diagram* is. The docs' own words are that `check` "cannot
tell you the drawing is the one you meant"; `describe` only half-fixes that,
because it drops the sources from its summary.

---

## 5. Features the library lacks, ranked by what they cost me here

1. **A two-terminal active-cooling element.** Cost: the brief's title object, a
   two-stage cryocooler, is not in the diagram as an object at all (1.1).
   Everything else on this list is smaller than this one.
2. **A way to mark a number as a capacity or limit rather than a load.** Cost:
   two standing `node-does-not-balance` warnings that are correct arithmetic on
   numbers never meant to balance, with no way to say so in data (1.2). The
   library already has the concept, since the remedy text names it; it just has
   no field for it.
3. **Automatic layout.** Cost: essentially all three rounds. Every finding I hit
   was a coordinate problem, not a physics problem, and the schema admits the
   network layer "is not built yet". A 3-node, 7-branch, 3-source diagram needed
   14 hand-chosen coordinates and two full re-plans.
4. **A group for related-but-not-identical parallel paths.** `count` plus
   `arrangement` handles N *identical* paths. It cannot express "three different
   paths in parallel", which is exactly what a cryostat stage is, so the
   parallel-group drawing machinery (the comb, the condensed form, the `page`
   control) is unavailable to the commonest cryogenic figure there is. I
   hand-built a three-lane comb out of `via` waypoints and earned two permanent
   notes for it.
5. **Sources attachable to a branch.** Cost: 1.5 — a current lead that both
   conducts and dissipates must be split into two unrelated objects.
6. **Any notion of enclosure or nesting.** Cost: 1.4 — the concentric geometry
   that makes this a dewar rather than a heatsink is entirely absent.
7. **`side` values that mean something on a horizontal branch.** Only "up" and
   "down" are usable, which makes `parallel-pair-same-side` unclearable for any
   group of three or more (2.4).
8. **Ids on branches and sources, and any way to relate two elements.** Even a
   bare `id` would let a file say "these two arrows are one machine", or "this
   source belongs to that branch". Items 1, 5 and 8 are all symptoms of the same
   hole: the format has no way to state that two elements are related.

---

## 6. Standing findings at the end

- `parallel-pair-same-side` x2 (notes; exit 0). **Unclearable.** Three parallel
  branches, two usable `side` values, so by pigeonhole two must share one. The
  printed remedy is circular and the only alternative is worse. The failed
  attempt and its full output are in `rounds.md`, round 3b. The schema itself
  blesses leaving this one: it is "a note rather than a warning because the hero
  diagram breaks it and is fine".
- `node-does-not-balance` x2 under `--physics` (warnings). **Not addressed, by
  choice.** The numbers are the brief's, they are cryocooler capacities rather
  than loads, and the drawing should say what the brief said. The check's
  arithmetic is right, including the 0.151 W it infers for the HTS leads, a
  number the brief never states. The disagreement is real information, not a
  defect in the drawing.
