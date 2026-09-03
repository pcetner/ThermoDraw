# What five agents found, in a clean room, with numbers that close

The third run of the gallery, and the first in which any pre-registered claim
held. Five new domains, five agents, `docs/schema.md` and nothing else — and
this time the briefs' numbers were solved as networks before they were written
as prose, so a `--physics` finding could only be the agent's arithmetic or the
library's. `RERUN.md` is the protocol and wrote the outcomes down first; this
is what the run produced, graded against them.

| | run on | model | harness | from |
|---|---|---|---|---|
| all five | 2026-09-02 | `claude-opus-5` | Claude Code, five sessions in parallel | clean room `db5dede`, built by `tools/clean_room.py` from `56f8e0a` |

The room was a sibling of this checkout, built and verified by script. Every
transcript records its working directory as `GitHub\ThermoDraw-cleanroom-run3`
and none records a path inside the checkout. All five SVGs are byte-identical
to fresh renders of their committed JSON.

| | diagram | rounds to exit 0 | standing findings | `check --physics` |
|---|---|---|---|---|
| 06 | `pack.json` | 2 | — | silent |
| 07 | `wall.json` | 3 | — | silent |
| 08 | `magnet.json` | 1 | — | silent |
| 09 | `bottle.json` | 1 | — | one note, 3 of 4 nodes unchecked |
| 10 | `array.json` | 1 | — | silent |

Run 2's counts were 9, 4, 3, 5, 2, and all five of its diagrams warned under
`--physics`.

## The pre-registered outcomes

### The physics claim holds

This is the first claim in three runs to survive its own test. No diagram
reports `node-does-not-balance`. No diagram reports `rate-does-not-match`.
Five agents, working from prose, reproduced networks whose stated numbers
agree with each other — which is what the claim asserted and what run 2 could
not distinguish from a brief that never closed.

