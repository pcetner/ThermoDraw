Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

# Rounds — 03-cryogenic

One section per `check` run, written as it happened.

---

## Round 1 — first draft

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 1 error, 4 warnings, 2 notes
error: [symbols-overlap] source 0 -> shield and source 1 shield -> overlap by 1  -> move one of them with `at`
warning: [label-adrift] node 'cold': its label was pushed 156 past its own clearance to get around branch 3 shield->cold and now sits nearer that than the thing it names  -> move branch 3 shield->cold along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] source 0 -> shield: its label was pushed 132 past its own clearance to get around branch 1 vessel->shield and now sits nearer that than the thing it names  -> move branch 1 vessel->shield along its branch with `at`, or move source 0 -> shield further from its node with `at` to take its label with it
warning: [label-adrift] source 1 shield ->: its label was pushed 136 past its own clearance to get around branch 4 shield->cold and now sits nearer that than the thing it names  -> move branch 4 shield->cold along its branch with `at`, or move source 1 shield -> further from its node with `at` to take its label with it
warning: [label-in-a-corridor] branch 4 shield->cold: its label sits inside a loop of the network, 48 from the opposite path and 50 tall, so it reads as belonging to either  -> set `side` to send it outside the loop
note: [parallel-pair-same-side] branch 0 vessel->shield and branch 1 vessel->shield run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
note: [parallel-pair-same-side] branch 3 shield->cold and branch 4 shield->cold run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=1
```

13 labels placed = 3 nodes + 7 branches + 3 sources, so nothing was dropped.

`describe` for the same file (run to see where things actually landed before
touching anything):

```
examples/gallery/03-cryogenic/dewar.json: canvas 1147 x 801, 13 labels

placements: ground x1, node x3, symbol/cap x1, symbol/cond x4,
            symbol/diss x1, symbol/flow x2, symbol/rad x2, wire x16

rail: y 780, span (200, 1200), reference 'vessel'

network:
  vessel --rad/cond/cond-- shield
  shield --rad/cond/cond-- cold
  cold --cap-- rail

nodes:
  vessel         fixed    at (200, 340)
  shield         free     at (620, 340)
  cold           free     at (1040, 340)

elements:
  branch 0 vessel->shiel symbol/rad      (450, 100)        above         109x50   MLI, vessel to shield | R_rad = 289 K/W | q = 0.9 W
  branch 1 vessel->shiel symbol/cond     (410, 340)        above         144x50   G10 struts, vessel to shield | R_cond = 433 K/W | q = 0.6 W
  branch 2 vessel->shiel symbol/cond     (450, 580)        below         107x33   HTS current leads | R_cond = 1720 K/W
  branch 3 shield->cold  symbol/rad      (870, 100)        above         128x50   MLI, shield to cold mass | R_rad = 1790 K/W | q = 0.02 W
  branch 4 shield->cold  symbol/cond     (830, 340)        above         164x50   G10 struts, shield to cold mass | R_cond = 716 K/W | q = 0.05 W
  branch 5 shield->cold  symbol/cond     (870, 580)        below         124x50   Instrumentation wiring | R_cond = 239 K/W | q = 0.15 W
  branch 6 cold->rail    symbol/cap      (1140, 560) a90   right          86x33   Cold mass | C_cm = 900 J/K
  source 0 -> shield     symbol/diss     (593, 367) a315   above left    123x33   pushed 132   HTS lead Joule heating | P_lead = 1.2 W
  source 1 shield ->     symbol/flow     (645, 365) a45    above right    99x33   pushed 136   Cryocooler stage 1 | q_s1 = 35 W
  source 2 cold ->       symbol/flow     (1065, 315) a315  above left     99x33   pushed 4   Cryocooler stage 2 | q_s2 = 1.5 W
  node 'vessel'          node            (200, 340)        above          80x33   Vacuum vessel | T_vac = 300 K
  node 'shield'          node            (620, 340) a135   above left     86x33   pushed 8   Radiation shield | T_sh = 40 K
  node 'cold'            node            (1040, 340) a135   above left    106x33   pushed 156   Cold mass (magnet) | T_cm = 4.2 K
