# Transcript — 02-building (two-zone house with ground-coupled slab)

Running as Claude Opus 5 (claude-opus-5) inside Claude Code (general-purpose subagent).
Appended as I go.

---

## Step 0 — Orientation

Read `examples/gallery/02-building/brief.md` (allowed). Read-restriction accepted:
`docs/schema.md` and the brief only. No `src/`, no other `examples/`, no existing
`.json` diagrams, no README/CHANGELOG/CLAUDE.md/tests.

Command:

```
$ ls examples/gallery/02-building/ && wc -l docs/schema.md
brief.md
538 docs/schema.md
```

So the schema is 538 lines. I will read it in chunks (per the instruction to work in
small steps) and take notes on what the format demands before writing any JSON.

## Step 1 — Reading docs/schema.md

Read in four chunks:

```
$ sed -n '1,120p'   docs/schema.md
$ sed -n '120,280p' docs/schema.md
$ sed -n '280,420p' docs/schema.md
$ sed -n '420,538p' docs/schema.md
```

(Output not pasted verbatim here — it is the repository's own `docs/schema.md`,
unchanged, and pasting 538 lines back would bury the log. Everything I relied on
from it is quoted where I use it.)

Notes I took that decide the drawing:

- Branch kinds: `cond conv rad contact spread pipe mixed cap flow break`.
- `flow` **is** a branch kind: "heat moved from one node to another because a
  fluid moves, or because something pumps it", directed `from`→`to`, carries a
  rate in `units.q`, `angle` refused, route with `via`.
- Source kinds: `diss` (P), `radin` (q), `flow` (q), `flux` (q″).
- Every `value` is a **string**. Units fixed per diagram, appended from `units`.
- Node with no `value` and no `sub` draws its label alone — the documented idiom
  for "interior junctions between series layers".
- Resistance subscripts are set by the library; `mixed`, `cap`, `flow` take my
  own `sub`.
- "A window quoted as one number for conduction *and* convection is `mixed`."
- Habits that are also checks: leave a node sideways before turning (40–90 units);
  a parallel pair needs `side`; space labels, not symbols.

### A contradiction I noticed immediately

Line ~124 onward documents `flow` as a branch kind that moves heat between two
nodes. Line ~424, under `network-in-pieces`, says the opposite:

> "heat carried from one node to another by a moving fluid has no branch kind
> yet, and this finding is what tells you the drawing did not say what you meant."

Both sentences are in the same file. The branch table is more specific and gives
`flow` a full row (value in `units.q`, directed, `angle` refused), so I am
believing the branch table and using `flow` **branches** for infiltration and for
the stairwell. Recording this for findings.md either way.

## Step 2 — Deciding the network before touching coordinates

Nodes (10):

| id | kind | T | why |
|---|---|---|---|
| `gf` | free | 21 | ground-floor zone air |
| `uf` | free | 23 | upper-floor zone air |
| `w1`..`w4` | free, **no `sub`, no `value`** | — | the three interfaces inside the wall plus the brick outer face. The brief gives no temperatures for them, and the schema's documented idiom for exactly this is a node with neither `sub` nor `value`: "Interior junctions between series layers routinely have no temperature of their own" |
| `out` | fixed | -4 | outdoor air |
| `sky` | fixed | -15 | effective sky |
| `gnd` | fixed | 10 | deep ground |
| `roof` | free | 8 | roof, stated temperature |

Branches (15):

- 4 × `cond` in series for the wall layers, then 1 × `conv` (0.012) from the
  brick outer face to outdoor air. Five branches, four interior nodes: this is
  the only way the schema lets me say "each layer is its own conduction path in
  series", and it is exactly right.
- lintel `gf`→`out`: **`mixed`**, `sub: "lintel"`, 0.42. Reasoning: the brief
  says 0.42 K/W "from zone air to outdoor air", in parallel with the *whole*
  wall assembly — and the whole wall assembly includes the outer convection
  film. A number that spans air to air is not pure conduction. The schema's rule
  is explicit for the analogous case: "A window quoted as one number for
  conduction *and* convection is `mixed`." Cost: the drawing no longer says
  "this is a steel conduction bridge"; `mixed` "has no texture at all". The word
  "lintel" survives only in `label` and in `R_lintel`.
