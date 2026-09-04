claude-opus-5 (Opus 5, 1M context) in Claude Code, running as a subagent; Windows 10, Git Bash, `PYTHONPATH=src PYTHONIOENCODING=utf-8`.

# 15-pv — rounds

Ten runs of `check` in total: seven on `array.json`, three on a scratch copy
`_probe.json` (since deleted) used to find out what the solver actually wanted.
Three of the seven were refusals (exit 2), not findings.

Before drawing anything I checked the brief's arithmetic by hand, because the
brief warns not to adjust a number to quieten `--physics`:

    sky   (65-10)/0.2  = 275 W   as stated
    conv  (65-35)/0.05 = 600 W   as stated
    back  900 - 275 - 600 = 25 W, and (65-55)/0.4 = 25 W
    clips four 1.6 K/W in parallel = 0.4 K/W, (55-45)/0.4 = 25 W

Every number in the brief closes. Nothing was adjusted.

---

## Round 1 — no `at` on any node, no `via`, as the brief instructs

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    error: DiagramError: node 'cell' joins 3 others ('amb', 'back', 'sky'); the solver places a chain, so give node 'cell' `at` yourself, and `via` on the branches that leave it sideways. This is a bug in thermodraw; the diagram was accepted and then could not be drawn
    EXIT=2

Refused, as expected: `cell` carries the sky path, the air path and the back
path, so the network is not a chain.

**Remedy named:** give node `cell` an `at`, and `via` to the branches that
leave it sideways.

---

## Round 2 — the first half of that remedy, applied literally

Added `"at": [300, 150]` to node `cell`. Nothing else.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    error: DiagramError: node 'cell' joins 3 others ('amb', 'back', 'sky'); the solver places a chain, so give node 'cell' `at` yourself, and `via` on the branches that leave it sideways. This is a bug in thermodraw; the diagram was accepted and then could not be drawn
    EXIT=2

**Did the remedy clear it? No.** Byte-identical message, still asking for the
`at` that is now there.

---

## Round 3 — the whole remedy, applied literally

`cell` still at `[300, 150]`; added `via` to the two branches that leave it
sideways — `[[380, 150], [380, 40]]` on `cell->sky`, `[[220, 150], [220, 40]]`
on `cell->amb`. These waypoints are guesses, necessarily: `via` is absolute and
the nodes they run to are still unplaced, so there is no number to write them
from.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    error: DiagramError: node 'cell' joins 3 others ('amb', 'back', 'sky'); the solver places a chain, so give node 'cell' `at` yourself, and `via` on the branches that leave it sideways. This is a bug in thermodraw; the diagram was accepted and then could not be drawn
    EXIT=2

**Did the remedy clear it? No.** The complete remedy, applied exactly as
written, leaves the message unchanged. At this point the brief's instructions
were exhausted, so I probed.

---

## Probes — what the solver actually wants

On a scratch copy `_probe.json`, since the brief's route was dead.

**Probe A — every node given `at`** (`sky [380,40]`, `amb [220,40]`,
`back [600,150]`, `roof [900,150]`, `cell [300,150]`):

    examples/gallery/15-pv/_probe.json: 10 labels placed, 2 errors, 4 warnings, 0 notes
    error: [symbols-overlap] branch 0 cell->sky and the boundary wall of node 'sky' overlap by 12  -> move one of them with `at`
    error: [symbols-overlap] branch 1 cell->amb and the boundary wall of node 'amb' overlap by 12  -> move one of them with `at`
    warning: [label-adrift] node 'cell': its label was pushed 68 past its own clearance to get around the boundary wall of node 'sky' and now sits nearer that than the thing it names  -> turn the wall of node 'sky' with `wall`, or move node 'sky' with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
    warning: [wire-through-symbol] branch 1 cell->amb runs straight through source 0 -> cell  -> move a `via` waypoint on branch 1 cell->amb so it does not run past it, or move source 0 -> cell with `at`
    warning: [wire-through-wall] branch 1 cell->amb runs through the boundary wall of node 'amb'  -> turn the wall of node 'amb' with `wall: "down"` so it faces away from branch 1 cell->amb, or move node 'amb' with `at`
    warning: [wire-through-wall] branch 0 cell->sky runs through the boundary wall of node 'sky'  -> turn the wall of node 'sky' with `wall: "down"` so it faces away from branch 0 cell->sky, or move node 'sky' with `at`
    EXIT=1

It draws. So the refusal is not about `cell` at all — it is about whether any
node is left for the solver.

