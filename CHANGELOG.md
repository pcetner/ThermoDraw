# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`thermodraw check` — is this diagram any good, answered without looking at
  it.** The library's premise is that a model can be handed `docs/schema.md`
  and emit something drawable, and that was tested directly: an agent with no
  other context produced correct, valid diagrams on the first run with no
  traceback. They were also ugly, and every aesthetic failure traced to the
  library rather than the author. Worse, the only way to find them was to
  render, serve over HTTP, open a browser, screenshot and look — five
  sequential steps, while 134 golden tests passed green throughout. Goldens
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

  It reports; it does not judge, and always exits 0. Keeping the judgement in
  `check` alone is why that command's summary line can stay one trustworthy
  sentence. Like `check`, it reads `render.compose`'s own `Scene` rather than
  rebuilding the page. `describe(diagram)` from Python, `.describe()` on a
  builder, `thermodraw describe file.json` from a shell, `--json`.

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