- window `gf`→`out`: `mixed`, `sub: "win"`, 0.31. Straight out of the doc.
- infiltration `gf`→`out`: `flow` branch, 185 W, `sub: "inf"`.
- slab `gf`→`gnd`: `cond` 0.6.
- intermediate floor `gf`→`uf`: `cond` 0.09.
- stairwell `gf`→`uf`: `flow` branch, 240 W, `sub: "stair"`.
- roof: `conv` 0.14 to `out`, `rad` 0.22 to `sky`, in parallel.
- 2 × `cap` to the rail: 2.1 and 1.8 MJ/K.

Sources (2): `diss` 600 W and `radin` 850 W, both into `gf`. Solar arriving
through glazing is radiation arriving at a node, which is exactly `radin`.

Total labels I expect `check` to count: 10 nodes + 15 branches + 2 sources = **27**.

### Three things I already know I cannot say

1. **Infiltration direction.** The brief is emphatic: "air leaks in ... carrying
   outdoor air straight into the ground-floor zone", i.e. the *air* moves
   outdoor → indoor, while the *heat* is a 185 W loss from the zone. A `flow`
   branch has one direction and the schema defines it as the heat's: "`from` and
   `to` are the way the heat goes". So I must write `gf`→`out` and the drawing
   will show air apparently leaving the house. I cannot state the mass direction
   at all.
2. **0.5 air changes per hour.** No field takes it. It goes in the `label` as
   prose or it is lost.
3. **"dominant heat loss per unit area"** — there is no per-area quantity except
   `q″` on a `flux` source, which is a source, not a property of a resistance.
   Lost.

### Units

`{"R": "K/W", "C": "MJ/K", "T": "°C", "P": "W", "q": "W"}`

I chose `MJ/K` rather than `J/K` + `"2100000"` because the brief states MJ/K and
the schema's own example of a non-base unit is a prefixed one ("a diagram cannot
mix `K/W` with `mK/W`", implying prefixed units are contemplated). Risk I am
taking knowingly: `--physics` says "a unit the check does not know skips the
diagram rather than guessing", and capacitance is irrelevant to a steady-state
balance, so if `MJ/K` makes it skip the whole diagram that is itself a finding.

## Step 3 — first draft, and the check rounds

Wrote `examples/gallery/02-building/house.json` in one go from the plan above.
Coordinates chosen by hand on the schema's stated habits: hot on the left, cold
on the right, rail along the bottom, parallel paths above and below the main
line, turns taken 80–160 units sideways out of `gf` rather than straight out of
it, and the wall chain pushed far enough right (first wall node at x = 1560) that
the gypsum-board symbol at x = 1100 sits clear of the four bypass stubs leaving
`gf` at x = 720/760/840/1000.

`gf` is the hard node: it carries eight wires (wall, lintel, glazing,
infiltration, slab, intermediate floor, stairwell, capacitance) and `side` offers
four directions, so its own label goes on `"angle": 135` — the diagonal that the
schema says only `angle` can reach. Same reason for `"angle": 45` on `out`, which
carries five (wall from the left, roof from above, glazing from below,
infiltration from the right, lintel on a short diagonal from the upper left).

Rounds 1–4 are in rounds.md with verbatim output. Summary: clean on the first
run (0 errors, 0 warnings), one `parallel-pair-same-side` note whose stated
remedy was already satisfied in the file and which turned out to be uncleanable —
three parallel branches, two sides. Verified the cycle by moving the label up
(note moved to the other pair), then by trying `"side": "right"` (1 error +
1 warning, both telling me to go back to up/down). Left it at the Round 1 file.

## Step 4 — describe

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/02-building/house.json
```

Full output is long; the parts I actually checked against my intent:

```
placements: ground x3, node x10, symbol/cap x2, symbol/cond x6,
            symbol/conv x2, symbol/diss x1, symbol/flow-branch x2,
            symbol/mixed x2, symbol/rad x1, symbol/radin x1, wire x36

network:
  gf --cond-- w1
  w1 --cond-- w2
  w2 --cond-- w3
  w3 --cond-- w4
  w4 --conv-- out
  gf --mixed/mixed/flow-branch-- out
  gf --cond-- gnd
  gf --cond/flow-branch-- uf
  roof --conv-- out
  roof --rad-- sky
  gf --cap-- rail
  uf --cap-- rail
