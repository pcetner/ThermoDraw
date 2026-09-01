# Findings — two-phase immersion rack

Written after one round. `check` was clean on the first draft: 17 labels, 0
errors, 0 warnings, 0 notes, exit 0. No remedy was ever offered, so the
question "does the remedy work when applied literally" has no answer from this
exercise — nothing fired.

That is the good news and it is real: a diagram of seven nodes, six branches
and four sources, in a physical domain the library was not written for, drew
clean from `docs/schema.md` alone with no traceback and no iteration. The rest
of this document is what the clean report could not tell anyone.

**Disclosure.** I did not read `src/`, `tests/`, `README.md`, `CHANGELOG.md`,
any other file under `examples/`, or any existing `.json` diagram. The
repository's `CLAUDE.md` was injected into my context automatically by the
harness before I was given the brief, so I had seen it without choosing to.

---

## 1. What I could not express

Ranked by how much damage it does to this drawing.

### 1a. Advective transport — heat carried between two nodes by a moving fluid

This is the big one, and it is the subject of the brief.

> "Inside the coil runs technical water, entering at 30 C and leaving at 38 C.
> It carries the heat away by flowing, not by conducting: the water physically
> transports 3.2 kW from the rack to the coolant distribution unit."

**What I wanted:** an element between the condenser coil and the technical
water at the CDU that says "3.2 kW moves along here because the water moves",
with no resistance and no temperature drop implied by a resistance.

**What the schema offers:** six branch kinds — `cond`, `conv`, `rad`,
`contact`, `cap`, `break`. Four of them are resistances that demand a value in
K/W; `cap` is storage; `break` explicitly "carries no heat". A source is
attached to exactly one node — `to` or `from`, never both — so `flow`, which is
the right *quantity*, cannot be a *link*.

**What I did:** two separate `flow` sources nose to tail across a deliberate
gap — `{"from": "coil", ..., "at": [1350,150], "angle": 0}` and
`{"to": "tw", ..., "at": [1560,150], "angle": 0}` — both `q_w = 3200 W`, both
pointing right.

**How misleading: badly.** The network is topologically severed at that point.
The drawn graph is in two disconnected components: `{j, ihs, sat, coil}` plus
the rail, and `{tw, fac, air}`. A reader tracing the wire finds the diagram
stops at the condenser coil and a second, unrelated diagram starts at the
technical water. The only thing asserting they are the same 3.2 kW is that I
typed the same number twice; nothing in the file relates them, and nothing in
the toolchain knows they are related. It is a picture of a thermal network with
the pipe cut out of it.

I checked, deliberately, whether the library minds a disconnected graph. It
does not. `check` has no connectivity finding among its nine codes and
`describe` never prints an edge list, so the single most significant fact about
this drawing is invisible to both instruments.

### 1b. An ideal link — zero resistance, and the phase change itself

> "The condensation itself happens at constant temperature - this is the latent
> heat of the fluid being given up, 3.2 kW of it, with no temperature drop
> across the phase change at all."

**What I wanted:** boiling surface and condensing surface joined by something
that carries 3.2 kW at zero delta-T and is labelled as a phase change.

**What I did:** collapsed both onto a single node, `sat`, "Boiling dielectric,
T_sat = 49 °C". Pool boiling arrives at it from the spreader; the condensing
film leaves it to the coil.

**How misleading: the numbers are right, the physics is deleted.** Zero delta-T
between two places *is* one node, so this is the correct answer and I am
content with it. But it is an answer arrived at by erasure. Nothing on the page
says a phase change happens; a reader sees a middle node between two convection
boxes and reads it as a lump of fluid. The 3.2 kW of latent heat — the entire
reason a two-phase system exists — has no symbol, no label and no place to
stand.

The alternative was a `cond` branch with `"value": "0"`. The schema would
accept it, and it would print `R_cond = 0 K/W` inside a section-hatched box,
i.e. a solid metal conductor. That is worse, so I did not do it. There is no
third option.

