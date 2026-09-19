# Assignment workflows

ThermoDraw 1.1 adds explicit network bases, compact chain layout, auditable
constant-property derivations, and clearer verification. Existing files keep
their meanings. New editor files select the analysis checking policy and a
640-unit compact layout; opening an existing file never inserts those defaults.

## Checking and direction

`analysis.check_policy` is `legacy` (also the default when absent) or `analysis`.
Legacy network checks retain 15% relative slack. Analysis checks use
`analysis.tolerance.relative` and `absolute_w`, defaulting to 0.01 and 0.001 W.
Control-volume checks retain their legacy 1%/0.001 W defaults unless the analysis
policy explicitly supplies replacements. Numerical equation residuals remain
separate from these tolerances. Explicit zero tolerances are respected.

`check --physics --check-policy analysis` temporarily overrides the policy.
Python accepts `check(..., physics=True, check_policy="analysis")` and the same
keyword on `Diagram.check`. Reports include a `physics` section with effective
thresholds, checked/unchecked node, rate and volume counts, and coverage status.
Nothing checkable is not independent verification. `--strict` still makes notes
fail the CLI check.

Source `from` and `to` define the drawn direction. Legacy negative values remain
readable and retain their arithmetic, but produce `source-direction-conflict`.
Their calculated values remain inspectable; updates for conflicted components
are not applied. In Properties, **Physics and document options** offers an
explicit correction to positive Flow with the opposite endpoint direction.
Flux correction preserves the flux kind and reverses its reference direction.

Branch `rate` remains a whole-group magnitude. Set `rate_convention: "signed"`
to make it positive from `from` toward `to`. The diagram prints that reference
direction. **Calculate heat rate** calculates the existing network and reviews
the result; **Apply calculated heat rate to label** writes its magnitude unless
the signed convention was explicitly selected. A rate assertion does not create
a boundary source or override a free node's conservation equation.

## A shared network basis

```json
{
  "network_basis": {"kind": "area", "value": 2, "unit": "m²"},
  "units": {"T": "°C", "R": "K*m²/W", "q": "W/m²", "P": "W/m²"}
}
```

Kinds are `total`, `area`, and `length`. Area and length require a positive
reference `value` and compatible `unit`; total needs only its kind. Absence
means total. Per-area resistance has dimensions K·m²/W and flow W/m²; per-length
resistance has dimensions K·m/W and flow W/m. All network branches and sources
use that basis. Volume budgets continue to use total power independently.

Before conservation, resistance is divided by the reference size and normalized
flow is multiplied by it. Existing `watts`, `resistance_k_per_w`, and residual
fields retain total SI meanings. Branch results additionally expose
`display_value` and `display_unit`. Applied resistances use the original units.

`convert_basis(diagram, target)` returns a new diagram preserving total physical
values. Editor basis conversion uses this function and is one Undo step. Reference
size changes therefore preserve total heat rates rather than silently scaling
the physical system. Symbolic values cannot be converted without supplied numbers.
Normalized streams are unsupported. A flux source is usable with an area basis;
convert it explicitly to a total Flow before changing that basis.

`mK/W` is millikelvin per watt, never metre-kelvin per watt. Type `m*K/W` or
`m·K/W` for the latter. Capacitance units must have energy/temperature dimensions
to participate in calculations. Unsupported legacy units remain drawable with
a finding. Unit parsing uses the same dimensional registry throughout.

## Layout and labels

```json
{
  "layout_options": {"max_width": 640, "wrap": true, "stack": true,
                     "starts": ["inside"]},
  "cases": [{"id": "original", "label": "Original wall",
             "nodes": ["inside", "surface", "outside"]}]
}
```

Only fully unplaced chains wrap. Explicit node coordinates and branch routes
win; **Re-layout** explicitly replaces affected positions in one Undo step.
`starts` lists at most one endpoint per chain and fixes its orientation independently
of temperatures. Disconnected chains stack in document order. Width is a measured
target, not a promise achieved by shrinking text: oversized output produces
`layout-width-exceeded`. General graphs still require explicit placement.

