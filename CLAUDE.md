# ThermoDraw

Thermal network diagrams for Python. Emits SVG. No runtime dependencies.

## What this is

A symbol library and label-placement engine for drawing thermal resistance
networks — the R–C ladders and branch networks used in electronics thermal
design. It draws them in heat-transfer notation (hatched boxes carrying a
mechanism texture) rather than circuit notation (resistor zigzags), because a
box has interior room for a mechanism glyph and a zigzag does not.

The symbol vocabulary is settled. The network layer is not built yet.

## Layout

```
src/thermodraw/
  model.py     the diagram as data — what you write, what an LLM emits
  layout.py    model -> placements. The one stage the network layer replaces
  render.py    placements -> SVG. Pure, deterministic, sizes its own canvas
  builder.py   sugar over model.py, holding no state the data cannot express
  core.py      text metrics, transforms, the label solver, occupancy, textures
  check.py     is the drawing any good? placements -> findings, no SVG
  __main__.py  the command line: `thermodraw check`, `thermodraw render`
  symbols.py   the twelve symbols, plus sheet renderers
  theme.py     CSS variables for web, baked literals and fonts for Word/slides
  _metrics.py  generated character widths — do not edit
  fonts/       the vendored subset, OFL-1.1
tools/
  gen_metrics.py  width tables from the real font
  subset_font.py  the vendored faces
  gen_docs.py     regenerates the symbol reference
  golden_diff.py  what actually changed in a golden, element by element
examples/
  hero.json              the README diagram, as data
  render_demo.py         the three README images
  render_reference.py    renders every symbol at every 45°
docs/
  schema.md              the format, written to be pasted into a prompt
  symbol-reference.html  the design record — open this first (generated)
```

`docs/symbol-reference.html` is the visual specification. It shows every
symbol at eight orientations with the reasoning for each choice. Read it
before changing any glyph.

## Design decisions, and why

These were argued out over several rounds. Each exists for a reason, and
several reverse an earlier decision that turned out to be wrong. Do not
change them without understanding what problem they solved.

### The pipeline

- **A diagram is data, and the data is the representation.** `dict -> Diagram
  -> placements -> SVG`, three pure stages with a builder as sugar over the
  first. Anything the builder can say is expressible as a dict, so a diagram
  from JSON is indistinguishable from one built in Python. The reason is that
  you should be able to describe a network to a model and have it emit
  something drawable; `docs/schema.md` exists to be pasted into a prompt.
- **`layout` is the seam.** It reads the coordinates you supply today and will
  solve for the ones you omit in 0.3. Nothing either side of it changes, and
  no diagram written now stops working.
- **Rendering is a pure function of its input.** Element ids are derived from
  the element's own parameters, not a counter. A counter meant the same
  diagram rendered twice in one process produced different bytes, which no
  golden-file test survives. Identical clip paths now collapse onto one
  definition, so `canvas` hoists `<defs>` and keeps one copy of each.

### Symbols

- **Boxes, not zigzags.** Uniform 84 × 32 rectangles. Mechanism is carried by
  the interior texture, not by the outline shape, so a ladder keeps an even
  rhythm however many mechanisms appear in it.
- **The interior states what the heat is crossing.** Section hatching is solid
  material; streamlines are a moving fluid; wavy arrows cross an empty box
  because radiation needs no medium; hatch-seam-hatch is two solids meeting.
  One rule generates all four, so a reader learns it once. An earlier draft
  used four unrelated icons and was unreadable.
- **Contact hatches its two halves in opposite directions.** The drafting
  convention for two parts meeting in section. Without it, contact reads as a
  solid block.
- **Radiation gets a dashed outline** as redundant coding. It is the one path
  that is not linear in T, so a reader must notice it before trusting any
  superposition.
- **Sources are arrows, not circled elements.** Heat appears at a node; it is
  not a two-terminal element. A circled source is the circuit convention and
  is wrong here.