There is also no boiling symbol and no condensing symbol. I used `conv` for
both, which is defensible — both are convective coefficients and the streamline
interior is honest — but a nucleate-boiling coefficient of 0.00375 K/W and a
filmwise-condensation coefficient of 0.0028 K/W are drawn identically to a fan
blowing on a heatsink. The mechanism is carried only by my free-text label.

### 1c. A stream has two temperatures; a node has one

Technical water enters the coil at 30 °C and leaves at 38 °C. A node has one
`value` and one `sub`.

**What I did:** put the outlet in the data (`"sub": "out", "value": "38"` ->
`T_out = 38 °C`) and shoved the inlet into free text in the label:
`"label": "Technical water, 30 C in"`.

**How misleading: mildly, and it looks bad.** The rendered block reads
"Technical water, 30 C in" over "T_out = 38 °C". Two temperatures on the same
node, set in two different weights, one of them typeset from `units.T` and one
of them prose with a hand-typed "C" that is not even the degree sign. Only one
of them is data. If someone later changes `units.T`, half of that node updates.

I considered a second node for the 30 °C return and rejected it: the return leg
carries the water back to the rack, and drawing it as a wire would close a loop
that is not a thermal-resistance loop, which is a bigger lie than the one I
told.

### 1d. Multiplicity — "eight of these, in parallel"

**This is the one genuinely wrong-looking number in the drawing, and I want it
read as such.**

Junction-to-spreader is 0.0275 K/W **per processor**, carrying **400 W**
(72 - 61 = 11 K = 400 x 0.0275). Everything downstream of the spreader is
rack-level, carrying **3200 W** (61 - 49 = 12 K = 3200 x 0.00375). The network
is eight parallel legs collapsing into one.

**What I wanted:** `"count": 8` on the branch, or any collapsed-parallel
notation.

**What the schema offers:** nothing. There is no repeat count, no xN, no way to
say two branches are the same branch.

**What I did:** left the value at the brief's `0.0275`, wrote the label "Each
of 8 processors", and put a single `P_chip = 3200 W` dissipation at the
junction.

**How misleading: this is the worst number on the page.** A reader who
multiplies the source by the first resistance gets 3200 x 0.0275 = 88 K and
expects a 137 °C junction, not the 72 °C the node states. The rack-level
equivalent is 0.0275 / 8 = 0.0034375 K/W — a number the brief never gives, so
writing it would have been exactly the silent substitution the brief forbids. I
chose to keep the stated number and carry the discrepancy in a label, and to
report it here.

Neither instrument can catch this. The schema says so plainly: "Two things it
does not check: whether the numbers are right, and whether the network is the
one you meant."

### 1e. Unit prefixes

`units` is fixed per quantity and "Every `value` is a **string** ... you get
exactly the digits you typed". The brief says **240 kJ/K** and **3.2 kW**. The
diagram says `C_fl = 240000 J/K` and `P_chip = 3200 W`. There is no
`"C": "kJ/K"` that would let me write `240`, and no scaling.

**How misleading: not at all; just unreadable.** But a six-digit capacitance is
a wide label, and the schema's own headline advice is "Space labels, not
symbols". The library's unit policy is fighting its own layout advice.

### 1f. No enclosures, so no idea where the rack stops

The rack, the CDU and the dry cooler are three separate physical boxes with
three different owners. `docs/schema.md` has no region, group, enclosure or
frame of any kind — the word does not appear. The result is one undifferentiated
chain from junction to ambient with no indication of where the immersion tank
ends, where the facility begins, or which loop the pump is in. The pump's 800 W
lands on a node whose membership in the technical water loop is something the
reader has to infer from my label text.

### 1g. One thing that was not a gap

Pump shaft work degrading to heat in the fluid is `diss` — "electrical or
internal dissipation". I hesitated over whether an 800 W pump belongs as a
`diss` or a `flow`, decided `diss` because the work appears *at* the fluid
rather than travelling to it, and the schema's own gloss for `diss` —
"dissipation *appearing* at a node rather than travelling to it" — settled it
in one sentence. Recording this as a case where the documentation did its job.

