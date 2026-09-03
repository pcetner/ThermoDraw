# The design record

This is the argument. `CLAUDE.md` is the decision.

Each heading here matches a decision listed there, and says why it was made,
what it replaced, and what it cost. This file is not loaded into every
session on purpose: it is long, it is written to persuade, and a record that
sits in every context window stops being a record and starts being an
instrument — the thing to be argued with was being read as the thing to
agree with. Read it when you are about to change one of these; the decision
list will tell you which heading.

An outside review in September 2026 found this file, as it then was, stale in
three places, arguing from constraints that did not support its conclusions in
two, and restating a claim its own evidence had already falsified. Those are
corrected below and the corrections are marked. The rest stands.

---

## The pipeline

**A diagram is data, and the data is the representation.** `dict -> Diagram
-> placements -> SVG`, three pure stages with a builder as sugar over the
first. Anything the builder can say is expressible as a dict, so a diagram
from JSON is indistinguishable from one built in Python. The reason is that
you should be able to describe a network to a model and have it emit
something drawable; `docs/schema.md` exists to be pasted into a prompt.

**`layout` is the seam.** It reads the coordinates you supply today and will
solve for the ones you omit when the network layer lands. Nothing either side
of it changes, and no diagram written now stops working. That feature is not
named after a version number any more: it was "0.3" in three places, one of
them an error message users read, and 0.3.0 shipped without it.

**Rendering is a pure function of its input.** Element ids are derived from
the element's own parameters, not a counter. A counter meant the same diagram
rendered twice in one process produced different bytes, which no golden-file
test survives. Identical clip paths now collapse onto one definition, so
`canvas` hoists `<defs>` and keeps one copy of each.

## Symbols

### Boxes, not zigzags

The decision that everything else rests on, and — corrected here — the one
whose recorded justification was the weakest.

The reason this file used to give was that *a box has interior room for a
mechanism glyph and a zigzag does not.* That is true, and it is an argument
about what is easy to draw. It says nothing about what is easy to read, and
the whole value of the thermal-resistance model is the circuit analogy: a
thermal engineer arrives already fluent in zigzags, and a notation that spends
that fluency has to buy something with it. The texture also repeats
information the label already carries — a box hatched for conduction is
captioned `R_cond`, by the library, structurally — so the question is narrow:
what does the texture tell a reader that the subscript does not?

The honest answer is **legibility where the subscript fails.** A structural
subscript is set at 0.7 of a 13 px face. At thumbnail size, on a slide seen
from the back of a room, or in a printed appendix at 60% scale, it is the
first thing to go, and a zigzag with an unreadable subscript says "some
resistance". A hatched box at the same scale still says *solid*, and a box of
streamlines still says *fluid*. The mechanism survives a reduction the
subscript does not. That is a reader's reason, and it is the reason to keep
the notation.

It is also, so far, an untested one. No human reader has been asked. The
gallery agents cannot judge it, because an agent does not look at the picture.
The evidence that would settle it is one thermal engineer who has never seen
this library, handed a thumbnail of the hero and a thumbnail of the same
network as zigzags, and asked which mechanism is where. Until that happens
this is a bet, and it is written down as one.

What follows from the bet: uniform 84 × 32 rectangles, so a ladder keeps an
even rhythm however many mechanisms appear in it. (The evenness follows from
*uniform*, not from *box* — uniform zigzags would be even too. The two choices
are independent, and this file used to weld them with a "so".)

**The interior states what the heat is crossing.** Section hatching is solid
material; streamlines are a moving fluid; wavy arrows cross an empty box
because radiation needs no medium; hatch-seam-hatch is two solids meeting.
One rule generates all four, so a reader learns it once. An earlier draft
used four unrelated icons and was unreadable.

**Contact hatches its two halves in opposite directions.** The drafting
convention for two parts meeting in section. Without it, contact reads as a
solid block.

### Radiation is dashed — and what the dash means

Corrected. This file used to say the dash marks *the one path that is not
linear in T, so a reader must notice it before trusting any superposition* —
and then, three hundred lines later under sharp edges, conceded that `R_rad`
is a *linearised* value in K/W. Both cannot be the reason. A linearised value
is linear: within the diagram it adds in series and combines in parallel like
any other resistance, and a reader who declines to superpose it is declining
for nothing.

