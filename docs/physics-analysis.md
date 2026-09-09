# Explicit physics analysis

Use **Solve physics** in the editor toolbar (or the narrow-screen More menu).
The right Components area temporarily becomes the solve panel. On narrow screens
it becomes a compact panel below the drawing. Close or Escape restores Components.
Green readiness and a prominent green Solve action stay visible above results.
Blue identifies unknowns, purple actual overrides, and red invalid or missing
inputs. Known badges, selection outlines and ordinary controls remain neutral. Click a schematic badge to cycle Known → Unknown → Override → Known
where supported. Components that require supplied inputs cycle Known/Override.
Click a component to open a floating value editor beside it. The canvas Values
button opens a separate searchable navigator with Known, Unknown, Overrides and
Problems filters. Selecting a row locates its value and closes the navigator. Known, Unknown, Override, Missing and Calculated states use text
as well as outlines. Invalid cases and missing inputs use red emphasis.

Opening Solve creates a temporary session copy. Use the floating editor’s
**Known**, **Unknown**, and **Override** controls. Numeric values and supported
unit choices edit the calculation. Entering Override mode without changing the
effective value does not create an override. The saved value appears only when
the effective value differs; Restore saved value and
Restore all saved values discard temporary edits. Assumptions and unknown selections are temporary too.
Nothing is saved and no drawing undo entry is created while experimenting.
On opening, numeric drawing values are Known even if saved analysis previously
selected them as unknowns. Free nodes without numeric values start Unknown.
The Python API's explicit unknown declarations retain their existing meanings.
Overrides and calculated answers render on the schematic only during Solve,
using the shared Python renderer. Closing restores the saved drawing immediately.

Per-value unit overrides are normalized to the drawing's declared unit. For
example, entering 3000 K/kW for a resistance declared in K/W produces a temporary
3 K/W input. Global drawing units remain unchanged. A symbolic value cannot be
converted without a numeric input. Existing Units & rail controls still edit the
document declaration; changing that document makes an open session outdated.

Fixed nodes remain boundary conditions. One unknown per control volume is
supported; independent volumes and multiple network temperature unknowns can be
solved together. Attempting a second unknown in the same volume explains the
limit without replacing the first. Steady state remains an explicit Time model
choice. Readiness reports invalid, missing, unsupported, inconsistent and underdetermined cases.
Choose whole independent systems; individual balance terms cannot be excluded.

Homework examples use automatic placement with intentional manual callout offsets where needed. Explicit
label offsets in existing user documents remain intentional manual placement;
the inspector identifies this and Auto position label resets both offset and side.

With no unknown selected, Solve is disabled and the panel says **No unknown selected**.
Choose unknown opens eligible temperatures and resistances. The separate
**Check supplied values** action evaluates conservation within
stated tolerances. Selected unknowns change the primary action to Solve. Results
compare drawing values with calculated answers and their differences. Known-only
network assessments use max(0.001 W, 1% of the larger energy-balance side), unless
analysis.tolerance specifies otherwise. Unknown network equations retain strict
numerical residual verification. Legacy check --physics tolerances are unchanged.

**Review changes** first reviews the complete successful scenario, including
changed inputs, assumptions and calculated values. **Apply changes**
commits those changes as one undo step. Copy results only and Export calculation
report keep the drawing unchanged. Reports include effective inputs, scope,
diagnostics and comparisons. Partial proposals leave blocked/unselected systems
unchanged. A shared network assumption cannot be applied to only part of the
network: all its components must succeed for that shared change to be committed.

Editing the drawing invalidates the session; Restart from current drawing discards
the stale session and uses the latest document. Close opens a small confirmation dialog with Keep editing and Discard and close
when changed inputs or unapplied calculated answers exist. Escape dismisses a
floating editor or confirmation before closing Solve. Settings (included systems
and time assumptions) are last in the panel; missing time assumptions have a
direct Set time model action in readiness. File switches discard the session
and never carry its references into another document. Diagram exports always use
the drawing, excluding temporary inputs and solve markers.

The example picker contains exactly the four answered HW2 questions. See the [homework guide](example-guide.md) and [editor guide](editor-guide.md). Saved examples open with supplied answers; choose unknowns explicitly.

## Python and JSON

```python
from thermodraw import Diagram, solve_physics

diagram = Diagram.from_json(open("problem.json", encoding="utf-8").read())
result = solve_physics(diagram)
print(result.to_dict())
solved_copy = result.apply(diagram)  # explicit, original remains unchanged
```

The optional top-level configuration is:

```json
{
  "analysis": {
    "network": {"steady": true, "unknowns": ["plate"]},
    "volumes": {
      "oven": {"entity": "transfer", "id": "electrical", "field": "rate"}
    },
    "tolerance": {"absolute_w": 0.001, "relative": 0.01}
  }
}
```

