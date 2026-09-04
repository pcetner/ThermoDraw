claude-opus-5 (Claude Code, as a subagent)

# 12-furnace — check rounds

## Round 1

The first draft of `wall.json`, written from `docs/schema.md` and the brief
alone. No node carries `at`; no branch or source carries `at` or `via`.

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/12-furnace/wall.json
examples/gallery/12-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean on the first round. No findings, so no remedy was applied and none is
graded here.

**Did the library refuse the file?** No. It never exited 2 and never named a
node. The four nodes form one chain — `furn — bb — shell — shop` — with the
convection and radiation branches sharing the `shell`/`shop` pair rather than
adding a third neighbour to either, so the solver placed every node itself.
Nothing was added to the file in response to a refusal, because there was
none.

9 labels placed is the number the file implies: 4 nodes + 4 branches +
1 source. Nothing was dropped.

Two things I had expected to cost a round and did not:

- The `shell`/`shop` **parallel pair** placed itself. The schema's advice
  ("A parallel pair needs `via` first, and then `side`") is written for a file
  that places its own nodes; when the solver places them it already routes the
  two branches 80 above and below the line, and the labels took opposite
  sides on their own — no `symbols-overlap`, and not even the
  `parallel-pair-same-side` note.
- The three firebrick courses as `count: 3, arrangement: series` fit in the
  solved 520-unit run between `furn` and `bb` without a `series` overlap.

### `describe`, round 1

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw describe examples/gallery/12-furnace/wall.json
examples/gallery/12-furnace/wall.json: canvas 1390 x 320, 9 labels

placements: anchor x1, ground x2, node x4, symbol/cond x4, symbol/conv x1,
            symbol/flux x1, symbol/rad x1, wire x13

network:
  furn --cond x3 series-- bb
  bb --cond-- shell
  shell --conv/rad-- shop
  source 0 --flux-> furn

nodes:
  furn           fixed    at (200, 150) solved
  bb             free     at (720, 150) solved
  shell          free     at (1040, 150) solved
  shop           fixed    at (1340, 150) solved

elements:
  branch 0 furn->bb      symbol/cond x3  (460, 150)        above         128x68   Firebrick courses | R_cond = 0.06 K/W | q = 3000 W | 3 in series = 0.18 K/W
  branch 1 bb->shell     symbol/cond     (880, 150)        above         106x33   Ceramic fibre board | R_cond = 0.18 K/W
  branch 2 shell->shop   symbol/conv     (1190, 70)        above         102x33   Natural convection | R_conv = 0.05 K/W
  branch 3 shell->shop   symbol/rad      (1190, 230)       below         104x33   Radiation to shop | R_rad = 0.075 K/W
  source 0 -> furn       symbol/flux     (90, 150)         above         104x33   Flame and hot gas | q″_rad = 18 W/cm²
  node 'furn'            node            (200, 150)        above          92x33   Furnace interior | T_furn = 1200 °C
  wall of node 'furn'    ground          (200, 162) a90    (no label)
  node 'bb'              node            (720, 150)        above         126x33   Brick to board interface | T_bb = 660 °C
  node 'shell'           node            (1040, 150)       above          87x33   Steel shell | T_shell = 120 °C
  node 'shop'            node            (1340, 150)       above          80x33   Shop air | T_shop = 30 °C
  wall of node 'shop'    ground          (1340, 162) a90   (no label)
EXIT=0
```

No label is marked `flipped`, `pushed` or `OVERLAPS`. The `network` block is
the network I meant, so the file was accepted as drawn and the render run.

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw render examples/gallery/12-furnace/wall.json -o examples/gallery/12-furnace/wall.svg
examples\gallery\12-furnace\wall.svg (95,991 bytes)
EXIT=0
```

Total: **one round**, no errors, no warnings, no notes, no refusal.

## `check --physics` on the final diagram

Run on the finished file, pasted exactly as it came:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/12-furnace/wall.json
examples/gallery/12-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Silent, and silent in the strong sense: there is no `physics-not-checked`
note, so every free node in the diagram was actually checked, not skipped.
The two free nodes are `bb` and `shell`, and both balance on the brief's own
numbers, unaltered:

- `bb`: (1200 − 660) / (3 × 0.06) = 3000 W in; (660 − 120) / 0.18 = 3000 W out.
- `shell`: 3000 W in; (120 − 30) / 0.05 = 1800 W and (120 − 30) / 0.075 =
  1200 W out, summing to 3000 W.

No number in the diagram was adjusted to get this. What `--physics` does
**not** see is the one number that does not close — see `findings.md`, item 1:
the 18 W/cm² flux sits on a `fixed` node, and a flux has no area, so it is
outside the balance either way.
