# Findings — 02-building

Drawn from `docs/schema.md` and `brief.md` alone. `check` exits 0 with 0 errors
and 0 warnings after four rounds, with one uncleanable note left standing.

---

## 1. What I could not express

Ranked by how much the drawing lies as a result.

### 1.1 Infiltration: the air goes one way and the heat goes the other. Worst one.

The brief could not be more explicit:

> "air leaks in at 0.5 air changes per hour, carrying outdoor air **straight into
> the ground-floor zone**. ... It is not a conduction or convection resistance -
> it is air physically moving from outside to inside."

A `flow` branch is the only thing in the schema that carries heat by moving
fluid, and its direction is defined as the **heat's**, not the air's:

> "It is the only **directed** branch: `from` and `to` are the way the heat goes"

The heat is a 185 W loss from the zone, so I wrote `{"from": "gf", "to": "out"}`.
**The drawing therefore shows chevrons pointing out of the house**, which is the
exact opposite of the sentence the brief spends two lines insisting on.

How misleading: badly, and in a way a reader cannot detect. Nothing on the page
says the mass transfer runs the other way. The only place the truth survives is
the label text I wrote by hand, and even there I could only fit "Infiltration,
0.5 ACH" — the direction is not in it. A reader who knows buildings will assume
exfiltration.

What I wanted: a mass-flow branch with a fluid direction distinct from the sign
of the enthalpy it delivers — or, minimally, a documented convention plus a field
to state it. There is neither.

### 1.2 "0.5 air changes per hour" is not a quantity this schema has.

`units` accepts `R C T P q q″`. An air change rate is 1/h; a volumetric flow is
m³/s; a mass flow is kg/s. None exist. The number that actually generates the
185 W is unstatable, so it lives in prose inside `label`, where it is styled as a
name rather than as data and cannot be checked by anything. Same for the
stairwell: 240 W is in the model, but the fact that it is buoyancy-driven air
movement is only in the word "stairwell".

### 1.3 "It is the dominant heat loss per unit area" — the lintel.

