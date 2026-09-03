# ThermoDraw

Thermal network diagrams for Python. Emits SVG. No runtime dependencies.

A symbol library and label-placement engine for drawing thermal resistance
networks — the R–C ladders and branch networks used in electronics thermal
design — in heat-transfer notation: hatched boxes carrying a mechanism
texture, not resistor zigzags. The network layer (solving for coordinates you
leave out) is not built yet.

This file is the list of decisions. **The argument behind each one is in
`docs/design-record.md`, under the same heading** — read that before changing
one. It is kept out of this file on purpose: a record that sits in every
context window stops being read as an argument and starts being read as an
order.

## Layout

```
src/thermodraw/
  model.py     the diagram as data — what you write, what an LLM emits
  _layout.py   model -> placements. The one stage the network layer replaces
  _render.py   placements -> SVG. Pure, deterministic, sizes its own canvas
  builder.py   sugar over model.py, holding no state the data cannot express
  core.py      text metrics, transforms, the label solver, occupancy, textures
  _check.py    is the drawing any good? placements -> findings, no SVG
  _physics.py  do the numbers agree with each other? behind --physics
  _describe.py is it the drawing you meant? placements -> prose, no SVG
  _page.py     the same SVG inline in HTML, with its controls
  __main__.py  the command line: `check`, `describe`, `render`, `page`
  symbols.py   the eighteen symbols, plus sheet renderers
  theme.py     CSS variables for web, baked literals and fonts for Word/slides
  _metrics.py  generated character widths — do not edit
  fonts/       the vendored subset, OFL-1.1
tools/
  gen_metrics.py     width tables from the real font
  subset_font.py     the vendored faces
  gen_docs.py        regenerates the symbol reference
  gen_dictionary.py  regenerates Dictionary.html — the prose lives here
  golden_diff.py     what actually changed in a golden, element by element
  clean_room.py      a sibling room, --profile gallery or review
examples/
  hero.json              the README diagram, as data
  render_demo.py         the three README images
  render_reference.py    renders every symbol at every 45°
  gallery/               five networks from five domains, drawn twice; FINDINGS.md is the clean run
docs/
  schema.md              the format, written to be pasted into a prompt
  design-record.md       why each decision below was made — read before changing one
  notation-test/         the two thumbnails that would settle the boxes-vs-zigzags bet
  symbol-reference.html  every symbol at eight orientations, with notes (generated)
Dictionary.html          what each symbol means, and when (generated)
```

Both HTML pages are generated from the library, so neither can show a glyph
the code cannot draw. Their freshness is checked in CI.

## Decisions

Each is a fact about the code unless marked **bet**, in which case the
sentence after it says what would overturn it.

### Pipeline
- A diagram is data: `dict -> Diagram -> placements -> SVG`, pure stages, a
  builder as sugar. Anything the builder can say is a dict.
- **The round trip is lossless.** `to_dict` writes every field the author
  set and none they did not, which is the field differing from its dataclass
  default — not the field being falsy. `count`, `arrangement`, `rate` and
  `side` used to be absent from the keep lists, and 0 °C and `angle: 0` were
  dropped for being falsy.
- Validation covers the top level too: `size`, `title`, `units` and the
  container types. **Exit 1 means findings and nothing else** — a diagram
  that cannot be drawn is refused and exits 2, and `__main__` has a net so
  an unexpected exception cannot reach the shell as 1.
- `layout` is the seam the network layer replaces. It is not named after a
  version number, since 0.3.0 shipped without it.
- Rendering is a pure function of its input; element ids are content-addressed.

### Symbols
- **Boxes, not zigzags — a bet.** The reader's reason is legibility at
  thumbnail and print scale, where a 0.7-em structural subscript fails and a
  texture does not. No human reader has been asked. One thermal engineer shown
  a thumbnail in each notation and asked which mechanism is where would settle
  it either way.
- Uniform 84 × 32 boxes. The interior states what the heat is crossing: four
  textures, one rule. Contact hatches its halves in opposite directions.
- Radiation is dashed because its **value holds at one operating point** —
  the one number on the page that is a result, not a property. Not because it
  is nonlinear on the page: the value is linearised and adds like any other.
- Sources are arrows. Direction is which end meets the node. Only `flow` and
  `flux` may point away.
- A fixed node connects to its wall; a break does not. The gap is the whole
  distinction. `break` is also a branch kind: an open circuit, no value.
- The wall faces `wall`: `down` by default, or `up`, `left`, `right`. A
  mount that holds something from above has its wall above, and run 3 could
  not draw that. `angle` still turns only the label; an automatic label goes
  away from the wall whichever way it faces.
- Boxes resist, arrows carry: `flow` is chevrons in the line. It is the one
  directed branch and refuses `angle`.
- `mixed` is an empty box, and that is a statement. Flux is several arrows.
  `q″` is its own quantity. No colour in the symbol set.