```

The useful fact from `describe`: a source with no `at` is placed **38 units**
from its node (shield is at 620,340; source 0 landed at 593,367). The schema
says leaving `at` out places the source "along its own `angle` with room for
its label", and that this "is usually what you want". It is not — 38 units is
not room for a 123-wide label, two sources on adjacent diagonals of the same
node overlap by 1, and both labels get shoved 130+.

### Remedies applied, literally, for round 2

| finding | remedy as printed | what I changed |
|---|---|---|
| `symbols-overlap` src 0 / src 1 | "move one of them with `at`" | gave source 1 `at: [740, 440]` |
| `label-adrift` node 'cold' | "move branch 3 … with `at`, or `angle`" | branch 3 `at` [870,100] → [820,100] |
| `label-adrift` source 0 | "move source 0 further from its node with `at`" | gave source 0 `at: [480, 440]` |
| `label-adrift` source 1 | "move source 1 further from its node with `at`" | same change as the overlap fix |
| `label-in-a-corridor` branch 4 | "set `side` to send it outside the loop" | branch 4 `side` "up" → "down" |
| `parallel-pair-same-side` x2 | "set `side` to \"down\" on the lower of the two" | branch 1 `side` → "down"; branch 4 already covered |

---

## Round 2 — the named remedies, applied literally

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 1 error, 4 warnings, 2 notes
error: [label-collision] source 0 -> shield: its label is printed over the wire of branch 0 vessel->shield  -> move a `via` waypoint on branch 0 vessel->shield so it does not run past this label, or set `side` to "down" or "left"
warning: [label-adrift] node 'cold': its label was pushed 120 past its own clearance to get around branch 4 shield->cold and now sits nearer that than the thing it names  -> move branch 4 shield->cold along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] source 0 -> shield: its label was pushed 160 past its own clearance to get around the wire of branch 0 vessel->shield and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 vessel->shield so it does not run past this label, or set `side` to "down" or "left"
warning: [label-adrift] source 1 shield ->: its label was pushed 156 past its own clearance to get around branch 4 shield->cold and now sits nearer that than the thing it names  -> move branch 4 shield->cold along its branch with `at`, or set `side` to "right"
warning: [label-adrift] source 2 cold ->: its label was pushed 28 past its own clearance to get around the wire of branch 3 shield->cold and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 3 shield->cold so it does not run past this label, or set `side` to "right"
note: [parallel-pair-same-side] branch 1 vessel->shield and branch 2 vessel->shield run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
note: [parallel-pair-same-side] branch 4 shield->cold and branch 5 shield->cold run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=1
```

### Did each named remedy clear its finding?

| round-1 finding | remedy applied literally | cleared? |
|---|---|---|
| `symbols-overlap` src0/src1 | "move one of them with `at`" | **yes** — gone |
| `label-in-a-corridor` branch 4 | "set `side` to send it outside the loop" | **yes** — gone |
| `label-adrift` node 'cold' | "move branch 3 … along its branch with `at`" | **no** — push 156 → 120, and the blame moved from branch 3 to branch 4. Moving a *label box* along a branch cannot help, because what is crowding the node is the branch's **wire**, which arrives vertically on top of the node, and `at` does not move a wire |
| `label-adrift` source 0 | "move source 0 further from its node with `at`" | **no, worse** — push 132 → 160, and it escalated to a `label-collision` **error**. Moving a source away from its node moves it into the next piece of traffic; the remedy has no way of knowing what is out there |
| `label-adrift` source 1 | "move source 1 further from its node with `at`" | **no, worse** — 136 → 156 |
| `parallel-pair-same-side` x2 | "set `side` to \"down\" on the lower of the two" | **no — and it cannot be** — the note just moved from the pair (0,1) to the pair (1,2). `side` has two useful values for a horizontal branch and there are **three** parallel branches between each pair of nodes, so by pigeonhole two of them always share a side. This remedy is circular for any group larger than two |

One new warning appeared as a side effect (`label-adrift` on source 2), from
nothing I touched — it is the same vertical-arrival problem as node 'cold'.

