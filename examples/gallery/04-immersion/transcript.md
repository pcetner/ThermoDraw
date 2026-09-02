# Working transcript — 04-immersion

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent).
Appended as I go.

---

## 0. Setup

```
$ cd "$(git rev-parse --show-toplevel)" && pwd && ls && wc -l docs/schema.md
/c/Users/Peter Cetner/Documents/GitHub/ThermoDraw-cleanroom
LICENSE
NOTICE
START-HERE.txt
docs/
examples/
pyproject.toml
src/
538 docs/schema.md
```

```
$ ls -la examples/gallery/04-immersion/ && python --version && git log --oneline -1
total 16
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  1 17:37 ./
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  1 17:37 ../
-rw-r--r-- 1 Peter Cetner 197121 4400 Sep  1 17:36 brief.md
Python 3.11.9
df3a92f clean room
```

Read `examples/gallery/04-immersion/brief.md` and `docs/schema.md`. Nothing
else. I did not open `src/`, `tests/`, `README.md`, `CLAUDE.md`, or any other
example. I never opened an existing `.json` diagram — the only worked example I
have is the hero listing pasted inside `docs/schema.md` itself.

---

## 1. Reading the brief into a network, before writing any JSON

The chain the brief describes, hot end to cold end:

```
junction 72 --cond 0.0275 x8 parallel--> spreader 61 --conv 0.00375--> fluid 49
   --conv 0.0028--> coil 40 --flow 3200 W--> technical water 38
   --mixed 0.0019--> facility water 26 --conv 0.0058--> ambient air 24
```

Arithmetic I did up front to decide which numbers are per-item and which are
for the whole rack:

- `8 x 0.0275 K/W` in parallel is `0.0034375 K/W`; `3200 W x 0.0034375 = 11 K`,
  and `72 - 61 = 11 K`. So `0.0275` is **per processor** and the group is
  parallel. (Per the schema, `value` is per item and `arrangement` is never
  inferred, so I have to say `parallel` explicitly or the number means
  something 64x different.)
- Pool boiling: `(61 - 49) / 0.00375 = 3200 W`. So `0.00375` is the **whole
  rack's** boiling path, not per processor (per processor it would need to be
  `0.03`). One branch, no `count`.
- Condensing film: `(49 - 40) / 0.0028 = 3214.3 W`, not 3200 W. The exact
  value for 3.2 kW over 9 K is `0.0028125`. The brief has rounded to two
  significant figures. Noted; I am transcribing the brief's number, not
  correcting it.
- CDU: `(38 - 26) / 0.0019 = 6316 W`, but the loop only carries
  `3200 + 800 = 4000 W`. Does not agree.
- Dry cooler: `(26 - 24) / 0.0058 = 345 W`, against 4000 W to reject. Does not
  agree by an order of magnitude.

So the hot half of the brief is internally consistent and the cold half is not.
I am drawing what the brief says and will report the disagreement rather than
inventing numbers that balance.

### Decision: the phase change is one node

`docs/schema.md`, Nodes: "`phase` is a node whose temperature a phase change
holds rather than a boundary ... Condensation at 3.2 kW with no temperature
drop is one node, not two surfaces with a path between them." That sentence is
written at this brief. The boiling surface and the condensing vapour are the
same saturated fluid at 49 C, so there is one `phase` node at 49 C with the
boiling resistance on one side and the condensing film on the other.

### Decision: the pumped water loop collapses to one node

This is the part the schema cannot say, and I want it recorded before I try.
The brief gives the technical water **two** temperatures — in at 30 C, out at
38 C — because it is a stream, not a place. A ThermoDraw node is a place with
one temperature, and `flow` is a branch between two such places carrying a
rate. There is no way to write "one stream, 30 in, 38 out".

The three shapes I considered:

1. Two nodes `wi` (30) and `wo` (38) with a `flow` branch between them. The
   water is heated at the coil, so a flow branch `wi -> wo` would claim the
   3.2 kW moves from the 30 C node to the 38 C node, and the coil would then
   have nothing carrying its heat away. Wrong.
