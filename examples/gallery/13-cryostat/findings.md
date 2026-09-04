# Findings — 13-cryostat

Written from `docs/schema.md` and the brief alone. No existing `.json` diagram was opened,
nothing under `src/` was read, no browser was used, and the rendered SVG was never looked at.

The diagram came out clean in two rounds with one finding, and `check --physics` is silent.
That result is not the interesting part. What follows is.

---

## 1. What I could not express

### 1a. The two 300 K boundaries are the same room, and the drawing says they are not

This is the worst thing on the page.

`vess` ("Outer vessel in room", 300 K) and `mt` ("Room-temperature mount", 300 K) are the
same physical environment — the lab the cryostat stands in. The G-10 straps run from the room
to the shield; the suspension strut runs from the magnet back to that same room. It is one
boundary with two attachments.

**What I wanted:** one ambient node, with the straps leaving one side and the strut the other.

**What I did instead:** two separate `fixed` nodes, each with its own hatched wall, 1380 units
apart at opposite ends of the canvas.

**How misleading:** materially. A reader who does not already know a cryostat will read two
distinct room-temperature boundaries, and will have no way to tell that the strut's far end
and the straps' near end are the same 300 K surface. Nothing in the drawing, in `describe`,
or in `check` says otherwise. It is the one place where the drawing states something the
brief did not.

**Why I could not do it — tested, not assumed.** Merging them makes the network a loop, not a
chain. I built the merged version as a scratch file and ran it:

```
error: DiagramError: the nodes form a loop through node 'vess'; the solver places a chain,
so give node 'vess' `at` yourself. This is a bug in thermodraw; the diagram was accepted and
then could not be drawn
```

Two separate defects in that one line, both with their own entries below (2c, 2d). The short
version: the remedy it names does not work, and the brief forbids me the one that does. So the
merged drawing was not available to me, and I did not silently approximate it — I drew two
boundaries and am telling you they are one.

### 1b. The bath boils, and nothing on the page can say how much

`he` is a `phase` node, which is right: "Its temperature is held by the phase change, not by
any boundary" is almost a quotation of the schema's own description. But a boiling helium
bath is a heat *sink* of a definite size. 0.2 W arrives from the instrumentation leads and
0.05 W from the winding — 0.25 W in total — and it leaves as helium vapour.

There is no way to state that. A `phase` node absorbs whatever arrives, silently, with no
number. I could have hung a `flow` source off it at 0.25 W, but the brief states no boil-off
and told me not to invent numbers, so I did not.

**How misleading:** moderate, and quietly so. The page shows 0.25 W entering a node and
nothing leaving it, and `--physics` does not object, because "a `phase` node is holding latent
heat this cannot see". A node that is exempt from the balance check *and* cannot state its own
load is a hole in exactly the tool that exists to catch holes.

### 1c. The MLI radiation arrives from nowhere

The brief: "Multi-layer insulation covers the shield. Radiation arriving through it adds
30 W." Physically that 30 W comes off the 300 K vessel — the node at the other end of the
G-10 straps, already on the page.

I drew it as a `radin` source labelled "Through MLI". The schema is clear this is the right
kind ("`radin` is radiation *arriving*"), and the brief phrases it as an amount arriving
rather than a resistance, so there was no `rad` value to state. But a source has one end. The
drawing shows radiation arriving at the shield from off-page, when its origin is drawn 300
units to the left.

The alternative — a `rad` branch from `vess` to `sh` alongside the `cond` straps — is a second
branch between one pair of nodes, which the schema says needs a `via` to separate, and the
brief forbids `via`. So it was doubly unavailable: no value to put on it, and no way to route
it.

**How misleading:** mild in effect, real in principle. It is the "way to relate two elements"
gap met from a new direction: I wanted to say *this source comes from that node*.

### 1d. A cryostat is concentric and the drawing is a line

Vessel contains shield contains bath contains magnet — four nested surfaces. The drawing is a
1553 × 330 strip. Nothing in the format can show containment, and I am not sure a ladder
should; but for this system the geometry *is* the explanation, and it is gone. No
approximation was attempted.

