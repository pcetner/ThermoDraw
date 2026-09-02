Model: claude-opus-5 (Opus 5) | Harness: Claude Code 2.1.255, claude-desktop entrypoint, Windows 10.0.19045, Python 3.11.9, `thermodraw` run from `src/` on branch `master`.

# Rounds

One section per round, written as it happened.

## Round 1 — first draft, straight from `docs/schema.md`

The diagram written before any checking: five nodes (board, flange, an
untitled vapour-chamber-top junction with no temperature, housing bore,
seawater), four branches (`spread`, `pipe` with a two-waypoint corner,
`conv`, `mixed`), one `diss` source.

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

**Findings: none.** 0 errors, 0 warnings, 0 notes on the first run, so no
remedy was applied and there is nothing to report about whether a remedy
worked. 10 labels placed = 5 nodes + 4 branches + 1 source, which is the
count the file predicts, so nothing was dropped.

Two habits from the schema were followed in the draft rather than
discovered by `check`, and they are probably why round 1 was clean:

- the `pipe` branch leaves `flange` sideways (`via` `[560, 320]`) before
  turning up to `[560, 160]`, instead of rising straight out of the node;
- nodes are 280 apart on the runs, not the 220 the schema suggests as a
  minimum, because `Housing wall to sea | R_cond+conv = 0.15 K/W` is a
  127-wide label.

No second round was needed. There is no round 2.

## `check --physics` on the finished diagram

Pasted exactly as it came, unedited:

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
```

The note is left standing deliberately. Its remedy is "give the node, or
its neighbour, a `value`", and the node in question is the top of the
vapour chamber, whose temperature the brief does not state. Applying that
remedy literally would mean inventing a number and putting it on the
drawing as if it had been measured. The brief says not to adjust a number
to make this output quieter, so the note stays and the three unchecked
nodes are unchecked.

For the record, the numbers do close by hand, all the way down the chain,
at 60 W throughout:

```
board  37.0
  spread 0.30 x 60 = 18.0 K
flange 19.0   (stated 19)
  pipe   0.02 x 60 =  1.2 K
vct    17.8   (not stated anywhere)
  conv   0.08 x 60 =  4.8 K
bore   13.0   (stated 13)
  mixed  0.15 x 60 =  9.0 K
sea     4.0   (stated 4)
```

So the brief's numbers agree with each other exactly. `--physics` checked
1 of the 4 free nodes and could not see any of that.

## `check --physics` re-run on the final diagram

Re-run after the diagram was finalised and rendered, exactly as invoked:

```
PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/09-subsea/bottle.json
```

Output, pasted exactly as it came:

```
examples/gallery/09-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vct' has no temperature); vct (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
```

Exit code 0. Identical to the run recorded above; the diagram did not change
between them. The note is still standing, for the reason given in that section.
