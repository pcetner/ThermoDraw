Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

# Rounds — 01-spacecraft

One section per `check` run, written as I went. Each finding records whether
the remedy the finding itself named cleared it when applied literally.

---

## Round 1 — first draft

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 3 warnings, 0 notes
warning: [label-adrift] source 1 -> panel: its label was pushed 124 past its own clearance to get around branch 0 twta->panel and now sits nearer that than the thing it names  -> move branch 0 twta->panel along its branch with `at`, or set `side` to "left"
warning: [label-adrift] source 2 -> panel: its label was pushed 124 past its own clearance to get around branch 3 panel->space and now sits nearer that than the thing it names  -> move branch 3 panel->space along its branch with `at`, or move source 2 -> panel further from its node with `at` to take its label with it
warning: [label-in-a-corridor] branch 1 panel->radiator: its label sits inside a loop of the network, 47 from the opposite path and 50 tall, so it reads as belonging to either  -> set `side` to send it outside the loop
EXIT=1
```

13 labels placed = 4 nodes + 5 branches + 4 sources, so nothing was dropped.

I also ran `describe` at this point to see *where* things had actually landed,
because the warnings talk about objects whose positions I never gave:

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: canvas 1234 x 444, 13 labels

placements: ground x1, node x4, symbol/cap x1, symbol/contact x1,
            symbol/diss x2, symbol/pipe x1, symbol/rad x2, symbol/radin x2,
            wire x14

rail: y 400, span (220, 1180), reference 'space'

network:
  twta --contact-- panel
  panel --pipe-- radiator
  radiator --rad-- space
  panel --rad-- space
  panel --cap-- rail

nodes:
  twta           free     at (220, 180)
  panel          free     at (540, 180)
  radiator       free     at (860, 180)
  space          fixed    at (1180, 180)

elements:
  branch 0 twta->panel   symbol/contact  (360, 180)        above         113x33   Filled silicone gasket | R_contact = 0.05 K/W
  branch 1 panel->radiat symbol/pipe     (730, 180)        above         124x50   Embedded heat pipes | R_pipe = 0.00182 K/W | q = 220 W
  branch 2 radiator->spa symbol/rad      (1020, 180)       above         160x33   Second-surface mirror, ε 0.80 | R_rad = 1.15 K/W
  branch 3 panel->space  symbol/rad      (900, 60)         above         109x33   MLI blanket, ε* 0.02 | R_rad = 26 K/W
  branch 4 panel->rail   symbol/cap      (540, 290) a90    right         102x33   Panel honeycomb | C_pnl = 18000 J/K
  source 0 -> twta       symbol/diss     (182, 180)        above          94x33   TWTA waste heat | P_twta = 220 W
  source 1 -> panel      symbol/radin    (511, 209) a315   above left     68x33   pushed 124   Earth IR | q_eir = 12 W
  source 2 -> panel      symbol/diss     (567, 207) a225   above right   167x33   pushed 124   Survival heater (30 W when on) | P_htr = 0 W
  source 3 -> radiator   symbol/radin    (860, 222) a270   right          81x33   Absorbed solar | q_sol = 45 W
  node 'twta'            node            (220, 180)        below          88x33   flipped   TWTA baseplate | T_twta = 78 °C
  node 'panel'           node            (540, 180) a135   above left     91x33   pushed 8   Equipment panel | T_pnl = 45 °C
  node 'radiator'        node            (860, 180)        above          74x33   Radiator | T_rad = 22 °C
  node 'space'           node            (1180, 180) a90   right          97x33   Deep space | T_space = -269 °C
```

The network block is exactly the one I meant — five branches, the right pairs,
`panel --rad-- space` and `radiator --rad-- space` as two separate edges rather
than being silently merged. That is the confirmation `check` cannot give.

What `describe` told me that the warnings did not: auto-placed sources land
about 40 units from their node (source 1 at (511, 209) for a node at
(540, 180)), which is far too close for a node that already has four wires and
a label on it. That is the root of both `label-adrift` warnings.

**Remedies applied for round 2** — the first one each finding names, literally:

1. finding 1, first remedy "move branch 0 twta->panel along its branch with
   `at`": `at` [360, 180] → [300, 180].
2. finding 2, first remedy "move branch 3 panel->space along its branch with
   `at`": `at` [900, 60] → [1000, 60].
3. finding 3, "set `side` to send it outside the loop": branch 1 `side`
   "up" → "down". The loop is panel–radiator–space–MLI and the pipe is its
   lower edge, so outside is down.

---

