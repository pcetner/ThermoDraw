# 12-furnace — session transcript

Model and harness: **claude-opus-5 in Claude Code, running as a subagent.**
Clean room: `ThermoDraw-cleanroom-run4`, from commit 9d507d3.
Date: 2026-09-03.

Instruction given to the session, in full:

> Read examples/gallery/12-furnace/brief.md and do exactly what it says.

This is the complete working record: every command in the order it was run,
its full output, and the reasoning between.

---

## 1. Reading the brief

```
$ cd "/c/Users/Peter Cetner/Documents/GitHub/ThermoDraw-cleanroom-run4" && cat examples/gallery/12-furnace/brief.md
```

Output: the brief as committed (`examples/gallery/12-furnace/brief.md`, 4797
bytes) — not reproduced here, since it is in the repository unchanged beside
this file. Its operative instructions, which govern everything below:

- Draw the furnace wall network; write it to `wall.json`.
- **Documentation is `docs/schema.md` alone.** Do not read anything under
  `src/`, nor `CLAUDE.md`, `README.md`, `CHANGELOG.md`, `tests/`, nor any
  other file under `examples/`, nor any existing `.json` diagram.
- **Give no node `at`**, and leave `via`, and `at` on a branch or source, off
  as well. If the library refuses, it names one node; give that node `at`.
- Iterate `check` to 0 errors and 0 warnings, applying each finding's named
  remedy **literally** before trying anything else.
- Run `check --physics` on the finished file and paste the output verbatim.
  Do not adjust a brief number to quiet it.
- Render once clean. Do not open a browser.
- Record rounds as you go; write `findings.md` at the end.

In the same message I listed the repository root and the gallery folder:

```
$ ls -la && ls examples/gallery/
total 38
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ./
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ../
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 17:08 .git/
-rw-r--r-- 1 Peter Cetner 197121  312 Sep  3 16:59 .gitattributes
-rw-r--r-- 1 Peter Cetner 197121  479 Sep  3 16:59 .gitignore
-rw-r--r-- 1 Peter Cetner 197121 1069 Sep  3 16:59 LICENSE
-rw-r--r-- 1 Peter Cetner 197121 2075 Sep  3 16:59 NOTICE
-rw-r--r-- 1 Peter Cetner 197121 1058 Sep  3 16:59 START-HERE.txt
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 docs/
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 examples/
-rw-r--r-- 1 Peter Cetner 197121 2380 Sep  3 16:59 pyproject.toml
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 src/
11-battery/
12-furnace/
13-cryostat/
14-subsea/
15-pv/
```

I opened no folder under `examples/gallery/` other than `12-furnace`, and no
file under `src/`.

## 2. Reading the schema

```
$ cat START-HERE.txt && ls docs/ && wc -l docs/schema.md
Clean room for a gallery run, from commit 9d507d3.

Start a NEW session in THIS directory for each brief, and give it
one line:

  Read examples/gallery/11-battery/brief.md and do exactly what it says.
  Read examples/gallery/12-furnace/brief.md and do exactly what it says.
  Read examples/gallery/13-cryostat/brief.md and do exactly what it says.
  Read examples/gallery/14-subsea/brief.md and do exactly what it says.
  Read examples/gallery/15-pv/brief.md and do exactly what it says.

Then, still in that session:

  Save the whole transcript of this session as
  <that folder>/transcript.md, put the model and harness on the
  first line of rounds.md, run `PYTHONPATH=src PYTHONIOENCODING=utf-8
  python -m thermodraw check --physics` on the final diagram and
  paste its output at the end of rounds.md, and commit everything
  under that folder as one commit.

When all are done, copy examples/gallery/*/ back into the main
repo on a branch, and read RERUN.md's pre-registered outcomes for
this run BEFORE reading any findings.
schema.md
670 docs/schema.md
```

Then `docs/schema.md` in full (670 lines). It is the repository's own
committed file and is not duplicated here.

The parts I actually leaned on while drafting, and what I took from each:

- **Units.** Fixed per diagram, given once per quantity, values are strings.
  `radin` and `flow` share `q`; a flux has its own key, `q″`, the letter `q`
  followed by U+2033 — "not two apostrophes, not two quote marks". I typed it
  as one character and verified it round-tripped through `json.load` before
  running anything else.