What the dash actually warns of is that **the value holds at one operating
point.** `R_rad` was taken at a pair of temperatures, and reuse the network at
a different ambient and the number is wrong with no visible sign — where a
conduction resistance would still be right. That is worth redundant coding:
it is the one value on the page that is a *result*, not a *property*. The
dash says "this number moves when the temperatures do". What it cannot say is
at which temperatures it was taken; that wants a per-element validity field,
which is a schema change, and until then the dash is the whole of the
warning. (`phase` also holds a temperature, but its value *is* the plateau,
so it is a property.)

**Sources are arrows, not circled elements.** Heat appears at a node; it is
not a two-terminal element. A circled source is the circuit convention and
is wrong here.

**Direction is which end of the arrow meets the node, and nothing else.**
`to` is heat arriving and `from` is heat leaving, as on a branch. Every source
glyph draws its tail at `-half_len` and its head at `+half_len`, so one
drawing at one rotation serves both: put the symbol on the far side and join
the head, or on the near side and join the tail. `flux` is what makes this
obvious — its hatch band *is* a surface, so joining the tail stands the
surface against the node with the arrows leaving it, which is what its own
note has said all along. No glyph changed to add this.

**Only `flow` and `flux` may point away.** They annotate heat crossing a
boundary, in either direction. `diss` is dissipation appearing at a node
rather than travelling to it, and `radin` is radiation *arriving* — an
outbound one would be a symbol whose own name contradicts it, and the thing
being asked for is a `rad` branch to a boundary. The error says that. (This
file used to say "the notes say so"; the symbol notes did not, and the claim
is now made here where it can be read.)

**Fixed node connects to its boundary; thermal break does not.** The visible
gap is the whole distinction, and it is topological rather than decorative,
so the two are never confused without reading text. `g_break` is therefore
`g_fixed_node` minus the stub, and nothing else. It used to draw a crossbar
and a wall standing *across* the branch, with no node circle — an arrangement
the data pipeline could not produce and never had, because neither boundary
glyph is reachable from `layout`. A generated symbol sheet cannot show a glyph
the code cannot draw, which is the reason it is generated.
`tests/test_check.py::TestBreakNode` pins the two to each other.

**A break is also a branch kind, and it draws an open circuit.** Wire,
crossbar, gap, crossbar, wire — for a standoff or a mount, a mechanical
connection carrying no heat. Deliberately *not* a plain wire, which would say
heat flows, and not a resistance, which would say how much. It names no
quantity, so it takes no value and gets no second label line. The node kind
and the branch kind share the word on purpose: same meaning, two positions.
They cannot share a `Symbol` key, because `layout.BY_KEY` is one namespace,
which is what `layout.BRANCH_SYM` exists to bridge.

**Boundaries use a clipped hatch band, not loose tick marks.** Ticks fall
apart at intermediate angles whatever shape they outline.

**Boxes resist; arrows carry.** The interior of a box states what the heat is
*crossing*, which is why there are exactly four textures and one rule
generating them. Advection crosses nothing — the medium is going — so a
`flow` branch is chevrons in the line, not a fifth texture. It extends the
rule that already made sources arrows rather than circled elements, instead
of straining the one that makes boxes boxes.

**`flow` is the first directed branch, and refuses `angle`.** On every other
kind `angle` merely orients the symbol and means nothing. On a directed one
it reverses the arrow, so the drawing could contradict `from` and `to`. The
drawing must not be able to disagree with the data.

**An empty box interior is a statement, not an absence.** In a vocabulary
where the texture names the mechanism, `mixed` having none says the mechanism
is combined or deliberately unstated — which is what a window quoted as one
number for conduction *and* convection actually is. It is also the one kind
whose subscript the caller sets, because it is the one kind the library
cannot name.

**Heat flux is several arrows, not one.** Flux is per unit area and has no
single line of action, so it must not borrow heat flow's symbol.

## Rotation

Geometry is defined in a local frame and placed with a transform. **Text is
never rotated** — it is emitted separately, upright. **Textures rotate with
their box.** The texture belongs to the block. **Boundary symbols mirror
rather than rotate** past vertical (`scale(1,-1)` after the rotation), so a
reservoir or wall never arrives upside down. See `core.flips`.

