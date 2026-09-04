# 14-subsea — session transcript

Model: claude-opus-5 in Claude Code, running as a subagent.
Harness: Claude Code on Windows 10, Bash tool (Git Bash), Python 3.11.9.
Working directory: the clean room `ThermoDraw-cleanroom-run4`, from commit
9d507d3. Every command below was run from the repository root.

The session's one instruction was: *"Read examples/gallery/14-subsea/brief.md
and do exactly what it says."*

---

## 1. Reading the brief

```
$ ls -la && echo "---" && cat examples/gallery/14-subsea/brief.md
total 38
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ./
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ../
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 17:31 .git/
-rw-r--r-- 1 Peter Cetner 197121  312 Sep  3 16:59 .gitattributes
-rw-r--r-- 1 Peter Cetner 197121  479 Sep  3 16:59 .gitignore
-rw-r--r-- 1 Peter Cetner 197121 1069 Sep  3 16:59 LICENSE
-rw-r--r-- 1 Peter Cetner 197121 2075 Sep  3 16:59 NOTICE
-rw-r--r-- 1 Peter Cetner 197121 1058 Sep  3 16:59 START-HERE.txt
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 docs/
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 examples/
-rw-r--r-- 1 Peter Cetner 197121 2380 Sep  3 16:59 pyproject.toml
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 src/
---
```

(The brief itself is `brief.md` beside this file and is not re-transcribed.)

Its binding constraints, as I read them:

- Only documentation is `docs/schema.md`. Nothing under `src/`, no
  `CLAUDE.md` / `README.md` / `CHANGELOG.md`, nothing under `tests/`, no
  other folder under `examples/`, and no existing `.json` diagram.
- **Give no node `at`**, and no `via` or `at` on any branch or source. If the
  library refuses the file it will name one node; give that node `at` and
  `via` to the branches leaving it sideways, and nothing else.
- Iterate `check` to 0 errors and 0 warnings. Apply each finding's named
  remedy literally before trying anything else. Notes may stand if I say why.
- Run `check --physics` on the finished file and paste the output verbatim.
  Do not adjust a brief number to quieten it.
- No browser, and do not render an image in order to look at it.
- Append to `rounds.md` as I go, and write `findings.md` at the end.

I obeyed all of these. I read `docs/schema.md` and this brief and nothing
else; I opened no `.json`, no source file, and no other gallery folder.

## 2. Orienting, without reading anything forbidden

```
$ cat START-HERE.txt && echo "=== SCHEMA ===" && wc -l docs/schema.md && ls docs/ examples/ examples/gallery/
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
=== SCHEMA ===
670 docs/schema.md

docs/:
schema.md

examples/:
gallery/

examples/gallery/:
11-battery/
12-furnace/
13-cryostat/
14-subsea/
15-pv/
```

The room contains only `docs/schema.md` — the design record, the changelog
and the decisions are all stripped, which is the point. `ls` of the gallery
names the sibling folders; I opened none of them.

## 3. Reading the schema

Read in three passes, because it is 670 lines.

```
$ sed -n '1,240p' docs/schema.md
$ sed -n '240,480p' docs/schema.md
$ sed -n '480,670p' docs/schema.md
```

(Output not reproduced — it is `docs/schema.md`, unchanged, in this
repository. The clauses I actually leaned on are quoted in `findings.md`.)

What I took from it, in the order it mattered:

- The shape: `nodes`, `branches`, `sources`, optional `rail`, `units`, `size`,
  `title`. `units` is per quantity, and every `value` is a **string**.
- Branch kinds. Three decided the diagram:
  - `spread` — "a path whose cross-section grows as the heat goes" — for the
    bolted joint, since the brief says heat "leaves a small footprint and
    enters a much larger one".
  - `pipe` — "a near isothermal link, a heat pipe or a vapour chamber" —
    named in the schema for exactly the part the brief names.
  - `mixed` — "the mechanism is combined or deliberately unstated. A window
    quoted as one number for conduction *and* convection is `mixed`." The
    brief's housing wall is one number covering steel and water film, and the
    brief says the drawing should not pretend otherwise.
- Subscripts on resistances are the library's, not mine — except on `mixed`,
  where `sub` is mine.
