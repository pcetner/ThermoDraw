Model: claude-opus-5 (Claude Code, running as a subagent). Harness: Claude Code, Bash tool (Git Bash) on Windows 10 Pro, Python 3.11.9, run as `PYTHONPATH=src PYTHONIOENCODING=utf-8`.

# Rounds

Documentation read: `docs/schema.md` and `examples/gallery/13-cryostat/brief.md`, and nothing
else. No `.json` diagram in this repository was opened, nothing under `src/` was read, and no
browser or image viewer was used.

## Before round 1 — the numbers

The brief's arithmetic was checked on paper before anything was written, so that a
`--physics` finding later would mean the drawing was wrong rather than the brief:

- G-10 straps: (300 − 40) / 50 = 5.2 W — matches the stated 5.2 W.
- Instrumentation leads: (40 − 4.2) / 179 = 0.2 W.
- Winding link: (4.5 − 4.2) / 6 = 0.05 W — matches the stated joint dissipation.
- Shield balance: in 5.2 + 30 = 35.2 W; out 35 (cryocooler) + 0.2 (leads) = 35.2 W.
- Winding balance: in 0.05 W; out 0.05 W.

The brief's numbers close exactly. No number was adjusted at any point.

## The shape chosen

One chain of five nodes, so that the brief's "give no node `at`" could be honoured:

    vess --cond-- sh --cond-- he --cond-- w --break-- mt

plus three sources: `radin` into `sh`, `flow` out of `sh`, `diss` into `w`. Every node was
written with no `at`; no branch and no source was given `at` or `via` in any round.

**The library never refused the file.** The solver placed all five nodes on the first
attempt and named no node. The brief's contingency ("If it refuses the file, it names one
node. Give that node `at` …") was never reached, so nothing was given `at`.

## Round 1

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: 12 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] node 'sh': its label was pushed 132 past its own clearance to get around source 0 -> sh and now sits nearer that than the thing it names  -> move source 0 -> sh further from its node with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
EXIT=1
```

`describe` on the same file, to see what the solver had actually done:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw describe examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: canvas 1323 x 365, 12 labels

placements: ground x2, node x5, phase x1, symbol/break-branch x1,
            symbol/cond x3, symbol/diss x1, symbol/flow x1, symbol/radin x1,
            wire x13

network:
  vess --cond-- sh
  sh --cond-- he
  he --cond-- w
  w --break-- mt
  source 0 --radin-> sh
  sh --flow-> source 1
  source 2 --diss-> w

temperatures: absolute, in K

nodes:
  vess           fixed    at (200, 150) solved
  sh             free     at (500, 150) solved
  he             phase    at (790, 150) solved
  w              free     at (1080, 150) solved
  mt             fixed    at (1350, 150) solved

elements:
  branch 0 vess->sh      symbol/cond     (350, 150)        above         107x50   G-10 support straps | R_cond = 50 K/W | q = 5.2 W
  branch 1 sh->he        symbol/cond     (645, 150)        above         119x33   Instrumentation leads | R_cond = 179 K/W
  branch 2 he->w         symbol/cond     (935, 150)        above         111x33   Winding-to-bath link | R_cond = 6 K/W
  branch 3 w->mt         symbol/break-br (1215, 150)       above          90x15   Suspension strut
  source 0 -> sh         symbol/radin    (500, 40) a90     right          70x33   Through MLI | q_mli = 30 W
  source 1 sh ->         symbol/flow     (500, 260) a90    right         114x33   Cryocooler first stage | q_cc = 35 W
  source 2 -> w          symbol/diss     (1080, 40) a90    right         107x33   Persistent-joint loss | P_j = 0.05 W
  node 'vess'            node            (200, 150)        above         110x33   Outer vessel in room | T_vess = 300 K
  wall of node 'vess'    ground          (200, 162) a90    (no label)
  node 'sh'              node            (500, 150)        above          86x33   pushed 132   Radiation shield | T_sh = 40 K
  node 'he'              node            (790, 150)        above          99x33   Liquid helium bath | T_He = 4.2 K
  node 'w'               node            (1080, 150)       below          85x33   flipped   Magnet winding | T_w = 4.5 K
  node 'mt'              node            (1350, 150)       above         140x33   Room-temperature mount | T_mt = 300 K
  wall of node 'mt'      ground          (1350, 162) a90   (no label)
EXIT=0
```

