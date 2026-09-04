# 15-pv — findings

Model: claude-opus-5 in Claude Code, as a subagent. Source material: the brief
and `docs/schema.md`, nothing else. Seven `check` runs on the file plus three
probe runs; three refusals; final state clean with no notes, and `--physics`
silent.

---

## 1. What I could not express

**The tilt, and with it the whole geometry of the thing.** The brief says the
module is mounted at a tilt and that "the reader should be able to tell the sky
path from the roof path at a glance". There is no field anywhere in the schema
for the physical orientation of a component or a boundary — no way to say "this
surface faces up" or "this boundary is the sky and that one is the ground".
What I did instead was use *direction on the page* as a stand-in: the two
front-side losses leave the cell as diagonals rising up-left and up-right to
boundary nodes with `"wall": "up"`, and the roof path runs along the ladder to
a boundary node with its wall below. That works, and I think it reads, but it
is a convention I invented in this file and nothing in the format records it.
A reader who assumes the library's stated habit — heat left to right, boundary
walls below — will read the two upward diagonals as "two more resistances" and
get no hint that one end of this drawing is the sky. **Mildly misleading:** the
physics is exactly right, the orientation is a private code.

**"Effective sky temperature" is drawn as an ordinary reservoir.** `sky` is a
`fixed` node at 10 °C, indistinguishable in the drawing from the ambient air at
35 °C. But an effective sky temperature is not a place — it is a radiative
equivalent, a number back-computed so that a linearised `rad` resistance gives
the right flux. The drawing states it as though you could put a thermometer
there. There is no node kind, no marking and no annotation slot for "this
temperature is an equivalent, not a measurement". The only thing carrying the
distinction is the word "Effective" in my `label`, which is prose, not
notation. **This is the most misleading thing on the page**, and it is
structural: the same gap would bite any radiation problem, which is most of
them.

**That the module exports electricity.** The brief takes the electrical output
off before handing me 900 W, so there is nothing I was *required* to draw. But
a PV module is the one device where the interesting number is the energy that
does *not* become heat, and this format cannot say "of the incident 1100 W,
200 W left as work". A `flow` source pointing away from the cell would be a
lie: work is not heat. I drew nothing and did not approximate. Worth recording
because the omission is invisible — the diagram looks complete.

**The 25 W through the back is nowhere on the page as a number.** The brief
says "the rest goes out the back", which is 900 − 275 − 600 = 25 W. `rate` is
exactly the field for it, and I left it off deliberately, because the brief
gave that path a resistance and a destination temperature but not a rate, and I
did not want to put a number on the page the brief had not written. The result
is that the two paths the brief quantified carry `q = 600 W` and `q = 275 W`
under them and the third carries nothing, which reads as if the third path's
throughput were unknown rather than "whatever is left". I would rather have had
a way to mark a rate as *derived* than choose between stating it as if given
and omitting it. Small, but a real hole in a page that is otherwise entirely
about where the 900 W goes.

**"Four identical mounting clips, side by side" comes out as two clips and an
ellipsis.** `count: 4, arrangement: parallel` is exactly right, and the group
value is drawn (`4 in parallel = 0.4 K/W`). But the schema condenses anything
over three, so the canonical `.svg` — the deliverable — shows two boxes with a
three-dot ellipsis between them. I verified this by grepping the output rather
than looking at it: the file has two `class="td-form"` groups, and the visible
one is the three-dot form while the expanded four is `display="none"`. This is
documented behaviour and the count is in the text, so it is not wrong. But a
brief that specifically says "four, side by side" produces a static picture in
which four are not side by side, and the only way to see them is a format
(`page`) that a README or a Word document cannot use. There is no per-group
override to say "draw all four, they are the point".

---

## 2. Where the documentation failed me

**The refusal message names a remedy that does not work, and calls itself a
bug.** The full text, three times:

> "node 'cell' joins 3 others ('amb', 'back', 'sky'); the solver places a
> chain, so give node 'cell' `at` yourself, and `via` on the branches that
> leave it sideways. This is a bug in thermodraw; the diagram was accepted and
> then could not be drawn"

Every clause of that is a problem.

- The remedy does not clear it. I gave `cell` an `at` — identical message. I
  added `via` to both sideways branches as well — identical message. I then
  established by probe that leaving *one* node unplaced anywhere is enough to
  refuse the file. The actual requirement is: in a non-chain network, **every**
  node must carry `at`. The message never says that, and neither does the
  schema.
- "This is a bug in thermodraw" is wrong and expensive. My file was correct and
  the limitation is documented; being told my correct file is a library bug
  cost me a round of assuming I had mis-written something before I trusted the
  probe over the message.
