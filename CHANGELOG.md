# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`at` is optional: the ladder solver.** A node without coordinates is
  placed. What is placed is a chain — every node joined to at most two
  others by branches, which is the shape nearly every network in this
  notation has — from the hot end, left to right on one line, each run as
  wide as the labels on it need and never narrower than the 220 the schema
  always recommended. Widths are measured through the same `compose` the
  renderer uses, so the arithmetic `nodes-too-close` reports is done
  before the drawing instead of after it. Two branches between one pair of
  nodes go above and below with leads at each end and their labels on the
  outer sides; a repeated branch keeps the straight run; a source without
  `at` sits half a run out along its angle, and an angle-0 source on any
  node but the hot end is turned to arrive from above. Anything that is
  not a chain is refused naming the node that joins three others, so
  nothing is drawn badly in silence. Explicit `at` is kept and the next
  node measured from it. It is a pre-pass on a copy in `_solve.py`, so
  `layout` is still the seam, `describe` marks a solved node `solved` on
  its row, and `thermodraw solve` writes the file back with every node
  placed, to edit from. Written with every coordinate removed, the hero
  checks clean; so do the battery, cryostat, subsea and immersion-rack
  diagrams from the gallery, and the four that are not chains are refused
  by name.
- **A boundary's wall can be turned.** `fixed` and `break` nodes take
  `wall`: `down`, which is what every diagram drew before, or `up`, `left`,
  `right`. A mount that a cold mass hangs from has its wall above, and the
  third clean-room run could not draw that: with the wall always below,
  the strut left through the mount's own hatching, so the agent shipped
  the arrangement it could verify and said so. The renderer's `ground` and
  the occupancy box already took an angle; two literals in `_layout` were
  the whole of "always below". The `wire-through-wall` remedy now names
  the direction that faces away from the offending branch first and `at`
  second, applied and tested in all four directions; with the wall above,
  an automatic label goes below; `describe` says `wall up` on the node's
  row when it is turned. A `free` or `phase` node has no wall and refuses
  the field. Six goldens added, none moved.
- **`units.T` can say which scale it is on.** `K` is byte-identical
  whether the author means absolute kelvin or a rise above ambient, and
  the record listed that among three limits that were not checks. It is a
  declaration now: `"T": {"unit": "K", "scale": "absolute"}` or `"rise"`,
  split on the way in so every reader of `units` still sees text, and
  written back nested. Plain `"T": "K"` stays valid and declares nothing.
  The drawing does not change; `describe` prints
  `temperatures: rise above ambient, in K`; and `--physics` adds one
  note, `rad-needs-absolute-scale`, for a `rad` branch carrying a value
  on a diagram declared as a rise, because a radiation resistance holds at
  a pair of absolute temperatures the page then cannot state. An
  undeclared scale fires nothing. `DiagramBuilder` takes `scale=` as a
  keyword of its own.
- **`symbol-off-its-run`: a branch symbol placed away from the line its own
  wire takes is a warning.** `at` is "where the box sits" and `layout` splits
  the route around it, so an `at` beside the route drew a diagonal jog out to
  the box and back — a path no thermal network has — and nothing looked,
  because every rule asked about labels and crossings rather than about a
  symbol's relationship to its own wire. Measured from the run's line, not
  from the wire, which is `half_len` away either way. The remedy is `at` on
  the route, or a `via` waypoint where the box is.
- **`theme.with_variables` embeds the faces**, as `bake` always did. Every
  clearance `check` certifies is measured in Plex, and the documented path
  for an SVG on the web embedded nothing and fell through to Arial, in which
  the hero's widest label is about five units wider than the solver cleared —
  so a clean report was a claim about a rendering the reader did not get.
  About 78 KB a file, and every gallery render moves by that one block.
  Goldens are unmoved; they are measured before the theme is applied.
- **A branch may not join a place to itself**, and a `corner` refuses
  `label`, `value` and `sub` rather than discarding them.
- **`docs/schema.md` says a finding's `where` is positional**, and so are
  the `td-…` element ids a page builds from it: insert a branch above and
  every later name shifts.
- **The gallery, re-run in a clean room.** `examples/gallery/RERUN.md` was
  run on 2026-09-01: five `claude-opus-5` agents in a copy of the repository
  outside this checkout, with `CLAUDE.md`, the design record, the tests, the
  goldens and every finished diagram removed, from `docs/schema.md` and a
  brief alone, one commit each with full transcripts. The five folders now
  hold that set; the leaked first run is `FINDINGS-first-run.md` and its
  diagrams are at `c95b816`. `FINDINGS.md` grades the run against the
  outcomes written down in advance — all four claims failed, which is the
  finding — and lists what was confirmed against the source: `--physics`
  skips a node silently when a neighbour has no temperature, two remedies
  name a `via` the element cannot take, the parallel-pair remedy is a fixed
  string, a counted source prints "8 in parallel", and the schema's second
  paragraph tripped every agent. Nothing in the library changed in that
  commit; the entries below are what changed because of it.
- **A remedy names only a field the element can take.** `Placement` carries
  `via`, `count`, `arrangement` and `outward` as data beside `role` and
  `ends`, and `_check._move` reads them: a source's lead and the rail move
  with `at` and `rail.y`, a straight branch is told to gain a `via`
  waypoint rather than move one, and a repeated branch's comb — which
  stands a fixed distance out from its nodes — moves nothing, so the remedy
  falls through to the label's `side` or `angle`. `wire-through-symbol`
  asks the same function about the offending wire.
- **`parallel-pair-same-side` names the branch and the side**, derived
  from where the two labels landed, so it cannot name a change already in
  the file. Three or more branches between one pair of nodes get one note
  for the group and no `side`, because none clears it.
- **`label-adrift` says when a node label is too wide for its room**,
  with both numbers and the two nodes to move apart, instead of blaming
  the symbol on one side and then the other.
- **`--physics` reports what it did not check**: one `note`,
  `physics-not-checked`, listing every free node it skipped and why — no
  temperature, a neighbour with none, a `flux` source, a value that is
  not a number — and an unknown unit says which units it knows instead of
  returning nothing. The balance message is ASCII; its em dash printed as
  a replacement character on every agent's console.
- **A counted source reads `each of 8`**, not "8 in parallel".
  `examples/gallery/04-immersion/rack.svg` moves by that label.
- **`describe`'s network block shows sources, direction and counts**:
  `cb --flow-> th`, `j --cond x8 parallel-- ihs`, `source 0 --diss-> j`,
  `th --flow-> source 1`. `to_dict` gains `count`, `arrangement` and
  `directed` per edge and a `sources` list. `_layout.network` returns the
  kind as written, `flow`, not the symbol key.