## Text

**One block per symbol, on one side of the branch, never split across it.**
Splitting name above and value below meant running the clearance solver twice
and pushed everything further from the component.

**Line 1 is the user's label. Line 2 is `symbol = value`.** The user label is
always the top line, at every orientation. An earlier version reversed the
order depending on which way the block stacked.

**Symbol text and value are matched in size and weight.** They are two sides
of one statement. Only the italic distinguishes the variable from its units,
which is standard maths typesetting.

**Two kinds of subscript, doing different jobs.** On a resistance the
subscript is structural — `cond`, `conv`, `rad`, `contact`, `spread`, `pipe`
— set by the library and naming physics. On T, C, P and q it is identity:
caller-set, empty by default. A subscript on an R names a mechanism; a
subscript on a T names a place. The asymmetry is self-explaining in use.

**Every quantity is its own symbol, `q″` included.** `radin` and `flow` are
both powers and share `q`; a flux is per unit area and is not measured in the
same thing, so it reads `units["q″"]`. They shared one entry until the symbol
sheet was found to be documenting `q″` and `W/cm²` — an arrangement the
pipeline could not produce.

**No colour anywhere in the symbol set.** Reserved for later use —
temperature maps, path highlighting. The user label is distinguished by
weight.

**A label is text, not markup.** `core.build_block` escapes what the author
wrote and `core.sym_text` escapes a subscript before wrapping it in the one
`<tspan>` a label legitimately carries. Both run before measurement, so
`core.text_w` unescapes and measures the glyph that will be drawn. Until
September 2026 nothing escaped anything: a label of "Fins & fans" produced a
document no conforming parser would open, and a label could put a `<script>`
into `thermodraw page` output. The page's *title* had been escaped and tested
from the start, which is what made it an oversight rather than a decision.

## The label solver (`core.clear_offset`)

The offset is **solved** from the symbol's oriented bounding box support
distance along the label direction, then refined against a narrowed test box
(36% of block width).

An earlier version searched outward from a guess until a rectangle test
passed. That overshoots badly at diagonals: an axis-aligned text block's
bounding box clips a rotated symbol's corner long before the glyphs would, so
the search kept pushing. Solving directly is what brought the labels in tight.

That is an argument against that search's *termination predicate*, not
against iteration as such — this file used to say "do not replace this with
an iterative search", which is wider than the evidence. The decision is: any
replacement must clear a rotated symbol as tightly as the support solve does
at 45°, and the goldens will say whether it did.

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

## Drawing several of the same path (`count`)

**An arrangement is never inferred.** Eight 0.0275 K/W paths are 0.0034 in
parallel and 0.22 in series, a factor of sixty-four, so `count` without
`arrangement` is a wrong answer waiting to be read. It is refused.

**Each form is a complete drawing of the group, independently centred.** Not
the full one with holes in it: a group of sixteen condensed to two should take
the room of two. Each carries its own copies, its own wire and its own label,
solved against its own extent, so a condensed group's text sits against what
it shows.

**The canvas is sized for the larger form.** So a condensed group leaves the
room its expansion needs, and expanding it moves that group and nothing else.
Sizing to the shown form instead would have made every toggle reflow the whole
page. That is a preference, not a measurement: nobody was asked which they
would rather have, and this file used to call it "a far worse trade" as if
someone had been.