- `rate` on a branch: "what this path actually carries", drawn on its own
  line, and "stating it opts the branch into `rate-does-not-match` under
  `--physics`".
- Interior junctions: "A node with **no `value` and no `sub`** draws its label
  alone and no `T` at all. Interior junctions between series layers routinely
  have no temperature of their own."
- The solver: "What is solved is a **ladder**: the nodes form one chain, each
  joined to at most two others by branches. ... Anything that is not a chain
  is refused, naming the node that joins three others."
- `--physics`: a free node is skipped when it, or a **neighbour**, has no
  temperature, and every skip is reported as one `physics-not-checked` note.

I read that last clause before writing anything, and predicted from it that
this diagram would get one node of four checked. It did.

## 4. Designing the diagram

The brief gives a straight series chain, so no `at` should be needed anywhere:

    board --spread(0.30)-- flange --pipe(0.02)-- vchead --conv(0.08)-- bore --mixed(0.15)-- sea

Three decisions worth naming:

1. **There must be a node between the vapour chamber and the oil gap.** They
   are two mechanisms with two numbers, so they cannot be one branch. The
   brief quotes no temperature for the chamber head, so `vchead` gets a
   `label` and neither `sub` nor `value`. I knew from §3 that this would cost
   three of four nodes under `--physics`, and did it anyway, because the
   alternative is writing a temperature nobody quoted.
2. **The housing wall is `mixed`, with `sub: "wall"`.** The schema says `sub`
   on a `mixed` "names the mechanism" — but the whole content of `mixed` is
   that the mechanism is not broken out, so there is no mechanism to name. I
   put a place name there instead, and recorded it as a documentation defect.
3. **`rate: "60"` on the spread branch only.** The brief says that path
   "carries the whole 60 W", and says it of no other path. All four carry
   60 W in steady state; the brief asserted it once, so I stated it once.

`sea` is `fixed` — a reservoir, and it gets the boundary wall. No `rail`:
steady state, no capacitance, and the schema says such a diagram "has nothing
to hang on it".

```
$ ls -la examples/gallery/14-subsea/ && git log --oneline -1 && python --version
total 12
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ./
drwxr-xr-x 1 Peter Cetner 197121    0 Sep  3 16:59 ../
-rw-r--r-- 1 Peter Cetner 197121 4841 Sep  3 16:59 brief.md
f9f3e17 13-cryostat: the solver placed it unaided; two 300 K walls it cannot join
Python 3.11.9
```

The folder held only the brief. (`git log` shows a sibling brief's commit
subject; I did not open that folder.)

## 5. Writing the file

```
$ cat > examples/gallery/14-subsea/bottle.json <<'EOF'
{
  "title": "Subsea electronics bottle on the seabed at 1800 m",
  "units": {"R": "K/W", "T": "°C", "P": "W", "q": "W"},
  "nodes": [
    {"id": "board",  "label": "Power board",   "sub": "b",   "value": "37"},
    {"id": "flange", "label": "Spreader flange", "sub": "f", "value": "19"},
    {"id": "vchead", "label": "Vapour chamber head"},
    {"id": "bore",   "label": "Housing bore",  "sub": "hb",  "value": "13"},
    {"id": "sea",    "kind": "fixed", "label": "Seawater at 1800 m", "sub": "sea", "value": "4"}
  ],
  "branches": [
    {"from": "board",  "to": "flange", "kind": "spread", "label": "Bolted joint spreading", "value": "0.30", "rate": "60"},
    {"from": "flange", "to": "vchead", "kind": "pipe",   "label": "Vapour chamber", "value": "0.02"},
    {"from": "vchead", "to": "bore",   "kind": "conv",   "label": "Oil-filled gap", "value": "0.08"},
    {"from": "bore",   "to": "sea",    "kind": "mixed",  "label": "Housing wall and sea film", "sub": "wall", "value": "0.15"}
  ],
  "sources": [
    {"to": "board", "kind": "diss", "label": "Converter stage", "value": "60", "sub": "d"}
  ]
}
EOF
$ python -c "import json;json.load(open('examples/gallery/14-subsea/bottle.json'))" && echo JSON_OK
JSON_OK
```

No `at` on any node. No `via` or `at` on any branch or source, per the brief.
`units.q` is present because the `rate` needs it.