- **`docs/schema.md`** says what the five agents had to find out: the
  render/theme paragraph is about the Python function and the command
  themes for you; `flow` is a branch; a source's lead is a wire and
  automatic placement assumes one source; the units `--physics` reads;
  `rail` and `label` optional; `rate` under `count`; `left`/`right` on a
  horizontal branch; the arrival end of the sideways habit; the solver is
  not local; `flipped`, `pushed` and `OVERLAPS` defined; both transcripts
  regenerated.
- **`tests/test_clean_room.py`** rebuilds each defect as the smallest
  diagram that produces it and applies the remedy, and replays every
  remedy on the five committed diagrams — and on the same five with their
  authors' `at`, `side` and `angle` removed — asserting `via` is never
  named on something that cannot take it.

- **`check --physics`: do the numbers on the page agree with each other?** A
  prototype, and the first check that reads a value. Ten checks say how the
  drawing reads; none said what it says, while `model` held every number a
  thermal network needs. This is Kirchhoff at a free node from stated values
  only — a resistance between two stated temperatures implies `ΔT/R`, sources
  and flows are what they say, `count` folds a group, a corner folds into the
  path through it — reported as `node-does-not-balance` with every term
  listed, plus `rate-does-not-match` for a branch whose `rate` disagrees with
  its ends.

  Run over the hero and the five gallery diagrams it fired on all six,
  seventeen nodes, and every finding is arithmetic a reader can redo: the
  hero's first branch implies 97 W leaving a node that receives 45; the rack's
  "each of 8 processors" box has no `count` and implies 400 W where 3,200
  arrive; the house's roof loses 190 W and is fed by nothing, because it is
  joined to neither zone — a modelling gap no layout check can see. None of
  the six diagrams' numbers closed; the hero's do now (below). It is opt-in
  and stays so: a sketch with placeholder numbers is a diagram too, and would
  fire at every node it has. Ask for it when you believe the numbers.
- **`examples/gallery/RERUN.md`** — the clean-room protocol for repeating the
  gallery with the `CLAUDE.md` injection actually suppressed, which
  `FINDINGS.md` said to do and nothing had. It cannot be run from inside this
  checkout, for the reason the first run leaked; it says how to build a room
  without the file, what to record, and what outcomes would count as failure,
  written before any run so the run cannot be read as confirming whatever it
  produced.
- **A positioning section in the README.** Nothing in the repository had
  named an alternative. Graphviz, D2 and Mermaid lay out graphs; schemdraw
  draws circuit notation; none says which mechanism a path is or checks the
  drawing. The part not yet built — the solver — is the part most likely to
  be someone else's solved problem.

### Changed

- **`--physics` is no longer called a prototype.** It was labelled one in
  the module, the checker's docstring, the command-line help and the
  schema while its fire rate on real diagrams was being judged. The third
  clean-room run was the judgement: five diagrams whose numbers were
  solved first, and no balance or rate finding on any of them — the first
  pre-registered claim in three runs to hold. It stays opt-in, for the
  reason it always was: a sketch with placeholder numbers is a diagram too.
- **A counted `flow` states its group value.** `model.FOLD` gains a row for
  a rate: in parallel the group carries the sum, `4 in parallel = 40 W`;
  in series every link passes the same heat, so the group carries one
  item's worth. The count line drew nothing for a `flow` before, and the
  schema, `CLAUDE.md` and the record all said that was deliberate; it was
  a missing row. `--physics` reads the same table (see Fixed).
- **Two checks join the solver table.** `wire-through-wall` is a constraint
  on the router and `symbol-off-its-run` is scaffolding — it fires only on
  an explicit branch `at`, which a solver never sets — so the partition
  reads four, two, four, three. The sentence under the table had said
  "delete three" over two rows since it was written; it is right now and
  says that it was not.
- **The hero's temperatures agree with its own power and resistances.**
  112, 78 and 61 °C were not what 45 W through 0.35, 0.15 and 1.80 ∥ 6.40 K/W
  from 40 °C gives; 126, 110 and 103 are. The inputs are untouched — the
  temperatures were the outputs and are recomputed. The README image, the
  schema's worked example and the `demo-hero` golden move with it; nothing
  else does.
- **`CLAUDE.md` is the decisions; `docs/design-record.md` is the argument.**
  The design record was 34KB of essay auto-loaded into every session, written
  so that revisiting a decision read as not having understood it, and it had
  become an instrument rather than a record: stale in three places, arguing
  from constraints that did not support two of its conclusions, restating a
  claim its own evidence had falsified. It is split. `CLAUDE.md` is one line
  per decision, marked **bet** where it is one, with what would overturn it.
  The essays move to `docs/design-record.md`, corrected where the review
  found them wrong and marked where they were, and not loaded into anything.
- **"Boxes, not zigzags" is recorded as a bet, with the reader's reason.**
  The justification had been that a box has room for a texture — an argument
  about drawing. The reader's reason is legibility at thumbnail and print
  scale, where a 0.7-em structural subscript fails and a texture does not. No
  human reader has been asked; the record says what one would settle.
- **The radiation dash means the value holds at one operating point**, not
  that the path is nonlinear on the page. The record had said both, three
  hundred lines apart: a linearised value is linear, and adds like any other.
  What is different about `R_rad` is that it is a result, not a property.
- **The ten checks are partitioned by what survives the solver.** Three are
  constraints it must satisfy, two are objectives it minimises, four are
  unchanged by it, and three exist only because a human places coordinates
  and are unreachable once one does not. The table is in the record, and it
  is the thing the checker-first order was for.

### Fixed

Everything a blind code review found — `tools/clean_room.py --profile
review` hands a reader the code and the tests with no argument for either.
Nine findings, seven of them defects, each reproduced before it was fixed
and each guarded in `tests/test_clean_room.py`. Across the eleven diagrams
no finding changed and no golden moved.

- **`to_dict` was lossy**, on a library whose thesis is that the data is the
  representation. The keep lists named some fields and not others, and
  `_keep` skipped anything falsy, so `count`, `arrangement`, `rate` and
  `side` vanished and so did a node at 0 °C and a branch at `angle: 0`.
  What "the author did not set this" looks like is the field still holding
  its dataclass default, which is why `Branch.angle` defaults to None. The
  one round-trip test used the hero, which uses none of the lost fields.
- **Exit 1 has to mean findings.** `validate` checked everything inside a
  node, a branch, a source and the rail, and nothing above them: `"size":
  "big"` reached the renderer and exited 1 through Python's own handler,
  the code the command line documents as *findings*, so a script gating
  on the status read a crash as a diagram with warnings. `"units": "K/W"`
  was reported as "is not valid JSON" about a file whose JSON was fine. The
  top level is validated — `size`, `units`, `nodes`, `branches`, `sources`,
  `rail` — NaN and Infinity are refused, and `__main__` keeps a net under
  whatever is left that answers 2, because a crash is no answer.
