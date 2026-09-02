# Findings — 08-cryostat

Written from `docs/schema.md` and `brief.md` only. The diagram was clean on the
first `check` (0 errors, 0 warnings, 0 notes), so there is nothing to report
about whether a finding's remedy worked when applied literally: no finding
fired. That is itself worth saying — the "Coordinates" and "Angles" sections of
the schema page are good enough that following them pre-emptively kept every
check quiet. Everything below is about what the drawing *cannot say*.

---

## 1. What I could not express

### 1.1 The MLI radiation is not joined to the vessel it comes from — the worst thing here

**Wanted:** 30 W of radiation crossing from the 300 K outer vessel to the 40 K
shield, through the multi-layer insulation, so a reader sees where it comes
from.

**Did:** a `radin` **source** on the shield, labelled `Multi-layer insulation |
q_mli = 30 W`.

**How misleading:** moderately, and structurally rather than numerically. A
source has one end. The drawing therefore says *30 W of radiation appears at
the shield from nowhere*, with the vessel sitting two symbols to its left,
unconnected to it. Every number is right; the topology is a half-truth. A
cryostat reader will supply the missing arrow from experience. A reader who
does not know the system will conclude the shield has an unexplained 30 W and
that the vessel's only influence is the 5.2 W down the straps.

**Why I did not do it properly.** The brief gives the radiation as a power, not
as a resistance, and `rad` is a resistance kind. A `rad` branch with `rate:
"30"` and no `value` is accepted — I tested it — but it costs the shield its
balance check:

```
note: [physics-not-checked] checked 1 of 2 free nodes; not checked: shield (branch 1 vessel->shield has no numeric value)
```

So the schema makes me choose between *drawing the radiation where it comes
from* and *having the shield's 5.2 + 30 = 35 + 0.2 arithmetic checked*. I chose
the check, because the brief asks for `--physics` output and the numbers
closing is the more load-bearing claim. I am not comfortable with the trade and
it should not exist. This is finding 6.1.

### 1.2 "Carries no heat at all" cannot be written as a number

The brief is emphatic: the strut "carries no heat at all", and "a reader has to
see that the load path exists and the heat path does not". The `break` branch
draws the open circuit, which is the right symbol. But it refuses to state the
zero, in either field, and refuses hard — exit 2, not a warning:

```
error: branch mag-mount is a break, which carries no heat and so no value; got '0'
error: branch mag-mount is a break, which carries no heat and so no rate; got '0'
```

So the only channel left is prose. I labelled it `Suspension strut (no heat
path)` rather than `Suspension strut`, putting the zero in English because the
schema would not let me put it in the notation. Compare the G-10 straps two
nodes away, which carry `q = 5.2 W` in the notation. The two statements are of
the same kind and are made in different registers, and that is a wart on the
drawing. I would rather have written `rate: "0"` and let the library decide
whether to draw it.

### 1.3 "Hangs from" — a boundary above the thing it holds

The magnet *hangs from* the mount. I put the mount to the **right** of the
magnet, on the same horizontal line, and the drawing says nothing about the
load being vertical.

I tried the honest arrangement — mount at `(1280, -40)`, magnet at
`(1280, 200)`, break branch running down between them — and `check` passed it
with 0 errors, 0 warnings, 0 notes. I did not ship it, because of this
sentence:

> "The wall is always drawn flat below the node, at every orientation. `angle`
> does not turn it, and neither does anything else"

A `fixed` node's boundary wall is below it, always. Put the mount above the
magnet and the mount's wall lands *between the mount and the strut*, so the
strut leaves through its own boundary's hatching. `wire-through-symbol` did not
fire, so `check` does not police it; `describe` prints `ground x2` on the
`placements:` line with no coordinates and omits grounds from the `elements:`
table entirely, so `describe` could not tell me either. The only way to settle
it was to render and look, which the brief forbids, so I took the arrangement I
could verify.

**Cost of the compromise:** the finished drawing puts a 300 K node immediately
to the right of a 4.5 K node, against the schema page's own "hottest node on
the left" habit, and a reader has to get "hangs from" out of the words
`Room-temperature mount` rather than out of the geometry. This is an
approximation and I am flagging it as one.

### 1.4 The helium's boil-off is not on the drawing and cannot be