Cases declare intended independent components. Node membership is unique and
cross-case branches are invalid. Accidental disconnection within a case continues
to warn. A reference rail joins drawing connectivity but does not make capacitances
carry steady heat. A capacitance branch still needs an explicitly chosen rail;
finite-interval control-volume storage does not.

Optional `label_runs` is a list of `{text, position}` records; position is
`normal`, `subscript`, or `superscript` (normal when omitted). Runs override label
presentation, are escaped before rendering, and use measured smaller spans.
Plain `label` text remains literal. Unicode primes need no markup. Physical
objects additionally accept `show_label: false` to suppress ID fallback.
`label_inside: true` on a region or volume requests containment; external labels
otherwise remain valid. Manual offsets remain fixed and collisions are reported.

Declared temperature-rise scales print ΔT and a reference caption. Optional
`temperature_reference` supplies explanatory text, not a numeric reference or
an inferred absolute temperature.

## Derivation inputs and owned results

```json
{
  "derivation": {
    "kind": "plane",
    "inputs": {
      "L": {"value": 0.35, "unit": "m"},
      "k": {"value": 50, "unit": "W/(m*K)"},
      "A": {"value": 1, "unit": "m²"}
    },
    "source": "Specified problem dimensions and constant conductivity"
  }
}
```

Place `derivation` on a resistance or capacitance branch. Every input is a
`{value, unit}` quantity. Optional `source` records assumptions or attribution;
ThermoDraw does not verify that source. Relations own their target values.
Rendering, checking and solving recalculate on a copy and ignore stale cached
values. Invalid inputs never fall back to the cache. Applying keeps the relation
and materializes its result. Derived resistance cannot also be an unknown.

| Kind | Required inputs | Total SI result |
|---|---|---|
| `plane` | L, k, A | L/(kA), K/W |
| `cylinder` | r1, r2, k, L | ln(r2/r1)/(2πkL), K/W |
| `sphere` | r1, r2, k | (1/r1−1/r2)/(4πk), K/W |
| `convection` | h, A | 1/(hA), K/W |
| `contact` | contact_resistivity, A | contact_resistivity/A, K/W |
| `capacity` | rho, cp, V | rho·cp·V, J/K |

Dimensions and coefficients must be positive and finite; r2 must exceed r1.
Inputs describe one element, before count/arrangement folding. Drawing size is
never physical area. Derived total resistance is converted into the declared
network basis. The public typed helpers `derive_resistance(spec)` and
`derive_capacity(spec)` return total SI results without constructing a diagram.

## Finite-interval storage

```json
{
  "storage_relation": {
    "capacity": {"value": 4200, "unit": "J/K"},
    "delta_t": {"value": -2, "unit": "K"},
    "duration": {"value": 1, "unit": "h"}
  }
}
```

Place `storage_relation` on a control volume. Choose exactly one capacity source:
`capacity`, a `capacity_derivation` using the capacity record above, or `branch`
naming an existing resolved capacitance branch ID. Supply signed `delta_t` and
positive `duration`. Celsius/Fahrenheit temperature units mean intervals here.
The result includes energy change CΔT and average storage power CΔT/Δt. Negative
change releases energy. The relation is incompatible with steady mode and owns
storage; remove it to supply manual storage or select storage as an unknown.

`derive_storage(spec, capacitance=None)` returns `capacity_j_per_k`, `energy_j`,
and `watts`. The optional second argument resolves a branch reference for callers
outside a diagram. Diagram evaluation resolves branch IDs itself. Dependencies
are restricted to capacity → storage; arbitrary expression references and cycles
are not accepted. No transient integration, property lookup, economic ranking,
critical-radius calculation, inverse geometry or nonlinear material laws are added.

## Examples and compatibility

See `examples/assignment/` for minimal repository-owned HW3 regression cases.
The four existing HW2 examples remain the editor picker contents.
JSON values may be strings or finite numbers. Authored strings preserve their
digits; computed values are numbers and display formatting is independent.
Machine CLI JSON uses safe escaping; files are UTF-8. Human `describe` shows
annotation text without JSON Unicode escapes where the console supports it.