- **The canvas is sized for the larger form, and a form is its text too.**
  The hidden label of a repeated group was solved against nothing and
  measured by nothing, so an eight-way group's expanded label sat above the
  canvas top and the root `<svg>` clipped it the moment a reader pressed
  the control that exists to show it. It is solved against the page and
  measured into the canvas, and it does not claim a place in the occupancy:
  an invisible label must not push a visible one. The test that should have
  caught it skipped anchors, which is the placement carrying the label.
- **`--physics` kept a second copy of the fold** that knew about resistances
  and not rates, so four correct 10 W loops in parallel into a 40 W sink
  were reported as a node that does not balance, at both ends. `model.FOLD`
  is the one table and the checker reads it.
- **`describe` unescapes a subscript** where `sym_text` had escaped it, so
  an ampersand in a `sub` reads as typed.
- **`py.typed` is honest.** Every public entry point is annotated, which
  made mypy check those bodies and surfaced 112 errors at
  `--check-untyped-defs`; 87 were one cause, the `**who` spreads, which are
  `Dict[str, Any]` because a heterogeneous spread into a dataclass is not
  checkable. Both levels are clean and CI runs the stricter one. Stale
  claims corrected on the way: `symbols.py` said six of twelve symbols, two
  comments asserted a shared footprint `_layout` had given up, and
  `CLAUDE.md` and `ci.yml` both said 91 mypy errors when there were 112.

### Removed

- **`corner`, the node kind that drew nothing.** A coordinate so that a wire
  had somewhere to bend. Fifteen agents in three clean-room runs never drew
  it, including the one whose brief was written to force it; the two
  readers who reached for it wanted a named junction and got a kind that
  lost the name. It put routing into the topology — `describe` hid it,
  `check` skipped it when counting labels, and `--physics` had to fold the
  two resistances through it into one before it could balance anything —
  and everything it did is done by things that already existed: a bend is
  `via`, and a junction between two paths is a `free` node with a `sub` and
  no `value`. A file that names it is refused with that advice, not with
  "unknown kind" beside a list it used to be on. The one committed diagram
  that used it, the run-3 reference solution for the subsea bottle, now has
  a free node at the junction with the temperature the brief's numbers
  give it, and still closes under `--physics`. `Dictionary.html` loses its
  one entry with no drawing.
- **Python 3.9.** It reached end of life in October 2025. The floor is 3.10
  and the CI matrix runs 3.10 to 3.13; no source changed for it.

## [0.3.0] - 2026-09-01

Five symbols, three schema fields, three CLI subcommands, a dictionary, and
an outside review that found the label text unescaped. The review's own
record is `claude.ai/code/artifact/db16bd4b-8839-4214-a29a-e87924bb7169`.

### Added

- **Guards for each class of defect the review found**, chosen because each
  would have caught something that shipped. Every rendered scene must parse
  as XML, and a hostile label is rendered and paged in the suite. A CI job
  rewrites every golden with `--update-goldens` and diffs the tree — that
  flag writes and then *skips*, so on its own it could never fail, and
  nothing had ever checked that the goldens were reproducible. Another
  re-renders the gallery and the README images and diffs them; two gallery
  renders had gone stale with nothing to say so. `gen_dictionary --check`
  is a named CI step like `gen_docs --check`, for the reason that step's own
  comment gives. `mypy` runs in CI, since the wheel ships `py.typed` and
  asserts it; it found one wrong annotation. `tests/scenes.py` fails rather
  than skips when `examples/` is present and the demo scenes did not import,
  which is how the three most complex scenes in the suite could have vanished
  silently. `docs/schema.md`'s vocabulary — every field, kind and quantity —
  is pinned to the model. The `page` subcommand has tests; it had none.
  `label-collision` and `parallel-pair-same-side` have negatives. Four tests
  that could not fail now can. Python 3.13 is in the matrix, and a
  deprecation raised from inside the package fails the run.
- **`Dictionary.html` — the page for someone who has not drawn one of these
  before.** `docs/symbol-reference.html` is the design record: eight
  orientations of each glyph and the argument behind every choice. It answers
  "why is it drawn this way", which is not the question a reader arriving at
  the vocabulary for the first time has. This one answers "what does this
  mean, and when would I use it": each symbol once, at 0°, with a plain
  description and one short scenario.

  Generated by `tools/gen_dictionary.py`, for the reason the reference sheet
  is. Every drawing comes from `symbols.card`, so the picture is whatever the
  library actually emits, and the build refuses to run if the library grows a
  symbol the generator has no entry for — adding a glyph breaks this page
  until someone writes down what it means.

  `corner` gets an entry too, and an empty dashed plate where the others have
  a drawing. It is a node kind that draws nothing, and two acceptance readers
  reached for it when what they wanted was a labelled free node; a reader who
  cannot find it here will assume it does not exist.

- **`thermodraw check` — is this diagram any good, answered without looking at
  it.** The library's premise is that a model can be handed `docs/schema.md`
  and emit something drawable, and that was tested directly: an agent with no
  other context produced correct, valid diagrams on the first run with no
  traceback. They were also ugly, and every aesthetic failure traced to the
  library rather than the author. Worse, the only way to find them was to
  render, serve over HTTP, open a browser, screenshot and look — five
  sequential steps, while the whole suite — 134 tests, 23 of them goldens —
  passed green throughout. Goldens
  pin bytes; they notice that something moved and can say nothing about
  whether it should have.

  Eight findings, from `label-collision` and `symbols-overlap` (errors)
  through `label-adrift`, `label-in-a-corridor`, `wire-through-symbol`,
  `off-canvas` and `frame-off-centre` (warnings) to
  `parallel-pair-same-side` (a note, because the hero breaks it and is fine).
  Two of them are the executable form of a paragraph `docs/schema.md`
  previously offered as advice. Every finding names the schema field that
  fixes it, and each remedy is tested by applying it and asserting the
  finding goes away.

  `check(diagram)` from Python, `.check()` on a builder, `thermodraw check
  file.json` from a shell — exit 0 clean, 1 with findings, 2 unreadable.
  `--json`, `--strict`, `--quiet`.

- **`thermodraw describe` — is this the diagram you meant?** The half `check`
  could not cover. Both acceptance agents, given only `docs/schema.md` and no
  other context, asked for the same missing thing without being prompted: the
  checker says nothing collides and cannot say the drawing is the one they
  intended. This reports element counts by kind, the canvas, every node with
  its kind and place, and the direction each label went — including `flipped`
  and `pushed N` where the solver had to work for it. The hero's parallel pair
  is directly visible in it, both labels reading "above", rather than only
  being graded by a note.

  It prints what each label reads, not only where it sits. Without that a
  description cannot tell a 41 J/K mass hung on the right node from one hung
  on the wrong node — the geometry is identical and only the words differ,
  which makes the words the one thing worth printing. It also prints the
  rail: `rail.reference` is documented as inert, recording which node the
  rail *is* and doing nothing, so this is the only place it can ever be
  checked against what was meant.

  It reports; it does not judge, and always exits 0. Keeping the judgement in
  `check` alone is why that command's summary line can stay one trustworthy
  sentence. Like `check`, it reads `render.compose`'s own `Scene` rather than
  rebuilding the page. `describe(diagram)` from Python, `.describe()` on a
  builder, `thermodraw describe file.json` from a shell, `--json`.

