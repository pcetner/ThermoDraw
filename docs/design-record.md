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

Since 1.0 it is a default rather than a bet. `render`, `Diagram.svg` and
the command line take `notation="zigzags"`, which draws every resistance as
leads and six peaks the length of a box — the same glyph
`docs/notation-test/make.py` used for the thumbnails — with `half` and
`half_len` unchanged, so labels, wires and the checker see the same
geometry. The reader who prefers the notation they arrived fluent in has
it; the reader's reason above is why boxes are what you get without
asking. The notation test is still worth running, because it would say
which should be the default, and nobody has run it.

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

### `corner` is gone

It was a node kind that drew nothing: "a coordinate, not a place", in the
dictionary's words, so that a wire had somewhere to bend. Removed before 1.0,
for three reasons in the order the evidence gave them.

It was never used. Fifteen agents in three clean-room runs drew sixteen of
the eighteen symbols and not this, including the run-3 brief written to force
it — the agent routed with `via` and did not mention having considered
`corner`. The two readers who did reach for it, in the first run, wanted a
named junction and got a kind that lost the name.

It put layout into the topology. A `via` waypoint says "the wire goes here"
and nothing about the network; a `corner` node said the same thing as a node,
so `describe` had to hide it, `check` had to skip it when counting labels,
and `--physics` had to fold the two resistances through it into one before it
could balance anything. Run 3 recorded that "a bend cannot be a property of
the hardware": delete the corner and the file asserts the same physics. Once a
solver routes wires for itself, it is the one kind that is not a node.

What it did is done by two things that already existed. A bend is `via`. A
junction between two paths — a vapour chamber ending where an oil gap begins
— is a `free` node with a `sub` and no `value`, which draws a circle, names
the place, and states no temperature; `--physics` then says by name that it
did not check it, which is more honest than folding it away. A file from 0.3
that names `corner` is refused with exactly that advice, not with "unknown
kind" beside a list it used to be on.

One committed diagram used it: the run-3 reference solution for the subsea
bottle, where the corner joined a `pipe` branch to a `conv` branch. It is a
junction, and it is now a free node with the temperature the brief's numbers
give it, 17.8 °C, so the reference still closes under `--physics`. That is a
retouch of evidence, made because the alternative was a reference the library
refuses to load.

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
decision was making. A rate has its own row: four loops in parallel carry
four times the heat, and four in series pass the same heat through every
link, so the group carries one loop's worth. This paragraph said a `flow`
states no group value, and the table had no row for it, until the blind code
review found `--physics` keeping a second copy of the fold that knew
resistances and not rates — and reporting four correct 10 W loops into a
40 W sink as a node that does not balance. One table, read by the drawing and
the checker both, is the fix for that class of bug. `break` carries nothing
and states none, and a non-numeric value is left alone.

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

Ten checks said how the drawing reads. None said what it says, while `model`
held every number a thermal network needs. `_physics.balance` is Kirchhoff at
a free node from stated values only: a resistance between two stated
temperatures implies `ΔT/R`, sources and flows are what they say, `count`
folds a group the way the schema says a count folds. (A `corner` used to fold
into the path through it; the kind is gone, under Symbols.) A fixed node is a
reservoir and is not asked; a phase node is
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
| `wire-through-wall` | **constraint** on the router — a boundary's wall is a box the route must not cross |
| `network-in-pieces` | **survives unchanged** — about the network, not the drawing |
| `node-does-not-balance` | **survives unchanged** — about the numbers |
| `off-canvas`, `frame-off-centre` | **survive unchanged** — only fire on an explicit `size`, which is the author's |
| `label-adrift` | **objective** — the solver minimises pushes; a finding only for hand placement |
| `label-in-a-corridor` | **objective** |
| `nodes-too-close` | **scaffolding** — the solver chooses spacing from the labels; unreachable when `at` is omitted |
| `parallel-pair-same-side` | **scaffolding** — the solver chooses sides |
| `symbol-off-its-run` | **scaffolding** — fires only on an explicit branch `at`, which a solver never sets |

So the solver may delete three, must satisfy four, minimises two, and leaves
four alone. (This sentence said "delete three" over a table that listed two,
and "satisfy three" — both written before `wire-through-wall` and
`symbol-off-its-run` existed. The counts are right now; they were not then.)
That partition is the useful thing the checker-first order
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
diagram, `checked 2 of 6 free places; not checked: ...`, with the reason
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

