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

Then find out whether it is any good, without opening it:

```bash
thermodraw check hero.json
```

```
hero.json: 11 labels placed, 0 errors, 0 warnings, 1 note
note: [parallel-pair-same-side] branch 2 s->amb and branch 3 s->amb run
      between the same two nodes and both labels went to the same side
      -> set `side` to "down" on the lower of the two
```

Eight checks on how the drawing reads — text over text, a label shoved out
past the thing it names, a wire through a symbol, ink off the page. Exit 0
clean, 1 with findings. `thermodraw render` writes the SVG, and both work as
`python -m thermodraw` from a checkout.

```bash
python examples/render_demo.py       # the three images above
python examples/render_reference.py  # every symbol at every 45°
pytest                               # 265 tests
```

## More

[`docs/schema.md`](docs/schema.md) — the whole format, written to be pasted into a prompt.
[`docs/symbol-reference.html`](docs/symbol-reference.html) — every symbol at eight orientations, with the reasoning.
[`CLAUDE.md`](CLAUDE.md) — the design record.

Alpha. The symbol vocabulary is settled; labels, wire runs and canvas size are
solved for you, and `thermodraw check` reports what a reader would notice.
Node coordinates are still yours to supply; solving for those is the network
layer, which changes one stage and nothing in the schema.

MIT. The bundled subset of IBM Plex Sans is [OFL-1.1](src/thermodraw/fonts/OFL.txt).
