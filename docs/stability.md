# What 1.0 promises

A promise is only worth making about things a script or a person gates
on. These are stable from 1.0: they change only by addition within a major
version, and a removal or a change of meaning is a new major version.
`tests/test_stability.py` holds this file to the code.

## Stable

**The JSON schema** (`docs/schema.md`). Every top-level key, every field on
a node, a branch, a source and the rail, every `kind`, every quantity in
`units`, and what each means. New fields and kinds may be added; none is
removed or renamed. `corner` was removed before 1.0 and is the last
removal; a file naming it is refused with the replacement named. A file
that validates under 1.0 validates under every 1.x, and draws the same
network.

**`check`'s report.** The shape of `check --json` and of `Report.to_dict()`:
`source`, `ok`, `labels`, and `findings`, each with `code`, `severity`,
`where`, `message`, `remedy` and `at`. The severities `error`, `warning`
and `note`. The exit codes: 0 clean, 1 findings, 2 no answer. And the
finding codes, which a script may key on:

`label-collision`, `symbols-overlap`, `off-canvas`, `network-in-pieces`,
`nodes-too-close`, `label-adrift`, `label-in-a-corridor`,
`wire-through-symbol`, `wire-through-wall`, `symbol-off-its-run`,
`frame-off-centre`, `parallel-pair-same-side`; and under `--physics`,
`node-does-not-balance`, `rate-does-not-match`, `rad-needs-absolute-scale`
and `physics-not-checked`.

A code's severity may not rise within 1.x. A new code may be added, and a
script that gates on `ok` will see it; a script that gates on a list of
codes will not.

**`describe`'s report.** The keys of `describe --json` and of
`Description.to_dict()`: `source`, `canvas`, `counts`, `nodes` (each with
`id`, `kind`, `at`, `solved`, `temperature`, and `wall` when turned),
`edges` (each with `from`, `to`, `kind`, `count`, `arrangement`,
`directed`), `sources`, `pieces`, `rail`, `scale` and `elements`. Keys may
be added; none is removed.

**`Placement`.** The fields `element`, `at`, `angle`, `symbol`, `points`,
`label`, `radius`, `ref`, `wall`, `role`, `ends`, `via`, `count`,
`arrangement`, `outward`, `variant`, `shown`, `copy` and `index`, and the four
values of `element`: `symbol`, `wire`, `node`, `ground`, plus `anchor` for
a repeated group's label.

**The public names.** Everything in `thermodraw.__all__`: `Diagram`,
`Node`, `Branch`, `Source`, `Rail`, `DiagramError`, `solve`, `layout`,
`render`, `Placement`, `DiagramBuilder`, `check`, `Report`, `Finding`,
`describe`, `Description`, `page`, `Symbol`, `SYMBOLS`, `save`, `theme`,
and the modules `symbols`, `core`, `model` and `io`. Those four modules are
public as names — `symbols` places one symbol at a time, and the README
says so — and their contents are not: a function inside `core` may change.

**The command line.** The five subcommands `check`, `describe`, `render`,
`page` and `solve`, their documented flags, and the exit codes.

## Not stable

**The SVG.** Its bytes, its element ids, its structure, its size. Two
releases may draw the same diagram differently, and a golden held against
the library's own output is the way to notice. Ids are content-addressed
on the element's positional name, which the schema says shifts when a
branch is inserted above.

**Wording.** A finding's `message`, `remedy` and `where`; `describe`'s
text; every error message. They are written for people and are edited
when a reader shows they were unclear, which the clean-room runs do every
time.

**Coordinates the solver chooses.** A file that leaves `at` out gets the
numbers the current solver chooses, and a better solver chooses better
ones. The network is the same; the picture may not be. Write the solved
file back with `thermodraw solve` if the picture matters.

**The three boundary-wall sizes**, the label solver's constants, and
anything under `core` and `symbols` below the `Symbol` dataclass.

## How a break would be made

A field or a kind is never removed within 1.x. If one has to go, the
version before the removal refuses it with the replacement named, as
`corner` is refused now, and the major version changes.