- **`size`.** "you almost never want it." Left out, so the canvas is measured
  and margins come out equal. I gave none.
- **Nodes.** `fixed` for a reservoir, drawing a boundary wall with a stub.
  `at` optional, "left out, the node is placed by the solver".
- **Branches.** `count` + `arrangement`, *required together and never
  inferred*; `value` is **per item** and the group value is drawn beside the
  count. `rate` is "what this path actually carries" and "On a `count`ed
  branch it is the whole group's, not per item".
- **Sources.** `flux` is "several arrows leaving a hatched surface", takes
  `units["q″"]`, and may use `from` or `to`.
- **Coordinates.** What is solved is a ladder: "the nodes form one chain, each
  joined to at most two others by branches". "Anything that is not a chain is
  refused, naming the node that joins three others."
- **`--physics`.** Kirchhoff at every `free` node with a temperature; a
  `fixed` node "is a reservoir and is not asked"; a free node is skipped
  "when it carries a `flux` source, which has no area", and every skip is
  reported as a `physics-not-checked` note.

## 3. Deciding the network before writing anything

From the brief, reading the wall from the inside out, the system is a plain
series ladder with one parallel pair at the cold end:

| element | what it is | how it is drawn |
|---|---|---|
| furnace interior, 1200 °C, held by burners | reservoir | node, `kind: fixed` |
| flame and hot gas, 18 W/cm² on the face | rate per unit area crossing in | source, `kind: flux` |
| three identical firebrick courses, 0.06 K/W each, 3000 W together | three of one path, end to end | one branch, `cond`, `count: 3`, `arrangement: series`, `rate: 3000` |
| brick to board interface, 660 °C | junction with a stated temperature | node, free |
| ceramic fibre board, 0.18 K/W | solid conduction | branch, `cond` |
| steel shell, 120 °C | junction | node, free |
| natural convection off the plate, 0.05 K/W | convection | branch, `conv` |
| radiation to the shop, 0.075 K/W | radiation | branch, `rad` |
| shop air, 30 °C | reservoir | node, `kind: fixed` |
| "no thermal mass … at temperature for two days" | steady state | **no `cap` branch and no `rail`** |

Two decisions worth stating because both are judgement calls, not readings:

1. **`series` with `count: 3`, not three separate branches.** The brief says
   "three courses of identical firebrick, laid one behind the other" — which
   is the schema's `arrangement: "series"` exactly. Three separate `cond`
   branches would have needed two more interior nodes with no temperatures,
   and would also have broken the chain requirement at each of them.
2. **The `flux` attaches to the furnace-interior node.** The brief calls the
   loaded surface "the refractory face", which is not the same place as the
   1200 °C gas — but no resistance is given between the two, so a separate
   face node would be an unconnected node (`network-in-pieces`). Recorded as a
   real gap in `findings.md` §1c rather than papered over.

Node count and neighbours, to confirm the solver would accept it: `furn — bb —
shell — shop`, four nodes in one chain. `shell` has two branches to `shop`,
but they share one pair, so `shell` has two *neighbours*, not three. Nothing
joins three others, so the ladder solver should place all four and I should
need no `at` anywhere — which is what the brief wants.

**Checking the brief's arithmetic before drawing it**, so that if `--physics`
fires later I know whether the fault is mine or the brief's:

```
$ python -c "
print('brick group R =', 3*0.06)
print('through brick =', (1200-660)/0.18)
print('through board =', (660-120)/0.18)
print('conv out      =', (120-30)/0.05)
print('rad out       =', (120-30)/0.075)
print('sum out       =', (120-30)/0.05 + (120-30)/0.075)
"
brick group R = 0.18
through brick = 3000.0
through board = 3000.0
conv out      = 1800.0
rad out       = 1200.0
sum out       = 3000.0
```

The resistance ladder closes exactly on the brief's own numbers: 3000 W
through the brick, 3000 W through the board, and 1800 + 1200 = 3000 W out of
the shell. The stated 3000 W on the brick is therefore consistent, and I could
put it in as `rate` without inventing anything.

