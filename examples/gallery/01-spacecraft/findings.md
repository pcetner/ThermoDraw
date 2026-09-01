# Findings — GEO satellite panel, drawn from `docs/schema.md` alone

Six rounds of `check`, ending 0 errors / 0 warnings / 0 notes. The drawing is
clean. What follows is what it could not say, and what the documentation did
not tell me.

## 0. A disclosure about the experiment

The brief forbids reading `CLAUDE.md`. I did not open it, but **the harness
injected its full text into my context automatically before I read the brief**,
as part of a "codebase and user instructions" system message I did not request
and could not decline. It contains design rationale for the symbol set, the
label solver and `check.py`. I worked from `docs/schema.md` for every decision
below and none of the layout choices came from it, but the isolation this
exercise depends on was not intact, and you should discount this run
accordingly. If you re-run it, that injection needs to be suppressed first.

## 1. Things I could not express

Ranked by how misleading the result is.

### 1a. A heat pipe. Badly misleading. (worst problem here)

The brief says the heat pipes are "very nearly isothermal: the temperature drop
along it is about **0.4 K** at this load". The schema has six branch kinds —
`cond`, `conv`, `rad`, `contact`, `cap`, `break` — and no seventh. There is no
way to say "isothermal link", and no way to state a **temperature drop** at
all; `units.R` is fixed for the diagram and every resistance value is read as
`K/W`.

What I did: divided by the load. Heat into the panel is 220 W from the TWTA
plus 12 W Earth IR, less the 12.1 W the MLI leaks to space, so about 220 W
crosses the pipes, giving 0.4 / 220 = **0.0018 K/W**, drawn as a `cond` branch.

How misleading:

1. **The number is derived, not given, and it silently encodes an operating
   point.** In eclipse the same pipe with the same drawing is wrong. Nothing on
   the page says so.
2. **The symbol lies about the physics.** `cond` is drawn with the section
   hatching that means solid material. A constant-conductance heat pipe is a
   two-phase device; hatching it as a solid is exactly the misreading a thermal
   engineer would object to. `conv` (streamlines, a moving fluid) is arguably
   closer but wrong in a different direction — it implies a convective film
   coefficient. I picked `cond` and it is wrong.
3. **`0.0018 K/W` is unreadable as printed.** It renders as
   `R_cond = 0.0018 K/W` beside `R_rad = 26 K/W` on the same page. The one
   thing a reader needs to see about a heat pipe — that it is orders of
   magnitude below everything else and effectively a short — is buried in
   leading zeros. `mK/W` would fix it, and the schema forbids mixed units
   explicitly: "a diagram cannot mix `K/W` with `mK/W`".