**Read of the situation.** Three of the four surviving findings share one root
cause the remedies do not name: I routed each off-line branch so that its last
waypoint sits directly above/below the destination node, which is what the
hero does with its parallel pair. With *two* parallel branches that is fine
(the hero's `amb` turns its label out with `angle: 90`). With *three* per pair
plus two sources on the middle node, the node has four wires on the four
cardinals and nothing left for a label. The remedies keep telling me to shuffle
labels; the fix is to stop the wires arriving vertically.

### Round 3 plan (a restructure, after the literal remedies were tried)

Route every off-line branch back to the main line *before* it reaches its node,
so all three branches of a group share one horizontal stub into the node — the
hero's own "leave a node sideways before turning", applied at the arrival end
too. That frees the space directly above and below every node.

- nodes spread to `x` 200 / 760 / 1320 (560 apart) so the loops are wide enough
  that the middle branch's label clears the risers. Round 1's
  `label-in-a-corridor` reported "48 from the opposite path" for a 164-wide box
  at `x=830` with a riser at `x=700` — 748 − 700 = 48. So the corridor metric is
  the **horizontal** gap from the label box to the riser, not the vertical gap
  to the far lane. That is worth knowing and is not in the docs.
- the branch with the **narrowest** label goes on the middle (straight) lane of
  each group, because that is the only one whose label must live inside a loop.
  Left group: HTS leads (107 wide, and 33 tall since it has no `rate` line).
  Right group: instrumentation wiring (124).
- shield's two sources go in the pocket between the two groups' risers, one
  above-left and one straight below.

---

## Round 3 — restructured: all wires arrive along the main line

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 0 warnings, 2 notes
note: [parallel-pair-same-side] branch 0 vessel->shield and branch 1 vessel->shield run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
note: [parallel-pair-same-side] branch 3 shield->cold and branch 4 shield->cold run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

Clean on errors and warnings, exit 0. Everything from rounds 1 and 2 cleared at
once, which says the four surviving findings really were one geometric mistake
wearing four hats, and that none of the four remedies named it.

`describe` on the clean file:

```
examples/gallery/03-cryogenic/dewar.json: canvas 1397 x 801, 13 labels

placements: ground x1, node x3, symbol/cap x1, symbol/cond x4,
            symbol/diss x1, symbol/flow x2, symbol/rad x2, wire x19

rail: y 780, span (200, 1320), reference 'vessel'

network:
  vessel --rad/cond/cond-- shield
  shield --rad/cond/cond-- cold
  cold --cap-- rail

nodes:
  vessel         fixed    at (200, 340)
  shield         free     at (760, 340)
  cold           free     at (1320, 340)

elements:
  branch 0 vessel->shiel symbol/rad      (435, 100)        above         109x50   MLI, vessel to shield | R_rad = 289 K/W | q = 0.9 W
  branch 1 vessel->shiel symbol/cond     (435, 340)        above         107x33   HTS current leads | R_cond = 1720 K/W
  branch 2 vessel->shiel symbol/cond     (435, 580)        below         144x50   G10 struts, vessel to shield | R_cond = 433 K/W | q = 0.6 W
  branch 3 shield->cold  symbol/rad      (1085, 100)       above         128x50   MLI, shield to cold mass | R_rad = 1790 K/W | q = 0.02 W
  branch 4 shield->cold  symbol/cond     (1085, 340)       above         124x50   Instrumentation wiring | R_cond = 239 K/W | q = 0.15 W
  branch 5 shield->cold  symbol/cond     (1085, 580)       below         164x50   G10 struts, shield to cold mass | R_cond = 716 K/W | q = 0.05 W
  branch 6 cold->rail    symbol/cap      (1320, 560) a90   right          86x33   Cold mass | C_cm = 900 J/K
  source 0 -> shield     symbol/diss     (660, 190) a55    above right   123x33   HTS lead Joule heating | P_lead = 1.2 W
  source 1 shield ->     symbol/flow     (760, 500) a90    right          99x33   Cryocooler stage 1 | q_s1 = 35 W
  source 2 cold ->       symbol/flow     (1460, 340)       above          99x33   Cryocooler stage 2 | q_s2 = 1.5 W
  node 'vessel'          node            (200, 340)        above          80x33   Vacuum vessel | T_vac = 300 K
  node 'shield'          node            (760, 340) a45    above right    86x33   pushed 8   Radiation shield | T_sh = 40 K
  node 'cold'            node            (1320, 340)       above         106x33   Cold mass (magnet) | T_cm = 4.2 K
```

Nothing is `pushed` except shield's label by 8, which is the solver doing its
job rather than losing an argument.

### Round 3b — one more attempt at the two standing notes

The note's own remedy ("set `side` to \"down\" on the lower of the two") cannot
work for a group of three; it only rotates which pair is reported. The one
untried escape is that `side` has four values, not two, so I set the middle
branch of each group to `"right"`:

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 2 errors, 4 warnings, 0 notes
error: [label-collision] branch 1 vessel->shield: its label is printed over node 'shield'  -> move node 'shield' with `at`, or set `side` to "up" or "down"
error: [label-collision] branch 4 shield->cold: its label is printed over source 2 cold ->  -> move source 2 cold -> further from its node with `at`, or set `side` to "up" or "down"
warning: [label-adrift] branch 1 vessel->shield: its label was pushed 160 past its own clearance to get around node 'shield' and now sits nearer that than the thing it names  -> move node 'shield' with `at`, or set `side` to "up" or "down"
warning: [label-adrift] branch 4 shield->cold: its label was pushed 160 past its own clearance to get around node 'cold' and now sits nearer that than the thing it names  -> move node 'cold' with `at`, or set `side` to "up" or "down"
warning: [label-adrift] node 'cold': its label was pushed 16 past its own clearance to get around the wire of branch 3 shield->cold  -> move a `via` waypoint on branch 3 shield->cold so it does not run past this label, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] source 2 cold ->: its label was pushed 12 past its own clearance to get around node 'cold'  -> move node 'cold' with `at`, or set `side` to "right"
```

It clears both notes and costs two errors and four warnings: `"right"` on a
horizontal branch pushes the label *along the wire* into the next node, and
`check` itself immediately tells me to set `side` back to "up" or "down".
Reverted.

**Two notes left standing, deliberately.** Reason: a note is advice and exits 0,
and with three parallel branches between one pair of nodes the only two usable
`side` values for a horizontal run are "up" and "down", so two of the three must
share one. The middle branch is the one on the shared side, and its label is the
narrowest of its group (107 and 124 wide) precisely so it survives sitting inside
a loop. The schema anticipates leaving this one: "`parallel-pair-same-side` is a
note rather than a warning because the hero diagram breaks it and is fine."

Final state: **0 errors, 0 warnings, 2 notes, exit 0, in 3 rounds.**

---

## Render

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/03-cryogenic/dewar.json -o examples/gallery/03-cryogenic/dewar.svg
examples\gallery\03-cryogenic\dewar.svg (19,491 bytes)
EXIT=0
```

