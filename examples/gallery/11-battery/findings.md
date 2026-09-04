# Findings — 11-battery, EV battery module on a liquid cold plate

One round of `check`, clean on the first try, no refusal, no `at` anywhere in
the file. That result flatters the library and I want to say up front that it
flatters it for a reason: this brief is a five-node series ladder with one
source and two capacitances, which is exactly the shape the solver was built
for. The interesting content below is what the drawing could not say, not how
many rounds it took.

## 1. What I could not express

### The glycol loop has an inlet and an outlet, and I could only draw one end

This is the worst one, and it sits at the centre of the diagram.

The brief says the pumped glycol loop carries 200 W away to the chiller, and
that the chiller supply is held at 25 C. Physically that is a stream: coolant
enters the plate at 25 C, picks up 200 W, and leaves warmer. Two ports, one
fluid, one temperature rise.

What I drew is `film --flow-> chill`: a single `flow` branch carrying 200 W
from the coolant film into one fixed node standing for the chiller side. The
schema is explicit that this is the only option — "a source has **one end**,
so two `flow` or `flux` sources cannot join two nodes however suggestively you
place them; heat carried from one node to another by a moving fluid is a
`flow` **branch**" — and a `flow` branch has exactly two ends, both of which
are nodes with temperatures.

**How misleading:** moderately. The heat balance is right and `--physics`
agrees with it. But the page now says the loop dumps into a 25 C reservoir,
and a reader cannot tell that 25 C is the *inlet*. The coolant's rise across
the plate — the number a cooling engineer would ask for second, after the cell
temperature — is not merely absent, it is not statable. There is no
approximation I made here; there is a fact the format has no slot for, and I
did not invent a number to fill it.

### "Both are referred to the chiller supply" is annotation, not drawing

The two thermal masses hang off `rail`, and `rail.reference` names `chill`.
The schema says outright what that buys: "`reference` must name a node that
exists, and does nothing else — it does not move the rail, route anything, or
have to be a `fixed` node."

So the sentence in the brief is recorded in a field that draws nothing. On the
page there is a rail line at y 372 and a boundary node at (1270, 150) with its
wall at (1270, 162), and no ink joins them. The rail's span happens to end at
x 1270, directly under the chiller, which reads as a tie by luck rather than
by construction. `describe` prints `reference 'chill'`, which is, as the
schema says, the only place it can be checked — and it is the only reason I
know the drawing means what I meant.

**How misleading:** low for a reader who knows the convention, real for one
who does not. I did not approximate; I stated it in the one field available
and it is not drawn.

### The eight cells are eight of everything, and only the source says eight

The module holds eight prismatic cells. Eight jelly rolls, eight cans, eight
pads pressed onto the plate. The brief lumps all of that: the 0.24 K/W path
"carries the module's whole 200 W", and the arithmetic confirms it
(48 / 0.24 = 200), so 0.24 is a module-level lumped path, not a per-cell one.

I expressed the eight only as `count: 8` on the dissipation source, which
draws `P_cell = 25 W` with `each of 8 = 200 W` beneath it. The three
resistance branches are single. `count` + `arrangement` on a branch was
available, but using it would have meant writing a per-item value — 1.92 K/W
in parallel for the jelly-roll path — that the brief never states and that I
would have had to derive and assert. I did not.

**How misleading:** mild, and it is the standard lumping. But the page shows
eight arrows arriving at one core and then one of each downstream element, so
the multiplicity dies at the first box. There is no way to say "this run of
the ladder occurs eight times" — `count` applies to one branch between one
pair of nodes, never to a stretch of the chain.

### The operating point is nowhere on the page

"At the end of a sustained fast charge, in steady state." Every number in the
brief is conditional on that — 25 W per cell is a current-dependent quantity,
and 108 C is what it produces. The only field for this is `title`, which the
schema flags as "optional, not drawn". I put the system name there. The
condition is not on the drawing at all.

The schema already knows this is a limit for `rad` branches, whose value holds
at one operating point. It is a limit for every diagram whose numbers are a
snapshot, which is most of them.

### Steady state and transient are on one page with nothing to separate them

