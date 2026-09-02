# What five agents found, in a clean room

The second run of the gallery, and the first one whose reading restriction
held. Five briefs, five agents, `docs/schema.md` and nothing else — no
`CLAUDE.md`, no design record, no tests, no goldens, no finished diagram to
copy. `RERUN.md` is the protocol; this is what it produced, graded against the
outcomes that protocol wrote down before the run. The first run, which leaked,
is kept as `FINDINGS-first-run.md`.

| | run on | model | harness | from |
|---|---|---|---|---|
| all five | 2026-09-01 | `claude-opus-5` | Claude Code, general-purpose subagents, in parallel | clean-room commit `df3a92f`, a `git archive` of `c95b816` with the files `RERUN.md` lists removed |

The clean room was a sibling directory of this checkout, not inside it, so no
ancestor `CLAUDE.md` could be loaded. Each agent's transcript is committed
beside its diagram as `transcript.md`, one commit per agent. Every command in
them is recorded with its output, and every `check` run reproduces against
this tree: all five SVGs are byte-identical to fresh renders of their JSON.

| | diagram | rounds to exit 0 | standing notes | `check --physics` |
|---|---|---|---|---|
| 01 | `satellite.json` | 9 | — | 4 warnings |
| 02 | `house.json` | 4 | `parallel-pair-same-side` | 2 warnings |
| 03 | `dewar.json` | 3 | `parallel-pair-same-side` ×2 | 2 warnings |
| 04 | `rack.json` | 5 | — | 4 warnings |
| 05 | `diode.json` | 2 | — | 2 warnings |

## The pre-registered outcomes

`RERUN.md` named four ways the run could go, before it went. All four went the
way that counts as a finding.

**The vocabulary claim fails, in every domain.** Each agent reported things it
could not express and had to approximate, and each ranked them by how badly
the drawing lies as a result. The one gap the protocol expected to recur —
active, pumped heat — did, in 03 and 05. Everything else in the list below is
new. What is *not* on it is also the result: of the first run's nine gaps,
eight shipped as symbols and fields, and no agent asked for any of them again.
`phase`, `spread`, `flow`, `count` and `mixed` were each used for exactly what
they were built for, and three agents said so unprompted. The second run's
gaps are not glyphs. They are things the data model cannot state.

**The documentation claim fails.** 01 needed nine `check` rounds, three past
the limit the protocol set, and every one of the nine was about label
placement. Four of the five asked a question the schema should have answered
and had to guess: whether `rail` and a node's `label` are optional, which
units `--physics` accepts, whether `rate` on a counted branch is per item, and
which of two contradictory sentences about `flow` to believe. One complaint
was unanimous: the schema's second paragraph says the `render` output "draws
nothing" without a theme step, and all five agents could not tell whether the
`render` *command* they were told to run would produce a file that draws.
It does; the CLI applies the theme. Two words — "from Python" — close it.

**The remedy claim fails.** Applied literally, as the briefs required:

| | applied | cleared its finding | made the next report strictly worse | not applicable as written |
|---|---|---|---|---|
| 01 | 15 | 9 | 3 | 2 |
| 02 | 1 | 0 | 0 | 1 |
| 03 | 6 | 2 | 2 | 1 |
| 04 | 7 | 3 | 2 | 3 |
| 05 | 2 | 2 | 0 | 0 |
| | **31** | **16** | **7** | **7** |

Better than the first run's 6 of 18, and for a reason the table shows: the
remedy that works is "move the source further from its node with `at`", and
05 hit nothing else. The seven that could not be applied are two defects in
the checker, below, not seven judgement calls. Three agents converged only by
abandoning the remedies for a restructure the finding never suggested — and
in each case the restructure cleared everything at once, which says the
findings were describing one geometric mistake as several label problems.

**The run was clean**, with two caveats worth recording. `docs/schema.md`
quotes `examples/hero.json` in full and its `describe` output, so "no
finished diagram" was not strictly true: every agent had one worked example,
and 03 found it actively misleading (below). And the user's global
instructions file, which names browser tooling and nothing about this
project, is loaded into every session and cannot be excluded by the recipe.
No transcript shows a file read beyond the brief and the schema; 02 built a
probe file in a scratch directory outside the repository to test a hypothesis
rather than open `src/`.