### What the blind code review taught it

`tools/clean_room.py --profile review` hands a reader the code, the tests and
no argument for any of it. Nine findings came back and seven were defects.
Four are worth the record.

**`to_dict` was lossy, and the thesis is that the data is the
representation.** The keep lists named some fields and not others, and
`_keep` then skipped anything falsy — so `count`, `arrangement`, `rate` and
`side` vanished, and so did a node at 0 °C and a branch at `angle: 0`. The
rule should never have been about falsiness: what "the author did not set
this" looks like is the field still holding its dataclass default, and
`Branch.angle` defaults to None precisely so that 0 remains expressible. The
one round-trip test used the hero, which happens to use none of the lost
fields.

**Exit 1 has to mean findings.** `validate` checked every field inside a
node, a branch, a source and the rail, and nothing above them, so `"size":
"big"` reached the renderer and died as `could not convert string to float:
'b'` — exiting 1 through Python's own handler, which the command line
documents as *findings*. A CI step gating on the status read a crash as a
diagram with warnings. The top level is validated now, and `__main__` keeps
a net under the unknown cases that answers 2, because a crash is "no
answer" and never "some warnings".

**The canvas is sized for the larger form, and a form is its text too.** The
hidden half of a repeated group had its label solved with `occupied=None` —
against nothing — and left out of `extent`, so an eight-way group's expanded
label sat above the canvas top and the root `<svg>` clipped it the moment a
reader pressed the control that exists to show it. It is now solved against
the page and measured into the canvas, and it does *not* claim a place in
the occupancy: an invisible label must not push a visible one. Two comments
asserted the two forms shared a footprint, a property `_layout` had
deliberately given up; the reviewer said those comments were what led them
to the bug.

**A clean report is about a rendering, and the reader has to get that
rendering.** Every clearance is measured from the Plex advance tables in
`_metrics.py`. `bake` embedded the faces for exactly that reason and
`with_variables` — the documented path for a `.svg` on the web — embedded
nothing, falling through to Arial, in which the hero's widest label is about
five units wider than the solver cleared. Both paths embed now. It costs
about 78 KB a file and buys the guarantee the library is for.

One more that is a fix in two places at once: `--physics` kept its own copy
of the fold and knew about resistances but not rates, so four correct 10 W
loops in parallel into a 40 W sink were reported as a node that does not
balance, at both ends. `model.FOLD` is the single table now and the checker
reads it, so the number on the drawing and the number in the report cannot
disagree.

**A boundary can sit above what it holds, since 1.0.** 08's finding was
one design limit and two tool gaps. The tool gaps closed first: `describe`
names every wall, and `wire-through-wall` fires. The limit closes with a
field. A `fixed` or `break` node takes `wall` — `down` by default, or `up`,
`left`, `right` — and layout turns the ground placement to match. The
renderer's `ground` and the occupancy box it feeds already took an angle;
nothing on the node reached them, and two literals in `_layout` were the
whole of "always below". The remedy for `wire-through-wall` now names the
direction that faces away from the offending branch first, `at` second, and
is tested by applying it in all four directions. With the wall above, the
automatic label goes below, for the reason it goes above when the wall is
below: the default should not be the aimed-at-the-wall case. The three
unreconciled wall sizes are untouched — this turns a wall, it does not
redesign one — and no existing golden or gallery render moves, because
`down` is the drawing they all had.

## The ladder solver (`_solve.py`)

**A chain, and nothing else.** Every network drawn in this notation in
three clean-room runs is a ladder or a ladder with a side branch: six of
the ten gallery diagrams are chains, each node joined to at most two others.
A chain can be placed without an objective. Rank along the chain gives `x`,
one line gives `y`, and the one ambiguity — which end is hot — has a rule:
the higher stated temperature, or failing numbers the end a source arrives
at, or failing that the one written first. Temperature picks the end and
only the end; sorting a whole chain by temperature would interleave a heater
in the middle of a ladder and cross its wires. Everything that is not a chain
is refused, naming the node that joins three others and saying to give it
`at`. That is the same failure mode the library had before — a diagram it
will not draw is refused by name — and it is chosen over drawing something
plausible and wrong, which is what a general placer produces when its
objective is not the reader's. The general placer is still the network layer
proper, and the table above says what it must satisfy.