- The `via` half is unusable even in principle. `via` is absolute coordinates,
  and the schema says so — "`via`, and `at` on a branch or a source, are
  absolute coordinates. A file that leaves node `at` out should leave those out
  too". At the moment you are asked for waypoints, the nodes they run to have
  no coordinates. The message asks for numbers that do not exist yet.

**The schema's "Coordinates" section reads as if partial placement works, and
it does not.** It says plainly:

> "The two mix: a node with `at` keeps it, and the solver measures the next one
> from it."

That is true for a chain. For anything else, mixing is precisely what is
refused, and the sentence sent me down the brief's path with confidence. The
paragraph that follows — "Anything that is not a chain is refused, naming the
node that joins three others: give that node `at`, and `via` to the branches
that leave it sideways" — repeats the impossible remedy verbatim. Two documents
agreeing on a wrong instruction is worse than one document saying it.

**A `wire-through-wall` remedy names the value that caused the finding.** In
the probe, with both boundary nodes on their default wall:

> "turn the wall of node 'amb' with `wall: "down"` so it faces away from
> branch 1 cell->amb"

The wall *was* down — that is the default, and the node had no `wall` key. The
branch arrives from below, so `down` is the direction it runs through. The
schema's own prose gets this right ("A mount that a cold mass hangs from has
its wall above, `"wall": "up"`, so the strut arrives from below through clear
space") while the checker's remedy tells you to set the thing you already have.
Setting `wall: "up"` cleared both `wire-through-wall` warnings *and* both
`symbols-overlap` errors — four findings from one field the remedy pointed away
from.

**A `label-adrift` remedy does not say which element takes the `side`.**

> "move branch 1 cell->sky along its branch with `at`, or set `side` to "up""

The finding's subject is `source 0 -> cell`; the sentence's nearest noun is
branch 1. I guessed the source, and that was right, but it was a one-in-two
guess and the round would have been wasted the other way.

**And "along its branch" has no sense to it.** I moved branch 1's symbol along
its own diagonal, in the direction that looked like it was moving away from the
crowding, and the push got *worse*: 112 → 132. A remedy that names an axis but
not a direction is a coin flip. Worse, the finding re-rolled its *second*
alternative between rounds — round 5 offered `side`, round 6 offered moving the
source out instead — so a reader working down a list of remedies is working
down a list that changes under them.

---

## 3. What I had to guess at

- **`radin` versus `diss` for the absorbed sunlight.** The brief calls it
  sunlight the module absorbs, already net of electrical output. `diss` is
  "electrical or internal dissipation"; `radin` is "radiation arriving". I
  chose `radin`, and I believe that is right — the heat arrives as radiation
  from outside. It also puts the number in `units.q` as `q_sol = 900 W` rather
  than `P`. **Guess held**, but the schema gives no worked example of solar
  gain, and `diss` would have drawn an equally clean diagram saying something
  subtly different.
- **Whether `roof` should be `fixed`.** The roof deck under the module is
  stated as a temperature, so I made it a reservoir. Arguably a commercial roof
  deck being warmed by the module above it is not a reservoir at all. **The
  guess is a simplification**, and the drawing cannot tell you it is one.
- **Wall directions.** Guessed `up` for both sky and air *against* the
  checker's advice, on the strength of the schema's prose. Right.
- **That diagonal branches are legal with no `via`.** The schema never says a
  branch may run diagonally between two arbitrarily placed nodes; every worked
  example is axis-aligned, and all the `via` advice is about turning corners
  cleanly. I guessed that a straight line between two nodes is fine and that
  the box would rotate onto it. It is, and it does — `describe` shows
  `a229.399` and `a313.603`, and the text stayed level. **Guess held, and it is
  what made the layout work.** Two diagonals off one node need no waypoints, no
  shared segments and no corridor; axis-aligned routing out of a node with four
  attachments doubles wires along the main line no matter how you order them. I
  found this by reasoning about the wire segments before drawing, not from the
  documentation, and it deserves to be in the schema.
- **`y = 320` for the main line instead of the documented 150.** Once you place
  every node, the 150 convention is yours to keep or not; I moved the line down
  to leave room above it for the sky and the air. Nothing complained.

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Yes, and it was the only thing that could.** The `network` block did the
work:

    cell --conv-- amb
    cell --rad-- sky
    cell --cond-- back
    back --cond x4 parallel-- roof
    source 0 --radin-> cell

