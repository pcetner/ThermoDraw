# The gallery

Five thermal networks from five engineering domains, each drawn by a separate
agent that had never seen this library, working from `docs/schema.md` and a
brief. It has been run twice: once in this checkout, where the harness
injected the project's `CLAUDE.md` into every agent unasked, and once in a
clean room outside it, with transcripts. The folders hold the clean-room
set. See the protocol below.

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

The first time, the reading restriction did not hold. The harness
auto-injected `CLAUDE.md` — the design record, with the reasoning behind
every symbol — into each agent's context before it received its brief, and
all five disclosed it. That run is `FINDINGS-first-run.md`, and its diagrams
are at commit `c95b816`.

The second time, on 2026-09-01, it held. `RERUN.md` is the recipe: a copy of
the repository in a directory outside this checkout, with the design record,
the tests, the goldens, the README images, the worked example and every
finished diagram removed, and the outcomes that would count as failure
written down before the run. Five agents (`claude-opus-5`, Claude Code) ran
in parallel from the briefs alone, one commit each, full transcripts. No
transcript shows a file read beyond the brief and the schema. `FINDINGS.md`
grades the run against the pre-registered outcomes and collects what the
five agreed on.

## What is in each folder

| file | what it is |
|---|---|
| `brief.md` | exactly what the agent was given |
| `*.json` | the diagram it produced |
| `*.svg` | the render |
| `rounds.md` | every `check` round, and whether each remedy worked |
| `findings.md` | what it could not express, and what the documentation lacked |
| `transcript.md` | the agent's full working record, every command with its output |

`FINDINGS.md` in this directory collects what all five agreed on.

## Reading the results

A clean `check` is not the headline. Every one of these was *made* to pass, and
what that cost — how many rounds, which remedies worked, and what had to be
approximated to get there — is in `rounds.md` and `findings.md`. A diagram that
checks clean while quietly drawing a heat pipe as a conduction resistance has
told you something about the vocabulary, not about the drawing.

All five exit 0. Two carry a `parallel-pair-same-side` note that cannot be
cleared: three branches in parallel on a horizontal run have two usable label
sides, and both agents proved the remedy only rotates which pair is reported.
And all five fail `thermodraw check --physics`: the briefs' numbers do not
close at every node, every agent found that by hand before drawing, and none
retuned a value to quiet the check. That is left as drawn — these are
evidence, not examples — and the next set of briefs should be written to
close.