The temperatures and the 200 W are steady-state. The two capacitances "matter
when the charge current steps" — they answer a different question. Drawn
together they read as one model. `--physics` never reads `C` (steady state,
per the schema) so it does not complain, and neither does `check`. That is the
right R-C ladder convention, and I am not asking for it to change; I am
recording that nothing in the file *says* the caps belong to a step response
and the numbers to a plateau, and there is no field that could.

### "Ohmic and entropic heat" is one arrow

Two mechanisms, one number (25 W), so one `diss` source labelled "Cell
dissipation". Splitting would have meant inventing the split. The label does
not say the heat is of two kinds. Minor, and honestly the right call, but it
is a place where the vocabulary is coarser than the sentence.

## 2. Where the documentation failed me

**`rail` is not a "neighbour" for the physics skip rule, and the schema does
not say so.** The skip rule reads: "A `free` node is skipped ... when a
**neighbour** has none [no temperature]". Two of my four free nodes — `core`
and `plate` — have a `cap` branch to `rail`, and `rail` is not a node and has
no temperature. On a literal reading, both should have been skipped and named
in a `physics-not-checked` note. Neither was; `--physics` produced no note at
all. The behaviour is the useful one and I am glad of it, but I could not
predict it from the page, and the wrong reading would have led me to conclude
that the two nodes carrying capacitance were the two nodes nobody checked —
exactly the failure mode the schema says the note exists to prevent ("a silent
skip ... hid the worst-balanced node"). One clause would fix it: *`rail` is
not a neighbour.*

**`rail.y` is the one absolute coordinate a solver-placed file still has to
invent, and the schema does not acknowledge it.** The Rail section documents
`span` as optional ("defaults to the extent of the nodes") and says of `y`
only that it "is what actually places the line". It never says whether `y` is
required, and there is no default described. Meanwhile the Coordinates section
warns: "A file that leaves node `at` out should leave those out too" — but
that sentence is about `via` and branch/source `at`, and says nothing about
`rail.y`. So in a file with no node coordinates I still had to hard-code one
number. I used 372, lifted straight from the section's own example, and it was
right only because the same page says elsewhere that the solved ladder sits at
y = 150. Nothing would have told me if I had been wrong: a rail at the wrong y
draws fine.

**`cond`, `conv`, `rad` and `contact` are never defined.** The branch `kind`
table lists nine kinds, and the prose that follows defines `spread`, `pipe`,
`mixed`, `flow`, `break` and (via the rail section) `cap`. The four everyone
will actually reach for first get no sentence. Here it cost me nothing — the
brief used the words "conduction", "contact resistance" and "convection", so
the mapping was handed to me — but "a compressible thermal pad" is only
obviously `contact` rather than `cond` if you already know the notation. If
the brief had said "the plate-to-coolant path is 0.05 K/W" I would have been
guessing between `conv` and `mixed` with no guidance. The subscript coming out
as `R_contact` in `describe` was the confirmation, after the fact.

## 3. What I had to guess at

| guess | outcome |
|---|---|
| `rail.y = 372`, copied from the schema's example | right — the ladder is at y 150, caps land at y 261, rail clears them |
| That 0.24 K/W is module-level, not per-cell | right — the arithmetic closes at 200 W, and `--physics` confirmed it |
| `contact` for the compressible pad | right — `R_contact` is the subscript the library set |
| `count: 8` on the source rather than a bare value of 200 | right — drew `P_cell = 25 W` and `each of 8 = 200 W`, exactly what the brief says |
| Leaving the source's `angle` off entirely | right — the solver put it at (90, 150), left of the hot end, arriving |
| `rate` on the jelly-roll branch only, since that is the only path the brief attributes a rate to | right — no `rate-does-not-match` |
| That `sub` on a `flow` branch is mine to set | right — `q_loop = 200 W` |

The one moment I wanted to look at something forbidden was `rail.y`: I was
about to open an existing diagram to see what value other files use. I did
not, and I am recording it because the brief asked me to. The schema has the
answer buried a section away, which is why the impulse came.

## 4. Did `describe` let me confirm the drawing was the one I meant?

Yes, and it was the deciding tool. The `network:` block is what does the work
— seven lines that I read straight against seven sentences of the brief. It
told me the `flow` branch runs `film --flow-> chill` and not backwards, that
both capacitances reach `rail`, and that the source arrives at `core`. It
printed every label's full text, so I could see `each of 8 = 200 W` and
`R_contact = 0.10 K/W` without rendering anything.

What it should have said and did not:

- **A counted source is invisible in the network block.** `source 0 --diss->
  core` gives no hint there are eight of them; the count survives only as
  label text on the element row. A counted *branch* does get it — the schema's
  own example is `j --cond x8 parallel-- ihs`. The asymmetry is documented,
  which does not make it right: the network block is the place you check
  topology, and "eight sources" is topology.
- **The `rate` on a branch is not in the network block either.** Branch 0
  carries `q = 200 W`, and that is the single most important claim in the
  diagram — it is what ties the source total to the ladder. It appears only as
  the third clause of a label string. `core --cond-- floor` would have been a
  better line if it read `core --cond, q=200-- floor`.
- **Nothing reports the rail's tie to its reference beyond echoing the
  field.** `rail: y 372, span (200, 1270), reference 'chill'` is exactly the
  right line to print, and it is the only thing standing between a documentary
  field and a silent lie. It could go further and say whether the span
  actually reaches the referenced node.

## 5. Was `check --physics` silent?

Completely, and in the strong sense: not only no warnings but no
`physics-not-checked` note, which the schema says means every free node was
checked rather than skipped. All four free nodes balance on the brief's
unmodified numbers:

- core: 8 x 25 = 200 W in, (108 - 60) / 0.24 = 200 W out
- floor: 200 in, (60 - 40) / 0.10 = 200 out
- plate: 200 in, (40 - 30) / 0.05 = 200 out
- film: 200 in, 200 out by the `flow` branch

I changed no number to get there. The brief's values were already consistent,
which is worth saying plainly: this run tests the checker against a case it
should pass, not against one it should catch.

## 6. Features the library lacks, ranked by what they cost here

1. **A stream with an inlet and an outlet.** The coolant loop is the subject of
   this diagram and its temperature rise is unstatable. Everything else on this
   list is smaller than this.
2. **A rail that is actually tied to its reference node.** "Both are referred
   to the chiller supply" is the brief's own sentence and the page cannot draw
   it. `reference` is a comment.
3. **A drawn operating point or condition.** "End of a sustained fast charge"
   governs every number and appears nowhere. `title` exists and is not drawn.
4. **Multiplicity across a run of the ladder, not one branch.** "These three
   layers each occur eight times" has no expression, so eight cells become a
   source count and then vanish.
5. **A marker for which elements answer the transient question and which the
   steady-state one.** Lowest cost here, but the two are on one page with
   nothing distinguishing them.

## 7. Were the solver's coordinates ones I would have chosen?

Largely yes, and I moved nothing — the file contains no node `at`, no branch
`at`, no `via`, and `check` was clean without them.

What it chose: five nodes on y 150 at x = 200, 480, 760, 1040, 1270. Three
interior runs of 280 and a last run of 230, which tracks the label widths —
the widest label on the ladder is "Compressible thermal pad" at 141, and the
last run carries only "Pumped glycol loop" at 105. Both capacitances drop
straight down from their nodes to the rail at y 372 and take their labels to
the `right`. The source sits at (90, 150), out to the left of the hot end. No
row is `flipped`, `pushed` or `OVERLAPS`.

Three things I would have done differently by hand, none of them enough to
override:

- **The `core` capacitance drops straight down from x 200 while the source
  lead comes in at x 90 on the same node.** That is three attachments on the
  hot end — lead from the left, ladder to the right, cap below — and I would
  instinctively have carried the cap out to x 260 or so with `via` before
  dropping. The checker says it is fine and the label went `right`, clear of
  everything, so my instinct is the one that was wrong here.
- **I would have put the two capacitance labels on opposite sides**, the core's
  to the left and the plate's to the right, so the eye reads them as a pair
  rather than as two things leaning the same way. Both went `right`. Purely
  taste; no finding.
- **The canvas is 1319 x 343** — a very long, flat strip, awkward in a document
  column. A five-node ladder cannot be anything else without folding, and there
  is no way to ask for a fold. Not a complaint about the solver, which had no
  other option.

The honest summary of this section: on a plain chain the solver's numbers are
the ones I would have written, and in the two places my hand-drawing instinct
differed, it was my instinct that was decorative and the solver's that was
correct.