The bath takes 0.2 W down the instrumentation leads and 0.05 W from the
winding. 0.25 W therefore leaves as helium vapour. `phase` is exactly the right
node kind and draws exactly the right thing — a temperature held by a phase
change, no wall — but there is no field anywhere for the latent load it
absorbs, and `--physics` skips `phase` nodes by design ("a `phase` node is
holding latent heat this cannot see"). So the one number that says how fast the
cryostat is losing helium is neither drawn nor checked.

I did **not** invent a `flow` source of 0.25 W off the bath to fill the gap,
because the brief does not state it and the brief says not to adjust numbers.
But the absence is a real hole in a cryostat drawing: boil-off is what the
customer cares about.

### 1.5 "Absolute, not a rise" cannot be stated

The brief opens by insisting the temperatures are absolute kelvin. The schema
has `units.T` and nothing else, and `--physics` reads T only as differences, so
`"K"` versus `"°C"` is the whole vocabulary and nothing distinguishes 300 K
absolute from a 300 K rise. It happens not to matter here. It mattered enough
for the brief to open with it.

### 1.6 The cold head is not a place

"That heat leaves the diagram at the cold head." A `flow` source with `from` is
the right construct and works — `describe` shows `shield --flow-> source 1`,
heat leaving. But there is no off-sheet or open terminal, so "cold head" is
label text and not a node. Minor, and arguably correct: it *is* outside the
diagram. Recorded because the brief named the destination and the file cannot.

---

## 2. Where the documentation failed me

**The `--physics` tolerance is undocumented, and it is wide.** The page says
the prototype asks "do the stated numbers agree with each other?" and never
says how closely. Measured, by sweeping the `rate` on the G-10 straps against
the 5.2 W its ends imply: 6.1 W (17.3% out) is silent, 6.2 W (19.2% out)
fires. Roughly an 18% band.

This cost me real time. My first sanity test of the flag moved the shield from
40 K to 60 K, which puts the node 1.4% out of balance and the strap `rate` 8%
out — and `--physics` said nothing at all. For several minutes I believed the
flag was not wired up, and I only recovered by running the schema page's own
two-node example with the dissipation changed from 130 W to 900 W to prove the
code path existed. A page that presents silence as agreement owes the reader
the width of the band.

**"Every skip is reported" is not enough to tell agreement from silence.** The
page lists four reasons a `free` node is skipped and promises
`physics-not-checked` for each. It does not say whether a `phase` **neighbour**
is one of them, and the phrase

> "when a **neighbour** has none — which is what an interior junction drawn the
> way this page recommends does to the nodes either side of it"

made me expect that it might be, since my shield and my magnet both sit next to
a `phase` node. It is not: I tested it and both are checked. But I had to run
that experiment because a clean run gives no positive statement of what was
checked. `checked 2 of 2 free nodes` on success would have cost nothing and
saved the whole investigation.

**Nothing says whether a `break` branch counts for network connectivity.**
`network-in-pieces` is defined over "a path of branches", and a `break` is a
branch that carries no heat, so it is genuinely open whether the mount is
attached or floating. It matters: it decides whether the strut is required or
decorative. I settled it by deleting the strut and getting
`warning: [network-in-pieces] nothing joins 'mount' to the rest of the network`.
The answer is the right one and the page should say it in the `break`
paragraph.

**The `fixed` wall paragraph states a fact and never draws its conclusion.**
"The wall is always drawn flat below the node, at every orientation" is
presented as a note about labels. It is actually a hard layout constraint: a
boundary you attach to *from below* has its own wall in the way. That belongs
in "Coordinates", next to "hottest node on the left", as a rule.

**`describe` will not show me the one thing I needed.** Its `placements:` line
gives `ground x2` — counts, no coordinates — and its `elements:` table lists
nodes, branches and sources and omits grounds and walls. So the geometry
question in 1.3 is precisely the question `describe` is blind to, on a page
whose whole pitch is "Seeing what got drawn".

**Two small ones.** The `elements:` table's columns are unlabelled; I inferred
`(element, placement, position, side, size, text)` from the single worked
example, and got it right, but it is a guess in a section meant to remove
guesses. And the table truncates ids to the column width —
`branch 0 vessel->shiel` — which is the column you scan to confirm topology.

---

## 3. What I had to guess at

| guess | outcome |
|---|---|
| MLI as a `radin` source rather than a `rad` branch | Right by the criterion I picked (kept the shield's balance check), wrong by the criterion of showing where the heat comes from. See 1.1 — the schema does not let both be right. |
| Vessel and room as **one** `fixed` node at 300 K | Believed right. "The outer vessel sits in the room at 300 K" could be two nodes, but two would need a vessel-to-room resistance the brief never gives. |
| Cryocooler as a `flow` **source** with `from`, not a branch to a cold-head node | Right. The kinds table says `flow` may use `from`, and the heat leaves the diagram, so there is no second node to draw. |
| No `rail` | Right. No capacitance, and the page says `rail` is optional for exactly that reason. |
| 360 units between nodes rather than the suggested 220 | Right. `Instrumentation leads` over `R_cond = 179 K/W` measures 119 wide with node labels flanking it; no `nodes-too-close` fired. At 220 I expect it would have. |
| `side: "down"` on the shield and the magnet, pre-emptively, because sources sit above them | Right. `describe` confirms both went `below`, no push, no collision. |
| `at` + `angle` 45 / 315 for the two shield sources, rather than letting them auto-place | Right, and the page told me to: "two auto-placed sources on adjacent diagonals overlap". `describe` shows `a45` and `a315`, one `flipped` label, nothing pushed. |
| `units.T: "K"` | Accepted silently. Right. |
| Leaving `rate` **off** the winding-to-bath branch | Defensible, not certain. The 0.05 W is implied by (4.5 − 4.2)/6, but the brief states 0.05 W as the joints' dissipation, not as a rate the coupling carries. Stating it would have bought one more checked assertion; inventing rates the brief did not state seemed the worse sin. |

---

## 4. Did `describe` confirm the drawing was the one I meant?

**For topology, yes, and convincingly.** The `network:` block is the network I
intended, line for line, and two lines in it did real work:

- `mag --break-- mount` names the kind, so I can see the strut is the open
  circuit and not an accidental `cond`.
- `shield --flow-> source 1` shows the cryocooler heat **leaving**, which is
  the one thing about that source I could have got backwards.

The element count (12 = 5 nodes + 4 branches + 3 sources) matched what I could
work out from the file, so nothing was dropped, and the only solver mark was a
`flipped` on the cryocooler label — no `pushed`, no `adrift`, no `OVERLAPS`.

**What it should have said and did not:**

1. **Where the ground walls are.** `ground x2` with no coordinates, and no rows
   in `elements:`. This is the blind spot that decided 1.3 against the truer
   layout.
2. **That the `radin` source has no origin.** `source 0 --radin-> shield` is
   printed identically whether the radiation genuinely appears at that node or,
   as here, comes from another node on the same page that the drawing fails to
   connect. `describe` is the tool for "is this the drawing I meant", and this
   is the largest way in which it is not — and `describe` renders it invisible.
3. **Which free nodes `--physics` would look at.** `describe` knows the node
   kinds; saying `free (physics-checked)` would have removed section 2's whole
   investigation.

---

## 5. Was `check --physics` silent?

Yes. Exactly as it came:

```
examples/gallery/08-cryostat/magnet.json: 12 labels placed, 0 errors, 0 warnings, 0 notes
```

Exit 0, and — the part that matters — **no `physics-not-checked` note**, which
by the page's own rule means every `free` node was actually checked rather than
skipped. Both of them close exactly, on the brief's own numbers and with no
adjustment by me:

- shield: 5.2 W in by the straps + 30 W in by MLI = 35 W out by the cryocooler
  + 0.2 W out by the leads. (260 K / 50 K/W = 5.2; 35.8 K / 179 K/W = 0.2.)
- magnet: 0.05 W in by the joints = 0.05 W out by the coupling.
  (0.3 K / 6 K/W = 0.05.)
- `rate: "5.2"` on the straps matches what its ends imply, so
  `rate-does-not-match` had a live assertion to fail and did not.

**The caveat I would not want a reader to miss.** Silence here means "within
~18%", not "exact" (section 2). The numbers in this brief happen to close to
the digit, but I know that because I did the arithmetic by hand, not because
the tool said so. A brief whose numbers were 10% inconsistent would have
produced this identical output.

---

## 6. Features the library lacks, ranked by what they cost me here

1. **A radiation path carrying a known power with no known resistance, that
   still lets its nodes be balance-checked.** Cost: the one genuine inaccuracy
   in the drawing (1.1). The 30 W is drawn as arriving from nowhere. Every
   other item on this list costs polish; this one costs correctness.
2. **A boundary node whose wall can face a direction other than down — or,
   failing that, `describe` reporting wall geometry so the question is
   answerable without rendering.** Cost: the mount is beside the magnet instead
   of above it, and "hangs from" is not in the drawing (1.3). These are one
   feature request with two acceptable answers.
3. **A way to state that a path carries zero.** `rate: "0"` on a `break`, drawn
   or not. Cost: the strut's zero is prose in a label while the straps' 5.2 W
   is notation (1.2), on the one relationship the brief singled out.
4. **A documented tolerance on `--physics`, plus positive confirmation of what
   was checked.** Cost: the longest detour of the exercise, and a period of
   believing the flag was dead. Both halves are cheap: print the band, and
   print `checked 2 of 2 free nodes` on success.
5. **A latent-load annotation on a `phase` node.** Cost: the 0.25 W boil-off,
   the number a cryostat exists to minimise, is absent from a cryostat diagram
   (1.4).
6. **`network-in-pieces` and the `break` paragraph documenting each other.**
   Cost: one experiment. Cheap to fix, and it changes whether a reader thinks
   the strut is structural or ornamental.
7. **Off-sheet terminals**, so "leaves at the cold head" names a place rather
   than a label (1.6). Genuinely minor.
8. **The network layer.** Every node needed `at`. It cost nothing this time —
   five nodes on a line, one round, clean — but the schema page is candid that
   it is missing and it is the reason the layout section is as long as it is.
