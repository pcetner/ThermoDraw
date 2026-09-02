# Findings — `examples/gallery/10-pv`

Written from `docs/schema.md` and `brief.md` alone. Nothing under `src/`,
`tests/`, no other example, no existing `.json`, no browser.

Result: clean on the first `check`, `--physics` silent, `describe` matched
intent. That makes the interesting part of this report the list below, not the
diagram.

---

## 1. What I could not express

### 1a. The direction the brief actually cares about is not data

The brief's one hard drawing requirement: *"the reader should be able to tell
the sky path from the roof path at a glance."* I met it by geometry — the two
front-side paths leave the cell upward to `sky` (y 140) and rightward to `amb`
(y 380), the back path leaves downward to `back` (y 700) and on to `roof`.

But that is a fact about the numbers in `at`, and nothing in the schema
expresses it. `describe` prints:

```
  cell --rad-- sky
  cell --cond-- back
```

Those two lines are identical in form. If I swapped the two `at` values the
diagram would be upside down, the brief's requirement would be violated, and
**`check` and `describe` would both be exactly as clean as they are now.**
There is no `check` code and no `describe` field for "which way does this
branch leave". The only guardrail is that I chose the coordinates myself.

*How misleading is the result?* Not at all in the SVG — up is up. Entirely so
in the data: a later editor reading the JSON has no signal that the y values
are load-bearing.

### 1b. The glass is folded into the cell node, and I could not say so