## What the vocabulary cannot say, second set

Ranked by how many briefs hit it and how badly the drawing misleads.

**The format cannot say that two elements are related — 5 of 5.** No ids on
branches or sources, no groups, no cross-references. It is one hole with five
faces. 03's two-stage cryocooler is one machine and can only be two unrelated
`flow` sources; nothing says stage 2's lift is a load on stage 1. 03's current
leads conduct and dissipate, and become a branch and a source with no link.
05's 80 W and its 800 W/cm² are the same joules stated twice, and with no
`area` and no cross-reference the agent drew both, so the junction now shows a
balance that deliberately does not close — the only place in the five where
the picture asserts something false rather than omitting something true. 05's
TEC has a 60 W pumped and a 40 W consumed on two unrelated elements, so its
COP is unwritable. 01's survival heater has a 30 W rating and a 0 W value, and
the rating went into label prose.

**A fluid stream has two temperatures; a node has one — 2 of 5.** 04's
technical water enters at 30 °C and leaves at 38 °C. Three shapes were tried
before any JSON was written; the one taken puts 38 °C in the data and 30 °C
in prose, and the closed return leg does not exist in the diagram. 02 found
the other face of it: `flow`'s direction is the heat's, so infiltration — a
185 W loss — must run `gf → out`, and the chevrons point *out* of the house,
the opposite of the sentence the brief spends two lines on. Undetectable to a
reader.

**No quantity outside `R C T P q q″` — 4 of 5.** No area, dimension, flow
rate, emissivity or ΔT. 01's heat pipe is specified as 0.4 K at 220 W, which
is how heat pipes are specified; divided into `0.00182 K/W` it becomes a
linear conductance the physics check extrapolates to 12.6 kW. So the
first run's "isothermal link" gap is half closed: the `pipe` symbol exists,
and the quantity a heat pipe is quoted in still does not. 02's "dominant loss
per unit area" was dropped outright, there being nothing to approximate it
with. 05's 100 µm → 10 mm spread, the reason the spreader exists, survives as
fanning hatch lines and a word.

**No way to mark a number a capacity, a limit, or provisional — 3 of 5.**
03's 35 W and 1.5 W are what the stages *can* lift, not what arrives; both of
its physics warnings follow from that and nothing in the file can say so. The
checker's own remedy text — "if a flow is a capacity rather than a load, say
so in the `label`" — is the library conceding the point in prose. 05
generalises it: `--physics` is opt-in because a sketch with placeholder
numbers is a diagram too, and the file has nowhere to record which of its
numbers are placeholders.

**Nothing marks a branch as active — 3 of 5, and the one gap expected.**
`flow` was the right choice for a Peltier, a pumped loop, a stairwell. It
carries direction and a rate. It cannot say the branch does work: 05's TEC
moves 60 W from 41 °C to 48 °C and renders identically to a physically
impossible passive link.