4. **The drawing now contains a contradiction the library cannot see.** Panel
   45 C, radiator 22 C, and between them a branch labelled 0.0018 K/W carrying
   220 W — which is a 0.4 K drop, not 23 K. The temperatures are the brief's
   and the resistance is the brief's, and they do not agree. `check` reports 0
   findings, which is correct per its own charter ("Two things it does not
   check: whether the numbers are right"), but it means a clean report was
   available for a diagram that is arithmetically impossible.

### 1b. Emissivity. Moderately misleading.

"second-surface mirror with emissivity **0.80**" and MLI with "effective
emissivity **0.02**" are the whole reason the two radiative paths differ by a
factor of 23. There is no field for a surface property. A `rad` branch carries
`kind`, `label`, `value`, and its subscript is library-set to `rad`.

What I did: dropped both numbers and leaned on the labels — "Second-surface
mirror" and "MLI blanket" — to carry the identity of the surface. The
resistances are on the page, so the *effect* survives; the *cause* does not. I
did not smuggle the emissivity into the label text, because that label is
already the widest thing on the page (120 units) and label width is what sets
node spacing.

### 1c. A source that is present but not currently active. Mildly misleading.

The brief: the survival heater "supplies 30 W when the thermostat calls for it.
It is **off** in this condition, but must appear on the diagram." A `diss`
source has `kind`, `label`, `value`, `sub`, `at`, `angle`, `side` — nothing for
state, and no dashed or greyed variant. Colour is unavailable by design.

What I did: wrote the state into the label — `Survival heater (off)` with
`P_htr = 30 W`. It draws a solid arrow pushing 30 W into the panel,
contradicted only by a parenthesis. A reader skimming the arrows will count
30 W that is not flowing, and the node energy balance on the page will not
close. I checked the alternative — omitting `value` is accepted by the
validator (round 6) — but that loses the 30 W rating, which is the thing an
engineer wants from a survival heater. Neither option is right. A
`"state": "off"` that dashed the arrow and parenthesised the value would be.

### 1d. Deep space as a reservoir. Not misleading here, but fragile.

Both radiative paths end at the same boundary, so I drew one `fixed` node and
routed the MLI over the top of the diagram to reach it. That created a loop
(panel to radiator to space, back along the MLI to the panel) and cost me the
`label-in-a-corridor` warning in round 1.

The obvious alternative — draw deep space twice, as thermal-network diagrams
routinely do — is not available, because **a `fixed` node's wall is always
drawn below it**: "The wall is always drawn flat below the node, at every
orientation. `angle` does not turn it, and neither does anything else." A
boundary a branch must reach from *below* cannot be drawn; the wall is in the
way. So every boundary in a ThermoDraw diagram has to be approached from above
or from the side, which pins where the cold end of a network can go.

### 1e. Grazing incidence. Not drawn, not important.

"Solar flux falls on the radiator at **grazing incidence**". A `radin` arrow's
`angle` is a real direction, so I could have pointed it shallowly — but the
angle also decides where the symbol and its label land, so geometry and physics
compete for one field. I used `angle: 270` for placement and let the incidence
go unsaid. Low cost.

## 2. Where the documentation failed me

**The check output's remedies are wrong more often than they are right.** This
is the largest documentation failure, because the remedy strings are the only
guidance an author gets once the schema page is exhausted.

> "move a `via` waypoint on source 1 -> panel so it does not run past this
> label"

`via` is not a field on a source. The validator says so:
`source 1: unknown field 'via'. Expected: angle, at, from, kind, label, side,
sub, to, value`. The checker recommends a field its own validator rejects.

> "move a `via` waypoint on branch 0 twta->panel so it does not run past this
> label"

Branch 0 is a straight two-node run with no `via`. There is no waypoint to
move. The remedy appears to be generated from the fact that the blocker was a
*wire*, without checking whether that wire has any waypoints.

> "or set `side` to one of the two the solver does not try (it tries only the
> sides of the branch)"

For node `panel` the two not tried are left and right — which is exactly where
its two branches leave the node. Applied literally it turned two warnings into
**two errors** (`label-collision`, label printed over a wire), both ways round.
The checker is holding the occupancy list it used to find the collision; it
could have known left and right were occupied, and it recommended them anyway.

> "or `angle` for a direction between those four"

Printed verbatim on a **source** finding, where it is not merely useless but
harmful: `angle` on a source is documented on the same page as "the direction
the arrow points". Taking this advice moves the arrow and its lead, not the
label. One remedy string is being emitted for nodes, branches and sources, and
it is only true for nodes.

The schema page itself has two real gaps:

- **Node labels can only go up.** The Angles section is explicit that a node's
  `angle` is "symmetric about 180°" and lists 0/45/90/135 as above /
  above-right / right / above-left. It never states the consequence: **`angle`
  cannot put a node label below the line, ever, and `side: "down"` is the only
  way to get it there.** That is the single fact that ended four rounds of
  thrash, and it has to be inferred from a table.
- **"Leave `at` out and the source is placed along its own `angle` with room
  for its label ... That is usually what you want"** is wrong on a busy node.
  `describe` showed the survival heater auto-placed at (533, 177) — 34 units
  from its own node — with a 106-wide label that had no choice but to cross the
  contact branch's wire. The automatic distance reserves room for the label
  against nothing else on the page.

Two sentences were exactly right and saved time: the `q″` warning about U+2033,
and "Space labels, not symbols. A box is 84 wide, but
`R_cond = 0.000877 K/W` is over twice that." The second is why I spaced nodes
320-360 apart on the first draft instead of the suggested 220, and why nothing
ever collided horizontally.

## 3. What I had to guess at, and whether the guess was right