- **Five symbols, closing most of what the gallery found.** `flow` for a
  branch that carries a rate instead of presenting a resistance, `spread` for
  a path whose cross-section grows as the heat goes, `pipe` for a near
  isothermal link, `mixed` for a mechanism that is combined or deliberately
  unstated, and `phase` for a node whose temperature a phase change holds.

  `flow` is chevrons in the line, not a box. The interior of a box states what
  the heat is crossing, and in transport nothing is crossed — the medium is
  going. Boxes resist; arrows carry. It is also the first **directed** branch,
  and `angle` is refused on one: turning the symbol would let the arrow
  contradict `from` and `to`, and the drawing must not be able to disagree
  with the data.

  `mixed` is the one kind whose mechanism the library does not know, so its
  subscript is the caller's to set. An empty interior is not an absence in
  this vocabulary — it is the statement.

- **`rate`, `count` and `arrangement` on a branch; `count` on a source.**
  `rate` is what a path actually carries beside the resistance it presents,
  which is the entire subject of a cryostat heat-load budget and previously
  had nowhere to go but the free-text label.

  `count` draws the repetition — fanned out in parallel, or end to end in
  series — and **requires `arrangement`**. Eight 0.0275 K/W paths are 0.0034
  in parallel and 0.22 in series, a factor of sixty-four, so a count on its
  own is a wrong answer waiting to be read. The value is per item; the library
  does no arithmetic, because values are strings and folding a count would
  mean parsing them as numbers.

  Above three the drawing condenses to two and an ellipsis, taking the room of
  two rather than of sixteen. Each form is a complete, independently centred
  drawing of the group — its own copies, its own wire, its own label — so the
  condensed one is genuinely smaller rather than the full one with holes in
  it. The canvas is sized for the larger form either way, which is what keeps
  expanding a group from reflowing everything else on the page.

  A trunk runs either side before the fan begins, because lanes radiating
  straight out of a node cross the space its own label wants — every
  default-placed group reported `label-adrift` until that was added.

- **`thermodraw page`, and `page(diagram)`.** The same SVG inline in a
  self-contained HTML document, fonts embedded, nothing fetched, plus a
  control for each repeated group. `render` stays canonical: Word, the README
  and every rasteriser need a static file and none of them run script. SVG was
  never what blocked interactivity — a *file* is, and inline SVG in a page is
  fully scriptable by its host. Both forms ship in the markup with stable
  content-addressed ids, so the control swaps a class rather than rebuilding
  anything, and the script lives in the page and never in the picture.

  The copies fade in from the middle outwards, each with a delay `render` sets
  from how far it sits off the centre line, so a group appears to run open. It
  is a fade and not a transform on purpose: a transform would drag the group's
  wires off the nodes they connect to.

  A parallel group is drawn as a comb — a trunk out of each node, a riser
  square across it, then one lane per copy — rather than a diagonal fan, which
  read as janky above about four lanes. The condensed form puts an ellipsis
  between the two copies it shows, running along the branch: an ellipsis means
  "and more of these" in the direction it runs, and stacked across the lanes
  it read as a decoration rather than as an omission.

  Each form carries its own label and fades with it. The visible one used to
  sit in the shared label list, which left it stranded in the middle of the
  other form after a swap.

- **`describe` prints the network.** Which nodes are joined to which, and by
  what — the thing three of five acceptance readers named as its single
  largest omission. Built the same way `network-in-pieces` builds it, so the
  two cannot disagree.

- **`network-in-pieces`, the tenth check.** Two of the five gallery diagrams
  are severed in half and passed everything else: a two-phase loop whose
  halves are joined only by a `flow` annotation at each end, and a stack whose
  Peltier stage is drawn the same way. Nothing in either file relates the two
  arrows except that the same number was typed twice.

  Over nodes joined by branches, not over wire segments. The hero's own wire
  graph is in two pieces — a source's lead and a node's boundary stub are
  legitimately separate ink — so a check on wire connectivity would condemn
  the flagship. A `break` branch counts, though it carries no heat: this
  finding is for a path the author meant to draw and did not, and a break is
  the opposite, an explicit statement that nothing flows there.

  Its remedy names the cause, because the cause is a gap in the vocabulary: a
  source has one end, so no arrangement of `flow` annotations can join two
  nodes.

- **`nodes-too-close`, the ninth check.** Every label finding names what is
  *nearest* the crowded label, and on a short run that is a wire — so the
  author is told to move a `via` when the spacing is what is wrong, and no
  amount of routing fixes spacing. An acceptance reader followed that advice
  into a dead end. This names the cause: the two nodes, how far apart they
  are, and what the labels along the run add up to.

  It needs both halves. The arithmetic alone over-reports, because labels
  stack at different heights and their spans along a run can overlap without
  the blocks touching — a four-stage ladder at 180 sums to 187 and is
  completely clean. The push alone under-explains, because a waypoint rising
  out of a node crowds a label just as hard and moving the nodes apart would
  not help. So it fires only when a label was actually pushed *and* the
  labels do not fit, and only on straight runs, since a routed branch has
  more room along its path than the line between its endpoints.

- **Heat leaving a node: `from` on a source, against `to`.** The acceptance
  reader was asked to annotate the flux leaving a cell's top face and could
  only draw arrows pointing into it — the one thing it was asked for and
  could not express.

  It needed no new geometry and no glyph change. Every source symbol already
  draws its tail at `-half_len` and its head at `+half_len`, so direction is
  only which end the lead attaches to and which side the default offset goes:
  far side and join the head, or near side and join the tail. `flux` is the
  one that shows why — its hatch band *is* a surface, and its note has read
  "several arrows leaving a surface" since the symbol was designed, so
  joining the tail stands that surface against the node with the arrows
  rising off it. `{"from": "cell", "kind": "flux", "angle": 270}` draws it
  and needs no coordinates.

  Only `flow` and `flux` may. `diss` is dissipation appearing at a node
  rather than travelling to it, and `radin` is radiation *arriving*; an
  outbound one would be a symbol whose own name contradicts it, and what is
  actually wanted is a `rad` branch to a boundary. The error says so.

- **A `break` **branch** kind.** The node kind leaves a wall floating: an
  acceptance agent drawing a fibreglass standoff got a labelled boundary with
  nothing tying it to the thing it was bolted to, because every branch kind
  drew a resistance or a capacitance. This draws the open circuit — wire,
  crossbar, gap, crossbar, wire. Deliberately not a plain wire, which would
  say heat flows, and not a resistance, which would say how much. It names no
  quantity, so it takes no `value` and no `sub`, and one given a value is
  refused with a message that says why. Same word as the node kind, same
  meaning, other position.

