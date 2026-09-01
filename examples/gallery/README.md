# The gallery

Five thermal networks from five engineering domains, each drawn by a separate
agent that had never seen this library, working from `docs/schema.md` — and,
it turned out, from the project's `CLAUDE.md`, which the harness injected into
every agent's context unasked. See the protocol below.

## Why it exists

Two purposes, and the second is the real one.

The first is examples. A ladder of four resistances is not evidence that a
symbol vocabulary is sufficient, and `examples/hero.json` is the only complete
diagram the repository had. These are harder: a radiation-dominant satellite
panel, a building with air physically moving between zones, three nested
cryogenic temperature levels, a boiling two-phase loop, and a stack where
spreading is the largest resistance in it.

The second is a test of whether the vocabulary is *exhaustive*. The cheapest
time to discover that a thermal network needs a symbol this library does not
have is before anyone depends on it, and the most honest way to find out is to
hand the schema to somebody with no other context and watch where they get
stuck. Every one of these systems was chosen because it was likely to hit a
wall — advective transport, latent heat, active refrigeration, spreading
resistance, isothermal links.

## The protocol

Each agent was given:

- one `brief.md` describing its system in plain English, with real numbers
- `docs/schema.md`, and an explicit instruction to read nothing else — not the
  source, not `CLAUDE.md`, not `hero.json`
- the three CLI commands, and the rule that it must iterate until
  `thermodraw check` exits 0 with no errors and no warnings
- an instruction to apply the remedy each finding names *literally*, before
  trying anything else, because whether those remedies work is part of what is
  being measured
- an instruction never to silently substitute a symbol that looks close enough:
  where the schema could not say something, say so

No agent could open a browser or look at an image.

The reading restriction did not hold. The harness auto-injected `CLAUDE.md`
— the design record, with the reasoning behind every symbol — into each
agent's context before it received its brief, and all five disclosed it.
None read the source, the tests, the README or an existing diagram, and none
reported it changing a layout decision. The vocabulary findings stand:
knowing the design rationale does not hand anyone a spreading-resistance
symbol. The documentation-quality findings are softer than they look, because
the agents were not working from the schema alone. *A note on method* in
`FINDINGS.md` says the same, and the run has not yet been repeated with the
injection suppressed.

## What is in each folder

| file | what it is |
|---|---|
| `brief.md` | exactly what the agent was given |
| `*.json` | the diagram it produced |
| `*.svg` | the render |
| `rounds.md` | every `check` round, and whether each remedy worked |
| `findings.md` | what it could not express, and what the documentation lacked |

`FINDINGS.md` in this directory collects what all five agreed on.

## Reading the results

A clean `check` is not the headline. Every one of these was *made* to pass, and
what that cost — how many rounds, which remedies worked, and what had to be
approximated to get there — is in `rounds.md` and `findings.md`. A diagram that
checks clean while quietly drawing a heat pipe as a conduction resistance has
told you something about the vocabulary, not about the drawing.

Three of them no longer check clean. `04-immersion` and `05-laser-diode`
report `network-in-pieces`, because the check added after this run finds the
severed network their agents could only describe in prose. `03-cryogenic`
reports `parallel-pair-same-side` twice: its agent set `side` explicitly to
silence that note, as the remedy said to, and the note later stopped being
silenceable by its own remedy. All three are left as they were drawn: the
findings are the point.
