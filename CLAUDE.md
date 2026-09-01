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
examples/
  hero.json              the README diagram, as data
  render_demo.py         the three README images
  render_reference.py    renders every symbol at every 45°
  gallery/               five networks from five domains; RERUN.md is the protocol
docs/
  schema.md              the format, written to be pasted into a prompt
  design-record.md       why each decision below was made — read before changing one
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
- Boxes resist, arrows carry: `flow` is chevrons in the line. It is the one
  directed branch and refuses `angle`.
- `mixed` is an empty box, and that is a statement. Flux is several arrows.
  `q″` is its own quantity. No colour in the symbol set.

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
- Each form is a complete drawing; the canvas is sized for the larger.
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
  *this* case, and never a direction the occupancy says is blocked.
- Connectivity is over nodes joined by branches, not over ink. A `break`
  counts as joined.
- A placement carries `role` and `ends` as data; `ref` is for people. Ids are
  non-empty and not `rail`, and nothing else is required of them.
- **The numbers were never checked, and none of the six real diagrams'
  numbers close.** `--physics` is Kirchhoff at a free node from stated values.
  It ships off by default until the hero and the gallery balance; then on.
- What survives the solver: three constraints, two objectives, four unchanged,
  three scaffolding. The table is in the record.

### Describing
- `check` grades; `describe` reports, always exits 0, reads the same `Scene`,
  keys rows on placements, prints what each label reads.

### Goldens
- No `--update-goldens` commit without `tools/golden_diff.py` output in its
  message and a sentence per moved element. CI regenerates every golden and
  diffs; CI re-renders the gallery and README images and diffs.

### Evidence
- The gallery was five subagents in this checkout with this file injected.
  The vocabulary findings stand; the documentation findings are softer.
  `examples/gallery/RERUN.md` is the clean-room protocol, not yet run.

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
  PowerPoint, cairosvg, librsvg. `bake` touches only the stylesheet. The
  embedded faces are renamed "ThermoDraw Sans" (OFL clause 3).
- Three limits that are not checks: a `rad` value's operating point is not
  representable; the temperature scale (absolute or rise) is not
  representable; `phase` draws the plateau, not the latent-heat budget.
- `mypy --check-untyped-defs` finds 91 more than the default level CI runs,
  most of them the `**who` keyword spreads in `_layout.py`.

## What is left to build

1. **The network layer.** The only genuinely hard piece. The record's table of
   what survives it says which checks it must satisfy, which it minimises, and
   which it may delete.
2. **Make the hero and the gallery balance**, then turn `--physics` on by
   default. The hero's temperatures do not agree with its own resistances and
   power; that is a content decision about the flagship, not a code change.
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
