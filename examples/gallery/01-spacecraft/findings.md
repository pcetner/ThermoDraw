# Findings — 01-spacecraft

Model: claude-opus-5 — Harness: Claude Code (general-purpose subagent).
Nine `check` rounds to exit 0 with no errors, no warnings and no notes.
`check --physics` fires four warnings, all of them real contradictions in the
brief; the diagram was not changed to silence them.

---

## 1. What I could not express

This is the section that matters, so it is first and it is long.

### 1.1 A heat pipe's temperature drop

**What I wanted.** The brief says: "A heat pipe is very nearly isothermal: the
temperature drop along it is about **0.4 K** at this load." That is how heat
pipes are always specified — a ΔT at a stated load, because the effective
conductance of a CCHP is not constant and quoting a K/W invites the reader to
extrapolate it to loads where it is meaningless.

**What the schema offers.** A `pipe` branch, whose `value` is "unit appended
from `units.R`" (line 134). There is no ΔT field anywhere in the format — not
on branches, not on nodes, nowhere. `rate` is a power, not a temperature.

**What I did instead.** Divided. R = 0.4 K / 220 W = 0.001818… and wrote
`"0.00182"`, with `"rate": "220"` on the same branch so that the load I
divided by is at least printed on the drawing, as `q = 220 W` beneath
`R_pipe = 0.00182 K/W`.

**How misleading the result is: badly, and in a specific way.** The drawing
now asserts a *linear* conductance of 550 W/K where the brief asserted a
*fixed offset* of 0.4 K. Those are different physical claims, and a reader who
takes the number at face value and asks what the pipe does at 400 W will get
0.73 K, which is not what the brief said and not how a CCHP behaves. Worse,
the same number is read by `check --physics`, which does exactly that
extrapolation — against the diagram's own end temperatures, 23 K apart — and
concludes the pipe carries 12.6 kW. The three-digit rounding is a second,
smaller lie: 0.4/220 is 0.0018181…, so `0.00182` is the ΔT restated as 0.4004 K.

**What would have fixed it.** A `drop` field on a branch, or letting `value`
carry a ΔT with `units.T` when the kind is `pipe` or `phase`-adjacent. One
field.

### 1.2 A source that is present but off

**What I wanted.** "A **survival heater** on the panel supplies **30 W** when
the thermostat calls for it. It is off in this condition, but must appear on
the diagram." Two facts: a rating of 30 W, and a current value of zero.

**What the schema offers.** A source has one `value` (line 217) and no state.
There is no `enabled`, no `off`, no distinction between a capacity and a load,
and no `style: "dashed"` or similar to draw an inactive element differently.

**What I did instead.** `"value": "0"` with the rating pushed into the label
text: `"Survival heater (30 W when on)"`, rendering as
`Survival heater (30 W when on) | P_htr = 0 W`.

**How misleading it is: not very, but it cost more than anything else in the
file.** The reading is unambiguous. But it puts a number on the page through a
label rather than through `value`, which is precisely what schema line 36 says
the design exists to prevent — "A value whose quantity has no entry here is
refused, so that a number never reaches the page without its unit." I had to
type the `W` myself, and no check will ever verify it against `units.P`. And
the resulting label is 167 units wide, the widest object in the diagram,
attached to the most crowded node in it; four of the nine layout rounds were
spent fighting it. The thing the schema could not say is the thing that
dominated the work.

Interestingly, `check --physics` reads `0 W in by source 2` and is right to.
So the zero is honest to the solver even though it is dishonest about the
hardware.

### 1.3 Surface properties: ε 0.80 and ε* 0.02

**What I wanted.** The brief specifies the radiator's optical coating by
emissivity (0.80, second-surface mirror) and the blanket by effective
emissivity (0.02). For a spacecraft panel these are the *design* quantities;
the K/W is derived from them and an area.

**What the schema offers.** Six quantities: `R`, `C`, `T`, `P`, `q`, `q″`
(line 38). Emissivity is dimensionless and is none of them. There is no
`area`, no `epsilon`, no free-form property bag.

**What I did instead.** Put them in the branch labels:
`"Second-surface mirror, ε 0.80"` and `"MLI blanket, ε* 0.02"`.

**How misleading it is: not misleading, but unverifiable and expensive.** The
mirror's label is 160 units wide because of it, which is what made it collide
with the MLI's descending wire in round 5 and forced its label below the line.
Nothing connects ε to the 1.15 K/W beside it; the two could contradict each
other freely.

### 1.4 "Heat pipes", plural