**A pre-pass on a copy, not a branch inside `layout`.** `_layout` reads
`node.at` in three places, `_describe` in two, and `to_dict` writes it.
Solving on a copy leaves every one of them alone and gives all of them the
numbers, so `describe` can say `solved` on the row and `thermodraw solve`
can write the file back placed, for the author to edit from. A diagram with
every node placed goes through untouched, by identity, so the ordinary path
costs nothing.

**The pitch is measured, not fixed.** The first version placed at the
schema's habit, 220, and the immersion rack — the plainest ladder in the
gallery, seven nodes on a line — reported `nodes-too-close` on three runs
and `label-adrift` on four nodes, because its labels are long. The checker
already had the arithmetic: half of each node label and all of the branch
label, along the run. So the solver places once at the habit, lays the
result out through `compose` to learn every label's width from the same
solver and metrics the renderer uses, and places again with each run as
wide as its labels need, up to the grid, never narrower than the habit.
The branch label is centred on the run, so the wider node label sets the
room on both sides: sized to the sum of two halves, 79 and 138 wide, the
rack's technical-water label still overlapped by five. A repeated branch's
boxes count as well as its label; three in series are longer than 220 on
their own, and the furnace wall's comb ran through both of its nodes.

**A pair goes above and below, with leads.** Two branches between one pair
of nodes on one straight run is `symbols-overlap`, and the remedy is `via`;
the solver applies it, 80 off the line, leaving and arriving 48 sideways of
each node. The leads are run 3's finding: a pair brought back to the node
rather than before it arrived vertically through a boundary's wall, in
three diagrams. A third branch between the same pair keeps the straight run,
a repeated branch always does, and `side` is set to the outer side where the
author left it automatic. Vias the author wrote are kept, and a file that
drops its node `at` should drop those too, since they are absolute.

**Sources are placed, and an interior one is turned.** The solver's first
draft left sources to `layout`'s default, 37.5 out from the node, and the
hero — clean in every other respect — reported its junction label pushed 36:
the source's label sat where the junction's needed to be. The hero's authors
had put their source 104 out. So a source without `at` goes half a run out
along its angle, and `angle` 0 on any node but the hot end is turned to
arrive from above, because on the line "from the left" is the branch. That
last rule reads an author's 0 as unset, which it also is; a source wanted
from the left on an interior node would sit on the wire in any case.

**What the gallery says.** With every coordinate removed: the hero and four
of the six chains check clean; the four diagrams that are not chains are
refused by name. The rack reports one `label-adrift`, on a junction whose
authored `angle: 135` aims its label at the spot the solver put the source;
the cryostat one, on the second of two sources on one node whose angles were
chosen for a different placement. Both are the author's fields, kept, and
both are what `check` is for. The dewar has three branches between each pair
of its nodes and three sources on its middle one, and reports labels and a
diagonal source's lead across a routed leg — never a wire through a wall,
two symbols on one run, or a run too narrow. `tests/test_solve.py` pins all
ten. One more rule came from the tests rather than the gallery: a node with
a source above it and a capacitance below it has nowhere on the line for its
label — the lead above, the wire below, the run either side — and every
`side` and every axis-aligned `angle` was measured to collide. A diagonal
clears it. Since it is the solver that puts the source above, it is the
solver that turns the frame to 45, where the author left it at 0.

**What survives it, in practice.** Of the table above: the three routing
constraints hold by construction on a chain — every run is straight or a
routed pair with leads, and a wall is never crossed because nothing arrives
at a node from below; the two objectives are the label solver's, unchanged;
of the three scaffolding checks, `nodes-too-close` is unreachable because the
pitch is measured, `parallel-pair-same-side` because sides are set, and
`symbol-off-its-run` because no branch `at` is written. `network-in-pieces`
becomes a refusal rather than a warning, since a solver cannot place two
pieces relative to each other.

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

## Two things that are limits, not checks

There were three. The temperature scale was the third, and it is a
declaration since 1.0; its paragraph is kept below, marked, because the
argument for a declaration over a check is the same one the other two rest
on.

**A `rad` value is linearised, and the diagram cannot say at what.** See the
dash, above. Stating the operating point wants a per-element validity
condition, which is a schema field. A check that fired on every `rad` branch
carrying a value would be a footnote wearing a severity.

