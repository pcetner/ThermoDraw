# Re-running the gallery in a clean room

The first run's protocol said each agent would read `docs/schema.md` and
nothing else. It did not hold: the harness injected the project's `CLAUDE.md`
into every agent's context before it received its brief, and all five said
so. `FINDINGS.md` disclosed it and said to suppress the injection before
re-running. This is how, and what to record when it is done.

## Why it cannot be run from inside this checkout

The injection *is* the harness behaviour: any agent started for this project
gets this project's `CLAUDE.md`, whoever starts it and whatever the prompt
says. An agent working in this repository therefore cannot run a clean room —
it can only run another leaky one and disclose it again. The re-run has to
start from a directory in which the file does not exist.

## The clean room

From the repository root:

```bash
room="$(mktemp -d)/thermodraw-clean"
mkdir -p "$room"
git archive HEAD | tar -x -C "$room"
cd "$room"
rm -f CLAUDE.md docs/design-record.md README.md CHANGELOG.md Dictionary.html
rm -rf .claude docs/symbol-reference.html docs/assets docs/notation-test tests tools
rm -f docs/*.template.html examples/*.py examples/hero.json
rm -f examples/gallery/*/findings.md examples/gallery/*/rounds.md \
      examples/gallery/*/*.json examples/gallery/*/*.svg
rm -f examples/gallery/FINDINGS.md examples/gallery/README.md examples/gallery/RERUN.md
git init -q && git add -A && git commit -qm "clean room"
```

The tests, the goldens, the README images, the worked example and the
notation thumbnails all go too: every one of them is a finished diagram, and
an agent that opens one has seen the answer. `tools/` goes because
`gen_dictionary.py` carries every symbol's meaning in prose, which is
documentation the protocol says the agent does not get.

No install: the library has no dependencies and the briefs run it as
`PYTHONPATH=src python -m thermodraw`. The `git init` is not optional — the
briefs find the root with `git rev-parse`, and one commit per agent is what
makes the run auditable.

What is left is the library, `docs/schema.md`, and the five `brief.md`
files. Nothing that argues for a design, nothing that shows a
finished diagram, nothing that names a prior result. Confirm before starting
— no `CLAUDE.md`, five briefs, and the checker runs:

```bash
test ! -e CLAUDE.md && ls examples/gallery/*/brief.md | wc -l \
  && PYTHONPATH=src python -m thermodraw check --help >/dev/null && echo clean
```

Then start **one fresh session per brief, from that directory**, and give it
only the brief. The brief already says which three commands to run and how to
iterate.

## What to record

The first run landed 27 files in one commit with no transcripts, so it cannot
be audited by anyone but its author. This one is worth more than the first
only if it can be:

- **One commit per agent**, under `examples/gallery/NN-*/`, containing the
  diagram, its render, `rounds.md`, `findings.md`, and the **full transcript**
  as `transcript.md`. The transcript is the evidence; the findings are the
  agent's reading of it.
- The **model and harness** used, in `rounds.md`'s first line.
- `thermodraw check --physics` output for the final diagram, in `rounds.md`.
  The first run's diagrams all fail it. If this run's do too, that is a fact
  about the briefs, not the agents, and it is worth knowing.

## Pre-registered outcomes

Written before the run, so the run cannot be read as confirming whatever it
produced. The claim under test is that the vocabulary is exhaustive for these
five systems and that `docs/schema.md` alone is enough to draw one.

The **vocabulary claim fails** for a domain if its agent reports, in
`findings.md`, a physical thing it could not express and had to approximate —
the first run found nine, and eight have since shipped. Active, pumped heat
(a Peltier stage, a refrigerator) is the one still open and is expected to
recur in `04-immersion` and `05-laser-diode`. Anything *else* is new.

The **documentation claim fails** if any agent needs more than six `check`
rounds to reach exit 0 with no errors and no warnings, or asks a question the
schema should have answered. The first run's counts are in each `rounds.md`.

The **remedy claim fails** if any remedy, applied literally as the brief
instructs, makes the next report worse. The first run: six of eighteen worked
and three made it worse, and the remedies were rewritten because of it.

The **run is not clean** if any transcript shows the agent reading a file
that the clean room removed, or referring to a design rationale the brief
does not contain.

Any of these failing is a finding, not a failure of the exercise. What would
make the exercise worthless is running it and then deciding what it showed.

## The run

Done on 2026-09-01, from a sibling directory of the checkout — a `git
archive` of `c95b816` with the files above removed, committed as `df3a92f`
in its own repository. Five `claude-opus-5` subagents under Claude Code, in
parallel, one line of prompt each, one commit each, transcripts committed.
Graded in `FINDINGS.md`: the vocabulary claim failed in all five domains,
the documentation claim failed (01 took nine rounds; four agents asked a
question the schema should have answered), the remedy claim failed (7 of 31
made the next report worse, 7 could not be applied as written), and the run
was clean.

Two things the recipe did not anticipate, for the next one. `docs/schema.md`
quotes the hero diagram and its `describe` output in full, so every agent
had one worked example after all, and one found it misleading. And the
directory must be a *sibling* of the checkout, not inside it: the harness
reads `CLAUDE.md` from every ancestor directory, so a clean room under this
one is not clean.

# Run 3

