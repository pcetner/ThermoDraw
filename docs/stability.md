# What 1.0 promises

A promise is only worth making about things a script or a person gates
on. These are stable from 1.0: they change only by addition within a major
version, and a removal or a change of meaning is a new major version.
`tests/test_stability.py` holds this file to the code.

## Stable

**The JSON schema** (`docs/schema.md`). Every top-level key, every field on
a node, a branch, a source, the rail and additive physical entities, every `kind`, every quantity in
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
`run-off-axis`, `frame-off-centre`, `parallel-pair-same-side`; and under
`--physics`,
`node-does-not-balance`, `rate-does-not-match`, `rad-needs-absolute-scale`,
`link-temperatures-disagree`, `physics-not-checked`,
`control-volume-not-checked` and `control-volume-does-not-balance`.
Added in 1.1: `source-direction-conflict`, `unit-spelling-clarification`,
`capacitance-unit-invalid`, `derivation-invalid`, `label-outside-region`,
and `layout-width-exceeded`. Physics reports add a `physics` metadata object
only when physics checking was requested.
This object reports the effective policy, relative and absolute tolerances,
network basis, checked/unchecked counts, status and reasons. Invocation policy
overrides affect the report without changing the document. Solver `coverage`
adds `assertion_tolerance`, `check_policy`, `network_basis`, `checked_systems`,
`unchecked_systems`, `reasons` and evaluated `derivations`. Existing `watts`
fields remain total watts; normalized results add `display_value` and
`display_unit`.

A code's severity may not rise within 1.x. A new code may be added, and a
script that gates on `ok` will see it; a script that gates on a list of
codes will not.

**`describe`'s report.** The keys of `describe --json` and of
`Description.to_dict()`: `source`, `canvas`, `counts`, `nodes` (each with
`id`, `kind`, `at`, `solved`, `temperature`, and `wall` when turned),
`edges` (each with `from`, `to`, `kind`, `count`, `arrangement`,
`directed`), `sources`, `pieces`, `rail`, `scale` and `elements`. Keys may
be added; none is removed.
The optional 1.1 keys `network_basis`, `cases` and `temperature_reference`
preserve the declared basis and reference meaning in descriptions.

**`Placement`.** The fields `element`, `at`, `angle`, `symbol`, `points`,
`label`, `radius`, `ref`, `wall`, `role`, `ends`, `via`, `count`,
`arrangement`, `outward`, `variant`, `shown`, `copy` and `index`, and the original network
elements `symbol`, `wire`, `node`, `ground`, plus `anchor` for
a repeated group's label. Physical geometry adds `region`, `volume`, `surface`,
`transfer` and `annotation`; phase nodes also have a `phase` placement.

**The public names.**

Additive 1.1 helpers: `derive_resistance`, `derive_capacity`, `derive_storage`,
`convert_basis`.

`assess_physics` assesses temporary scenarios and proposes complete-system application without changing its inputs.

`solve_physics` and `PhysicsResult` add explicit physical analysis; `solve` retains coordinate placement semantics. Everything in `thermodraw.__all__`: `Diagram`,
`Node`, `Branch`, `Source`, `Rail`, `Region`, `ControlVolume`, `ControlSurface`,
`Transfer`, `Annotation`, `DiagramError`, `solve`, `layout`,
`render`, `Placement`, `DiagramBuilder`, `check`, `Report`, `Finding`,
`describe`, `Description`, `page`, `Symbol`, `SYMBOLS`, `save`, `theme`,
and the modules `symbols`, `core`, `model` and `io`. Those four modules are
public as names — `symbols` places one symbol at a time, and the README
says so — and their contents are not: a function inside `core` may change.

**The command line.** The six subcommands `check`, `describe`, `render`,
`page`, `solve` and `solve-physics`, their documented flags, and the exit codes.

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


Component-panel categories, search aliases and property layouts are private editor presentation. They do not alter serialized roles, IDs, units or the whole-group meaning of branch `rate`. Physical placements add region, volume, surface, transfer and annotation elements to the original network vocabulary.


## Physics analysis contract

`PhysicsResult.to_dict()` contains `status`, `input_hash`, `components`, `volumes`,
`updates` and `coverage`. Aggregate statuses are `not-configured`, `solved`,
`partial` and `not-solved`. Component/volume statuses include `solved`, `balanced`,
`unbalanced`, `unchecked`, `missing-inputs`, `unsupported`, `inconsistent`,
`underdetermined`, `numerically-unreliable` and `direction-conflict`. New fields
and statuses may be added; consumers must handle unknown statuses conservatively.

Updates contain `entity`, `id`, `field`, `value` and `unit`; branch updates also
contain `index`. `PhysicsResult.apply(diagram)` returns a validated copy and
rejects a stale input fingerprint. Partial results contain only successful
systems' updates. Applying never mutates the original document.

`assess_physics` always returns `status`, `systems`, `issues`, `result`, `applied`,
`changes` and `comparisons`. Valid inputs additionally return `input_hash`,
`scenario_hash` and `effective_inputs`; invalid inputs return status `invalid`,
a null result/proposal and explanatory issues. A successful assessment may have
no proposal when nothing changed or a shared assumption prevents application.
Callers must check `applied`, and guard the original fingerprint before applying.

Supplied resistance `rate` remains a whole-group magnitude; calculated report
rates are signed from source to target. Analysis tolerances govern supplied
assertions and volume checks, while unknown network equations retain strict
numerical residual checks. See `physics-analysis.md` for partial-application rules.

## Editor rendering additions

Existing Python entry points and unit-declared JSON documents remain supported.
Repeated branches now accept `via` for the outer route; the assembly occupies
the selected segment. Very large groups use bounded compact rendering.

The internal editor bridge accepts optional presentation arguments:
`_editor.scene(data, notation="boxes", physics=False, adornments=None, display=None)`
and `_editor.export(data, what="svg", mode=None, notation="boxes", display=None)`.
`display={"mode":"automatic"}` uses engineering prefixes and
`display={"mode":"scientific"}` uses SI scientific notation. Omitting this
argument retains existing Python rendering behavior. `Diagram.display` provides
the same optional rendering preference and is excluded from JSON serialization.

Editor file metadata stores display and panel preferences separately from
full-precision unit-declared diagram data. Kelvin temperature state is separate
from editable text; display toggles never parse rendered labels back into data.
Finite temperature conversion round trips are tested against independent decimal
references within `max(1e-10 K, 8 ULPs)`. Symbolic conversions remain explicit.

Topology proposals are pure copies. Worker validation and generation/revision
checks precede interactive topology commits; Undo restores the whole operation.
Compatible legacy overlaps normalize once when opened, with their original
state retained in Undo. The supplied regression fixture originals are unchanged.