The CLI's `render` already emits a `:root{--sym:…}` block, i.e. it applies the
theme step the schema tells you to do by hand in Python. Not documented; I
would have gone looking for a `--theme` flag if I had not looked at the file.

---

## `check --physics` — record only, run once, not iterated on

```
$ PYTHONPATH=src python -m thermodraw check --physics examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 2 warnings, 2 notes
warning: [node-does-not-balance] node 'cold': 0.22 W arrives and 1.5 W leaves at the stated values � 1.5 W out by source 2; 0.02 W in by branch 3 shield->cold (35.8 K over 1.79e+03 K/W); 0.15 W in by branch 4 shield->cold (35.8 K over 239 K/W); 0.05 W in by branch 5 shield->cold (35.8 K over 716 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [node-does-not-balance] node 'shield': 2.85 W arrives and 35.2 W leaves at the stated values � 1.2 W in by source 0; 35 W out by source 1; 0.9 W in by branch 0 vessel->shield (260 K over 289 K/W); 0.151 W in by branch 1 vessel->shield (260 K over 1.72e+03 K/W); 0.6 W in by branch 2 vessel->shield (260 K over 433 K/W); 0.02 W out by branch 3 shield->cold (35.8 K over 1.79e+03 K/W); 0.15 W out by branch 4 shield->cold (35.8 K over 239 K/W); 0.05 W out by branch 5 shield->cold (35.8 K over 716 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
note: [parallel-pair-same-side] branch 0 vessel->shield and branch 1 vessel->shield run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
note: [parallel-pair-same-side] branch 3 shield->cold and branch 4 shield->cold run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=1
```

(The `�` is a Windows console encoding artefact. Re-running with
`PYTHONIOENCODING=utf-8` shows the character is an em dash `—`. `check` writes
non-ASCII to stdout without forcing an encoding, so on a cp1252 console the
report is corrupted; on a `--json` run that would be a data bug, not just a
cosmetic one.)

**I did not change the diagram in response to this.** Both warnings are real
and both are properties of the brief, not of my drawing: the brief's 35 W and
1.5 W are cryocooler *capacities* at those stage temperatures, while the actual
load reaching the shield is 2.85 W and the load reaching the cold mass is
0.22 W. The physics pass reads them as loads, correctly notices the mismatch,
and its own suggested remedy — "if a flow is a capacity rather than a load, say
so in the `label`" — is a wording change that would not alter the arithmetic or
clear the warning. Discussed in `findings.md`.

The arithmetic it prints is otherwise exactly right, including the 0.151 W it
infers for the HTS leads, a number the brief never states.