**The temperature scale was not representable, so it could not be checked.**
`units["T"]` was a free string, and `K` is byte-identical whether the author
means absolute kelvin or a rise above ambient. This was a missing
declaration, not a missing check. The library was nevertheless safe, because
it never evaluates the radiation law; the hazard is downstream. A sharp
version was tried — a `rad` branch plus a negative node temperature — and a
wall at −10 °C radiating to sky is a correct diagram that fires on it.
*Resolved at 1.0, as the declaration this paragraph asked for:* `units.T`
may be `{"unit": "K", "scale": "absolute" | "rise"}`, split on the way in so
every reader of `units` still sees text. The drawing does not change.
`describe` prints it. `--physics` is the one reader that cares, and only in
the one case a declaration makes sharp: a `rad` branch carrying a value on a
diagram declared as a rise has no absolute temperature anywhere on the page
to have been linearised at, and gets a note. An undeclared scale is exactly
that and fires nothing — the footnote-wearing-a-severity argument, kept.

**`phase` draws the plateau, not the budget.** A PCM buffer pins until its
latent energy is spent and then knees hard, and the time to that knee is
usually the reason the diagram was drawn. Saying it needs an energy beside a
temperature — a second quantity on a node kind that has one, which is a
schema change. Until then the limit is prose.

## What the format cannot state

`CLAUDE.md` lists eight of these and says each needs its argument here before
it is built. None had one. The evidence sat in `examples/gallery/FINDINGS*.md`
and in fifteen per-diagram `findings.md` files, and the decision list pointed
at a section of this record that did not exist — so the gate was unenforceable
in the one direction that matters, which is refusing to build something that
has not been argued for. This is that section.

The rule it applies is the checker's, read in the other direction. **Validation
catches diagrams that cannot be drawn; `check` catches diagrams that should not
be; and a thing stays on this list until someone shows a drawing that says
something false without it.** Wanting a field is not the standard. A diagram
that states a number the author did not mean is.

Two entries below meet that standard. Both are being built. The rest of the
list stays prose.

A note on how the first one got here: it is not one of the eight. It was found
twice, in two runs, by agents who reached for the same three words — and it
never reached the decision list at all, because nothing collected it. That is
the cost of a gate with nothing behind it.

### Two nodes that are one place

**The vocabulary can say two things are not connected and cannot say they are
the same place.** `break` is an open circuit; every other branch kind is a
resistance, a capacitance or a rate. There is no way to join two named nodes
with nothing between them.

This was pre-registered. The gallery README says every brief was chosen because
it was likely to hit a wall, and names five: advective transport, latent heat,
active refrigeration, spreading resistance, **isothermal links**. Two of the
five walls in that sentence are the two entries in this section.

Two agents hit it, in two runs, and both wrote the words. Run 2's laser diode:
"the schema has no zero-resistance link, no way to give one node two names, and
no `pipe` that would read as 'these are the same temperature by construction'
without also claiming a small resistance." It merged the baseplate into the TEC
hot face, so the word "baseplate" survives only inside a branch label, and a
reader counting parts gets seven where the brief describes eight. Run 3's
furnace wall: "a radiative link between two nodes at the same temperature is a
zero-resistance branch, which the schema cannot draw as anything meaningful."
It merged the refractory hot face into the furnace interior and asked for the
approximation to be on the record — the drawing now asserts the face is at
exactly 1200 °C, which no furnace engineer believes. That agent's own summary
of what it had done is the standard this section asks for: it *promoted an
implication into a printed fact.*

**So `link` is a branch kind, and it is an ideal short rather than a small
resistance.** Not "negligible, unchecked": an element that states nothing
checkable does not earn a glyph here. `--physics` merges linked nodes into one
before balancing, so the two ends' attachments sum where they physically do, and
it reports when their two stated temperatures disagree. That last finding is the
whole difference between an element and a decoration.

**It is a plain line, and that answers `corner`.** `g_branch_break`'s comment
already argues the geometry from the other side — "Not a plain wire: a wire says
heat flows" — and a link is exactly the case where heat flows and nothing
impedes it. The objection to be met is not the glyph but the precedent: `corner`
was removed for drawing nothing. It was removed for drawing nothing *and saying
nothing*. It put routing into the topology, so `describe` hid it, `check` skipped
it, and `--physics` folded it away before it could balance anything. A `link`
draws a line and makes a claim that can be wrong — these two are one place — and
a claim that can be wrong is the thing `corner` never had. If the line turns out
to be indistinguishable from a routed wire on a real drawing, that is an
argument about the mark, and the goldens will say.