```

`ground x3` = the three `fixed` nodes. `symbol/cond x6` = five wall/slab
conductions plus the intermediate floor. Counts match what I wrote. No
`network-in-pieces`: `roof` is joined to the rest only through `out`, which is
what the brief describes, and `describe` confirms it is one piece.

What `describe` did **not** tell me is in findings.md — chiefly that
`gf --mixed/mixed/flow-branch-- out` does not say which `mixed` is the lintel and
which is the glazing, and that the network block drops the direction of the
`flow` branches, which is the one thing about them that carries meaning.

Also noticed: `describe` escapes `→` as `\u2192` in its output but prints `°`
raw, so on a cp1252 terminal the temperatures come out as `23 �C` while the
arrows come out as escapes. Cosmetic, but inconsistent.

## Step 5 — render

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/02-building/house.json -o examples/gallery/02-building/house.svg
examples\gallery\02-building\house.svg (29,474 bytes)
EXIT=0
```

The schema warns that "`render` alone emits CSS custom properties with no
fallback, so pass its output through `theme` before saving it ... Without one of
them the file draws nothing." I did not want to ship a blank SVG, so I grepped
the output rather than opening it:

```
$ grep -n ':root' examples/gallery/02-building/house.svg | head
3:  :root{--sym:#1b1b1f;--panel:#ffffff;--ink:#16181d; ...}
5:    :root:not([data-theme="light"]){--sym:#d8d6d1; ...}
6:  :root[data-theme="dark"]{--sym:#d8d6d1; ...}
```

So the **CLI** `render` already applies `theme.with_variables`; the warning is
about the Python API only, and the page does not say so. Recorded in findings.

## Step 6 — `--physics`, and one diagnostic probe

Ran `check --physics` once on the final file (output pasted verbatim at the end
of rounds.md). It fired `node-does-not-balance` on `roof` and on `uf` — and
**not** on `gf`, which is the node whose numbers most obviously do not add up.

That surprised me, so before writing it up I tested the hypothesis on a **copy in
the scratchpad**, not on the shipped diagram: give the four wall-interface nodes
the temperatures the series chain implies (19.80 / -0.31 / -1.83 / -2.70 °C) and
see whether `gf` starts being asked.

```
$ PYTHONIOENCODING=utf-8 PYTHONPATH=src python -m thermodraw check --physics --quiet <scratchpad>/probe.json
warning: [node-does-not-balance] node 'gf': 1.47e+03 W arrives and 693 W leaves at the stated values — 600 W in by source 0; 850 W in by source 1; 185 W out by branch 7 gf->out; 240 W out by branch 10 gf->uf; 109 W out by branch 0 gf->w1 (1.2 K over 0.011 K/W); 59.5 W out by branch 5 gf->out (25 K over 0.42 K/W); 80.6 W out by branch 6 gf->out (25 K over 0.31 K/W); 18.3 W out by branch 8 gf->gnd (11 K over 0.6 K/W); 22.2 W in by branch 9 gf->uf (2 K over 0.09 K/W)
[roof and uf warnings unchanged]
EXIT=1
```

Confirmed. A `free` node adjacent to a valueless junction is skipped silently, so
the schema's own recommended idiom for series layers ("Interior junctions between
series layers routinely have no temperature of their own") switches off the
physics check for the node on the inside of the wall. The probe file stays in the
scratchpad; the shipped `house.json` is unchanged.

The 780 W gap is a property of the brief's numbers, not of my drawing (the house
has no heating plant), so per instructions I am recording it rather than editing
the diagram to make it go away.

## Step 7 — commit

Path-scoped add and commit of `examples/gallery/02-building/` only.

Wrote `findings.md` (7 sections). Final confirmation run before committing:

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/02-building/house.json
examples/gallery/02-building/house.json: 27 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 6 gf->out and branch 7 gf->out run between the same two nodes and both labels went to the same side  -> set `side` to "down" on the lower of the two
EXIT=0
```

`house.svg` was rendered from this exact file and is newer than it, so it is
current. Committing `examples/gallery/02-building/` path-scoped.

Note on the commit command: the form given in my instructions,
`git commit -- <path> -m "<msg>"`, fails — after `--` git treats everything as a
pathspec, so `-m` and the message text are both read as filenames
(`error: pathspec '-m' did not match any file(s) known to git`). Ten retries all
failed the same way; it was not a lock. Committed with the message flag before
the `--` instead, which is the same commit, path-scoped identically:

```
$ git commit -F <msgfile> -- examples/gallery/02-building/
[master f7d8100] gallery: two-zone house with a ground-coupled slab (02-building)
 5 files changed, 843 insertions(+)
```

(This transcript note is the one thing in the folder written after the commit,
so it is not in it.)