Use only IDs actually present in the diagram. Omit either network or volumes
when unused. `DiagramBuilder.analysis(**settings)` accepts the same settings;
`builder.solve_physics()` is a convenience method. No runtime dependencies added.
Old JSON needs no migration; `solve()` still places drawing coordinates.

The legacy network `unknowns` field identifies free-node temperatures; `resistance_unknowns` identifies resistance branches. Other free temperatures are
assertions in the conservation equations; fixed temperatures are boundary
conditions. Resistances not selected as unknowns and heat/power sources require numeric supplied values.
Temperature units are K, C or degrees Celsius; absolute Celsius is converted to
kelvin internally, and a declared temperature-rise scale has no offset.
Resistance and power units use the library's existing conversion tables.
Parallel and series counts use the same folding rules as the checker. Ideal
links impose equal temperatures; individual ideal-link rates are reported as
unresolved. Capacitances and breaks have zero steady rate. Boundary reactions
are positive for required energy input and negative for energy removal.
Calculated branch rates are signed, positive from the declared source to target.
A resistance branch's supplied `rate` is a nonnegative magnitude for the whole
group, independent of endpoint order, following the existing checker convention.
For an unknown resistance, known endpoint temperatures determine the direction
of a supplied magnitude. Otherwise conservation must determine the signed rate;
the solver never guesses a direction from the order of the endpoints.