| guess | right? |
|---|---|
| A non-listed unit string (`kJ/K`) is legal | **Yes** — accepted, 0 findings. The schema only ever shows `J/K` and does not say whether the string is validated. It is not: `"18"` with `"J/K"` would also have passed, and would have been wrong by 1000x. |
| `via` on a `"to": "rail"` capacitance can move where it drops | **Yes.** The Rail section says "Give it `via` if you want it somewhere else"; `[[460,150],[460,430]]` put the capacitance on its own vertical and freed the space under the panel. Whether the last waypoint should sit on the rail line was a guess; including it worked. |
| A node's `sub` can be a word (`twta`, `pnl`, `space`), not a letter | **Yes.** `T_twta` and `T_space` render fine. |
| Deriving a resistance from a stated temperature drop | Accepted, but see 1a. It draws; it is not right. |
| `cond` for a heat pipe | **No.** Accepted by the validator, wrong to a reader, and there is no better option in the vocabulary. |
| Routing the MLI over the top at y=20 to reach the shared boundary node | **Yes**, once the heat-pipe label was pushed out of the resulting loop with `side: "down"`. |
| Whether collinear overlapping wires are acceptable — the capacitance's first leg lies on the contact branch's wire between x=460 and x=560 | **Unknown.** `check` has no rule for it and says nothing. I believe it reads correctly, since that stretch of wire *is* the panel node, but the library never confirmed it either way. |

## 4. Did `describe` confirm the drawing was the one I meant?

**Partly, and it was the most useful tool in the set** — more useful than
`check`, because `check`'s remedies were wrong and `describe`'s facts were not.
It was `describe` that revealed the survival heater had been auto-placed 34
units from its node, which is what actually diagnosed rounds 2 to 4. The
`pushed N` column and the direction column ("above", "below", "flipped") are
exactly the right things to expose.

What it confirmed: 13 labels, all present; four nodes at the coordinates I
wrote; five branches with the kinds I chose; four sources with the arrow
directions I chose; and every label's rendered text, so I could read
`R_cond = 0.0018 K/W` and `C_pnl = 18 kJ/K` as a reader would.

What it did **not** tell me, in order of how much I wanted it:

1. **The topology, as a topology.** It lists elements, not a network. There is
   no line reading "twta -contact- panel -cond- rad -rad- space, plus
   panel -rad- space and panel -cap- rail". I verified the network by re-reading
   my own JSON, which is circular: had I mistyped `"to": "rad"` as
   `"to": "space"` on the heat pipes, `describe` would have printed
   `branch 1 panel->space` in a column of `->` pairs and I would very plausibly
   have missed it.
2. **Any energy balance.** It knows every source, every node and every
   resistance. It could say "node panel: 232 W in, 232 W out", or that it does
   not balance. It says nothing, and an unbalanced network is the most common
   way a thermal diagram is wrong. This is the check that would have caught 1a.
3. **The wires it drew.** It reports `wire x15` as a count — fifteen wires, no
   coordinates. When I wanted to know whether the capacitance's first leg lay on
   top of the contact branch's wire, that count was all I had.
4. **The degree sign, on a Windows console.** Every temperature prints as
   `78 ?C`. The SVG is correct — I grepped it, all four degree signs are there —
   but `describe`'s whole job is letting you read what got drawn, and on the
   platform this ran on it cannot print the one character every temperature
   label ends with.

## 5. Features the library lacks, ranked by what they cost here

1. **A heat-pipe / isothermal-link branch kind, and a way to state a temperature
   drop.** Cost: the diagram is physically wrong (1a), in the way an engineer
   would catch instantly. Every spacecraft, laptop and base-station thermal
   network has one of these.
2. **Remedies that consult the occupancy list before they advise.** Cost: four
   wasted rounds, three of which made the diagram strictly worse. The
   information needed to say "left and right are occupied; use `side: down`" is
   already in the checker's hand at the moment it prints the finding.
3. **Per-quantity unit scaling** (`0.0018 K/W` becoming `1.8 mK/W`). Already
   item 4 on the roadmap. Here it is not cosmetic: it is the difference between
   a heat pipe reading as a short and reading as a rounding error.
4. **Automatic placement, or even automatic relief, for a crowded node.**
   `panel` has six attachments plus its own label, for eight directions. Rounds
   1 to 5 were me solving that packing problem by hand with `at`, `angle`,
   `side` and `via`, in a coordinate space I had to hold in my head. This
   exercise is a clear vote for the network layer.
5. **Surface properties on a `rad` branch** (emissivity, area, view factor) —
   enough to tell an optical solar reflector from an MLI blanket without relying
   on the caller's prose.
6. **An inactive or conditional state on a source.** A dashed arrow with a
   parenthesised value.
7. **An energy-balance check.** The one diagnostic `check` does not have that
   would have caught the real error in this drawing.
8. **A boundary wall that can face a direction other than down.** Until then the
   cold end of every network is laid out around that constraint rather than
   around the physics.
