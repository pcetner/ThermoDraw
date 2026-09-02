# Findings — 05-laser-diode

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent).
Documentation available: `docs/schema.md` and `brief.md`, nothing else.
Result: `check` exits 0, 0 errors / 0 warnings / 0 notes, in two rounds.

The diagram is clean. Here is what it does not say.

---

## 1. Things I could not express

### 1a. The 80 W and the 800 W/cm² are the same heat, and the drawing says they are two

**This is the worst one.** The brief states both: the bar "dumps **80 W** as
waste heat", and "the waste heat leaves the junction as a **heat flux of
800 W/cm2** through the emitting face". Same joules, described twice — once as
a total, once per unit area.

The schema has `diss` (a `P` in watts, arriving) and `flux` (a `q″` in W/cm²,
which may leave). It has no way at all to say that one source *is* the other
expressed per unit area. There is no `area` field on a node or a source, no
grouping, no cross-reference between sources, no "annotation" flavour of a
source that decorates a quantity already stated rather than adding a new one.

What I did: I drew both. Source 0 is `diss`, `P_d = 80 W`, arriving at the
junction. Source 1 is `flux`, `q″_e = 800 W/cm²`, leaving the junction upward
off a hatched face.

**How misleading this is: quite badly, and in a specific way.** A reader who
knows the vocabulary reads that node as: 80 W appears here, an unquantified
amount leaves upward through a hatched face at 800 W/cm², and separately 80 W
goes right into the semiconductor. That is an energy balance that does not
close, drawn on purpose. The picture claims the junction is a three-way node
when it is a two-way one. Anyone summing the arrows gets the wrong answer.

The alternatives were both worse in a way I could not accept:

- Drop the `flux`, and the diagram silently loses the one number the brief
  calls out as the point of the whole example — "an extremely high flux over a
  very small area" is the reason this system needs a spreader at all.
- Drop the `diss` and keep only the `flux`, and the diagram never states 80 W
  anywhere, which is the number every other resistance in the stack is sized
  against.

I chose visible redundancy over silent omission, because a reader can see the
redundancy and cannot see an omission. But I want to be explicit that I did not
find a right answer here; I picked the least wrong of three wrong ones.

Secondary problem in the same place: 80 W over the stated 10 mm × 100 µm stripe
is 8000 W/cm², not 800. The brief's flux corresponds to an area ten times the
stripe. I drew the brief's number, 800, unchanged. Since the schema cannot
carry an area, there was nothing to check it against and nothing to write it
down in — the discrepancy is invisible in the file, and `--physics` skips the
node rather than noticing.

### 1b. Nothing in the file says the TEC is a heat pump rather than a leak

The `flow` branch was, genuinely, the right tool — "heat moved from one node to
another ... because something pumps it", and "the only directed branch". The
direction is carried. The 60 W is carried. The 40 W of electrical work lands on
the hot node as `diss`, which is honest.

What is not carried is that this branch moves heat **up a temperature
gradient**. The cooler body is at 41 C and the hot face is at 48 C, and the
diagram shows 60 W travelling from the cold one to the hot one. Every other
branch on the page runs downhill. There is no field — no `kind`, no flag, no
`sub` convention documented for it — that marks a branch as active rather than
passive. A `flow` branch carrying water from a cold node to a hot node would be
a physical impossibility and would render identically.

What I did instead: put the words "TEC pumps heat" in the `label`. That is
prose, not data. It is not checkable, it does not affect the rendering, and a
reader who skims the symbols and not the words sees a thermal short circuit
running the wrong way.

The `node-does-not-balance` remedy text actually gestures at this workaround —
"if a temperature is a limit rather than a result, or a flow is a capacity
rather than a load, say so in the `label`". Both of its escape hatches are
"write English in the label". That is the documentation admitting the data
model cannot express the distinction.

Also unexpressed: the TEC's coefficient of performance, which is the entire
design parameter of the component (60 W pumped for 40 W consumed, COP 1.5). It
exists only as two numbers on two unrelated elements that a reader has to
notice are related.

### 1c. The brief's numbers do not balance, and the diagram cannot say which ones I trust

Worked out by hand before drawing (see `transcript.md`, Step 1), and confirmed
afterwards by `check --physics` (see the end of `rounds.md`):

| leg | stated | implied | verdict |
|---|---|---|---|
| 65 → 58 over 0.0875 | 80 W | 80 W | exact |
| 58 → 51 over 0.0125 | 80 W | 560 W | out by 7x |
| 51 → 41 over 0.158 | 80 W | 63 W | out by 1.3x |
| 41 → 18 over 0.045 | 20 W | 511 W | out by 25x |
| 48 → 25 over 0.23 | 100 W | 100 W | exact |

