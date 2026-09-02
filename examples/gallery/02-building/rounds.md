Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

# Rounds — 02-building

Each section is one `check` run: the verbatim output, then what I did about each
finding and whether the remedy the finding named cleared it when applied
literally.

---

## Round 1 — first draft

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

27 labels placed is exactly the count I predicted from the file (10 nodes + 15
branches + 2 sources), so nothing was dropped. No errors and no warnings on the
first draft — the "leave a node sideways before turning" and "space labels, not
symbols" habits, applied by hand while laying it out, appear to have been worth
following.

**Finding 1 — `parallel-pair-same-side` on branches 6 and 7.**

Remedy as named: *set `side` to "down" on the lower of the two.*

Applied literally: **no-op.** Branch 6 is the window (horizontal run at y = 820),
branch 7 is infiltration (horizontal run at y = 1000). y increases downward, so
branch 7 *is* the lower of the two, and it already carries `"side": "down"`. So
does branch 6. The remedy the finding names is already satisfied and the finding
fires anyway. Re-running unchanged to confirm that, then trying something else.

---

## Round 2 — literal remedy applied (no-op), re-run unchanged

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

Confirmed: the named remedy was already in the file and the note still fires.
**Remedy applied literally: did not clear.**

---

## Round 3 — move the *upper* of the pair to "up" instead

The finding's own remedy is unusable, so I inverted it: branch 6 (window, run at
y = 820) set to `"side": "up"`, leaving branch 7 (infiltration, y = 1000) "down".

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 5 gf->out and branch 6 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

The note **moved** rather than cleared: branch 5 is the steel lintel, whose run
is at y = 470 with `"side": "up"`. There are **three** branches between `gf` and
`out` (lintel, glazing, infiltration) and a horizontal run has only two usable
sides, so at least one pair must always share one. Applying the remedy again
here — set "down" on the lower of 5 and 6, i.e. put branch 6 back to "down" —
returns exactly to Round 1. It is a two-state cycle.

---

## Round 4 — try a side the finding does not offer

Set branch 6 to `"side": "right"`, to see whether a non-vertical side escapes the
cycle.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 1 error, 1 warning, 0 notes
error: [label-collision] branch 6 gf->out: its label is printed over the wire of branch 6 gf->out  -> move a `via` waypoint on branch 6 gf->out so it does not run past this label, or set `side` to "up" or "down"
warning: [label-adrift] branch 6 gf->out: its label was pushed 160 past its own clearance to get around branch 2 w2->w3  -> move branch 2 w2->w3 along its branch with `at`, or set `side` to "up" or "down"
EXIT=1
```

Worse: `left`/`right` on a long horizontal branch puts the label on its own wire.
Both findings' remedies say to go back to "up" or "down", which is the cycle.
Reverted branch 6 to `"side": "down"`, i.e. back to the Round 1 file.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

**Decision: the note stands, deliberately.** The brief allows a standing note if
I say why, and this one cannot be cleared: three parallel paths, two sides. The
two that share "down" are the glazing (y = 820) and the infiltration flow
(y = 1000), 180 units apart with nothing between them, so nothing is actually
ambiguous on the page — which is the same reason the schema gives for the hero
being allowed to trip it: "`parallel-pair-same-side` is a note rather than a
warning because the hero diagram breaks it and is fine."

`check` is now **0 errors, 0 warnings, exit 0**.

---

## Round 5 — `describe` and `render` (not check rounds, recorded for completeness)

`describe` exited 0 and reported `canvas 2771 x 1270, 27 labels`, `ground x3`,
`node x10`, `symbol/cond x6`, `symbol/mixed x2`, `symbol/flow-branch x2`,
`symbol/cap x2`, `symbol/conv x2`, `symbol/rad x1`, `symbol/diss x1`,
`symbol/radin x1`, `wire x36` — every count matching the file. Its `network`
block shows one connected graph, so `roof` hanging off `out` alone (which is all
the brief gives it) does not trip `network-in-pieces`.

`render` exited 0 and wrote `house.svg` (29,474 bytes). Grepping the file shows
the CLI already applies `theme.with_variables` (`:root{--sym:...}` blocks for
light, `prefers-color-scheme:dark`, and `[data-theme="dark"]`), so the schema's
"`render` alone ... draws nothing" warning does not apply to the command line.

---

## Final `check` state

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

Four rounds. One finding, uncleanable, left standing with the reason above.

---

## Record-only: `check --physics`

Run once on the final diagram. **Not iterated on.** Where it disagrees with the
drawing, the disagreement is discussed in findings.md and the diagram was not
changed to please it.

```
$ PYTHONPATH=src python -m thermodraw check --physics examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 2 warnings, 1 note
warning: [node-does-not-balance] node 'roof': 0 W arrives and 190 W leaves at the stated values — 85.7 W out by branch 11 roof->out (12 K over 0.14 K/W); 105 W out by branch 12 roof->sky (23 K over 0.22 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [node-does-not-balance] node 'uf': 240 W arrives and 22.2 W leaves at the stated values — 240 W in by branch 10 gf->uf; 22.2 W out by branch 9 gf->uf (2 K over 0.09 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=1
```

(The first invocation printed the same text with `—` mangled to `?` by the
Windows console codepage; the block above is the same run re-captured with
`PYTHONIOENCODING=utf-8` so the characters are the real ones. No other
difference, and the diagram was not touched between them.)

Both warnings are true of the brief's own numbers and both would be wrong to
"fix":

- **`roof`** has 190 W leaving and nothing arriving because the brief gives the
  roof a temperature (8 °C) and two loss paths but never says what heats it —
  there is no roof-to-upper-zone resistance anywhere in the brief. Inventing one
  would be inventing data.
- **`uf`** takes 240 W up the stairwell and loses only 22.2 W back down through
  the intermediate floor, because the brief gives the upper zone no other path to
  anywhere. Also true, also not mine to fix.
- **`gf` is not listed at all**, and it is the node that is furthest out of
  balance (1.47 kW in, 693 W out). See findings.md §5 — the physics check skips
  it, silently, because the wall's interior junction nodes have no temperature,
  which is the idiom `docs/schema.md` itself recommends for series layers.
