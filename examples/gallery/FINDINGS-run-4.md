# What five agents found when they could not place a node

Run 4, 2026-09-03. The same five briefs as run 3 — `06` to `10`, copied to
`11-battery`, `12-furnace`, `13-cryostat`, `14-subsea` and `15-pv` — with one
change: no node may carry `at`. Five `claude-opus-5` sessions, one after
another, in a room built by `tools/clean_room.py` from `9d507d3`, each
committing its own folder. `RERUN.md`'s run-4 section wrote the outcomes down
before the room was built. This file grades the run against them, in order,
and then lists what was found.

The library under test is `2ec1962`, the commit that made `at` optional.
Every defect below marked *fixed* was fixed after the run, in the commit that
carries this file, and each has a guard in
`tests/test_clean_room.py::TestRunFour` or `tests/test_solve.py`.

## The pre-registered outcomes

### 1. The solver claim holds

11, 12, 13 and 14 are chains, and each reached exit 0 with no errors and no
warnings with no node carrying `at`. Their final files hold no `at` on any
node, no `via`, and no `at` on a branch or a source. Three of the four were
clean on the first draft; 13 took two rounds (below). The solver placed
five, four, five and five nodes, and all four agents said the ordering was
the one they would have chosen. Three said the spacing was not — the
furnace's brick run is widest because three series boxes sit in it, the
cryostat's leads run is widest because a label was turned, the bottle's
vapour-chamber run is wider than its spreading run because its label is
longer — and all three read horizontal distance as resistance. The solver
spaces by label width, which is not a quantity, and nothing says so.

### 2. The routing claim holds

On the four solved diagrams, no round reported `wire-through-wall`,
`symbols-overlap`, `nodes-too-close` or `symbol-off-its-run`. 13's one
finding was `label-adrift`. 15's probes reported walls and overlaps, on a
diagram every node of which the agent had placed by hand, which the claim
excludes.

### 3. The refusal claim fails, on the library's own words

15 is a star and was refused naming `cell`, as predicted. What the refusal
said to do was wrong. It said "give node 'cell' `at` yourself, and `via` on
the branches that leave it sideways". The agent gave `cell` `at` and got the
same message back, byte for byte; added `via` to both sideways branches and
got it a third time; then established by probe that one unplaced node
anywhere sends the whole file to the chain test. The agent's final file has
`at` on every node, which is what works, and the claim said one.

The remedy was written by the author of the solver before checking that it
applied — the class of defect run 2 found in the checker's `via` remedies,
now in the solver's own refusal, and pre-registered as if it were true. The
command line then wrapped the refusal in "This is a bug in thermodraw; the
diagram was accepted and then could not be drawn", because the crash net
under `main` caught a `DiagramError` it was never meant for. 13 met the
same pair on a probe — merging its two 300 K walls makes a loop, and the
loop refusal named a node whose `at` changes nothing — and called it "the
most confusing sentence I met all session".

**Fixed.** Both refusals say "give every node `at` yourself"; the test
applies that and draws. The command line prints a `DiagramError` from the
pipeline as a refusal and exits 2, and the word "bug" is reserved for an
exception that is one. The schema's "the two mix" sentence now says the
mixing is within a chain and a non-chain is refused whole. Placing part of a
non-chain is the general placer, which is still what is left to build.

### 4. The rounds claim fails, on two briefs

| brief | run 3 | run 4 |
|---|---|---|
| 11 (06) | 2 | 1 |
| 12 (07) | 3 | 1 |
| 13 (08) | 1 | 2 |
| 14 (09) | 1 | 1 |
| 15 (10) | 1 | 4, after three refusals |

13's extra round was the solver's: it turned the shield's `radin` source to
arrive from above and its outbound `flow` to leave below, and the shield's
label had a lead above it and a lead below it. The remedy named `angle` and
the agent's `angle: 45` cleared it in one round. The solver already turned a
node's label to 45 when it put a source above a node with a capacitance
below; a solver-placed source below is the same crowding, and the rule now
covers any solver-placed wire below (*fixed*). 15's four drawable rounds were
one clean draft, one deliberate change — the sun moved overhead, which "is
the one arrow on this page whose direction has a physical referent" — and a
`label-adrift` whose first remedy, "move it along its branch with `at`",
names an axis and no direction; the agent went the wrong way and the push
grew from 112 to 132. Its second remedy cleared it. That remedy defect is
recorded and not fixed: the checker does not know which way is better, and
saying so would be a guess wearing an instruction.

### 5. The two fields hold

13's final file has `"wall": "up"` on the mount and
`"T": {"unit": "K", "scale": "absolute"}`. The brief named neither. The
agent found `scale` on the first read and wrote it; it found `wall` in the
schema's own prose about a mount a cold mass hangs from, and added it after
the diagram was clean, "so the hatching at least faces the right way even
though the node does not sit in the right place" — the mount is on the
line to the right of the winding, because a chain has no *above*.

### 6. The physics claim holds

11, 12, 13 and 15 are silent under `--physics` with no `physics-not-checked`
note: every free node was checked and balanced on the briefs' numbers,
which none of the agents adjusted. 14 reports one note — three of four free
nodes unchecked, because the junction between the vapour chamber and the
oil gap has no quoted temperature — and no balance finding. 12's agent makes
the sharp observation that silence covers what the check can see: its flux
and its conducted power differ by sixty per square metre, the flux sits on a
`fixed` node that is not asked, and no note says anything went unexamined.