- **A command line.** `[project.scripts]` was missing entirely.
  `thermodraw check`, `thermodraw describe` and `thermodraw render`, argparse
  and stdlib only, so
  `python -m thermodraw` works from a checkout with no install. SVG only —
  PNG needs a rasteriser, and the library has no dependencies.

- **`Symbol.reach` and `Symbol.ink`.** `half`/`half_len` are clearance for the
  label solver, and six symbols draw outside them: a box symbol runs `LEAD`
  past each end, a capacitance draws ±40 against a `half_len` of 15. Mid-route
  those leads lie over wire the canvas already counts, which is why it never
  showed; at the end of a run they were clipped off silently. `reach` is set
  only where the geometry exceeds the clearance, and `ink` falls back, so the
  two stay one measurement wherever they agree.

- **`render.Scene` and `render.compose`.** `draw` computed the occupancy,
  solved every label against it, and dropped it on the floor. `compose`
  returns it, along with the rectangles, the ink bounds and the canvas.
  `draw` keeps its `(parts, rects)` contract; a rect is now a `LabelRect`,
  which still unpacks as four numbers and compares equal to the plain tuple,
  and additionally knows its owner and what the solver did to place it.

- **`Placement.ref`.** Every placement names what produced it — `node 'j'`,
  `branch 2 j->c`, `source 0 -> j`, `rail` — wires included, which is what
  lets a check exclude a branch's own lead from "what is nearer to this label
  than its owner". A string rather than the model object: holding a `Node`
  would alias mutable state into a documented-pure output.

- **`core.gap`, `core.box_bounds`, `core.segment_box`, `Occupancy.blocker`,
  and a `report` out-parameter on `core.annotate`.** Each is the informative
  half of a predicate that already existed: `_overlap` is now `gap(...) < 0`
  and `free` is `blocker(...) is None`, so there is one SAT formula and one
  skip rule rather than a diagnostic that will eventually disagree with the
  decision it explains. `report` carries `side`, `solved`, `used`, `flipped`
  and `clear` — the last of which is `False` when the push loop ran out of
  steps and accepted an overlap, which it has always been able to do silently.

- **`tools/golden_diff.py`.** A golden is one long line, so `git diff` marks
  the whole file changed for a one-number edit, which makes
  `pytest --update-goldens` a rubber stamp. This splits both sides into
  element tokens and reports how many were added, removed and moved.

- `tests/test_check.py`, `tests/test_frame.py`, `tests/test_cli.py` and
  `tests/test_describe.py`. The suite goes 134 → 322.

- **`side` on nodes, branches and sources.** `core.annotate` has taken an
  explicit label side since the occupancy work, and `layout.Label` has carried
  the field, but the model had nowhere to write it — so the override existed
  in Python and was unreachable from a diagram written as data. A parallel
  pair is where it is missed: both branches are horizontal, both labels choose
  "up", and the lower one lands inside the loop. Accepts `auto` (the default,
  and the previous behaviour exactly), `up`, `down`, `left`, `right`.

### Fixed

- **A label is text, not markup.** Nothing escaped what an author wrote
  before it reached `<text>`, so a label of "Fins & fans" produced a document
  that no conforming XML parser would open — Word, cairosvg and librsvg among
  them — and a label of `</svg><script>…` became live script in `thermodraw
  page` output. The page's *title* had been escaped and tested from the start;
  the labels, subscripts, values and units all went round it.

  `core.build_block` now escapes the author's strings, and `core.sym_text`
  escapes a subscript before wrapping it in the one `<tspan>` a label
  legitimately carries. Both run ahead of measurement, and `core.text_w`
  unescapes before it sums advances, so the solver clears the glyph the
  renderer draws. That replaced a regex that counted every entity as one
  double-prime-wide glyph — dead while no label carried an entity, and a third
  of an em wrong the moment one did. `describe` reports a label as the author
  typed it, which is also what the drawing now shows; it used to unescape.

  No golden moved: nothing in the corpus had ever put `&`, `<` or `"` in a
  label, which is the kind of input this library was built to receive and had
  never been given.
- **A node called `a->b` severed its own branches.** `Placement.ref` is a
  string for people — `branch 0 a->b`, `node 'j'` — and its own docstring
  said so: "a diagnostic, not a key". `check` and `describe` both used it as
  a key anyway, recovering endpoints by splitting on `->`, so an id
  containing that dropped its branches on the floor: `check` reported a
  connected diagram as two pieces, with a remedy, and `describe` printed no
  edges at all. `hot side` and `o'clock` survived only by luck.

  `Placement` now carries `role` ("branch", "source", "node", "rail") and
  `ends` — the ids at its ends — as data, set by `layout` and read by both.
  The network itself is built once, in `_layout.network`/`pieces`, so the
  checker's `network-in-pieces` and the description's `network:` block cannot
  disagree; they used to be the same algorithm written twice, and
  `describe`'s docstring promised they could not diverge. The ref string is
  unchanged in format, since `render.variant_id` hashes it into the DOM ids
  a page holds. `network-in-pieces` now reports `node 'x'` as its `where`,
  like every other finding, rather than a bare id.

  Validation, in the same change: a coordinate or angle must be *finite*
  (`nan` rendered `width="nan"`, a blank document, and passed); an id must
  be non-empty and may not be `rail`, which is the reference rail's name and
  was silently taken for it; and a source's `count` goes through the same
  check a branch's does (`count: 0` drew one; `count: "many"` died in
  `layout` with a `TypeError` naming no source). Deliberately nothing else
  about an id: no code parses one out of a string any more, so there is
  nothing to defend.
- **`theme.bake` rewrote `var(--x)` wherever it found it, labels included.**
  A label reading "Sink var(--ink)" came out as "Sink #16181d". The
  substitution now stops at `</style>`, which is the only place the library
  writes one. Its `#000` fallback for a name it did not know is gone too: a
  renamed palette key used to come out black-on-black in dark mode while the
  custom-properties path stayed correct, and only a rendered pixel could tell.
  Every variable `symbols.CSS` uses is now checked against every palette at
  import, an unknown one raises with its name, and the `:root` block is
  generated from `PALETTES` rather than kept as a third and fourth copy by
  hand. (`--panel` is written `#ffffff` where it was `#fff`; nothing else
  moves.)
- **A file that was not UTF-8 crashed the CLI with exit 1**, which is the
  code that means "findings". `UnicodeDecodeError` is a `ValueError`, not an
  `OSError`, so `_load`'s handler never saw it — the exact failure `io.py`'s
  docstring is written about, unhandled on the read side. It exits 2 now and
  says which byte. Files are read as `utf-8-sig`, because PowerShell writes a
  BOM and the file is no less UTF-8 for it.