- **Fixed node connects to its boundary; thermal break does not.** The visible
  gap is the whole distinction, and it is topological rather than decorative,
  so the two are never confused without reading text.
- **Boundaries use a clipped hatch band, not loose tick marks.** Ticks fall
  apart at intermediate angles whatever shape they outline.
- **Heat flux is several arrows, not one.** Flux is per unit area and has no
  single line of action, so it must not borrow heat flow's symbol.

### Rotation

- Geometry is defined in a local frame and placed with a transform. **Text is
  never rotated** — it is emitted separately, upright.
- **Textures rotate with their box.** The texture belongs to the block.
- **Boundary symbols mirror rather than rotate** past vertical
  (`scale(1,-1)` after the rotation), so a reservoir or wall never arrives
  upside down. See `core.flips`.

### Text

- **One block per symbol, on one side of the branch, never split across it.**
  Splitting name above and value below meant running the clearance solver
  twice and pushed everything further from the component.
- **Line 1 is the user's label. Line 2 is `symbol = value`.** The user label
  is always the top line, at every orientation. An earlier version reversed
  the order depending on which way the block stacked.
- **Symbol text and value are matched in size and weight.** They are two sides
  of one statement. Only the italic distinguishes the variable from its units,
  which is standard maths typesetting.
- **Two kinds of subscript, doing different jobs.** On a resistance the
  subscript is structural — `cond`, `conv`, `rad`, `contact` — set by the
  library and naming physics. On T, C, P and q it is identity: caller-set,
  empty by default. A subscript on an R names a mechanism; a subscript on a T
  names a place. The asymmetry is self-explaining in use.
- **No colour anywhere in the symbol set.** Reserved for later use —
  temperature maps, path highlighting. The user label is distinguished by
  weight.

### The label solver (`core.clear_offset`)

The offset is **solved** from the symbol's oriented bounding box support
distance along the label direction, then refined against a narrowed test box
(36% of block width).

An earlier version searched outward from a guess until a rectangle test
passed. That overshoots badly at diagonals: an axis-aligned text block's
bounding box clips a rotated symbol's corner long before the glyphs would, so
the search kept pushing. Solving directly is what brought the labels in
tight. **Do not replace this with an iterative search.**

`clear_offset` clears a label from *its own* symbol and nothing else, which is
correct and is why it stays. Everything else on the page is `core.Occupancy`:
placed labels, drawn wires, other symbols. A label skips its own symbol
through `owner`, so the tight solve is never second-guessed by a bounding box.
`annotate` tries the automatic side, then the opposite one — a blocked label
steps across the branch rather than drifting off it — and only pushes outward
if both are taken. `side="up"/"down"/"left"/"right"` overrides the choice.

Before this existed, the demo was fixed by hand: moving coordinates, and
inflating `half` — a clearance parameter — into a "push harder" knob. If you
find yourself doing that again, the occupancy list is the thing to reach for.

### Checking a diagram (`check.py`)

- **The premise was tested, and the docs passed.** An agent given only
  `docs/schema.md` and no other context produced correct, valid diagrams on
  the first run with no traceback. It also produced ugly ones, and every
  aesthetic failure traced to the library rather than the author. It saw zero
  error messages across the whole exercise, because the failure mode was
  accepted-and-inert input, not wrong input. **Validation catches diagrams
  that cannot be drawn. This catches diagrams that should not be.**
- **Goldens pin bytes and cannot pin quality.** 134 of them passed green while
  the hero sat 17 units high in its own frame — because the frame had always
  been wrong, so the bytes had never changed. Every check here exists because
  the only instrument for it was a browser.
- **The checker never rebuilds the page.** `render.compose` hands back the
  actual `Occupancy` the labels were solved against and what `core.annotate`
  did with each one. A diagnostic that reconstructs the page will eventually
  disagree with the render it claims to explain, and its first bug will be
  forgetting whatever the original forgot.