That is the brief, restated. `x4 parallel` on the clip line is the thing I
would otherwise have had to open a picture to confirm, and the arrow direction
on the source line confirmed the sun arrives rather than leaves. The `elements`
table printing every label in full — `Glass to sky | R_rad = 0.2 K/W | q = 275
W`, and `Mounting clip | R_cond = 1.6 K/W | 4 in parallel = 0.4 K/W` — let me
check each number against the brief without rendering anything. The folded
group value being printed there is the single most useful line in the output:
it is the one number on the page that the library computed rather than me.

Two things it should have said and did not:

- **It does not say which form of a condensed group is the visible one.** The
  row reads `symbol/cond x6` — four expanded plus two condensed. Nothing tells
  you that the `.svg` a reader opens shows the two. I had to grep my own
  deliverable for `display="none"` to find out what it looks like, which is
  exactly the kind of question `describe` exists to answer without a browser.
  One word on that row (`condensed`) would fix it.
- **It reports a wall's facing twice, in two encodings.** `wall of node 'amb'
  ground (180, 98) a270` on one row and `wall up` on another. Not wrong, just
  an angle to convert before you can compare the two.

---

## 5. Was `check --physics` silent?

**Completely silent**, and — the part that matters — with **no
`physics-not-checked` note**. The schema says a diagram whose free nodes were
all checked gets no note, so both free nodes were genuinely balanced rather
than quietly skipped:

    examples/gallery/15-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes

I had computed all four balances by hand before writing a line of JSON, because
the brief warns against adjusting a number to quieten the check: 275 + 600 + 25
= 900 at the cell, and 25 W in and out of the backsheet through four clips
folding to 0.4 K/W. Nothing was adjusted, and nothing needed to be. This is the
one part of the exercise where the library and the brief agreed without
argument.

---

## 6. Features the library lacks, ranked by what they cost me here

1. **A placer for anything that is not a chain.** Cost: three refused rounds,
   three probe runs, and every node coordinate in the file written by hand. A
   node with three branches is not an exotic network — it is what every
   component with a front and a back looks like, and this brief is the ordinary
   case, not a hard one. Second place is a long way behind this.
2. **A refusal message whose remedy works.** Cost: two of those three rounds.
   Even keeping the limitation exactly as it is, "in a network that is not a
   chain, every node needs `at`" is one sentence and would have cost nothing.
   Deleting "This is a bug in thermodraw" is free.
3. **Any way to say what a node or a boundary physically *is*** — sky, ground,
   ambient, or an equivalent temperature rather than a measured one. Cost: the
   sky node reads as a reservoir, and the tilt survives only as a page
   convention I made up.
4. **A `rate` that can be marked derived rather than stated.** Cost: the 25 W is
   missing from a diagram whose entire subject is where the 900 W goes.
5. **A per-group override for condensing.** Cost: the four clips the brief asked
   for are not four clips in the file anyone will actually open.
6. **A direction on the `label-adrift` remedy.** "Along its branch" should say
   which way along it. Cost: one round, spent making the finding worse.

---

## 7. Were the coordinates the library chose ones I would have chosen?

**The library chose no coordinates. That is the finding.** Every node position
in this file is mine, because the solver refused to place any of them. What it
did choose was the symbol positions on the runs, the label sides, and the
canvas — and there its choices were good:

- **Symbol positions:** midpoints of the diagonals and of the runs. Correct,
  and I would not have moved any of them. I moved one (branch 1, on a remedy)
  and it was worse; I put it back.
- **Label sides:** it flipped four labels — both boundary nodes to above their
  upward walls, the cell's label to below the line, and both diagonal branch
  labels to the *outer* side of their diagonals. Every one is what I would have
  picked. Putting the two loss-path labels outside the fan and the source label
  inside it is a better arrangement than I would have thought to specify, and
  it arrived free.
- **The one I overrode:** the source label, forced to `side: "up"`. That was a
  remedy, not a preference.
- **Canvas 948 × 405**, even margins, no `size` set. Right, and the schema is
  correct that setting `size` only buys you two extra findings.

What I would have moved, and did: the sun. The solver's idiom puts a source out
along its angle from the hot end, and my first drawable layout had it arriving
horizontally from the left. I moved it overhead — `angle 90`, `at [360, 190]`,
in the empty wedge between the two diagonals — because on this particular
drawing that arrow's direction is the one thing on the page with a physical
referent, and a rooftop module at solar noon is not lit from the side. That
cost one round and one forced `side`, and it was worth it.

What I would still move: nothing on the page. What I would change is not a
coordinate at all — the two diagonals rising to the sky and to the air want to
be legibly *the front of the module*, and the only tool the format gave me for
that was where I chose to put them.