**Missing kinds and structures.** Boiling and condensation (04: drawn as the
same `R_conv` as the dry cooler's air side). A thermal bridge (02: a steel
lintel quoted air-to-air had to be `mixed`, so the one path the brief calls
dominant says "mechanism unstated"; `cond` would have been a lie). Enclosure
or nesting (03: a dewar is concentric, and the drawing is a chain). `count`
for *different* paths in parallel (03: a cryostat stage is three unlike
paths, so the comb, the condensed form and the page control are unavailable
to the commonest cryogenic figure there is). `count` with an aggregate value
(01: "heat pipes", one ΔT, no pipe count). An operating case (01: "in
sunlight, not eclipse" has nowhere to go but the undrawn `title`). A control
element (01: the thermostat is absent). Non-thermal power leaving a node
(05: 120 W of light, ranked last by the agent that lost it).

## Where the documentation failed

Line numbers are in `docs/schema.md` at `c95b816`. Each was checked.

- **Lines 12–15, the `render`/`theme` paragraph** — 5 of 5, unanimous. It is
  about the Python function and does not say so. Every agent grepped its own
  SVG for the `:root` block to find out whether the file it was about to
  commit would draw.
- **Line 426, "heat carried from one node to another by a moving fluid has no
  branch kind yet"** — stale since `flow` shipped as a branch, and it sits
  200 lines under the table that documents the branch. 02 had to choose which
  half of the page to trust before drawing either of the two features that
  most needed it.
- **Line 250, "`at` only has to be roughly right"** — wrong in the way that
  matters. A source's `at` sets its lead, the lead is an obstacle other labels
  are pushed around, and 01 traced three findings to it, including one where
  moving a source further out *on the tool's instruction* lengthened the lead
  into a collision. 03: automatic placement is 38 units from the node, which
  for a 123-wide label is not "room for its label", and two auto-placed
  sources on one node overlapped.
- **Line 449, "a unit the check does not know skips the diagram"** with no
  list — 4 of 5. The check knows `K/W`, `°C/W`, `C/W`, `mK/W`, `K/kW` for
  resistance and `W`, `kW`, `mW` for power (`_physics.py:38`); it never reads
  a capacitance, and it never scales a temperature, since only differences
  are used. So 01's `18000 J/K` and 04's `240000 J/K`, written in place of
  the briefs' `18 kJ/K` and `240 kJ/K` to be safe, bought nothing but six
  digits on the page. The failure mode the sentence names is silence, which
  is why they hedged.
- **The hero as the only worked example** — 2 of 5, decisive there. It shows
  none of `spread`, `flow`, `flux`, `break`, `count`, `rate`, `phase`,
  `pipe`, `mixed` or `corner`; 05 needed four of those and assembled its
  `flow` branch from three prose paragraphs that never show JSON. 03 found
  the hero misleading in a specific way: "leave a node sideways before
  turning" is stated for the end a branch leaves, and the hero then drops
  straight down *onto* its ambient node, which works only because that node
  has no other traffic. Copying it was the root cause of four findings.
- **Unstated:** whether `rail` and a node's `label` are optional (02 invented
  four labels and a 2771 px canvas rather than risk a dropped one); whether
  `rate` on a counted branch is per item (04 left the per-processor 400 W off
  the page rather than guess — the code reads it as the whole group's,
  `_physics.py:208`); what `--physics`'s tolerance is; what `describe`'s
  `flipped`, `pushed N` and `OVERLAPS` mean; and that supplying `rate` opts a
  branch into `rate-does-not-match`, so the incentive as documented is to
  leave it off.

## What the library got wrong

Each of these was found by an agent that could not read the source, and each
was confirmed against it afterwards.

1. **`--physics` skips a node silently when a neighbour has no temperature.**
   `_physics.py:170`: a path to a node with no stated `T` sets `known = False`
   and the node is dropped without a word; the same at line 125 for the node
   itself, and at 133 for a `flux` source. The schema documents the `fixed`,
   `phase` and `flux` skips and not this one, and the trigger is the idiom the
   schema recommends for layered assemblies — interior junctions with no
   temperature. 02 proved it by experiment: `gf`, the worst-balanced node in
   its system at 1.47 kW in against 693 W out, is not mentioned in the output.
   05 counted: of eight nodes, two reported, three silently skipped, and a
   reader would conclude they passed. Both asked for one line, `5 of 8 nodes
   checked, 3 skipped`. This is the most actionable thing in the run.
2. **A wire's remedy names a `via` the branch cannot have.** `_check.py:240`
   says "move a `via` waypoint on {branch}" for any branch wire. 01 got it
   twice on a straight run with no `via`; 04 got it three times on a
   `count: 8` branch, which the schema says cannot take `via` at all — and a
   counted group is wide, so it is exactly what labels collide with. The
   source case was already special-cased at line 237; the branch cases were
   not.
3. **`wire-through-symbol` offers `via` for a source's lead.** `_check.py:740`
   is a fixed string; 01 was told to route a source around with a field the
   source table does not have.
4. **`parallel-pair-same-side`'s remedy is a fixed string.** `_check.py:810`:
   "set `side` to \"down\" on the lower of the two", not re-derived from the
   file. 02's pair both already carried `"side": "down"` and the lower one was
   the lower one; the remedy was a no-op and the note survived it. With three
   parallel branches and two usable sides, it only rotates which pair is
   reported — 02 and 03 each proved the cycle — and the one escape, `side:
   "right"`, puts the label along the wire into the next node for two errors
   and four warnings. Neither the note nor the `side` table says left and
   right are meaningless on a horizontal run. Both agents left the note
   standing, deliberately, and were right to.
