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
