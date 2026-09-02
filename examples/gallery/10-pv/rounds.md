Model: Claude Opus 5 (`claude-opus-5`). Harness: Claude Code (Claude Agent SDK), Windows 10 Pro 19045, Bash tool (Git Bash), `PYTHONPATH=src PYTHONIOENCODING=utf-8`.

# Rounds

## Round 1 — first draft

Written straight from `docs/schema.md` and the brief. Layout choice: heat
leaves the cell layer **upward** to the two front-side boundaries (sky,
ambient) and **downward** to the back, so the sky path and the roof path are
told apart by direction alone. No `size` key (so no `off-canvas` /
`frame-off-centre` to chase), no `rail` (steady state, no capacitance).

`check`:

```
examples/gallery/10-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0. **No findings, so no remedies to apply or evaluate.** 10 labels
placed is the number worked out from the file: 5 nodes + 4 branches + 1
source.

Three pieces of advice from the schema page were applied *before* the first
run rather than after a finding, so the checker never had the chance to
disagree with them:

- `"angle": 45` on `cell`, because it has four attachments (rad up, conv
  right, cond down, source lead from the left) and `side` only offers four
  orthogonal slots — the page's "only `angle` reaches the diagonals".
- `"angle": 135` on `back` (cond arrives from straight above, the clip comb
  leaves to the right) and `"angle": 90` on `roof` (comb arrives from the
  left, and the comb's lanes converge above the node).
- No `side` pair was needed: no two branches run between the same pair of
  nodes, so `parallel-pair-same-side` cannot fire here.

One thing the page warns about *was* violated deliberately and did not fire:
branch 0 (`cell -> sky`) leaves the cell **straight up** via `[[320, 140]]`,
which is exactly the "a `via` that goes straight up from a node" case the
page says almost always means `label-adrift`. It did not, because `cell`'s
own label was already sent to the diagonal by `angle: 45`. `describe` shows
that label as `pushed 8` — the finding threshold is "adrift past 8", so it
sits one unit inside the limit rather than comfortably clear.

## Round 1 — `describe`

```
examples/gallery/10-pv/array.json: canvas 954 x 766, 10 labels

placements: anchor x2, ellipsis x1, ground x3, node x5, symbol/cond x7,
            symbol/conv x1, symbol/diss x1, symbol/rad x1, wire x22

network:
  cell --rad-- sky
  cell --conv-- amb
  cell --cond-- back
  back --cond x4 parallel-- roof
  source 0 --diss-> cell

nodes:
  cell           free     at (320, 380)
  sky            fixed    at (900, 140)
  amb            fixed    at (900, 380)
  back           free     at (320, 700)
  roof           fixed    at (880, 700)

elements:
  branch 0 cell->sky     symbol/rad      (610, 140)        above          89x50   Glass to sky | R_rad = 0.2 K/W | q = 275 W
  branch 1 cell->amb     symbol/conv     (610, 380)        above         102x50   Wind over glass | R_conv = 0.05 K/W | q = 600 W
  branch 2 cell->back    symbol/cond     (320, 540) a90    right         147x33   Encapsulant and backsheet | R_cond = 0.4 K/W
  branch 3 back->roof    symbol/cond x6  (600, 700)        above          95x50   Mounting clips | R_cond = 1.6 K/W | 4 in parallel
  source 0 -> cell       symbol/diss     (140, 380)        above         107x33   Absorbed solar heat | P_sun = 900 W
  node 'cell'            node            (320, 380) a45    above right    74x33   pushed 8   Cell layer | T_cell = 65 °C
  node 'sky'             node            (900, 140)        above          73x33   Effective sky | T_sky = 10 °C
  node 'amb'             node            (900, 380)        above          78x33   Ambient air | T_amb = 35 °C
  node 'back'            node            (320, 700) a135   above left     80x33   Backsheet | T_back = 55 °C
  node 'roof'            node            (880, 700) a90    right          76x33   Roof deck | T_roof = 45 °C
```

The `network` block is the network I meant, line for line. No second round
was needed, so nothing below this point is a fix.

## Round 1 — `check --physics`

Pasted exactly as it came:

```
examples/gallery/10-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
```

Silent. No `node-does-not-balance`, no `rate-does-not-match`, and no
`physics-not-checked` note — which per the schema page means **both** free
nodes (`cell`, `back`) were actually checked, not skipped.

## Render

```
examples\gallery\10-pv\array.svg (22,851 bytes)
```

Exit 0. Not opened, not viewed.

## Final `check --physics` on the finished diagram

Command, run at the end of the session on the file as committed:

```
PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/10-pv/array.json
```

Output, pasted exactly as it came:

```
examples/gallery/10-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0. No number in this diagram was adjusted to make that output quieter;
the values are the brief's throughout.
