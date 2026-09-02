Model: Claude Opus 5 (`claude-opus-5`) | Harness: Claude Code (Claude Agent SDK), Windows 10, Git Bash

# Rounds — 07-furnace

Working from `docs/schema.md` and the brief only. One section per `check` run,
recorded as it happened.

## Round 1 — first draft

Draft: four nodes on one horizontal line at y=200 (furn 220, bb 840, shell 1180,
shop 1540), the three firebrick courses as one `cond` branch with
`count: 3, arrangement: "series"`, the board as a plain `cond`, and the shell
losses as two branches `shell->shop` (`conv` with `"side": "up"`, `rad` with
`"side": "down"`), plus a `flux` source arriving at `furn`.

```
examples/gallery/07-furnace/wall.json: 9 labels placed, 1 error, 0 warnings, 0 notes
error: [symbols-overlap] branch 2 shell->shop and branch 3 shell->shop overlap by 32  -> move one of them with `at`
EXIT=1
```

Finding 1 — `symbols-overlap`, remedy "move one of them with `at`":
applied literally, `at: [1440, 200]` on branch 3 (the `rad` one), leaving
branch 2 at its default centre. Result in round 2.

Note on what I expected: `side: up` / `side: down` moves only the *labels*, so
two branches between one pair of nodes share a single wire run and their two
boxes land on top of each other. Nothing in the schema says a parallel pair is
drawn as two separate wires; the "A parallel pair needs `side`" advice under
Coordinates reads as though the geometry is handled and only the text needs a
hint. It is not.

## Round 2 — after moving the `rad` symbol with `at`

```
examples/gallery/07-furnace/wall.json: 9 labels placed, 1 error, 1 warning, 0 notes
error: [symbols-overlap] branch 2 shell->shop and branch 3 shell->shop overlap by 4  -> move one of them with `at`
warning: [wire-through-symbol] branch 2 shell->shop and branch 3 shell->shop cross each other, each one's wire running through the other's symbol  -> route either of them around with `via`, which clears both, or move one symbol along its branch with `at`
EXIT=1
```

Finding 1 — `symbols-overlap`, remedy "move one of them with `at`":
**the literal remedy did not clear it.** Overlap went 32 -> 4 and the error
stood. Sliding a symbol along a shared wire cannot clear it, because both
symbols are on the same wire; the only way out is to stop sharing the wire.
The remedy text names the one field that cannot fix this finding.

Finding 2 — `wire-through-symbol`, remedy "route either of them around with
`via`, which clears both": this is the correct remedy, and it says so
explicitly ("which clears both"). Applied to branch 3 (`rad`):
`via: [[1260,200],[1260,300],[1460,300],[1460,200]]`, leaving each node
sideways before turning as the Coordinates section advises, with the symbol
moved onto the lower run at `at: [1360, 300]`. Result in round 3.

## Round 3 — after routing the `rad` branch with `via`

```
examples/gallery/07-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean. 9 labels placed is the count the file predicts: 4 nodes + 4 branches +
1 source, no `corner` nodes. No notes left standing.

Findings cleared: both round-2 findings went at once, exactly as the
`wire-through-symbol` remedy promised ("which clears both"). The
`symbols-overlap` error was cleared by the *other* finding's remedy, never by
its own.

### `describe` on the finished diagram

```
examples/gallery/07-furnace/wall.json: canvas 1616 x 294, 9 labels

placements: anchor x1, ground x2, node x4, symbol/cond x4, symbol/conv x1,
            symbol/flux x1, symbol/rad x1, wire x13

network:
  furn --cond x3 series-- bb
  bb --cond-- shell
  shell --conv/rad-- shop
  source 0 --flux-> furn

nodes:
  furn           fixed    at (220, 200)
  bb             free     at (840, 200)
  shell          free     at (1180, 200)
  shop           fixed    at (1540, 200)

elements:
  branch 0 furn->bb      symbol/cond x3  (530, 200)        above         103x68   Firebrick course | R_cond = 0.06 K/W | q = 3000 W | 3 in series
  branch 1 bb->shell     symbol/cond     (1010, 200)       above         106x33   Ceramic fibre board | R_cond = 0.18 K/W
  branch 2 shell->shop   symbol/conv     (1360, 200)       above         102x33   Natural convection | R_conv = 0.05 K/W
  branch 3 shell->shop   symbol/rad      (1360, 300)       below         104x33   Radiation to shop | R_rad = 0.075 K/W
  source 0 -> furn       symbol/flux     (60, 200)         above          97x33   Flame and hot gas | q″_r = 18 W/cm²
  node 'furn'            node            (220, 200)        above          92x33   Furnace interior | T_furn = 1200 °C
  node 'bb'              node            (840, 200)        above          78x33   Brick to board | T_bb = 660 °C
  node 'shell'           node            (1180, 200)       above          87x33   Steel shell | T_shell = 120 °C
  node 'shop'            node            (1540, 200)       above          80x33   Shop air | T_shop = 30 °C
```

### `check --physics` on the finished diagram

Pasted exactly as it came:

```
examples/gallery/07-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Silent. See findings 5 — silence here is doing less work than it looks like it
is doing, because the one number in this brief that does *not* agree with the
others sits on a `fixed` node and on a `flux` source, and `--physics` asks
neither.

### Render

```
python -m thermodraw render examples/gallery/07-furnace/wall.json -o examples/gallery/07-furnace/wall.svg
examples\gallery\07-furnace\wall.svg (16,933 bytes)
EXIT=0
```

---

## `check --physics` on the final diagram

Re-run on the committed `wall.json`, pasted exactly as it came:

```
PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/07-furnace/wall.json
examples/gallery/07-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Identical to the round-3 run above: silent. Nothing was changed to make it so,
and nothing in this brief was adjusted to keep it quiet. The 18 W/cm² flux is
still 60x the 3000 W the rest of the wall carries; `--physics` does not see it
because the source sits on a `fixed` node, which is not asked, and the
`physics-not-checked` note counts only `free` nodes, both of which *were*
checked. See findings 5.