Prepared 2026-09-02. Five new domains, five new briefs, and three changes to
the protocol. Run 2's four claims all failed; the eight library defects and
six documentation defects it found have since been fixed, and until this run
nothing has re-tested them. That is what run 3 is for.

## What is different, and why

**New domains, not the same five.** Run 2's five are evidence and are left
exactly as their agents drew them. Re-running them would mostly re-find the
four format gaps already recorded, which are unbuilt by decision rather than
by oversight. New domains ask a question that has not been asked.

**The briefs' numbers close.** Every temperature, resistance and power in the
five briefs was solved as a network first and only then written into prose.
A reference solution for each lives in `examples/gallery/run-3/reference/`,
committed *before* the run so that the pre-registration is checkable, and
removed from the clean room by `tools/clean_room.py`. Each reference passes
`check` with no errors, no warnings and no notes, and `check --physics` on
each is silent. Run 2 could not tell a library defect from a brief whose
numbers never closed; this run can.

**The five briefs use every symbol between them.** Run 2's five diagrams,
plus the hero, never used `break` in either position, never used `corner`,
and never used `series`; `spread`, `pipe`, `phase` and `flux` were each used
exactly once. A symbol no brief forces is a symbol no evidence covers. The
table below is the coverage claim, and it is checked against the finished
diagrams after the run, not before.

**The room is a script.** `tools/clean_room.py` archives a named commit,
removes everything that shows an answer, and then verifies its own work —
no `CLAUDE.md`, no `.claude`, no tests, no tools, no finished diagram, five
briefs, and a checker that runs. Run 2's room was a block of shell pasted
into a terminal, which cannot be audited afterwards.

**The worked example is gone.** `docs/schema.md` quoted `examples/hero.json`
in full together with its `describe` output, so run 2's "no finished diagram"
was not true and one agent found the hero actively misleading. The room's
copy of the schema carries a deliberately trivial example instead — two
nodes, one path, one source, its JSON and its real `describe` output
generated by the archived library — and every sentence that named the hero is
rewritten. This is a **recorded deviation**: the agents read a schema no real
user reads. It is the price of the protocol being literally true, and if a
run-3 agent reports the schema is missing a worked example, that is this
decision showing up as a finding rather than a surprise.

## What each brief is for

| | system | what it forces that nothing had forced |
|---|---|---|
| 06 | EV battery module on a liquid cold plate | `count` on a **source**, a `flow` branch carrying a rate, `contact`, two `cap`s on the rail |
| 07 | Industrial furnace wall | a `flux` source, `count` + **`series`**, `rad` and `conv` in parallel off one node, `via` |
| 08 | Superconducting magnet in a cryostat | **`break` as a node and as a branch**, a `phase` node, a `flow` source pointing **away**, `radin`, `angle` on a branch |
| 09 | Subsea electronics bottle | `spread`, `pipe`, `mixed`, a **`corner`** node routing a wire |
| 10 | Roof-mounted PV module | `count` + `parallel`, `radin`, `rad` to sky against `conv` to air, `angle` on a node label |

Between them: all ten branch kinds, all five node kinds, all four source
kinds, both arrangements, and every field that changes what is drawn.

## Pre-registered outcomes

Written before the run. Any of these failing is a finding, not a failure of
the exercise; what would make the exercise worthless is running it and then
deciding what it showed.

**The physics claim — new, and the sharpest.** Each brief's numbers close by
construction, and each reference solution is silent under `check --physics`.
So a `--physics` finding on a run-3 diagram is either the agent's arithmetic
or the library's, and the transcript says which. The claim **fails** if any
final diagram reports a `node-does-not-balance` or `rate-does-not-match` that
the reference does not.

**The vocabulary claim, narrowed.** Run 2 recorded four gaps that are known
and unbuilt by decision: no way to say two elements are related, a stream
having an inlet and an outlet temperature where a node has one, no quantity
outside `R C T P q q″`, and no way to mark a number a capacity, a limit or
provisional. **Recurrence of those four is not a new finding.** The claim
fails on anything outside that list — and one thing outside it is expected,
since nothing marks a branch as active.

**The documentation claim.** Fails if any agent needs more than **six**
`check` rounds to reach exit 0 with no errors and no warnings, or asks a
question the schema should have answered. Six specific defects were fixed
after run 2 and none may recur: the `render`/`theme` paragraph that did not
say it was about the Python function; the stale sentence saying a moving
fluid has no branch kind; "`at` only has to be roughly right"; the
`--physics` units left unlisted; whether `rail` and a node's `label` are
optional; and whether `rate` on a counted branch is per item.

**The remedy claim.** Fails if any remedy, applied literally as the brief
instructs, makes the next report strictly worse, or names a field the element
cannot take. Run 2: of 31 remedies applied, 16 cleared their finding, 7 made
the next report worse, and 7 could not be applied as written.
`tests/test_clean_room.py` replays those five diagrams and guards the fixes.

**The run is clean** if no transcript shows the agent reading a file the room
removed, or referring to a rationale the brief does not contain.

## Running it

```bash
python tools/clean_room.py ../ThermoDraw-cleanroom-run3
```

Then one fresh session per brief, started **in that directory**, each given
one line naming its brief. `START-HERE.txt` in the room carries the five
lines and the recording instructions.