The 18 W/cm² does **not** join this arithmetic — 18 W/cm² over a square metre
is 180 kW against 3 kW conducted — and nothing in the schema can relate them,
because a diagram has no area. I drew both as stated and wrote the
discrepancy up rather than adjusting either, per the brief. See
`findings.md` §1a.

## 4. Writing the diagram

```
$ cat > examples/gallery/12-furnace/wall.json <<'JSON'
{
  "title": "Industrial furnace wall, steady state, per square metre",
  "units": {"R": "K/W", "T": "°C", "q": "W", "q″": "W/cm²"},
  "nodes": [
    {"id": "furn", "kind": "fixed", "label": "Furnace interior", "sub": "furn", "value": "1200"},
    {"id": "bb", "label": "Brick to board interface", "sub": "bb", "value": "660"},
    {"id": "shell", "label": "Steel shell", "sub": "shell", "value": "120"},
    {"id": "shop", "kind": "fixed", "label": "Shop air", "sub": "shop", "value": "30"}
  ],
  "branches": [
    {"from": "furn", "to": "bb", "kind": "cond", "label": "Firebrick courses",
     "value": "0.06", "count": 3, "arrangement": "series", "rate": "3000"},
    {"from": "bb", "to": "shell", "kind": "cond", "label": "Ceramic fibre board",
     "value": "0.18"},
    {"from": "shell", "to": "shop", "kind": "conv", "label": "Natural convection",
     "value": "0.05"},
    {"from": "shell", "to": "shop", "kind": "rad", "label": "Radiation to shop",
     "value": "0.075"}
  ],
  "sources": [
    {"to": "furn", "kind": "flux", "label": "Flame and hot gas", "value": "18", "sub": "rad"}
  ]
}
JSON
$ python -c "import json;print(json.load(open(r'examples/gallery/12-furnace/wall.json'))['units'])"
{'R': 'K/W', 'T': '°C', 'q': 'W', 'q″': 'W/cm²'}
```

The second command is the U+2033 check: the units key printed back as `q″`,
one character, so the double prime survived being typed, written and parsed.
The schema warns that getting it wrong is "a JSON syntax error at best and an
unknown-quantity error at worst", and this was cheaper than finding out from
`check`.

No `at` on any node. No `at` and no `via` on any branch or source. No `angle`
anywhere — including on the source, where the schema never states the default
and I was guessing it is 0. No `size`. No `rail`, there being no capacitance.
`P` is not in `units` because there is no `diss` source; `C` is not, because
there is no `cap`.

## 5. Round 1 — check

```
$ export PYTHONPATH=src PYTHONIOENCODING=utf-8 && python -m thermodraw check examples/gallery/12-furnace/wall.json; echo "EXIT=$?"
examples/gallery/12-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean on the first round. **The library never refused the file** — it did not
exit 2 and never named a node, so no `at` was added to anything and the
brief's fallback path was not exercised.

9 labels placed is the number the file implies (4 nodes + 4 branches + 1
source), so nothing was dropped rather than moved.

There were no findings, so no remedy was named and none could be graded.
The measurement the brief is making — whether a named remedy works when
applied literally — has no data from this diagram. That is worth saying
plainly rather than reporting it as a success.

Two things I had budgeted a round for and did not spend one on:

- The **`shell`/`shop` parallel pair.** The schema's bold rule says a
  parallel pair "needs `via` first, and then `side`", and that setting `side`
  alone "is a recipe for the error it looks like it prevents". With the solver
  placing the nodes, none of that applied: the two branches were routed 80
  above and below the line automatically and their labels took opposite sides
  on their own. Not even the `parallel-pair-same-side` note fired. Written up
  as a documentation defect in `findings.md` §2a, because the bold rule gives
  no hint that it is about hand-placed files only — and following it here
  would have required absolute `via` coordinates for a layout I had not yet
  seen, which the same document forbids.
- The **three series firebrick boxes**, which the schema warns can overlap if
  their nodes are too close ("A `series` group needs its nodes far enough
  apart to hold the whole chain"). The solver widened that run to 520 and
  they fit.

## 6. Round 1 — describe

`check` grades the drawing; it cannot say the drawing is the one I meant. The
schema is explicit that "a clean report is not the same as a correct diagram",
so I read `describe` before rendering anything.

```
$ python -m thermodraw describe examples/gallery/12-furnace/wall.json; echo "EXIT=$?"
examples/gallery/12-furnace/wall.json: canvas 1390 x 320, 9 labels