**What it does not reach.** Run 4's cryostat wanted its two 300 K boundaries to
be one room, and a link between them makes the network a loop, which the chain
solver refuses; that is the general placer, not this. Run 2's heat pipe drops
0.4 K at load, which is neither zero nor a resistance, and still has nowhere to
go. Neither is made worse by this, and neither is fixed by it.

### A stream is a branch, and the first version of it was a node

**A medium moving through a diagram is a two-terminal element.** It enters at
one temperature and leaves at another, and the difference *is* the transfer.
`docs/schema.md` opens the node table with "A place with a temperature" —
singular — and that is the whole of the difficulty. Water through a coil is
30 °C at one end and 38 °C at the other.

It is the most-asked-for thing in four clean-room runs, and the only gap two
separate agents, two runs apart, each ranked first on their own list. Run 2's
immersion rack tried three shapes before writing any JSON, took the least bad,
and said so: 38 °C is in the data and 30 °C is *prose*, set in the same size as
the rest of the label, not a `T` of anything, invisible to `--physics`. Run 4's
battery pack drew the glycol loop dumping into a 25 °C reservoir that is really
the inlet — "there is a fact the format has no slot for, and I did not invent a
number to fill it". Two agents independently refused to fake it as an `R_conv`,
which would have named physics that is not happening.

**What makes it a schema change rather than a limit is that the silence is
total.** A furnace drawn the obvious way — strip in at 300 K and out at 1250 K
as two `fixed` nodes, with the firing rate as a source between them — reports
nothing, because `_physics.balance` asks only free nodes to close and a fixed
node is a reservoir. Set that firing rate to 99,999 kW against a 1578.4 kW load
and `check --physics` still exits 0 with no findings. Every other entry on this
list costs a number that cannot be written down. This one costs the check.

**The first version made it a node kind, and that was wrong.** It carried
`inlet`, `outlet` and `rate`, and `CLAUDE.md` defended it as "the one node that
is not a place". That sentence should have been read as a bug report rather
than an argument. Three things followed from the wrong container, and all three
go away in the right one:

- `reference` — `inlet`, `outlet`, `mean` or `lmtd` — existed **only** because
  the node had two temperatures and something had to choose which one a
  resistance saw. Give the stream two end nodes and a resistance attaches to a
  node, which has exactly one temperature. The field, its validation rule and
  `lmtd`'s unimplemented arm all disappear, and `lmtd` returns to this list as
  the "relate two elements" gap it always was.
- The author could not state what they know. A stream is characterised by a
  mass flow and a specific heat; the node took a pre-multiplied `rate`, so the
  arithmetic was the author's and the library could not check it.
- A drawing needs the two temperature nodes anyway, and the node kind put both
  numbers on one symbol, where a reader has to be told which end is which.

**The evidence had said "branch" from the start**, which is the part worth
recording. Run 4's battery pack: "Two ports, one fluid, one temperature rise."
Run 2's immersion rack named the near-miss precisely — "`flow` is a *branch*
between two ordinary nodes carrying a rate, which is a different statement" —
and its ranked list asked for "an inlet, an outlet, a mass flow and a closed
return". The first design cited both of those findings and then built the shape
neither of them described. A record that collects evidence is not enough on its
own; the evidence has to be read for what it says about the *shape*, not only
about the gap.

**So a stream is a directed branch stating `mdot` and `cp`, and the library
derives what it carries:** `q = ṁ c_p (T_to − T_from)`, from one function that
the label and `--physics` both call, so the number drawn and the number checked
cannot disagree. That is the `FOLD` table's argument, applied again. `from` is
the inlet and `to` is the outlet, so `angle` is refused as it is on `flow` — the
drawing must not be able to contradict the data.

**The sign is the one thing that must not be got wrong.** A stream is not a
conductance. A conductance carries heat from hot to cold; a stream carries it
from inlet to outlet, *up* the gradient, because the mass is doing the
carrying. In circuit terms it is a dependent source, not a resistance. The rule
is that `q` is applied as a departure at the `to` node and nothing happens at
`from`: the inlet is where the medium arrives from outside, and for the furnace
that is a reservoir. Cooling then needs no special case — water in at 80 °C and
out at 40 °C with ṁ c_p of 2 kW/K gives −80 kW, so 80 kW *arrives* at the outlet
and must leave through whatever the water is heating. Got backwards, every
heated stream reports about twice its true imbalance while looking entirely
reasonable, which is why it is asserted in a test of its own rather than left to
a passing example.