The brief says pipes. `count` + `arrangement` exists (line 171) but `value` is
explicitly **per item** (line 183), and the brief gives one aggregate ΔT and no
pipe count. Writing `"count": 4, "arrangement": "parallel"` with the aggregate
resistance would state that each pipe has that resistance, i.e. it would
divide the real conductance by four. I drew **one** `pipe` branch labelled
"Embedded heat pipes". The drawing therefore shows a single link where the
hardware has several — a drafting simplification, not a numerical error.

### 1.5 The operating case

"in sunlight (not eclipse)" and "18 kJ/K, which matters when the satellite
enters eclipse" are statements about a *case*, not about an element. A thermal
diagram of a spacecraft is meaningless without its case, and the schema has
nowhere to put one. `title` exists but line 21 says "optional, **not drawn**".
So the one sentence that tells the reader which of the two operating points
they are looking at is in the JSON and never on the page. I put it in `title`
anyway, knowing it is invisible.

### 1.6 The thermostat

The heater is thermostatically controlled. There is no control element of any
kind — no setpoint, no switch, no hysteresis band. The `break` branch draws an
open circuit for "a mechanical connection that carries no heat" (line 204) and
I considered using it to suggest a switch, but a `break` is by definition
something that never carries heat, which is the opposite of a thermostat. That
would have been exactly the "silently substitute something that looks similar"
the brief warns against, so I did not.

### 1.7 kJ/K

Minor but real. The brief says 18 kJ/K. Units are fixed per diagram (line 31)
and I have only one capacitance, so `"C": "kJ/K"` with `"18"` would have been
legal. I wrote `"J/K"` and `"18000"` instead, because line 450 says "a unit the
check does not know skips the diagram rather than guessing" and the page never
lists the units it knows. I traded readability for certainty that the physics
run would not silently no-op. I never found out whether `kJ/K` would have
worked.

---

## 2. Where the documentation failed me

### 2.1 The one sentence that cost the most

> "A lead is drawn from the symbol to the node whichever you choose, so `at`
> only has to be roughly right." — line 250

This is wrong in the way that matters. A source's `at` does not just place a
symbol approximately; it determines the **lead**, and the lead is a
first-class obstacle that other labels are pushed around and that other
symbols can be reported as crossing. Three separate findings in this session
were caused by it:

- round 5, `label-adrift` on branch 4, "to get around **the wire of** source 2
  -> panel";
- round 6, `label-collision`, "printed over **the wire of** source 3 ->
  radiator" — caused by my having moved source 3 *further out* on the tool's
  own instruction, which lengthened its lead;
- round 8, `wire-through-symbol`, "source 1 -> panel runs straight through
  branch 4 panel->rail".

`at` on a source has to be exactly right, and the page tells you the opposite.
Nothing anywhere describes how a lead is routed or how much room a source
needs. The advice that does exist — "Space labels, not symbols… A box is 84
wide" (line 374) — is about node-to-node spacing and says nothing about
sources.

### 2.2 Findings that name remedies which cannot be applied

Not the documentation as such, but the same contract. Three times a finding
named a remedy that does not exist:

> "-> move a `via` waypoint on branch 0 twta->panel so it does not run past
> this label" (round 2, twice)

Branch 0 is a straight run between two adjacent nodes. It has no `via`. There
is no waypoint to move. The text appears to be generated from "the obstruction
is a wire" without checking whether that branch has any waypoints.

> "-> route it around with `via`, or move the symbol along its branch with
> `at`" (round 8, on `wire-through-symbol` for **source** 1)

`via` is a branch field. The source table at lines 228-258 has no `via`, and
line 157 confirms sources are not routed ("Route it with `via` instead" is said
of `flow` *branches*). Half of that remedy is inapplicable to the element it
was offered for.

The brief asked me to apply each named remedy literally before trying anything
else. In these three cases that was impossible, and I had to fall through to
the second option each time.

### 2.3 `render` and the theme warning

> "`render` alone emits CSS custom properties with no fallback, so pass its
> output through `theme` before saving it… Without one of them the file draws
> nothing." — lines 12-15

This is placed immediately under a Python snippet but reads as a statement
about "render", and the only invocation the brief gives me is the **CLI**
`thermodraw render`. I could not tell from the page whether the SVG I was
about to commit would draw at all. It does — the CLI writes a `:root` block
into the file — but I had to grep the output to find that out, and the page
never says that the subcommand and the function differ.

### 2.4 Undocumented `describe` annotations

