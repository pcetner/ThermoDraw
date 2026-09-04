# 14-subsea — findings

One check round, clean on the first draft, no refusal, no remedy ever needed.
That makes this a weak test of the checker and a fairly strong test of the
schema, so most of what follows is about what the *format* could not say
rather than about what the tool got wrong.

## 1. What I could not express

### The corner the vapour chamber turns

The brief says the chamber "runs up the length of the bottle to the housing"
and that "it turns a corner on the way". **The corner is not in the drawing,
and there is no way to put it there that is not a statement about the page
rather than about the part.**

The only tool for a bend is `via`, and `via` is `[[x, y], ...]` waypoints —
absolute page coordinates. That says "the wire bends at this point on the
canvas", which is a fact about ink. It is not a way to say "this physical
path turns a corner", which is a property of the object. This run's brief
forbade `via` anyway, so the question was moot here, but it would still be
unanswerable with `via` allowed: I would have been choosing where to bend a
line, not recording that the thing bends.

How misleading is the result? Mildly. No reader takes a horizontal box on a
ladder as a claim that the hardware is straight. But the brief spent a clause
on it, the diagram drops it in silence, and nothing — not `check`, not
`describe` — can tell you a stated fact went missing.

### The physical arrangement of the whole bottle

This is the bigger version of the same gap, and it is the thing I most wanted
and could not have. The system the brief describes is **vertical**: a board
low in a pressure vessel, a spreader flange under it, a vapour chamber
running *up* the length of the bottle, an oil gap and the housing bore *at
the top*, sea outside. The diagram is a 1454 x 146 horizontal strip with all
five nodes on one line at `y = 150`.

There is no way in the schema to state that two nodes are physically above
and below one another, as distinct from where they are drawn. Position is
`at`, and `at` is page coordinates. So the choice is between the solver's
line and hand-placed ink; either way the file records a layout, never a
geometry. What I did instead: nothing. I left the chain flat and put "runs
up the length of the bottle" nowhere, because there is nowhere to put it.

Honest assessment of how badly this misleads: the thermal network is exactly
right and the physical story is entirely absent. For an R-network that is
arguably fine. For a brief whose first paragraph is about where things sit
inside a vessel, half the content did not survive the format.

### Diagram-level context that is actually drawn

"one-atmosphere", "oil-filled", "steady state", "1800 m" are conditions on the
whole diagram. `title` exists and the schema says plainly it is **"not
drawn"**. There is no drawn caption, subtitle or note field.

What I did instead, and it is a bodge: I glued the depth into a node label —
`"Seawater at 1800 m"` — so that one fact at least reaches the page. The depth
is not a property of the seawater node any more than it is of the housing; it
is a property of the diagram. "one-atmosphere" and "oil-filled" had no node to
attach to and are simply gone. A reader of `bottle.svg` cannot tell this is a
subsea vessel rather than a rack-mount box, apart from the word "Seawater".

### The 60 W on the rest of the chain

Expressible, and I deliberately did not. `rate` went on the `spread` branch
only, because that is the one path the brief explicitly says carries the whole
60 W. In steady state all four carry it, but the brief asserted it once and I
recorded it once. Not a gap — noted so nobody reads the absence as an
oversight.

### What *was* expressible, and cleanly

The vendor's single number for steel plus water film is the case the schema
was built for. `mixed` — "the mechanism is combined or deliberately unstated.
A window quoted as one number for conduction *and* convection is `mixed`" — is
exactly the brief's "which part is conduction and which is convection is not
broken out anywhere, and the drawing should not pretend otherwise". Two
documents written independently landing on the same construct is the best
result in this file. Same for `pipe`, which the schema names a vapour chamber
in so many words, and `spread`, whose "cross-section grows as the heat goes"
is the brief's small footprint entering a much larger one.

## 2. Where the documentation failed me

`docs/schema.md` is unusually good — I wrote a five-node diagram from it in
one pass with no round trips. Three specific defects.

**(a) Two sentences in one document give different numbers for the same
thing.** Under *Sources*:

> "Leave `at` out and the source is placed along its own `angle`, about 40
> units from the node"

Under *Coordinates*:

> "A source without `at` is placed half a run out along its `angle`"

`describe` reports the source centre at `(90, 150)` with `board` at
`(200, 150)`: **110 units**, which is half of the 220 minimum run and matches
the second sentence exactly. The "about 40" is wrong — off by nearly a factor
of three — and it is the one a reader hits first, because it is in the section
about sources. This cost me nothing, because I let the solver place
everything, but a reader budgeting canvas space from the Sources section would
be badly out.