## Round 2 — the first-named remedies, applied literally

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 4 warnings, 0 notes
warning: [label-adrift] node 'panel': its label was pushed 56 past its own clearance to get around the wire of branch 0 twta->panel and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 twta->panel so it does not run past this label, or set `side` to "up"
warning: [label-adrift] node 'twta': its label was pushed 44 past its own clearance to get around branch 0 twta->panel and now sits nearer that than the thing it names  -> move branch 0 twta->panel along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] source 1 -> panel: its label was pushed 44 past its own clearance to get around the wire of branch 0 twta->panel and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 twta->panel so it does not run past this label, or set `side` to "left"
warning: [label-adrift] source 2 -> panel: its label was pushed 44 past its own clearance to get around branch 1 panel->radiator and now sits nearer that than the thing it names  -> move branch 1 panel->radiator along its branch with `at`, or move source 2 -> panel further from its node with `at` to take its label with it
EXIT=1
```

Did each round-1 remedy clear its finding?

| round-1 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-adrift` source 1 (around branch 0) | moved branch 0 `at` 360 → 300 | **no** — still adrift, and the finding now blames branch 0's *wire* rather than its symbol |
| `label-adrift` source 2 (around branch 3) | moved branch 3 `at` 900 → 1000 | **no** — the finding survived and re-aimed itself at branch 1 instead |
| `label-in-a-corridor` branch 1 | set `side` "up" → "down" | **yes**, gone |

Net: 3 warnings → 4 warnings. Moving branch 0's label *toward* the TWTA to
get it away from the panel simply crowded the TWTA instead, and produced a
second `label-adrift` on node `twta` that had not existed before. Sending the
pipe label down out of the loop worked, but it landed on top of the heater
source, which is where the fourth warning comes from.

The important observation: **two of these findings name a remedy that cannot
be carried out.** "move a `via` waypoint on branch 0 twta->panel so it does
not run past this label" — branch 0 has no `via`. It is a straight run between
two adjacent nodes. There is no waypoint to move. The finding text is
generated from the obstruction being a wire rather than a symbol, without
checking whether the obstructing branch actually has waypoints.

**Remedies applied for round 3** — the second option each finding names, since
the first either failed or is impossible:

1. node `panel`: first option impossible (no `via` on branch 0); second option
   `side` "up" → replaced `"angle": 135` with `"side": "up"`.
2. node `twta`: "move branch 0 along its branch with `at`" → 300 back out to
   380, i.e. away from the TWTA this time.
3. source 1: first option impossible (same non-existent `via`); second option
   `side` "left".
4. source 2: "move source 2 further from its node with `at`" → explicit
   `at` [700, 320], well clear of the panel.

---

## Round 3 — the second-named remedies

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] source 1 -> panel: its label was pushed 136 past its own clearance to get around branch 0 twta->panel and now sits nearer that than the thing it names  -> move branch 0 twta->panel along its branch with `at`, or move source 1 -> panel further from its node with `at` to take its label with it
EXIT=1
```

Did each round-2 remedy clear its finding?

| round-2 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-adrift` node `panel` | `side` "up" (replacing `angle` 135) | **yes** |
| `label-adrift` node `twta` | branch 0 `at` 300 → 380 | **yes** |
| `label-adrift` source 1 | `side` "left" | **no** — same finding survives, now with a bigger push (44 → 136) and a *different* second remedy offered |
| `label-adrift` source 2 | explicit `at` [700, 320], far from the node | **yes** |

4 warnings → 1. The one remedy that reliably works is the one that moves a
source's own symbol away from its node with an explicit `at`; it cleared
source 2 outright. `side` on a source did not help source 1 at all — the push
got *worse*, from 44 to 136, because "left" aims the label straight into the
run of branch 0 that the source was already trying to get around.

**Remedy applied for round 4:** the finding's second option, "move source 1
-> panel further from its node with `at`" — `at` [380, 320], mirroring what
worked for source 2. Its first option (move branch 0 with `at`) is the one
that already failed for this same finding in round 2, so I am not repeating
it.

---

## Round 4 — moving source 1 out with `at`

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 1 error, 2 warnings, 0 notes
error: [label-collision] source 2 -> panel: its label is printed over branch 2 radiator->space  -> move branch 2 radiator->space along its branch with `at`, or set `side` to "down"
warning: [label-adrift] branch 4 panel->rail: its label was pushed 120 past its own clearance to get around source 2 -> panel and now sits nearer that than the thing it names  -> move source 2 -> panel further from its node with `at`, or move branch 4 panel->rail along its branch with `at` to take its label with it
warning: [label-adrift] source 2 -> panel: its label was pushed 160 past its own clearance to get around branch 2 radiator->space and now sits nearer that than the thing it names  -> move branch 2 radiator->space along its branch with `at`, or set `side` to "down"
EXIT=1
```

| round-3 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-adrift` source 1 | explicit `at` [380, 320] | **yes** |