Note the two `wire-through-wall` remedies: both say to set `wall: "down"`, and
both walls are already `down` — that is the default and neither node carried a
`wall` key. The branch arrives at each of these nodes **from below**, so `down`
is the direction that is in the way. The remedy names the value that caused the
finding. The fix is `wall: "up"`, which the schema's own prose gets right ("A
mount that a cold mass hangs from has its wall above") while the checker's
remedy contradicts it.

**Probe B — two nodes left unplaced** (`back` and `roof` back to no `at`):

    error: DiagramError: node 'cell' joins 3 others ('amb', 'back', 'sky'); ...
    EXIT=2

**Probe C — exactly one node left unplaced** (`roof` only):

    error: DiagramError: node 'cell' joins 3 others ('amb', 'back', 'sky'); ...
    EXIT=2

**Conclusion: it is all-or-nothing.** In a network that is not a chain, one
unplaced node anywhere sends the whole file to the chain solver, which refuses
on topology and names a node whose `at` cannot help. There is no partial
solving, and the refusal message's remedy is unreachable.

---

## Round 4 — every node placed, laid out deliberately

Discarded the probe. Real layout, chosen by hand: the ladder `cell -> back ->
roof` runs left to right along `y = 320`, and the two front-side losses leave
`cell` as straight diagonals to boundary nodes above — air up-left at
`[180,110]`, sky up-right at `[560,110]`, both with `"wall": "up"` so the wall
faces away from a branch arriving from below. Sun as a `radin` source on the
left of the line at `[120, 320]`, `angle 0`. No `via` anywhere: a diagonal
branch is a straight line and needs none, and it keeps the two loss paths off
the main run entirely.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
    EXIT=0

Clean on the first drawable round. `wall: "up"` cleared both `symbols-overlap`
errors and both `wire-through-wall` warnings at once — that is, the opposite of
what those two remedies said to do.

`describe` confirmed the network, but with one reservation I wanted to fix: the
sun arrived horizontally from the left. That is the ladder idiom, and it is the
one arrow on this page whose direction has a physical referent. So:

---

## Round 5 — sun moved overhead

Source `at [360, 190]`, `angle 90` (pointing down into the cell), in the empty
wedge between the two diagonals.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 1 warning, 0 notes
    warning: [label-adrift] source 0 -> cell: its label was pushed 112 past its own clearance to get around branch 1 cell->sky and now sits nearer that than the thing it names  -> move branch 1 cell->sky along its branch with `at`, or set `side` to "up"
    EXIT=1

Two remedies offered. Applied in the order given.

---

## Round 6 — remedy 1, applied literally

"move branch 1 cell->sky along its branch with `at`". Its symbol sat at the
midpoint `(460, 215)`; moved it up the same diagonal to `[510, 162]`.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 1 warning, 0 notes
    warning: [label-adrift] source 0 -> cell: its label was pushed 132 past its own clearance to get around branch 1 cell->sky and now sits nearer that than the thing it names  -> move branch 1 cell->sky along its branch with `at`, or move source 0 -> cell further from its node with `at` to take its label with it
    EXIT=1

**Did the remedy clear it? No — it made it worse**, 112 -> 132. The remedy
names an axis of travel but not a sense; "along its branch" has two ways to go,
and the one that reads naturally (away from the crowding) is the wrong one.
Note also that the finding's *second* alternative silently changed between
rounds, so a reader working down a list of remedies is working down a moving
list.

---

## Round 7 — remedy 2, applied literally

Reverted branch 1's `at`. Round 5's other remedy was `set "side" to "up"`,
which does not say **which element** takes it: the finding's subject is the
source, but the clause sits immediately after one about branch 1. Read it as
the source — `"side": "up"` on source 0.

    $ python -m thermodraw check examples/gallery/15-pv/array.json
    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
    EXIT=0

**Cleared it.** Clean: no errors, no warnings, no notes. Nothing left standing,
so there is no note to justify.

Rendered:

    $ python -m thermodraw render examples/gallery/15-pv/array.json -o examples/gallery/15-pv/array.svg
    examples\gallery\15-pv\array.svg (102,594 bytes)
    EXIT=0

---

## `check --physics` on the final diagram

    $ PYTHONPATH=src PYTHONIOENCODING=utf-8 python -m thermodraw check --physics examples/gallery/15-pv/array.json
    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
    EXIT=0

Silent, and with **no `physics-not-checked` note** — the schema says "A diagram
whose free nodes were all checked gets no note", so both free nodes (`cell` and
`back`) were actually balanced, not skipped. The brief's numbers close against
each other with nothing adjusted.