5. **A counted source prints "8 in parallel".** `_layout.py:399` passes a
   source's `count` through `count_text(count, "parallel")`; the schema says
   sources "simply add, so there is no `arrangement` to state". Eight
   processors are not in parallel. 04 left it, because removing `count` would
   delete "400 W each, eight of them" from the data to fix a wording bug.
6. **`label-adrift` cannot say the label is too wide.** 04's `sat` label is
   192 wide between runs of 260, so it is 48 too wide on both sides. The
   finding blamed the neighbour on one side, then the other, with the
   overshoot at exactly 48 both times; the named remedies moved neighbours
   and changed nothing, and `angle` made it 84. `nodes-too-close` speaks in
   the right terms and did not fire for those runs. Two of 04's five rounds
   went to proving a remedy had no effect.
7. **`describe`'s `network:` block omits what the agents most needed to
   verify.** Sources are absent from it (01, 03, 05: "if I had attached the
   heater to the wrong node the block would be byte-identical"). Direction is
   invisible on the one directed branch kind — `coil --flow-branch-- tw`,
   symmetric dashes, and written backwards it would look the same (all four
   that used `flow`). Parallel groups collapse to `gf --mixed/mixed/flow-branch--
   out`, so the two paths easiest to swap cannot be told apart, and
   `j --cond-- ihs` gives no hint of eight paths. `rate` appears only inside
   label text. The `elements` table does carry direction, as `source 1 shield
   ->`; the block where you would look does not.
8. **The label solver is non-local, and nothing says so.** 01, round 4: freeing
   one source let another's label travel 160 units across a 1234-wide canvas
   onto a different branch's label. "The single most important thing to know
   before laying out a diagram with more than four elements on a node."

Cosmetic but consistent, 4 of 5: on a Windows cp1252 console, `check` and
`describe` print characters outside the codepage as `\uXXXX` escapes
(`__main__.py:84`) and the rest raw, so `ε` is escaped and `°C` is not. Two
agents re-captured their `--physics` output under `PYTHONIOENCODING=utf-8`.
Under `--json` on that console the escapes happen to be valid JSON, but the
stream is the console's encoding, not UTF-8.

## The physics

All five fail `check --physics`, 14 warnings between them. No agent changed a
diagram to quiet it, independently and for the same stated reason: the
numbers are the brief's, and retuning a resistance to please a tool would be
falsifying data. Four of the five did the arithmetic by hand before writing
any JSON and predicted the warnings they later got. Every warning is a
contradiction inside a brief — 01's gasket at 0.05 K/W cannot drop 33 K at
220 W; 04's CDU cannot pass 4 kW at 12 K over 0.0019 K/W — and `RERUN.md` said
in advance that if this happened it would be a fact about the briefs, not the
agents. It is. The briefs' numbers were written to read well, not to close,
and the next set should be written to close.

Two things the check did right are worth as much as the list above: it folded
`count: 8, arrangement: parallel` exactly as documented, proven by 04's hot
half balancing; and it folded a `flow` branch and a `diss` source into one
correct 100 W balance at 05's TEC hot face, which one agent called the tool
doing something genuinely hard, correctly.

## What this changes

The first run's headline was that the symbol set was short by nine. Eight of
those shipped, and this run did not ask for them again. Its headline is
different: every one of the 23 rounds across the five agents was a layout
round, and not one concerned whether a diagram said the right thing — the
network layer is the whole of the iteration cost — and the gaps that remain
are in what the format can *state*, not what it can draw. Ids and relations
between elements, quantities beyond the six the units block knows, a
capacity-versus-load distinction, an inlet and an outlet on a stream. Those
are schema decisions, and each one is now backed by a transcript in which
someone needed it.

The cheap fixes are items 1 to 5 above and the first two documentation lines.
None needs a design decision, and all of them were reached by an agent
working from the schema alone, which is the reader they would be fixed for.