2. Two nodes, with `wo` in the network and `wi` left hanging. `wi` would have
   no branch at all and `check` would fire `network-in-pieces` — correctly.
   Attaching it with a `break` branch to silence that would be a lie: `break`
   means a mechanical connection that carries no heat, and the return line is
   not that.
3. One node `tw` at 38 C, with "30 C in" carried in the node's **label** text.

I am taking (3). It is an approximation: the 30 C stops being a temperature the
library knows about and becomes prose. Recorded in findings.

### Decision: kinds

- junction to spreader: `cond` (the brief says "by conduction").
- pool boiling: `conv`. Boiling is convection; the schema has no boiling kind
  and `pipe`/`spread` are both wrong.
- condensing film: `conv`, same reasoning.
- water carrying 3.2 kW to the CDU: `flow`. The schema is explicit that this
  is what `flow` is for, and that a `flow` *source* cannot join two nodes.
- plate heat exchanger, quoted as one overall resistance across two streams:
  `mixed`. The schema: "A window quoted as one number for conduction *and*
  convection is `mixed`." An overall exchanger resistance is exactly that.
- dry cooler: `conv` (air side).
- fluid inventory: `cap` to `rail`.

### Decision: units for the thermal mass

The brief says 240 kJ/K. `units` are fixed per diagram and there is one `C`
entry, so I cannot write kJ/K for this one and J/K elsewhere — but there is
only one capacitance, so that is not the constraint. The real reason I chose
`"C": "J/K"` with value `"240000"` is the physics checker: "a unit the check
does not know skips the diagram rather than guessing", and I have exactly one
shot at `--physics` at the end. `J/K` is the unit the schema's own example
uses, so it is the one I am sure is known. `240000 J/K` is the same quantity as
240 kJ/K, just less readable on the page.

### Decision: `rate` annotations

`rate` states what a path carries. I put it on the branches whose carried power
the brief states in words (`3.2 kW` through the boiling and condensing paths,
"everything" = 3200 + 800 = 4000 W through the CDU and the dry cooler). I left
it off the counted `j -> ihs` group, because the schema does not say whether
`rate` on a `count`ed branch is per item or for the group, the way it says
`value` is per item. Guessing there would put a wrong number on the page.

### Layout plan

Heat left to right along `y = 160`, nodes 260 apart (the schema suggests 220,
but `R_cond = 0.0275 K/W` plus a two-line label is wide, and it says to space
labels rather than symbols). Rail at `y = 420`. Ambient `fixed` on the main
line rather than at rail level, with `angle: 90` so its label goes right and
away from the branch arriving from the left, copying the hero.

---

## 2. Round 1

