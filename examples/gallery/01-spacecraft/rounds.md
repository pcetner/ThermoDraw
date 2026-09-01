# Rounds

Iteration log for `satellite.json`. One section per `check` run, written as it
happened.

## Round 1 — first draft

Layout: single main line at y=150, heat left to right
(TWTA 200 -> panel 560 -> radiator 920 -> deep space 1240), MLI routed over the
top at y=20, panel capacitance dropping to a rail at y=430, four sources placed
by `angle` alone with no `at`.

```
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 3 warnings, 0 notes
warning: [label-adrift] node 'panel': its label was pushed 52 past its own clearance to get around source 1 -> panel and now sits nearer that than the thing it names  -> move source 1 -> panel further from its node with `at`, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
warning: [label-adrift] source 2 -> panel: its label was pushed 112 past its own clearance to get around branch 0 twta->panel and now sits nearer that than the thing it names  -> move branch 0 twta->panel along its branch with `at`, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
warning: [label-in-a-corridor] branch 1 panel->rad: its label sits inside a loop of the network, 21 from the opposite path and 33 tall, so it reads as belonging to either  -> set `side` to send it outside the loop
EXIT=1
```

13 labels placed is the expected count (4 nodes + 5 branches + 4 sources), so
nothing was dropped.

Remedies to apply literally in round 2 — in each case the **first** option the
finding names:

1. `label-adrift` on node `panel` -> "move source 1 -> panel further from its
   node with `at`". Source 1 is the Earth IR `radin`. Give it an explicit `at`
   further out along its own 45 deg line: `[430, 20]`.
2. `label-adrift` on source 2 (survival heater) -> "move branch 0 twta->panel
   along its branch with `at`". Give branch 0 `"at": [320, 150]`, shifting the
   contact box left from its default midpoint of 380.
3. `label-in-a-corridor` on branch 1 (heat pipes) -> "set `side` to send it
   outside the loop". The loop is panel -> radiator -> space -> MLI -> panel and
   the MLI runs above, so outside is below: `"side": "down"`.

## Round 2 — applied the three round-1 remedies literally

Changes: `"at": [430, 20]` on the Earth IR source, `"at": [320, 150]` on the
contact branch, `"side": "down"` on the heat-pipe branch.

```
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 2 warnings, 0 notes
warning: [label-adrift] node 'panel': its label was pushed 36 past its own clearance to get around the wire of source 1 -> panel and now sits nearer that than the thing it names  -> move a `via` waypoint on source 1 -> panel so it does not run past this label, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
warning: [label-adrift] source 2 -> panel: its label was pushed 32 past its own clearance to get around the wire of branch 0 twta->panel and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 twta->panel so it does not run past this label, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
EXIT=1
```

Did each remedy clear its finding?

- **`label-in-a-corridor` on the heat pipes: YES.** `"side": "down"` cleared it
  outright and nothing new appeared in its place.
- **`label-adrift` on node `panel`: NO, but it helped.** Moving the source out
  with `at` cut the push from 52 to 36. The finding then changed its own advice:
  the blocker is no longer the source *symbol* but the source's *lead wire*, and
  the lead wire converges on the node no matter how far out the symbol goes, so
  this remedy cannot ever finish the job. Pushing the symbol further away only
  makes the lead longer.
- **`label-adrift` on source 2 (heater): NO, but it helped.** Push fell from 112
  to 32, and again the blocker changed from the contact *symbol* to the contact
  *wire*, which cannot be moved by `at` because `at` slides the box along a wire
  that stays where it is.

Both surviving findings now name a remedy I cannot apply as written — see
round 3.

## Round 3 — testing the named remedy literally: `via` on a source

The round-2 remedy for node `panel` is:

> move a `via` waypoint on source 1 -> panel so it does not run past this label

Applied literally, on a copy, adding `"via": [[560, 20]]` to source 1:

```
error: .../sat_via.json: source 1: unknown field 'via'. Expected: angle, at, from, kind, label, side, sub, to, value
EXIT=2
```

**The remedy names a field that does not exist.** `via` is a branch field; the
Sources table in `docs/schema.md` does not list it and the validator rejects it.
The finding for source 2 has the same shape of problem for a different reason:
it says "move a `via` waypoint on branch 0", and branch 0 is a straight two-node
run with no `via` at all — there is no waypoint to move, and inventing a detour
in a straight conduction path to unstick a label is not a fix a reader would
thank you for.

So for both, fall through to the remaining named options: `side` "to one of the
two the solver does not try", and `angle` "for a direction between those four".

## Round 4 — the remaining named options, tried one at a time

`side` "to one of the two the solver does not try" on node `panel` means left or
right, because the imaginary branch through it is horizontal. Both were tried on
copies, together with `"side": "down"` on the heater.

`"side": "right"` on `panel`, `"side": "down"` on the heater:

```
13 labels placed, 2 errors, 2 warnings, 0 notes
error: [label-collision] node 'panel': its label is printed over branch 1 panel->rad
error: [label-collision] source 2 -> panel: its label is printed over the wire of branch 4 panel->rail
warning: [label-adrift] node 'panel': ... pushed 160 ... to get around branch 1 panel->rad
warning: [label-adrift] source 2 -> panel: ... pushed 160 ... to get around the wire of branch 4 panel->rail
EXIT=1
```

`"side": "left"` on `panel`, `"side": "down"` on the heater:

```
13 labels placed, 2 errors, 2 warnings, 0 notes
error: [label-collision] node 'panel': its label is printed over branch 0 twta->panel
error: [label-collision] source 2 -> panel: its label is printed over the wire of branch 4 panel->rail
warning: [label-adrift] node 'panel': ... pushed 160 ... to get around branch 0 twta->panel
warning: [label-adrift] source 2 -> panel: ... pushed 160 ... to get around the wire of branch 4 panel->rail
EXIT=1
```

Then `angle` "for a direction between those four" on `panel`, alone:

```
angle 45:  13 labels placed, 0 errors, 2 warnings, 0 notes
warning: [label-adrift] node 'panel': ... pushed 120 ... around the wire of branch 3 panel->space
warning: [label-adrift] source 2 -> panel: ... pushed 32 ... around the wire of branch 0 twta->panel
EXIT=1

angle 135: 13 labels placed, 1 error, 2 warnings, 0 notes
error: [label-collision] node 'panel': its label is printed over source 1 -> panel
warning: [label-adrift] node 'panel': ... pushed 160 ... around source 1 -> panel
warning: [label-adrift] source 2 -> panel: ... pushed 32 ... around the wire of branch 0 twta->panel
EXIT=1
```

**Every one of the four named remedies for `label-adrift` on node `panel` fails,
and three of the four make the diagram strictly worse** (an error where there
was a warning). The `side` suggestions are the worst advice: left and right are
exactly where the two branches leave the node, so the finding is recommending
the only two directions that are guaranteed to print the label on a wire. The
checker knows what is at left and right — it is holding the occupancy list it
used to detect the collision — and it recommends them anyway.

`"side": "down"` on the heater also fails, for the same reason: down is where
the capacitance drops.

Note also that "or `angle` for a direction between those four" is meaningless on
a **source**. On a source, `angle` is documented as "the direction the arrow
points" — changing it moves the whole arrow and its lead, not the label. The
same remedy string is being printed for nodes, branches and sources, and it is
only true for nodes.

`describe` was the thing that actually explained the problem:

```
source 2 -> panel  symbol/diss  (533, 177) a315  above left  106x33  pushed 32
```

The heater, given no `at`, was auto-placed **34 units** from its own node — its
106-wide label had nowhere to go but across the contact branch's wire. The
schema says "Leave `at` out and the source is placed along its own `angle` with
room for its label ... That is usually what you want", and here it is not: the
automatic distance leaves room for the label only if nothing else is nearby.

### The real diagnosis

`panel` has six attachments — contact left, heat pipes right, MLI leaving
up-right, capacitance down, and two sources — plus its own label, for eight
directions. Node labels are further restricted: `angle` is documented as
symmetric about 180 deg, so `angle` alone can only ever put a node label in the
**upper** half. And any source arriving diagonally from above cuts through the
cone directly above the node, so an "up" label is unreachable while a diagonal
source exists.

So round 5 rearranges rather than nudging: free the space directly **below**
the panel and put the label there with `side`, which is the one control that
reaches down.

## Round 5 — rearranged, clean

Changes from round 4:

- `"side": "down"` on node `panel`, the one control that reaches below the line.
- Capacitance rerouted off the space under the panel with
  `"via": [[460, 150], [460, 430]]`, so it now leaves the node sideways and
  drops at x=460. This is what freed the "down" slot.
- Survival heater moved from a down-left diagonal to directly above the node,
  `"angle": 90, "at": [560, 30]`, so its lead is vertical and clears the
  contact branch entirely.
- Earth IR moved further out and up, `"at": [360, 10]`, so its lead crosses
  nothing.

```
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

`describe` confirms all 13 labels, the four nodes at the intended coordinates,
five branches with the intended kinds, four sources with the intended arrow
directions, and no `pushed N` anywhere.

## Round 6 — units probe, still clean

Three probes on copies, to find out how much of the schema is actually checked:

| probe | result |
|---|---|
| `units.C` set to `"kJ/K"`, capacitance value `"18"` | **accepted**, 0 findings |
| survival heater with `value` removed entirely | **accepted**, 0 findings |
| branch `"kind": "heatpipe"` | rejected: `unknown kind 'heatpipe'; expected one of break, cap, cond, contact, conv, rad` |

`kJ/K` being accepted is the useful one: the brief says 18 kJ/K and I had been
writing 18000 J/K, so the diagram now says what the brief says. Nothing
validates the unit string, though — `"18"` with `"J/K"` would have been accepted
just as happily and would have been wrong by a factor of 1000.

Final:

```
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Rendered to `satellite.svg`, 18,111 bytes. Six rounds; no notes left standing.