- **Each new primitive is the informative half of a predicate that already
  existed.** `core.gap` returns the separation and `_overlap` is its sign;
  `Occupancy.blocker` returns the record and `free` is whether it is None.
  One SAT formula, one skip rule, one iteration order. A second copy is the
  drift this file keeps warning about, arriving with a straight face.
- **Severity is a claim about the reader.** An error is something they would
  misread; a warning is something they would notice and mistrust; a note is a
  habit. `parallel-pair-same-side` is a note because the hero breaks it and
  is fine, and a rule that condemns the flagship is one an author learns to
  ignore — and then ignores when it is right.
- **Every remedy is tested by applying it.** A check whose remedy is untested
  is a check that gives bad advice with authority.
- **The corridor check has a known blind spot, and it is written down.** It
  fires on parallel paths 80 apart and not on 160. Four formulations were
  tried, and every one that caught the loose case also condemned the hero's
  own capacitance label, which is inside the ladder's main loop and correct
  where it is. The threshold-free `parallel-pair-same-side` note covers the
  loose case instead. `tests/test_check.py` pins the limit rather than
  pretending it is not there.
- **Fundamental cycles, not all cycles.** A spanning forest by DFS, one cycle
  per non-tree edge. Enumerating every cycle is exponential; this finds every
  loop a hand-drawn ladder makes. Two steps are load-bearing and easy to miss:
  `layout._split` cuts a hole in every branch, so each symbol needs a
  synthetic edge across it, and a capacitance meets the middle of the rail
  without sharing a vertex, so every edge is split at every vertex on it.
- **The report opens with a positive line.** An agent needs a signal that says
  *good*, not merely an absence of output — silence is also what a crashed
  checker produces.
- **The report is ASCII.** It goes to a terminal, and a Windows console is
  cp1252: an arrow in a fixed string is a `UnicodeEncodeError` on the machine
  most likely to be running it. Node ids can still carry anything, which is
  why `__main__` also reconfigures stdout with `errors="replace"`.

### Reviewing goldens rather than rubber-stamping them

A golden is one long line, so `git diff` marks the whole file changed for a
one-number edit — which makes the diff unreadable, so nobody reads it, so the
goldens stop being a review and become a record of whatever happened.

**No commit runs `--update-goldens` without `tools/golden_diff.py` output for
every changed scene in its message, and a sentence saying why each element
moved.** "0 elements moved" is checkable in five seconds; a 13KB single-line
diff is not. Land the instrument before the change, not after.

## Known sharp edges

- **`Placement.mirror` is dead.** Nothing writes it and nothing reads it —
  `render.place` recomputes the value for itself. It stays because removing a
  field from a public dataclass breaks anyone constructing one positionally.
  So is `core.LEAD`, which `symbols.LEAD` shadowed.
- **`LabelRect` has no `__slots__`.** It is a `tuple` subclass so that it
  still unpacks as four numbers and compares equal to the plain tuple it
  replaced, and CPython refuses a nonempty `__slots__` on a subtype of a
  variable-length built-in. It carries a `__dict__`; that is the price.
- **`thermodraw.render` and `thermodraw.layout` are functions, not modules.**
  `__init__` rebinds both, so `from . import render` inside the package gets
  the function and `render.PADDING` is an `AttributeError`. Import the names:
  `from .render import PADDING, compose`. `check.py` and `tests/test_frame.py`
  both do, and both say why.
- **There are three boundary-wall sizes and they are not unified.**
  `render.WALL_HALF/WALL_DEPTH` is (24, 13), `g_fixed_node` draws (20, 12) and
  `g_break` (22, 13). They are three different walls at three different
  scales, and `docs/symbol-reference.html` is the declared visual record for
  two of them. `layout.BREAK_WALL` passes `g_break`'s own numbers through the
  placement rather than taking `ground`'s defaults. Unifying them would move
  four goldens and the generated page, in the one area this file calls
  settled, for tidiness.