Wrote `rack.json` (7 nodes, 7 branches, 2 sources, rail) and ran:

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/04-immersion/rack.json; echo "EXIT=$?"
examples/gallery/04-immersion/rack.json: 16 labels placed, 0 errors, 4 warnings, 0 notes
warning: [label-adrift] node 'j': its label was pushed 52 past its own clearance to get around the wire of branch 0 j->ihs and now sits nearer that than the thing it names  -> move a `via` waypoint on branch 0 j->ihs so it does not run past this label, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'sat': its label was pushed 48 past its own clearance to get around branch 1 ihs->sat and now sits nearer that than the thing it names  -> move branch 1 ihs->sat along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [label-adrift] node 'tw': its label was pushed 40 past its own clearance to get around branch 4 tw->fw and now sits nearer that than the thing it names  -> move branch 4 tw->fw along its branch with `at`, or `angle`, which turns a node's label frame and is the only thing that reaches a diagonal
warning: [nodes-too-close] node 'coil' and node 'tw' are 260 apart, and the labels along that run come to 262  -> move them apart with `at`. It is the labels that set the spacing, not the symbol, which is only 44 wide
EXIT=1
```

Reasoning at this decision point. 16 labels placed is exactly 7 + 7 + 2, so
nothing was dropped and every finding is about placement. The first finding's
first named remedy — put a `via` on branch 0 — **cannot be done**: branch 0 is
the `count: 8` parallel group and the schema says a repeated branch "cannot
also take `via`". So I take its second named remedy, `angle` on the node.

Edits made, and why:

- `nodes[0]` (`j`): added `"angle": 135` — the schema's angle table says 135
  puts the label above and to the left, which is away from the comb that fans
  out to the right.
- `branches[1]` (`ihs->sat`): added `"at": [540, 160]`, moving the box back
  towards `ihs`. This is the literal named remedy.
- `branches[4]` (`tw->fw`): added `"at": [1470, 160]` after the re-spacing
  below, moving the box away from `tw`. Literal named remedy.
- `nodes` `tw`, `fw`, `amb`: x moved from 1240/1500/1760 to 1300/1560/1820, so
  the `coil`-`tw` run is 320 rather than the 260 that was 2 short of the 262
  the finding asked for. `rail.span` widened to `[180, 1840]` to match.

---

## 3. Rounds 2-5

Full `check` output for every round, and which named remedy cleared which
finding, is in `rounds.md` — written round by round as I went, not afterwards.
The short version of the reasoning at each decision point:

- **Round 2.** `tw` and `nodes-too-close` cleared by their literal remedies.
  `j` moved off the comb onto the source on its other side (52 -> 96 past).
  `sat` was unchanged at *exactly* 48 past after moving branch 1 fifty units —
  the first evidence the remedy was addressing the wrong thing.
- **Round 3.** Pushed the same remedy harder (branch 1 to `x = 500`) purely to
  test it. The `sat` finding then re-blamed the branch on the *other* side with
  the same number, 48. That settles it: the overshoot is `sat`'s label width
  (192, per `describe`) against a 260 run, and moving neighbours cannot help.
  Obeying the remedy also manufactured two new findings —
  `wire-through-symbol` and an adrift `ihs`.
- **Round 4.** Took the second named remedy, `angle: 135` on `sat`. It made
  things worse (48 -> 84) by swinging a wide label across `ihs` onto the comb,
  and then offered the impossible `via`-on-a-counted-branch remedy again. Both
  named remedies now exhausted, so I stopped applying the finding's text and
  fixed the cause it never names: spaced the run out from 260 to 360.
- **Round 5.** Clean: `0 errors, 0 warnings, 0 notes`, exit 0, 16 labels.

The one judgement call I want on the record: I chose to widen the drawing
(canvas ended up 2221 x 485) rather than shorten `Dielectric fluid, boiling /
condensing` to something that fits. The label is the only place in the file
that says the boiling and the condensing are the *same* node, which is the
whole point of the `phase` kind here, so I paid canvas for it.

---

## 4. describe

```
$ PYTHONPATH=src python -m thermodraw describe examples/gallery/04-immersion/rack.json
examples/gallery/04-immersion/rack.json: canvas 2221 x 485, 16 labels

placements: anchor x2, ellipsis x1, ground x1, node x7, phase x1,
            symbol/cap x1, symbol/cond x10, symbol/conv x3, symbol/diss x2,
            symbol/flow-branch x1, symbol/mixed x1, wire x35

rail: y 420, span (180, 2040), reference 'amb'

network:
  j --cond-- ihs
  ihs --conv-- sat
  sat --conv-- coil
  coil --flow-branch-- tw
  tw --mixed-- fw
  fw --conv-- amb
  sat --cap-- rail

nodes:
  j              free     at (200, 160)
  ihs            free     at (460, 160)
  sat            phase    at (820, 160)
  coil           free     at (1180, 160)
  tw             free     at (1500, 160)
  fw             free     at (1760, 160)
  amb            fixed    at (2020, 160)