I drew the brief's numbers exactly as given and changed nothing to please the
checker. That is the instruction and it is also the right call: the brief is
the specification. **So yes — `check --physics` disagrees with my diagram, and
I left the diagram alone.** The disagreement is the brief's arithmetic, not the
drawing's; both warnings match what I computed by hand before I wrote any JSON.

What that leaves is a gap in the schema. There is no way to mark a value as
provisional, nominal, a design limit, or measured-rather-than-computed.
`--physics` is opt-in precisely because "a sketch with placeholder numbers is a
diagram too" — yet the file itself has nowhere to record which of its numbers
are placeholders. That state lives only in whether someone remembers to pass
`--physics`, and in this markdown file, which does not travel with the JSON.
A top-level `"physics": false`, or a per-value `"nominal": true`, would have
let the file say what I am saying here.

### 1d. The baseplate is not on the diagram

The brief has "The TEC hot face is at 48 C and meets a **baseplate**, which
loses heat by convection to ambient air at 25 C at 0.23 K/W". Two named
physical parts, one temperature, and one resistance between the *first* of them
and ambient (0.23 × 100 W = 23 K = 48 − 25, exactly).

No resistance is given between the hot face and the baseplate, and the schema
has no zero-resistance link, no way to give one node two names, and no `pipe`
that would read as "these are the same temperature by construction" without
also claiming a small resistance. I merged them: one node, `T_h = 48 °C`,
labelled "TEC hot face", with the convection branch labelled "Baseplate to
air".

**How misleading: mildly, but really.** The word "baseplate" appears on the
diagram only inside a branch label, so it reads as a property of the air path
rather than as a part. A reader counting parts in the assembly gets seven where
the brief describes eight. I would rather have drawn a `pipe` branch with a
label and no value — the schema does allow "a path with no number draws its
label alone" — but `pipe` "still takes a small resistance" by definition, and
asserting a resistance the brief does not state seemed worse than merging two
nodes the brief puts at one temperature.

### 1e. The submount base has a temperature; the diagram just does not know it

The `spread` structure the brief forces — 51 C at the top of the submount,
spreading 0.15 K/W, then the indium contact, then 41 C at the cooler — needs an
intermediate node with no stated temperature. The schema handles this well: no
`value` and no `sub` gives "its label alone and no `T` at all", which is
exactly right, and is the one place the schema anticipated my problem before I
had it.

The cost is downstream and is not the schema's fault, but it is worth recording
because it is invisible: that missing temperature silently disables the physics
check on **both** its neighbours. See `rounds.md`. Two of the three broken legs
in the table above are the two nodes `--physics` never evaluated.

### 1f. Geometry, everywhere

The brief is full of geometry: a 10 mm × 100 µm stripe, a 100 µm line source
spreading to a 10 mm width, "the cross-section the heat flows through grows as
it goes". The `spread` branch kind renders that idea as hatching that fans from
a point, which is a genuinely good symbol and the right one.

But no dimension in the brief can be written down anywhere. Not the stripe
length, not the source width, not the spread width, not the area the flux is
per. `spread` says *that* the cross-section grows; nothing says from what, to
what. The 100 µm → 10 mm hundredfold spread — the most characteristic fact
about this thermal design, and the reason the spreading resistance is the
largest term in the stack — survives on the page only as fanning hatch lines
and the word "submount". I put the ratio in neither place because there is no
place: `label` is the only free-text field and it is already carrying
"Spreading in submount".

### 1g. The 120 W of light

"It emits 120 W of light and dumps 80 W as waste heat." The 120 W is energy
leaving the junction that is not heat. There is no source kind for non-thermal
power leaving a node, and no way to write the electro-optical efficiency that
relates 120 W of light, 80 W of heat and 200 W of drive. I omitted the 120 W
entirely rather than misuse `flow` for it, which would have claimed 120 W of
*heat* leaves the junction and wrecked the diagram. A clean omission, signposted
here — but a reader of the SVG alone has no way to know the device is 200 W in.

---

## 2. Where the documentation failed me

**2a. The `render`/`theme` warning is wrong for the CLI, and it is the second
paragraph on the page.**

> "`render` alone emits CSS custom properties with no fallback, so pass its
> output through `theme` before saving it ... Without one of them the file
> draws nothing."

