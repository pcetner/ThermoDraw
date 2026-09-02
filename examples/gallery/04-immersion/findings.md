# Findings — 04-immersion

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent).
Sources available to me: `docs/schema.md` and `brief.md`. Nothing else. I did
not open `src/`, `tests/`, any other example, or any existing `.json` diagram.

Result: `check` exits 0 clean at round 5, after four rounds of edits. Every one
of those rounds was about label placement. Not one was about the thermal
network, which was right in the first draft.

---

## 1. What I could not express

Ranked by how much of the brief it lost.

### 1.1 A fluid stream has two temperatures. A node has one.

**The worst one.** The brief says: "Inside the coil runs **technical water**,
entering at **30 C** and leaving at **38 C**."

A ThermoDraw node is "A place with a temperature" — singular. A stream is not a
place; it is 30 C at one end of the coil and 38 C at the other, and the
difference *is* the heat transfer. There is no primitive for it. `flow` is a
*branch* between two ordinary nodes carrying a rate, which is a different
statement: it says heat moved from place A to place B, not that a fluid warmed
by 8 K on the way through.

I tried three shapes before writing any JSON (recorded in `transcript.md` §1):

1. Two nodes `wi` (30) and `wo` (38) with `flow` between them. This claims
   3.2 kW travels from the 30 C node to the 38 C node, and leaves the coil with
   nothing carrying its heat away. Physically backwards.
2. Two nodes with `wi` unattached. `check` would fire `network-in-pieces`, and
   correctly. Silencing that with a `break` branch would be a lie — `break`
   means "a mechanical connection that carries no heat, such as a standoff or a
   mount", and a pumped return line is not a standoff.
3. One node at 38 C with "30 °C in" written into the node's label text.

**I took (3), and it is an approximation.** How misleading: the 38 C is a real
temperature the library knows about, participates in the physics check, and is
typeset as `T_w = 38 °C`. The 30 C is *prose*. It is set in the same size as
the rest of the label, it is not a `T` of anything, no branch connects to it,
and the physics check cannot see it. A reader gets both numbers; the file only
means one of them. And nothing in the drawing says the technical water is a
**closed loop** at all — the return leg simply does not exist in the diagram.

### 1.2 Boiling and condensation are drawn as ordinary convection

The brief's two most characteristic elements are pool boiling on the spreader
and film condensation on the coil. The branch kinds are `cond`, `conv`, `rad`,
`contact`, `spread`, `pipe`, `mixed`, `cap`, `flow`, `break`. There is no
boiling and no condensation. I used `conv` for both, which is defensible —
both are convective — but it means:

- the two phase-change paths draw with **the same hatching and the same
  subscript** (`R_conv`) as the dry cooler's air-side convection at the far end
  of the diagram, and
- the only thing distinguishing 0.00375 K/W of nucleate boiling from
  0.0058 K/W of forced air is the words I typed in `label`.

`mixed` was the alternative — "no texture at all, which in this vocabulary is
not an absence but a statement" — but that says "combined or deliberately
unstated", and pool boiling is neither combined nor unstated. So `conv` it is,
and the physics is carried entirely by prose. **How misleading: moderately.** A
reader who trusts the symbols sees a single-phase loop with an oddly low
convective resistance in the middle.

### 1.3 The latent heat is not a quantity anywhere

The brief: "the latent heat of the fluid being given up, **3.2 kW** of it, with
no temperature drop across the phase change at all."

The "no temperature drop" half is expressed perfectly — the `phase` kind exists
for exactly this, and the schema's own paragraph ("Condensation at 3.2 kW with
no temperature drop is one node, not two surfaces with a path between them")
reads as though it was written at this brief. One node, 49 C, boiling on one
side and condensing on the other. That is the best-served thing in the diagram.

The **3.2 kW** half is not expressible. A node has no `rate` field, and a
`phase` node in particular has nothing to say how much latent heat it holds. I
put `rate: "3200"` on the branches either side, so the number is on the page
twice, adjacent to the phase node — but that says "these two resistances each
carry 3.2 kW", not "3.2 kW of latent heat is released here". The physics check
confirms the gap from the other side: "a `phase` node is holding latent heat
this cannot see". The library agrees it cannot see it.

### 1.4 `rate` on a counted branch: I left a number off rather than guess

