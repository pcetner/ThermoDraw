# Findings — 07-furnace

Built from `docs/schema.md` and the brief alone. Three `check` rounds, clean at
round 3 with 0 errors, 0 warnings, 0 notes. Nothing under `src/`, no other
example, no existing `.json` was opened. I did not want to open one; the schema
page is genuinely self-contained as a *format* reference. Where it let me down
was on drawing behaviour, not on field names — see 2.

---

## 1. What I could not express

### 1a. "Per square metre of wall" — the qualifier that governs every number

**This is the worst one.** The brief's first sentence scopes the whole problem:
"per square metre of wall". Every resistance, the 3000 W, and the 18 W/cm² all
mean nothing without it.

There is nowhere to put it. `title` is documented as "optional, not drawn". There
is no caption, subtitle, note, or free-text field anywhere in the schema. The
rendered SVG therefore states a basis-dependent set of numbers with the basis
omitted. I put it in `title` so it survives in the JSON, knowing it will not
appear on the page.

**How misleading:** badly. A reader of `wall.svg` alone cannot tell whether
0.06 K/W is a whole wall, a square metre, or a test coupon.

### 1b. The flux and the watts do not reconcile, and nothing in the diagram says so

18 W/cm² on 1 m² is 180,000 W. Everything downstream of the refractory face
carries 3000 W — which is 0.3 W/cm². The two printed numbers differ by a factor
of **60**.

I did not adjust either, per the brief. But the schema gives no way to express
the relationship at all: there is no `area` field on a `flux` source, on a node,
or on the diagram, so there is no way to say "18 W/cm² over this face is 180 kW"
or to mark the flux as a face loading rather than the through-wall throughput.
The drawing prints `q″_r = 18 W/cm²` arriving at `furn` and `q = 3000 W` leaving
it through the brick, side by side, silently.

**How misleading:** very. It reads as a diagram where 18 W/cm² goes in and 3000 W
comes out. `check --physics` does not catch it either — see 5.

### 1c. The refractory hot face and the furnace interior are one node, and they should not be

The brief names two places: "the **furnace interior** is held at **1200 C**", and
separately "the flame and the hot gas load the inner face radiatively... on the
refractory face". The prose says gas, then a radiative film, then a brick face.

**I drew them as a single `fixed` node at 1200 °C.** That is an approximation and
I want it on the record.

Why I did it: the brief's own arithmetic forces it. Three courses at 0.06 K/W is
0.18 K/W; 3000 W through that is a 540 K drop; 1200 − 540 = 660, which is exactly
the stated brick-to-board temperature. So the brick chain must start at 1200. If
the refractory face were its own node it would have to sit at 1200 as well, and a
radiative link between two nodes at the same temperature is a zero-resistance
branch, which the schema cannot draw as anything meaningful.

Why the schema left me no better option, even if I had wanted the second node:

