# Homework diagrams

The editor Example menu contains only the four answered questions from `HW2 - submission.pdf`, in submission order. Click a title to create an editable copy. Existing saved files are unaffected. Historical gallery/API fixtures remain in the repository but are not offered in this picker.

| Question | Drawing | Submitted result |
| --- | --- | --- |
| 1.44 | Rectangular annealing oven, control volume, electrical work, net steel energy gain, convection, radiation and base conduction | Approximately 1834.5 kW electrical input |
| 1.51 | Adjacent frost/air rectangles, exposed surface and convection flux feeding latent storage | 17,535 s = 4.87 h |
| 1.57a | One solid-wall rectangle, labeled inner/outer surfaces and outward convection/radiation paths, with a linked resistance network | Inner surface 599.4 K |
| 1.60a | Rectangular plate schematic, explicit steady-state callout and parallel convection/radiation network with electrical input | 188.6 W |

1.61 is marked SKIPPED in the submission and is excluded.

## Using the examples

The examples open with supplied answers, rather than silently turning a different quantity into the assignment unknown. Open Solve physics to check supplied values, or explicitly choose an eligible unknown and calculate. Temporary overrides let you explore without changing the saved drawing. Export produces a compact light SVG or PNG.

The frost diagram includes the submitted melting time as a text annotation. Its balance checks the supplied 40 W storage from 40 W/m² over an explicit 1 m² area; it does not integrate melting. The oven uses the submitted net steel energy gain relative to inlet conditions, counted once as a mass-carried-energy crossing. Drawing dimensions do not imply physical area.

## Fidelity and rounding

These are editable schematic reconstructions using ThermoDraw symbols and rectangular regions, not embedded screenshots. The wall preserves the submitted 599.4 K and rounded resistances. The oven sums the submitted rounded terms to 1834.53 kW (reported as 1834.5 kW in the homework).

The hot-plate submission labels the surroundings 25 °C but uses 293.15 K in coefficient calculations; 25 °C corresponds to 298.15 K. The example preserves the submitted 25 °C label, 3.16 and 1.313 K/W resistances and 188.6 W answer. Checking those supplied values is not validation of the original coefficient derivation.

See the [editor guide](../../docs/editor-guide.md) for the searchable component library and floating property workflows.
