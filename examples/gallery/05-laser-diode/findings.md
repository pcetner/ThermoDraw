# Findings — 05-laser-diode

Three rounds. Clean at 0 errors, 0 warnings, 0 notes, exit 0.

## 0. A disclosure about the reading restriction

I obeyed the brief: I read `docs/schema.md` and the brief and nothing else. I
did not open `src/`, `tests/`, `README.md`, `CHANGELOG.md`, or any existing
`.json` diagram.

But the harness injected the project `CLAUDE.md` into my context automatically,
before I was given the brief, as part of the session preamble. I could not
decline it. It contains design rationale, a "What is left to build" list, and a
"Known sharp edges" section. The exercise should know that: my knowledge of the
library was not purely `docs/schema.md`. I have flagged below where `CLAUDE.md`
told me something the schema did not, so the contamination is visible rather
than silent.

## 1. What I could not express

### The spreading resistance — the headline failure

The brief is explicit that this is the point of the exercise:

> "It is not a plain one-dimensional conduction path: the cross-section the
> heat flows through grows as it goes."

There is no `spread` kind. `docs/schema.md` gives exactly six branch kinds —
`cond`, `conv`, `rad`, `contact`, `cap`, `break` — and none of them is
spreading.

**What I did instead:** `{"kind": "cond", "label": "Spreading in CuW",
"value": "0.15"}`.

**How misleading it is: badly, and in the one place it matters most.** The
drawn box carries the section-hatching texture the library uses for plain
solid conduction, and the auto-generated subscript renders the label as

```
Spreading in CuW | R_cond = 0.15 K/W
```

So the drawing *asserts* `R_cond`, in library-set type that the schema says is
"not yours to set" and that names the physics. The physics it names is wrong.
This is the single largest resistance in the stack (0.15 of 0.29 K/W total) and
the whole reason the system is interesting, and the diagram says it is ordinary
1-D conduction. A reader who trusts the subscript — which the schema trains
them to do, since it is the library and not the author speaking — is misled
about the dominant term.

The word "Spreading" appears only in the free-text label, i.e. in the one part
of the label the schema tells the reader is the *author's* words. The
mechanism, which is what the notation exists to carry, is wrong.

There is no workaround. I cannot suppress the subscript (`sub` is documented as
"only for `cap`"), so I cannot even leave it silent and let the label carry the
truth. The choice was `R_cond` or nothing.

### The thermoelectric cooler — no active element

There is no way to draw a device that moves heat against the temperature
gradient. Every branch kind is a passive resistance, and a resistance between
the 41 °C cooler body and the 48 °C TEC hot face would be nonsense — it would
draw heat flowing uphill through a resistor.

**What I did instead:** I drew the TEC as *nothing*. There is no branch between
`cool` and `tech`; they are two disconnected components of the graph. The pump
is represented by three annotation sources:

- `{"from": "cool", "kind": "flow", "value": "60"}` — 60 W leaving the cooler
- `{"to": "tech",  "kind": "flow", "value": "60"}` — the same 60 W arriving
- `{"to": "tech",  "kind": "diss", "value": "40"}` — the 40 W of electrical work

**How misleading it is: moderately, and in a way a reader must reconstruct.**
Nothing in the drawing states that those two 60 W arrows are the *same* 60 W.
They are two independent annotations that happen to be vertically aligned and
happen to carry the same number. A reader has to infer the pump from adjacency.
There is no symbol saying "Peltier", no element linking the two, and no way to
label the pair as one device. If they drift apart in a later edit, nothing
catches it — `check` grades layout, not meaning, and `describe` lists them as
unrelated rows.

Nor can I distinguish the 40 W of electrical *work* from 40 W of ohmic
self-heating: `diss` is "electrical or internal dissipation" and draws the same
plain arrow for both.

### "100 W leaves its hot face" — a power cannot be put on a branch

The brief states a heat rate crossing the baseplate path. Sources attach to
**nodes** only (`to`/`from` take a node id), so a heat rate can be annotated at
a node but never *on the path that carries it*. I left the 100 W out. It is
recoverable as 60 + 40 from the two arrows at `tech`, but the diagram does not
say it.

