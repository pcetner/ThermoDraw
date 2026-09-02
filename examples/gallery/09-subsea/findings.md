# Findings — 09-subsea

Written from `docs/schema.md` and `brief.md` alone. The diagram was clean on
the first `check`, so almost nothing here is about fighting the layout
engine; it is about what the format could not be made to say.

---

## 1. What I could not express

This is the part that matters, so it is longest.

### 1.1 "It turns a corner on the way" — the corner is not in the data

The brief says the vapour chamber "runs up the length of the bottle to the
housing" and "turns a corner on the way". I drew that with waypoints:

```json
"via": [[560, 320], [560, 160]]
```

**That is a routing instruction, not a physical claim.** `via` says where the
wire goes on the page. It cannot distinguish "this component physically turns
a corner" from "the author needed to get from the lower row of the drawing to
the upper row". In this diagram both are true at once, which makes it look
like it worked, but nothing in the file records that the corner is a property
of the hardware. Delete the `via`, move `vct` down to y=320, and the diagram
says exactly the same thing about the vapour chamber while drawing a straight
line.

**How misleading:** mildly. Nothing false is drawn. But the reader cannot
recover the fact from the picture, and a second reader redrawing this from
the JSON would have no reason to keep the bend.

### 1.2 The whole physical setting is unsayable

"On the seabed at 1800 m, oil-filled, one atmosphere inside, steady state."

There is **no annotation, caption, or note element** in the schema. There are
nodes, branches, sources and a rail, and every one of them is a thing heat is
at or passes through. `title` exists and is documented as `"optional, not
drawn"`. So the depth, the internal pressure, and the fact that this is
subsea at all have exactly two possible homes: a node or branch `label`,
where they would masquerade as the name of a component, or nowhere.

I put them nowhere. **The rendered SVG is a generic five-node series chain.**
It would be a pixel-identical correct drawing of a box on a bench wired to a
bucket of 4 °C water. Everything that made this a subsea problem is gone.

I did not silently smuggle it into a label, and this is the single largest
thing the format cost here.

### 1.3 "Oil-filled gap" is prose in a label, not data

The convection branch is `"label": "Oil-filled gap"`. There is no `medium` or
`fluid` field on a `conv` branch, so the working fluid is a string a human
reads, not something the file knows. Same class of problem as 1.2, smaller.

### 1.4 I had to invent a node, and give it a name the brief never used

The brief describes flange → vapour chamber → oil gap → bore. Two resistances
in series need a node between them, so there is a place in the diagram the
brief never names: the top of the vapour chamber, where it meets the oil gap.

