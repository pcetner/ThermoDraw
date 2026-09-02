# Working transcript — 01-spacecraft

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent)

Appended as I went. Every command is recorded with its verbatim output.

---

## 0. Setup and reading

Read `examples/gallery/01-spacecraft/brief.md` (the task) and `docs/schema.md`
(538 lines, the only documentation I am allowed). Nothing else. I deliberately
did not open `src/`, `README.md`, `CLAUDE.md`, `tests/`, or any existing
`.json` diagram, including `examples/hero.json` — although `docs/schema.md`
quotes that file in full at lines 285-310 and quotes its `describe` output at
lines 468-501, so I effectively have one worked example anyway.

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

---

## 1. Turning the brief into a network

The brief describes nine things. Mapping each onto the schema vocabulary:

| brief | schema |
|---|---|
| TWTA baseplate at 78 °C | `free` node, `value` "78" |
| 220 W waste heat | `diss` source `to` the TWTA node |
| filled silicone gasket, 0.05 K/W | `contact` branch |
| equipment panel at 45 °C | `free` node |
| panel thermal mass 18 kJ/K | `cap` branch to `rail` |
| constant-conductance heat pipes, ~0.4 K drop | `pipe` branch — **but the schema wants a resistance, not a ΔT** |
| radiator at 22 °C | `free` node |
| second-surface mirror, ε 0.80, 1.15 K/W to space | `rad` branch to a `fixed` deep-space node |
| deep space at -269 °C | `fixed` node |
| MLI, ε* 0.02, 26 K/W to space | second `rad` branch to the same deep-space node |
| solar 45 W absorbed on the radiator | `radin` source |
| Earth IR 12 W onto the panel | `radin` source |
| 30 W survival heater, currently off | `diss` source — **and the schema has no way to say "off"** |

### Decision points

**Heat pipe.** The brief gives a temperature *drop* (0.4 K), not a resistance.
Schema line 131 offers `pipe` as a kind and line 134 says `value` is in
`units.R`. There is no ΔT field anywhere in the schema. So I have to divide:
R = 0.4 K / q. The load through the pipe is the 220 W from the TWTA plus the
12 W of Earth IR minus what the MLI leaks, so q ≈ 220 W. R = 0.4/220 =
0.001818 → I will write `"0.00182"`. I will also set `rate: "220"` on that
branch (schema line 135: "what this path actually carries") so that the
division I performed is visible on the drawing rather than hidden. Recorded
in findings.

**The temperatures do not agree with the pipe.** Panel 45 °C, radiator 22 °C
— 23 K apart — but the pipe between them is stated as dropping 0.4 K. Those
two statements cannot both be true of a single branch. The brief gives no
saddle/evaporator/condenser resistances that would absorb the other 22.6 K. I
am **not** inventing intermediate nodes to make the arithmetic close; I am
drawing exactly what the brief says and recording the inconsistency. Same for
the gasket: 0.05 K/W at 220 W is an 11 K drop, but the TWTA and the panel are
33 K apart.

**Survival heater.** Brief: "It is off in this condition, but must appear on
the diagram." A source has `value` and nothing else — no enabled/disabled flag,
no rating-versus-current distinction. If I write `value: "30"` the diagram
claims 30 W is arriving, which is false. If I omit `value` the 30 W rating
disappears. I chose `value: "0"` with the rating carried in the `label` text:
`"Survival heater (30 W when on)"`. That puts a number on the page through a
label rather than through `value`, which is exactly the thing schema line 36
says the design is trying to prevent. Recorded in findings.

**Thermal mass units.** The brief says 18 kJ/K. Schema line 31: "Units are
fixed per diagram". There is only one capacitance so `"C": "kJ/K"` with
`"18"` would be legal — but schema line 450 says "a unit the check does not
know skips the diagram rather than guessing", and I have no list of known
units. Rather than risk the `--physics` run silently skipping the whole file,
I wrote `"C": "J/K"` and `"18000"`. Same quantity, less readable.

