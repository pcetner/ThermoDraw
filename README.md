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

A diagram is data. Write it, or have a model write it, and render it:

```python
from thermodraw import Diagram, layout, render, save, theme

d = Diagram.from_json(open("hero.json").read())
svg = render(layout(d))

save(theme.with_variables(svg), "web.svg")   # follows the reader's light/dark
save(theme.bake(svg, "light"), "word.svg")   # colours and font resolved
```

Or build it in Python:

```python
from thermodraw import DiagramBuilder

d = (DiagramBuilder(R="K/W", T="°C", P="W")
     .node("j", "Junction", 112, at=(200, 150), sub="j")
     .node("c", "Case", 78, at=(424, 150), sub="c")
     .branch("j", "c", "cond", "Die attach", "0.35")
     .source("j", "diss", "Switching loss", 45, sub="d"))
open("out.svg", "w", encoding="utf-8").write(d.svg("light"))
```

```bash
python examples/render_demo.py       # the three images above
python examples/render_reference.py  # every symbol at every 45°
pytest                               # 100 tests
```

## More

[`docs/schema.md`](docs/schema.md) — the whole format, written to be pasted into a prompt.
[`docs/symbol-reference.html`](docs/symbol-reference.html) — every symbol at eight orientations, with the reasoning.
[`CLAUDE.md`](CLAUDE.md) — the design record.

Alpha. The symbol vocabulary is settled and labels, wire runs and canvas size
are solved for you. Node coordinates are still yours to supply; solving for
those is the network layer, which changes one stage and nothing in the schema.

MIT. The bundled subset of IBM Plex Sans is [OFL-1.1](src/thermodraw/fonts/OFL.txt).