placements: anchor x1, ground x2, node x4, symbol/cond x4, symbol/conv x1,
            symbol/flux x1, symbol/rad x1, wire x13

network:
  furn --cond x3 series-- bb
  bb --cond-- shell
  shell --conv/rad-- shop
  source 0 --flux-> furn

nodes:
  furn           fixed    at (200, 150) solved
  bb             free     at (720, 150) solved
  shell          free     at (1040, 150) solved
  shop           fixed    at (1340, 150) solved

elements:
  branch 0 furn->bb      symbol/cond x3  (460, 150)        above         128x68   Firebrick courses | R_cond = 0.06 K/W | q = 3000 W | 3 in series = 0.18 K/W
  branch 1 bb->shell     symbol/cond     (880, 150)        above         106x33   Ceramic fibre board | R_cond = 0.18 K/W
  branch 2 shell->shop   symbol/conv     (1190, 70)        above         102x33   Natural convection | R_conv = 0.05 K/W
  branch 3 shell->shop   symbol/rad      (1190, 230)       below         104x33   Radiation to shop | R_rad = 0.075 K/W
  source 0 -> furn       symbol/flux     (90, 150)         above         104x33   Flame and hot gas | q″_rad = 18 W/cm²
  node 'furn'            node            (200, 150)        above          92x33   Furnace interior | T_furn = 1200 °C
  wall of node 'furn'    ground          (200, 162) a90    (no label)
  node 'bb'              node            (720, 150)        above         126x33   Brick to board interface | T_bb = 660 °C
  node 'shell'           node            (1040, 150)       above          87x33   Steel shell | T_shell = 120 °C
  node 'shop'            node            (1340, 150)       above          80x33   Shop air | T_shop = 30 °C
  wall of node 'shop'    ground          (1340, 162) a90   (no label)
EXIT=0
```

What I checked in this output, item by item:

- **The `network` block is the network I meant.** `furn --cond x3 series-- bb`
  confirms the count *and* the arrangement — a `parallel` typo there would
  have been a factor of nine on the brick and would have drawn cleanly.
  `shell --conv/rad-- shop` on one line confirms the two cold-end paths are
  one parallel pair between one pair of nodes, not two chains.
  `source 0 --flux-> furn` confirms the arrow arrives rather than leaves.
- **All four nodes are marked `solved`**, i.e. the library placed every one
  of them, which is what the brief asked for.
- **No label is marked `flipped`, `pushed` or `OVERLAPS`.** Every label took
  its automatic side and none had to be moved to get clear, which is a
  stronger statement than "0 warnings".
- **The `q″` reached the page**: `q″_rad = 18 W/cm²`.
- **The counted label reads** `R_cond = 0.06 K/W | q = 3000 W | 3 in series =
  0.18 K/W` — per-item resistance, group rate, derived group resistance. The
  0.18 confirms the fold, and it is the number the brief's board layer also
  is, which is the coincidence that makes the diagram's spacing misleading
  (`findings.md` §7).
- **Two `ground` rows**, one per `fixed` node, both at `a90` and 12 units
  below their node. Nothing arrives at either node from below, so no
  `wire-through-wall`.
- Canvas 1390 x 320, measured rather than fixed, since I set no `size`.

The one thing `describe` could not confirm: that `3000` was read as the
group's rate rather than per item. It appears only inside the label string,
with no field-level row. Written up in `findings.md` §4.

## 7. `check --physics` on the finished diagram

Run on the final file, with no number altered from the brief:

```
$ python -m thermodraw check --physics examples/gallery/12-furnace/wall.json; echo "EXIT=$?"
examples/gallery/12-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Silent, and silent in the strong sense: **no `physics-not-checked` note**, so
no free node was skipped. The two free nodes are `bb` and `shell`, and both
balance — the arithmetic in §3 is exactly what the check redid. `furn` and
`shop` are `fixed`, and the schema says a fixed node "is a reservoir and is
not asked".