## 6. Round 1 — check

```
$ export PYTHONPATH=src PYTHONIOENCODING=utf-8
$ python -m thermodraw check examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Clean on the first draft. 10 labels is 5 nodes + 4 branches + 1 source, which
is the count from the file, so nothing was dropped.

**The library never refused the file.** It did not refuse it here and it did
not refuse it at any later point. The chain is a ladder — every node joins at
most two others — so the solver placed all five unaided, and no node ever
needed an `at` and no branch ever needed a `via`. There were no findings, so
there were no remedies to apply, and nothing to report on whether a remedy
works when applied literally. That is a real gap in this brief's evidence, and
I have said so in `findings.md`.

## 7. Round 1 — describe

`check` grades the drawing; it cannot say the drawing is the one I meant. So:

```
$ python -m thermodraw describe examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: canvas 1454 x 146, 10 labels

placements: ground x1, node x5, symbol/conv x1, symbol/diss x1,
            symbol/mixed x1, symbol/pipe x1, symbol/spread x1, wire x10

network:
  board --spread-- flange
  flange --pipe-- vchead
  vchead --conv-- bore
  bore --mixed-- sea
  source 0 --diss-> board

nodes:
  board          free     at (200, 150) solved
  flange         free     at (480, 150) solved
  vchead         free     at (790, 150) solved
  bore           free     at (1100, 150) solved
  sea            fixed    at (1400, 150) solved

elements:
  branch 0 board->flange symbol/spread   (340, 150)        above         118x50   Bolted joint spreading | R_spread = 0.30 K/W | q = 60 W
  branch 1 flange->vchea symbol/pipe     (635, 150)        above         100x33   Vapour chamber | R_pipe = 0.02 K/W
  branch 2 vchead->bore  symbol/conv     (945, 150)        above         102x33   Oil-filled gap | R_conv = 0.08 K/W
  branch 3 bore->sea     symbol/mixed    (1250, 150)       above         136x33   Housing wall and sea film | R_wall = 0.15 K/W
  source 0 -> board      symbol/diss     (90, 150)         above          85x33   Converter stage | P_d = 60 W
  node 'board'           node            (200, 150)        above          68x33   Power board | T_b = 37 °C
  node 'flange'          node            (480, 150)        above          85x33   Spreader flange | T_f = 19 °C
  node 'vchead'          node            (790, 150)        above         117x15   Vapour chamber head
  node 'bore'            node            (1100, 150)       above          70x33   Housing bore | T_hb = 13 °C
  node 'sea'             node            (1400, 150)       above         108x33   Seawater at 1800 m | T_sea = 4 °C
  wall of node 'sea'     ground          (1400, 162) a90   (no label)