The brief tells me to run `thermodraw render ... -o diode.svg`. The schema tells
me that output draws nothing. Both cannot be true, and the page never
distinguishes the Python `render()` function from the `render` CLI command. I
resolved it by grepping my own SVG (`transcript.md`, Step 5) and finding the
`:root` block already there — the CLI does the `theme` step for you. That is a
frightening sentence to hit as the first thing you read, about the exact command
you are about to be told to run, and it cost a detour to disprove.

**2b. Whether `rail` is required is never stated.**

`rail` appears in the "Shape" block alongside `nodes`, `branches` and `sources`
with no marking. "Only give the keys you use" is said about `units` keys
specifically, not about top-level keys. The `rail` section says it is "the
reference the capacitances return to" — this diagram is steady-state and has
none, so I guessed omit. Right guess (`describe` shows no rail ground, `check`
is clean), but it was a guess, and one word — "optional" — in the Shape block
would have removed it.

**2c. Six features have no worked example, and four of them are in this brief.**

The page has exactly one complete example, the hero. It contains `cond`,
`contact`, `conv`, `rad`, `cap`, `diss`, `fixed`, `via` and a rail. It contains
no `spread`, no `flow` branch, no `flux` source, no `break`, no `count`, no
`rate`, no `phase`, no `pipe`, no `mixed`, no `corner`. This brief needed
`spread`, `flow`, `flux` and `rate` — four of the ten unexemplified features,
every one of them load-bearing here. The `flow` branch in particular is
described in prose across three separate paragraphs (in "Branches", in the
`sub` paragraph, and again under `network-in-pieces`) and never once shown as
JSON. I assembled `{"kind": "flow", "sub": ..., "value": ...}` from three
places and hoped.

**2d. `rate` is described but never shown, and its interaction with `--physics`
is not mentioned where you decide to use it.**

> "`rate` | what this path actually carries. Drawn as `q = 12 W` on its own
> line"

Nothing there warns that supplying `rate` opts that branch into a consistency
check (`rate-does-not-match`) that a branch without `rate` never gets. The
`--physics` paragraph mentions the code; the `rate` row in the branch table —
where the decision is made — does not. Using `rate` honestly made my file fail
a check that omitting it would have passed. Correct behaviour, bad signposting:
the incentive as documented is to leave `rate` off.

**2e. `label-adrift` does not say how far "further" is.**

> "-> move source 0 -> j further from its node with `at`"

The finding gives the overshoot ("pushed 36 past its own clearance"), which is
more than most tools give, but the remedy is a direction without a distance. I
moved 160 units and it cleared. I do not know whether 40 would have. On a worse
day that is a binary search.

**2f. Two things stated as facts I could not verify and had to take on trust:**
that `angle` is refused on a `flow` branch (I did not try), and that `break`
refuses `value` and `rate` (I had no `break`). Not failures — just unexercised.

---

## 3. What I had to guess at

| guess | outcome |
|---|---|
| Omit `rail` entirely, there being no capacitance | **right** — clean check, `describe` shows only the two `fixed`-node grounds |
| The TEC is a `flow` **branch**, not two `flow` **sources** | **right**, and the schema half-warned me: "a source has one end ... cannot join two nodes however suggestively you place two of them". `describe` shows `symbol/flow-branch` and `cb --flow-branch-- th` in one connected network |
| `sub` on a `flow` branch is mine to set, so `q_pump` | **right** — rendered `q_pump = 60 W` |
| A `flow` branch's `value` takes `units.q`, so I must declare `q` even with no `radin` | **right** — no unknown-quantity error |
| 260 units of node spacing rather than the suggested 220, because my labels are long | **right** — widest label came out 128 wide, and no `nodes-too-close` |
| `side: "down"` on `j` and `th`, both crowded | **half right** — it did keep the labels off the vertical wire and the flux face, but it is what provoked both `label-adrift` warnings in round 1 |
| `angle: 270` with no `at` on the `flux` source puts the hatched face on top | **right**, copied verbatim from the schema's `{"from": "cell", "kind": "flux", "angle": 270}` line, which is the single most useful sentence on the page |
| The 80 W splits 60 W (TEC) / 20 W (water) at the cooler body | **right by arithmetic** — the only split consistent with "pumps 60 W out" and "100 W leaves its hot face", and node `th` balances exactly under `--physics` |
| Merging the baseplate into the hot-face node | **defensible, not right** — see 1d |
| Typing `q″` as one U+2033 character | **right**, and the schema's three-sentence warning was warranted; it is the kind of thing that costs twenty minutes otherwise |

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

**Mostly yes, and it is the better of the two tools.** Full output in
`transcript.md`, Step 4. Without opening a picture it confirmed:

- 18 labels, matching 8 nodes + 7 branches + 3 sources, so nothing was dropped
- the series order of the stack, in one connected piece
- `symbol/flow-branch` as a distinct placement kind, so the TEC drew as
  something other than a resistance
- the `flux` source at `a270`, `flipped`, label pushed `left` — clear of the
  node label I had sent `below`
- `ground x2` for the two `fixed` nodes and no third ground, confirming the
  omitted `rail` was fine
- every label's exact rendered text, including `q″_e = 800 W/cm²`, which is how
  I know the double prime went in correctly

**What it should have said and did not:**

1. **Sources are absent from the `network:` block.** That block is introduced as
   "which nodes are joined to which", and lists branches only. All three of my
   sources — 80 W into the junction, 800 W/cm² off it, 40 W of TEC electrical
   work into the hot face — appear nowhere in it. The 40 W is not decoration;
   node `th` does not balance without it. The one block designed for verifying
   topology omits a third of the topology.
2. **The `network:` block does not show direction.** `cb --flow-branch-- th`
   uses the same symmetric `--` as `j --cond-- sol`, for the one branch kind the
   schema calls "the only **directed** branch", where "`from` and `to` are the
   way the heat goes". Had I written the TEC backwards, this block would look
   identical. I had to drop to `elements` (`branch 5 cb->th`) to confirm it.
   `cb --flow-branch-> th` would cost one character.
3. **`rate` is not surfaced structurally.** The 20 W and 100 W appear only
   inside label text. Nothing says which branches carry a declared rate, so the
   power budget cannot be checked from the summary.
4. **No totals.** `describe` knows every source value and every branch value and
   never says "sources: 120 W in". A sum would have made 1a — my knowingly
   double-counted junction — visible in the output instead of only in my head.
5. **It cannot tell me the physics went unchecked.** `describe` reports
   placement, `--physics` reports balance, and neither says which nodes
   `--physics` skipped. Between them, three of my eight nodes went unexamined
   and nothing in either output says so.

---

## 5. Features the library lacks, ranked by what they cost me here

1. **A way to state an area, and to relate a flux to the power it is a flux
   of.** Cost: the junction is drawn with a fabricated third arrow (1a). The
   most damaging gap by far, because it makes the picture assert something
   false rather than merely fail to assert something true. One optional `area`
   on a node, or an `of` cross-reference on a `flux` source naming the `diss`
   it restates, fixes it.
2. **A branch kind, or a flag, for active heat transport.** Cost: the TEC reads
   as a passive link running uphill (1b). Everything else about the `flow`
   branch is right; it just cannot say the branch does work. `"active": true`,
   or a `pump` kind with a `work` field, would put the 40 W on the element that
   consumes it instead of floating it as a `diss` on the node.
3. **Dimensions on anything.** Cost: the 100 µm → 10 mm spread, the defining
   feature of this design, is fanning hatch lines and nothing else (1f). The
   `spread` symbol is good, and is handicapped by having no numbers to carry.
4. **A way to mark values provisional, and to record in the file whether the
   physics is meant to hold.** Cost: this diagram is permanently ambiguous
   between "correct diagram" and "sketch with placeholder numbers", and the only
   record of which it is, is this file (1c).
5. **Sources and direction in `describe`'s `network:` block.** Cost: a third of
   the topology and all direction unverifiable from the block built for
   verifying topology (4.1, 4.2). Cheapest fix on this list.
6. **A "skipped" report from `--physics`.** Cost: two wrong nodes passed
   silently, and I would not have known without having done the arithmetic
   myself first (`rounds.md`). The check is good; the silence is what is
   dangerous.
7. **A zero-resistance or identity link between two named parts.** Cost: the
   baseplate is not on the diagram as a part (1d). Low harm, easy fix.
8. **Non-thermal power out of a node.** Cost: the 120 W of light, and with it
   the device efficiency, is simply absent (1g). Arguably out of scope for a
   thermal-network tool, so ranked last — but for a laser diode it is the number
   the customer asks about first.

---

## 6. What worked

Worth saying, because the list above is long. `spread` is the right symbol and
it exists, which surprised me. The `flow` branch is a well-reasoned piece of
design and it modelled a Peltier element properly. `diss` on the hot node,
`flow` into it, and `--physics` folding both into one balance that came out at
exactly 100 W is the tool doing something genuinely hard, correctly. The
node-with-no-`sub`-and-no-`value` rule anticipated the submount base before I
knew I needed it. The `label-adrift` remedy worked on the first literal
application, twice. And the U+2033 warning, which reads as paranoid on a first
pass, is the reason this file has no encoding bug in it.

Two rounds, clean, nothing left standing.