Adding `{"from": "tech", "kind": "flow", "value": "100"}` would have been
actively wrong: it draws a second exit arrow leaving `tech` alongside the
baseplate branch, implying two exit paths where there is one. The same applies
to the 80 W flowing down the main chain — I can state it at the junction, never
along the ladder.

### An interior node with a name but no temperature

The spreading resistance and the indium contact are in series, so the schema
forces a node between them. The brief gives no temperature there, and the
brief's own numbers do not close (51 − 80 × 0.15 = 39 °C, below the cooler body
at 41 °C), so inventing one would have put a false number on the page.

A `free` node with `label` and no `value` renders as `Submount base | T` — a
bare, dangling `T`. Deleting the `label` too still renders a lone `T` (7x17).
`check` reports 0 findings on both; it is a well-formed label that says nothing.

**What I did instead:** `"kind": "corner"`, which draws nothing. Honest, but it
loses the name — a reader cannot tell that the point between the two boxes is
the submount underside.

I want a named node with no temperature. The schema comes close and stops
short: a `break` node gets "the label alone drawn", but a `break` draws a
boundary wall, which this is not.

### Everything else expressed cleanly

`contact` covered both the AuSn joint and the indium layer; `conv` covered both
the microchannel water and the baseplate; `flux` with `from` and its own
`q″` / `W/cm²` unit covered the 800 W/cm² emitting face exactly, and is the one
place where the vocabulary was clearly *better* than I expected.

## 2. Where the documentation failed me

**The lone `T` is undocumented and unwarned.** The schema says a node's `value`
is optional and never says what happens when you omit it on a `free` node. The
only hint is buried in the `break` paragraph — "A `break` has no temperature to
state, so `sub` and `value` are usually left off and the label alone is drawn"
— which by implication says a non-`break` node does *not* get the label alone.
I found the stray `T` from `describe` output, and only because I ran `describe`
at all.

**"Every finding names the schema field that fixes it" — true, and the fields
were complete, but the check set has a hole exactly where the docs do.** A
diagram that renders a naked `T` with no subscript and no value passes with
0 errors, 0 warnings, 0 notes. The schema's own promise — "so that a number
never reaches the page without its unit" — has an unguarded mirror image: a
*symbol* reaching the page without a number.

**The `q″` warning earned its length.** The U+2033 paragraph is longer than
anything else in the document and it saved me: I would have typed `q"` and got,
per the doc, "a JSON syntax error at best". Documentation doing its job.

**`describe` output is mangled on the platform the docs care about.** The
schema's `check` section says the report is ASCII for cp1252 consoles.
`describe` is not: run plainly on Windows it printed my labels as
`q″_e = 800 W/cm?` and `T_j = 65 ?C` — the degree sign and the superscript
two both replaced. Since `describe` exists specifically so you can read the
labels back and confirm they are what you meant, mangling exactly the two
characters the schema *mandates* (`°C`, `W/cm²`) defeats the tool. I had to set
`PYTHONIOENCODING=utf-8` to verify my own diagram. The docs do not mention this.

**No guidance on multiple sources at one node.** The `tech` node carries two.
The layout advice — "Space nodes about 220 apart", "put parallel paths 80 above
and below" — covers nodes and branches but says nothing about sources sharing a
node, which is precisely what produced my only error.

## 3. What I had to guess at

| guess | right? |
|---|---|
| `rail` can be omitted entirely when there are no capacitances | **yes** — "Only give the keys you use" is said of `units`, not of the top level, so this was inference. Renders fine. |
| Two disconnected components in one diagram (the TEC splits the graph) would be accepted | **yes** — no complaint from `check` or `render`. Not documented either way. |
| A `corner` node keeps routing the wire, draws no dot, and drops out of the label count | **yes** — count went 19 to 18, both boxes stayed put |
| `flux` with `from` and `angle: 270` puts the hatched face on top of the junction | **yes** — the schema's `{"from": "cell", "kind": "flux", "angle": 270}` example transferred directly |
| 260 units of node spacing clears labels up to `R_contact = 0.0125 K/W` | **yes** — no `nodes-too-close`. "about 220" plus "space labels, not symbols" was enough to pick a working number first time |
| `angle: 0` on a `diss` source puts it to the *left* of its node pointing right | **yes**, per "on the far side of the node for a `to`" |
| `"side": "down"` on the junction to keep its label clear of the flux arrows above | **yes**, and necessary |

