# Rounds

Written as each round happened.

## Round 1 - first draft

Layout idea: heat runs left to right, vessel (300 K, `fixed`) -> shield (40 K) ->
cold mass (4.2 K). Three parallel paths in each gap, drawn as lanes at y = 300
(main), 450 and 600. Cryocooler stages as `flow` sources with `from`. Cold mass
capacitance dropped to a rail at y = 780, routed right with `"via": [[1400, 300]]`
so that it would miss the lane wires arriving vertically at x = 1300. Explicit
`side` on every horizontal branch.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean on the first run, so there were no findings and no remedies to apply.

`describe` disagreed:

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: canvas 1339 x 710, 13 labels
...
  branch 6 cm->rail   symbol/cap   (1350, 540) a101.768   right   86x33   Cold mass | C_cm = 900 J/K
```

`a101.768` on a capacitance that was meant to hang vertically. The `via`
`[[1400, 300]]` moved the wire out to x = 1400, but the branch still ends at the
rail point *directly below the node* (1300, 780), so the last leg is a 480-unit
diagonal slashing across the bottom right. The schema reads as though the
waypoint moves the meeting point:

> `"to": "rail"` drops straight down to the reference rail from wherever the
> other end is. ... Give it `via` if you want it somewhere else

It does not. The meeting point is pinned to the node's own x, whatever the `via`
says. **No finding fired for this.** A capacitance 12 degrees off vertical, with
a 480-unit diagonal wire, is not something `check` grades.

## Round 2 - re-layout so the capacitance can drop cleanly

Re-laid out rather than patched, because the diagonal is a consequence of the
lane geometry: both extra paths into the cold mass arrive vertically at x = 1300,
which is exactly the column the capacitance needs, and a rail branch cannot meet
the rail anywhere else.

Change: put all four parallel leak lanes **above** the main line (lanes y = 310
and y = 160, main line y = 460), leaving everything below the main line free. The
capacitance now drops straight from (1300, 460) to the rail at y = 760 with
nothing in its column, and the Joule `diss` source and the two cryocooler `flow`
sources go below the main line where there is room. `sh` and `cm` node labels
moved to `"angle": 135`, since straight up is now the lane column at the node's
own x.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: canvas 1450 x 704, 13 labels
...
  branch 6 cm->rail   symbol/cap   (1300, 610) a90   left   86x33   Cold mass | C_cm = 900 J/K
```

`a90`. Fixed, and every other symbol landed where I put it.

## Round 3 - finding out that the clean report was not earned

Two clean runs in a row made me suspicious, because the schema says a parallel
pair should draw a note and I have *three* parallel paths in each gap, both
labelled on the same side. Four probes, in the scratchpad, not in the diagram:

**Probe A - can a branch carry a heat rate at all?** Added `"watts"`, `"heat"`,
`"nonsense"` to a branch.

```
error: branch 0: unknown field 'watts', 'heat' (did you mean 'at'?), 'nonsense'.
Expected: angle, at, from, kind, label, side, sub, to, value, via
```

Good error, and it settles the question: there is no field for it. (See findings 1.)

**Probe B / C - does `parallel-pair-same-side` work?** Two parallel branches, no
explicit `side`: the note fires exactly as documented. Two parallel branches with
`"side": "up"` on both: no note.

**Probe D - three parallel branches, no explicit `side`:** three notes, one per
pair. So the check does handle more than two.

**Probe E - the same three branches with `"side": "up"` on all three:**

```
probeE.json: 5 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Zero notes, with all three labels demonstrably on the same side. **Setting `side`
suppresses `parallel-pair-same-side` outright** - and `side` is the field the
schema page tells you to set on parallel pairs ("A parallel pair needs `side`").
So my two clean reports were clean because I had silenced the check, not because
the drawing satisfied it.

Re-ran the real diagram with every `side` stripped, to see what it had been
hiding:

```
$ PYTHONPATH=src python -m thermodraw check .../dewar_bare.json
dewar_bare.json: 13 labels placed, 0 errors, 1 warning, 6 notes
warning: [label-in-a-corridor] branch 3 sh->cm: its label sits inside a loop of the
      network, 18 from the opposite path and 33 tall, so it reads as belonging to
      either  -> set `side` to send it outside the loop
