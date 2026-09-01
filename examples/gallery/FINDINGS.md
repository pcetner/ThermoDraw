# What five agents found

Five thermal networks, five domains, five agents that had never seen the
library, each working from `docs/schema.md` and a plain-English brief. All five
diagrams check clean. Getting them there cost 22 rounds between them, and
**6 of the 18 remedies the checker offered actually worked**.

| | domain | rounds | remedies that worked |
|---|---|---|---|
| 01 | GEO satellite payload panel | 6 | 1 of 9 — three made it strictly worse |
| 02 | Two-zone house, ground-coupled | 8 | 1 of 4 |
| 03 | LHe dewar, two-stage cryocooler | 4 | 1 of 2 — one has no fixed point |
| 04 | Two-phase immersion rack | 1 | none offered |
| 05 | Laser diode on a microchannel cooler | 3 | 3 of 3, first try |

The spread between 01/02 and 05 is the shape of the result. The remedies hold
up on a linear stack and fall apart at a node where several branches meet,
which is where an author actually needs them.

Every claim below was reproduced against the library before being written down.

> **Since this was written, §1 to §5 have been fixed.** Each section below is
> left as the agents found it, because the record of what went wrong is worth
> more than a tidy list of what is now right. Where a fix landed it is marked
> **[fixed]**, and the last section says what changed.
>
> Two consequences worth knowing before you read on. `04-immersion` and
> `05-laser-diode` **now report a warning** where they used to be clean: the
> new connectivity check finds exactly the severed network their agents had to
> describe in prose. That is the check working, not a regression. And the
> remedy strings quoted below no longer exist in that form.

---

## 1. The remedies are wrong more often than they are right — [fixed]

All four of these were introduced in the same change that claimed each finding
"names the schema field that fixes it". Three agents hit them independently.

**`angle` is offered for every element, and means three different things.**
The schema's own tables say so: on a node it "moves the label and nothing
else"; on a branch it "overrides the direction taken from the wire"; on a
source it aims the arrow. Only the node case is label advice. Following it on
a branch lays the conduction box diagonally across a vertical wire — and
`check` then reports the diagram clean:

```
angle=None  symbol drawn at 90.0 deg   check: clean
angle=45    symbol drawn at 45.0 deg   check: clean
```

This is the most dangerous of the four, precisely because it is the one that
appears to work.

**`via` is offered on sources, which have no such field.** A source's lead is a
wire carrying the source's ref, so a source lead as culprit produces *"move a
`via` waypoint on source 1 -> panel"*. The validator rejects it outright:
`source 0: unknown field 'via'`.

**`side` is offered without consulting the occupancy that produced the
finding.** Telling a node to try left or right, when those are the two
directions its branches leave in, is advice guaranteed to print the label on a
wire — and the checker held the `Occupancy` when it said so. On a vertical
branch the two untried sides lie *along* the wire, so following it turned a
warning into an error.

**`parallel-pair-same-side` has no fixed point with three parallel paths.**
Two sides, three branches: the remedy cannot be satisfied. It should say so.

## 2. Two false cleans — [fixed]

**Setting `side` silences `parallel-pair-same-side` whether or not it helped.**
The check skips any pair where neither label is `auto`, so following its own
remedy removes the pair from consideration:

```
both auto          -> ['label-in-a-corridor', 'parallel-pair-same-side']
both set to "down" -> ['label-in-a-corridor']          <-- same side, silent
set to up / down   -> []
```

The author does the documented thing and is rewarded with a clean report
either way. Found by 03.

**A node with no temperature prints a bare italic `T`,** and `check` says
nothing. Interior junctions between series layers — four of them in 02, one in
05 — have no temperature to state. Both agents were forced to `corner`, which
draws nothing and loses the name. Found independently by 02 and 05.

## 3. Nothing checks that the network is connected — [fixed]

04 drew a two-phase loop whose two halves are joined only by two `flow`
annotations pointing at each other. The result is a thermal network **severed
into two components**, and neither instrument noticed. 02 left its roof wired
to nothing indoors, likewise unremarked.

The obvious fix is barred: the hero's own *wire* graph has two components
(sizes 3 and 24), so a check on wire connectivity would condemn the flagship.
The right formulation is a graph over **nodes joined by branches**.

A `break` branch counts, though it carries no heat. Excluding it was tempting
— the two sides of a standoff really are thermally apart — and wrong: this
finding is for a path the author *meant* to draw and did not, and a break is
the opposite, an explicit statement that nothing flows. Excluding it warns
about every standoff ever drawn.

Nothing checks energy balance either. 01's heat pipe is drawn with a
resistance that contradicts the temperatures printed either side of it by a
factor of 50, and the report is clean.

## 4. `describe` reports everything except the network