Only one guess was wrong, and it was the `T`.

## 4. Did `describe` confirm the drawing was the one I meant?

**Partly, and it earned its place — it caught the one defect `check` could
not.** The `Submount base | T` row is the whole reason round 3 exists. Reading
every label back as rendered text is the right design.

What it should have said and did not:

- **Nothing about connectivity.** It lists nodes and it lists elements, but it
  never says the graph is in two pieces. My diagram is two disconnected
  components joined only by an implication, and that is the single most
  load-bearing structural fact about it. `describe` reports `wire x18` and
  leaves me to work out which 18. A "components: 2" line, or a per-node degree,
  would have let me confirm at a glance that the TEC really is *the* break in
  the conduction path and not an accidental one somewhere else.
- **Nothing pairs a source with anything.** `source 2 cool ->` and
  `source 3 -> tech` are 114 units apart and are the same 60 W. Nothing relates
  them; I verified their alignment by reading coordinates by hand.
- **It does not flag a label with no value.** It faithfully printed `T`, which
  is how I found it — but in the same register as every other row. A
  `(no value)` marker, alongside the `(no label)` marker it already has for
  valueless `break` branches, would have made it jump out.
- **The `title` field never appears.** The schema says it is "not drawn", and
  `describe` does not echo it either, so the one human-readable statement of
  what the diagram *is* is unverifiable by any tool.

## 5. Features the library lacks, ranked by what they cost me here

1. **A spreading-resistance branch kind.** Cost: the diagram makes a false
   claim about its own dominant resistance, in library-set type. Nothing else
   on this list is a correctness failure. (`CLAUDE.md`, which I was given
   involuntarily, lists this as known gap #2 — but `docs/schema.md`, my only
   sanctioned source, does not hint that the six kinds are incomplete or that
   spreading was ever considered. From the schema alone I would conclude
   spreading simply is not a thing this library draws.)
2. **An active element — a TEC, a heat pump, anything that moves heat against
   the gradient.** Cost: a real component drawn as a coincidence between two
   annotations. That the 60 W in and the 60 W out are the same watts, that the
   40 W of work is what buys the uphill move, that these are one device — all
   inference.
3. **A named node with no temperature.** Cost: lost the name "Submount base"
   entirely, because the alternative was a bare `T`. The fix is one line — do
   not emit `T` when there is no `value` — and it would have saved a round.
4. **Heat rates on branches, not just at nodes.** Cost: "80 W flows down this
   ladder" and "100 W leaves the hot face" are both unsayable. In a diagram
   where the power split *is* the story — 80 W in, 60 W pumped, 40 W of work,
   100 W out — powers can only be pinned to places, never to paths.
5. **A check for a symbol printed with no value.** Cost: one round. The library
   already refuses a number without its unit; it should equally refuse a symbol
   with neither subscript nor number.
6. **UTF-8 output from `describe` by default on Windows.** Cost: one wasted
   read of a mangled report before I worked out it was the console.
7. **Grouping or enclosure.** Not needed for correctness here, but the cooler
   body / TEC / baseplate assembly is three things a reader would want boxed
   together, and there is no way to say so.

## What the diagram does say correctly

The conduction stack junction to solder to submount to cooler with its four
resistances; the 800 W/cm² flux leaving the emitting face with its own unit;
the microchannel convection to 18 °C water at a fixed boundary; the baseplate
convection to 25 °C ambient at a fixed boundary; every temperature the brief
gives; the 80 W dissipation; the 60 W pumped and the 40 W of electrical work as
separate, correctly-signed arrows. The two things it gets wrong are the
mechanism of the biggest resistance in it, and the existence of the device that
makes the whole arrangement work.
