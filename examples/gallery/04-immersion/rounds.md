# Rounds

## Round 1 — first draft, written from `docs/schema.md` alone

Diagram written before running anything: seven nodes on one horizontal line at
`y = 150` spaced 340 apart, boundary node at the right end, rail at `y = 380`
carrying one capacitance, four sources.

Spacing choice was made from the schema's own advice — "Space nodes about 220
apart" plus "Space labels, not symbols. A box is 84 wide, but
`R_cond = 0.000877 K/W` is over twice that". My resistance values are the same
shape as that example (`0.00375`, `0.0028`), so I opened at 340 rather than 220
on the assumption that 220 would trip `nodes-too-close`. It was never tested,
because nothing was ever reported.

Exact `check` output:

```
examples/gallery/04-immersion/rack.json: 17 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

17 labels is the count I could work out from the file in advance: 7 nodes + 6
branches + 4 sources, no `corner` nodes. Nothing was dropped.

**Findings raised: none. No remedies to apply, so nothing to report on whether
they work when applied literally.**

`describe` output for the same file:

```
examples/gallery/04-immersion/rack.json: canvas 2438 x 348, 17 labels

placements: ground x1, node x7, symbol/cap x1, symbol/cond x1,
            symbol/conv x4, symbol/diss x2, symbol/flow x2, wire x16

rail: y 380, span (200, 2380), reference 'air'

nodes:
  j              free     at (200, 150)
  ihs            free     at (540, 150)
  sat            free     at (880, 150)
  coil           free     at (1220, 150)
  tw             free     at (1700, 150)
  fac            free     at (2040, 150)
  air            fixed    at (2380, 150)

elements:
  branch 0 j->ihs        symbol/cond     (370, 150)        above         118x33   Each of 8 processors | R_cond = 0.0275 K/W
  branch 1 ihs->sat      symbol/conv     (710, 150)        above         125x33   Pool boiling | R_conv = 0.00375 K/W
  branch 2 sat->coil     symbol/conv     (1050, 150)       above         117x33   Condensing film | R_conv = 0.0028 K/W
  branch 3 tw->fac       symbol/conv     (1870, 150)       above         117x33   CDU plate exchanger | R_conv = 0.0019 K/W
  branch 4 fac->air      symbol/conv     (2210, 150)       above         117x33   Dry cooler | R_conv = 0.0058 K/W
  branch 5 sat->rail     symbol/cap      (880, 265) a90    right         103x33   Fluid inventory | C_fl = 240000 J/K
  source 0 -> j          symbol/diss     (162, 150)        above         114x33   8 processors x 400 W | P_chip = 3200 W
  source 1 coil ->       symbol/flow     (1350, 150)       above         109x33   Carried out by water | q_w = 3200 W
  source 2 -> tw         symbol/flow     (1560, 150)       below         101x33   Carried in by water | q_w = 3200 W
  source 3 -> tw         symbol/diss     (1700, 112) a90   left           89x33   flipped   Pump work | P_pump = 800 W
  node 'j'               node            (200, 150)        below          99x33   flipped   Processor junction | T_j = 72 ?C
  node 'ihs'             node            (540, 150)        above          76x33   Heat spreader | T_ihs = 61 ?C
  node 'sat'             node            (880, 150)        above          90x33   Boiling dielectric | T_sat = 49 ?C
  node 'coil'            node            (1220, 150)       above          79x33   Condenser coil | T_coil = 40 ?C
  node 'tw'              node            (1700, 150)       below         128x33   flipped   Technical water, 30 C in | T_out = 38 ?C
  node 'fac'             node            (2040, 150)       above          73x33   Facility water | T_fac = 26 ?C
  node 'air'             node            (2380, 150) a90   right          78x33   Ambient air | T_amb = 24 ?C
```

(The `?C` is the terminal, not the file — a Windows console is cp1252 and the
degree sign is replaced on the way out. The JSON says `°C`.)

Everything placed where I intended. Two placements I had not predicted and was
happy with: node `j`'s label flipped **below** the line to get out of the way of
the `diss` arrow coming in from the left, and node `tw`'s label flipped below to
get out from under the pump arrow coming down from above. I had set neither
`side` nor `angle` on either. That is the solver doing the thing the README-level
promise says it does.

Round 1 is clean: exit 0, no errors, no warnings, no notes. No further rounds
were needed, so there is no round 2.

## Render

```
PYTHONPATH=src python -m thermodraw render examples/gallery/04-immersion/rack.json -o examples/gallery/04-immersion/rack.svg
```

```
examples\gallery\04-immersion\rack.svg (16,099 bytes)
EXIT=0
```

Rendered once, clean, and not opened. `check` and `describe` were the only
instruments used.