The schema is careful that `value` on a `count`ed branch is per item, and says
so twice with worked arithmetic. It says **nothing** about `rate`. Eight
parallel paths carry 400 W each and 3200 W together, and I had no way to know
which one `rate: "400"` would be read as. So branch 0 carries no `rate` at all,
and the per-processor 400 W of conducted heat is stated only by the dissipation
source. One number silently absent from the drawing, because guessing would
have put a possibly-wrong one there instead.

### 1.5 "3.2 kW total" appears nowhere as a number

The library does no arithmetic — deliberately, and the schema says why ("values
are strings so `"2.10"` stays `2.10`"). So the diagram states `P_p = 400 W`
with 8 of them, and the headline figure of the whole brief, 3.2 kW, is not
printed anywhere. I could have written it into a label as prose, which is what
I did for the 30 C, but one prose number per diagram was already one too many.

### 1.6 The pump is a heat source but not a device in a loop

`{"to": "tw", "kind": "diss", "value": "800"}` says 800 W of dissipation
appears at the technical-water node. Thermally correct. What is lost is that
the pump is a *machine on a particular line*, and that its 800 W is shaft work,
not an electrical loss in a solid. `diss` is glossed as "electrical or internal
dissipation"; there is no kind for work done on a fluid. Minor — the label
carries it.

### 1.7 Units have no prefixes

The brief says **240 kJ/K**. `units` is one string per quantity for the whole
diagram, so the page reads `C_f = 240000 J/K`. Same quantity, so nothing is
lost physically, but it is six digits where the brief had three.

Honesty about my own choice: `"C": "kJ/K"` with `"240"` would probably have
worked and read better. I chose `J/K` because the schema warns that in the
physics check "a unit the check does not know skips the diagram rather than
guessing", I had exactly one non-iterated shot at `--physics`, and `J/K` is the
unit the schema's own example uses. I traded page quality for certainty about a
tool I was allowed to run once. **A per-value unit override, or a published
list of the units the checker knows, would have removed the trade entirely.**

---

## 2. Where the documentation failed me

### 2.1 A finding told me to do something the schema forbids — three times

`check` said, on three separate rounds and against three different nodes:

> "move a `via` waypoint on branch 0 j->ihs so it does not run past this label"

Branch 0 is `"count": 8, "arrangement": "parallel"`. `docs/schema.md` says:

> "A repeated branch is drawn between its two nodes, so it cannot also take
> `via`."

The finding's **first** named remedy is a field the library refuses on that
branch. Anyone following the instruction literally — which is what the brief
asked me to do — gets an error, not a fix. This is not a one-off: any diagram
with a counted group will hit it, because a counted group is physically wide
and is therefore exactly what labels collide with.

### 2.2 `label-adrift`'s remedies cannot say "your label is too wide"

The `sat` finding survived four rounds. Its named remedies were "move branch 1
ihs->sat along its branch with `at`" and "`angle`". I applied both, literally,
repeatedly:

- moved branch 1 by 50: the overshoot stayed at **exactly 48**;
- moved it by 90: the finding **re-blamed the branch on the other side**, still
  48, and manufactured a `wire-through-symbol` and a second `label-adrift` on
  the way;
- `angle: 135`: the overshoot went **48 -> 84**, worse than doing nothing.

The actual cause, which no finding ever stated: `sat`'s label is 192 wide (I
only know that from `describe`) and the runs either side were 260. It was 48
too wide on *both* sides, which is why moving neighbours could not help and why
the number never budged. `nodes-too-close` is the finding that speaks in those
terms — "the labels along that run come to 262" — and that is precisely the
sentence I needed, but it did not fire for these two runs. **`label-adrift`
should be able to notice it is really a spacing problem and hand over to
`nodes-too-close`'s wording.** As written its advice sends you in circles, and
the brief's instruction to apply remedies literally is what produced rounds 3
and 4.

### 2.3 The library prints an arrangement it documents as not existing

`docs/schema.md`, on a source's `count`:

> "They simply add, so there is no `arrangement` to state."

`describe` on my file:

> `source 0 -> j   symbol/diss ... Processor dissipation | P_p = 400 W | 8 in parallel`

It prints **"8 in parallel"**, borrowing the branch wording, for a quantity the
schema says has no arrangement and for which I could not have supplied one.
Eight processors each dissipating 400 W are not "in parallel"; there are simply
eight of them. This is a false statement on the page put there by the library.
I left it, because removing `count` would delete "400 W each, eight of them"
from the data in order to fix a wording bug that is not mine.

