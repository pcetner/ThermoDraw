# Rounds

Iteration log for `house.json`. One section per `check` run, written as it happened.

## Round 1 — first draft

Diagram written from `docs/schema.md` and the brief alone. 10 nodes, 13
branches, 4 sources, rail at y 1360.

```
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] branch 7 zg->grd: its label was pushed 20 past its own clearance to get around the wire of source 2 zg -> and now sits nearer that than the thing it names  -> move a `via` waypoint on source 2 zg -> so it does not run past this label, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
EXIT=1
```

27 labels placed = 10 nodes + 13 branches + 4 sources, so nothing was dropped.

Findings and what the remedy did — see below.

## Round 2 — remedy 1, literally

The finding's first remedy: "move a `via` waypoint on source 2 zg -> so it does
not run past this label". Source 2 has no `via` waypoints, so there is nothing
to move; the only literal reading is to add one. Added
`"via": [[860, 700], [700, 940]]` to source 2.

```
error: examples/gallery/02-building/house.json: source 2: unknown field 'via'. Expected: angle, at, from, kind, label, side, sub, to, value
EXIT=2
```

**Remedy 1 did not work, and cannot.** Sources have no `via` field. The
remedy text is written for branches and is emitted verbatim on a finding whose
blocker is a source. Reverted.

## Round 3 — remedy 2, literally

Second remedy: "set `side` to one of the two the solver does not try (it tries
only the sides of the branch)". Branch 7 (`zg->grd`) is vertical, so the solver
tried left and right; the two untried are `up` and `down`. Set `"side": "down"`.

```
examples/gallery/02-building/house.json: 27 labels placed, 1 error, 1 warning, 0 notes
error: [label-collision] branch 7 zg->grd: its label is printed over the wire of branch 7 zg->grd  -> move a `via` waypoint on branch 7 zg->grd so it does not run past this label, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
warning: [label-adrift] branch 7 zg->grd: its label was pushed 160 past its own clearance to get around node 'grd'  -> move node 'grd' with `at`, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
EXIT=1
```

**Remedy 2 made it strictly worse** — a warning became an error plus a warning.
On a vertical branch, `up` and `down` are the two sides that lie *along the
wire*, so the label lands on top of the branch's own wire. The remedy is
generic text that does not know the branch's orientation, and for a vertical
branch it is guaranteed to be wrong.

## Round 4 — remedy 3, literally

Third remedy: "`angle` for a direction between those four". Set
`"angle": 135` on branch 7.

```
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

**Remedy 3 cleared the finding — and silently broke the drawing.** On a *node*,
`angle` "turns the node's label frame... It moves the label and nothing else".
On a *branch*, the schema says `angle` "overrides the direction taken from the
wire" — it rotates the **symbol**. `describe` confirms it:

```
  branch 7 zg->grd       symbol/cond     (760, 880) a135   below right   107x33   flipped   Slab to deep ground | R_cond = 0.6 K/W
```

`a135` on a wire that runs straight down: the conduction box now sits at 45
degrees across a vertical wire. `check` reports the diagram clean. The third
remedy on a branch finding is the node remedy's wording, and taking it
literally trades a misplaced label for a symbol pointing the wrong way that
nothing checks. Not kept.

### What else `describe` turned up in round 4

Two defects that `check` passed clean:

1. `node 'w1' ... Gypsum-wool | T` — the four wall-layer interface nodes have
   a label but no `sub` and no `value`, because the brief gives no temperature
   for them. The second line renders as a bare, meaningless `T`.
2. `branch 12 zu->rail symbol/cap (480, 1200) a81.8699` — the upper-zone
   capacitance is drawn at 81.87 degrees, not vertical. `via: [[480, 380]]`
   moved the wire sideways but *not* the point where it meets the rail, which
   stays directly below `zu` at x=620, so the last leg is a long diagonal.

## Round 5 — structural rework, not a remedy

Round 4's `angle` was reverted. The real cause of round 1's warning was that
the slab branch and the two down-left sources on `zg` occupied the same column,
so a source lead always crossed the slab's label. Reworked instead:

- `zg`'s capacitance moved off the straight-down column (`via` now has a second
  waypoint on the rail line so the drop is a true vertical - see round 4 note 2)
- the slab now runs straight down from `zg` to `grd`, with its label on the
  right
- the four wall-layer interface nodes lost their labels

```
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] branch 7 zg->grd: its label was pushed 20 past its own clearance to get around the wire of branch 5 zg->out and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 5 zg->out so it does not run past this label, or set `side` to one of the two the solver does not try (it tries only the sides of the branch), or `angle` for a direction between those four
EXIT=1
```

Note: still "27 labels placed" with four nodes carrying no `label` at all, so
an unlabelled node is still counted.

## Round 6 — remedy 1, literally (this time it applies)

"move a `via` waypoint on branch 5 zg->out so it does not run past this label".
Branch 5 turns down at x=960, inside the slab label's band (x 920-1080). Moved
the turn to x=1120, clear of the label on the right.

```
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 1 warning, 0 notes
warning: [wire-through-symbol] branch 5 zg->out runs straight through branch 0 zg->w1  -> route it around with `via`, or move the symbol along its branch with `at`
EXIT=1
```

**Remedy 1 applied cleanly and traded one warning for another.** There is no
free x between the slab label's right edge (1080) and the gypsum board symbol
(988-1072): the label and the symbol overlap in x, so any turn that clears the
label is inside the symbol. The remedy is locally correct and globally
impossible, and the finding cannot know that.

## Round 7 — move the label out of the corridor instead

Reverted branch 5 to x=960. Moved the slab symbol from `at [900, 720]` to
`at [900, 1060]`, below both the lintel run (y=820) and the glazing run
(y=980), so a right-hand label has nothing to get around. Moved `grd` to
(900, 1240), both capacitance columns left (x 620 and x 380), both `zg`
sources to x=760, rail to y=1420.

```
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

`describe` confirms the symbols are back on their wires - `branch 7 ... a90`,
`branch 8 ... a90`, `branch 11/12 symbol/cap ... a90` - so the round-4 damage
is undone and the capacitance drops are true verticals.

Two things `describe` still showed wrong:

```
  node 'w1'              node            (1160, 620)       above           7x17   T
  node 'out'             node            (2240, 620) a135  below right   70x33   flipped   Outdoor air | T_out = -4 C
```

- `w1`-`w4` print a lone italic `T` even with **no `label`, no `sub` and no
  `value` at all**. There is no way to write a plain junction.
- `out` asked for `angle: 135` (above-left) and got below-right, because
  branch 4's label was sitting in the above-left slot.

## Round 8 — final

- `w1`-`w4` changed to `"kind": "corner"`. This is the only way found to get a
  series junction that prints nothing; the cost is that the layer interfaces
  are no longer nodes a reader can point at, and the label count drops by four.
- branch 4 (`w4->out`) given `"side": "down"` to free the above-left slot for
  `out`'s label.

```
examples/gallery/02-building/house.json: 23 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

23 = 6 labelled nodes + 13 branches + 4 sources; the four `corner` nodes are
correctly excluded. `describe` now shows every symbol on its own wire, `out`
`a135 above left` with no flip, and no stray `T`.

Rendered: `house.svg`, canvas 2354.6 x 1429.8.

One placement left standing, deliberately: `node 'zu' ... below flipped`. The
upper-zone label sits below its node because the stairwell source's lead
occupies the space above it. It is legible and unambiguous, and the design the
solver is documented to have - try the automatic side, then the opposite -
worked exactly as advertised. No note was raised for it.