Line 507 says the output includes "`flipped` and `pushed N` where the solver
had to work for it" and never defines either. `OVERLAPS`, which appeared in my
round-4 output on source 2, is not mentioned at all. `flipped` on node `twta`
is in my final, clean diagram and I do not know from the documentation whether
it is a problem, or how to prevent it if it were.

### 2.5 The units the physics check knows

> "a unit the check does not know skips the diagram rather than guessing" —
> line 450

No list. See 1.7.

### 2.6 Nothing about how the label solver behaves globally

The page presents label placement as local: `side` moves a label, `angle`
reaches diagonals. In practice pushes propagate hundreds of units and clearing
one finding creates another somewhere else entirely — in round 4, freeing
source 1 let source 2's label travel 160 units to the far right of a
1234-wide canvas and land on a different branch's label. There is no hint of
this anywhere, and it is the single most important thing to know before
laying out a diagram with more than four elements on a node.

---

## 3. What I had to guess at, and whether the guess was right

| guess | right? |
|---|---|
| `radin` rather than `flux` for "solar flux… 45 W absorbed" — the brief says W, and line 40 says a flux "is per unit area" | **right** — and `flux` would also have made the node unaskable by `--physics` (line 449: "a `flux` source has no area, so its node is skipped") |
| one `fixed` "Deep space" node can be the far end of two `rad` branches from two *different* nodes, rather than needing two space nodes | **right** — `describe` shows `radiator --rad-- space` and `panel --rad-- space` as separate edges |
| `"value": "0"` is accepted on a source | **right** |
| `rate` is allowed on a `pipe` branch — line 135 refuses it only "on `flow`… and on `break`" | **right**, and `--physics` reads it |
| `rail.reference` may name a node that is not on the rail line (`space` is at y 180, rail at y 400) | **right** — line 270, "does not move the rail… does not have to be a `fixed` node" |
| a negative temperature string `"-269"` is fine | **right** |
| `angle: 270` on a `to` source places the symbol *below* the node with the arrow pointing up into it | **right** — line 253, "on the far side of the node for a `to`" |
| `side` works on a source label | **right** — line 258, and `"right"` on source 2 is what finally cleared rounds 6-7 |
| a `via` on a `cap`-to-`rail` branch may have a single waypoint and then drop | **right** — `describe` shows the symbol on the vertical run at (440, 350) |
| the shared wire segment where two branches leave the same node in the same direction (panel → x 620 for both the pipe and the MLI) is idiomatic rather than a fault | **right** — no finding, and the hero does the same thing at x = 696 |
| `units.C` of `"kJ/K"` might be rejected or might skip the physics run | **never found out** — I avoided it, so this guess is untested |
| `angle: 135` on the panel node would keep its label clear of the MLI wire | **wrong** — round 2 flagged it `label-adrift`; plain `side: "up"` was correct |
| moving the *other* object, as most findings suggest first, would clear a `label-adrift` | **wrong, repeatedly** — it relocated the problem six times out of seven |

The one guess I would most like to have been able to check without guessing is
the last one, because it is the difference between converging in three rounds
and converging in nine.

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

**Mostly yes, and it was the most useful tool in the set** — more useful than
`check`, because `check` grades a picture I was forbidden to look at while
`describe` tells me what is in it.

What it confirmed outright:

- the `network` block is exactly the network I intended, five edges, with the
  two radiative paths listed separately rather than collapsed;
- every label's full rendered text, so I could see `R_pipe = 0.00182 K/W`
  and `q = 220 W` actually reaching the page, and `P_htr = 0 W` for the heater;
- 13 labels placed = 4 nodes + 5 branches + 4 sources, so nothing was dropped;
- where the solver *actually* put things I had left to it — this is what told
  me in round 1 that auto-placed sources land ~40 units from their node, which
  no amount of reading the schema would have.

What it should have said and did not:

1. **Sources are absent from the `network` block.** It lists `panel --pipe--
   radiator` but not "220 W of `diss` arrives at `twta`". They appear in the
   `elements` table as `source 0 -> twta`, so the information is there, but the
   one block whose stated purpose is "which nodes are joined to which, and by
   what" (line 510) omits the four elements that inject all the heat. If I had
   attached the survival heater to the radiator instead of the panel — a
   plausible slip, they are adjacent in the file — the `network` block would be
   byte-identical.
2. **It never restates `units`.** A wrong unit key is invisible here.
3. **It cannot tell me what a number means.** `R_pipe = 0.00182 K/W` is the
   whole of section 1.1 compressed into a number, and nothing in `describe`
   (or anywhere) records that it came from "0.4 K at 220 W". The provenance of
   every derived value in the diagram is lost at the moment I type it.