EXIT=0
```

Read against the brief line by line, this is the diagram I meant: the chain in
the brief's order, with the brief's mechanisms and the brief's numbers. Every
node is marked `solved`. Every label went `above`, and not one is marked
`flipped`, `pushed` or `OVERLAPS`, so nothing was shoved anywhere. `q = 60 W`
is on the spreading branch and nowhere else, which is what I intended.

Two things I noticed here and wrote up: the element-name column truncates
`vchead` to `vchea`, and the `nodes:` block gives no sign that `vchead` is the
node with no temperature — the one fact that decides what `--physics` can do.

## 8. The physics check

```
$ python -m thermodraw check --physics examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vchead' has no temperature); vchead (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
```

Exactly what §3 predicted. One node of four. No `node-does-not-balance` and no
`rate-does-not-match`: `board` balanced — 60 W in from the source, 18 K over
0.30 K/W out — and the `rate` I stated agreed with its ends.

I worked the rest out by hand, since the tool would not: 60 W through
0.02 K/W is 1.2 K, so the chamber head is at 19 - 1.2 = 17.8 C; 17.8 - 13 =
4.8 K over 0.08 K/W is 60 W; 13 - 4 = 9 K over 0.15 K/W is 60 W. Every link
carries exactly 60 W. The brief's numbers close all the way down.

## 9. The probe — what the note actually costs

To turn "I think the numbers close" into evidence, I copied the file, gave
`vchead` the temperature its own chain forces, ran `--physics` on the copy,
and deleted the copy. The copy is **not** the diagram and is **not**
committed. No number from the brief was changed, in the copy or in the file.

```
$ sed 's/{"id": "vchead", "label": "Vapour chamber head"}/{"id": "vchead", "label": "Vapour chamber head", "sub": "vc", "value": "17.8"}/' examples/gallery/14-subsea/bottle.json > examples/gallery/14-subsea/_probe.json
$ python -m thermodraw check --physics examples/gallery/14-subsea/_probe.json
examples/gallery/14-subsea/_probe.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
$ rm examples/gallery/14-subsea/_probe.json
removed
```

All four free nodes balance. So the chain is perfectly consistent, and the
only thing standing between the shipped diagram and a silent `--physics` is
one junction temperature nobody quoted.

**I chose to leave the note standing**, which the brief permits provided I say
why. The reason: 17.8 C is a *result*, not a stated property, and putting a
result on the page as though it were quoted is exactly what this diagram is
meant not to do — the same instinct that made the housing wall `mixed` rather
than a made-up split between steel and film. A diagram that states only what
is known, with a note admitting what could not be checked, is the more honest
artefact. The full argument is §5 of `findings.md`.

## 10. Render

Once clean, and only once clean. I did not open the SVG to look at it, per
the brief.

```
$ python -m thermodraw render examples/gallery/14-subsea/bottle.json -o examples/gallery/14-subsea/bottle.svg
examples\gallery\14-subsea\bottle.svg (88,798 bytes)
EXIT=0
$ ls -l examples/gallery/14-subsea/
total 100
-rw-r--r-- 1 Peter Cetner 197121  1111 Sep  3 17:33 bottle.json
-rw-r--r-- 1 Peter Cetner 197121 88841 Sep  3 17:34 bottle.svg
-rw-r--r-- 1 Peter Cetner 197121  4841 Sep  3 16:59 brief.md
$ head -c 300 examples/gallery/14-subsea/bottle.svg
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1454.2 146.2" width="1454.2" height="146.2" role="img"><style>@font-face{font-family:"ThermoDraw Sans";font-style:normal;font-weight:400;src:url(data:font/woff2;base64,AAEAAAAOAIAAAwBgR0RFRgOPA2kAAEn8AAAAOkdQ
```

The `head` was to confirm the fonts came out embedded and the viewBox matched
the canvas `describe` reported, not to look at the picture. 1454.2 x 146.2
against `describe`'s `canvas 1454 x 146` — they agree.

## 11. Writing the record

`rounds.md` was written from the outputs above, with the model and harness on
its first line as required, and the final `check --physics` output pasted
verbatim at its end. `findings.md` was written last.

```
$ wc -l examples/gallery/14-subsea/rounds.md
134 examples/gallery/14-subsea/rounds.md
```

The first attempt at `findings.md` was a single heredoc of about 230 lines and
the harness cut it off mid-file:

```
/usr/bin/bash: -c: line 145: unexpected EOF while looking for matching `''
```

That is the harness's ~140-line limit on one Bash command, not anything to do
with ThermoDraw. Rewritten as three appends:

```
$ wc -l examples/gallery/14-subsea/findings.md
82
183
282
```

## 12. Final verification

Re-ran both checks on the finished file, to be sure the text pasted into
`rounds.md` is what the current file actually produces:

```
$ python -m thermodraw check --physics examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vchead' has no temperature); vchead (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
EXIT=0
--- and plain check ---
$ python -m thermodraw check examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

Byte-identical to what `rounds.md` carries.

## 13. Summary of the session

- **Check rounds: one.** Clean first draft — 0 errors, 0 warnings, 0 notes.
- **Did the library refuse the file? No**, never. The solver placed all five
  nodes unaided; the file contains no `at` and no `via` anywhere.
- **Final status:** `check` exits 0 with nothing at all; `check --physics`
  exits 0 with one `physics-not-checked` note, left standing on purpose and
  argued for in §5 of `findings.md`.
- **Remedies applied:** none, there being no findings. This brief tests the
  schema, not the checker.
- **Files written:** `bottle.json`, `bottle.svg`, `rounds.md`, `findings.md`,
  `transcript.md`, all under `examples/gallery/14-subsea/`.
