Model claude-opus-5 (Opus 5, 1M context) in Claude Code, running as a subagent.

# Rounds — 11-battery

## Round 1

First draft. Written from `docs/schema.md` and `brief.md` alone. No node
carries `at`; no branch or source carries `at` or `via`. The only coordinate
in the file is `rail.y`, which the schema says is "what actually places the
line" and which is not a node `at`.

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/11-battery/pack.json
examples/gallery/11-battery/pack.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

No findings, so no remedies to apply. Twelve labels placed is exactly the
count the file implies: five nodes, six branches, one source.

The library **did not refuse the file**. It named no node and asked for no
`at`. The network is a chain — `core – floor – plate – film – chill` — with
two capacitances hanging off it to `rail`, and the schema says `rail` and
sources do not count toward the at-most-two-others rule. They did not.

`describe` on the same round, to confirm the drawing is the one meant:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw describe examples/gallery/11-battery/pack.json
examples/gallery/11-battery/pack.json: canvas 1319 x 343, 12 labels

placements: ground x1, node x5, symbol/cap x2, symbol/cond x1,
            symbol/contact x1, symbol/conv x1, symbol/diss x1,
            symbol/flow-branch x1, wire x15

rail: y 372, span (200, 1270), reference 'chill'

network:
  core --cond-- floor
  floor --contact-- plate
  plate --conv-- film
  core --cap-- rail
  plate --cap-- rail
  film --flow-> chill
  source 0 --diss-> core

nodes:
  core           free     at (200, 150) solved
  floor          free     at (480, 150) solved
  plate          free     at (760, 150) solved
  film           free     at (1040, 150) solved
  chill          fixed    at (1270, 150) solved

elements:
  branch 0 core->floor   symbol/cond     (340, 150)        above         109x50   Jelly roll to can floor | R_cond = 0.24 K/W | q = 200 W
  branch 1 floor->plate  symbol/contact  (620, 150)        above         141x33   Compressible thermal pad | R_contact = 0.10 K/W
  branch 2 plate->film   symbol/conv     (900, 150)        above         114x33   Milled microchannels | R_conv = 0.05 K/W
  branch 3 film->chill   symbol/flow-bra (1155, 150)       above         105x33   Pumped glycol loop | q_loop = 200 W
  branch 4 core->rail    symbol/cap      (200, 261) a90    right         100x33   Cells | C_cells = 4200 J/K
  branch 5 plate->rail   symbol/cap      (760, 261) a90    right          91x33   Cold plate | C_cp = 1800 J/K
  source 0 -> core       symbol/diss     (90, 150)         above         105x50   Cell dissipation | P_cell = 25 W | each of 8 = 200 W
  node 'core'            node            (200, 150)        above          85x33   Cell core | T_core = 108 °C
  node 'floor'           node            (480, 150)        above          78x33   Can floor | T_floor = 60 °C
  node 'plate'           node            (760, 150)        above          80x33   Cold plate wall | T_plate = 40 °C
  node 'film'            node            (1040, 150)       above          75x33   Coolant film | T_film = 30 °C
  node 'chill'           node            (1270, 150)       above          77x33   Chiller supply | T_chill = 25 °C
  wall of node 'chill'   ground          (1270, 162) a90   (no label)
EXIT=0
```

Every element the brief describes is present and joined the way the brief
describes it. No row carries `flipped`, `pushed` or `OVERLAPS`. The network
block matches the brief line for line, so no second round was needed and no
finding was left standing.

Render, once clean:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw render examples/gallery/11-battery/pack.json -o examples/gallery/11-battery/pack.svg
examples\gallery\11-battery\pack.svg (92,090 bytes)
EXIT=0
```

**Rounds of `check`: 1. Refusals: none. Final status: 0 errors, 0 warnings,
0 notes, exit 0.**

## `check --physics` on the final diagram

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/11-battery/pack.json
examples/gallery/11-battery/pack.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Silent, and silent in the strong sense: there is no `physics-not-checked`
note either, which the schema says means every free node was checked. All
four free nodes balance on the brief's own numbers, unadjusted:

- core: 8 x 25 W in = (108 - 60) / 0.24 = 200 W out
- floor: 200 W in = (60 - 40) / 0.10 = 200 W out
- plate: 200 W in = (40 - 30) / 0.05 = 200 W out
- film: 200 W in = the 200 W the `flow` branch carries out

No number in the file was changed to make this quieter. They are the brief's.
