<h1 align="center">ThermoDraw</h1>

<p align="center">
  Thermal network diagrams for Python.<br>
  Emits SVG. No runtime dependencies.
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-dark.svg">
    <img src="docs/assets/hero-light.svg" alt="A power device from junction to still air: conduction, contact and a parallel convection and radiation path, with two capacitances on the reference rail" width="960">
  </picture>
</p>

<p align="center"><sub>Junction to still air — conduction, contact, then convection and radiation in parallel.</sub></p>

<br>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/vocabulary-dark.svg">
    <img src="docs/assets/vocabulary-light.svg" alt="The twelve symbols" width="800">
  </picture>
</p>

<p align="center"><sub>Twelve symbols. Mechanism is carried by the interior texture, not by the outline.</sub></p>

<br>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/assets/rosette-dark.svg">
    <img src="docs/assets/rosette-light.svg" alt="One node losing heat by twelve parallel paths, each drawn at a different angle" width="460">
  </picture>
</p>

<p align="center"><sub>Every symbol at every angle. Textures rotate; labels never do.</sub></p>

<br>

## Install

```bash
pip install -e .
```

## Use

```python
from thermodraw import save, symbols, theme

svg = symbols.diagonal_demo()

save(theme.with_variables(svg), "web.svg")    # follows the reader's light/dark
save(theme.bake(svg, "light"), "word.svg")    # colours resolved for Word
```

```bash
python examples/render_demo.py       # the three images above
python examples/render_reference.py  # every symbol at every 45°
```

## More

[`docs/symbol-reference.html`](docs/symbol-reference.html) — every symbol at eight orientations, with the reasoning.
[`CLAUDE.md`](CLAUDE.md) — the design record.

Alpha: the symbol vocabulary is settled, the network layer is not built yet.
Symbols are placed at coordinates you supply.

MIT.
