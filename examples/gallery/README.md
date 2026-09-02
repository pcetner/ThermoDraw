# The gallery

Ten thermal networks from ten engineering domains, each drawn by a separate
agent that had never seen this library, working from `docs/schema.md` and a
brief. It has been run three times: once in this checkout, where the harness
injected the project's `CLAUDE.md` into every agent unasked; once in a clean
room outside it, with transcripts (`01`-`05`); and once more in a clean room
built by script, from briefs whose numbers were solved first (`06`-`10`).
See the protocol below.

## Why it exists

Two purposes, and the second is the real one.

The first is examples. A ladder of four resistances is not evidence that a
symbol vocabulary is sufficient, and `examples/hero.json` is the only complete
diagram the repository had. These are harder: a radiation-dominant satellite
panel, a building with air physically moving between zones, three nested
cryogenic temperature levels, a boiling two-phase loop, and a stack where
spreading is the largest resistance in it — and then a battery module on a
cold plate, a furnace wall quoted as a heat flux, a magnet hanging in a
cryostat on a strut that carries no heat, an oil-filled bottle on the seabed,
and a PV module losing heat three ways at once.

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

The third time, on 2026-09-02, the room was built by `tools/clean_room.py`,
which archives a named commit, removes everything that shows an answer, and
refuses to finish unless the result is clean. Two things changed besides. The
briefs' numbers were solved as networks before the prose was written, with a
reference solution for each committed beforehand, so that `check --physics` on
a finished diagram measures the library rather than the brief. And the worked
example was stripped: `docs/schema.md` quotes `examples/hero.json` in full
with its `describe` output, so run 2's "no finished diagram" was never true
and one agent found the hero actively misleading. The room's schema carries a
trivial two-node example instead. That is a recorded deviation — the agents
read a schema no real user reads.

The five systems were also chosen for coverage rather than variety. Run 2's
five diagrams and the hero never used `break` in either position, never used
`corner`, and never used `series`; `spread`, `pipe`, `phase` and `flux` were
used once each. Sixteen of the eighteen symbols were drawn in run 3, and
which two were not is in `FINDINGS-run-3.md`. Run 3's five agents worked in
parallel in one tree, which cost the one-commit-per-agent rule: two commits
swept up another agent's files.

## What is in each folder

| file | what it is |
|---|---|
| `brief.md` | exactly what the agent was given |
| `*.json` | the diagram it produced |
| `*.svg` | the render |
| `rounds.md` | every `check` round, and whether each remedy worked |
| `findings.md` | what it could not express, and what the documentation lacked |
| `transcript.md` | the agent's full working record, every command with its output |

`FINDINGS.md` collects what run 2 agreed on, `FINDINGS-run-3.md` run 3.

## Reading the results

A clean `check` is not the headline. Every one of these was *made* to pass, and
what that cost — how many rounds, which remedies worked, and what had to be
approximated to get there — is in `rounds.md` and `findings.md`. A diagram that
checks clean while quietly drawing a heat pipe as a conduction resistance has
told you something about the vocabulary, not about the drawing.

All ten exit 0. Two of run 2's carry a `parallel-pair-same-side` note that
cannot be cleared: three branches in parallel on a horizontal run have two
usable label sides, and both agents proved the remedy only rotates which pair
is reported. And all five of run 2's fail `thermodraw check --physics`: those
briefs' numbers do not close at every node, every agent found that by hand
before drawing, and none retuned a value to quiet the check. That is left as
drawn — they are evidence, not examples.

Run 3's briefs were solved as networks before they were written as prose, so
that a `--physics` finding could only be the agent's arithmetic or the
library's. None of the five reports one. The interesting result is 09, which
is silent only because three of its four free nodes were never examined, and
says so in a note that did not exist before run 2 asked for it.
