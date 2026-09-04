Model: claude-opus-5 (Claude Code, running as a subagent). Harness: Claude Code, Bash tool (Git Bash) on Windows 10, Python 3.11.9, `PYTHONPATH=src PYTHONIOENCODING=utf-8`.

# 14-subsea — check rounds

One round. The library never refused the file, and `check` was clean on the
first draft.

## Before round 1 — what I wrote

Read `docs/schema.md` and the brief, and nothing else. The brief's chain is
five nodes:

    board --spread(0.30)-- flange --pipe(0.02)-- vchead --conv(0.08)-- bore --mixed(0.15)-- sea

with a `diss` source of 60 W at the board. Three decisions worth naming:

- The vapour chamber and the oil gap are two different mechanisms with two
  different numbers, so there has to be a node between them. The brief quotes
  no temperature for it, so `vchead` gets a `label` and neither `sub` nor
  `value` — the schema's "interior junctions between series layers routinely
  have no temperature of their own".
- The housing wall to the sea is quoted as one number covering steel and
  water film, and the brief says the drawing should not pretend otherwise.
  That is `mixed`, exactly as the schema puts it: "A window quoted as one
  number for conduction *and* convection is `mixed`." `mixed` is the one kind
  whose `sub` is mine, so it reads `R_wall`.
- `rate: "60"` goes on the spread branch only, because that is the one path
  the brief explicitly says carries the whole 60 W. I did not put a `rate` on
  the other three; they carry the same 60 W in steady state, but the brief
  states it only there.

Per the brief, no node got `at`, and no branch or source got `at` or `via`.

## Round 1

```
$ export PYTHONPATH=src PYTHONIOENCODING=utf-8
$ python -m thermodraw check examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

10 labels is 5 nodes + 4 branches + 1 source, which is the count from the
file. No findings, so no remedies to apply, and nothing to report about
whether a remedy worked when applied literally.

**Did the library refuse the file?** No. It never refused it, at any point.
The solver placed all five nodes unaided — `describe` marks every one
`solved` — so no node ever needed an `at`, and no branch ever needed a `via`.
This is a plain chain: every node joins at most two others, which is the
shape the solver handles.

## describe, round 1

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

Every label went `above`, none is marked `flipped`, `pushed` or `OVERLAPS`.
The network block is the brief's chain in the brief's order.

## The one note I am leaving standing, and a probe

`check --physics` leaves one `physics-not-checked` note (output at the end of
this file). I am leaving it standing on purpose, and the brief asks me to say
why: clearing it means giving `vchead` a temperature, and the brief quotes
none for that junction. Every temperature on the page is one the brief
states.

To find out what the note actually costs, I copied the file, added
`"sub": "vc", "value": "17.8"` to `vchead` alone — 19 - 60 x 0.02 = 17.8 °C,
the value the brief's own numbers force — ran `--physics` on the copy, and
deleted the copy. It is not committed and it is not the diagram:

```
$ sed 's/{"id": "vchead", "label": "Vapour chamber head"}/{"id": "vchead", "label": "Vapour chamber head", "sub": "vc", "value": "17.8"}/' examples/gallery/14-subsea/bottle.json > examples/gallery/14-subsea/_probe.json
$ python -m thermodraw check --physics examples/gallery/14-subsea/_probe.json
examples/gallery/14-subsea/_probe.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
$ rm examples/gallery/14-subsea/_probe.json
```

So the brief's numbers close all the way down the chain — all four free nodes
balance to the last digit — and the only reason the shipped diagram cannot be
told so is one junction temperature nobody quoted. No number was adjusted
either way.

## Render

```
$ python -m thermodraw render examples/gallery/14-subsea/bottle.json -o examples/gallery/14-subsea/bottle.svg
examples\gallery\14-subsea\bottle.svg (88,798 bytes)
EXIT=0
```

## Final `check --physics`

```
$ python -m thermodraw check --physics examples/gallery/14-subsea/bottle.json
examples/gallery/14-subsea/bottle.json: 10 labels placed, 0 errors, 0 warnings, 1 note
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vchead' has no temperature); vchead (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
```