**(b) `mixed`'s subscript is documented as naming the one thing `mixed` exists
to say you do not know.** From the branch table:

> "`sub` | yours on the kinds whose subscript the library does not set: ...
> `mixed`, where it names the mechanism"

But `mixed` is defined four paragraphs later as the kind where "the mechanism
is combined or deliberately unstated". If the mechanism were nameable the
branch would not be `mixed`. I had nothing honest to put there and used
`"wall"` — a *place*, not a mechanism — giving `R_wall`. That reads well and I
stand by it, but the schema told me to do something it also tells me is
impossible, and it does not say what a good `mixed` subscript looks like, nor
whether it may be omitted.

**(c) The schema documents its own recommendation defeating its own checker,
and stops there.** From the `--physics` section, a `free` node is skipped

> "when a **neighbour** has none — which is what an interior junction drawn
> the way this page recommends does to the nodes either side of it"

It is admirable that this is written down. It is still a defect, and here it
was the most expensive thing in the file — see §5. The schema recommends
temperature-less interior junctions, documents that following the
recommendation blinds the numeric check on both neighbours, and offers no way
out other than inventing a temperature.

Nothing I needed was *missing*. I never wanted to open a source file. The one
moment I wanted to look at an existing `.json` was to see what people put in
`sub` on a `mixed` branch; I guessed instead, per §3.

## 3. What I had to guess at

| Guess | Right? |
|---|---|
| `spread` for the bolted-joint path | Yes — the schema's "cross-section grows as the heat goes" is the brief's footprint-into-a-larger-one in effect verbatim |
| `pipe` for the vapour chamber | Yes — the schema names a vapour chamber as its own example |
| `mixed` for the vendor's combined wall number | Yes — the schema's worked case |
| `"wall"` as `sub` on the `mixed` branch | Unverifiable. It drew `R_wall = 0.15 K/W`, which reads correctly, but see §2(b): the doc asked for a mechanism name and I gave a place name |
| Leaving `vchead` with a label and no `sub`/`value` | Right for the drawing — it drew the label alone, exactly as documented. Wrong for `--physics` (§5) |
| Omitting `rail` entirely — steady state, no capacitance | Yes. "A steady-state diagram with no capacitance has nothing to hang on it" |
| Letting the source auto-place with no `at` and no `angle` | Yes — one source, short label, hot end of the chain. It landed left of the board pointing in, which is what a ladder wants |

## 4. Did `describe` confirm the drawing was the one I meant?

Yes, and it is the most useful of the three commands here. The `network:`
block

    board --spread-- flange
    flange --pipe-- vchead
    vchead --conv-- bore
    bore --mixed-- sea
    source 0 --diss-> board

is the brief's chain, in the brief's order, with the brief's mechanisms, and
reading it against the brief line by line is a check `check` cannot do. Every
label came out `above` with no `flipped`, no `pushed` and no `OVERLAPS`, so I
know nothing was shoved. The label-text column let me confirm `q = 60 W`
landed on the spreading branch and nowhere else.

**Three things it should have said and did not:**

1. **It truncates the identifier it names elements by.** The row reads
   `branch 1 flange->vchea` — `vchead` cut to five characters to fit the
   column. The point of that column is to be the name a `check` finding will
   use. Two nodes sharing a five-character prefix would produce two rows a
   reader cannot tell apart, in the one output whose job is to disambiguate.
2. **It does not report which nodes have no temperature.** The `nodes:` block
   prints `vchead free at (790, 150) solved`, identical in form to nodes that
   carry a value. That `vchead` is the node about to silence three quarters of
   `--physics` is visible only by noticing its label column is short.
   `describe` reports where a ground landed and whether a label was pushed; it
   does not report the one property that decides whether the diagram can be
   numerically checked at all.
3. **It reports the canvas as two numbers and no judgement.** `canvas 1454 x
   146` is a 10:1 strip, illegible at any width a document page allows. That
   is arguably `check`'s job rather than `describe`'s — but no tool said it,
   so I am saying it here.

## 5. Was `check --physics` silent?

