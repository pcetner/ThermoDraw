# ThermoDraw

Thermal network diagrams for Python. Emits SVG, no runtime dependencies.

Draws thermal resistance networks in heat-transfer notation — hatched boxes
carrying a mechanism texture — rather than borrowing circuit schematic
symbols. Every symbol works at any orientation, and labels are placed by a
solver rather than by hand.

## Status

Alpha. The symbol vocabulary is settled; the network layer is not built yet.
Symbols are currently placed individually at coordinates you supply.

## Install

```bash
pip install -e .
```

## Use

```python
from thermodraw import symbols, theme

svg = symbols.diagonal_demo()

# For the web: CSS variables, follows the reader's light/dark setting
open("diagram.svg", "w").write(theme.with_variables(svg))

# For Word or PowerPoint: colours resolved, since neither honours var()
open("diagram-light.svg", "w").write(theme.bake(svg, "light"))
```

Render the full symbol reference:

```bash
python examples/render_reference.py
```

## Symbols

Twelve, each drawn at any angle:

| | |
|---|---|
| Free node | temperature solved for |
| Fixed node | temperature imposed, wire connects to the boundary |
| Conduction | section hatching — heat crossing solid material |
| Convection | streamlines — heat carried by a moving fluid |
| Radiation | wavy arrows crossing an empty box, dashed outline |
| Contact | two solids meeting, hatched in opposing directions |
| Capacitance | thermal mass |
| Dissipation | power appearing at a node |
| Radiative input | incident flux |
| Thermal break | adiabatic boundary, wire stops short of the wall |
| Heat flow | annotation, W |
| Heat flux | annotation, W/m² — several arrows, no single line of action |

`docs/symbol-reference.html` shows all of them at eight orientations with the
reasoning behind each choice. Open it in a browser; it carries its own
light/dark toggle.

## Design notes

`CLAUDE.md` records why each decision was made, including several that reverse
an earlier choice. Worth reading before changing a glyph or the label solver.

## Licence

MIT
