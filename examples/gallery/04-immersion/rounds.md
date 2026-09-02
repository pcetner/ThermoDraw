Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

# `check` rounds for `examples/gallery/04-immersion/rack.json`

One section per run of `check`, written as I went. For each finding: the
remedy the finding named, applied literally, and whether it cleared.

Five rounds. Round 5 was clean.

---

## Round 1 — first draft

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/04-immersion/rack.json
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 4 warnings, 0 notes
warning: [label-adrift] node 'j': its label was pushed 52 past its own clearance to get around the wire of branch 0 j->ihs and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 j->ihs so it does not run past this label, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'sat': its label was pushed 48 past its own clearance to get around branch 1 ihs->sat and now sits nearer that than the thing it names  -> move branch 1 ihs->sat along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'tw': its label was pushed 40 past its own clearance to get around branch 4 tw->fw and now sits nearer that than the thing it names  -> move branch 4 tw->fw along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [nodes-too-close] node 'coil' and node 'tw' are 260 apart, and the labels along that run come to 262  -> move them apart with `at`. It is the labels that set the spacing, not the symbol, which is only 44 wide
EXIT=1
```

16 labels placed = 7 nodes + 7 branches + 2 sources, so nothing was dropped and
every finding is a placement problem.

Remedies, applied literally:

1. **`label-adrift` on `j`** — named remedies: "move a `via` waypoint on branch
   0 j->ihs", or `angle` on the node. **The first named remedy is impossible.**
   Branch 0 is a `count: 8, arrangement: parallel` group, and the schema says
   "A repeated branch is drawn between its two nodes, so it cannot also take
   `via`." The finding suggests a field the library refuses on that branch.
   Applied the second: `"angle": 135` on `j`.
2. **`label-adrift` on `sat`** — named remedy: move branch 1 along its branch
   with `at`. Applied literally: `"at": [540, 160]` (default was the midpoint,
   590), pulling the box back towards `ihs`.
3. **`label-adrift` on `tw`** — named remedy: move branch 4 along its branch
   with `at`. Applied literally: `"at": [1470, 160]`.
4. **`nodes-too-close` coil/tw** — named remedy: move them apart with `at`.
   Applied literally: `tw`, `fw`, `amb` moved right by 60 (that run 260 -> 320,
   against the 262 asked for); `rail.span` widened to `[180, 1840]`.

## Round 2 — after those four edits

```
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 2 warnings, 0 notes
warning: [label-adrift] node 'j': its label was pushed 96 past its own clearance to get around source 0 -> j and now sits nearer that than the thing it names  -> move source 0 -> j further from its node with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'tw': ...cleared...
warning: [label-adrift] node 'sat': its label was pushed 48 past its own clearance to get around branch 1 ihs->sat and now sits nearer that than the thing it names  -> move branch 1 ihs->sat along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
EXIT=1
```

(The `tw` line above is my annotation, not output — the run printed only the
two warnings quoted.)

Did the remedies clear?

- **`j` adrift: partly.** `angle: 135` did move the label off the branch-0
  comb — the finding stopped naming branch 0. But it moved it straight into
  the dissipation source on the other side, and the overshoot went **up**, 52
  -> 96. One literal remedy, one new problem: the two things a leftmost node's
  label can collide with are on opposite sides of it, and `angle` only ever
  chooses between them.
- **`tw` adrift: yes.** Moving branch 4 with `at` cleared it outright.
- **`nodes-too-close`: yes.** Cleared outright.
- **`sat` adrift: no. The named remedy had literally zero effect.** Moving
  branch 1 fifty units along its branch left the number at *exactly* 48 past,
  the same as before the edit. That is the first sign the finding is
  misdiagnosing: the problem is the width of `sat`'s own label, not where the
  neighbouring box sits.

New edits, both literal:

- `sources[0]`: `"at": [20, 160]` — "move source 0 -> j further from its node
  with `at`", exactly as named.
- `branches[1]`: `"at": [500, 160]` — the same named remedy again, pushed
  harder, to test whether it does anything at all.

## Round 3

```
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 3 warnings, 0 notes
warning: [label-adrift] node 'ihs': its label was pushed 64 past its own clearance to get around the wire of branch 0 j->ihs and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 j->ihs so it does not run past this label, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'sat': its label was pushed 48 past its own clearance to get around branch 2 sat->coil and now sits nearer that than the thing it names  -> move branch 2 sat->coil along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [wire-through-symbol] branch 0 j->ihs runs straight through branch 1 ihs->sat  -> route it around with `via`, or move the symbol along its branch with `at`
EXIT=1
```

Did the remedies clear?

- **`j` adrift: yes.** Moving the source out to `x = 20` cleared it.
- **`sat` adrift: no, and now demonstrably a misdiagnosis.** Applying the named
  remedy harder moved branch 1 out of the way, and the finding simply
  re-blamed the box on the *other* side — same node, same overshoot, **same
  number, 48**, new culprit. `sat`'s label is 192 units wide (`describe`
  confirms) and the runs either side are 260, so it is 48 too wide for the
  space whichever neighbour you move. The remedy text never says that; only
  `nodes-too-close` speaks in those terms, and it did not fire here.
- **Two new findings caused by obeying the remedy.** Pushing branch 1 to
  `x = 500` put it inside the parallel comb, giving `wire-through-symbol`, and
  it crowded `ihs` into its own `label-adrift`. The remedy for one finding
  manufactured two more.

Edits: backed branch 1 out to `"at": [560, 160]` (clear of the comb), and took
the **other** named remedy for `sat` — `"angle": 135` on the node.

## Round 4

```
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] node 'sat': its label was pushed 84 past its own clearance to get around the wire of branch 0 j->ihs and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 j->ihs so it does not run past this label, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
EXIT=1
```

Did the remedies clear?

- **`ihs` adrift and `wire-through-symbol`: yes**, both cleared by moving
  branch 1 back out of the comb.
- **`sat` adrift: no.** `angle: 135` swung a 192-wide label out to the left,
  where it reached past `ihs` entirely and landed on the comb of branch 0 — the
  overshoot went 48 -> 84, worse than doing nothing. And the remedy now offered
  is the impossible one again: a `via` on a `count`ed branch.

At this point **both named remedies for this finding were exhausted**: `at` on
either neighbouring branch does nothing to the number, `angle` makes it worse,
and the third suggestion is refused by the schema. So I stopped applying the
finding's own text and fixed the thing the finding never mentions — the label
does not fit the run.

Edits:

- `sat`: dropped `angle`, back to the default label position.
- Spaced the network out: `ihs -> sat` and `sat -> coil` from 260 to 360, and
  `coil -> tw` to 320. `sat` 720 -> 820, `coil` 980 -> 1180, `tw` 1300 -> 1500,
  `fw` 1560 -> 1760, `amb` 1820 -> 2020, `rail.span` -> `[180, 2040]`.
- Removed the explicit `at` on branch 1 (back to its midpoint default), moved
  branch 4's to `[1670, 160]` for the new geometry.

## Round 5 — clean

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/04-immersion/rack.json
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

No findings, no notes left standing. 16 labels placed, which is the count the
file implies, so nothing was dropped to get there.

---

## Physics check — record only, run once, not iterated on

Run after the diagram was final and clean, as a record. I have **not** changed
the diagram in response to it.

```
$ PYTHONPATH=src python -m thermodraw check --physics examples/gallery/04-immersion/rack.json
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 4 warnings, 0 notes
warning: [node-does-not-balance] node 'fw': 6.32e+03 W arrives and 345 W leaves at the stated values � 6.32e+03 W in by branch 4 tw->fw (12 K over 0.0019 K/W); 345 W out by branch 5 fw->amb (2 K over 0.0058 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [node-does-not-balance] node 'tw': 4e+03 W arrives and 6.32e+03 W leaves at the stated values � 800 W in by source 1; 3.2e+03 W in by branch 3 coil->tw; 6.32e+03 W out by branch 4 tw->fw (12 K over 0.0019 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [rate-does-not-match] branch 4 tw->fw says it carries 4e+03 W, and its ends imply 6.32e+03 W (12 K over 0.0019 K/W)  -> one of `rate`, `value` or an end temperature is wrong
warning: [rate-does-not-match] branch 5 fw->amb says it carries 4e+03 W, and its ends imply 345 W (2 K over 0.0058 K/W)  -> one of `rate`, `value` or an end temperature is wrong
```

(The `�` in two lines is this Windows console failing to print a non-ASCII
separator character; it is not in the file.)

These four warnings are the brief's arithmetic, not my drawing's, and I worked
them out by hand before I wrote a line of JSON — see `transcript.md` section 1.
`(38 − 26) / 0.0019 = 6316 W` but the loop only carries `3200 + 800 = 4000 W`,
and `(26 − 24) / 0.0058 = 345 W` against 4000 W to reject. The cold half of the
brief does not close. Changing the diagram to please the checker would mean
inventing resistances or temperatures the brief does not give. See
`findings.md`.

Worth recording what it did **not** fire on: the whole hot half — `j`, `ihs`
and `sat` — balances, which means the `count: 8, arrangement: parallel` folding
worked exactly as the schema documents it, and the checker tolerated the
condensing film's `(49 − 40) / 0.0028 = 3214 W` against 3200 W (0.45% out,
because the brief rounded `0.0028125` to two figures).