But the count went 1 warning → 1 error + 2 warnings. `describe` explains why:

```
  branch 4 panel->rail   symbol/cap      (540, 290) a90    right         102x33   pushed 120   Panel honeycomb | C_pnl = 18000 J/K
  source 1 -> panel      symbol/radin    (380, 320) a315   left           68x33   Earth IR | q_eir = 12 W
  source 2 -> panel      symbol/diss     (700, 320) a225   above right   167x33   pushed 160   OVERLAPS   Survival heater (30 W when on) | P_htr = 0 W
```

Source 2's symbol is at (700, 320) and its label is the widest in the diagram
at 167 units. It went "above right" and was then pushed a further 160 in that
direction, which carried it all the way up into branch 2's label near
(1020, 180) at the far right of the drawing. Nothing near source 2 changed in
round 3 — source 1 moving out of the way simply freed the solver to push
source 2 further, and it pushed it into something worse. **`label-adrift`
pushes are not local: clearing one can make another one travel hundreds of
units.**

**Remedies applied for round 5** — first-named for each:

1. error, "move branch 2 radiator->space along its branch with `at`": `at`
   [1020, 180] → [1090, 180].
2. warning on branch 4, "move source 2 -> panel further from its node with
   `at`": `at` [700, 320] → [720, 350].

---

## Round 5

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 3 warnings, 0 notes
warning: [label-adrift] branch 4 panel->rail: its label was pushed 100 past its own clearance to get around the wire of source 2 -> panel and now sits nearer that than the thing it names  -> move source 2 -> panel with `at`, or move branch 4 panel->rail along its branch with `at` to take its label with it
warning: [label-adrift] source 2 -> panel: its label was pushed 44 past its own clearance to get around source 3 -> radiator and now sits nearer that than the thing it names  -> move source 3 -> radiator further from its node with `at`, or set `side` to "right"
warning: [label-in-a-corridor] branch 2 radiator->space: its label sits inside a loop of the network, 10 from the opposite path and 33 tall, so it reads as belonging to either  -> set `side` to send it outside the loop
EXIT=1
```

| round-4 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-collision` source 2 over branch 2 | branch 2 `at` 1020 → 1090 | **yes** as an error — but it converted straight into a new `label-in-a-corridor` on branch 2, because 1090 puts that label 10 units from the MLI wire descending at x = 1180 |
| `label-adrift` branch 4 | source 2 `at` [700,320] → [720,350] | **no** — still adrift, push 120 → 100 |
| `label-adrift` source 2 | (shared remedy with the error) | **partly** — it stopped colliding, still adrift, push 160 → 44 |

**Remedies applied for round 6** — first-named for each:

1. branch 4: "move source 2 -> panel with `at`" → [720, 350] → [660, 350].
2. source 2: "move source 3 -> radiator further from its node with `at`" →
   source 3 gets an explicit `at` [860, 300] instead of its auto placement at
   (860, 222).
3. branch 2: "set `side` to send it outside the loop" → `side` "up" → "down".

---

## Round 6

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 1 error, 2 warnings, 0 notes
error: [label-collision] source 2 -> panel: its label is printed over the wire of source 3 -> radiator  -> move source 3 -> radiator with `at`, or set `side` to "right"
warning: [label-adrift] branch 4 panel->rail: its label was pushed 48 past its own clearance to get around the wire of source 2 -> panel and now sits nearer that than the thing it names  -> move source 2 -> panel with `at`, or move branch 4 panel->rail along its branch with `at` to take its label with it
warning: [label-adrift] source 2 -> panel: its label was pushed 160 past its own clearance to get around the wire of source 3 -> radiator and now sits nearer that than the thing it names  -> move source 3 -> radiator with `at`, or set `side` to "right"
EXIT=1
```

| round-5 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-adrift` branch 4 | source 2 `at` [720,350] → [660,350] | **no** — push 100 → 48, still adrift |
| `label-adrift` source 2 | source 3 given explicit `at` [860, 300] | **no, backfired** — push 44 → 160, and it became a hard `label-collision`. Pulling source 3 down to y = 300 lengthened its lead from (860,300) up to the radiator at (860,180), and that longer wire is now what source 2's label collides with |
| `label-in-a-corridor` branch 2 | `side` "up" → "down" | **yes** |

