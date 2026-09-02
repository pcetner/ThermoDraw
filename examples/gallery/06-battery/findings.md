# Findings: EV battery module on a liquid cold plate

Written from `docs/schema.md` and the brief alone. `check` was clean on the
first draft, so this file is mostly about what the schema could not say, not
about what the checker caught.

## 1. What I could not express

### The eight cells are eight sources but one resistance path, and the drawing cannot say that

This is the worst of it. The brief says eight prismatic cells, each
dissipating 25 W, and one conduction path of 0.24 K/W that "carries the
module's whole 200 W". So the dissipation is per cell and the path is per
module.

The source says this correctly: `count: 8` with `value: "25"` draws
`P_cell = 25 W` and `each of 8`, and 8 x 25 = 200 W is what the rest of the
network carries.

The path cannot. The 0.24 K/W is a *lumped* module-level path, not eight
copies of anything - writing `count: 8, arrangement: "parallel"` on it would
mean eight 0.24 K/W paths, which is 0.03 K/W, a factor of eight wrong, and
would also break the physics check. So the branch is written plain. The
consequence is that a reader sees eight cells feeding a single lump, with
nothing in the drawing saying whether 0.24 K/W is per cell or for the module.
**I put "the module's whole 200 W" into that branch's `rate` (`q = 200 W`)
precisely so the drawing states the total somewhere**, which is the closest
the schema gets. It is a workaround, not the thing I wanted.

What I wanted: a way to mark a resistance as already-lumped over a counted
group - something like `count: 8, arrangement: "lumped"`, or the ability to
write a per-item value with an explicit group total beside it. The
`count`/`arrangement` pair covers "several identical ones" and nothing else.

**How misleading is the result?** Moderately. The numbers are all correct and
self-consistent; what is lost is the *provenance* of 0.24 K/W. Someone
reading the SVG could reasonably assume it is a per-cell figure and conclude
each cell rises 6 K, not 48 K.

### The eight cells are one node, and the schema has no way to say "eight of these"

Related but separate. There is one `core` node standing for eight cell cores
at 108 C. `count` exists on branches and on sources; it does **not** exist on
nodes. So the drawing shows one cell core where the system has eight. I did
not approximate a number here - 108 C is the stated hottest point either way
- but the topology is a lump and the drawing does not admit it.

I considered eight parallel `cond` branches from eight nodes. That would need
eight nodes, eight sources and eight branches, and the schema gives no way to
condense *nodes* the way it condenses repeated branches. It would also
contradict the brief's own 0.24 K/W.

### The thermal masses are steady-state decoration and cannot be tied to the transient

The brief says the two capacitances "matter when the charge current steps".
The schema has one place to put a capacitance - a `cap` branch to the rail -
and nothing to express the step, the time constant, or the fact that these
two numbers only mean anything in a transient the rest of the diagram is not
drawing. `docs/schema.md` is explicit that this is by design: "`C` is never
read (steady state)". So the drawing shows 4200 J/K and 1800 J/K hanging off
a network whose every other number is a steady-state value, and a reader has
to know from outside the diagram which regime each number belongs to. I did
not substitute anything; I just could not say it.

### "Referred to the chiller supply" is documentary only

The brief says both masses are referred to the chiller supply. I set
`rail.reference: "cs"`. The schema says outright that `reference` "does
nothing else - it does not move the rail, route anything". The `cs` node sits
at y 150 and the rail line at y 372, so **the drawing does not visually
connect the reference node to the rail it is the reference for**. A reader
who does not know that `reference` is documentary cannot tell from the
picture that the rail *is* the chiller supply; `describe` is the only place
it shows up. That is the schema telling the truth about itself, but the
result is still a diagram that under-states a fact the brief made a point of.

I chose not to move `cs` down to y 372 to fake the connection, because the
chiller supply is genuinely in series on the heat path (the glycol flow
arrives there) and putting it on the rail line would suggest a wire that does
not exist.

### No way to say the coolant is moving, other than the flow branch itself

The glycol loop is a `flow` branch, which is right: it is directed, it carries
200 W, and it draws chevrons. What I could not express is flow rate,
inlet/outlet, or a coolant temperature *rise* - the brief gives one coolant
film temperature and one chiller supply temperature, and the schema's `flow`
carries a heat rate and nothing else. That happens to be exactly what the
brief needed, so nothing was lost here. Recording it because it is the obvious
next thing anyone drawing a liquid loop will want.

### Nothing marks which numbers are boundary conditions

