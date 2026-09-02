Model: Claude Opus 5 (`claude-opus-5`). Harness: Claude Code (Claude Agent SDK), Windows 10 Pro 19045, commands run via Git Bash.

# Rounds

## Round 1 — first draft, from `docs/schema.md` alone

Diagram as first written: five nodes (`vessel` fixed 300 K, `shield` free 40 K,
`he` phase 4.2 K, `mag` free 4.5 K, `mount` fixed 300 K) in one horizontal line
at y = 200, spaced 360 apart; three `cond` branches and one `break` branch; a
`radin` source and a `flow` source on the shield placed explicitly at y = 80 on
diagonals, and a `diss` source above the magnet.

```
$ python -m thermodraw check examples/gallery/08-cryostat/magnet.json
examples/gallery/08-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0. No findings, so no remedies to apply and nothing to report on whether a
remedy worked. 12 labels placed is exactly the count from the file (5 nodes +
4 branches + 3 sources), so nothing was dropped.

Three pieces of advice in `docs/schema.md` were followed pre-emptively rather
than after being told, and each of them is a finding that did not fire:

- Shield and magnet were given `"side": "down"` from the start, because both
  have sources sitting above them. Without that the node label and the source
  lead compete for the same space.
- The two sources on the shield were given explicit `at`, per "Two sources on
  one node, or a wide label, want an explicit `at` on at least one of them".
- Nodes were spaced 360 apart rather than the suggested 220, because
  `R_cond = 179 K/W` under `Instrumentation leads` is a wide label and the page
  says to space labels, not symbols.

No `via` was used anywhere, so the `label-adrift` trap the doc warns about most
loudly never had a chance to fire.

### `describe`

```
$ python -m thermodraw describe examples/gallery/08-cryostat/magnet.json
examples/gallery/08-cryostat/magnet.json: canvas 1610 x 254, 12 labels

placements: ground x2, node x5, phase x1, symbol/break-branch x1,
            symbol/cond x3, symbol/diss x1, symbol/flow x1, symbol/radin x1,
            wire x13

network:
  vessel --cond-- shield
  shield --cond-- he
  mag --cond-- he
  mag --break-- mount
  source 0 --radin-> shield
  shield --flow-> source 1
  source 2 --diss-> mag

nodes:
  vessel         fixed    at (200, 200)
  shield         free     at (560, 200)
  he             phase    at (920, 200)
  mag            free     at (1280, 200)
  mount          fixed    at (1640, 200)

elements:
  branch 0 vessel->shiel symbol/cond     (380, 200)        above         107x50   G-10 support straps | R_cond = 50 K/W | q = 5.2 W
  branch 1 shield->he    symbol/cond     (740, 200)        above         119x33   Instrumentation leads | R_cond = 179 K/W
  branch 2 mag->he       symbol/cond     (1100, 200) a180  above         137x33   Winding-to-bath coupling | R_cond = 6 K/W
  branch 3 mag->mount    symbol/break-br (1460, 200)       above         168x15   Suspension strut (no heat path)
  source 0 -> shield     symbol/radin    (430, 80) a45     above right   114x33   Multi-layer insulation | q_mli = 30 W
  source 1 shield ->     symbol/flow     (690, 80) a315    below right   114x33   flipped   Cryocooler first stage | q_cc = 35 W
  source 2 -> mag        symbol/diss     (1280, 80) a90    right         145x33   Persistent-joint dissipation | P_j = 0.05 W
  node 'vessel'          node            (200, 200)        above         105x33   Outer vessel (room) | T_room = 300 K
  node 'shield'          node            (560, 200)        below          86x33   Radiation shield | T_sh = 40 K
  node 'he'              node            (920, 200)        above          99x33   Liquid helium bath | T_He = 4.2 K
  node 'mag'             node            (1280, 200)       below          85x33   Magnet winding | T_w = 4.5 K
  node 'mount'           node            (1640, 200)       above         140x33   Room-temperature mount | T_mnt = 300 K
```

One solver mark: `source 1` is `flipped` — the cryocooler label took the
opposite side from the one it wanted. No `pushed`, no `OVERLAPS`, no `adrift`.

### `check --physics`

Pasted exactly as it came:

```
$ python -m thermodraw check --physics examples/gallery/08-cryostat/magnet.json
examples/gallery/08-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0. Silent — and, importantly, **no `physics-not-checked` note**, which per
the schema page means every `free` node was actually checked, not skipped.

### Render

```
$ python -m thermodraw render examples/gallery/08-cryostat/magnet.json -o examples/gallery/08-cryostat/magnet.svg
examples\gallery\08-cryostat\magnet.svg (13,724 bytes)
```

Exit 0. One round; no round 2 was needed.

## Appendix — probes run after the diagram was clean

These are not rounds; the diagram was already clean and none of them changed
it. They were run on scratch copies to turn guesses in `findings.md` into
facts. Output quoted exactly.

**Does a `break` branch count for network connectivity?** Yes. Deleting the
strut:

```
warning: [network-in-pieces] nothing joins 'mount' to the rest of the network  -> connect it with a branch. If a `flow` or `flux` source is standing in for a path that carries heat between two nodes, it cannot join them: a source has one end
```

**Can the strut say it carries zero?** No, both fields are refused, exit 2:

```
error: ...: branch mag-mount is a break, which carries no heat and so no value; got '0'
error: ...: branch mag-mount is a break, which carries no heat and so no rate; got '0'
```

**Does a `phase` neighbour suppress `--physics` on the free nodes either side?**
No. With the helium left as `phase` and the MLI source raised to 3000 W:

```
warning: [node-does-not-balance] node 'shield': 3.01e+03 W arrives and 35.2 W leaves at the stated values: 3e+03 W in by source 0; 35 W out by source 1; 5.2 W in by branch 0 vessel->shield (260 K over 50 K/W); 0.2 W out by branch 1 shield->he (35.8 K over 179 K/W)  -> check the values...
```

and with the joint dissipation raised to 500 W, `node 'mag'` fires too. Both
free nodes are genuinely checked in the shipped file.

**What is `--physics`'s tolerance?** Undocumented, and wide. Sweeping the
`rate` on the G-10 straps against the 5.2 W its ends imply:

```
rate=5.7  err= 9.6%  silent
rate=6.0  err=15.4%  silent
rate=6.1  err=17.3%  silent
rate=6.2  err=19.2%  fires
rate=6.5  err=25.0%  fires
```

The band is somewhere between 17.3% and 19.2% relative.

**MLI as a `rad` branch from the vessel instead of a `radin` source.** Legal
(`rate` with no `value` is accepted), but it costs the shield's balance check:

```
error: [symbols-overlap] branch 0 vessel->shield and branch 1 vessel->shield overlap by 32  -> move one of them with `at`
note: [physics-not-checked] checked 1 of 2 free nodes; not checked: shield (branch 1 vessel->shield has no numeric value)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
```

**Mount placed above the magnet, so it hangs from it.** `check` is clean —
`12 labels placed, 0 errors, 0 warnings, 0 notes` — but `describe` reports
only `ground x2` with no coordinates, and a `fixed` node's wall is always
drawn below it, so the strut would have to leave through the mount's own
boundary hatching. `wire-through-symbol` did not fire, so `check` does not
police that. Not adopted; see `findings.md`.

## Final `check --physics` on the shipped diagram

Re-run on the finished file, pasted exactly as it came:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/08-cryostat/magnet.json
examples/gallery/08-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0. Unchanged from the round 1 run above.