**Remedy applied for round 7:** the one named option I have not yet tried on
source 2 — `side` "right". (Its first-named option, "move source 3 -> radiator
with `at`", is what I just did and it made things worse.)

---

## Round 7

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 1 warning, 0 notes
warning: [label-adrift] branch 4 panel->rail: its label was pushed 48 past its own clearance to get around the wire of source 2 -> panel and now sits nearer that than the thing it names  -> move source 2 -> panel with `at`, or move branch 4 panel->rail along its branch with `at` to take its label with it
EXIT=1
```

| round-6 finding | remedy applied literally | cleared? |
|---|---|---|
| `label-collision` source 2 over source 3's wire | source 2 `side` "right" | **yes** |
| `label-adrift` source 2 | same | **yes** |
| `label-adrift` branch 4 | (not re-attempted this round) | still standing |

One left, and it is the same one that has survived since round 4: the panel's
capacitance label sitting in the path of the heater source's diagonal lead.
Both of its named remedies are "nudge one of the two along a bit", and I have
now nudged source 2 three times ([700,320] → [720,350] → [660,350]) with the
push going 120 → 100 → 48 but never to zero. Nudging is converging far too
slowly to be the intended fix.

**Round 8 takes the structural option instead**, which the schema names at
line 275 for exactly this situation: "waypoints work on a capacitance exactly
as they do on any other branch, which is how you free up the space directly
under a node that already has too much attached to it." So branch 4 gets
`"via": [[440, 180]]` — it leaves the panel westward for 100 units and then
drops to the rail from there, taking its label out of the heater's lead
entirely. This is in the spirit of "move branch 4 to take its label with it"
but it is `via`, not `at`, and the finding did not suggest it.

---

## Round 8 — capacitance moved off the panel's underside with `via`

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 1 warning, 0 notes
warning: [wire-through-symbol] source 1 -> panel runs straight through branch 4 panel->rail  -> route it around with `via`, or move the symbol along its branch with `at`
EXIT=1
```

| round-7 finding | remedy applied | cleared? |
|---|---|---|
| `label-adrift` branch 4 | `via` [[440, 180]] on branch 4 (structural, not the named nudge) | **yes** |

A new one, and a genuinely useful one: the Earth-IR source's lead from
(380, 320) up to the panel now passes straight through the capacitance symbol
I just moved to x = 440. Note again that the first remedy named — "route it
around with `via`" — **cannot be applied to a source**: `via` is a branch
field, and the schema's source table (lines 228-258) has no `via`. Only the
second option is available.

**Remedy applied for round 9:** "move the symbol along its branch with `at`" —
branch 4 `at` [440, 350], sliding the capacitance symbol down its own vertical
run to below where source 1's lead crosses x = 440.

---

## Round 9 — clean

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

| round-8 finding | remedy applied literally | cleared? |
|---|---|---|
| `wire-through-symbol` source 1 through branch 4 | branch 4 `at` [440, 350] ("move the symbol along its branch with `at`") | **yes** |

Nine rounds, exit 0, no notes standing. Final `describe`:

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: canvas 1234 x 444, 13 labels

placements: ground x1, node x4, symbol/cap x1, symbol/contact x1,
            symbol/diss x2, symbol/pipe x1, symbol/rad x2, symbol/radin x2,
            wire x15

rail: y 400, span (220, 1180), reference 'space'

network:
  twta --contact-- panel
  panel --pipe-- radiator
  radiator --rad-- space
  panel --rad-- space
  panel --cap-- rail

nodes:
  twta           free     at (220, 180)
  panel          free     at (540, 180)
  radiator       free     at (860, 180)
  space          fixed    at (1180, 180)

elements:
  branch 0 twta->panel   symbol/contact  (380, 180)        above         113x33   Filled silicone gasket | R_contact = 0.05 K/W
  branch 1 panel->radiat symbol/pipe     (730, 180)        below         124x50   Embedded heat pipes | R_pipe = 0.00182 K/W | q = 220 W
  branch 2 radiator->spa symbol/rad      (1090, 180)       below         160x33   pushed 4   Second-surface mirror, ε 0.80 | R_rad = 1.15 K/W
  branch 3 panel->space  symbol/rad      (1000, 60)        above         109x33   MLI blanket, ε* 0.02 | R_rad = 26 K/W
  branch 4 panel->rail   symbol/cap      (440, 350) a90    right         102x33   Panel honeycomb | C_pnl = 18000 J/K
  source 0 -> twta       symbol/diss     (182, 180)        above          94x33   TWTA waste heat | P_twta = 220 W
  source 1 -> panel      symbol/radin    (380, 320) a315   left           68x33   Earth IR | q_eir = 12 W
  source 2 -> panel      symbol/diss     (660, 350) a225   right         167x33   Survival heater (30 W when on) | P_htr = 0 W
  source 3 -> radiator   symbol/radin    (860, 300) a270   right          81x33   Absorbed solar | q_sol = 45 W
  node 'twta'            node            (220, 180)        below          88x33   flipped   TWTA baseplate | T_twta = 78 °C
  node 'panel'           node            (540, 180)        above          91x33   Equipment panel | T_pnl = 45 °C
  node 'radiator'        node            (860, 180)        above          74x33   Radiator | T_rad = 22 °C
  node 'space'           node            (1180, 180) a90   right          97x33   Deep space | T_space = -269 °C
```

The `network` block is the one I meant. The one thing I would have changed if
the drawing were free to change: `node 'twta'` is `flipped`, so the hottest
node in the diagram carries its label *below* the line while the other three
carry theirs above. `check` is happy with it and `describe` reports it plainly,
but nothing in the schema documents `flipped` or says how to prevent it, and
setting `"side": "up"` on that node would just re-create the collision with
source 0's label that caused the flip. Left as it is.

---

## Render

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/01-spacecraft/satellite.json -o examples/gallery/01-spacecraft/satellite.svg
examples\gallery\01-spacecraft\satellite.svg (17,793 bytes)
EXIT=0
```

(The CLI's `render` already writes the `:root` variable block into the file, so
the standalone SVG draws. `docs/schema.md` lines 12-15 warn that "`render`
alone emits CSS custom properties with no fallback... Without one of them the
file draws nothing" — that warning is about the Python `render()` function, not
the `render` subcommand, and the page does not say so.)

---

## `check --physics` — record only, not iterated on

Run once after the diagram was final and clean. Pasted verbatim, including the
`�` where the Windows console could not encode the separator character the
tool printed:

```
$ PYTHONPATH=src python -m thermodraw check --physics examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 4 warnings, 0 notes
warning: [node-does-not-balance] node 'panel': 672 W arrives and 1.26e+04 W leaves at the stated values � 12 W in by source 1; 0 W in by source 2; 660 W in by branch 0 twta->panel (33 K over 0.05 K/W); 1.26e+04 W out by branch 1 panel->radiator (23 K over 0.00182 K/W); 12.1 W out by branch 3 panel->space (314 K over 26 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [node-does-not-balance] node 'radiator': 1.27e+04 W arrives and 253 W leaves at the stated values � 45 W in by source 3; 1.26e+04 W in by branch 1 panel->radiator (23 K over 0.00182 K/W); 253 W out by branch 2 radiator->space (291 K over 1.15 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [node-does-not-balance] node 'twta': 220 W arrives and 660 W leaves at the stated values � 220 W in by source 0; 660 W out by branch 0 twta->panel (33 K over 0.05 K/W)  -> check the values. If one box stands for several identical paths, give it `count` and `arrangement`; if a temperature is a limit rather than a result, or a flow is a capacity rather than a load, say so in the `label`
warning: [rate-does-not-match] branch 1 panel->radiator says it carries 220 W, and its ends imply 1.26e+04 W (23 K over 0.00182 K/W)  -> one of `rate`, `value` or an end temperature is wrong
EXIT=1
```

Not acted on, by instruction, and I would not have acted on it anyway: every
one of these four warnings is a real inconsistency **in the brief**, not in the
drawing. See `findings.md` for the arithmetic. Briefly:

- `twta` — 220 W across 0.05 K/W is an 11 K drop, but the brief puts the TWTA
  baseplate 33 K above the panel. The brief's gasket resistance and its two
  temperatures cannot all be right.
- `panel` and `radiator` — the brief says the heat pipe drops "about 0.4 K",
  and also puts its two ends 23 K apart. The physics checker resolves that
  contradiction the only way it can, by dividing 23 K by the tiny resistance
  the 0.4 K figure implies, and gets 12.6 kW.
- `rate-does-not-match` — the same contradiction seen from the other side, and
  it is the most useful of the four: it is the checker noticing that the load
  I used to convert the brief's ΔT into a resistance (220 W) disagrees with the
  load the brief's own temperatures imply.

Both `node-does-not-balance` remedies suggest `count`/`arrangement` — the brief
does say "heat pipe**s**" — but adding a count would not fix this. A count of
*n* in parallel makes the implied flow *n* times worse, not better, and the
brief gives no pipe count. The other suggested remedy, "say so in the `label`",
is not a fix either; it asks me to annotate an inconsistency rather than
resolve it, and the checker would still fire.