That silence is narrower than it looks, and I want it on the record here as
well as in the findings: the 18 W/cm² flux sits on `furn`, a fixed node, so it
was never in the balance; and even on a free node the schema says a flux
"has no area" and forces a skip. The one pair of numbers in this brief that do
not reconcile is the pair `--physics` structurally cannot see, and the report
does not say so. `findings.md` §1a and §5.

## 8. Render

```
$ python -m thermodraw render examples/gallery/12-furnace/wall.json -o examples/gallery/12-furnace/wall.svg; echo "EXIT=$?"; ls -la examples/gallery/12-furnace/; head -c 300 examples/gallery/12-furnace/wall.svg
examples\gallery\12-furnace\wall.svg (95,991 bytes)
EXIT=0
total 112
drwxr-xr-x 1 Peter Cetner 197121     0 Sep  3 17:10 ./
drwxr-xr-x 1 Peter Cetner 197121     0 Sep  3 16:59 ../
-rw-r--r-- 1 Peter Cetner 197121  4797 Sep  3 16:59 brief.md
-rw-r--r-- 1 Peter Cetner 197121  1107 Sep  3 17:09 wall.json
-rw-r--r-- 1 Peter Cetner 197121 96037 Sep  3 17:10 wall.svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1389.8 319.7" width="1389.8" height="319.7" role="img"><style>@font-face{font-family:"ThermoDraw Sans">…
```

(The `head -c 300` is truncated mid-attribute above; it was read only to
confirm the file begins as an SVG with the fonts embedded and a viewBox
matching the 1390 x 320 canvas `describe` predicted. **No browser was opened
and the image was never viewed**, per the brief.)

The 96,037 bytes on disk against the 95,991 the command reports is the CRLF
translation this checkout applies on write; `.gitattributes` governs what is
committed.

## 9. Writing the records

`rounds.md` was written with the model and harness on line 1, the round-1
`check` and `describe` output, the refusal question answered explicitly, and
the `--physics` output pasted verbatim at the end.

`findings.md` was written last, covering the brief's seven questions. Its
substance is not repeated here; the headline is that the diagram is clean in
one round and that this is a **weaker** result than it looks, because the one
inconsistent pair of numbers in the brief (18 W/cm² incident against 3000 W
conducted) is invisible to every check the library has.

One tool note, since this transcript is meant to be complete: the first
attempt to write `findings.md` as a single shell heredoc failed —

```
$ cat > examples/gallery/12-furnace/findings.md <<'MD'
… (13 KB of content) …
MD
/usr/bin/bash: -c: line 155: unexpected EOF while looking for matching `''
Exit code 2
```

— the command was too long and was truncated before its terminator. The file
was then written in four appended heredocs (`PART1`…`PART4`), verified by
`wc -c` after each. This affected nothing about the diagram.

## 10. What was and was not read

Read: `examples/gallery/12-furnace/brief.md`, `docs/schema.md`,
`START-HERE.txt`, and a directory listing of the repository root and of
`examples/gallery/`.

Not read, per the brief: anything under `src/`, `CLAUDE.md`, `README.md`,
`CHANGELOG.md`, anything under `tests/`, any other folder under
`examples/gallery/`, and any existing `.json` diagram. There was no point at
which I wanted to and stopped myself — the schema answered every question I
had except the ones recorded as documentation defects in `findings.md` §2,
and those are gaps no example file would have closed honestly.

## 11. Summary

| | |
|---|---|
| check rounds | **1** |
| errors / warnings / notes, final | 0 / 0 / 0 |
| did the library refuse the file | **no** — no node needed `at` |
| labels placed | 9 of 9 |
| `check --physics` | silent, and no `physics-not-checked` note |
| remedies applied | none — there were no findings to grade |
| `at` / `via` written by hand | none |
| files written | `wall.json`, `wall.svg`, `rounds.md`, `findings.md`, `transcript.md` |

---

*Addendum, folded into the same commit.* A second tooling detail, for the same
reason as the heredoc note in §9: the first `git commit` was written with
PowerShell here-string delimiters (`@'` … `'@`) while running under Git Bash,
which is not here-string syntax there — the `@` characters became part of the
message, giving a subject of `@ 12-furnace: …` and a stray `@` after the
trailer. The message was rewritten from a file and the commit amended, so
there is still exactly one commit for this folder. No file under
`examples/gallery/12-furnace/` was changed by it.