### 1e. "The strut carries load but not heat" is half-expressible

`break` says "carries no heat" well — the open-circuit symbol is unambiguous, and the brief's
requirement that "a reader has to see that the load path exists and the heat path does not" is
met by the symbol plus the words "Suspension strut". There is no way to mark a connection as
*structural*, so the load half rests entirely on the label. Probably acceptable; I record it
because I looked for a way and there is none.

### 1f. The ladder is not monotonic in temperature, and nothing cares

Along the line: 300 K, 40 K, 4.2 K, 4.5 K, 300 K. The winding at 4.5 K sits to the *right* of
the bath at 4.2 K, so on that last resistance heat flows right to left, against the convention
the schema states twice ("heat runs left to right, hottest node on the left").

I could not avoid it: the winding hangs off the bath, and the bath is in the middle of the
chain. The topology forces it. But nothing anywhere told me — see 4 and 6.

---

## 2. Where the documentation failed me

### 2a. Auto-placement of a source: two different distances, and neither is what happened

Two sentences, in two sections, about the same thing:

> Leave `at` out and the source is placed along its own `angle`, about 40 units from the node

and, in *Coordinates*:

> A source without `at` is placed half a run out along its `angle`

Those disagree with each other, and both disagree with the file. My sources landed at
(500, 40) and (500, 260) around a node at (500, 150) — **110 units** out. Not 40. Not half a
run either: the runs at that point were 300 and 520, so half a run is 150 or 260. Whatever the
rule is, the page states it twice and gets it wrong twice.

### 2b. "the far side of the node for a `to`" is ambiguous, and only the `from` case is worked

> on the far side of the node for a `to`, so the arrow arrives, and on the near side for a
> `from`, so it leaves

Far side of the node *relative to what*? The reader is given no origin. I reasoned it out
backwards from the one worked example, which is a `from`:
`{"from": "cell", "kind": "flux", "angle": 270}` "puts a hatched face on top of the cell". That
pins 270 = up, hence 90 = down, hence a `to` at `angle: 90` should sit *above* its node with
the arrow travelling down into it. The guess was right — `describe` showed
`source 0 -> sh   symbol/radin   (500, 40) a90` — but I had to draw it to find out, and "far
side" is the only phrase carrying the meaning. One worked `to` example would fix it.

### 2c. The loop refusal names a remedy that does not work

The message says "give node 'vess' `at` yourself". I did exactly that, changing nothing else,
and got the identical message back, word for word. Giving *every* node an `at` is what
actually gets past it — I confirmed that too, and the file then drew, badly: one
`symbols-overlap` and three `wire-through-symbol`, because the strut returns straight back
along the line through every symbol on it.

So the refusal's remedy, applied literally, does not clear it. Same class of defect as a
`check` remedy that cannot be applied, but the cost is higher here: a refusal exits 2 and draws
nothing, so the user cannot see the drawing to reason about it.

### 2d. A user-authored loop is reported as a bug in the library

> This is a bug in thermodraw; the diagram was accepted and then could not be drawn

It is not a bug. It is a diagram the solver does not handle, exactly as the schema says
("Anything that is not a chain is refused"), reached by a user drawing a perfectly ordinary
cryostat. Telling that user they have found an internal error, in the same breath as telling
them what to type instead, is the most confusing sentence I met all session. The refusal for a
node joining three others is documented and calm; the refusal for a loop is documented nowhere
and shouts.

### 2e. The `label-adrift` remedy does not say which element the `angle` belongs to

> move source 0 -> sh further from its node with `at`, or `angle`, which turns a node's label
> frame and is the only thing that reaches a diagonal

`at` and `angle` both exist on a source *and* on a node. Read at speed, that sentence offers
two fields on the source. Only the trailing relative clause — "which turns a node's label
frame" — reveals that the `angle` is the *node's*. I got it right, but I read it three times,
and a remedy that needs three readings is doing less work than it looks like. Something like
"…or give node 'sh' an `angle`" would be unambiguous.