The brief describes a *glass front* that radiates and that wind blows over.
It gives no glass temperature and no cell-to-glass resistance, so the glass
cannot be a node — there is nothing to put in `value`, and a node with no
value is legal but then `--physics` skips both its neighbours ("when a
**neighbour** has none").

So both front-side branches originate at `cell` at 65 °C. **The diagram
therefore states that the radiation leaves a 65 °C surface**, which a module
does not do — the glass is cooler than the cells. The 0.2 K/W and 0.05 K/W
must be understood as cell-to-sky and cell-to-air including the glass.

I approximated. I said so only in free text — `label: "Glass to sky"`,
`label: "Wind over glass"` — because `label` is the only field that can carry
"this resistance spans a layer I have not drawn". A reader who reads only the
symbols sees `R_rad` hanging off `T_cell` and will believe it.

### 1c. 25 W is the answer and the diagram cannot say it

The brief states `q` for two paths (275 W to sky, 600 W to air) and for the
third says only *"the rest goes out the back."* The rest is 25 W. It agrees
three ways: 900 − 275 − 600, (65 − 55)/0.4, and (55 − 45)/(1.6/4).

I left `rate` **off** branch 2 and off the clip group. Two reasons: the brief
says the values are the brief's, and 25 is not in the brief; and the page is
explicit that "the library does no arithmetic". The cost is a diagram that
prints `q = 275 W` and `q = 600 W` on the two upper paths and nothing on the
two lower ones, which reads as *unknown* rather than as *implied*. There is no
way to mark a number as derived, and no way to say "this path carries the
balance".

### 1d. A parallel group prints a number that is not the group's

This is the one I would fix first. The clip group renders as:

```
Mounting clips | R_cond = 1.6 K/W | 4 in parallel
```

The effective resistance is 0.4 K/W. It is never printed. A reader who checks
the arithmetic on the page — 10 K across the clips, so 10/1.6 — gets
**6.25 W**, and the correct answer is 25 W. They have to notice "4 in
parallel", know that parallel means divide, and do it in their head. The
schema page defends per-item values well (`"2.10"` stays `2.10`; folding would
mean parsing), and that defence is about the *stored* value — it says nothing
about why the *rendered* label cannot also carry `= 0.4 K/W`. `--physics`
folds the count correctly, so the library computes the effective value
internally and declines to show it.

I could not express the effective resistance at all, and did not fake it.

### 1e. No way to group the module against its environment

`cell`, the encapsulant path and `back` are one physical object; `sky`, `amb`
and `roof` are three separate environments it touches. The schema has node
`kind`s but no grouping, no enclosure, no "these three are boundaries of the
same assembly". `fixed` is the closest thing and it marks all three
environments the same way it would mark anything else.

### 1f. Tilt

The brief let me off ("nothing in the drawing has to be tilted"), so this cost
nothing here. For the record: `angle` on a node "turns nothing that is drawn",
and on a branch it "overrides the direction taken from the wire" — i.e. it
turns the symbol but not the run. There is no way to draw a stack at an angle.

### 1g. Things I wanted to look at and could not

I wanted to open an existing `.json` in `examples/` to see a `count`ed branch
and a three-way fan-out in a real layout before guessing at spacing. The brief
forbade it; recording it here as instructed. In the event, the "A whole
diagram" section is a complete runnable file and that was enough to start
from. What an example would have saved me is the geometry guesswork in §3.

---

## 2. Where the documentation failed me

**Two adjacent fields on the same branch use opposite conventions, and the
page states it in passing.** On `count`:

> "The `value` is **per item**."

and on `rate`, four rows earlier in the same table:

> "On a `count`ed branch it is the whole group's, not per item."

Per-item and whole-group, on one element, one table apart, with no
cross-reference and no worked example showing both. I avoided the trap only
because I had no `rate` to put on the clips. This deserves to be a callout
next to the `count` example, not a clause.

**The wall/approach interaction is never stated.** The page says:

> "The wall is always drawn flat below the node, at every orientation."

It never says what happens when a *wire* arrives at a `fixed` node from
directly below, where that wall and its stub are. I assumed it would be bad
and designed every boundary approach in this diagram to arrive horizontally
from the left. That constraint drove most of the layout — `sky`, `amb` and
`roof` are all on the right-hand side because of an assumption I could not
check. If approaching from below is fine, the page cost me a more compact
drawing; if it is not, the page should say so.

**The `via`-straight-up rule is overstated.** The page says:

> "`label-adrift` almost always means a `via` rising straight out of a node."

Branch 0 in this diagram is `"via": [[320, 140]]` — a waypoint straight up out
of `cell` — and it produced no finding. The real condition appears to be
whether the *node's own label* is aimed into that wire; `cell` has
`"angle": 45`, so it is not. Stating the rule as "a `via` straight out of a
node whose label goes that way" would have saved me a long detour spent trying
to design a layout with no vertical departures at all.

**Good, and worth keeping:** the `size` paragraph ("you almost never want
it… the two findings `off-canvas` and `frame-off-centre` exist only for
diagrams that set it") is the clearest cost/benefit statement on the page, and
following it removed two of the ten finding codes from play before I started.
Same for the `q″` U+2033 paragraph — unnecessary here, but unambiguous.

---

## 3. What I had to guess at

| Guess | Right? |
|---|---|
| `"angle": 45` on `cell` to reach a diagonal, it having four attachments (rad up, conv right, cond down, source lead left) and `side` offering only four orthogonal slots | **Yes.** `describe`: `a45 / above right`. But `pushed 8`, and the adrift threshold is "past 8" — one unit of margin, entirely by luck. |
| `"angle": 135` on `back`, `"angle": 90` on `roof`, to keep labels out of the arriving wire and the converging comb lanes | **Yes**, both clean. |
| Omitting `rail` entirely (steady state, no capacitance) | **Yes.** The page says it is optional; accepted without comment. |
| `sub: "sun"` on the `diss` source | **Yes** — `sub` is mine on a source. |
| That leaving `cell` rightward for *two* branches would put two wire runs on top of each other | **Never tested**, and this is a gap: the finding table has `wire-through-symbol` but **no wire-through-wire code**. I restructured the layout to avoid it, and as far as I can tell `check` would not have told me if I hadn't. |
| That a wire into a `fixed` node from below hits its wall (§2) | **Never tested.** Drove the layout. |
| That `label` is the right place for "which conduction path this is" | **Yes**, stated outright, and `R_cond` was set for me on all three `cond` branches. |

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Partly — the topology yes, the layout no.**

It confirmed, unambiguously and in one screen: five nodes with the right
kinds, four branches with the right mechanisms between the right pairs, the
group as `--cond x4 parallel--`, the source as `--diss-> cell` (arriving, not
leaving), all ten labels present with their exact rendered text and units.
That is real value and it is what stopped me needing to render and look.

What it should have said and did not:

1. **Which way each branch leaves and arrives.** As in §1a — the brief's whole
   readability requirement is invisible here. A `routes:` block echoing `via`
   waypoints, or even just the departure direction per end, would make the
   sky-up/roof-down claim checkable without a browser.
2. **The `via` waypoints at all.** Branch 0 has one and `describe` never
   mentions it. The only trace is that the symbol landed at `(610, 140)`
   rather than on the straight line between the two nodes, which you have to
   notice.
3. **The effective value of a counted group** (§1d).
4. **What `symbol/cond x7` in `placements` versus `symbol/cond x6` on branch 3
   means.** Working it out: the group carries both forms — 4 expanded plus 2
   condensed = 6 — and branch 2 is the seventh. Nothing labels those as two
   alternative renderings of one group, and a reader counting symbols against
   their file will think there are five conduction paths.
5. **`title`.** The file has one, `describe` never echoes it. The page says it
   is "not drawn", so this is consistent, but `describe` is the tool for
   checking the file says what you meant, and one field of it is unreachable.

---

## 5. Was `check --physics` silent?

**Yes, completely.** Pasted in `rounds.md` exactly as it came:

```
examples/gallery/10-pv/array.json: 10 labels placed, 0 errors, 0 warnings, 0 notes
```

No `node-does-not-balance`, no `rate-does-not-match`, and — the part I would
have missed without the page saying so — **no `physics-not-checked` note**,
which per the page's "A diagram whose free nodes were all checked gets no
note" means both free nodes were genuinely balanced rather than skipped.

For the record, the balances it did not have to complain about:

- `cell` (65 °C): in 900 W. Out (65−10)/0.2 = 275, (65−35)/0.05 = 600,
  (65−55)/0.4 = 25. Sum 900. Both stated `rate`s match.
- `back` (55 °C): in 25 W. Out (55−45)/(1.6/4) = 25 W — the count folded the
  way the page says it folds.

So the brief's numbers agree with each other exactly, and nothing was adjusted
to make that so. That also means this diagram exercised the *silent* path of
`--physics` and not its reporting; I have no evidence about how useful its
messages are.

---

## 6. Features the library lacks, ranked by what they cost me here

1. **A rendered effective value for a counted group.** (§1d) Cost: the single
   most misleading number on the finished page. The library already computes
   it for `--physics`.
2. **Route information in `describe`.** (§4.1, §4.2) Cost: the brief's one
   explicit drawing requirement cannot be verified by any tool, only by
   opening the SVG — which the brief forbade.
3. **A wire-through-wire check.** (§3) Cost: none realised, because I designed
   around it blind. But `check`'s ten codes grade "how the drawing reads" and
   two runs printed on top of each other is exactly that, so its absence is a
   hole in the stated contract.
4. **Layer/assembly grouping.** (§1e) Cost: the drawing cannot distinguish
   "boundary of my module" from "the environment", and a five-node network is
   small enough to survive that. A twenty-node stack would not.
5. **A way to mark a value as derived or as the remainder.** (§1c) Cost: two
   of four paths silently carry no `q`.
6. **The network layer — solving for coordinates.** Documented as future work
   ("Every node needs `at` for now"). Cost: essentially all of the effort in
   this exercise was choosing five `at` pairs so that four labels would not
   collide. None of that was thinking about heat.
7. **A whole-diagram energy balance.** `--physics` checks node by node.
   Nothing anywhere asserts that the 900 W entering the module equals
   275 + 600 + 25 leaving it, which is the statement a reader of a PV thermal
   model most wants confirmed.
8. **Non-orthogonal / tilted geometry.** (§1f) Cost: nothing here, by the
   brief's own dispensation.