**No.** One note, and it is the headline finding of this brief:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange, bore (neighbour 'vchead' has no temperature); vchead (it has no temperature)  -> give the node, or its neighbour, a `value`, or read those nodes as unchecked
```

**One node of four was checked.** No `node-does-not-balance` and no
`rate-does-not-match` fired: `board` balanced (60 W in, 18 K over 0.30 K/W
out) and the `rate: "60"` on the spread branch agreed with its ends.

The brief's numbers close *completely*, and the tool cannot tell you so. I
verified that two ways.

By hand: 60 W through 0.02 K/W is 1.2 K, so the chamber head sits at
19 - 1.2 = 17.8 C; 17.8 - 13 = 4.8 K, and 4.8 / 0.08 = 60 W; 13 - 4 = 9 K, and
9 / 0.15 = 60 W. Every link carries exactly 60 W. Whoever wrote this brief
solved it first.

And by probe: I copied the file, added `"sub": "vc", "value": "17.8"` to
`vchead` and changed nothing else, and `--physics` came back **`0 errors, 0
warnings, 0 notes`** — all four free nodes balancing. The copy was deleted and
is not committed; `rounds.md` and the transcript carry the exact commands.

So a five-element series chain whose numbers are perfectly consistent gets one
node checked, because one junction in the middle has no quoted temperature.
The checker had everything it needed: a stated 60 W through the `spread`
branch (I put it there as `rate`), 19 C on one side of the chamber, 13 C two
links away, and two resistances. One unknown, more than enough equations. It
propagates ignorance rather than solving it.

**I left the note standing**, as the brief permits, and the reason is that
clearing it means writing a temperature the brief does not quote. 17.8 C is a
*result*, and putting a result on the page as though it were a stated property
is precisely what this diagram is meant not to do — the same instinct that
made the housing wall `mixed`. Better to ship a diagram stating only what is
known, with a note admitting what could not be checked.

The remedy text is at least honest about the third option — "or read those
nodes as unchecked". That is what I did.

## 6. Features the library lacks, ranked by what they cost here

1. **`--physics` will not solve for an unknown junction temperature.** Cost:
   three of four nodes unchecked on a chain that is perfectly consistent, and
   a diagram shipping with a note it does not deserve. This is one linear
   solve on a series chain with a stated `rate`; everything needed is in the
   file.
2. **No way to state physical arrangement separately from page layout.** Cost:
   the corner, the vertical run up the bottle, and the whole "where things
   sit" half of the brief. Both `at` and `via` are ink, not geometry.
3. **No drawn caption or diagram-level note.** Cost: "one-atmosphere",
   "oil-filled" and "steady state" are absent from the picture, and "1800 m"
   only survives because I smuggled it into a node label where it does not
   belong. `title` is explicitly not drawn, which leaves nowhere else.
4. **The solver draws one straight line and only one.** Cost: a 1454 x 146
   canvas, 10:1, out of five nodes. There is no fold, no serpentine, no
   aspect-ratio target, and no way to ask for one short of hand-placing every
   node — which is exactly the work the solver exists to remove. A six-node
   chain would be 1700 wide.
5. **Run width is set by label width, so spacing is anti-correlated with
   resistance.** The 0.02 K/W vapour chamber gets a 310-wide run; the
   0.30 K/W spreading, fifteen times the resistance, gets 280 — because
   "Bolted joint spreading" is a shorter string than "Housing wall and sea
   film" is long. Nothing is wrong, and a reader skimming for the dominant
   resistance is pulled the wrong way. Cheap to live with here; worth knowing.
6. **No way to mark a value as vendor-quoted, or as an operating-point
   result.** `mixed` carries "not broken out" to a reader who knows the
   vocabulary; nothing carries "this is what the datasheet says" as against
   "this is what I measured".

## 7. Were the solver's coordinates ones I would have chosen?

**No, and I did not move them** — the brief forbade `at`, and I want it clear
that the constraint, not agreement, is why the file has none.

The solver's choices, from `describe`: `board (200, 150)`, `flange (480)`,
`vchead (790)`, `bore (1100)`, `sea (1400)`, all on one line — runs of 280,
310, 310, 300. *Within the ladder it chose well*: hot end left, cold end
right, the boundary wall on the seawater node at the right-hand end, every run
wide enough that no label was pushed, and not one finding out of a first draft
in which I supplied no coordinates at all. As a ladder it is better than what
I would have typed by hand, and it is the strongest result in this run: the
solver placed a five-node chain unaided and the checker had nothing to say.

What I would have changed:

- **I would not have drawn it as one line.** I would have folded it — board
  and flange along the bottom left, the chamber turning up, the oil gap and
  bore across the top, sea on the right. That mirrors the hardware, gives the
  corner somewhere to be, and would come out roughly 700 x 500 instead of
  1454 x 146. At a printed column width the current canvas renders its text at
  about a tenth of body size.
- **I would have shortened the runs either side of `vchead`.** Its label is
  117 wide, wider than the 0.02 K/W it sits between deserves; the near-zero
  resistance on the page gets the most horizontal room on the page.
- I would have left everything else exactly where it is.