`describe` explained the finding exactly. `sh` has the `radin` source directly above it at
(500, 40) and the `flow` source directly below it at (500, 260), so its label had nowhere
straight to go and was shoved 132 units out. `w`, which has only one source above it,
`flipped` its label to below and was fine without help.

**Remedy applied, literally.** The remedy names two fields: `at` on the source, or `angle`
on the node. The brief forbids `at` on a source, so the other half of the same remedy was
taken — `"angle": 45` on node `sh`, the diagonal that the remedy says is the only thing that
reaches. Nothing else in the file was changed.

**Did the remedy clear it? Yes** — one edit, first try.

## Round 2

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean. 12 labels placed = 5 nodes + 4 branches + 3 sources, so nothing was dropped. No note
was left standing, because there were none.

`describe` after the fix. `sh` now reads `a45 / above right / pushed 8`; `check` reports
adrift past 8, so this sits exactly at the threshold and is clean:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw describe examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: canvas 1553 x 330, 12 labels

placements: ground x2, node x5, phase x1, symbol/break-branch x1,
            symbol/cond x3, symbol/diss x1, symbol/flow x1, symbol/radin x1,
            wire x13

network:
  vess --cond-- sh
  sh --cond-- he
  he --cond-- w
  w --break-- mt
  source 0 --radin-> sh
  sh --flow-> source 1
  source 2 --diss-> w

temperatures: absolute, in K

nodes:
  vess           fixed    at (200, 150) solved
  sh             free     at (500, 150) solved
  he             phase    at (1020, 150) solved
  w              free     at (1310, 150) solved
  mt             fixed    at (1580, 150) solved

elements:
  branch 0 vess->sh      symbol/cond     (350, 150)        above         107x50   G-10 support straps | R_cond = 50 K/W | q = 5.2 W
  branch 1 sh->he        symbol/cond     (760, 150)        above         119x33   Instrumentation leads | R_cond = 179 K/W
  branch 2 he->w         symbol/cond     (1165, 150)       above         111x33   Winding-to-bath link | R_cond = 6 K/W
  branch 3 w->mt         symbol/break-br (1445, 150)       above          90x15   Suspension strut
  source 0 -> sh         symbol/radin    (500, 40) a90     right          70x33   Through MLI | q_mli = 30 W
  source 1 sh ->         symbol/flow     (500, 260) a90    right         114x33   Cryocooler first stage | q_cc = 35 W
  source 2 -> w          symbol/diss     (1310, 40) a90    right         107x33   Persistent-joint loss | P_j = 0.05 W
  node 'vess'            node            (200, 150)        above         110x33   Outer vessel in room | T_vess = 300 K
  wall of node 'vess'    ground          (200, 162) a90    (no label)
  node 'sh'              node            (500, 150) a45    above right    86x33   pushed 8   Radiation shield | T_sh = 40 K
  node 'he'              node            (1020, 150)       above          99x33   Liquid helium bath | T_He = 4.2 K
  node 'w'               node            (1310, 150)       below          85x33   flipped   Magnet winding | T_w = 4.5 K
  node 'mt'              node            (1580, 150)       above         140x33   Room-temperature mount | T_mt = 300 K
  wall of node 'mt'      ground          (1580, 162) a90   (no label)
EXIT=0
```

Worth recording: freeing that one label widened the whole page. The `sh -> he` run grew from
290 to 520 and the canvas from 1323 x 365 to 1553 x 330. The schema warns that the label
solver is not local ("freeing one label can let the next travel a long way"); here it moved
the runs rather than another label, which is the same effect from the other end.

## After round 2 — one deliberate change, not a finding

`check` was already clean, so this is not a round. The schema says, of a boundary node:

> A mount that a cold mass hangs from has its wall above, `"wall": "up"`, so the strut
> arrives from below through clear space instead of through the hatching

The magnet hangs from `mt`, so `"wall": "up"` was added to that node. It did not clear any
finding — no `wire-through-wall` ever fired, because the solver put the strut on the
horizontal line and never below the mount — but it is the honest statement of what the mount
is, and it stops the two 300 K walls at opposite ends of the page (`vess` below, `mt` above)
reading as one continuous boundary. Re-checked immediately:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

`describe` confirms the wall turned and the label followed it to the other side:

```
  node 'mt'              node            (1580, 150)       below         140x33   Room-temperature mount | T_mt = 300 K
  wall of node 'mt'      ground          (1580, 138) a270  (no label)
