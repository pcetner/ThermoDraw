# Release engineering review

## Candidate and scope

Baseline: `c6facfff5e5d850f40db63019db872eae73a60fb`, including the pre-existing
uncommitted physical model, analysis, scenario and editor additions. The initial
review passed 1,110 tests but found seven gaps with independent reproductions.
This pass implements fixes on that working tree; it does not publish a release.

Local verification uses Windows, Python 3.11.9, pytest 8.3.5, mypy 2.3.1,
Playwright 1.62.0, build 1.6.0 and twine 7.0.0. Builds use isolated build
dependencies; the development environment's setuptools is not the build floor.
CI retains Python 3.10–3.13 on Windows and Linux and a Chromium editor job.

## Finding register

| Finding | Priority | Resolution and regression evidence |
| --- | --- | --- |
| Infinite numeric strings could pass legacy balances | P1 | Shared finite parsing; overflow is unchecked, not balanced. `test_nonfinite_temperature_is_never_certified`, `test_finite_inputs_that_overflow_do_not_balance`. |
| Release tests ran before build prerequisites were installed | P1 | Install dev/build dependencies first; publication requires reusable full CI. `test_the_release_workflow_guards_the_tag`. |
| Checker and solver disagreed on resistance rate sign | P2 | Supplied rate remains whole-group magnitude; calculated rate remains directional. Reversed known/unknown resistances and series/parallel counts tested by `test_rate_magnitude_survives_endpoint_reversal`. |
| Applied scenarios dropped their approval tolerance | P2 | Preserve or remove tolerance explicitly; changed shared tolerances require all systems to succeed and be selected. Application/reassessment and partial-selection regressions. |
| Explicit IDs could overwrite implicit solver identities | P2 | Branch indices key solver variables; display IDs are separate. `test_branch_ids_cannot_replace_another_unknown`. |
| Supplied volume analysis ignored custom tolerances | P2 | Analysis passes tolerance to shared budgets; legacy checking keeps its previous defaults. Strict-zero regression. |
| Public calls became Any for consumers | P2 | Typed builder/model serialization/output and analysis entry points; typed report/update envelopes. Consumer tests prove both valid calls and rejected misuse. |

Additional adjacent fixes: negative source/flow inputs now contribute to the
correct balance side; checking an ideal link to the reference rail resolves its
reference temperature; the builder accepts stream `mdot` and `cp`; scenario mass
flow conversion shares the model's complete conversion table.

## Contracts and coverage

- Numerical equations: known analytic chain answers, reordered nodes and
  equivalent units, reversed endpoints, counts, collisions and overflow.
- Scenario transactions: assessment purity, stale application, successful
  proposal reassessment, partial systems and shared assumption restrictions.
- Compatibility: new dataclass fields remain appended; serialization retains
  existing fields; supplied branch rates preserve magnitude semantics.
- API: stable report envelopes, update keys, fluent return types and misuse
  checks. Detailed component dictionaries remain extensible; full strict typing
  of internal algorithms is deferred.
- Rendering/editor: existing goldens, generated-document checks and Chromium
  interaction tests exercise export, cancellation, delayed results, selection,
  copying, physical authoring and scenario application. No new editor gestures
  were introduced in this pass. No separate manual accessibility or cross-browser
  visual certification is claimed.
- Artifacts: `tools/release_smoke.py` installs the wheel and rebuilds/installs the
  sdist in separate fresh virtual environments outside the checkout. It checks
  imports, typing marker, font resources, SVG/HTML, physical geometry, analysis
  and CLI rendering/solving. CI and publication both run it.

## Repeating the gate

```text
python -m pytest -q
python -m mypy --check-untyped-defs src/thermodraw
python -m build
python -m twine check dist/*
python tools/release_smoke.py dist
```

Playwright and its Chromium browser must be installed to include editor tests;
CI does this explicitly. The artifact directory must contain exactly one wheel
and one sdist. Release notes are generated before PyPI publication, so missing
notes cannot leave a half-completed release.

## Verification and release disposition

Final local verification after the last source changes:

- Full suite: **1,132 passed**, including Chromium editor tests (69.26 seconds).
- Mypy: **no issues in 21 source files**, plus the consumer typing regression.
- Wheel and sdist: **built successfully** with isolated build dependencies.
- Twine metadata checks: **both artifacts passed**.
- Clean installation smoke checks: **wheel and rebuilt sdist passed**.
- `git diff --check`: **passed**.

The artifacts were built in a temporary directory outside the checkout. Local
verification covers Windows/Python 3.11; the configured remote CI matrix still
must pass on the committed candidate before publication. All seven reproduced
review findings are addressed; no P1 finding remains open in this pass.

The remaining release preparation is administrative: choose the next version,
move the finalized Unreleased notes into its dated section, regenerate versioned
documentation and commit the candidate before tagging it. Version remains 1.0.0
in this working tree; neither a tag nor a package has been published.

Deferred work is intentionally separate from these fixes: general graph layout,
transient/nonlinear physics, material-law derivation, splitting the editor into
modules and exhaustive typing of nested diagnostics. A supplied rate magnitude
cannot invent the direction of an unknown resistance: known temperatures or
independent conservation equations must determine its sign; otherwise the solver
reports an unresolved system.