### 2.4 The `theme` warning does not say the CLI already does it

> "`render` alone emits CSS custom properties with no fallback, so pass its
> output through `theme` before saving it ... Without one of them the file
> draws nothing."

That is written about the Python API, and there is no CLI equivalent of
`theme.with_variables` in the documented commands. I could not tell whether
`thermodraw render -o file.svg` produces a file that draws nothing. I checked
by grepping the output: every `var(--...)` referenced is also defined in the
SVG's own `<style>`, so the CLI themes for you. **The doc should say so**, in
that paragraph, because the alternative reading is that the documented render
command is broken by default.

### 2.5 Small gaps I worked around

- Nothing says whether a `phase` node may carry a `cap` branch to the rail. I
  did it; it drew.
- Nothing says what tolerance `--physics` uses. My condensing film is 0.45% out
  (the brief rounded `0.0028125` to `0.0028`) and passed. I know only that the
  tolerance lies somewhere between 0.45% and 58%, by observing which nodes
  fired and which did not.
- Nothing says whether a source's `at` may sit outside the node extent. Mine is
  at `x = 20` with a label reaching negative x. It worked; the canvas grew.

---

## 3. What I had to guess, and whether the guess was right

| Guess | Right? |
|---|---|
| `phase` node shared by the boiling and the condensing, rather than two nodes | **Right.** `describe` shows `phase x1`, and `--physics` skips it as latent, exactly as documented. |
| `mixed` for the CDU plate exchanger's single overall resistance | **Right,** by the schema's own window example. Renders `symbol/mixed`, `R_hx`. |
| `conv` for pool boiling and for film condensation | **Accepted, but unverifiable.** Nothing rejected it; whether the drawn texture reads as boiling I cannot know without looking at the image, which the brief forbids. |
| `0.0275` is per processor, `count: 8`, `arrangement: parallel` | **Right,** and `--physics` proved it: `j` and `ihs` balance, which happens only if the count folds to 0.0034375 K/W. |
| `0.00375` boiling is the whole rack, not per processor | **Right** — `(61-49)/0.00375 = 3200 W` exactly; per processor it would need 0.03. |
| Facility water is a `free` node, not `fixed` | Judgement call. The brief never calls it a reservoir, and it is cooled by the dry cooler, so it has a balance. Consequence: it gets physics-checked and fires. A `fixed` node "is a reservoir and is not asked", so calling it fixed would have *hidden* one of the brief's inconsistencies. I preferred it visible. |
| `angle: 270` on the pump source to put it below `tw` | **Right.** `describe`: `source 1 -> tw ... (1500, 198) a270 right`. |
| `fixed` ambient on the main line rather than at rail level like the hero | **Right** — "A `fixed` node may sit anywhere." Drew clean. |
| `units.C = "J/K"` to be safe with the physics checker | **Unverified.** The check ran, so nothing was refused, but I never learned whether `kJ/K` would also have been fine. I paid for that ignorance with six digits on the page. |
| `angle: 135` puts a node label above-left | **Right,** matches the table; `describe` reports `a135 above left`. |

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

**Mostly yes, and it is the most useful of the three commands.** The `network:`
block let me read the topology back and see it was my chain; `phase x1` and
`symbol/cond x10` with `ellipsis x1` confirmed two kinds I could not otherwise
verify without an image; and it is the only reason I know `fw`'s label went
`below ... flipped` and `j` is `pushed 8`. It is also the only reason I found
the "8 in parallel" bug in section 2.3.

What it should have said and did not:

1. **It does not show direction on the one directed branch kind.** The network
   block prints `coil --flow-branch-- tw`, symmetric dashes, identical in form
   to `tw --mixed-- fw`. The schema makes a point that `flow` "is the only
   **directed** branch: `from` and `to` are the way the heat goes", and even
   refuses `angle` on one so that "turning the symbol would let the drawing
   contradict the data". Then the summary that exists to tell you what you drew
   renders that direction invisible. It should print `coil --flow-branch--> tw`.
   For this diagram — whose entire cold half is "the water carries 3.2 kW *that
   way*" — that is the single thing I most wanted confirmed.