I created it as `vct`, labelled **"Vapour chamber top"**, with no `value` and
no `sub` — which `docs/schema.md` explicitly endorses ("Interior junctions
between series layers routinely have no temperature of their own").

**But the words "Vapour chamber top" are mine, not the brief's, and they are
printed on the drawing.** That is the only text on the page the brief did not
supply. The alternative was `kind: "corner"`, which "draws nothing and exists
only to route a wire" — but this junction is not a routing artefact, it is a
real thermal location where one mechanism hands off to another, and calling
it a `corner` would have understated it. I took the label. Flagging it
because a reader could reasonably assume the name came from the source.

The cost of this node is not cosmetic — see §5.

### 1.5 "It carries the whole 60 W" — sayable once, and then misleading

The brief states the throughput for the spreading path only. I put
`"rate": "60"` on that branch and on no other, because that is what the brief
states.

The result reads as though the spread path's throughput is known and the
other three paths' throughput is not. **That is false.** It is a series chain
with one source; every branch carries 60 W by inspection. There is no way to
say "and everything downstream of this carries the same" once. The two
available options were:

- state it once (what I did) — implies the rest are unknown;
- repeat `"rate": "60"` on all four — implies four independent statements of
  throughput where the brief made one, and opts all four branches into
  `rate-does-not-match`.

Neither is honest. I chose the one that adds no numbers the brief did not
give.

### 1.6 "Should not pretend otherwise" — `mixed` is right, its subscript is a judgement call

> "Which part is conduction and which is convection is not broken out
> anywhere, and the drawing should not pretend otherwise."

`mixed` is exactly this, and the schema says so almost verbatim: "A window
quoted as one number for conduction *and* convection is `mixed`." **This is
the schema's best moment in the whole exercise** — the vocabulary had a word
for the thing the brief was worried about.

The subscript was the judgement call. On `mixed`, `sub` is mine and "names
the mechanism". I wrote `"sub": "cond+conv"`, which renders as:

```
Housing wall to sea | R_cond+conv = 0.15 K/W
```

I tested the alternative (omitting `sub`), which renders a bare
`R = 0.15 K/W`. I kept `cond+conv` on the grounds that what is *unknown* here
is the split, not the mechanisms — both are present, they are lumped, and no
share is assigned. A reader who parses `R_cond+conv` as "R_cond + R_conv" is
not misled: it is their sum, with both addends unstated.

**Residual risk, stated plainly:** if a reader takes the subscript as a claim
that the two parts *were* separated somewhere, that is wrong. A bare `R`
would be immune to that reading and would say less. This is the one place I
could have gone either way.

### 1.7 No provenance

The brief twice distinguishes vendor-quoted numbers ("the path is quoted as",
"quoted by the vendor as a single number") from the temperatures. There is no
field for where a number came from. All eight numbers render identically.
Low cost here; it is a real absence.

---

## 2. Where the documentation failed me

`docs/schema.md` is unusually good — round 1 was clean, which is mostly its
doing. Three real gaps:

**2.1 It never says what a `mixed` branch prints with no `sub`.** The text is:

> "`mixed`, where it names the mechanism"

It says the field is mine and what it is for. It does not say whether
omitting it yields a bare `R`, drops the subscript row, or is refused. Since
§1.6 was the brief's central worry, I needed to know, and the only way to
find out was to write a throwaway file and run `describe` on it. One sentence
would have saved that.

**2.2 `describe`'s `flipped` mark names the symptom and not the cause.** The
doc says:

> "`flipped` means the label tried its automatic side, found it blocked, and
> took the opposite one"

`describe` reported `node 'vct' ... below ... flipped`. Nothing in the output
says *what* blocked it, and from the coordinates alone there is nothing
obviously above that node. I only established the cause by forcing
`"side": "up"` in a scratch copy, which produced:

> `warning: [label-adrift] node 'vct': its label was pushed 44 past its own
> clearance to get around branch 1 flange->vct`

So it was the vapour chamber's own branch label. The solver did the right
thing silently, and I could not tell that from `describe`. `check` names
blockers; `describe` does not. That asymmetry is undocumented, and it means
`flipped` is unactionable information — you learn that the solver worked, not
what it worked around.

**2.3 Nothing says there is no annotation element.** §1.2 is a hole you find
by searching for a section that is not there. The doc lists what exists; it
never says "a diagram carries no free text besides labels", so I spent time
confirming a negative.

**2.4 (minor, and the doc gets this right)** The `PYTHONIOENCODING` and the
`render` vs `theme` warnings both read as scar tissue from earlier readers,
and both were accurate. I used the CLI, so the theme trap never fired. The
`q″` U+2033 warning was three paragraphs for a key I did not need. That
proportion is a little off, but it is a fair guess at where people fall in.

---

## 3. What I guessed, and whether the guess held

| Guess | Held? |
|---|---|
| An interior junction with no `value` and no `sub` is the right way to draw the vapour-chamber / oil-gap handoff | **Yes** — doc endorses it explicitly. But it cost §5. |
| `sub: "cond+conv"` is a legal subscript string and renders literally | **Yes** — `R_cond+conv` |
| 280 units between nodes (doc suggests "about 220") | **Yes** — no `nodes-too-close`. 220 would likely have failed on the 127-wide `Housing wall to sea` label |
| 80 units of sideways clearance before the `via` turn (doc says 40–90) | **Yes** — no `label-adrift` |
| Omitting `rail` entirely is legal for a steady-state diagram with no capacitance | **Yes** — doc says so, and `describe` still lists `ground x1` |
| `diss` source with explicit `at` left of the node and default `angle` points into it | **Yes** — copied the doc's worked example |
| `pipe` is the right kind for a vapour chamber | **Yes** — doc names vapour chambers specifically |
| Nothing needed a `side` override | **Yes** — the one flip resolved itself correctly |

Nothing I guessed turned out wrong. That is a compliment to the doc, not to
me — every one of those was answered somewhere in it.

---

## 4. Did `describe` confirm the drawing was the one I meant?

**Largely yes.** The network block is the right tool and did the job:

```
board --spread-- flange
flange --pipe-- vct
vct --conv-- bore
bore --mixed-- sea
source 0 --diss-> board
```

That is the chain from the brief, in order, with the mechanism on each link
and the dissipation arriving at the right end. It confirmed the topology, and
`symbol/mixed` in the placements line confirmed that §1.6 landed.

**What it should have said and did not:**

1. **Nothing about `via`.** The single feature I was least confident in — the
   corner — is the one thing `describe` is silent on. It gives the symbol
   centre `(660, 160)`, from which a determined reader can infer that branch 1
   is not a straight line between `(480, 320)` and `(760, 160)`, but the
   waypoints are never listed and the branch is never marked as routed. A
   corner at the wrong height would produce identical `describe` output.
   **If you cannot open the SVG, `via` is unverifiable.**
2. **`flipped` without a blocker.** See §2.2.
3. **Throughput is not in the network block.** `q = 60 W` appears inside
   branch 0's label text and nowhere else. Fine by accident here; in a diagram
   with several `rate`s you would be reading them out of label strings.
4. It does not echo `title`, which is documented as undrawn but is still the
   only place the diagram's subject is written down.

---

## 5. Was `check --physics` silent?

**No.** The exact output is in `rounds.md`. It said:

```
note: [physics-not-checked] checked 1 of 4 free nodes; not checked: flange,
bore (neighbour 'vct' has no temperature); vct (it has no temperature)
```

It found **no disagreement** — no `node-does-not-balance`, no
`rate-does-not-match`. It checked the board: 60 W in from the source, and
`(37 − 19) / 0.30` = 60 W out. That balances exactly.

**But it only checked one node of four, and this is the sharpest finding in
this report.** The numbers in the brief agree with each other perfectly, all
the way down, at 60 W throughout:

```
board  37.0 -(0.30)- flange 19.0 -(0.02)- vct 17.8 -(0.08)- bore 13.0 -(0.15)- sea 4.0
        18.0 K              1.2 K            4.8 K             9.0 K
```

`--physics` verified one link of four. It was blinded by `vct` — the
untemperatured interior junction that the **same document** tells you to draw
("Interior junctions between series layers routinely have no temperature of
their own"), and whose consequence the `--physics` section then describes as
routine ("which is what an interior junction drawn the way this page
recommends does to the nodes either side of it").

So the recommended modelling idiom and the numeric checker are in direct
conflict, and the doc knows it and shrugs. Two resistances in series carrying
a known current through an unknown intermediate temperature is
arithmetically determinate — `(T_flange − T_bore) / (R_pipe + R_conv)` is
60 W and needs no model of anything. The checker gives up instead.

**The note is left standing.** Its remedy is "give the node, or its
neighbour, a `value`". Applying that literally means inventing 17.8 °C and
printing it on the drawing as though it had been measured. The brief forbids
adjusting numbers to quieten this output, so it stays.

---

## 6. Features the library lacks, ranked by what they cost here

1. **`--physics` cannot propagate through an untemperatured junction.**
   Cost: 3 of 4 nodes unverified, on a diagram whose numbers are exactly
   consistent, plus a note in the shipped output that cannot honestly be
   cleared. It defeats itself on the idiom its own documentation recommends.
2. **No annotation / caption / free-text element.** Cost: 1800 m, one
   atmosphere, oil-filled and steady-state are all absent from the drawing.
   The picture is context-free. (§1.2)
3. **`via` is routing only; no way to say a path physically bends.** Cost:
   "it turns a corner on the way" is not recoverable from the file. (§1.1)
4. **`describe` does not report `via` waypoints.** Cost: the one thing I most
   wanted to verify without opening the SVG is the one thing it will not tell
   me. (§4.1)
5. **`describe`'s `flipped` does not name the blocker**, though `check`'s
   warnings do. Cost: one scratch-file experiment to learn something the tool
   already knew. (§2.2)
6. **No way to state throughput for a chain rather than a branch.** Cost:
   three branches read as unknown-throughput when they are not. (§1.5)
7. **No `medium`/`fluid` on `conv`, no provenance on any value.** Cost: low
   here, but the brief drew both distinctions deliberately and neither
   survives into the data. (§1.3, §1.7)
8. **Every node still needs `at`.** Cost: near zero at five nodes. The doc is
   upfront that the network layer is not built.

---

## 7. Two things worth saying in the library's favour

- **`mixed` exists and is documented for exactly this case.** A vendor lumping
  conduction and convection into one number is a common, awkward thing to
  draw, and the format has a word for it that refuses to guess. That was the
  brief's hardest requirement and it was the easiest thing to satisfy.
- **The two layout habits in the doc are real.** Leaving `flange` sideways
  before turning up, and spacing for label width rather than symbol width,
  are the whole reason round 1 was clean. Both are stated plainly and both
  were correct.