**Where the heat enters is placed by cutting the stream into segments**, not by
a keyword. Two stream branches from `in` through `mid` to `out` each demand
their own share, and a preheater on `mid` balances separately from the main zone
on `out`. That is what `reference: "mean"` was approximating, and it needs no
new machinery: it is a chain, which the solver already places. The
approximation a lumped model makes is now a node someone put on the page rather
than a word in a file.

**What it does not reach.** A stream exchanging with another stream — a
counterflow exchanger — is still two elements with nothing relating them, which
is the first of the deferred four and stays deferred; LMTD is a property of that
pair, not of either stream, which is why it left with `reference`. And `count`
is refused on a stream for now: with no `value`, `Diagram.fold` has nothing to
fold and the group line would read "4 in parallel" with no number after it,
which is the failure the `=` was added to prevent.

**The closed loop was written down here as unreachable, and it is not.** This
entry first said a pumped loop "becomes a chain that does not close, so run 2's
missing return leg is still missing". Redrawing run 2's immersion rack showed
that is wrong, and wrong in a way worth keeping rather than quietly deleting:
**it is the solver that refuses a loop, not the format.** Three nodes in a
triangle with `at` on each lay out in twelve placements and `check` reports
nothing; take the coordinates away and `_solve` refuses by name, which is the
only refusal there ever was. The immersion rack's water loop then draws clean —
the coil heating the water on the way up, the CDU cooling it on the way back
down, the pump on the inlet, and `check` silent — and run 2 could have drawn
that return leg all along. What it could not do was say what the water was at
each end of it, which is the thing this entry is actually about. A limit of the
placer was recorded as a limit of the vocabulary because nobody drew the
picture, which is the whole reason this record asks for one.

## The README hero

The picture at the top of the README was the power-device ladder in
`examples/hero.json` for every release before this. It is a good worked
example and it stays one: the schema quotes it in full with its `describe`
output, a dozen tests read it, and the clean-room builder knows how to
strip it. It was a weak hero. A junction-to-air ladder is the first
diagram anyone in electronics thermal design draws, so it says "this can
draw the obvious thing", which is not the claim 1.0 makes.

The hero since 1.0.1 is `examples/raptor.json`: one square centimetre of a
regeneratively cooled methalox throat wall at the conditions SpaceX has
stated publicly for Raptor 3, drawn from combustion gas to methane coolant.
It was chosen for three things at once. It is a diagram whose numbers were
solved before it was drawn, so `--physics` is silent on it and a wrong
number is caught, which the README shows. It carries no coordinate, so the
picture is the solver's, which is the thing 1.0 shipped. And a reader
recognises the subject, which a power device on a heatsink does not
earn.

The cost is a claim about a real engine, and the record is careful about
it. SpaceX has published a chamber pressure and a cooling architecture and
nothing else a thermal network needs. Every temperature, resistance and
heat rate in the file is an engine-class estimate, from the open literature
on high-pressure liquid engines, and `examples/raptor.md` says which figure
is a public statement, which is an estimate, and where each came from. The
diagram's title says so too, in the file, so no render of it can lose the
disclaimer. Nothing is presented as SpaceX data, and nothing should be.

A capacitance for the liner was drawn and removed. The title says steady
state, a 0.8 mm copper liner settles in well under a second, and the rail
it hung on ended under the coolant node without meeting it, because the
solver drops a rail 222 below the chain and a rail's reference is stated,
not drawn. That last is a solver fact worth a sentence of its own: a
solved diagram with a rail reads better when the rail's reference is the
cold end of the chain and the rail is left out unless something hangs on
it.

## The editor

Everything before this started from a file someone or some model wrote.
The editor is a page on the site where a person draws the network by
hand, and three decisions shape it.