`fixed` on `cs` gets close, and it is the right kind. But "the chiller supply
is held at 25 C" and "the cell core is at 108 C" are different kinds of
statement - one is imposed, one is a result - and only the first has a
representation. That is fine and probably correct design; noting it for
completeness.

## 2. Where the documentation failed me

`docs/schema.md` was, on the whole, unusually good: it anticipated most of
what I was about to get wrong and it was right when it did. Three gaps.

**Capacitances and `--physics` are never reconciled.** The physics section
says "At every `free` node with a temperature, what arrives by sources and
`flow` must leave by resistances at `(T_here - T_there) / R`". A `cap` branch
to `rail` is a branch at a free node, `rail` is not a node and has no
temperature, and the skip list includes "when a **neighbour** has none". Read
literally, that says my `core` and `plate` nodes should have been *skipped*
for having a rail neighbour with no temperature. It also says "`C` is never
read (steady state)", which implies the opposite. I could not tell in advance
which reading was right, and the two readings differ in whether a transient
diagram gets any physics checking at all. The run resolved it - silent, with
no `physics-not-checked` note, so capacitances are excluded from the balance
and do not poison their nodes - but I had to run it to find out. **The physics
section should say explicitly that `cap` branches and the rail are invisible
to the balance and do not count as a neighbour without a temperature.**

**The count/arrangement text does not cover a lumped group.** "**`arrangement`
is required, and never inferred.** Eight 0.0275 K/W paths are 0.0034 K/W in
parallel and 0.22 K/W in series" is a good warning about the two cases it
knows. It does not address the third case, which is the one I had: a value
that is *already* the group's. Nothing tells you what to do, so I left `count`
off the branch and lost the information. A sentence saying "if your value is
already the whole group's, leave `count` off, and the count lives on the
source or in the label" would have taken five seconds to follow.

**`rate` is documented on branches, but a `flow` branch's `value` is only
half-stated.** "Refused on `flow`, whose value already is a rate" is clear.
What is not stated is whether a `flow` branch's `value` participates in
`rate-does-not-match` or in the node balance the way a `rate` does. The
physics paragraph says "what arrives by sources and `flow`", so I inferred
yes. It appears to be yes - the `film` node balances only if the flow's 200 W
counts as leaving - but I was inferring, and the sentence about `flow` sits in
the branch table while the sentence that resolves it sits three sections away.

## 3. What I guessed at

| guess | right? |
|---|---|
| Cell core to can floor is one `cond` branch, not `spread`, despite a jelly roll genuinely spreading. Brief called it "a conduction path". | Right, I believe. `spread` is for a growing cross-section, and the brief gave a single lumped number. |
| The thermal pad is `contact`, not `cond`. | Right, and the brief said so in those words: "a contact resistance". |
| Microchannel wall-to-fluid is `conv`. | Right - "wall to fluid convection". |
| The glycol loop is a `flow` **branch**, not a `flow` **source**. | Right, and the schema warns about exactly this: "a source has **one end**, so two `flow` or `flux` sources cannot join two nodes". Had I used sources, `network-in-pieces` would have caught it. That warning earned its place. |
| Chiller supply is `fixed` (it is "held at 25 C"). | Right. |
| Node spacing 300 rather than the suggested 220, because `q = 200 W` adds a third line to the first branch's label and "Jelly roll to can floor" is wide. | Right - clean on the first run. At 220 I expected `nodes-too-close`; I never tested it, so this is an untested guess that simply did not bite. |
| `sub` on the `flow` branch is mine to choose (`loop`). | Right, stated: "on `flow` it is yours too". |
| `count: 8` on the source folds as 8 x 25 = 200 W for the physics balance. | Right. The `core` node balanced, which it could not have done if the source had counted as 25 W. |
| Capacitances to the rail would not trip `network-in-pieces` or the physics balance. | Right, but see section 2 - this was a guess, not something the docs let me know. |
| Leaving `size` out. | Right, and the schema recommends it. Nothing went off-canvas and margins came out even. |

## 4. Did `describe` confirm the drawing was the one I meant?

**Yes, substantially.** The `network:` block is the single most useful thing
in the toolchain. Seeing

```
  core --cond-- can
  can --contact-- plate
  plate --conv-- film
  core --cap-- rail
  plate --cap-- rail
  film --flow-> cs
  source 0 --diss-> core
```

confirmed the series chain, the direction of the flow branch, both
capacitances landing on the rail, and the source arriving rather than leaving.
The `elements:` block confirmed every label's exact rendered text
(`R_contact = 0.10 K/W` - the trailing zero I typed survived, as promised) and
that no label was `flipped`, `pushed` or `OVERLAPS`.