### 7. The run is clean

Five commits, one per folder, in sequence. No transcript shows a removed
file being read; 13 listed the tree with `find` on its first command and
opened nothing under `src/`. The room built and verified itself.

## What was found

### Defects in the library, all fixed

- **The `wire-through-wall` remedy named the side the branch came through.**
  On 15's probe, a branch arriving from below at a wall that faced down was
  told `wall: "down"`. `_away_from` measured the offending run's far end
  from the hatching's own box centre; the run that crosses a wall is the
  short one between the box and the node, and from the box centre its far
  end is the node. Measured from the node, the answer is `up`, and applying
  it clears the wall finding and the overlap with it.
- **`symbols-overlap` against a wall named `at`.** The two are not on one
  run, so the remedy fell through to "move one of them with `at`". A
  hatching turns; the remedy names `wall` first.
- **The refusal's remedy and the "bug" wrapper**, above.
- **`describe` cut a long ref.** `branch 1 flange->vchead` printed as
  `vchea`, in the column whose job is to be the name a finding uses. Padded,
  never cut.
- **A ground row said `a270`.** Two agents set `wall: "up"` and turned 270
  back into "up" by hand to confirm it took. The row says `faces up`.
- **A node with no temperature looked like every other node.** 14's
  junction, the one about to blind `--physics` on three of four nodes, read
  `free at (790, 150) solved`. It reads `no T` now, and `describe --json`
  carries `temperature: false`.
- **`rail.y` was required and undocumented.** 11: "the one absolute
  coordinate a solver-placed file still has to invent", and nothing said
  whether it was required or what it should be. It is optional and goes 222
  below the lowest node, which is the hero's 372 on a line at 150.

### Defects in `docs/schema.md`, all fixed

Four agents quoted the same pair of sentences: a source without `at` is
placed "about 40 units from the node" in one section and "half a run out"
in another, and the file put it 110 out. Both now say 110, half the
narrowest run, and the default `angle` of 0 is stated. The bold parallel-pair
rule — `via` first, then `side` — contradicted the Coordinates section for a
solved file and is scoped to a file whose nodes the author places. `rail` is
said not to be a neighbour for the physics skip. `mixed`'s `sub` was
documented as naming the mechanism, on the one kind that exists to say the
mechanism is not broken out; it names the part. `cond`, `conv`, `rad` and
`contact` had no sentence each; they do.

### What the format cannot state

The deferred four recurred, as the protocol says they would: a stream with
an inlet and an outlet (11's glycol loop dumps into a reservoir that is
really the inlet), relating two elements (13's MLI radiation arrives from
off-page when its source is drawn 300 units away; 12's flux lands on the
gas rather than on the refractory face), a result or a provisional number
(12 and 15 both left off a rate they had derived rather than state it as
given), and a diagram-wide qualifier (12's "per square metre of wall" and
14's "1800 m" have nowhere drawn to go). Newly named:

- **An area basis** (12). Without one, `q″` and `q` on one page cannot be
  compared and `--physics` skips every node a flux touches.
- **A boundary that is one thing drawn twice** (13). The vessel and the
  mount are the same room; a chain cannot join a node to two others, so the
  drawing states two boundaries. This is the solver's limit meeting the
  format's, and the agent ranked it first.
- **Physical arrangement as distinct from page layout** (14, 15). The
  bottle is vertical and the drawing is a strip; the module is tilted and
  the agent encoded sky-versus-roof as a direction on the page, "a private
  code". `at` and `via` are ink.
- **An effective temperature marked as one** (15). A sky at 10 °C draws as
  a reservoir a thermometer could be put in.
- **A `phase` node's budget** (13), already a recorded limit, now with its
  cost: 0.25 W arrives at the bath and nothing on the page or in
  `--physics` says where it goes.
- **`--physics` does not solve an unknown junction** (14). One linear
  equation, all its terms stated, and three nodes go unchecked. Recorded as
  a limit, not a defect: the check reads stated values by decision.
- **Spacing by label width reads as resistance** (12, 13, 14). Not a gap in
  the format; a consequence of the solver a reader will meet.
- Smaller: multiplicity across a run of the ladder (11), a rail visibly
  tied to its reference (11), a per-group override on condensing (15),
  the work a PV module exports (15), a fold or an aspect ratio for a long
  chain (13, 14).

### Coverage

Seventeen of the eighteen symbols were drawn, checked against the five
files after the run. `break` as a node kind was not — for the fourth run
running, and in the brief written to force it. 13's agent drew the mount as
a `fixed` node with `wall: "up"` and the strut as a `break` branch, as run
3's did, and did not mention the node kind in its findings. Run 3's
explanation was that the arrangement could not be verified without
rendering; `describe` reports the wall now and the agent used it. The
remaining explanation is the schema's: the node kind is one sentence in the
Nodes section, and a mount that is a boundary reads as `fixed` first.

## What to do about it

Everything marked fixed is fixed in this commit. What is left is design:
the general placer, which would let 13 draw one room and 15 keep its `at`
off; an area basis; a way to mark a temperature or a rate as derived;
`describe` saying which way heat runs on each branch, which 13 asked for
and which needs nothing the tool does not already hold; and either a
worked example for `break` as a node kind or a decision that a `fixed` node
with a `break` branch is what that symbol is for.
