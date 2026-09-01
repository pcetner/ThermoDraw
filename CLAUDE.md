# ThermoDraw

Thermal network diagrams for Python. Emits SVG. No runtime dependencies.

## What this is

A symbol library and label-placement engine for drawing thermal resistance
networks — the R–C ladders and branch networks used in electronics thermal
design. It draws them in heat-transfer notation (hatched boxes carrying a
mechanism texture) rather than circuit notation (resistor zigzags), because a
box has interior room for a mechanism glyph and a zigzag does not.

The network layer is not built yet. The symbol vocabulary was settled
until five agents drew five networks from five domains and named nine
things it could not say; `examples/gallery/FINDINGS.md` is that list,
and most of it has since been built.

## Layout

```
src/thermodraw/
  model.py     the diagram as data — what you write, what an LLM emits
  layout.py    model -> placements. The one stage the network layer replaces
  render.py    placements -> SVG. Pure, deterministic, sizes its own canvas
  builder.py   sugar over model.py, holding no state the data cannot express
  core.py      text metrics, transforms, the label solver, occupancy, textures
  check.py     is the drawing any good? placements -> findings, no SVG
  describe.py  is it the drawing you meant? placements -> prose, no SVG
  page.py      the same SVG inline in HTML, with its controls
  __main__.py  the command line: `check`, `describe`, `render`, `page`
  symbols.py   the eighteen symbols, plus sheet renderers
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
- **Direction is which end of the arrow meets the node, and nothing else.**
  `to` is heat arriving and `from` is heat leaving, as on a branch. Every
  source glyph draws its tail at `-half_len` and its head at `+half_len`, so
  one drawing at one rotation serves both: put the symbol on the far side and
  join the head, or on the near side and join the tail. `flux` is what makes
  this obvious — its hatch band *is* a surface, so joining the tail stands the
  surface against the node with the arrows leaving it, which is what its own
  note has said all along. No glyph changed to add this.
- **Only `flow` and `flux` may point away.** They are the annotation kinds,
  and the notes say so. `diss` is dissipation appearing at a node rather than
  travelling to it, and `radin` is radiation *arriving* — an outbound one
  would be a symbol whose own name contradicts it, and the thing being asked
  for is a `rad` branch to a boundary. The error says that.
- **Fixed node connects to its boundary; thermal break does not.** The visible
  gap is the whole distinction, and it is topological rather than decorative,
  so the two are never confused without reading text. `g_break` is therefore
  `g_fixed_node` minus the stub, and nothing else. It used to draw a crossbar
  and a wall standing *across* the branch, with no node circle — an
  arrangement the data pipeline could not produce and never had, because
  neither boundary glyph is reachable from `layout`. The symbol sheet is the
  visual specification, so a glyph it shows that the library cannot draw is
  worse than no sheet at all. `tests/test_check.py::TestBreakNode` now pins
  the two to each other.
- **A break is also a branch kind, and it draws an open circuit.** Wire,
  crossbar, gap, crossbar, wire — for a standoff or a mount, a mechanical
  connection carrying no heat. Deliberately *not* a plain wire, which would
  say heat flows, and not a resistance, which would say how much. It names no
  quantity, so it takes no value and gets no second label line. The node kind
  and the branch kind share the word on purpose: same meaning, two positions.
  They cannot share a `Symbol` key, because `layout.BY_KEY` is one namespace,
  which is what `layout.BRANCH_SYM` exists to bridge.
- **Boundaries use a clipped hatch band, not loose tick marks.** Ticks fall
  apart at intermediate angles whatever shape they outline.
- **Boxes resist; arrows carry.** The interior of a box states what the heat
  is *crossing*, which is why there are exactly four textures and one rule
  generating them. Advection crosses nothing — the medium is going — so a
  `flow` branch is chevrons in the line, not a fifth texture. It extends the
  rule that already made sources arrows rather than circled elements, instead
  of straining the one that makes boxes boxes.
- **`flow` is the first directed branch, and refuses `angle`.** On every other
  kind `angle` merely orients the symbol and means nothing. On a directed one
  it reverses the arrow, so the drawing could contradict `from` and `to`. The
  drawing must not be able to disagree with the data.
- **An empty box interior is a statement, not an absence.** In a vocabulary
  where the texture names the mechanism, `mixed` having none says the
  mechanism is combined or deliberately unstated — which is what a window
  quoted as one number for conduction *and* convection actually is. It is
  also the one kind whose subscript the caller sets, because it is the one
  kind the library cannot name.
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
- **Every quantity is its own symbol, `q″` included.** `radin` and `flow` are
  both powers and share `q`; a flux is per unit area and is not measured in
  the same thing, so it reads `units["q″"]`. They shared one entry until the
  symbol sheet was found to be documenting `q″` and `W/cm²` — an arrangement
  the pipeline could not produce.
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

### Drawing several of the same path (`count`)

- **An arrangement is never inferred.** Eight 0.0275 K/W paths are 0.0034 in
  parallel and 0.22 in series, a factor of sixty-four, so `count` without
  `arrangement` is a wrong answer waiting to be read. It is refused.
- **Each form is a complete drawing of the group, independently centred.**
  Not the full one with holes in it: a group of sixteen condensed to two
  should take the room of two. Each carries its own copies, its own wire and
  its own label, solved against its own extent, so a condensed group's text
  sits against what it shows.
- **The canvas is sized for the larger form.** So a condensed group leaves the
  room its expansion needs, and expanding it moves that group and nothing
  else. Sizing to the shown form instead would have made every toggle reflow
  the whole page, which is a far worse trade than some reserved whitespace.
- **Right angles, not a fan.** The first version peeled each lane off on a
  diagonal, which reads as janky at any count above about four and worsens as
  the group grows. A trunk, a riser square across it, then the lane: a comb,
  which is how it is drawn by hand, and which puts every riser on one line so
  the branch point is a single visible junction rather than a spray.
- **The elision mark is stubs of the missing lanes, not an ellipsis.** Three
  dots are punctuation and too quiet to say "there is a branch here". Short
  segments at the lane pitch, in the same stroke as a lane, say it in the
  drawing's own language. Across the run for a series group, since there the
  dropped copies sit along it.
- **The motion is a staggered fade, not a transform.** A transform on the
  group would drag the wires off the nodes they connect to. `render` gives
  each copy a delay from how far it sits off the centre line, so the fan runs
  open from the middle outwards while no geometry moves at all.
- **A form's label belongs to that form.** Both are drawn, each solved against
  its own extent, and each fades with the drawing it describes. Putting the
  visible one in the shared label list left it stranded in the middle of the
  other form after a swap — the text stayed where sixteen lanes had opened
  around it.
- **Wire dedup is keyed per form.** Both forms share their trunks, and a
  global key handed the shared segment to whichever was emitted first —
  leaving the other drawn with nothing joining it to its nodes.
- **A trunk before the fan.** Lanes radiating straight out of a node cross the
  space that node's own label wants, so every default-placed parallel group
  reported `label-adrift`. Forty-four units of clean wire either side fixed
  it, and it is how the drawing is made by hand anyway. Both trunks dedupe,
  being one segment shared by every lane.
- **One label for the group.** It rides an `anchor` placement at the group
  centre that draws nothing, with `half`/`half_len` covering the whole fan, so
  the solver clears the group rather than one lane of it. `radius=0` keeps it
  out of the canvas measurement, which the copies already account for.

### A page instead of a picture (`page.py`)

- **SVG stays canonical.** Word, PowerPoint, the README and every rasteriser
  need a static file, and `theme.bake` exists because they cannot even resolve
  a CSS variable. None of them run script.
- **SVG is not what blocks interactivity — a *file* is.** Inline SVG in a page
  is fully scriptable by its host, so the page is where the controls live and
  the picture stays a picture. A library whose first line is "emits SVG, no
  runtime dependencies" should not put a widget inside every drawing it makes.
- **Both forms ship in the markup with stable ids.** `render.variant_id`
  content-addresses them, so a page holding those ids does not break when
  something unrelated in the diagram moves.

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
- **A bare `T` is not a statement.** A node with no value and no subscript
  drew a lone italic `T` and nothing objected, so two readers fell back to
  `corner`, which draws nothing and loses the name. Interior junctions between
  series layers routinely have no temperature of their own. A subscript is
  enough to make it meaningful — a diagram may be symbolic throughout — but
  nothing at all is not.
- **The report opens with a positive line.** An agent needs a signal that says
  *good*, not merely an absence of output — silence is also what a crashed
  checker produces.
- **Two branches laid across each other are one finding, not two.** Both
  directions are true — each one's wire really is inside the other's box —
  but they are one place on the page and moving either clears both.
- **The report is ASCII.** It goes to a terminal, and a Windows console is
  cp1252: an arrow in a fixed string is a `UnicodeEncodeError` on the machine
  most likely to be running it. Node ids can still carry anything, which is
  why `__main__` also reconfigures stdout with `errors="replace"`.
- **A finding that can only name the symptom is worth a second finding for
  the cause.** Every label check names what is *nearest* the crowded label,
  and on a short run that is a wire — so the author is told to move a `via`
  when the spacing is what is wrong, and `via` cannot fix spacing. An
  acceptance reader followed that into a dead end. `nodes-too-close` says the
  cause with both numbers in it. It fires on a push that actually happened
  *and* labels that arithmetically do not fit: the sum alone over-reports,
  because labels stack at different heights and a ladder at 180 sums to 187
  and is fine; the push alone under-explains, because a waypoint crowds a
  label just as hard and moving the nodes would not help.
- **Advice that names a direction is worth nothing unless the direction is
  free.** The checker recommended sides while holding the `Occupancy` that
  proved them blocked — telling a node to try left or right when those were
  where its branches left. Five readers applied these remedies literally and
  six of eighteen worked; three made the drawing worse. `core.free_sides` asks
  the same question `annotate` asks of a candidate, of all four sides, from
  the same `clear_offset`/`_corner`/`free` primitives, so a second copy of the
  placement arithmetic cannot drift from the placement.
- **`angle` is only ever offered for a node's label.** The schema gives it
  three meanings: on a node it moves the label and nothing else, on a branch
  it overrides the direction taken from the wire, on a source it aims the
  arrow. Recommending it for a branch label laid the conduction box diagonally
  across its own wire — and the checker then passed the result, which makes it
  the worst kind of bad advice: the kind that appears to work.
- **A remedy must name a field the element actually has.** A source's lead is
  a wire carrying the source's ref, and the wire branch of the remedy offered
  a `via`. Sources have none; the validator refuses the field outright.
- **A finding that its own remedy can silence is worse than no finding.**
  `parallel-pair-same-side` skipped any pair whose sides were both set
  explicitly, so doing the thing it asked for bought a clean report whether or
  not it helped. What matters is where the labels landed, not how they got
  there. A note is already something you are free to ignore.
- **Connectivity is a question about the network, not about the ink.** Two of
  five gallery diagrams were severed in half and passed everything. The hero's
  *wire* graph is in two pieces — a source's lead and a node's boundary stub
  are separate ink — so `network-in-pieces` works over nodes joined by
  branches. A `break` branch counts: the finding is for a path someone meant
  to draw, and a break is an explicit statement that nothing flows.
- **A remedy names the field that fixes *this* case.** Both label findings
  carried one fixed string offering `side`, `angle` and `via` whatever was in
  the way, which leaves the author to work out which applies — and sometimes
  they cannot, because the answer was not in the list. A source crowding its
  node is moved with `at`. `check._remedy` chooses on the culprit's element,
  and drops `side` once the solver has already tried both sides. That last
  condition is `used > solved`, not `report["flipped"]`: when the flip fails
  too, `annotate` falls back to the first candidate and leaves `flipped`
  False, so the case where the advice matters most is the one it does not
  mark.

### Describing a diagram (`describe.py`)

- **`check` grades; `describe` reports.** Both acceptance agents, given only
  `docs/schema.md`, asked for the same missing thing, unprompted: the checker
  says nothing collides and cannot say the drawing is the one they meant.
  Element counts, canvas size, and which way each label went is enough to
  confirm intent without a browser.
- **They stay separate.** Keeping the judgement in one place is why `check`'s
  summary line can be one trustworthy sentence; a describe that also graded
  would have to hedge it.
- **It reads the same `Scene`, for the same reason the checker does.** A
  description that re-derives the page will drift from the render it claims
  to describe.
- **It always exits 0.** The exit code is `check`'s to own. Two questions,
  two commands, two meanings for the number.
- **Rows are keyed on placements, not on labels.** `compose` skips a label
  with nothing to say, so a table built from `scene.rects` cannot show an
  element that carries no text — and a `break` branch names no quantity by
  design, so one with no `label` vanished into the counts. Keyed on
  placements, it gets a row marked `(no label)`.
- **It prints what each label reads.** Position alone cannot tell a 41 J/K
  mass hung on the right node from one hung on the wrong node: the geometry
  is identical and only the words differ, which makes the words the thing
  worth printing. Subscripts are read back out of the `<tspan>` markup.

### Reviewing goldens rather than rubber-stamping them

A golden is one long line, so `git diff` marks the whole file changed for a
one-number edit — which makes the diff unreadable, so nobody reads it, so the
goldens stop being a review and become a record of whatever happened.

**No commit runs `--update-goldens` without `tools/golden_diff.py` output for
every changed scene in its message, and a sentence saying why each element
moved.** "0 elements moved" is checkable in five seconds; a 13KB single-line
diff is not. Land the instrument before the change, not after.

## Known sharp edges

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
   A per-element `unit` override belongs here too: units are one entry per
   quantity per diagram, which is the rule that keeps `K/W` from mixing with
   `mK/W`, and the escape hatch has to be deliberate rather than a side effect
   of the quantity table.
5. **More checks, as they earn their place.** A finding is worth adding when
   it caught something a browser was needed for. It is not worth adding
   because it is easy to compute.

## Conventions

- Units are fixed per diagram: `K/W`, `J/K`, `°C`, `W`, `W/cm²`. Never mixed.
- Stroke width 1.8 throughout. Geometry on a 10 px grid where practical.
- Heat runs left to right in a default ladder: hottest node left, coldest
  right, reference rail at the bottom.
