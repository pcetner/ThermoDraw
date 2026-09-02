# Transcript — 03-cryogenic

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

Running log, appended as I go.

---

## 00 — Setup

Read `examples/gallery/03-cryogenic/brief.md` and `docs/schema.md`. Those are the
only two files I read. I did not open `src/`, `tests/`, `README.md`,
`CLAUDE.md`, `CHANGELOG.md`, or any other `examples/` file, and I did not open
an existing `.json` diagram. (I wanted to open `examples/hero.json` to see a
real file rather than the schema's excerpt of it — the schema quotes the whole
hero file inline, so I did not need to, but the instinct is recorded in
findings.)

```
$ cd "$(git rev-parse --show-toplevel)" && pwd && ls
/c/Users/Peter Cetner/Documents/GitHub/ThermoDraw-cleanroom
LICENSE
NOTICE
START-HERE.txt
docs/
examples/
pyproject.toml
src/
```

```
$ ls examples/gallery/03-cryogenic/ && python --version
brief.md
Python 3.11.9
```

---

## 01 — Reading the brief into schema terms

Before writing anything I mapped every sentence of the brief onto a schema
construct. Decisions and the reasoning behind each:

| brief | schema construct | why |
|---|---|---|
| vacuum vessel, 300 K, "held there by the laboratory" | node `kind: fixed`, `value "300"` | schema: `fixed` "draws the boundary wall"; a reservoir held by something outside the model |
| radiation shield, 40 K | node `free` (default), `value "40"` | it has its own balance; not held |
| cold mass, 4.2 K, C = 900 J/K | node `free` + `cap` branch to `rail` | schema: "`\"to\": \"rail\"` … is how thermal mass is hung off a transient model" |
| MLI vessel→shield, 0.9 W, 289 K/W | branch `kind: rad`, `value "289"`, `rate "0.9"` | `rate` is "what this path actually carries" |
| MLI shield→cold, 0.02 W, 1790 K/W | branch `rad`, `value "1790"`, `rate "0.02"` | same |
| G10 struts vessel→shield, 433 K/W, 0.6 W | branch `cond` | solid conduction |
| G10 struts shield→cold, 716 K/W, 0.05 W | branch `cond` | same |
| HTS leads, 1720 K/W conduction | branch `cond`, `value "1720"`, **no `rate`** | the brief never states what the leads conduct, only their resistance |
| HTS leads' 1.2 W Joule heating "deposited at the shield" | `source` `kind: diss`, `to: shield` | schema: `diss` is "electrical or internal dissipation … *appearing* at a node rather than travelling to it" — exactly right |
| instrumentation wiring, 0.15 W, 239 K/W | branch `cond` | |
| stage 1 removes 35 W at the shield | `source` `kind: flow`, **`from: shield`**, `"35"` | schema: "Only `flow` and `flux` may point away"; `diss` cannot take `from`. Heat leaving, so `from` |
| stage 2 removes 1.5 W at the cold mass | `source` `flow`, `from: cold`, `"1.5"` | same |

Key forced choice: **the cryocooler is not in the drawing as a thing.** There
is no branch kind for "an active refrigerator", so each stage is a one-ended
`flow` arrow pointing away from the node it cools. The schema is explicit that
this is all a source can be — "A source has **one end**" — so the two stages
cannot be shown as belonging to one machine. Recorded in findings.

Units: `{"R": "K/W", "C": "J/K", "T": "K", "P": "W", "q": "W"}`. `T` is `K`,
not `°C` as in the hero. The schema says units are free strings appended to
values, so `K` should be accepted; the only warning sign is the `--physics`
note that "a unit the check does not know skips the diagram rather than
guessing", which implies the physics pass has an opinion about unit strings.
Guess: `K`, `K/W`, `W`, `J/K` are all known. To be verified.

No `size` key: the schema says "you almost never want it" and that
`off-canvas` and `frame-off-centre` "exist only for diagrams that set it".
Cheapest way to make two of the ten findings impossible.

---

## 02 — Layout reasoning (before writing any JSON)

Three nodes, but **six** branches between them — three in parallel on each
side. That is the whole layout problem. The hero has one parallel pair and
already needs `via` + `side` on both. I have two groups of three.

Chosen geometry — three horizontal lanes, one node column per temperature:

- main line `y = 340`; upper lane `y = 100`; lower lane `y = 580`; rail `y = 780`
- `vessel` at `x = 200`, `shield` at `x = 620`, `cold` at `x = 1040`
- 420 apart, not the schema's suggested 220, because "Space labels, not
  symbols" and `R_cond = 1720 K/W` plus a second line `q = 0.6 W` is a wide box.

Per group: the middle path runs straight; the upper path leaves sideways at
`x = node+80` then rises to the upper lane; the lower path does the same
downward. Both turn 80 units clear of the node, which is the schema's
"Give the turn 40–90 units of clearance" habit, aimed at `label-adrift`.