**What it should have said and did not:**

- **It does not report `count`.** The source line reads `source 0 --diss->
  core` with no hint that there are eight of them. The eightness appears only
  inside the element label text (`each of 8`), where I have to notice it. The
  schema documents `j --cond x8 parallel-- ihs` for a repeated *branch*, so
  the network block clearly can carry a count - it just does not for sources.
  Given that the eight cells are the single most compressible fact in this
  diagram, that is the omission that mattered most here.
- **It does not report `rate`.** `q = 200 W` on branch 0 is visible only
  because it appears in the label text. There is no structural statement of
  what each path carries, so I cannot check power flow at a glance - which is
  exactly what I want when confirming a thermal network.
- **Node kinds are shown but node temperatures are not**, except inside label
  text. `core free at (220, 150)` does not say 108 C. A temperature column
  would make the whole `nodes:` block diffable against a brief in one pass.
- **It says `rail: y 372, span (220, 1420), reference 'cs'`, which is good**,
  and is the only place that fact is checkable, exactly as the schema
  promises. Credit where due.

## 5. Was `check --physics` silent?

**Yes, completely silent**, and with no `physics-not-checked` note - which per
the schema means all four free nodes were checked rather than skipped, not
that the checker declined to look.

The brief's numbers agree with each other exactly, which I did not assume in
advance:

- core: 8 x 25 W in; (108 - 60) / 0.24 = 200 W out
- can floor: 200 W in; (60 - 40) / 0.10 = 200 W out
- cold plate wall: 200 W in; (40 - 30) / 0.05 = 200 W out
- coolant film: 200 W in; 200 W out by the glycol flow
- chiller supply: `fixed`, a reservoir, not asked

No value was adjusted to get there. The `rate: "200"` I stated on branch 0
also opted that branch into `rate-does-not-match`, and it did not fire.

Worth setting against the schema's own remark that "When it was written every
diagram in this repository fired it": this one does not, because the brief's
author made the numbers close. That is a property of the brief, not of my
drawing.

## 6. Features the library lacks, ranked by what they cost me here

1. **A lumped-group marker on a resistance.** The one real expressiveness
   failure in this diagram. Eight cells, one path, and no way to write that
   down. Cost: the drawing cannot tell a reader whether 0.24 K/W is per cell
   or per module.
2. **`count` on nodes.** Eight cell cores drawn as one, with nothing saying
   so. Would also have fixed (1) if a counted node let its branches inherit
   the count.
3. **Any transient vocabulary at all.** Two capacitances sit in the file and
   mean nothing to any tool: `check` ignores them, `--physics` ignores them by
   design, and the drawing gives no hint that they bite only during a current
   step. A regime marker, a stated step, or even a time constant printed
   beside a `cap` would make them load-bearing rather than decorative. This is
   the brief's own framing - "matter when the charge current steps" - and the
   library has no place to put it.
4. **`count` and `rate` in `describe`'s network block.** Both are structural
   facts I had to read out of label strings. Cheap to add, and it is the block
   whose whole job is letting me confirm the drawing is the one I meant.
5. **A visible link between `rail.reference` and the rail.** The schema is
   honest that `reference` is documentary, but the result is that "referred to
   the chiller supply" - a phrase the brief used deliberately - survives only
   in `describe` output and not in the picture.
6. **Node temperatures in `describe`'s `nodes:` block.** Minor; the label text
   has them, but a column would let me diff a whole diagram against a brief in
   one glance.
7. **Anything distinguishing an imposed temperature from a computed one**
   beyond `fixed`/`free`. Lowest cost of the seven; `fixed` did the job here.

## Process notes

Not asked for, but relevant to what this exercise measures.

**I did not read anything outside `docs/schema.md` and the brief.** The one
moment I wanted to was the capacitance-versus-`--physics` question in section
2, where I nearly opened `src/` to settle whether a rail neighbour would skip
my nodes. I did not; I ran the tool instead, which answered it. Recording it
because the brief asked me to.

**No finding was ever raised, so no remedy was tested.** `check` was clean on
the first draft and stayed clean, so this run contributes nothing to the
question of whether the remedies work when applied literally. That is a null
result for the thing the brief said it was measuring, and it is worth being
clear that it is a null result rather than a pass. The two pieces of advice I
followed pre-emptively - spacing nodes wider than 220 because a three-line
label is wide, and using a `flow` branch rather than two `flow` sources - both
came from `docs/schema.md`, and both would otherwise have been findings. The
documentation prevented the errors instead of the checker catching them, which
is the better outcome but a different one.