elements:
  branch 0 j->ihs        symbol/cond x10 (330, 160)        above         118x50   Junction → spreader | R_cond = 0.0275 K/W | 8 in parallel
  branch 1 ihs->sat      symbol/conv     (640, 160)        above         125x50   Pool boiling | R_conv = 0.00375 K/W | q = 3200 W
  branch 2 sat->coil     symbol/conv     (1000, 160)       above         117x50   Condensing film | R_conv = 0.0028 K/W | q = 3200 W
  branch 3 coil->tw      symbol/flow-bra (1340, 160)       above         153x33   Technical water, rack → CDU | q_w = 3200 W
  branch 4 tw->fw        symbol/mixed    (1670, 160)       above         112x50   CDU plate exchanger | R_hx = 0.0019 K/W | q = 4000 W
  branch 5 fw->amb       symbol/conv     (1890, 160)       above         117x50   Dry cooler | R_conv = 0.0058 K/W | q = 4000 W
  branch 6 sat->rail     symbol/cap      (820, 290) a90    right         100x33   Fluid inventory | C_f = 240000 J/K
  source 0 -> j          symbol/diss     (20, 160)         above         115x50   Processor dissipation | P_p = 400 W | 8 in parallel
  source 1 -> tw         symbol/diss     (1500, 198) a270  right          89x33   Pump work | P_pump = 800 W
  node 'j'               node            (200, 160) a135   above left     99x33   pushed 8   Processor junction | T_j = 72 �C
  node 'ihs'             node            (460, 160)        above          76x33   Heat spreader | T_ihs = 61 �C
  node 'sat'             node            (820, 160)        above         192x33   Dielectric fluid, boiling / condensing | T_sat = 49 �C
  node 'coil'            node            (1180, 160)       above          79x33   Condenser coil | T_coil = 40 �C
  node 'tw'              node            (1500, 160)       above         138x33   Technical water (30 �C in) | T_w = 38 �C
  node 'fw'              node            (1760, 160)       below          73x33   flipped   Facility water | T_fw = 26 �C
  node 'amb'             node            (2020, 160) a90   right          78x33   Ambient air | T_amb = 24 °C
EXIT=0
```

What I checked against, and what it told me:

- 16 labels, 7 nodes, and the `network:` block reads as the chain I meant. The
  `phase x1` placement confirms `sat` drew as a phase node and not as a
  boundary.
- `symbol/cond x10` with `ellipsis x1` and `anchor x2` is the condensed form of
  the eight parallel paths plus the expanded form, both in the file, exactly as
  the schema says.
- **A real defect it surfaced:** `source 0` prints `8 in parallel`. The schema
  says of a source's `count`: "They simply add, so there is no `arrangement` to
  state." The library nonetheless borrows the branch wording and prints an
  arrangement I was told not to give and could not have given. Eight processors
  each dissipating 400 W are not "in parallel". I left it, because dropping
  `count` would lose "400 W each, eight of them" from the data, and the wrong
  word is the library's, not mine. Logged in `findings.md`.
- `node 'fw'` went `below`, marked `flipped`, and `node 'j'` is `pushed 8`.
  Both fine, and I would not have known without this command.
- The `°` and `→` characters print as `→` in one column and mojibake in
  another, in the same output. Cosmetic, but it means you cannot trust this
  output to proofread a label's text.

---

## 5. Render

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/04-immersion/rack.json -o examples/gallery/04-immersion/rack.svg
examples\gallery\04-immersion\rack.svg (29,220 bytes)
EXIT=0
```

Checked, without opening a browser or looking at the image, that the file is
not the "draws nothing" case the schema warns about:

```
$ grep -o 'var(--[a-z0-9-]*' rack.svg | sort -u   ->  --ink --ink-2 --ink-3 --panel --rule --sans --sym --tex
$ grep -o '\-\-[a-z0-9-]*:'   rack.svg | sort -u  ->  --accent --d --ink --ink-2 --ink-3 --panel --rule --sans --sym --tex
```

Every variable referenced is also defined, so the CLI's `render` has already
done what the schema tells you to call `theme.with_variables` for. The schema's
warning ("Without one of them the file draws nothing") is written about the
Python API and does not say the CLI already handles it — a doc gap, noted.

---

## 6. Physics check (record only)

Run once, verbatim output pasted at the end of `rounds.md`, diagram not
changed in response. Four warnings, all in the cold half of the loop, all of
them the brief's arithmetic that I had already computed by hand in section 1
above. The hot half — junction, spreader, phase node — balances, so the
`count`/`arrangement` folding is doing what the schema says.

---

## 7. Commit

`git add` and `git commit` scoped to `examples/gallery/04-immersion/` only, so
that the four other agents working in this repository in parallel cannot have
their files swept into this commit.