### 2f. Advice that would have forced me to break the brief

> Two sources on one node, or a wide label, want an explicit `at` on at least one of them;
> left to themselves, two auto-placed sources on adjacent diagonals overlap.

I had two sources on one node and the brief forbade `at`. What actually worked, and what the
schema does not mention, is that a `to` and a `from` at the *same* `angle` land on opposite
sides of the node and cannot collide. That is a one-clause addition, and it is the answer for
anyone letting the solver place things.

### 2g. `break` node versus `break` branch, when you need both things drawn

> To tie one to the thing it is bolted to, use a `break` **branch** — the same word for the
> same thing in the other position.

That sentence is about a `break` *node*. My case was its mirror: I had a `fixed` node (the
room-temperature mount, which has a temperature and a wall) and wanted the strut drawn as a
named element beside it. `fixed` node + `break` branch turned out right, and draws both things
the brief demanded. But nothing in the schema addresses that choice directly, and a `break`
node would also have been a defensible reading of "a mount that is thermally broken" — one
that draws the mount and loses the strut.

---

## 3. What I had to guess at

| Guess | Right? |
|---|---|
| `angle: 90` on a `to` source puts it above the node, arrow pointing down | Yes — verified with `describe` before trusting it |
| A `to` and a `from` source at the same `angle` do not collide | Yes |
| `fixed` node + `break` branch draws both mount and strut; a `break` node would draw only one | Yes |
| With both chain ends at 300 K, the tie is broken by file order and `vess` goes left | Yes. The schema's rule — "the higher stated temperature, or **failing numbers** the end a source arrives at, or failing that the one written first" — covers missing numbers, not equal ones |
| A `phase` node accepts `sub` and `value` like any other node | Yes |
| `{"unit": "K", "scale": "absolute"}` is what an absolute-kelvin diagram needs | Yes, and `describe` echoed `temperatures: absolute, in K`, exactly the confirmation the brief's first line wanted |
| Stating `rate: "5.2"` would be checked against its ends under `--physics` | Yes, and it agreed |

I twice wanted to open an existing `.json` in this repository and did not: once working out the
`to`-source placement convention (2b), and once choosing between a `break` node and a `break`
branch (2g). Both were resolvable from the schema plus one `describe` run, so the gap cost me
minutes rather than correctness — but both are places where a single worked example in
`docs/schema.md` would have removed the temptation.

---

## 4. Did `describe` confirm the drawing was the one I meant?

Mostly yes, and it is the most useful thing in the toolchain.

It confirmed: all four branches and all three sources present; the `flow` direction printed as
`sh --flow-> source 1`, so I could see the cryocooler takes heat *out* rather than putting it
in; `temperatures: absolute, in K`; every label's exact text, including the derived `q = 5.2 W`
line on the straps; and — decisively — *why* round 1's finding fired, since (500, 40) and
(500, 260) around a node at (500, 150) is a label boxed in above and below. I fixed that
finding by reading `describe`, not by reading `check`.

**Three things it should have said and did not:**

1. **Which way heat flows on each branch.** It knows both end temperatures and the resistance.
   It prints neither the rate nor the direction. Had it printed `he --cond-- w   0.05 W, right
   to left`, it would have told me about 1f — the one fact about this drawing I most wanted
   confirmed and never got from any tool.
2. **The net heat at each node.** One column would have shown 0.25 W arriving at `he` and
   nothing leaving, which is 1b, invisible everywhere else.
3. **The wall direction in the word I wrote.** I set `"wall": "up"` and the row reads
   `wall of node 'mt'   ground   (1580, 138) a270`. I had to convert 270 back into "up" to
   confirm the change took. The rule that `a…` is printed "only when there is one" makes this
   worse rather than better: a default-walled node prints no marker at all, so the two cases
   are distinguished by the *absence* of a number rather than by a word.

---

## 5. Was `check --physics` silent?

**Yes, entirely.** 0 errors, 0 warnings, 0 notes, exit 0. Pasted verbatim at the end of
`rounds.md`.