4. **No totals.** It knows every source and every resistance at a node; a
   single "node `panel`: 4 attachments, 232 W in by sources and branches" line
   would have caught the brief's inconsistency in round 1 instead of at the
   very end. `--physics` does this, but it is opt-in and I was told to run it
   once, last.
5. **Non-ASCII is escaped inconsistently.** The elements table prints
   `Second-surface mirror, ε 0.80` with the epsilon escaped, but prints
   `°C` raw in the same table (where my console then mangled it). Whatever the
   rule is — it looks like "escape above Latin-1" — it makes the one place I
   can verify my label text against what I typed harder to read.

---

## 5. Features the library lacks, ranked by what they cost me here

1. **No way to state a temperature drop instead of a resistance.** Cost: the
   central number of the diagram is a derived approximation with invented
   provenance (§1.1), and it is what makes three of the four `--physics`
   warnings fire. For spacecraft thermal work specifically this is close to
   disqualifying — heat pipes, thermal straps and interface fillers are all
   quoted as ΔT at a load.
2. **No inactive/rated state on a source.** Cost: four of nine layout rounds,
   the widest label in the file, and a number on the page that bypasses the
   unit machinery (§1.2).
3. **No network layer — every node needs `at`, and the label solver is
   non-local.** Cost: all nine rounds were layout. Not one was about whether
   the diagram said the right thing. The schema is honest that this is coming
   (line 320), but until it does, drawing a six-attachment node is a
   trial-and-error process with no way to reason ahead, because a change at
   x = 380 can move a label at x = 1020.
4. **Sources cannot be routed.** No `via`, no control over the lead, and the
   lead is an obstacle. Cost: three findings (§2.1), and one remedy the tool
   offered that cannot be carried out (§2.2).
5. **No place for dimensionless or geometric properties** — ε, α/ε, area.
   Cost: two overwide labels and no link between a coating and the resistance
   it produces (§1.3).
6. **No operating case / scenario.** Cost: the sentence that makes the whole
   diagram meaningful ("in sunlight, not eclipse") cannot be drawn (§1.5).
7. **No control elements.** Cost: the thermostat is simply absent (§1.6).
8. **`count` cannot express "n of these, aggregate value given".** Cost: the
   heat pipes are drawn as one (§1.4).

---

## 6. The `--physics` disagreement, stated plainly

Run once, record only, output at the end of `rounds.md`. It fires four
warnings. **It is right and the brief is wrong**, and I did not change the
diagram.

- **Gasket.** 220 W through 0.05 K/W is an 11 K drop. The brief puts the TWTA
  baseplate at 78 °C and the panel at 45 °C — 33 K. For 33 K at 220 W the
  contact resistance would have to be 0.15 K/W, three times what the brief
  says. One of the three numbers is wrong; nothing in the brief says which.
- **Heat pipe.** Stated as dropping 0.4 K, and stated as having ends 23 K
  apart. Those cannot both hold. The checker takes the resistance seriously
  and reports 12.6 kW. Physically the brief is describing a real panel in which
  there *are* saddle and condenser resistances between the panel skin and the
  pipe and between the pipe and the radiator, absorbing the other 22.6 K — but
  the brief gives no values for them, and inventing nodes to make the
  arithmetic close would have been exactly the silent substitution I was told
  not to make.
- **What does hold.** The radiative half is nearly self-consistent, which is
  worth saying because it shows the brief is not simply random: the radiator at
  22 °C over 1.15 K/W to −269 °C rejects 253 W; 45 W of that is absorbed solar,
  leaving 208 W to arrive by pipe. The panel receives 220 W plus 12 W of Earth
  IR and leaks 12.1 W through the MLI, sending 220 W down the pipe. 220 against
  208 is a 5 % closure. The brief's radiator, MLI and solar numbers were built
  to fit each other; its conduction numbers were not.
- **The remedies `--physics` names do not apply.** "give it `count` and
  `arrangement`" makes the heat-pipe discrepancy *worse* by a factor of *n*,
  not better. "say so in the `label`" asks me to annotate an inconsistency
  rather than resolve it, and would not silence the check anyway.

The honest summary: `check` passes because the picture is legible;
`check --physics` fails because the brief's numbers do not close. Those are
different questions and the library is right to separate them. What the
library cannot do — and what would have caught this on the first round rather
than the last — is tell me that before I spend nine rounds on label positions.