The one qualification is 09, and it is worth more than the pass. `bottle.json`
is silent on the balance and carries this instead:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange,
bore (neighbour 'vct' has no temperature); vct (it has no temperature)
```

The agent needed a node the brief did not name — the top of the vapour
chamber — and gave it no temperature, which is the idiom the schema
recommends for an interior junction. Three of its four free nodes were
therefore never examined. Under run 2's library that would have been silent,
and the diagram would have read as fully checked. The note that says otherwise
is run 2's most actionable finding, shipped, earning its place on the first
diagram that could have hidden behind it.

### The vocabulary claim fails, and the four known gaps are not why

All four deferred gaps recurred, as the protocol said they would and as does
not count: 08 could not join the MLI radiation to the vessel it comes from
("the worst thing here"), 10 could not say that 25 W is the answer rather
than an input, 08 could not say its temperatures are absolute rather than a
rise, and 07 could not mark a number provisional.

Four gaps outside that list are new.

**A boundary cannot sit above the thing it holds — 08.** The magnet *hangs
from* its mount. The agent built the honest arrangement, mount above and the
break branch running down, and `check` passed it with nothing to say. It
shipped the other one anyway, because a boundary node's wall is always drawn
flat below the node, so a mount above the magnet puts that wall between the
mount and the strut and the strut leaves through its own boundary's hatching.
`check` does not police that. `describe` counts grounds on the `placements:`
line and gives them no row in `elements:`, so it cannot say where a wall is
either. The only way to settle it was to render and look, which the brief
forbids. The finished drawing therefore puts a 300 K node immediately right of
a 4.5 K one, against the schema's own left-to-right habit, and "hangs from"
survives only in the words. This is one design limit and two tool gaps, and
the two tool gaps are the reason the design limit could not be worked around.

**A bend cannot be a property of the hardware — 09.** The vapour chamber
turns a corner. `via` draws the bend and says nothing: delete it, move the
node, and the file asserts exactly the same physics while drawing a straight
line. `corner` is no better, being defined as routing too. Nothing false is
drawn; the fact simply cannot be recovered from the file.

**A group's effective value is never printed — 10.** The clip group renders
as `Mounting clips | R_cond = 1.6 K/W | 4 in parallel`. The effective 0.4 K/W
appears nowhere, so a reader checking the arithmetic on the page gets 6.25 W
where the answer is 25 W. `--physics` folds the count correctly, so the
library computes the number internally and declines to show it. The schema
defends per-item *storage* well; that defence says nothing about the rendered
label.

**A qualifier governing every number has nowhere to go — 07.** "Per square
metre of wall" conditions the whole diagram and can only be put in a title
that is not drawn.

### The documentation claim fails on one sentence, and passes on rounds

No agent needed more than three rounds, against a limit of six and run 2's
nine. None of the six documentation defects fixed after run 2 recurred. That
part of the claim is comfortably met.

It fails on a sentence that was not wrong before, because nothing had tested
it. Under "Two more details are worth copying rather than rediscovering":

> **A parallel pair needs `side`.** Both branches are horizontal, so both
> labels choose "up" and the lower one lands inside the loop. Set
> `"side": "up"` on the upper branch and `"side": "down"` on the lower one.

07 did exactly this and round 1 was a `symbols-overlap` **error**. The advice
presupposes a loop — two wires with space between them. There is none. Two
branches between one pair of nodes share one straight wire and their boxes
land on the same point; "the upper branch" does not exist until one of them is
routed away with `via`, which the paragraph never mentions. As written it is a
recipe for the error it exists to prevent, and it sits in the passage that
tells the reader to copy it rather than work it out.

Two smaller ones. `describe` is documented as reporting "which way it is
turned", and the angle marker is deliberately suppressed when the angle is
zero (`_describe.py:114`), so a reader cannot tell "not turned" from "not
reported" — 07 wanted exactly this confirmed for a `flux` source and could
not get it. And `flux` with `to:` has no worked example, only a `from:` one,
so whether the hatched face belongs to the source or to the node is a guess.

### The remedy claim fails, on one remedy

`symbols-overlap`'s remedy is a fixed string, `_check.py:765`:

```python
remedy="move one of them with `at`"
```

07 applied it literally, as the brief requires. The overlap fell from 32 to 4
and the error stood — it could not have cleared, because both symbols are on
the same wire and sliding one along it only trades overlap for near-overlap.
Round 2 was strictly worse than round 1: the same error, plus a
`wire-through-symbol` warning. The remedy that works appears only in that
*other* finding, which names `via` and says "which clears both", and did.

This is the same class as run 2's defect 2 — a fixed remedy string naming a
field that cannot fix the case in front of it — in a rule that was not part of
that fix. `symbols-overlap` between two branches on a shared run should name
`via`.

### The run is clean, with one deviation in the recording

No transcript shows a file the room removed, and none refers to a rationale
its brief does not contain. The deviation is procedural: the five agents ran
in parallel in one working tree sharing one git index, so two commits swept up
another agent's files — 09's commit carries 06's work, 07's carries 10's — and
06 and 10 have no commit of their own. `RERUN.md` asks for one commit per
agent because that is what makes the run auditable; the transcripts still are,
but the commit boundary is not. Run them sequentially, or give each agent its
own clone.

## The coverage claim, checked afterwards

The five briefs were written so that between them they would force every
symbol in the library. Sixteen of eighteen were drawn. Two were not, and they
are precisely the two that no previous diagram had ever used:

- **`break` as a node kind.** Brief 08 asks for a mount that is thermally
  broken and says both it and the strut must appear. The agent used a `fixed`
  node and a `break` **branch** — a defensible reading, and the wall-below
  problem above is why the alternative looked unverifiable.
- **`corner`.** Brief 09 says the vapour chamber turns a corner. The agent
  used `via` waypoints and never mentions `corner` in its findings.

`angle` on a branch also went undrawn. So a brief written specifically to
force a symbol does not force it: the two symbols with no prior use in any
diagram still have none, and in both cases the agent reached for something
else without recording that it had considered them. That is a finding about
how discoverable those two are from the schema, and it is the reason to keep
the coverage table rather than assume the vocabulary is exercised.

## What to do about it

In the order the evidence supports.

1. `symbols-overlap` should name `via` when the two symbols share a run. It is
   the one remedy in this run that could not work, and the fix is the one that
   was already applied to the wire findings after run 2.
2. Rewrite the parallel-pair paragraph: route one branch with `via` first,
   *then* set `side`. It is the first thing a first draft hits.
3. Give `describe` a row for each ground, with its coordinates. Without it,
   nothing but a rendered picture can say where a boundary wall sits — and the
   brief that most needed to know was told not to look.
4. Decide whether a repeated group should print its effective value beside the
   per-item one. The library already computes it for `--physics`.
5. Say in the schema that `describe` prints no angle marker at zero.

Four of the five are the same shape as run 2's list: the tools describe the
drawing accurately and stop just short of the one thing the reader needed.

## What happened when they were fixed

All five are done, and two of them changed what the rest of the repository
says about itself.

**`wire-through-wall` found three real defects nobody had seen.** Two are in
run 2's `house.json` — `branch 6 gf->out` and `branch 12 roof->sky` both
arrive at a boundary node from below and pass through its hatching — and the
third is in this run's own `07-furnace` reference solution, a diagram written
during preparation, checked clean at the time, and used to prove the brief was
satisfiable. All three have the same cause, and it is the idiom the schema
recommends: route a parallel pair clear with `via`, then bring it back to the
node. Brought back *at the node* rather than before it, the branch arrives
vertically from underneath and crosses the wall that is always drawn there.

None of the three is retouched. `house.json` and the reference are evidence,
and the expectation is recorded in `tests/test_clean_room.py` instead. The
remedy for `symbols-overlap` now names the arrival as well as the routing,
because the short version of the advice is what produced all three.

**A counted source's total had to be trimmed to fit.** The first version wrote
`each of 8 = 3200 W total` and pushed the immersion rack's junction label 96
past its clearance, turning a clean diagram into a `label-adrift` warning. The
word "total" says nothing the `=` has not; without it every counted diagram
stays as clean as it was. Worth recording because it is the general shape of
the risk: adding a true statement to a label is not free, and the diagrams
that would pay for it are the ones nobody may edit.