**Emissivities.** ε 0.80 on the mirror and ε* 0.02 on the MLI are given in
the brief and are dimensionless, so they are not one of the six quantities
(`R`, `C`, `T`, `P`, `q`, `q″`). There is no field for a surface property. I
put them in the branch `label` text. Recorded in findings.

**"Heat pipes", plural.** The brief says pipes. `count` + `arrangement`
exists (schema line 171) but `value` is per item (line 183) and the brief
gives one aggregate ΔT and no pipe count. Inventing a count would change the
stated conductance by that factor, so I drew one `pipe` branch. Recorded.

### Layout plan

Heat runs left to right (schema line 325). Deep space is the cold end, so I
put it on the right of the main line rather than off in a corner: the chain
is TWTA → panel → radiator → deep space, all at y = 180, and the MLI path
arcs over the top from the panel to the same deep-space node. That gives each
of the two radiative branches its own approach to the space node — one from
the left along the main line, one dropping in from above — with no shared
wire. Rail along the bottom at y = 400.

Panel node is the crowded one: contact in from the left, pipe out to the
right, MLI leaving upward, capacitance down to the rail, plus two sources
(Earth IR and the heater). That is six attachments. Schema line 359 warns
about exactly this. Plan: the two sources come in diagonally from below-left
(angle 315) and below-right (angle 225), the capacitance drops straight down,
and the MLI `via` leaves sideways to x = 620 before turning up, per the habit
at schema line 365.

---

## 2. Round-by-round work

The nine `check` rounds, their verbatim output and the remedy applied to each
finding are in `rounds.md`, written one section at a time as each round
finished. Rather than duplicate them here, this is the decision log that sits
behind them.

### Round 1 → 2 — applied the first-named remedy of every finding

3 warnings. Two `label-adrift` on the two panel sources, one
`label-in-a-corridor` on the pipe. I ran `describe` before editing, because
the warnings referred to positions I had never written down: it showed the
auto-placed sources landing ~40 units from their node, which is far too close
for a node with four wires on it.

Edits: branch 0 `at` 360→300, branch 3 `at` 900→1000, branch 1 `side`
up→down. Result: 3 warnings → 4. Only the corridor one cleared.

### Round 2 → 3 — two of the named remedies were impossible

Two findings said "move a `via` waypoint on branch 0 twta->panel". Branch 0
is a straight run with no `via` at all. There is no waypoint to move. I fell
through to each finding's second option: `side: "up"` on node panel (dropping
the `angle: 135` I had chosen), branch 0 `at` back out to 380, `side: "left"`
on source 1, explicit `at` [700,320] on source 2. 4 → 1.

The pattern that emerged and held for the rest of the session: **remedies that
move a source's own symbol out with `at` work; remedies that nudge the
*other* object, or that set `side` on a crowded label, mostly relocate the
problem.**

### Round 3 → 4 — pushes are not local

Gave source 1 an explicit `at` [380, 320]. That cleared source 1 and made
everything worse: 1 warning → 1 error + 2 warnings. `describe` showed why —
source 2's 167-unit-wide label, freed by source 1 moving, was pushed a further
160 units up-and-right and landed on branch 2's label at the far right of the
canvas. A label-adrift push can travel most of the width of the drawing.

That 167-unit label is the widest thing in the diagram and it exists only
because of the workaround for the heater being off. The thing the schema could
not express is the thing that cost the most layout rounds.

### Rounds 4 → 7 — the nudge loop

Three rounds of "move source 2 a bit" ([700,320] → [720,350] → [660,350]),
push going 120 → 100 → 48 and never to zero. Moving source 3 out with `at` as
instructed made its own finding *worse* (44 → 160) and promoted it to a hard
error, because a source's lead gets longer as you move its symbol away, and
the lead is itself an obstacle.