**The library draws, in the browser.** The alternatives were a port of
the label solver and the twelve checks to JavaScript, or a server. A port
is a second implementation that drifts from the first the week after it
ships, and the two generated pages already live by the rule that nothing
on the site can show a glyph the code cannot draw. A server is not free.
Pyodide runs the wheel this build made, in a worker; the spike that
chose it boots in under four seconds here, loads the wheel in a fifth of
a second, and checks the largest gallery diagram with `--physics` in
under a hundred milliseconds. The classic `pyodide.js` fails to import
from a worker in Chromium; the ES module build does not, so the worker
is a module.

**A hit map, not attributes in the SVG.** The render carries no
identity: no `data-*`, no per-element id beyond clip geometry and
repeated-group forms. The choice was to add attributes to every element
the renderer writes, or to build a map of clickable boxes in Python from
what `compose` already knows and hand it across with the drawing. The
map won. The SVG's bytes stay what they are for every other reader, the
boxes come from the same placements and label rectangles the checker
grades, and a wire segment gets a box a finger can land on without the
renderer knowing a finger exists. The one thing the map needed that no
placement stated was which element a placement came from, as a number.
`ref` says it in prose, and a pair of branches between one node pair
share every other field. `Placement.index` is that number, and it is
data where `ref` is for people, which is the same argument `role` and
`ends` were added on.

**Coordinates are written in.** A file the solver placed is drawn as
the solver placed it, so the editor writes those coordinates into the
file once it is drawn. Nothing on screen changes; what a drag does
changes. Without it, pinning one node with `at` made the solver re-flow
every unplaced node around it, and a drag moved the whole chain. With
it, one node moves. That is the editor taking the solver's answer as a
starting point, which is what `thermodraw solve` exists for on the
command line.

The rest is the reader's: mouse and touch alike, a popover beside the
element rather than a panel, files in the browser's storage, a link
that carries the diagram compressed in its fragment so nothing is stored
anywhere, and a present mode for a lecture hall. What is not built is
written down in the plan that built it: offline use, pinch-zoom polish,
editing a repeated group's expanded form on the canvas, a text view of
the JSON.

### What ten minutes of using it found

Three of the four things that were wrong were the same mistake in
different clothes: a gesture that produced a file the library would
draw but the checker would object to, or a control whose words did not
describe what it did.

**A drag must not write a warning.** Dragging a path's box wrote the
drop point into `at`, and `layout` uses `at` exactly as written — it
finds the nearest segment and then throws the projection away — so the
wire jogged diagonally out to meet the box and back, and `check` said
`symbol-off-its-run` about a drawing the reader had just made by hand.
The library's own remedy names the fix: `at` on the route, or a `via`
where the box is. The editor now does both, choosing by how far the drop
landed from the run. Two details are not obvious and were found by
running the library rather than by reasoning about it. The first is that
the slide must be quantised **along the run**: `OFF_RUN` is one unit and
the page grid is ten, so snapping a point that is on a diagonal line to
the grid moves it up to seven units off that line, and the snap alone
raises the warning the change exists to remove. The second is that the
waypoints must go into the leg the drop landed on, not onto the end of
the list, or a drop near the source end of an already-bent path sends
the route to the far end and back. A run shorter than the box plus its
pad is refused rather than routed around: the route would run past both
nodes and come back, raise no finding at all, and silence
`nodes-too-close`, which skips any branch that is not straight.

**A field that grabs the cursor eats every key.** `Delete` was bound and
never fired, because selecting anything opened its card and put the
cursor in the empty Label field, and the key handler ignores every key
typed in a field. It was the correct guard defeating the correct
binding, and it failed precisely on elements with no label yet — the new
ones. Only the three creation paths focus the label now; a plain
selection hands the keyboard to the canvas.

**Two names for one drawing.** The top bar renamed the file and
`Title & units` set `title`, and nothing said which was which. They are
one name now. The checkbox that was going to say "draw this as the
diagram's title" says something else, because nothing draws a title:
`title` is what an exported page is called and what names the copy at
the far end of a share link. That is worth having and worth saying
accurately; a control that promises ink and delivers metadata is the
same defect as a remedy that cannot be applied.

**Prose is not a walkthrough.** The help panel taught the workflow in a
numbered list nobody reads. The tour teaches it in four steps on a
scratch file, each finished by making the move. Two orderings had to be
got right and both were found by using it: Escape closes the card the
step just asked you to type into before it ends the tour, and the card
must stop its own Escape from bubbling, or the document handler finds
the card already shut and ends the tour anyway. And a reader who
finishes keeps what they drew; one who skips is left with nothing,
because they asked for nothing.