- No resistance is quoted for the gas-to-face radiation, so the branch would have
  to be a `rad` with no `value` (legal: "a path with no number draws its label
  alone").
- The face node would then have no temperature of its own, and per the physics
  rules that silently disqualifies **both** its neighbours from being checked
  ("when a **neighbour** has none"). I would have traded one honest node for
  losing the only arithmetic verification in the file.
- Omitting the branch entirely gives `network-in-pieces`.

**How misleading:** moderately. The diagram asserts the refractory hot face is at
exactly 1200 °C. No furnace engineer believes that — there is always a film drop
across the radiating boundary. The brief's numbers assert it too, so I have not
contradicted the brief, but I have promoted an implication into a printed fact.

### 1d. Two unlike parallel paths have no parallel construct

The shell loses heat by convection (0.05 K/W) and radiation (0.075 K/W)
simultaneously — a genuine parallel pair. `count`/`arrangement` only covers
*identical* repeated branches, so it does not apply to two branches of different
`kind` and different `value`.

The result is that I hand-routed the `rad` branch below the line with a four-point
`via` while the `conv` branch runs straight through. Physically the two are peers;
the drawing makes radiation look like a detour off the main path. I did not
approximate any number here — both branches carry their exact stated values and
`describe` reports `shell --conv/rad-- shop`, which is right — but the *geometry*
misrepresents the symmetry.

### 1e. "No thermal mass" can only be said by silence

"There is no thermal mass in this picture. The furnace has been at temperature
for two days." I expressed this by omitting `rail` and every `cap` branch, which
the schema endorses ("a steady-state diagram with no capacitance has nothing to
hang on it"). But omission is not a statement. Nothing in the file or the drawing
distinguishes "deliberately steady state" from "the author forgot the
capacitance", and `describe` does not remark on it either.

Low cost here. Worth a `"steady_state": true` or a drawn marking.

### 1f. A `count`ed series group is opaque

Three courses "laid one behind the other" became one branch with
`count: 3, arrangement: "series"`. Correct, and it drew and balanced. But the two
junctions between the courses do not exist, so nothing can be attached to them or
said about them. Costless in this brief — no inter-course temperatures are given
— but a real limit if one course were instrumented.

---

## 2. Where the documentation failed me

### 2a. The parallel-pair advice is wrong, and it is the first thing a first draft hits

> "**A parallel pair needs `side`.** Both branches are horizontal, so both labels
> choose "up" and the lower one lands inside the loop. Set `"side": "up"` on the
> upper branch and `"side": "down"` on the lower one."

I did exactly this. Round 1 was a `symbols-overlap` **error**.

The sentence presupposes a loop — two separate wires with space between them.
There is none. Two branches between one pair of nodes share a single straight
wire, and their two symbol boxes are drawn at the same point. "the upper branch"
and "the lower one" do not exist until you have routed one of them with `via`,
which this paragraph never mentions. `side` moves labels; it does not create the
geometry the paragraph describes.

It should read: route one of the pair with `via` so there are two wires, *then*
set `side` on each. As written it is a recipe for the error it is trying to
prevent, and it sits in the section headed "Two more details are worth copying
rather than rediscovering".

### 2b. `symbols-overlap` names a remedy that cannot work

Round 1 remedy, verbatim: `-> move one of them with 'at'`.

I applied it literally, as the brief required: `at: [1440, 200]` on the `rad`
branch, an 80-unit slide. The overlap fell from 32 to 4 and **the error stood**.
It could not have cleared. Both symbols are on the same wire, so sliding one along
that wire only trades overlap for near-overlap; at any separation large enough to
clear, each symbol sits on the other's wire, which is the `wire-through-symbol`
warning that duly appeared on round 2.

The schema promises: "Every finding names the schema field that fixes it." For
this case it does not. `at` is a field the element can take — so the narrower
promise ("A remedy names only a field the element can take") is kept — but the
finding's stated remedy is not a fix, and round 1 gave no hint that `via` was the
answer. The correct remedy only appears once you have half-applied the wrong one,
in a *different* finding, which then says so explicitly and correctly: "route
either of them around with `via`, **which clears both**". That one worked first
time and cleared both findings.

`symbols-overlap` between two branches on a shared run should name `via`.

### 2c. `describe` is documented as reporting orientation, and does not

> "Element counts against what you wrote, the canvas you will get, where each
> symbol sits and **which way it is turned**, what each label reads, and which way
> it went."

There is no angle column. The `above` / `below` column is where the *label* went —
that is "which way it went", the next clause. Nothing in the output states the
angle of any symbol. For my `flux` source, whose whole appearance is a hatched
face with arrows coming off it at `angle: 0`, this is the one thing I wanted
confirmed and could not get.

### 2d. `flux` with `to:` is under-specified

> "`flux` | several arrows leaving a hatched surface"

With `to`, the arrows arrive at the node. Do they leave a hatched surface *at the
source position* and travel to the node, or is the hatched surface the node's own
face? I assumed the former and placed the surface at `at: [60, 200]`, left of the
node, arrows travelling right. `check` is happy and `describe` confirms the
position — but see 2c, neither confirms the orientation. The one worked example in
the schema is a `from` case (`{"from": "cell", "kind": "flux", "angle": 270}`), so
the `to` direction has none.

---

## 3. What I had to guess at

| Guess | Right? | How I know |
|---|---|---|
| Brick chain starts at the 1200 °C node — no separate refractory-face node | Right, given the brief's numbers | `--physics` balanced `bb`: (1200−660)/0.18 = 3000 = (660−120)/0.18. Had I inserted a face node, `bb` would have been skipped |
| `arrangement: "series"` for "laid one behind the other" | Right | Heat passes through each in turn; `describe` reads `furn --cond x3 series-- bb` |
| `rate: "3000"` on the counted branch is the **group** total, not per course | Right | Schema is explicit ("On a `count`ed branch it is the whole group's"), and `rate-does-not-match` stayed silent, which independently confirms it folded 3×0.06 |
| `q″` key is one U+2033 character | Right | I round-tripped the JSON in Python and printed `repr()` of the key before running anything, because the schema warns that getting it wrong fails as an *unknown-quantity* error rather than obviously |
| Omitting `size` | Right | Canvas came out 1616×294 measured from the drawing; no `off-canvas`, no `frame-off-centre` |
| 80 units of clearance before turning on the `via`, at both ends (1180→1260, 1540→1460) | Right first time | Schema says "give the turn 40–90 units of clearance"; no `label-adrift` in round 3 |
| `flux` source orientation at `angle: 0`, `at: [60, 200]` | **Unverified** | See 2c/2d — nothing available to me reports it |
| Shell radiation as a `rad` branch to a boundary node, not a source | Right | Schema is explicit: "for radiation leaving, draw a `rad` branch to a boundary node" |

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Largely yes**, and the `network:` block is the part that does the work:

```
  furn --cond x3 series-- bb
  bb --cond-- shell
  shell --conv/rad-- shop
  source 0 --flux-> furn
```

Four lines, and every structural claim in the brief is checkable against them:
three courses in series, one board, two mechanisms in parallel on the shell, one
flux arriving. The `x3 series` and the `conv/rad` compaction are exactly the two
things I most wanted to verify. Label text is reproduced in full, so I could
confirm the subscripts the library sets (`R_cond`, `R_conv`, `R_rad`, `q″_r`)
without rendering anything.

**What it should have said and did not:**

1. **Symbol angles.** Documented as present (2c). Absent. My one unverifiable
   guess is an angle.
2. **`via` routes.** Branch 3's symbol is reported at (1360, 300), which implies
   the detour, but the waypoints themselves are never shown. I cannot confirm
   from `describe` that the wire leaves `shell` sideways before turning — only
   infer it from `check` not complaining. For the one branch in the file whose
   geometry I hand-built, `describe` shows me the least.
3. **That `furn` carries a source nothing checks.** `describe` knows the node is
   `fixed` and knows a `flux` lands on it. It says both, in different blocks, and
   never joins them.
4. **Anything about the absent rail.** No line saying "no capacitance", so 1e is
   invisible here too.
5. **Units-versus-quantity sanity.** `q″_r = 18 W/cm²` and `q = 3000 W` are both
   printed with no remark that they are incommensurable without an area.

---

## 5. Was `check --physics` silent?

**Yes — completely, and that is the most alarming result in this exercise.**

```
examples/gallery/07-furnace/wall.json: 9 labels placed, 0 errors, 0 warnings, 0 notes
```

No `node-does-not-balance`, no `rate-does-not-match`, and — importantly — **no
`physics-not-checked` note**.

The two `free` nodes both balance, genuinely and to the digit:

- `bb`: in (1200−660)/(3×0.06) = 3000 W, out (660−120)/0.18 = 3000 W
- `shell`: in 3000 W, out (120−30)/0.05 + (120−30)/0.075 = 1800 + 1200 = 3000 W

That part is real and the checker earned it, including folding the `series` count
correctly.

But the diagram also contains a source that is wrong by a factor of 60 against
everything else in it, and `--physics` says nothing, because two documented rules
compose into a blind spot:

> "A fixed node is a reservoir and is not asked"

> "A `free` node is skipped when ... it carries a `flux` source, which has no area"

My `flux` sits on a `fixed` node. Rule one exempts it. Rule two never fires,
because rule two only applies to `free` nodes. And the `physics-not-checked` note
counts only free nodes — "A diagram whose free nodes were all checked gets no
note" — so both of mine were checked, and no note is emitted to tell the reader
that a source went unexamined.

Neither sentence is wrong. Together they produce **confident silence over an
unchecked term**. A user who reads "Ask for it when you believe the numbers" and
gets a clean run will reasonably conclude the numbers agree. Here they do not.

The fix is small: `physics-not-checked` should report un-asked *sources* as well
as un-asked free nodes — "source 0 (`flux` on a fixed node) was not checked"
would have been enough.

---

## 6. Features the library lacks, ranked by what they cost here

1. **Area, and any per-unit-area basis.** No `area` on a `flux` source or a node,
   and no drawn place to write "per square metre of wall" (`title` is "not
   drawn"). This cost the most: the brief's headline number is printed on a page
   that cannot say what it applies to, next to a 3000 W it disagrees with by 60×,
   and no tool in the repository will mention it. Fixing this fixes 1a, 1b and
   half of 5.

2. **Parallel geometry for unlike branches.** `count`/`arrangement` handles
   identical repeats beautifully — three courses in series took one line. Two
   *different* mechanisms between the same pair of nodes, which is the commonest
   situation in real thermal work, gets no construct at all: it gets a
   `symbols-overlap` error, a misleading paragraph of advice (2a), a remedy that
   does not work (2b), and a hand-built four-point `via`. Two of my three rounds
   were this. An `arrangement: "parallel"` group holding unlike branches, or just
   auto-fanning the second branch between a repeated node pair, would remove the
   single sharpest edge in the tool.

3. **A radiative boundary layer onto a face whose temperature is then stated.**
   Needed to keep gas and refractory face as two places — see 1c. Related: a
   branch with no `value` poisons its neighbours' physics checks, so the "label
   alone" escape hatch is more expensive than it looks.

4. **`describe` reporting symbol angle and `via` waypoints.** Documented for the
   first (2c), absent for both. Cost: one guess I still cannot verify, on the one
   element type whose appearance is entirely orientation.

5. **`physics-not-checked` covering skipped sources.** Cost: nothing to this
   diagram's correctness, everything to my confidence in the silence. Ranked here
   rather than higher only because I happened to do the arithmetic by hand first.

6. **A positive statement of "steady state, no capacitance".** Absence is not
   assertion (1e). Near-zero cost here.

7. **Named junctions inside a `count`ed series group.** Zero cost in this brief
   (1f), listed for completeness.

---

## What went right, since the brief asks for blunt and not for sour

- The schema is a genuinely complete *format* reference. I never needed a field
  name I could not find, and I never wanted to open `src/` or another example to
  learn what a key does.
- `count: 3, arrangement: "series"` with `rate` on the group expressed "three
  identical courses carrying 3000 W between them" in one branch, exactly, with
  the label reading `R_cond = 0.06 K/W | q = 3000 W | 3 in series`. That is the
  brief's sentence, drawn.
- The library setting resistance subscripts itself and refusing mine meant
  `R_conv` and `R_rad` distinguish the two shell paths without me naming the
  mechanism twice.
- The `wire-through-symbol` remedy said "which clears both" and cleared both, on
  the first attempt, including the error whose own remedy had failed.
- Leaving `size` out produced correct margins with no thought, exactly as
  documented.