`side: "right"` on source 2 finally cleared both of its findings at once in
round 7.

### Round 7 → 8 — went structural

One warning left, the capacitance label sitting in the heater's diagonal lead,
and both named remedies were nudges that had already failed to converge. I
stopped applying them and used the idiom the schema documents at line 275
instead: `via` on the capacitance, to get it out from under an overloaded
node. `"via": [[440, 180]]`. Cleared it, and produced one honest new finding —
`wire-through-symbol`, source 1's lead now crossing the capacitance symbol at
its new home.

### Round 8 → 9 — clean

`wire-through-symbol` named two remedies. The first, "route it around with
`via`", is impossible: `via` is a branch field and this is a source. The
second, "move the symbol along its branch with `at`", worked: branch 4 `at`
[440, 350], sliding the capacitance down its own vertical run below where the
source lead crosses it.

```
$ PYTHONPATH=src python -m thermodraw check examples/gallery/01-spacecraft/satellite.json
examples/gallery/01-spacecraft/satellite.json: 13 labels placed, 0 errors, 0 warnings, 0 notes
EXIT=0
```

---

## 3. Render

```
$ PYTHONPATH=src python -m thermodraw render examples/gallery/01-spacecraft/satellite.json -o examples/gallery/01-spacecraft/satellite.svg
examples\gallery\01-spacecraft\satellite.svg (17,793 bytes)
EXIT=0
```

I did not open it — the brief forbids rendering an image in order to look at
it. I did check by `grep` that the file contains its own `:root` variable
block, since schema lines 12-15 warn that a bare `render` produces a file that
"draws nothing". It does contain one; the warning is about the Python function,
not the subcommand.

```
$ grep -o 'var([^)]*)' examples/gallery/01-spacecraft/satellite.svg | sort -u
var(--ink)
var(--ink-2)
var(--ink-3)
var(--panel)
var(--rule)
var(--sans)
var(--sym)
var(--tex)
```

---

## 4. `check --physics`, once, record only

Output pasted verbatim at the end of `rounds.md`. Four warnings, all of them
real contradictions inside the brief rather than mistakes in the drawing. I did
not change the diagram to satisfy it. Reasoning in `findings.md`.

---

## 5. Things I wanted to read and did not

Recording these because the brief asks for them.

1. **`examples/hero.json`.** Twice, in round 1 (to see how sources are placed
   in practice) and round 4 (to see how a crowded node is handled). I did not
   open it. It turned out not to matter much, because `docs/schema.md` quotes
   the whole file at lines 285-310 and its `describe` output at lines 468-501.
2. **A list of the units the checker knows.** Schema line 450 says "a unit the
   check does not know skips the diagram rather than guessing" and then never
   lists them. I wanted to write `18 kJ/K` and could not risk it, so I wrote
   `18000 J/K`. That is a documentation gap, not a source-reading urge, but it
   is the one place where not being able to look at the code changed what I
   put in the file.
3. **How `at` on a source relates to its lead.** Three rounds went into
   discovering by experiment that moving a source's symbol lengthens its lead
   and that the lead is itself an obstacle for other labels. Nothing in the
   schema says this; line 250 says only "`at` only has to be roughly right",
   which is the opposite of what I found.

---

## 6. Write-up

`findings.md` written last, in six sections, covering the five points the
brief asks for plus a sixth on the `--physics` disagreement. Nothing in it was
reconstructed from memory that is not also in `rounds.md`, which was appended
to at the end of every round.

Final state of the folder:

```
brief.md       (given)
findings.md    (written)
rounds.md      (appended per round; model/harness on line 1, --physics at the end)
satellite.json (the diagram, check exits 0 clean)
satellite.svg  (rendered once, after the diagram was clean; not opened)
transcript.md  (this file)
```

## 7. Commit

One commit, path-scoped to `examples/gallery/01-spacecraft/` so that nothing
from the four agents working in parallel elsewhere in this repository is
picked up.
