# Findings

Drawing a two-stage pulse-tube cryostat from `docs/schema.md` alone.

Result: `dewar.json` renders, `check` exits 0 with 0 errors, 0 warnings and 2
notes left standing (justified in `rounds.md`, round 4). Four rounds, one of
which was a full re-layout and one of which was spent discovering that my first
two clean reports were not real.

A disclosure first: the harness injected the project's `CLAUDE.md` into my
context automatically before I saw the brief. I did not open it, and I did not
open `src/`, `README.md`, `tests/`, or any other example - the diagram was
written from `docs/schema.md` and the brief. But the exercise was not perfectly
sealed and it would be wrong not to say so.

---

## 1. What I could not express

### 1.1 The heat carried by a path. This is the big one.

The brief gives a wattage for five of the six paths: MLI passes 0.9 W and 0.02 W,
G10 struts carry 0.6 W and 0.05 W, instrumentation wiring 0.15 W. **A branch has
no field for a heat rate.** The fields are `from`, `to`, `kind`, `label`, `sub`,
`value`, `via`, `at`, `angle`, `side`, and `value` is spent on the resistance.
Confirmed rather than assumed - adding one is refused outright:

```
error: branch 0: unknown field 'watts', 'heat' (did you mean 'at'?), 'nonsense'.
Expected: angle, at, from, kind, label, side, sub, to, value, via
```

**What I did instead:** put the number in the free-text `label`, so the boxes read

```
MLI blanket, 0.9 W          Instrumentation wiring, 0.15 W
R_rad = 289 K/W             R_cond = 239 K/W
```

**How misleading that is, specifically.** Badly, in four separate ways, and I do
not think it should pass as an equivalent:

- It is set in the user-label line, in the user-label weight, so it reads as part
  of the *name* of the path rather than as a measured quantity. "MLI blanket,
  0.9 W" reads like a part number. The library's own line-2 typography - italic
  symbol, roman unit, matched size - is exactly what distinguishes a quantity
  from a name, and this number does not get it.
- It carries no symbol. Line 2 says `R_rad = 289 K/W`; the 0.9 W has no `q =`
  in front of it, so nothing states that it is a heat rate rather than a rating,
  a limit, or a measurement uncertainty.
- **It is completely unchecked.** The whole point of the `units` block - "a value
  whose quantity has no entry here is refused, so that a number never reaches the
  page without its unit" - is bypassed. I typed the string "W" myself. Nothing
  would have stopped me typing "0.9 mW", or writing 0.9 in a diagram whose
  `units.q` was kW.
- It widens the label. "Instrumentation wiring, 0.15 W" is a 168-wide label where
  the name alone would have been about 120, and label width is what sets node
  spacing. I paid for it in canvas.

**What I considered and rejected.** A `flow` source at each node carrying the
same wattage. That would be *wrong*, not merely ugly: `flow` attaches to a node,
so six of them at the shield would say six separate boundary crossings rather
than "this branch carries this much", and the shield's arrivals and departures
would double-count against the cryocooler load already drawn. I would rather the
numbers be typographically demoted than topologically false.

**What I wanted:** an optional `q` on a branch, drawn small on the wire beside
the box with an arrowhead giving direction, validated against `units.q` like
everything else. A resistance network with the load on each path is the normal
deliverable of a cryostat heat-load budget; the resistances alone are half the
document.

### 1.2 That the 1.2 W of Joule heating comes from the HTS leads

The current leads do two things at once: conduct 1720 K/W from vessel to shield,
and dissipate 1.2 W into the shield. I drew a `cond` branch and a separate `diss`
source at `sh`. That is correct physics and correct topology, but the two
elements are **unrelated on the page** - nothing links "HTS current leads" the
branch to "HTS lead Joule heating" the arrow except that I chose similar words.
A reader has to notice the wording. There is no way to bind a source to the
branch that produces it. Mildly misleading: the drawing is true, it just does not
say the thing the brief said.

### 1.3 That the two cryocooler stages are one machine

Stage 1 (35 W at the shield) and stage 2 (1.5 W at the cold mass) are two `flow`
sources pointing away from two different nodes. Nothing in the schema can say
they are the two stages of a single cold head - no grouping, no enclosure, no
shared label. The drawing reads as two independent refrigerators. That is a real
misstatement about the system, and I could not avoid it. Marking them `q_1` and
`q_2` and naming them "Cryocooler stage 1 / 2" is the entire mitigation, and it
is text, not structure.

### 1.4 That the three levels are nested

A cryostat is physically nested: cold mass inside shield inside vacuum vessel.
The network is a chain, and a chain is what I drew. Containment is not
expressible. This one I think is fine - a thermal network is a network, and
nobody reading one expects it to be a section drawing - but it is the reason the
schema's own to-do of "region enclosures" would earn its keep here.