Three of five named this as its single largest omission, and two called it the
most valuable tool they had. It caught what `check` passed: a rotated symbol,
a bare `T`, a source auto-placed 34 units from its node, a capacitance sitting
at `a101.768` instead of vertical.

But it prints `wire x19` and not one coordinate, and it never states what is
connected to what. 02 put it best: *the one question `describe` exists to
answer is the one it doesn't.*

## 5. The documentation — [fixed]

- **`size` is never defined.** It appears in `docs/schema.md` only inside the
  check-codes table, as a field two findings tell you to adjust, in a page
  whose opening line calls itself "the whole format".
- **The `via` sentence is wrong.** *"waypoints work on a capacitance exactly as
  they do on any other branch, which is how you free up the space directly
  under a node that already has too much attached to it."* A rail branch's
  endpoint is always directly below its node, so a waypoint buys a detour that
  comes back to the same place. Cost 03 a full re-layout.
- **Whether `value` is optional on a branch is not stated.** Both 03 and 04
  needed a path the brief gives no number for.
- **`angle`'s three meanings are never set beside each other**, and the
  consequence that a node label cannot be sent *below* the line by `angle`
  alone is never stated. Four of 01's six rounds were about that one fact.

---

## What was fixed

- **`angle` is offered only for a node's label**, the one element where it
  means what the remedy said. `via` is never offered on a source, which has no
  such field. `side` is offered only for directions `core.free_sides` says are
  actually free — the checker now asks the occupancy it is holding.
- **`parallel-pair-same-side` no longer skips a pair whose sides were set
  explicitly**, so its own remedy can no longer buy a clean report by silencing
  it.
- **A node with no value and no sub draws no `T`.** Interior junctions stop
  needing to be `corner`s.
- **`network-in-pieces`** is new: a graph over nodes joined by branches, so the
  hero's two-piece wire graph is not condemned. Its remedy names why a source
  cannot join two nodes.
- **A waypoint on a rail branch now frees the space it promised.** The rail end
  drops from the last waypoint rather than from the node, which makes the
  sentence in §5 true rather than merely corrected.
- **`size` is defined**, branch `value` is documented as optional, and the
  Angles section now says outright that no `angle` sends a node's label below
  the line.

§6 is untouched. Nothing there was fixed, and nothing there is cheap.

---

## 6. What the vocabulary cannot say

This is what the exercise was for. Ranked by how many domains needed it and
how badly the drawing lies without it.

**Two-ended advective transport — heat carried by a moving fluid.** Needed by
three of the five, and the only gap that makes a drawing state something
false. Infiltration, an open stairwell between zones, a pumped water loop: in
each case heat leaves one node and arrives at another because mass moves. A
`flow` source is the right *quantity* with the wrong *arity* — it has one end.
02 drew the stairwell with one end missing, so 240 W appears at the upper zone
from nowhere and never leaves the lower one. 04's loop severed its own network
in half. Both refused to fake it as an `R_conv`, which would have named physics
that is not happening.

**A branch cannot carry a heat rate.** Five of 03's numbers are heat loads in
watts on paths — the actual subject of a cryostat budget — and there is
nowhere to put them. They ended up inside the free-text `label`, reading as
part of the path's name, bypassing the `units` block entirely.

**Spreading resistance.** 05's largest resistance. Drawn as `cond`, whose
library-set subscript the schema says "names the physics", so the diagram
positively asserts one-dimensional conduction for the one path that is not.

**Active, pumped heat.** A Peltier stage and a cryocooler both move heat
against a gradient. 05 drew its TEC as two `flow` annotations plus a `diss`,
with nothing stating they are one device.

**Latent heat at constant temperature.** 04's condensation is 3.2 kW with no
temperature drop — the whole reason a two-phase system exists. Representable
only by collapsing both surfaces onto one node: correct by erasure.

**An isothermal link.** A heat pipe drops 0.4 K at load. 01 divided by the
load to get `0.0018 K/W`, a number that encodes one operating point and wears
solid-conduction hatching on a two-phase device.

**Multiplicity.** 04's eight processors. There is no `x8`, so a reader
multiplying the drawn source by the drawn resistance gets 88 K and expects a
137 °C junction against the 72 °C stated.

**A combined-mechanism resistance.** 02's window is "conduction and convection
at 0.31 K/W" as one number. Flattened to `cond`, section hatching and all.

**An interior node with no temperature.** See §2.

---

## A note on method

The harness auto-injected the project `CLAUDE.md` into every agent's context
before it received its brief. All five disclosed this. None read `src/`,
`tests/`, the README, or an existing diagram, and none reported it changing a
layout decision — but the reading restriction was not intact, so the
*documentation-quality* half of this result is softer than it looks. The
vocabulary findings are unaffected: knowing the design rationale does not hand
anyone a spreading-resistance symbol.

Suppress that injection before re-running.