2. **Counts do not appear in the network block.** `j --cond-- ihs` gives no
   hint that it is eight paths. You must infer it from `symbol/cond x10` in the
   placements line and from the label text. `j --cond x8 parallel-- ihs` would
   make the most dangerous field in the file — a factor of 64, by the schema's
   own arithmetic — checkable at a glance.
3. **`rate` is invisible as a field.** It appears only baked into the label
   string as `q = 3200 W`, indistinguishable from part of the value. There is
   no way to confirm from `describe` that a number is an assertion about what
   the path carries rather than something the library derived.
4. **The nodes block does not repeat `phase` into the network block.** `sat`
   shows as `phase` in the nodes list but reads as an ordinary junction in the
   network. A phase node is topologically special — it is the one node whose
   temperature is not a result — and the network view is where that matters.
5. **Non-ASCII is unreliable in the output.** The same run printed the arrow in
   one row correctly and `°C` as a replacement character in others. So
   `describe` cannot be used to proofread label text, which is otherwise one of
   the things it is for.

---

## 5. Features the library lacks, ranked by what they cost me here

1. **A fluid stream / advection primitive.** A node has one temperature; a real
   coolant loop has an inlet, an outlet, a mass flow and a closed return. Cost:
   the 30 C inlet demoted from data to prose, the return leg absent entirely,
   the pumped loop drawn as a one-way chain. The biggest gap between the brief
   and the file. (1.1)
2. **Boiling and condensation branch kinds.** The two elements that make this a
   *two-phase* immersion rack draw as generic convection. Cost: the diagram's
   defining physics is legible only in the words. (1.2)
3. **A network layer / auto-layout.** The schema says this is known and not
   built. Concretely: **all four edit rounds, and every one of the nine
   findings I cleared, were about where labels sit.** Zero were about the
   thermal network, which was correct in the first draft. The library made me
   spend 100% of my iteration budget on typesetting.
4. **A `label-adrift` that can diagnose a too-wide label.** Its remedies are
   locally scoped ("move that box") for a problem that is often global ("this
   run is too short for these three labels"). Cost: two of five rounds spent
   proving a named remedy had literally no effect. (2.2)
5. **Any arithmetic at all.** No total dissipation, no series/parallel
   reduction, no `dT = q x R` shown anywhere. `--physics` proves the library
   can do the arithmetic; it just will not put the answer on the page. Cost:
   "3.2 kW total", the brief's headline number, is not in the drawing. (1.5)
6. **`rate` semantics under `count`.** One undocumented sentence would have put
   a number on the page that is currently missing. (1.4)
7. **Per-value unit prefixes, or a published list of the units `--physics`
   understands.** Cost: `240000 J/K` where the brief said `240 kJ/K`. (1.7)
8. **A way to state a quantity at a node** — the latent heat a `phase` node
   passes, or a heat balance at a junction. Cost: the 3.2 kW of latent heat is
   asserted twice, on the branches either side, rather than once where it
   belongs. (1.3)

---

## 6. The physics check disagrees with the diagram, and I did not change the diagram

Verbatim output is at the end of `rounds.md`. Four warnings, all in the cold
half of the loop:

- `tw` does not balance: 4000 W in (3200 carried + 800 pump), 6316 W out
  through the CDU at `(38 - 26) / 0.0019`.
- `fw` does not balance: 6316 W in, 345 W out through the dry cooler at
  `(26 - 24) / 0.0058`.
- both `rate` values I wrote (4000 W) disagree with what the ends imply.

**These are the brief's numbers, not a mistake in my drawing.** I did this
arithmetic by hand before writing any JSON — it is in `transcript.md` section 1,
written ahead of the first `check` run. To make the CDU balance at 4000 W its
resistance would have to be about 0.0030 K/W, not 0.0019; to make the dry
cooler reject 4000 W into 24 C air the facility water would have to sit near
47 C, not 26 C. Every one of those numbers is given explicitly in the brief,
and there is no assignment of them that closes.

I have left the diagram saying what the brief says. Silently retuning a
resistance to make a checker go quiet would have been the one genuinely
dishonest thing available to me here.

For the record, the hot half is clean: `j`, `ihs` and `sat` all balance, which
also confirms that `count: 8, arrangement: parallel` folds exactly as
documented, and the condensing film's 0.45% rounding error (the brief's
`0.0028` for a true `0.0028125`) is inside tolerance.