```

Then rendered, once clean:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw render examples/gallery/13-cryostat/magnet.json -o examples/gallery/13-cryostat/magnet.svg
examples\gallery\13-cryostat\magnet.svg (92,634 bytes)
EXIT=0
```

## After round 2 — a probe, on a scratch file, never on `magnet.json`

To find out whether the drawing's one compromise (two separate 300 K boundaries that are
physically one room) was forced or merely chosen, a throwaway copy `_probe.json` was built
with `mt` deleted and the strut re-pointed at `vess`. It was checked, then deleted; it is not
part of the commit and `magnet.json` was never touched.

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/_probe.json
error: DiagramError: the nodes form a loop through node 'vess'; the solver places a chain, so give node 'vess' `at` yourself. This is a bug in thermodraw; the diagram was accepted and then could not be drawn
EXIT=2
```

The remedy was applied literally — `"at": [200, 150]` on node `vess`, nothing else changed:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/_probe.json
error: DiagramError: the nodes form a loop through node 'vess'; the solver places a chain, so give node 'vess' `at` yourself. This is a bug in thermodraw; the diagram was accepted and then could not be drawn
EXIT=2
```

**Identical message. The remedy this refusal names does not clear it.** Placing *every* node
by hand is what actually gets past it:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check examples/gallery/13-cryostat/_probe.json
examples/gallery/13-cryostat/_probe.json: 11 labels placed, 1 error, 4 warnings, 0 notes
error: [symbols-overlap] branch 1 sh->he and branch 3 w->vess overlap by 26  -> move one of them with `at`
warning: [label-adrift] node 'sh': its label was pushed 84 past its own clearance to get around branch 1 sh->he and now sits nearer that than the thing it names  -> move branch 1 sh->he along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [wire-through-symbol] branch 3 w->vess runs straight through branch 0 vess->sh  -> give branch 3 w->vess a `via` waypoint so it does not run past it, or move the symbol along its branch with `at`
warning: [wire-through-symbol] branch 3 w->vess runs straight through branch 1 sh->he  -> give branch 3 w->vess a `via` waypoint so it does not run past it, or move the symbol along its branch with `at`
warning: [wire-through-symbol] branch 3 w->vess runs straight through branch 2 he->w  -> give branch 3 w->vess a `via` waypoint so it does not run past it, or move the symbol along its branch with `at`
EXIT=1
```

So the merged-boundary drawing is reachable, but only with an `at` on every node and a `via`
on the strut to route it clear — both forbidden by this brief. The compromise in `magnet.json`
was forced, and `findings.md` says so rather than hiding it. The probe was then removed:

```
$ rm -f examples/gallery/13-cryostat/_probe.json && ls examples/gallery/13-cryostat/
brief.md
magnet.json
magnet.svg
rounds.md
```

## Summary

- Check rounds: **2** — one with a finding, one clean.
- Findings in total: **1** warning, `label-adrift`. Its remedy worked when applied literally.
- The library never refused the file. No node was ever given `at`, and no `via` and no
  branch or source `at` was ever written.
- Final status: 0 errors, 0 warnings, 0 notes, exit 0.

## Final `check --physics`

Run on the final `magnet.json`, pasted exactly as it came:

```
$ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/13-cryostat/magnet.json
examples/gallery/13-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit status 0. Silent: no `node-does-not-balance`, no `rate-does-not-match`, and — worth
noting separately — no `physics-not-checked` note either, so both free nodes (`sh` and `w`)
were actually checked rather than skipped. The `rate` of 5.2 W stated on the G-10 straps was
checked against its ends and agreed.