- **`render -o -` and `render -o file.svg` produced different bytes.** The
  CLI wrote files itself, typing the XML declaration out a second time,
  while `io.save` — "the one place in the library that writes a file" — was
  bypassed. Both paths go through `save` now, and stdout gets the
  declaration the file always did.
- **`tools/subset_font.py` was not reproducible.** fontTools stamps
  `head.modified` with the current time unless told not to, so two runs over
  the same TTFs gave two different woff2s, in a repository that pins its
  fonts and its width table to each other byte for byte. Both font tools
  now say which release of IBM Plex they read, and the next regenerated
  `_metrics.py` records it. The vendored fonts themselves are unchanged.
- **The documentation contradicted the code in fourteen places, and itself
  in two.** The README captioned eighteen symbols as twelve, promised "exit 1
  with findings" directly under a report that exits 0, and described a
  rosette of four textures as every symbol at every angle. `docs/schema.md`
  said a `break` refuses `sub` and accepts `rate` — it is the other way
  round — named the two source kinds that may point away and then listed the
  two that may not, and carried a `describe` transcript assembled by hand,
  with `nodes:` twice and `network:` missing; it is the real output now.
  `CLAUDE.md` cited `errors="replace"` as the rationale for a line that uses
  `backslashreplace` and argues against `replace` by name, still listed a
  spreading-resistance symbol as "the one gap in the vocabulary" nine commits
  after it shipped, and counted 134 goldens where there are 23 — 134 was the
  whole suite. `FINDINGS.md` said §6 was untouched with eight of its nine
  items fixed by a commit whose message says so. The gallery README
  described a reading protocol its own findings file discloses did not hold,
  and counted two unclean diagrams where there are three. `__init__`'s usage
  example saved a file that draws nothing, because `render` emits custom
  properties with no fallback. The README's test count was wrong and is
  removed rather than corrected: a number that changes with every added test
  is a contradiction waiting to happen. The five gallery briefs no longer
  hardcode the author's home directory. And the network layer is no longer
  named "0.3" in three places — one of them a validator error users read —
  because this is 0.3.0 and it is not in it.
- **The remedies were wrong more often than they were right.** Five agents
  drawing five thermal networks applied them literally, as instructed. Six of
  eighteen worked; three made the drawing worse. Every fault was in the change
  that claimed each finding "names the schema field that fixes it", and three
  agents hit them independently.

  `angle` was offered for every element and means three different things — the
  schema's own tables say so. On a branch it overrides the direction taken
  from the wire, so following the advice laid a conduction box diagonally
  across its own wire and the checker then reported the diagram clean. It is
  now offered only for a node's label, the one element where it means what the
  remedy says.

  `via` was offered on sources, which have no such field: a source's lead is a
  wire carrying the source's ref, and the validator refuses `via` outright.

  `side` was offered without consulting the occupancy that produced the
  finding — telling a node to try left or right when those were the directions
  its branches left in, and on a vertical branch naming the two sides that lie
  *along* the wire. `core.free_sides` now asks the same question `annotate`
  asks of a candidate, of all four sides, built from the same `clear_offset`,
  `_corner` and `Occupancy.free`, so it cannot drift from the placement.

- **`parallel-pair-same-side` could be silenced by its own remedy.** It
  skipped any pair whose labels both had an explicit `side`, so setting
  `side` — which is exactly what it tells you to do — removed the pair from
  the check whether or not it had helped. A false clean is worse than a
  missing check, and a note is already something you may ignore. It now
  reports where the labels actually landed, however they got there.

- **A node with no value and no subscript drew a bare italic `T`,** and
  nothing objected. Interior junctions between series layers routinely have no
  temperature of their own; two readers fell back to `corner`, which draws
  nothing and loses the name. Such a node now draws its label alone. A
  subscript still produces `T_mid` with no number, which is what a symbolic
  diagram wants.

- **A waypoint on a rail branch now frees the space it promised.** The rail
  end dropped from the node whatever the route did, so a `via` bought a
  detour that came back to the same place — making `docs/schema.md`'s claim
  that waypoints are "how you free up the space directly under a node" false,
  and costing one reader a full re-layout. It now drops from the last
  waypoint.

- **The symbol sheet documented a glyph the library cannot draw.**
  `docs/symbol-reference.html` is what `CLAUDE.md` calls the visual
  specification, and `g_break` showed a wire stopping short, a crossbar, and a
  wall standing *across* the branch, with no node circle at all. The data
  pipeline draws a break as circle, gap, horizontal wall below — matching a
  fixed node minus its stub, which is what the distinction has always been.
  Neither boundary glyph is reachable from `layout` (`render.place` runs only
  for `element == "symbol"`), so the two arrangements drifted with nothing to
  say so. `g_break` is redrawn to match, its `reach` re-measured against the
  real markup, and `tests/test_check.py::TestBreakNode` now pins the glyph and
  the pipeline to each other.

- **An unknown source kind with a value raised `KeyError`.** The bare-value
  check ran before the source-kind check, and `_valued()` yields sources, so
  `QUANTITY[kind]` was reached with a kind that does not exist. Nodes and
  branches validate their kinds earlier, so only sources were exposed. It is
  now a `DiagramError` naming the kinds that do exist.

- **`tests/test_frame.py` under-measured a nested transform.**
  `transform="translate(0,24) rotate(90)"` composes as T·R, so a point is
  rotated first and then translated; the helper applied them left to right.
  Every `translate(...) rotate(90)` boundary wall landed in the wrong place,
  and the fixed node's 24-deep wall measured 12 — under-measuring, which is
  the direction that fails silently. With it corrected, every symbol's
  `reach` matches its drawn ink exactly.

- **A `break` node drew nothing.** `layout` on one returned a single `node`
  placement — byte for byte what a `free` node produces — so `g_break` was
  unreachable from the data pipeline and a distinction CLAUDE.md calls
  "topological rather than decorative" rendered as no distinction at all. A
  break now emits its wall, and deliberately no stub reaching it: the visible
  gap is the whole point of having two symbols.

- **The canvas reserved room the drawing does not use.** `extent` took
  `hypot(half_len, half)` isotropically — 44.9 around a conduction box that
  draws 16 across — and a flat 30 around a boundary wall that draws 13 deep,
  downward only. The hero therefore sat 17 units high in its own frame, and
  no golden could ever have said so, because the frame had always been wrong
  and the bytes never changed. `render.bounds` measures each placement
  anisotropically; `WALL_HALF`/`WALL_DEPTH` name what `ground` actually draws.
  Moves one golden, `demo-hero.svg`, by one number: 447.8 → 430.8 in height,
  0 elements added, removed or moved.

  A node stays `±radius` on purpose. A fixed node's `half=22, half_len=19` are
  clearance numbers for the label solver, and substituting them would reserve
  22 units above a 5.5 circle and count the wall twice.