Worth stating precisely, because "silent" can mean two things: there was also **no
`physics-not-checked` note**, so both free nodes (`sh` and `w`) were actually checked, not
skipped. The brief's numbers close, and the tool agrees they close. The `rate` of 5.2 W I put
on the G-10 straps was checked against its ends and agreed too.

The caveat is 1b. The one node whose numbers do *not* visibly close — the helium bath, 0.25 W
in and nothing out — is a `phase` node and exempt by design. So the silence covers two nodes
out of five: it is honest about the two boundaries (correctly exempt, they are reservoirs) and
quiet about the bath for a reason that hides a real absence.

No number from the brief was adjusted to get this result. Nothing needed adjusting: I checked
the brief's arithmetic on paper before writing a line of JSON, and it closes exactly.

---

## 6. Features the library lacks, ranked by what they cost here

1. **A boundary that can carry more than one branch** — equivalently, any topology that is not
   a chain. This cost the most: it is 1a directly, and 1a is the drawing's one false statement.
   The network layer is the general fix, but even a "these two `fixed` nodes are one boundary"
   annotation would have let me label them honestly.
2. **A load or rate on a `phase` node** (1b) — a boil-off, a latent-heat budget, anything.
   Second because it is both an expressiveness gap *and* a silent hole in `--physics`, and the
   two hide each other.
3. **A flow-direction report** — in `describe`, or as a `check` note when a branch's heat runs
   against the left-to-right convention (1f, 4.1). Cheap to compute from data the tool already
   has, and it would have caught the one thing about my layout I could not see.
4. **A refusal that can be acted on** (2c, 2d). A repair rather than a feature, but it is what
   stood between me and a better drawing.
5. **Relating a source to the surface it came from** (1c) — the "way to relate two elements"
   already on the list, met here as a `radin` with no origin.
6. **Region enclosures** (1d). Real, but I would not have used them under a no-`at` brief
   anyway, so they cost me least of the expressiveness gaps.
7. **A structural-connection marker** (1e). Nice to have; the label carried it.

---

## 7. Were the coordinates the ones I would have chosen?

Nodes landed at x = 200, 500, 1020, 1310, 1580, all at y = 150. Runs of 300, 520, 290, 270.

**What I would have moved, and did not, because the brief forbids `at`:**

- **The 520-wide run between the shield and the bath.** It is nearly twice every other run, and
  it got that way for a reason unrelated to it: freeing the shield's label onto the upper-right
  diagonal in round 2 pushed the next node away. The result reads as emphasis — the widest gap
  on the page belongs to the instrumentation leads, which carry 0.2 W, the smallest quantity in
  the diagram, while the G-10 straps at 5.2 W and the cryocooler at 35 W get narrower runs. I
  would have equalised all four at about 300.
- **The mount.** The magnet *hangs* from it. On the page it sits to the right of the winding on
  the same line, which is the one relationship the drawing gets geometrically backwards. I
  would have put it directly above the winding with the strut dropping down — exactly the
  arrangement `"wall": "up"` exists for. I set that wall (see `rounds.md`), so the hatching at
  least faces the right way even though the node does not sit in the right place.
- **The aspect ratio.** 1553 × 330 is a 4.7:1 strip for a system that is four concentric
  shells. I would have folded the cold end down and back.

**What I would have chosen, and the solver chose for me:**

- The `radin` above the shield and the `flow` below it — heat in from the top, heat out to the
  cold head at the bottom, which is how a cryostat is drawn.
- The `diss` above the winding, and the winding's own label flipping below to clear it.
- Both hot ends at the outside, cold in the middle. Given that the topology is a chain, that is
  the right chain.

So: the solver's *ordering* was mine; its *spacing* was not, and the spacing it chose
misdirects the eye to the least important path on the page. I changed neither, because the
brief's whole point was to find out what it does unaided.

---

## In one line

Two rounds, one finding, one remedy that worked, and silent physics — and a drawing that
cannot say the two 300 K walls at its ends are the same room, cannot say the bath boils off
0.25 W, and cannot say the magnet hangs from the mount rather than standing beside it.