The brief calls this out as the point of the whole lintel. There is no per-area
anything on a branch. `q″` exists but only on a `flux` **source**, which is "heat
crossing into or out of a node", not a property of a resistance — and a `flux`
source has no area either ("a `flux` source has no area, so its node is
skipped"). So the schema has a unit for heat flux and no way to attach an area to
anything. **Dropped entirely.** Not approximated — there is nothing to
approximate it with.

### 1.4 The lintel is a steel conduction bridge, drawn as "mechanism unstated".

The brief gives 0.42 K/W "from zone air to outdoor air", in parallel with the
whole wall assembly — and the whole wall assembly, as the brief defines it,
includes the 0.012 K/W outer convection film. A number spanning air to air is not
pure conduction, and the schema's rule for exactly that case is unambiguous:

> "A window quoted as one number for conduction *and* convection is `mixed`."

So I used `mixed`, `sub: "lintel"`. `mixed` is explicitly texture-free — "`mixed`
has no texture at all, which in this vocabulary is not an absence but a
statement: the mechanism is combined or deliberately unstated." The drawing
therefore says *we are not telling you what this is* about the one path the brief
singles out as the dominant loss. The word "steel" survives only in the label.

How misleading: moderately. It is not wrong, it is silent. The alternative —
`cond` — would have been a positive false statement (that the 0.42 K/W is pure
solid conduction with no surface films), so I took silence over a lie. There is
no `bridge` kind and no way to say "conduction dominant, films included".

### 1.5 The roof is not attached to the house.

The brief gives the roof a temperature and two parallel loss paths and never says
what heats it. There is no roof-to-upper-zone resistance in the brief. I drew
exactly that: `roof` connects only to `out` and `sky`. `check` does not complain
(the graph is connected *through* `out`), but `--physics` correctly reports 190 W
leaving `roof` and nothing arriving. **I did not invent a ceiling resistance to
make it balance.** This is a gap in the brief rather than in the library, but it
is worth saying that `check` without `--physics` gave me no signal at all that a
node was radiating 190 W out of nowhere.

### 1.6 Three parallel paths, two label sides.

`gf` and `out` are joined by three branches (lintel, glazing, infiltration). A
horizontal run has only "up" and "down" available — `left`/`right` puts the label
on its own wire (verified: it produced a `label-collision` error, rounds.md
Round 4). So `parallel-pair-same-side` is structurally uncleanable for any
three-way parallel group. It is only a note, so this costs nothing but noise, but
the finding's remedy text is wrong here (see 2.1).

### 1.7 Minor, but real: the two zone capacitances

`C_gf = 2.1 MJ/K` renders fine because `units` will accept any string. The
brief's "air thermal mass" is a property of the zone air; the schema draws it as
a two-terminal capacitance to a reference rail, which is correct practice and
which I did. No loss here — noting it only because it was the one thing I
expected to fight and did not.

---

## 2. Where the documentation failed me

### 2.1 The page contradicts itself about whether `flow` branches exist.

The branch table gives `flow` a full row, and the prose under it says:

> "`flow` is the odd one. It carries a **rate**, not a resistance — heat moved
> from one node to another because a fluid moves, or because something pumps it."

Two hundred lines later, under `network-in-pieces`:

> "heat carried from one node to another by a moving fluid **has no branch kind
> yet**, and this finding is what tells you the drawing did not say what you
> meant."

These cannot both be true. I believed the branch table, which was right — the
`flow` branch works, `describe` reports `symbol/flow-branch`, and `--physics`
counts it. The second sentence cost me real time on the two features of this
brief (infiltration, stairwell) that most needed it, because I had to decide
which half of the documentation to trust before I could draw anything. If the
second sentence is stale it should be deleted; it currently tells you not to use
a feature the same page documents.

### 2.2 The `parallel-pair-same-side` remedy assumes the case it fires on.

> `-> set "side" to "down" on the lower of the two`

The finding fired on branches 6 and 7 while **both already carried
`"side": "down"`**, and branch 7 already was the lower. Applying the named remedy
literally is a no-op and the finding survives it (rounds.md Rounds 1–2). The
remedy is written for the default case the schema describes ("Both branches are
horizontal, so both labels choose 'up'"), and is not re-derived from what the
file actually says. It should name the branch to move and the side to move it to.

### 2.3 "`render` alone ... draws nothing" is about the Python API and does not say so.

> "`render` alone emits CSS custom properties with no fallback, so pass its
> output through `theme` before saving it ... Without one of them the file draws
> nothing."

That is the second paragraph of the page, above a Python snippet — but the same
word `render` is the CLI subcommand the page later tells you to run, and the CLI
already applies `theme.with_variables` (verified by grepping the emitted SVG for
`:root{--sym:...}`). I nearly went looking for a `--theme` flag. Two words —
"from Python" — would fix it.

### 2.4 Nothing says what `label`-less nodes do.

The page explains `sub`/`value` combinations exhaustively and never says whether
`label` is optional on a node, or what `describe`'s label count does with one
that has none. I wanted to drop the four wall-interface labels to buy horizontal
room and could not tell whether that would read as a dropped label ("a number
lower than that means a label was dropped rather than moved"). I invented four
labels instead and spread the diagram to 2771 px wide.

### 2.5 `units` is fixed-per-quantity but its accepted vocabulary is never given.

"a diagram cannot mix `K/W` with `mK/W`" implies prefixed units are fine, but
`--physics` says "a unit the check does not know skips the diagram rather than
guessing" and no list of known units appears anywhere. I used `MJ/K` as a
deliberate gamble. It turned out fine — `--physics` still ran — but I had no way
to know that in advance, and the failure mode named is silent.

---

## 3. What I had to guess at

| Guess | Right? |
|---|---|
| `flow` branches exist and work despite 2.1 | **Yes** |
| `mixed` for the lintel rather than `cond` | Defensible; no way to confirm |
| `radin` source for the 850 W solar gain | **Yes** — `describe` shows `symbol/radin`, `q_sol = 850 W` |
| `diss` for 600 W of occupants/lighting/appliances (`P_int`) | **Yes**, though "dissipation" is an electronics word for what is mostly people |
| Wall interfaces as free nodes with no `sub`/`value` | Drew correctly, but **silently disabled the physics check on `gf`** (section 5) |
| `MJ/K` as a unit string | **Yes** |
| Rail `reference: "out"` | Unverifiable; the page says it "does nothing" but is "the only place it can be checked against what you meant" |
| `"angle": 135` on `gf` and `"angle": 45` on `out`, for nodes with more than four attachments | **Yes** — `describe` reports `above left` / `above right`, `pushed 8` on `gf` |
| Ending every `via` chain aligned with its target so the last leg is orthogonal | **Yes**, and worth documenting — it is what the hero does but the page never says why |
| That a wire crossing another wire is not a finding (only wires crossing *symbols* are) | **Yes** |

The single most useful thing in the page was the three "habits that are now
checks" — sideways-before-turning, `side` on parallel pairs, space labels not
symbols. Applying them by hand while laying out gave a first draft with **0
errors and 0 warnings**. That is a genuinely good piece of documentation.

---

## 4. Did `describe` let me confirm the drawing was the one I meant?

Partly. It confirmed the counts (27 labels, `ground x3`, `symbol/cond x6`,
`symbol/flow-branch x2`) and that the graph is one piece. Three things it should
have said and did not:

1. **The `network` block drops branch identity in a parallel group.** It prints

   ```
   gf --mixed/mixed/flow-branch-- out
   ```

   Which `mixed` is the lintel and which is the glazing? The block that exists to
   answer "is this the network I meant" cannot distinguish the two paths that are
   easiest to swap. Labels, or branch indices, would fix it.

2. **The `network` block drops direction on the one directed branch kind.**
   `gf --cond/flow-branch-- uf` does not say the stairwell carries heat *upward*.
   Direction is the entire content of a `flow` branch, and it is the field I was
   least sure of (1.1). It survives only in the `elements` block as
   `branch 10 gf->uf`, which reads as a from/to pair like every undirected branch
   above it — so there is no way to tell from `describe` alone that the arrow is
   meaningful there and meaningless on `branch 9 gf->uf`.

3. **Nothing about what the physics check will and will not look at.** See
   section 5.

Cosmetic: `describe` escapes the arrow in a label as `\u2192` but prints `°` raw,
so on a Windows console the temperatures come out as `23 ?C` while the arrows
come out as escapes. One or the other, not both.

---

## 5. `--physics` silently skipped the node that matters most

Run once on the final diagram (verbatim output at the end of rounds.md). It fired
on `roof` and on `uf`. It did **not** fire on `gf`.

`gf` is the worst-balanced node in the diagram: 1.47 kW in (600 W internal gains
+ 850 W solar + 22.2 W back down the stairs) against 693 W out. The house has no
heating plant in the brief, so it cannot balance. The check said nothing.

I tested why on a scratch copy (not the shipped file): give the four wall
interface nodes the temperatures the series chain implies (19.80 / -0.31 / -1.83
/ -2.70 °C) and `gf` immediately fires with the full term-by-term listing. So a
`free` node adjacent to a node with no temperature is skipped, and skipped
**silently**.

That is a bad interaction, because the thing that triggers it is the idiom the
schema recommends:

> "Interior junctions between series layers routinely have no temperature of
> their own, and a lone italic `T` states nothing."

Follow the page's advice about layered assemblies and you turn off the physics
check on whatever is on the inside of the assembly — which, in a building, is the
zone. The page does document that `fixed`, `phase` and `flux`-attached nodes are
skipped, and says so plainly; this fourth skip rule is not mentioned at all, and
unlike the other three it is not visible from the file. A one-line
`note: physics skipped node 'gf' (neighbour 'w1' has no temperature)` would have
turned a silent hole into information.

Both warnings it *did* raise are true of the brief's own numbers and I did not
touch the diagram to clear them, per instructions.

---

## 6. Features the library lacks, ranked by what they cost me here

1. **A mass-flow branch whose fluid direction is separable from its heat
   direction** (1.1). Cost: the drawing states the opposite of the brief on
   infiltration, undetectably.
2. **Physics-skip transparency** (5). Cost: the single largest error in the
   system — a 780 W imbalance on the main zone — is invisible in the only tool
   that looks for errors of that kind.
3. **Quantities beyond `R C T P q q″`** — a flow rate, an air change rate, an
   area (1.2, 1.3). Cost: two of the brief's stated facts are demoted to prose in
   a label, and one is dropped entirely.
4. **A thermal-bridge / "conduction-dominant, films included" branch kind**, or
   any way to say a lumped air-to-air path is mostly one mechanism (1.4). Cost:
   the dominant loss path is drawn as "mechanism unstated".
5. **Label sides beyond four on a horizontal run**, or a parallel-group construct
   that lays out three-plus parallel paths and labels them (1.6). Cost: a
   permanent note and a lot of hand-placed `at` coordinates.
6. **Anything that solves coordinates.** The page is honest that the network
   layer is not built. It is still the biggest cost in wall-clock terms: `gf` has
   eight attachments and `out` has five, and every one of the ~25 waypoints in
   this file was placed by hand and mentally collision-checked against label
   boxes whose widths I had to estimate from one worked example in the docs.
   `check` catching the mistakes afterwards is good; not having to make them
   would be better.
7. **A `describe` that identifies branches inside a parallel group and shows flow
   direction** (4). Cost: I could not use `describe` to confirm the thing it
   exists to confirm.

---

## 7. Things I wanted to look at and deliberately did not

Per the brief's read restriction I did not open anything under `src/`, any other
gallery example, `examples/hero.json`, `README.md`, `CHANGELOG.md`, or `tests/`.

Where I felt the pull:

- **When the `flow`-branch contradiction (2.1) surfaced.** I wanted to grep
  `src/` for the branch-kind enum to settle it in five seconds. Instead I picked
  the more specific of the two statements and let `describe` confirm it after the
  fact.
- **When deciding whether a node may omit `label` (2.4).** One glance at any
  existing diagram would have answered it. I widened the canvas instead.
- **When `--physics` skipped `gf` (5).** I wanted to read the balance code. I
  built a probe file in a scratch directory outside the repository and tested the
  hypothesis from outside instead, which worked, but took three times as long and
  only confirms the behaviour rather than the rule.
- **Deciding `mixed` vs `cond` for the lintel (1.4).** I wanted to see how any
  other diagram in the gallery had treated a thermal bridge. There is no worked
  example of a bridge in `docs/schema.md`.

None of these gaps stopped me. All four would have been closed by one more worked
example on the schema page — a layered wall with a bridge across it is the single
most common thermal network in the building world, and the page's only worked
example is a power semiconductor.