The network uses scaled pivoted elimination on independent components and
verifies energy residuals. Free-node equations are enforced numerically (not the
legacy checker's deliberately loose 15% tolerance for rounded annotations).
The configurable watt/relative tolerance applies to supplied branch-rate
assertions and both supplied and solved control-volume balances. The legacy
`check --physics` control-volume tolerance remains 0.001 W / 1%. Fixed temperatures joined by
an ideal link must agree. Floating, inconsistent, unsupported and incomplete
components produce diagnostics; successful independent components may still be
applied in a partial result.

Volume targets are `entity: "volume"`, the volume ID, and `field: "generation"`
or `"storage"`; or `entity: "transfer"`, an attached transfer ID, and `field:
"rate"` or `"flux"`. Flux requires a heat transfer and explicit surface area.
Remove the alternate rate/flux before selecting its unknown. A steady volume
already fixes storage at zero, so cannot select it as unknown. Numeric values
in selected unknown slots are ignored during calculation, permitting a solved
file to be recalculated. Other missing/symbolic values block the balance.
Generation must be supplied, including explicit zero, unless selected unknown.
A negative transfer solution reports a direction conflict; it never flips an
arrow. Storage is signed, positive for accumulation.

Unselected volumes are checked against supplied terms. Physical associations
never duplicate network energy in a balance. Detached transfers and unselected
volumes are included in coverage. Drawing positions and rectangular dimensions
never become physical area. Results record normalized equations and totals.
Applying writes optional `analysis.provenance` with the input fingerprint and
calculated values; this is historical provenance, not a claim that later edits
remain balanced. Applying a result to a changed input is refused.

## Command line

```text
python -m thermodraw solve-physics problem.json --json
python -m thermodraw solve-physics problem.json --apply -o calculated.json
```

Without `--apply`, `-o` saves the result report. Exit 0 means all requested
analysis/checks succeeded, 1 means incomplete or failed analysis, and 2 means
invalid input. A partial result can apply only its successful updates. The input
is never overwritten implicitly. Layout `solve` remains unchanged.

## Worked examples and limits

`examples/analysis/` contains hot-plate and wall temperature problems, an oven
power balance and a frost storage balance. Each uses the existing rectangular
homework drawing. The hot plate solves to 199.942206 C; oven input is 1834.53 kW.

This milestone solves constant-resistance networks, including identifiable resistance unknowns and one linear
energy-balance unknown per volume. It does not derive resistance from material properties, convection or
radiation laws, infer mass-carried energy from mass flow, solve stream branches,
integrate transients, find melting times, or couple multiple volume unknowns.
Unsupported network streams and network flux without physical area are explicit
diagnostics. General graph solving does not imply general automatic graph layout;
complex graphs can retain manually placed geometry.

## Delivery verification

Verified locally on 2026-09-08: 1,054 tests passed, including browser gesture,
clipboard, group resize, physics configure/review/apply/undo, and delayed-result
regressions. All four analysis examples solve and apply successfully. Type checks,
generated reference checks, site build, wheel and source-distribution builds pass.
Existing drawing goldens were not updated. Desktop and 375-pixel inspector views
were inspected using the in-app browser; screenshots are in the ignored local
`out/review/physics-desktop.png` and `out/review/physics-narrow.png` artifacts.


The solve-workflow cleanup passed the full 1,059-test suite and then 44 affected
browser/site checks after final selection and labeling refinements. The rebuilt
local site includes the curated catalog. Type and generated-reference checks
remain clean. Dark desktop and narrow views were inspected, including the
scrollbar, canvas markers, and fixed action area. No existing drawing goldens
were changed.

## Scenario assessment API and CLI

```python
import copy
from thermodraw import Diagram, assess_physics

original = Diagram.from_json(open("problem.json", encoding="utf-8").read())
scenario = copy.deepcopy(original)
scenario.nodes[0].value = 450  # temporary input, in the document's unit
report = assess_physics(original, scenario)
# report["systems"] supplies IDs for optional whole-system selection.
# report["applied"] is a validated proposal, not an automatic mutation.
```

`assess_physics(original, scenario=None, systems=None)` accepts Diagram or JSON
objects. It validates both, refuses topology/geometry changes, and returns systems,
issues, the numerical result, effective_inputs, comparisons, changes and an optional
applied proposal. Invalid models return an invalid assessment. Unknown system IDs
raise DiagramError. An empty systems list selects nothing. References to legacy
branches/sources without IDs use their fixed index within the immutable session
snapshot; neither opening nor calculating assigns document IDs.

The API requires normalized overrides in the original declared units; unit registry
changes are refused. The editor's private bridge performs per-value conversions.
Before writing a proposal outside the editor, ensure the source is still the
originating input; `input_hash` identifies that input, excluding historical
provenance. The editor additionally guards generation, revision and session edits.

```text
python -m thermodraw solve-physics original.json --assess --json
python -m thermodraw solve-physics original.json --scenario temporary.json --json
python -m thermodraw solve-physics original.json --scenario temporary.json --system network:hot --apply -o reviewed.json
```

A scenario file is a complete document copy with numeric and analysis edits only.
CLI assessment never overwrites either input implicitly. Application requires an
explicit output path. Layout solve and the existing solve_physics API retain their
meanings; the new assessment enables tolerant known-only checking separately.


## Resistance unknowns

`analysis.network.resistance_unknowns` is an optional list of resistance branch
IDs (preferred) or zero-based branch indices for legacy branches without IDs.
The existing `unknowns` list still identifies free-node temperatures. References
are validated for type, range, resistance kind and duplicates. Index references
are relative to the current document; editor deletion remaps them in the same
undoable edit. External code that reorders branches must remap indices or use IDs.

The solver adds unknown branch heat rates to the linear conservation equations.
Known resistances retain their constitutive relations. Supplied whole-group branch
rates can supply independent equations for unknown resistances. When temperatures
and rates have a unique solution, each unknown resistance is temperature drop /
heat rate. Outputs are converted back to the declared resistance unit and per-item
basis for repeated branches. Branch updates use the same stale-result guard,
comparison, complete-scenario review and Undo as temperature updates.

Two parallel unknown resistances cannot be separated from total input and boundary
temperatures alone. Supply an independent branch rate or other independent data.
Zero drop and zero flow leave resistance indeterminate; nonzero drop at zero flow
has no finite solution. Nonpositive resistances and unreliable numerical results
are refused. This identifies constant resistances; it does not fit nonlinear laws.

## Label and badge placement

Solve badges are measured in the browser and their dimensions are passed to the
shared Python renderer. Automatic labels reserve space for the centered badge
stack and avoid symbols, boundaries, arrows and other labels. Badges omit duplicate
numeric values. A manual label retains its text position; its badge searches upward
for clearance. Normal exports do not contain badges or their reserved space.

Physical labels prefer an inside corner where clear, rather than treating that
preference as a manual offset. **Auto-position all labels** in View or the Solve
canvas toolbar clears old offsets and forced sides in one undoable document edit.
This works on existing saved drawings; opening a file does not erase manual work.


## Application and identity guarantees

Scenario tolerance settings are shared by all physical systems. A changed or
removed tolerance can be applied only when every system is selected and succeeds;
otherwise the report includes an `application-limited` issue and no proposal.
Results remain available for inspection and copying. Successful proposals retain
the tolerance under which they were assessed, including an explicit zero.

Branch indices identify equations and updates internally. User IDs are labels
and references, and may contain strings such as `branch:0` without colliding
with an unnamed branch. Resistance entries in `branch_rates` include `index`;
rate coefficients use `branch:<index>` keys. Calculated update `index` selects
the original branch, even when two displayed references look identical.

Missing/symbolic inputs and nonfinite numeric strings are never evidence of
balance. The legacy checker reports unchecked inputs as notes (use `--strict`
to make notes fail a gate). Numerical overflow cannot produce a successful
analysis result. Physics analysis reports contain no NaN or Infinity values.