- **The boundary wall was invisible to the label solver.** Ground placements
  fell through all three branches of the occupancy loop, so a label could be
  placed on a wall with nothing objecting. They are registered now, as the
  oriented box the wall actually occupies — which hangs off its anchor rather
  than straddling it.

### Changed

- **Two branches laid across each other are one `wire-through-symbol`, not
  two.** Both directions were reported, and both were true: each one's wire
  really is inside the other's box. They are one place on the page and one
  thing to fix, and moving either clears both, so it now reads as a crossing
  rather than as two separate trespasses.

- **A source with no `at` now follows its own `angle`.** The default placed
  it to the left of its node whatever `angle` said, so turning a source
  without also giving coordinates put the symbol beside the node and ran the
  lead across the page. It is now offset along the direction the arrow
  points. Identical for `angle: 0`, which is every source in the repo.

- **`describe` keys its rows on placements rather than on labels, and gives
  each one its position and angle.** `compose` skips a label with nothing to
  say, so an element carrying no text had no row at all — a `break` branch
  names no quantity by design, and one with no `label` vanished into the
  counts. It now gets a row marked `(no label)`. For a source, which way it
  points is the whole of its meaning, and it could previously only be
  inferred from where the label landed. The JSON `labels` key becomes
  `elements`, with the label's own fields nested under `label`.

- **The command line softens output with `backslashreplace`, not `replace`.**
  The quantity for a heat flux is `q` followed by U+2033, and on a cp1252
  console the old setting printed `units names 'q?'` — an error naming a key
  the reader cannot copy, about a character they had most likely just
  mistyped. It now prints `q″`, which is ugly and recoverable.

- **Every quantity is its own symbol, `q″` included.** `radin` and `flow` are
  both powers and share `units.q`; a heat flux is per unit area, is not
  measured in the same thing, and now reads `units["q″"]`. They shared one
  entry, so a diagram carrying a heat rate in `W` and a heat flux in `W/cm²`
  could label only one of them — while `docs/symbol-reference.html` had been
  showing `q″` and `1.4 W/cm²` all along, an arrangement the pipeline could
  not produce. `model.SOURCE_SYMBOL["flux"]` matches. The accepted `units`
  keys are derived from the table, so the key set and its error message
  updated themselves, and no diagram in the repo uses `flux` at all.

- **A default-placed source no longer crowds its node.** `layout` put every
  source at `half_len + 5.5`, which considers how long the symbol is and never
  how tall. That suits the three arrow kinds; `flux` is a 52 × 48 block, and
  at that offset it blocked the node's label from below while the source's own
  label blocked it from above — both candidate sides gone, so `annotate`
  pushed rather than flipped and the checker called it adrift. The offset now
  buys room in proportion to the symbol's height and leaves the arrows exactly
  where they were. No constant can be universally right here, because whether
  a label fits depends on its width and labels are not solved until `render`;
  the docstring says so.

- **A remedy names the field that fixes *this* case.** `label-collision` and
  `label-adrift` carried one fixed string offering `side`, `angle` and `via`
  whatever was in the way. For a source crowding its node the answer is `at`,
  and it was not in the list — the same defect an acceptance agent hit when it
  was told to "set `side`" at a node with all four sides already taken. The
  remedy now depends on the culprit: a `via` waypoint for a wire, `at` for a
  symbol or a node, `side` for two labels, and `angle` once the solver has
  tried both sides of the branch.

- `docs/schema.md`, from the five-domain gallery run. `size` was referenced by
  two findings and defined nowhere, in a page whose opening line calls itself
  "the whole format". Branch `value` is now documented as optional. The Angles
  section now says outright what its table only implies: symmetry about 180°
  means no `angle` sends a node's label *below* the line, and `side: "down"`
  is the only thing that reaches there.

- `docs/schema.md`, from a third acceptance run — a fan-out topology rather
  than a ladder, drawn from the page alone, clean on the first `check`. Three
  things it had to guess at and now does not: that the flux units key is `q`
  followed by U+2033 and not two quote marks; that `at` on a source is the
  centre of the symbol, that `angle` turns it, and that a source arrow always
  points *into* its node, there being no kind for heat leaving; and what
  `"side": "down"` does on a boundary node, which is safe but snug on a
  `break`. `tests/test_check.py` pins that last one, including the detail
  that the 8-unit push it costs is exactly `ADRIFT` and so is reported by
  nothing.

- `docs/schema.md` gains a **Seeing what got drawn** section for `describe`,
  documents the `break` branch kind, and corrects two things: the sources
  table now shows `flux` reading its own unit, and the claim that a quantity
  used without its unit "simply draws the bare number" is gone. It never did
  — `validate()` refuses it, which is the better behaviour and now the
  documented one.

- `docs/schema.md` gains a **Checking a diagram** section: the command, the
  eight codes as a table, and the note that the two habits above are now
  enforced rather than advised. That page is written to be pasted into a
  prompt, so a model reading it learns both the format and how to verify what
  it wrote.

- `docs/schema.md` also answers what two fresh agents, given the page and
  nothing else, had to guess at — the acceptance test the whole exercise
  exists to pass. Added: an **Angles** section, because `angle` was described
  only as "rotates the node's own frame", from which a reader inferred a plain
  clockwise rotation and was wrong about half the circle (the choice is
  symmetric about 180°, since a label is never set upside down); that y
  increases downward; that `value` is a string and `units` keys are optional;
  that `rail.reference` must name a real node and is otherwise inert; that
  `via` works on a capacitance, which is how you free the space under a
  crowded node; that a `fixed` node need not sit at the rail's `y`; that one
  `q` unit is shared by `radin`, `flow` and `flux`; what the "labels placed"
  count counts; and that a `break` node has to stand alone, because no branch
  kind draws a plain wire. `tests/test_check.py` pins the angle table so the
  page cannot drift from the code.

- `docs/schema.md` documents `side`, the per-kind unit each source reads, and
  two layout habits that were previously only visible by reading `hero.json`:
  turn a `via` clear of the node before going vertical, and set `side` on a
  parallel pair. The old advice — "put parallel paths 80 above and below the
  main line" — led straight into both problems.
- `angle` on a `fixed` node is documented as not turning the boundary wall,
  which it never did.

### Removed

- **The `thermodraw.layout`, `.render`, `.check`, `.describe` and `.page`
  submodules**, renamed `_layout`, `_render`, `_check`, `_describe`, `_page`.
  `__init__` exported a function under each of those five names, so
  `import thermodraw.render as r` silently bound the *function* and
  `r.PADDING` failed a line later — and four modules carried a comment routing
  around it. The public names are unchanged: `from thermodraw import render`
  still yields the function. What breaks is `from thermodraw.render import
  PADDING`, which becomes `from thermodraw._render import PADDING`.