### 1.5 Direction of heat flow

Nothing on the drawing states that heat runs vessel -> shield -> cold mass. It is
inferable from 300 K / 40 K / 4.2 K and from the left-to-right convention, and
the source arrows do point. But the six resistive paths are undirected, and in a
diagram whose whole subject is *where the load goes*, that is felt. Related to
1.1: a `q` on a branch would have carried the direction for free.

### 1.6 Nothing else was blocked

Temperatures, capacitance, the fixed boundary, the reference rail, the two
annotation arrows and the six paths all went in cleanly. `"units": {"T": "K"}`
was accepted without complaint even though the schema's only example is degrees
Celsius, which is what I hoped and not what I could verify in advance.

---

## 2. Where the documentation failed me

### 2.1 The `via`-on-a-rail-branch sentence is wrong, and it cost me a re-layout

> "A branch naming `rail` as its `to` drops straight down from the other end,
> meeting the line directly below that node. Give it `via` if you want it
> somewhere else: waypoints work on a capacitance exactly as they do on any other
> branch, **which is how you free up the space directly under a node that already
> has too much attached to it.**"

That last clause describes my exact situation - the cold mass had two lane wires
arriving vertically in the column the capacitance wanted - and it does not work.
The waypoints move the *wire*, but the branch still terminates at the rail point
directly below the node, so `"via": [[1400, 300]]` bought me a 480-unit diagonal
from (1400, 300) to (1300, 780) instead of a clear vertical. `describe` reported
it as `a101.768`; `check` said nothing.

Either the sentence is wrong or the feature is. Read literally against the
preceding sentence ("meeting the line directly below that node") the behaviour is
consistent, but then the promise about freeing up space is unachievable and
should be deleted.

### 2.2 The parallel-pair advice disables the check it is about

> "**A parallel pair needs `side`.** Both branches are horizontal, so both labels
> choose "up" and the lower one lands inside the loop. Set `"side": "up"` on the
> upper branch and `"side": "down"` on the lower one."

and

> "`parallel-pair-same-side` | note | two branches between the same two nodes,
> both labelled on the same side"

Setting `side` on a branch removes it from `parallel-pair-same-side` entirely,
even when the labels do land on the same side. I verified this directly (round 3,
probes C/D/E): three parallel branches with no `side` produce three notes; the
same three with `"side": "up"` on all three produce zero, with `describe`
confirming all three labels still land `above`.

Nothing on the page says this. The consequence is that following the documented
habit turns the check off, and a first-time author - me, twice - gets a clean
report and believes it. Suppression-on-explicit-`side` may well be deliberate
(you asked for it, you own it), but then it belongs in the table, and the note
should probably still fire when the *drawing* has the problem regardless of who
chose the side.

### 2.3 The remedy for that note has no fixed point past two branches

> "-> set `side` to "down" on the lower of the two"

Two sides, three parallel branches. Each gap here carries three. Applying the
remedy literally to all six reported pairs (round 3) leaves branches 0 and 1 both
`below` and 3 and 4 both `below` - the condition unchanged - and reports zero
notes only because of 2.2. The remedy text should say something a three-path
network can actually do, or the note should be phrased per-group rather than
per-pair.

### 2.4 Nothing describes a source's lead, so `at` is guesswork

> "A lead is drawn from the symbol to the node whichever you choose, so `at` only
> has to be roughly right."

"Roughly right" is fine for the arrow, but the lead is a wire, and wires collide
with labels and cross other wires. There is no statement of whether the lead is
drawn straight from `at` to the node (so a diagonal `at` gives a diagonal lead
that can cut across a label) or routed orthogonally. I placed three sources by
reasoning about a straight line and then confirming after the fact with
`describe`. It came out right; I could not have known in advance.

### 2.5 No numbers for the label box, so "space labels, not symbols" is unusable up front

> "Space labels, not symbols. A box is 84 wide, but `R_cond = 0.000877 K/W` is
> over twice that, and it is the label that decides how far apart two nodes have
> to be."

Correct advice, and the section that follows is the most useful part of the page.
But there is no figure for label *height*, and no figure for the clearance the
solver leaves between a label and its box. I chose 150 units of vertical
separation between lanes by guessing; `describe` later told me a label is 33 tall,
which is the number I needed before I started, not after. One sentence -
"a two-line label is 33 tall and sits about 16 clear of its symbol" - would have
removed most of the arithmetic I did blind.

### 2.6 Small gaps

- Nothing says whether a `units` value is validated against a known list. It is
  not; `"T": "K"` is accepted. Worth one clause, since the surrounding paragraph
  is emphatic about units being policed.