**Right angles, not a fan.** The first version peeled each lane off on a
diagonal. A trunk, a riser square across it, then the lane: a comb, which is
how it is drawn by hand, and which puts every riser on one line so the branch
point is a single visible junction rather than a spray. ("Reads as janky above
about four" was the author's eye; the threshold has no derivation.)

**The elision mark runs along the branch, not across it.** An ellipsis means
"and more of these" in the direction it runs, so stacked perpendicular to the
lanes it read as a decoration rather than as an omission. Lane stubs at the
lane pitch were tried instead and were worse: heavy enough to compete with the
copies they stand in for.

**The motion is a staggered fade, not a transform.** A transform on the group
would drag the wires off the nodes they connect to. `render` gives each copy a
delay from how far it sits off the centre line, so the fan runs open from the
middle outwards while no geometry moves at all.

**A form's label belongs to that form.** Both are drawn, each solved against
its own extent, and each fades with the drawing it describes. Putting the
visible one in the shared label list left it stranded in the middle of the
other form after a swap.

**Wire dedup is keyed per form.** Both forms share their trunks, and a global
key handed the shared segment to whichever was emitted first — leaving the
other drawn with nothing joining it to its nodes.

**A trunk before the fan.** Lanes radiating straight out of a node cross the
space that node's own label wants, so every default-placed parallel group
reported `label-adrift`. Forty-four units of clean wire either side fixed it,
and it is how the drawing is made by hand anyway.

**One label for the group.** It rides an `anchor` placement at the group
centre that draws nothing, with `half`/`half_len` covering the whole fan, so
the solver clears the group rather than one lane of it. `radius=0` keeps it
out of the canvas measurement, which the copies already account for.

**The group's own value is drawn, and this overturns "no arithmetic".** The
original decision was that values are strings so `"2.10"` stays `2.10`, and
folding a count would mean parsing them as numbers. It was already half
false: `_physics._effective` has parsed and folded since `--physics` shipped.
What made it wrong rather than merely inconsistent is what a reader does with
`R_cond = 1.6 K/W | 4 in parallel`. They check the arithmetic on the page,
divide ten degrees by 1.6, and get 6.25 W where the answer is 25 W. The
library knew 0.4 K/W and declined to say it.

So the count line carries it: `4 in parallel = 0.4 K/W`. The per-item value
is untouched and still exactly the digits that were typed; this is a second,
derived number, and it is marked as derived by sitting after the arrangement
rather than replacing anything.

**The fold is a table, not a formula.** Resistances in parallel divide and in
series multiply; a capacitance is the exact dual, adding in parallel and
dividing in series. Writing that as one expression with a sign flip is how it
comes to be got backwards later, and a confidently wrong number on a drawing
is worse than no number — which is the true part of the argument the old
decision was making. `flow` carries a rate and `break` carries nothing, so
neither states one, and a non-numeric value is left alone.

The cost was measured rather than assumed. A wider label pushes its
neighbours, and the first version wrote `each of 8 = 3200 W total` on a
counted source, which pushed the immersion rack's junction label 96 past its
clearance and made a diagram that had been clean report `label-adrift`. The
word "total" says nothing the `=` has not. Dropping it fits, and the
remaining four diagrams with counts are unchanged.

## A page instead of a picture (`_page.py`)

**SVG stays canonical.** Word, PowerPoint, the README and every rasteriser
need a static file, and `theme.bake` exists because they cannot even resolve
a CSS variable. None of them run script.

**SVG is not what blocks interactivity — a *file* is.** Inline SVG in a page
is fully scriptable by its host, so the page is where the controls live and
the picture stays a picture. A library whose first line is "emits SVG, no
runtime dependencies" should not put a widget inside every drawing it makes.

**Both forms ship in the markup with stable ids.** `render.variant_id`
content-addresses them, so a page holding those ids does not break when
something unrelated in the diagram moves.

## Checking a diagram (`_check.py`)

**The premise was tested, and the docs passed.** An agent given only
`docs/schema.md` produced correct, valid diagrams on the first run with no
traceback. It also produced ugly ones, and every aesthetic failure traced to
the library rather than the author. It saw zero error messages across the
whole exercise, because the failure mode was accepted-and-inert input, not
wrong input. **Validation catches diagrams that cannot be drawn. This catches
diagrams that should not be.** (Then an outside reviewer typed an ampersand
into a label, and the failure mode was wrong input after all — the scrutiny
had been pointed at decisions, never at inputs the author did not write.)

**Goldens pin bytes and cannot pin quality.** Every one of them passed green
while the hero sat 17 units high in its own frame — because the frame had
always been wrong, so the bytes had never changed. Every check here exists
because the only instrument for it was a browser.

**The checker never rebuilds the page.** `render.compose` hands back the
actual `Occupancy` the labels were solved against and what `core.annotate`
did with each one. A diagnostic that reconstructs the page will eventually
disagree with the render it claims to explain, and its first bug will be
forgetting whatever the original forgot.

**Each new primitive is the informative half of a predicate that already
existed.** `core.gap` returns the separation and `_overlap` is its sign;
`Occupancy.blocker` returns the record and `free` is whether it is None. One
SAT formula, one skip rule, one iteration order.

**Severity is a claim about the reader.** An error is something they would
misread; a warning is something they would notice and mistrust; a note is a
habit. `parallel-pair-same-side` is a note because the hero breaks it and is
fine, and a rule that condemns the flagship is one an author learns to ignore
— and then ignores when it is right. The corollary, learned later: when the
flagship is actually *wrong*, the answer is to fix the flagship, not to demote
the finding. See the numbers, below.

**Every remedy is tested by applying it.** The first version of this sentence
was written, and then five readers applied the remedies literally and six of
eighteen worked. The sentence is true now because `tests/test_check.py`
applies each one and asserts the finding goes away, and it is recorded here
with its history because a claim of this shape that was once false deserves
to be read with that in mind.

**The corridor check has a known blind spot, and it is written down.** It
fires on parallel paths 80 apart and not on 160. Four formulations were tried,
and every one that caught the loose case also condemned the hero's own
capacitance label, which is inside the ladder's main loop and correct where it
is. The threshold-free `parallel-pair-same-side` note covers the loose case
instead.

**Fundamental cycles, not all cycles.** A spanning forest by DFS, one cycle
per non-tree edge. Two steps are load-bearing and easy to miss: `layout._split`
cuts a hole in every branch, so each symbol needs a synthetic edge across it,
and a capacitance meets the middle of the rail without sharing a vertex, so
every edge is split at every vertex on it.

**A bare `T` is not a statement.** A node with no value and no subscript drew
a lone italic `T` and nothing objected, so two readers fell back to `corner`,
which draws nothing and loses the name. A subscript is enough to make it
meaningful; nothing at all is not.

**The report opens with a positive line.** An agent needs a signal that says
*good* — silence is also what a crashed checker produces.

**Two branches laid across each other are one finding, not two.** Both
directions are true, but they are one place on the page and moving either
clears both.

**The report is ASCII.** A Windows console is cp1252: an arrow in a fixed
string is a `UnicodeEncodeError` on the machine most likely to be running it.
Node ids can still carry anything, which is why `__main__` reconfigures stdout
with `errors="backslashreplace"` — not `replace`, which printed a key the
reader could not copy back.

**A finding that can only name the symptom is worth a second finding for the
cause.** Every label check names what is *nearest* the crowded label, and on
a short run that is a wire — so the author is told to move a `via` when the
spacing is what is wrong. `nodes-too-close` says the cause with both numbers
in it. It fires on a push that actually happened *and* labels that
arithmetically do not fit: the sum alone over-reports, the push alone
under-explains.

**Advice that names a direction is worth nothing unless the direction is
free.** The checker recommended sides while holding the `Occupancy` that
proved them blocked. `core.free_sides` asks the same question `annotate` asks
of a candidate, of all four sides, from the same primitives, so a second copy
of the placement arithmetic cannot drift from the placement.

**`angle` is only ever offered for a node's label.** The schema gives it three
meanings. Recommending it for a branch label laid the conduction box
diagonally across its own wire — and the checker then passed the result,
which is the worst kind of bad advice: the kind that appears to work.

**A remedy must name a field the element actually has.** A source has no
`via`; the validator refuses the field outright.

**A finding that its own remedy can silence is worse than no finding.**
`parallel-pair-same-side` skipped any pair whose sides were both set
explicitly, so doing the thing it asked for bought a clean report whether or
not it helped. What matters is where the labels landed, not how they got
there.

**Connectivity is a question about the network, not about the ink.** The
hero's *wire* graph is in two pieces — a source's lead and a node's boundary
stub are separate ink — so `network-in-pieces` works over nodes joined by
branches. A `break` branch counts: it is an explicit statement that nothing
flows, and the finding is for a path someone meant to draw.

**A placement says what it came from as data, and the ref string is for
people.** `Placement.role` and `.ends` carry the element category and the ids
at its ends; `ref` is `branch 0 a->b`, and its docstring always said it was a
diagnostic, not a key. Both `check` and `describe` used it as a key anyway,
recovering endpoints by splitting on `->`, until a node called `a->b` made the
checker report a connected diagram as severed. The network is built once, in
`_layout.network`, and both read it. The corollary is a decision about ids:
non-empty and not `rail`, and **nothing else** — forbidding `->` would defend
a parse that no longer exists, and would refuse `hot side` and `o'clock`.

**A remedy names the field that fixes *this* case.** `check._remedy` chooses
on the culprit's element, and drops `side` once the solver has already tried
both sides. That condition is `used > solved`, not `report["flipped"]`: when
the flip fails too, `annotate` falls back to the first candidate and leaves
`flipped` False, so the case where the advice matters most is the one it does
not mark.

### The numbers were never checked

Ten checks say how the drawing reads. None said what it says, while `model`
held every number a thermal network needs. `_physics.balance` is Kirchhoff at
a free node from stated values only: a resistance between two stated
temperatures implies `ΔT/R`, sources and flows are what they say, `count`
folds a group the way the schema says a count folds, a corner folds into the
path through it. A fixed node is a reservoir and is not asked; a phase node is
holding latent heat this cannot see; a `flux` source has no area; a unit it
does not know skips the diagram rather than guessing.

Run over the hero and the five gallery diagrams it fired on all six, seventeen
nodes, and every finding is arithmetic a reader can redo. The hero's first
branch implies 97 W leaving a node that receives 45. The rack's "each of 8
processors" box has no `count` and implies 400 W where 3,200 arrive — the
exact case `count` exists for. The house's roof loses 190 W and is fed by
nothing: it is joined to neither zone, which no layout check could see. The
dewar's cryocooler flows are capacities, not loads, and the remedy says to say
so in the label. None of the six diagrams' numbers closed.

The hero's do now. Its temperatures were never results of its own power and
resistances — 45 W through 0.35, 0.15 and 1.80 ∥ 6.40 K/W from 40 °C gives
126, 110 and 103 °C, not 112, 78 and 61 — so the temperatures were
recomputed and the inputs left alone. The gallery is left as its agents drew
it, because it is evidence; the clean-room re-run produces the next set.

This is the counterexample to the objection under sharp edges against physics
checks — that one would fire on every instance of a symbol. This fires on
values that disagree, and they all did. It is nevertheless **opt-in, and
stays so.** Not because the committed diagrams fail it, but because a sketch
with placeholder numbers is a legitimate diagram — the suite's own fixtures
are full of them — and it would fire at every node such a sketch has. A rule
that fires on every sketch is the rule an author learns to ignore. `--physics`
is for a diagram whose numbers you believe, and the README says so. (The
first version of this paragraph said it would go on by default the day the
hero balanced. The hero balanced, and the reasoning above is why it did not.)

### What survives the solver

The checker was built before the network layer it is meant to serve, on the
argument that it is "most of what a solver needs". That is half right. A
solver needs constraints and an objective; an author needs findings and
remedies; and several of the ten exist only because a human is placing
coordinates by hand. Asked of each check, *does this survive a solver?*:

| check | under a solver |
|---|---|
| `label-collision` | **constraint** — any placer must avoid it; stays a finding for hand placement |
| `symbols-overlap` | **constraint** |
| `wire-through-symbol` | **constraint** on the router |
| `network-in-pieces` | **survives unchanged** — about the network, not the drawing |
| `node-does-not-balance` | **survives unchanged** — about the numbers |
| `off-canvas`, `frame-off-centre` | **survive unchanged** — only fire on an explicit `size`, which is the author's |
| `label-adrift` | **objective** — the solver minimises pushes; a finding only for hand placement |
| `label-in-a-corridor` | **objective** |
| `nodes-too-close` | **scaffolding** — the solver chooses spacing from the labels; unreachable when `at` is omitted |
| `parallel-pair-same-side` | **scaffolding** — the solver chooses sides |

So the solver may delete three, must satisfy three, minimises two, and leaves
four alone. That partition is the useful thing the checker-first order
produced, and it is more useful for having been written before the solver
than it would have been after.

### What the clean room taught the checker

The second gallery run (`examples/gallery/FINDINGS.md`) applied every
remedy literally, which is the one way to find out whether a remedy is
advice or decoration. Seven of thirty-one could not be applied as written,
and they were two defects, both of the same shape: the checker named a
field without knowing whether the element had it. "Move a `via`
waypoint" went to a branch with no waypoint and to a `count: 8` branch
the validator refuses `via` on; "route it around with `via`" went to a
source's lead. The fix is not cleverer wording. It is that a placement
carries `via`, `count` and `arrangement` as data, the way it already
carried `role` and `ends`, so `_move` can read what the element is
before it says how to move it — and say nothing when nothing moves
usefully, which is the case for a comb's riser: it stands a fixed
distance out from its node whatever the spacing, so only the label can
move, and the remedy falls through to `side` or `angle`.

The parallel-pair note was a fixed sentence — set `side` to down on the
lower of the two — and one reader applied it to a pair that already had
both. A remedy derived from where the labels landed cannot name a change
that is already in the file. Three or more branches between one pair of
nodes get one note and no `side`, because a run has two useful sides and
no `side` clears three; the old remedy rotated which pair was reported,
and two readers each proved the cycle before leaving the note standing.

`label-adrift` names whatever is nearest, and on a node between two short
runs that is a symbol. Move it and the label is pushed by the symbol on
the other side by exactly the same amount. The finding now measures the
room between the two symbols against the label and says both numbers —
192 against 176, in the transcript — because `nodes-too-close`, which
speaks in those terms, sums labels *along* a run and a node label sits
across its node.

And the physics check reports what it did not check. It skipped a free
node silently whenever a neighbour had no temperature, and a node with no
temperature is the idiom the schema recommends for an interior junction;
so following the page's advice about layered walls switched the check
off for the zone inside them, and the worst-balanced node in one diagram
was absent from the only report that could have found it. A skip that is
not visible from the file has to be visible in the output. One note per
diagram, `checked 2 of 6 free nodes; not checked: ...`, with the reason
for each, and nothing on a diagram whose nodes were all asked.

### What the third clean room taught it

The third run (`examples/gallery/FINDINGS-run-3.md`) found the same defect
class in a rule the second run's fix had not reached. `symbols-overlap`
named `at`, as a fixed string, for two branches drawn between one pair of
nodes. Both symbols sit on the single run between those nodes, so sliding
one along it trades overlap for near-overlap, and at any separation wide
enough to clear, each symbol stands on the other's wire — which is
`wire-through-symbol`, arriving on the next round. A reader applied the
remedy literally, watched the overlap go 32 to 4 with the error standing,
and collected the warning as well. The remedy that works was in the *other*
finding all along, naming `via`, and it cleared both at once. So the same
treatment: ask whether the two symbols share a run, and whether the branch
can take a `via` at all, before naming a field.

The schema's own advice had the identical bug, one layer up. "A parallel
pair needs `side`" presupposed two wires with space between them, which do
not exist until one branch is routed away — and it sat in the passage headed
"worth copying rather than rediscovering". Advice that produces the error it
prevents is worse than no advice, because the reader trusts it first.

**A wire through a boundary wall is now a warning.** The wall is drawn flat
below its node at every orientation, so a branch arriving from *below* runs
through its hatching, and nothing caught it: `_symbols_overlap` counts a
ground as a box, but `_wire_through_symbol` only looks at placements
carrying a `Symbol`, and a ground carries none. The run found it from the
other side — a reader wanted a mount *above* the magnet that hangs from it,
built exactly that, and `check` passed it in silence, so it could not tell
whether the strut left through the mount's own hatching and shipped the
arrangement it could verify instead. This is the bar a new rule is supposed
to clear: it caught something a browser was needed for. It also fires twice
on run 2's `house.json`, and both are real. Those diagrams are evidence and
are not retouched; the finding is recorded instead.

**A ground gets a row in `describe`.** Same reader, same round. The wall was
counted on the `placements:` line and given no row, so the tool whose
question is "is this the drawing you meant" could not answer it for the one
element whose position was in doubt. It carries no text, so the row reads
`(no label)` — the shape a `break` branch with no label already takes — and
it is named `wall of node 'amb'`, because a ground carries its node's `ref`
and two rows under one key lose one of the two.

## Describing a diagram (`_describe.py`)

**`check` grades; `describe` reports.** Both acceptance agents asked for the
same missing thing, unprompted: the checker says nothing collides and cannot
say the drawing is the one they meant. **They stay separate.** Keeping the
judgement in one place is why `check`'s summary line can be one trustworthy
sentence. **It reads the same `Scene`**, for the same reason the checker does.
**It always exits 0.** **Rows are keyed on placements, not on labels**, so an
element carrying no text still gets a row. **It prints what each label
reads**, because position alone cannot tell a 41 J/K mass hung on the right
node from one hung on the wrong node.

The network block prints sources, direction and counts since the clean
room. It was introduced as "which nodes are joined to which, and by what"
and printed branches only, with the same symmetric dashes for a `flow` as
for a resistance: three readers observed that a source attached to the
wrong node would leave the block byte-identical, and all four that used
`flow` that one written backwards would too. `cb --flow-> th`,
`j --cond x8 parallel-- ihs`, `source 0 --diss-> j`, `th --flow-> source
1`: heat reads left to right, and the block can now confirm the things
each of them most needed confirmed. `network()` returns the kind as the
author wrote it, `flow` rather than the symbol key `flow-branch`, which
its docstring had claimed all along.

## Reviewing goldens rather than rubber-stamping them

A golden is one long line, so `git diff` marks the whole file changed for a
one-number edit — which makes the diff unreadable, so nobody reads it, so the
goldens stop being a review and become a record of whatever happened.

**No commit runs `--update-goldens` without `tools/golden_diff.py` output for
every changed scene in its message, and a sentence saying why each element
moved.** "0 elements moved" is checkable in five seconds; a 13KB single-line
diff is not. Land the instrument before the change, not after.

CI also rewrites every golden from current code and diffs the tree.
`--update-goldens` writes and then *skips*, so on its own it can never fail,
and for a while nothing checked that a golden was reproducible at all — the
font subsetter was not. The same job re-renders the gallery and the README
images: two gallery renders had gone stale, and the gallery is the evidence
this record keeps citing.

## On the evidence this record cites

The gallery — "five agents", "acceptance readers", "five readers applied
these remedies" — is five subagents run in the author's own checkout, and
this file was injected into every one of them before it received its brief.
`examples/gallery/FINDINGS.md` disclosed that; the gallery README, for a
while, did not. The vocabulary findings stand: knowing the design rationale
does not hand anyone a spreading-resistance symbol. The documentation-quality
findings are softer than they read, and every sentence in this record that
leans on "the readers asked for" should be read with that in mind.
`examples/gallery/RERUN.md` is the protocol for doing it properly.

It was done on 2026-09-01, in a sibling directory with this file removed,
and the result is `examples/gallery/FINDINGS.md`. The vocabulary findings
held, and the first run's nine gaps did not recur; the documentation
findings turned out not to be softer but harder — one agent took nine rounds
and all five tripped on the same paragraph — so wherever this record says
"the readers asked for", the clean run asked for it again, from the schema
alone, with a transcript. The first run is kept as
`examples/gallery/FINDINGS-first-run.md`.

## Three things that are limits, not checks

**A `rad` value is linearised, and the diagram cannot say at what.** See the
dash, above. Stating the operating point wants a per-element validity
condition, which is a schema field. A check that fired on every `rad` branch
carrying a value would be a footnote wearing a severity.

**The temperature scale is not representable, so it cannot be checked.**
`units["T"]` is a free string, and `K` is byte-identical whether the author
means absolute kelvin or a rise above ambient. This is a missing declaration,
not a missing check. The library is nevertheless safe, because it never
evaluates the radiation law; the hazard is downstream. A sharp version was
tried — a `rad` branch plus a negative node temperature — and a wall at
−10 °C radiating to sky is a correct diagram that fires on it.

**`phase` draws the plateau, not the budget.** A PCM buffer pins until its
latent energy is spent and then knees hard, and the time to that knee is
usually the reason the diagram was drawn. Saying it needs an energy beside a
temperature — a second quantity on a node kind that has one, which is a
schema change. Until then the limit is prose.