- **`cairosvg` and `pillow` from the `dev` extra**, and the CI job that
  existed to keep them installable. Neither was imported anywhere; the suite
  rasterises nothing. The test matrix installs the extra directly now.
- **Examples no longer write into `build/`**, which is setuptools' scratch
  directory and holds a stale copy of the package. They write to `out/`.
- **`core.LEAD`** — referenced nowhere. `symbols.LEAD = 20` is the one in use,
  and `core.LEAD = 34` shadowing it under the same name was the hazard rather
  than the waste.
- **`Placement.mirror`** — written by nobody and read by nobody;
  `render.place` recomputes it from `sym.mirror`. A field leaving a public
  dataclass breaks anyone constructing one positionally, which is why it goes
  in a release note rather than quietly.

## [0.2.0] - 2026-08-31

0.1.0 was a symbol library: it drew one symbol at a time, at coordinates you
supplied. 0.2.0 makes a diagram a piece of data, makes the render
reproducible, and puts a test suite under both.

### Added

- **A data model, and a pipeline.** `dict`/JSON → `Diagram` → placements →
  SVG, as three pure stages: `model`, `layout`, `render`. The model carries no
  SVG and no geometry beyond the coordinates given to it, so a diagram loaded
  from JSON is indistinguishable from one built in code. `Diagram`, `Node`,
  `Branch`, `Source`, `Rail` and `DiagramError` are the vocabulary.
- **`DiagramBuilder`**, sugar over the same data — anything the builder can
  say is expressible as data.
- **A JSON schema**, `docs/schema.md`, written to be pasted into a prompt.
- **`save()`**, which writes UTF-8 (see *Fixed*).
- **Measured font metrics.** `_metrics.py`, generated per face by
  `tools/gen_metrics.py`, replaces a sixteen-entry estimate table.
- **An embedded font.** Three subsetted woff2 faces ship in the package as
  ThermoDraw Sans; `theme.faces_used` embeds only the faces a given diagram
  needs, so baked SVGs for Word, PowerPoint and rasterisers carry the font
  they name.
- **Diagram-aware label placement.** An occupancy structure carries the placed
  labels, the drawn wires and the symbols. `annotate` tries the automatic side
  of the branch first and the opposite side second, so a blocked label steps
  across the branch rather than drifting off it; only if both are blocked does
  it push out. A `side="up"/"down"/"left"/"right"` override was added.
- **A documentation generator.** `tools/gen_docs.py` builds
  `docs/symbol-reference.html` from the library and a prose template, with the
  per-symbol notes coming from `Symbol.note`. `--check` fails if the committed
  page is not a fresh render.
- **Unit validation**, catching a value with no unit — which used to render as
  a bare number — with an error naming the element and the quantity.
- **An explicit `__all__`**, drawn deliberately around the data, the pipeline,
  the vocabulary and output.
- **102 tests**, where there were none: golden SVGs for all 17 scenes,
  determinism, id uniqueness, the model and its errors, label clearance, the
  font subsets against the width table, and the docs page against a fresh
  render.
- **Three demo scenes and a visual README** — a power-device ladder, a
  twelve-path rosette and a vocabulary sheet, in light and dark. The hero
  renders from `examples/hero.json`.
- **Packaging**: an MIT `LICENSE`, a `NOTICE` recording the OFL-1.1 terms of
  the bundled fonts, and a PEP 561 `py.typed` marker so type checkers read the
  annotations that were already there.
- `.gitattributes` pinning LF, since the goldens compare byte for byte.

### Changed

- **The render is deterministic.** Element ids derive from the element's own
  parameters rather than a module-global counter, so the same diagram renders
  to the same bytes twice in one process. Identical elements therefore share an
  id by design: `canvas()` hoists every `<defs>` block to the front and keeps
  one copy of each, which collapses the rosette from 24 clip paths to 4 and
  takes output 2.7% smaller.
- **Symbols are objects.** Geometry lived in twelve `g_*` functions while the
  extents the label solver needs lived in a parallel dict; both now travel
  together on a frozen `Symbol` dataclass, with fields named rather than
  abbreviated (`g` → `draw`, `val` → `value`, `hl` → `half_len`). The four box
  symbols also expose their interior on its own.
- **Text is measured in the face that will draw it.** The old table assumed
  0.55 for 36 of the 52 glyphs the library emits; measured against IBM Plex the
  mean per-glyph error was 12%, and 98% for `/`. SemiBold runs 4% wider than
  Regular — the same size as the error being removed.
- **Kerning is dropped from the subsets, deliberately.** `text_w` sums advances
  and cannot see a kern pair, so a font without GPOS is the one the solver is
  modelling. It also takes each face from 54KB to 19KB.
- **The canvas sizes itself** to what was actually drawn, which retired the
  regex that rewrote the root tag.
- Segments shared by two branches are stroked once.
- The README leads with the data API.

### Fixed

- **`save()` writes UTF-8.** `conv`, `rad` and `flux` emit an arrow or a double
  prime; `write_text` defaults to cp1252 on Windows, which crashed
  `render_reference.py` outright.
- **Exported SVGs carry explicit pixel dimensions.** `canvas()` emitted
  `width="100%"`, which is right for a page that owns its column and wrong for
  a file loaded through an `<img>` tag.
- **Duplicate ids in one document** — invalid SVG, even where renderers
  tolerate it — no longer occur.
- **Baked SVGs no longer render in Arial** while the clearances assume Plex.
- A capacitance takes an identity subscript from the caller, as `T` does;
  `DiagramBuilder.branch` gained the `sub` it needed.
- A fixed node's label clears its boundary wall rather than a 5.5px circle.
- `docs/symbol-reference.html` was stale — labelled draft 5 against `core.py`'s
  draft 4 — and now cannot go stale silently.
- **`validate()` checks the shape of what it is given.** It verified ids and
  kinds but nothing else, so seven ways of writing a bad coordinate got
  through: six died inside the renderer with messages like `Unknown format
  code 'f' for object of type 'str'` that named no node and no field, and one
  drew the wrong picture in silence. Coordinates, angles, waypoints, rail
  geometry and values are now checked before anything draws, and the error
  names the element and the field.
- **A near-miss key is named and corrected.** An unknown field raised
  `Node.__init__() got an unexpected keyword argument 'name'` — a Python
  internal, the wrong exception type, no hint. It now raises `DiagramError`
  with a suggestion (`'name'` -> `'label'`, `'position'` -> `'at'`,
  `'type'` -> `'kind'`) and the list of valid fields. The flagship input is
  JSON written by a model, so these are the errors that matter most.
- **`save()` no longer prepends an XML declaration to non-SVG files**, which
  turned a written diagram-as-data file into invalid JSON.

## [0.1.0] - 2026-08-31

The baseline, recorded so the changes above are reviewable.

- Twelve symbols, each drawn at any angle.
- Label placement solved from the symbol's oriented bounding box.