- `corner` is gone. It was a node kind that drew nothing so a wire could
  bend, never drawn in three clean-room runs including the brief written to
  force it. `via` bends a wire; a junction between two paths is a `free`
  node with a `sub`, which says what it is; a 0.3 file naming it is refused
  with that advice. It was the one kind the physics check had to fold away.

### Rotation and text
- Text is never rotated. Textures rotate with their box. Boundary symbols
  mirror past vertical.
- One text block per symbol, one side, never split. User label first, then
  `symbol = value` in one size and weight; the italic marks the variable.
- Subscripts: structural on an R (library-set, names physics); identity on
  T, C, P, q (caller-set, names a place).
- **A label is text, not markup.** `core.build_block` and `core.sym_text`
  escape; `core.text_w` unescapes before measuring. An ampersand in a label
  used to produce a document no parser would open.

### The label solver
- The offset is solved from the symbol's oriented support distance, not
  searched. A replacement must clear a rotated symbol as tightly at 45°; the
  goldens will say.
- `clear_offset` clears a label from its own symbol only; `core.Occupancy` is
  everything else. `annotate` tries the automatic side, then the opposite.

### Repeated paths (`count`)
- `arrangement` is never inferred; it is refused when missing.
- The group's own value is drawn beside the count — `4 in parallel =
  0.4 K/W` — and the per-item value stays exactly as typed. The fold is a
  table, not a formula: a capacitance is the dual of a resistance, a rate
  adds in parallel and is one item's worth in series, `break` states none.
  `--physics` reads the same table. This overturns "the library does no
  arithmetic", which `--physics` had already made half false.
- Each form is a complete drawing; the canvas is sized for the larger,
  **text included**. The hidden form's label was solved against nothing and
  measured by nothing, so an eight-way group's expanded label sat above the
  canvas top and was clipped by the control that exists to show it. It is
  solved against the page and does not claim a place on it.
- A comb, not a fan; the ellipsis runs along the branch; motion is a fade.
- One label per group, on an `anchor` placement that draws nothing.

### The page
- SVG stays canonical; the script lives in the page, never in the SVG. Both
  forms ship with content-addressed ids.

### Checking
- Validation catches diagrams that cannot be drawn; `check` catches ones that
  should not be. It never rebuilds the page — it reads `render.compose`'s
  `Scene`.
- Severity is a claim about the reader: error, warning, note. A rule that
  condemns the flagship is one an author learns to ignore — and when the
  flagship is actually wrong, the fix is the flagship.
- Every remedy is tested by applying it. A remedy names the field that fixes
  *this* case, never a direction the occupancy says is blocked, and never
  a field the element cannot take: a source and a repeated branch are not
  told to use `via`, and the pair note names the branch and the side from
  where the labels landed. Two symbols on one run are told to use `via`,
  not `at`, which cannot clear them. Seven of the clean room's thirty-one remedies
  could not be applied as written; `tests/test_clean_room.py` replays the
  five diagrams and would fail on each.
- Connectivity is over nodes joined by branches, not over ink. A `break`
  counts as joined.
- A branch symbol placed off its own run is a warning: `layout` splits the
  route around the box, so an `at` beside the route draws a diagonal jog out
  to it and back. Measured from the run's line, not from the wire, which is
  `half_len` away either way.
- A branch may not join a place to itself.
- A wire through a boundary node's hatching is a warning. The wall faces
  `wall`, `down` unless turned, so a branch arriving from that side crosses
  it; nothing looked, because a ground carries no `Symbol`. The remedy names
  the `wall` that faces away from the branch first, then `at`. It fires twice
  on run 2's `house.json`, correctly, and that diagram is evidence and stays
  as drawn.
- A placement carries `role`, `ends`, `via`, `count`, `arrangement` and
  `outward` as data; `ref` is for people. Ids are non-empty and not `rail`,
  and nothing else is required of them.
- **The numbers were never checked, and none of the six real diagrams'
  numbers closed.** `--physics` is Kirchhoff at a free node from stated
  values. The hero's do now. It stays opt-in: a sketch with placeholder
  numbers is a diagram too, and would fire at every node it has. It says
  which free nodes it did not check, in one note: a silent skip on the
  neighbour of a node with no temperature hid the worst-balanced node in
  a diagram from the only tool that looks for that.
- `units.T` may declare its scale, `absolute` or `rise`, written as
  `{"unit": "K", "scale": "rise"}`; plain `"K"` declares nothing. The
  drawing does not change; `describe` says it, and `--physics` notes a `rad`
  value on a declared rise, the one reader that cares. It stays a
  declaration, not an inference: a sharp check was tried and fired on a wall
  at −10 °C radiating to sky, which is correct.
- What survives the solver: four constraints, two objectives, four unchanged,
  three scaffolding. The table is in the record.

### Describing
- `check` grades; `describe` reports, always exits 0, reads the same `Scene`,
  keys rows on placements, prints what each label reads. A ground gets a row
  too, named `wall of node 'x'`: where a boundary wall landed was the one
  thing on the page nothing could report.

### Goldens
- No `--update-goldens` commit without `tools/golden_diff.py` output in its
  message and a sentence per moved element. CI regenerates every golden and
  diffs; CI re-renders the gallery and README images and diffs.

### Evidence
- A clean room is built by `tools/clean_room.py`, never by hand, and it
  verifies its own work. `--profile gallery` strips everything that shows an
  answer and keeps the briefs; `--profile review` strips everything that
  argues — the decisions, the record, the changelog, every prior finding —
  and keeps the tests and tools, which are the subject. `git archive` drops
  the commit messages either way. Neither room can sit inside the checkout.
- The gallery has been run twice. The first run was five subagents in this
  checkout with this file injected (`FINDINGS-first-run.md`). The second,
  2026-09-01, was five agents in a clean room outside the checkout, from the
  schema alone, transcripts committed (`FINDINGS.md`), graded against the
  outcomes `RERUN.md` wrote down first. All four pre-registered claims
  failed. The first run's nine vocabulary gaps did not recur; the second
  run's gaps are what the format can state, not what it can draw.
- The third, 2026-09-02, was five agents in a room built by
  `tools/clean_room.py`, from briefs whose numbers were solved first
  (`FINDINGS-run-3.md`). **The physics claim held** — no diagram reports a
  balance or rate finding, the first pre-registered claim in three runs to
  survive. Rounds fell to 2, 3, 1, 1, 1 from run 2's 9, 4, 3, 5, 2, and none
  of run 2's six documentation defects recurred. The vocabulary, remedy and
  documentation claims failed on new ground: `symbols-overlap` names a remedy
  that cannot clear it, the schema's parallel-pair advice is a recipe for the
  error it prevents, and a boundary cannot sit above what it holds. Sixteen of
  eighteen symbols were drawn; `break` as a node kind and `corner` were not,
  in the two briefs written to force them.

## Sharp edges

- `LabelRect` has no `__slots__`: a `tuple` subclass, and CPython refuses one.
- Three boundary-wall sizes, unreconciled: three glyphs tuned by eye at three
  scales. Unifying is a redesign, not tidying — the only reason to leave them.
- `render.WALL_HALF`/`WALL_DEPTH` are ints; `24.0` changes bytes and clip ids.
- A node's bounds are `±radius`; the symbol's `half`/`half_len` are clearance,
  not ink.
- Text widths are measured from the real font, one table per face; kerning is
  ignored on purpose and the subset drops GPOS to match. Table and fonts are
  regenerated together, from the Plex release the table header names.
- Subscripts are pre-centred by hand (`core.measure`); rasterisers disagree on
  `<tspan>` under `text-anchor="middle"`.
- CSS custom properties die outside a browser: `theme.bake` for Word,
  PowerPoint, cairosvg, librsvg. `bake` touches only the stylesheet.
  **Both theme paths embed the faces**: every clearance `check` certifies is
  measured in Plex, and a standalone `.svg` cannot fetch a font, so the web
  path embedding nothing made a clean report a claim about a rendering the
  reader would not see. It costs about 78 KB a file. The
  embedded faces are renamed "ThermoDraw Sans" (OFL clause 3).
- Two limits that are not checks: a `rad` value's operating point is not
  representable; `phase` draws the plateau, not the latent-heat budget. The
  temperature scale was the third, and is a declaration since 1.0.
- Every public entry point is annotated and CI runs
  `mypy --check-untyped-defs`, which is clean. The `**who` keyword spreads
  in `_layout.py` are `Dict[str, Any]` because a heterogeneous `**` spread
  into a dataclass is not checkable, and they were 87 of the 112 errors that
  annotating the public surface first surfaced.

## What is left to build

1. **The network layer.** The only genuinely hard piece. The record's table of
   what survives it says which checks it must satisfy, which it minimises, and
   which it may delete.
2. **What the format cannot state** (`examples/gallery/FINDINGS.md`, the
   second set, and its deferred table). The clean-room run's checker and
   schema defects are fixed; what is left is design: a way to relate two
   elements first, then a stream with an inlet and an outlet, quantities
   beyond the six, a capacity-versus-load marker. Each needs its argument
   in the record before it is built. The next set of briefs is written and
   its numbers close; run 3 will say whether these four are still what is
   missing.
3. Region enclosures that auto-size to their contents.
4. Unit handling — `0.35` choosing between K/W and mK/W, with a deliberate
   per-element override.
5. More checks, as they earn their place: when one caught something a browser
   was needed for, not because it was easy to compute.

## Conventions

- Units are fixed per diagram: `K/W`, `J/K`, `°C`, `W`, `W/cm²`. Never mixed.
- Stroke width 1.8 throughout. Geometry on a 10 px grid where practical.
- Heat runs left to right in a default ladder: hottest node left, coldest
  right, reference rail at the bottom.
- Commit messages say what changed and why in the subject and body; a golden
  change carries its element diff.