- **`render.WALL_HALF` and `WALL_DEPTH` are ints.** They reach the markup
  through an f-string, so `24.0` writes `y="-24.0"` where the drawing has
  always said `y="-24"`, and the clip ids are content-addressed on exactly
  those numbers. Naming a constant moved 5 elements until they were ints
  again.
- **A node's bounds are `±radius`, deliberately.** A fixed node's `half=22,
  half_len=19` are clearance numbers for the label solver, not ink.
  Substituting them reserves 22 units above a 5.5 circle and counts the
  boundary wall a second time, when the wall is already its own placement.

- **Text widths are measured**, not estimated. `core._metrics` is generated
  by `tools/gen_metrics.py` from the real font, one table per face because
  SemiBold runs about 4% wider than Regular — the same size as the error
  being removed. It replaced a sixteen-entry hand-written table that assumed
  0.55 for everything else, covering 16 of the 52 glyphs the library emits;
  mean per-glyph error was 12%, and 98% for `/`.
- **Kerning is ignored on purpose.** `text_w` sums advances and cannot see a
  kern pair, so the vendored subset drops GPOS. The render then matches what
  the solver modelled, rather than being a little tighter than it in places.
- **The width table and the vendored font must be regenerated together.**
  They are two halves of one measurement; `tests/test_fonts.py` pins them to
  each other.
- **HTML entities count as one glyph** in `core.text_w` via `_ENT`. Removing
  that regex silently breaks any label using one — it caused a 40 px phantom
  gap in the heat-flux label.
- **Subscripts are pre-centred manually** (`core.measure`) because rasterisers
  disagree on `<tspan>` metrics under `text-anchor="middle"`. Do not switch to
  a plain centred `<text>` with a tspan inside.
- **CSS custom properties do not survive outside a browser.** Word,
  PowerPoint, cairosvg and librsvg all ignore them; cairosvg throws. Use
  `theme.bake()` for those targets. It also embeds the text faces, because a
  target that cannot fetch a stylesheet cannot fetch a font either, and text
  set in a substitute face does not match the widths it was cleared against.
  `theme.faces_used` embeds only what the diagram needs — all three cost
  about 79KB, and a diagram with no text carries none.
- **The embedded faces are renamed.** IBM Plex is OFL-1.1 with Reserved Font
  Name "Plex", and a subset is a Modified Version under clause 3, so they
  ship as "ThermoDraw Sans". The CSS stack still asks for the real font
  first, and the metrics are identical either way.

## What is left to build

In rough priority order:

1. **The network layer.** `layout` computes the coordinates you leave out.
   The model, the schema and the render are in place; what is missing is the
   solver. A ladder walking left to right with capacitances dropping to a
   common rail covers most cases; parallel paths are expressed with explicit
   `via` waypoints today and need routing. This is the largest remaining piece
   and the only genuinely hard one. `check.py` is now the thing that tells it
   whether its answer was any good, which is most of what a solver needs and
   was the reason to build the checker first.
2. **A spreading resistance symbol** — the one gap in the vocabulary. The
   natural glyph under the current scheme is hatching that fans from a point
   rather than running parallel, reading as heat diverging into a larger
   cross-section.
3. **Region enclosures that auto-size to their contents** rather than taking
   fixed dimensions.
4. **Unit handling** — pass `0.35` and have it choose between K/W and mK/W.
5. **More checks, as they earn their place.** A finding is worth adding when
   it caught something a browser was needed for. It is not worth adding
   because it is easy to compute.

## Conventions

- Units are fixed per diagram: `K/W`, `J/K`, `°C`, `W`, `W/cm²`. Never mixed.
- Stroke width 1.8 throughout. Geometry on a 10 px grid where practical.
- Heat runs left to right in a default ladder: hottest node left, coldest
  right, reference rail at the bottom.