---

## 2. Where the documentation failed me

The schema is good, and I want that on the record before the complaints: it is
the reason this drew clean on the first attempt. Six holes.

**2a. `size` is a documented finding about an undocumented field.** The check
table has two codes that reference it —

> `off-canvas` | error | the drawing runs past a `size` you fixed
>
> `frame-off-centre` | warning | the `size` you fixed leaves lopsided margins

— and the "Shape" section, which announces itself as "the whole format", has no
`size` key. Two of the nine findings are about a field the schema never
defines: not its name in the object, not its type, not whether it is
`[w, h]`. I could not have used it, and if either finding had fired I would
have had nowhere to look.

**2b. It never says whether `value` is optional on a branch.** The table gives
`value` with no annotation. `break` is singled out as taking none ("it takes
**no `value` and no `sub`**, and one given a value is refused"), which by
contrast implies the others require it, but never says so. I needed exactly a
value-less labelled branch — the coil wall to water path, which the brief
describes and gives no number for — and could not tell from the schema whether
it was legal. I did not try it, because the brief scopes me to the schema and
the schema is silent. Node `value` has the same silence, but the `break`
paragraph rescues it: "A `break` has no temperature to state, so `sub` and
`value` are usually left off".

**2c. Nothing about disconnected graphs.** I produced one on purpose (1a) and
had no way to know in advance whether that would be refused, warned, or
ignored. It is ignored. I established that by rendering, not by reading.

**2d. The source default-placement sentence needs a reference frame.**

> "Leave `at` out and the source is placed along its own `angle` with room for
> its label — on the far side of the node for a `to`, so the arrow arrives, and
> on the near side for a `from`, so it leaves."

"Near" and "far" relative to *what*? Presumably the direction the angle points,
but the sentence never says, and getting it backwards puts an arrow on the
wrong side of the node. I gave explicit `at` to both `flow` sources to avoid
finding out, and let the two `diss` sources default. Both defaults were right,
which I could only confirm from `describe` afterwards.

**2e. The sample `describe` output in the schema prints `nodes:` twice.** The
documented sample lists `nodes:`, then `rail:`, then `nodes:` again with
identical content. The real thing prints it once. Small, but that block is the
sample a first-time reader calibrates against, and I spent a moment looking for
the second block that was not there.

**2f. Minor: `"to": "rail"` is documented and `"from": "rail"` is not.** The
asymmetry is unexplained. I did not need it.

---

## 3. What I had to guess, and whether the guess was right

| Guess | Right? |
|---|---|
| 340 units of node spacing instead of the documented 220, because my labels are the long kind the schema warns about (`R_conv = 0.00375 K/W`) | **Yes** — but untested. Nothing fired, so I have no idea how much margin I had. I would rather have been *told* the numbers than have to break the drawing to see them. |
| Rail at `y = 380` with nodes at `y = 150`, copied off the hero's 372/150 | **Yes** |
| Boundary node `air` on the main line at `y = 150` rather than down on the rail, with `"angle": 90` copied from the hero's ambient node | **Yes.** The schema explicitly licenses it: "A `fixed` node may sit anywhere". |
| `conv` for a plate heat exchanger and for a dry cooler | **Yes, I believe** — both are overall fluid-side coefficients and streamlines are the honest interior. But the schema gives no guidance at all on which kind fits a heat exchanger, and I would have liked one worked line. |
| `conv` for pool boiling and for filmwise condensation | **Defensible, not right.** See 1b. |
| That a pair of `flow` sources could stand in for a transport link | **No.** It renders, it checks clean, and it does not mean what I need it to mean. |
| That a `diss` source and a node label would not collide at node `tw`, which has an arrow coming in from the left, a branch going out right, and a pump coming down from above — four attachments | **Yes**, and the solver handled it without being asked: `describe` shows the node label **flipped** below the line on its own. |

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Mostly, and it is the most useful thing in the toolchain.** It is the only
reason I can make claims about this drawing without having opened it. Four
things it told me that I could not have known otherwise:

- The exact rendered label text with units appended — which is how I know
  `C_fl = 240000 J/K` sits on the page, and how bad that looks (1e).
- Which side each of the 17 labels went, and its measured box.
- That node `j` and node `tw` **flipped** to the far side of the line on their
  own, and that `source 3` flipped too. I set neither `side` nor `angle` on any
  of them.
- A placement census — `symbol/flow x2`, `symbol/diss x2`, `wire x16` — that
  let me confirm the element counts against what I wrote.

**What it should have said and did not:**

1. **Connectivity.** My drawing is in two disconnected components and
   `describe` cannot say so. It lists nodes, and it lists elements, and it never
   once states which node is joined to which. A `components: 2` line, or a
   degree per node in the `nodes:` block, would have made the severed transport
   in 1a a visible fact instead of an assertion I have to make in prose here.
   This is the single highest-value line it is missing.
2. **What attaches to each node.** I reconstructed the topology by reading the
   `branch N a->b` rows and matching ids by eye. Fine for seven nodes; the
   schema is aimed at ladders bigger than this.
3. **The canvas figure is unexplainable from the schema.** `canvas 2438 x 348`
   for a drawing whose content spans y = 150 to y = 380. I can back out that
   the difference is padding plus label extents, but nothing documents it — and
   `off-canvas` is an *error* graded against a `size` I would have had to guess
   (2a).
4. Nothing about whether the numbers hang together, which is fair and stated —
   "it reports, it does not judge" — but it means 1d passes both instruments in
   total silence.

---

## 5. Features the library lacks, ranked by what they cost me here

1. **An advective / transport element.** Cost: the diagram is cut in half. Every
   other item on this list is cosmetic beside it. A pumped loop and a boiling
   loop are the whole subject of the brief, and the library cannot draw the leg
   that makes either one a loop. Shape of the fix:
   `{"from": "coil", "to": "tw", "kind": "advect", "value": "3200"}` — an arrow
   along the wire, a `q` not an `R`, no box, no temperature drop implied.
2. **Multiplicity on a branch.** Cost: the one misleading number on the page
   (1d). `"count": 8`, rendered as `x8`, and a checker that knows the effective
   value is R/8 and can say so when the temperatures disagree with it.
3. **An ideal zero-resistance link, and a phase-change symbol.** Cost: the
   defining physics of a two-phase system is invisible (1b). Even without a new
   glyph, a labelled wire between two nodes at the same temperature would have
   let me write "latent heat, 3.2 kW, no delta-T" on the thing itself instead of
   deleting it. Boiling and condensing are two mechanisms this brief needed and
   the vocabulary does not have; both are currently `conv`.
4. **Unit prefixes.** Cost: `240000 J/K` and `3200 W` where the source says
   240 kJ/K and 3.2 kW, on a page whose layout advice is "space labels".
5. **Region enclosures.** Cost: no rack / CDU / facility boundaries, so the
   drawing cannot show where responsibility changes hands (1f).
6. **Two temperatures on a stream, or a stream element.** Cost: "30 C in" is
   prose in a label (1c).
7. **Connectivity, in both instruments.** Cost: nothing caught the disconnected
   graph I built on purpose. A `check` finding and a `describe` line.

---

## 6. The summary judgement

A clean report on the first attempt, from documentation alone, in a domain the
library was not designed for. That is a strong result for `docs/schema.md`.

But the report is clean about the wrong things. `check` graded the typography
of a drawing whose network is severed in the middle, whose first resistance is
off by a factor of eight against its own source, and which nowhere indicates
that the fluid boils. All three are outside what it claims to grade, and it
says so honestly — "It reports how the drawing reads, not what it says." The
gap this exercise found is not in the checker. It is that the symbol vocabulary
covers conduction networks and this system is a fluid loop, and the four
mechanisms it can draw are not the four mechanisms that move the heat here.