note: [parallel-pair-same-side] branch 0 v->sh and branch 1 v->sh ...
note: [parallel-pair-same-side] branch 0 v->sh and branch 2 v->sh ...
note: [parallel-pair-same-side] branch 1 v->sh and branch 2 v->sh ...
note: [parallel-pair-same-side] branch 3 sh->cm and branch 4 sh->cm ...
note: [parallel-pair-same-side] branch 3 sh->cm and branch 5 sh->cm ...
note: [parallel-pair-same-side] branch 4 sh->cm and branch 5 sh->cm ...
EXIT=1
```

### Applying the remedies literally

- **`label-in-a-corridor` on branch 3** - remedy: "set `side` to send it outside
  the loop". Branch 3 is the main line at y = 460 and the loop is closed by branch
  4 at y = 310, so outside the loop is `"down"`. **Worked, literally, first try.**
- **The six `parallel-pair-same-side` notes** - remedy on each: "set `side` to
  `down` on the lower of the two". Applied to all six literally: the lower member
  of each pair is branch 0 (pairs 0-1, 0-2), branch 1 (pair 1-2), branch 3 (pairs
  3-4, 3-5), branch 4 (pair 4-5). So branches 0, 1, 3, 4 get `"side": "down"`.

```
$ PYTHONPATH=src python -m thermodraw check .../dewar_literal.json
dewar_literal.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Zero findings - but this is a **false clear**. `describe` on that same file:

```
  branch 0 v->sh    symbol/cond   (490, 460)   below   ...
  branch 1 v->sh    symbol/rad    (540, 310)   below   ...
  branch 3 sh->cm   symbol/cond   (1030, 460)  below   ...
  branch 4 sh->cm   symbol/rad    (1120, 310)  below   ...
  branch 6 cm->rail symbol/cap    (1300, 610) a90 left  86x33  flipped  ...
```

Branches 0 and 1 are still on the same side as each other, and so are 3 and 4.
The condition the note describes is still true; the note is gone only because
`side` was set. Following the remedy literally on all six pairs is *guaranteed* to
end here, because three branches share a node pair and there are only two sides -
the remedy has no fixed point. It also made the capacitance label `flipped`, which
the round-2 arrangement did not.

So: the remedy for `label-in-a-corridor` worked literally and is kept. The remedy
for `parallel-pair-same-side` cannot be satisfied, and applying it literally only
turned the check off, so it is **not** applied.

## Round 4 - final

Kept the round-2 geometry, which is the better drawing, and deleted the four
redundant `"side": "up"` hints on branches 1, 2, 4 and 5. `describe` output before
and after is byte-identical (`diff` on the elements block: no difference) - the
solver picks `above` for those four on its own - but with the hints gone the two
notes are *printed* instead of silently suppressed. A note I am leaving standing
should be visible in the report I hand over.

`"side": "down"` is kept on branches 0 and 3 (clears the corridor warning on 3,
and keeps both main-line labels out of the band where the `sh` and `cm` node
labels sit), and `"side": "left"` on the capacitance.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 0 warnings, 2 notes
note: [parallel-pair-same-side] branch 1 v->sh and branch 2 v->sh run between the same
      two nodes and both labels went to the same side  -> set `side` to "down" on the
      lower of the two
note: [parallel-pair-same-side] branch 4 sh->cm and branch 5 sh->cm run between the same
      two nodes and both labels went to the same side  -> set `side` to "down" on the
      lower of the two
EXIT=0
```

**Why these two notes are left standing.** Each gap carries three parallel paths,
not two, so the pigeonhole makes at least one same-side pair unavoidable: two
sides, three branches. The specific pairs left are branches 1 and 2 (lanes y = 310
and y = 160) and branches 4 and 5 (the same two lanes on the right). The lanes are
150 apart and each label (33 tall, per `describe`) sits directly above its own box
with roughly 100 units of clear air between it and the other path, so neither
label is ambiguous about which box it belongs to - which is the thing the note is
warning about. `label-in-a-corridor`, which is the warning-severity version of the
same worry, does not fire on either of them. Taking the remedy would put branch 1's label into the band
between the lane and the main line, where it would be closer to the `sh` node
label, i.e. worse.

Rendered:

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/03-cryogenic/dewar.json \
    -o examples/gallery/03-cryogenic/dewar.svg
examples\gallery\03-cryogenic\dewar.svg (18,243 bytes)
EXIT=0
```

`check --strict` exits 1, as expected with notes standing.