- Nothing says what happens when two branches from the same node run down the
  same column - here, four places where the y=160 lane's vertical overlies the
  y=310 lane's vertical at the same x. I believe this is correct and reads as a
  bus, since both wires belong to the same node, but I could not confirm it, and
  `check` has no finding for coincident wires.
- The `flipped` and `pushed N` markers in `describe` are shown in the sample
  output but never defined. I inferred "the solver had to work for it" and
  treated `pushed 8` as tolerable and `flipped` as a smell. That inference drove
  a real decision (round 3, rejecting the literal-remedy layout partly because it
  flipped the capacitance label) and I have no idea whether it was right.

---

## 3. What I had to guess, and whether the guess held

| Guess | Held? |
|---|---|
| `"units": {"T": "K"}` accepted despite the example using degrees Celsius | Yes |
| `flow` + `from` is how you say "the cryocooler removes 35 W here" | Yes - it is the only construct offered, and `describe` renders it `source 1 sh ->` |
| `diss` (not `flow`) for Joule heating appearing in the leads | Yes - "electrical or internal dissipation" is exactly that |
| Wattages into `label` text, having no other slot | Held mechanically; misleading typographically (1.1) |
| `"angle": 135` on a node to escape a four-way junction | Yes - both `sh` and `cm` labels landed `above left` with only `pushed 8` |
| Source `at` placed so the lead would not cross a wire | Yes, but only confirmed after the fact |
| `rail.reference: "v"` on a `fixed` node not on the rail line | Yes - schema says it is documentary, `describe` echoed it |
| 150 units between lanes is enough for a two-line label | Yes, by luck; see 2.5 |
| `"via": [[1400, 300]]` frees the column under the node | **No.** See 2.1 - the one guess that cost a round |

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

**Partly, and it was decisive once.** It is the only reason this diagram is not
shipping with a 480-unit diagonal across the bottom-right corner: `check` gave me
a clean bill twice on a drawing that was wrong, and the single token `a101.768`
on the capacitance row is what caught it. It also let me verify the label count
(3 nodes + 7 branches + 3 sources = 13, exactly as the page promises), that every
symbol sat at the coordinate I intended, and that no label had been dropped.

**What it should have said and did not:**

1. **The wire routes.** It reports `wire x19` and not one coordinate. Every
   geometric decision I made was about wires - does this `via` go where I think,
   does that source lead cross that lane, do these two verticals lie on top of
   each other - and `describe` is silent on all of it. Note how I found the one
   real error: not from a wire, but by *inferring* a bad wire from a symbol's
   angle. A `wires:` block listing each polyline, by branch, would have caught it
   directly and would have answered 2.6's overlap question too.
2. **The topology, grouped by node.** Elements are listed in file order. To check
   the shield against the brief - three paths in, three out, one dissipation in,
   one flow out - I counted rows by hand. A per-node summary is the thing that
   actually answers "is this the network I meant", and it is the one question
   `describe` is advertised as answering.
3. **The values, structurally.** It prints label text, which is what I typed. It
   cannot catch me having typed 716 where I meant 761. A column of
   `kind / R / from / to` would let a reader diff against a heat-load table.
4. **Arrow direction in words.** `source 0 -> sh ... a315` requires converting
   315 degrees, clockwise, y-down, in your head. "arrow up-right, into sh" costs
   nothing.
5. **A definition of `flipped` and `pushed N`.** See 2.6.

---

## 5. Features the library lacks, ranked by what they cost here

1. **A heat rate on a branch.** Cost: five of the brief's numbers demoted from
   checked quantities to free text, and the diagram cannot state its own subject -
   the heat-load budget. Everything else on this list is a distant second.
2. **A rail branch that meets the rail under its last waypoint** (or any way to
   move where a capacitance lands). Cost: one full re-layout, round 2. The
   documentation actively promises this works.
3. **A `parallel-pair-same-side` that survives an explicit `side`, and a remedy
   that works for three paths.** Cost: two false-clean reports, and a round of
   probes to find out. This is worse than a missing check, because it teaches you
   to trust a clean report.
4. **Grouping / enclosure.** Cost: the drawing says "two refrigerators" where the
   system has one two-stage cold head (1.3), and cannot show the nesting (1.4).
5. **Binding a source to the branch that produces it.** Cost: the HTS leads'
   conduction and their Joule heating are two unrelated marks on the page (1.2).
6. **Wire routes in `describe`, and a coincident-wire check.** Cost: every
   routing decision was made blind and confirmed by inference. See section 4.
7. **Automatic layout.** Every one of the ~30 coordinates in this file is mine,
   and the two re-layouts were re-typing coordinate blocks. The schema is honest
   that this is 0.3 work ("Every node needs `at` in 0.2"), so it is last on the
   list rather than first - but it is where the time went. For a network this
   shape - a chain of three levels with a fan of parallel paths in each gap - the
   lane assignment is mechanical, and I did it by hand twice.