Arrival ends drop *vertically* onto the destination node (last waypoint shares
the node's `x`), copying the hero, whose two parallel branches both arrive at
`amb` from directly above and below. That means the space directly above and
below `shield` and `cold` is wire, so their labels cannot go `up` or `down` —
the hero solves the same problem with `"angle": 90`. I use `angle: 135`
(above-left) for both, since above-right is where I want a source.

`shield` has eight attachments — 3 branches in, 3 out, 2 sources — against
four `side` slots. The schema anticipates exactly this: "a node fanning three
ways with a capacitance below it and a source coming in has five attachments
for four slots. Only `angle` reaches the diagonals." So all four cardinal
directions at `shield` are wires and everything else goes on a diagonal.

Sources: I am deliberately leaving `at` off and giving only `angle`, because
the schema says that placement "is usually what you want" and I would rather
find out whether it is true than pre-empt it with coordinates. If `check`
complains I will add `at`.

The capacitance is the one place the geometry fights back. `cold` already has
wire above (upper lane arrives), below (lower lane arrives) and left (middle
path), so a `cap` dropping straight to the rail would run down `x = 1040` on
top of the lower lane's riser. The schema names the fix: "Give it `via` if you
want it somewhere else … which is how you free up the space directly under a
node that already has too much attached to it." So `via: [[1140, 340]]` — step
right, then drop.

`rail.reference`: must be an existing node id. I picked `vessel`. This is
already wrong in a way the schema cannot fix — see findings — because 900 J/K
of cold mass is referenced to absolute zero, not to the vacuum vessel. The
schema says `reference` "is documentary and does nothing", so nothing breaks;
it just says something untrue.

Expected label count: 3 nodes + 7 branches + 3 sources = **13**.

---

## 03 — Round 1: first `check`

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 1 error, 4 warnings, 2 notes
error: [symbols-overlap] source 0 -> shield and source 1 shield -> overlap by 1  -> move one of them with `at`
warning: [label-adrift] node 'cold': ... pushed 156 ...
warning: [label-adrift] source 0 -> shield: ... pushed 132 ...
warning: [label-adrift] source 1 shield ->: ... pushed 136 ...
warning: [label-in-a-corridor] branch 4 shield->cold: ... 48 from the opposite path and 50 tall ...
note: [parallel-pair-same-side] branch 0 / branch 1
note: [parallel-pair-same-side] branch 3 / branch 4
EXIT=1
```

(Full verbatim output is in `rounds.md`; this log records the reasoning.)

Two things I learned immediately and could not have known from the schema:

1. **A source with no `at` is placed 38 units from its node.** `describe` gave
   me shield at (620,340) and source 0 at (593,367). The schema promised
   placement "with room for its label" and said this "is usually what you
   want". Two sources on adjacent diagonals of one node therefore overlapped by
   1 pixel, and their 123-wide and 99-wide labels were both shoved 130+. So the
   schema's advice to omit `at` is only safe for a node with **one** source.
2. **`describe` is the tool that actually explains `check`.** `check` says a
   label was "pushed 156"; only `describe` tells you where anything is, how
   wide each label is, and which way it went. I ran `describe` before touching
   anything and would not have got anywhere without it.

## 04 — Round 2: applying the printed remedies literally

The brief requires the named remedy first, so I applied all six verbatim (table
in `rounds.md`). Result: **2 of 6 cleared, 3 got worse, 1 is unfixable.**

Reasoning about why:

- The two that cleared (`symbols-overlap` → `at`, `label-in-a-corridor` →
  `side`) are findings whose cause really is the thing the remedy names.
- The three `label-adrift` remedies all say some variant of "move it further
  away with `at`". That treats a crowded label as a local problem. It is not:
  moving a source away from its node walks it into whatever else is out there,
  and the push went 132 → 160 and 136 → 156, with one escalating to a
  `label-collision` **error**. The remedy made the report worse.
- `parallel-pair-same-side`'s remedy ("set `side` to \"down\" on the lower of
  the two") is **circular** for three parallel branches. Setting branch 1 to
  "down" simply moved the note from the pair (0,1) to the pair (1,2). The
  finding is written for two branches and the library has no idea it is looking
  at three.

I also decoded the corridor metric from the round-1 numbers, which is not
documented: branch 4's box was 164 wide at `x=830` (span 748–912) and the loop's
riser was at `x=700`; 748 − 700 = 48, the number reported. So
`label-in-a-corridor` measures the **horizontal** gap from the label box to the
loop's vertical riser, and the threshold is about the label's own height. That
told me the fix was to widen the loops, not to move the labels.

## 05 — Round 3: the restructure

Root cause of everything that would not clear: I had routed each off-line
branch so its last waypoint sat directly above or below the destination node.
That is what the hero does, and with the hero's *two* parallel branches it is
fine. With three per pair plus two sources on the middle node, every cardinal
direction at `shield` and `cold` was a wire and there was nothing left for a
label to occupy.

Changes:

- Every off-line branch now turns back to the main line **before** the node
  (`[…, [580, 100], [580, 340]]`), so all three branches of a group share one
  horizontal stub into the node. This is the schema's "leave a node sideways
  before turning" applied at the *arrival* end, which the schema does not say.
- Nodes moved to `x` 200 / 760 / 1320, 560 apart rather than the schema's
  suggested 220, so each loop is 290 wide and the middle branch's label clears
  both risers by 80+.
- **Reordered the lanes by label width.** The middle (straight) branch is the
  only one whose label must live inside a loop, so the narrowest label of each
  group goes there: HTS leads (107 wide, and only 33 tall because it has no
  `rate` line) on the left, instrumentation wiring (124) on the right. The G10
  struts, whose labels are the widest at 144 and 164, moved to the outer lanes
  where their labels sit outside every loop. Nothing physical motivates this
  ordering; it is purely to satisfy the label solver.
- `shield` keeps its two sources in the 360-wide pocket between the two groups'
  risers — the Joule-heating `diss` arrow coming in from above-left at
  `angle 55`, and the stage-1 `flow` arrow leaving straight down at `angle 90`
  with `side: "right"`. `shield`'s own label goes to `angle 45` (above-right).
- The capacitance no longer needs a `via`: with the lanes turning back early,
  the space directly below `cold` is free, so it drops straight to the rail as
  the schema's default does.
- Dropped `rail.span`; the default (extent of the nodes) is right now.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/03-cryogenic/dewar.json
examples/gallery/03-cryogenic/dewar.json: 13 labels placed, 0 errors, 0 warnings, 2 notes
EXIT=0
```

## 06 — Round 3b: trying to clear the two notes

The note's own remedy is circular, so I tried the one thing left: `side` takes
four values, so I set the middle branch of each group to `"right"`. Both notes
cleared and it cost **2 errors and 4 warnings** — on a horizontal branch,
`"right"` pushes the label along the wire into the next node, and `check`
immediately tells you to set it back to "up" or "down". Reverted.

Decision: leave both notes standing. Justification in `rounds.md` and
`findings.md` — with three parallel branches and two usable `side` values,
two of the three must share a side. The schema explicitly blesses leaving this
one ("`parallel-pair-same-side` is a note rather than a warning because the
hero diagram breaks it and is fine").

## 07 — Render and physics

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/03-cryogenic/dewar.json -o examples/gallery/03-cryogenic/dewar.svg
examples\gallery\03-cryogenic\dewar.svg (19,491 bytes)
EXIT=0
```

I did **not** open the SVG in a browser and did not look at the image. I did
read the first 300 bytes to confirm it was not empty, and that showed the CLI
already emits `:root{--sym:…}` — i.e. `render` from the command line applies
the `theme` step the schema tells you to apply by hand from Python. Undocumented
in the schema, and the schema's warning ("Without one of them the file draws
nothing") would have sent me hunting for a flag that does not need to exist.

`check --physics` run once, verbatim output pasted at the end of `rounds.md`,
diagram left alone. Both `node-does-not-balance` warnings are the brief's own
numbers: the cryocooler figures are stage *capacities* (35 W, 1.5 W) and the
loads that actually arrive are 2.85 W and 0.22 W. See `findings.md`.

## 08 — Files written

- `examples/gallery/03-cryogenic/dewar.json` — the diagram
- `examples/gallery/03-cryogenic/dewar.svg` — the render
- `examples/gallery/03-cryogenic/rounds.md` — verbatim check output per round
- `examples/gallery/03-cryogenic/findings.md` — what the schema could not say
- `examples/gallery/03-cryogenic/transcript.md` — this file

No file outside `examples/gallery/03-cryogenic/` was touched.

---

## 09 — Commit

The brief's operational note gives the commit as
`git commit -- examples/gallery/03-cryogenic/ -m "<message>"`. That form does
not work: everything after `--` is a pathspec, so git reads `-m` and the
message itself as filenames and fails ten times over with
`error: pathspec '-m' did not match any file(s) known to git`. The working
order is `git commit -F <msgfile> -- examples/gallery/03-cryogenic/`, with the
options before the `--`.

```
$ git commit -q -F "$MSG" -- examples/gallery/03-cryogenic/
COMMITTED on attempt 1
1fc29fc gallery: liquid-helium dewar with two-stage pulse-tube cryocooler
 examples/gallery/03-cryogenic/dewar.json    |  49 +++++
 examples/gallery/03-cryogenic/dewar.svg     |  24 +++
 examples/gallery/03-cryogenic/findings.md   | 310 ++++++++++++++++++++++++++++
 examples/gallery/03-cryogenic/rounds.md     | 273 ++++++++++++++++++++++++
 examples/gallery/03-cryogenic/transcript.md | 271 ++++++++++++++++++++++++
 5 files changed, 927 insertions(+)
```

Path-scoped, so nothing from the four agents working in parallel was picked up
(one of them, `04-immersion`, landed a commit while I was mid-attempt). No
`.git/index.lock` contention occurred.

This last section is appended after the commit, so it is not in it.
