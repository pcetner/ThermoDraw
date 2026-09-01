# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-08-31

0.1.0 was a symbol library: it drew one symbol at a time, at coordinates you
supplied. 0.2.0 makes a diagram a piece of data, makes the render
reproducible, and puts a test suite under both.

### Added

- **A data model, and a pipeline.** `dict`/JSON → `Diagram` → placements →
  SVG, as three pure stages: `model`, `layout`, `render`. The model carries no
  SVG and no geometry beyond the coordinates given to it, so a diagram loaded
  from JSON is indistinguishable from one built in code. `Diagram`, `Node`,
  `Branch`, `Source`, `Rail` and `DiagramError` are the vocabulary.
- **`DiagramBuilder`**, sugar over the same data — anything the builder can
  say is expressible as data.
- **A JSON schema**, `docs/schema.md`, written to be pasted into a prompt.
- **`save()`**, which writes UTF-8 (see *Fixed*).
- **Measured font metrics.** `_metrics.py`, generated per face by
  `tools/gen_metrics.py`, replaces a sixteen-entry estimate table.
- **An embedded font.** Three subsetted woff2 faces ship in the package as
  ThermoDraw Sans; `theme.faces_used` embeds only the faces a given diagram
  needs, so baked SVGs for Word, PowerPoint and rasterisers carry the font
  they name.
- **Diagram-aware label placement.** An occupancy structure carries the placed
  labels, the drawn wires and the symbols. `annotate` tries the automatic side
  of the branch first and the opposite side second, so a blocked label steps
  across the branch rather than drifting off it; only if both are blocked does
  it push out. A `side="up"/"down"/"left"/"right"` override was added.
- **A documentation generator.** `tools/gen_docs.py` builds
  `docs/symbol-reference.html` from the library and a prose template, with the
  per-symbol notes coming from `Symbol.note`. `--check` fails if the committed
  page is not a fresh render.
- **Unit validation**, catching a value with no unit — which used to render as
  a bare number — with an error naming the element and the quantity.
- **An explicit `__all__`**, drawn deliberately around the data, the pipeline,
  the vocabulary and output.
- **102 tests**, where there were none: golden SVGs for all 17 scenes,
  determinism, id uniqueness, the model and its errors, label clearance, the
  font subsets against the width table, and the docs page against a fresh
  render.
- **Three demo scenes and a visual README** — a power-device ladder, a
  twelve-path rosette and a vocabulary sheet, in light and dark. The hero
  renders from `examples/hero.json`.
- **Packaging**: an MIT `LICENSE`, a `NOTICE` recording the OFL-1.1 terms of
  the bundled fonts, and a PEP 561 `py.typed` marker so type checkers read the
  annotations that were already there.
- `.gitattributes` pinning LF, since the goldens compare byte for byte.

### Changed

- **The render is deterministic.** Element ids derive from the element's own
  parameters rather than a module-global counter, so the same diagram renders
  to the same bytes twice in one process. Identical elements therefore share an
  id by design: `canvas()` hoists every `<defs>` block to the front and keeps
  one copy of each, which collapses the rosette from 24 clip paths to 4 and
  takes output 2.7% smaller.
- **Symbols are objects.** Geometry lived in twelve `g_*` functions while the
  extents the label solver needs lived in a parallel dict; both now travel
  together on a frozen `Symbol` dataclass, with fields named rather than
  abbreviated (`g` → `draw`, `val` → `value`, `hl` → `half_len`). The four box
  symbols also expose their interior on its own.
- **Text is measured in the face that will draw it.** The old table assumed
  0.55 for 36 of the 52 glyphs the library emits; measured against IBM Plex the
  mean per-glyph error was 12%, and 98% for `/`. SemiBold runs 4% wider than
  Regular — the same size as the error being removed.
- **Kerning is dropped from the subsets, deliberately.** `text_w` sums advances
  and cannot see a kern pair, so a font without GPOS is the one the solver is
  modelling. It also takes each face from 54KB to 19KB.
- **The canvas sizes itself** to what was actually drawn, which retired the
  regex that rewrote the root tag.
- Segments shared by two branches are stroked once.
- The README leads with the data API.

### Fixed

- **`save()` writes UTF-8.** `conv`, `rad` and `flux` emit an arrow or a double
  prime; `write_text` defaults to cp1252 on Windows, which crashed
  `render_reference.py` outright.
- **Exported SVGs carry explicit pixel dimensions.** `canvas()` emitted
  `width="100%"`, which is right for a page that owns its column and wrong for
  a file loaded through an `<img>` tag.
- **Duplicate ids in one document** — invalid SVG, even where renderers
  tolerate it — no longer occur.
- **Baked SVGs no longer render in Arial** while the clearances assume Plex.
- A capacitance takes an identity subscript from the caller, as `T` does;
  `DiagramBuilder.branch` gained the `sub` it needed.
- A fixed node's label clears its boundary wall rather than a 5.5px circle.
- `docs/symbol-reference.html` was stale — labelled draft 5 against `core.py`'s
  draft 4 — and now cannot go stale silently.
- **`validate()` checks the shape of what it is given.** It verified ids and
  kinds but nothing else, so seven ways of writing a bad coordinate got
  through: six died inside the renderer with messages like `Unknown format
  code 'f' for object of type 'str'` that named no node and no field, and one
  drew the wrong picture in silence. Coordinates, angles, waypoints, rail
  geometry and values are now checked before anything draws, and the error
  names the element and the field.
- **A near-miss key is named and corrected.** An unknown field raised
  `Node.__init__() got an unexpected keyword argument 'name'` — a Python
  internal, the wrong exception type, no hint. It now raises `DiagramError`
  with a suggestion (`'name'` -> `'label'`, `'position'` -> `'at'`,
  `'type'` -> `'kind'`) and the list of valid fields. The flagship input is
  JSON written by a model, so these are the errors that matter most.
- **`save()` no longer prepends an XML declaration to non-SVG files**, which
  turned a written diagram-as-data file into invalid JSON.

## [0.1.0] - 2026-08-31

The baseline, recorded so the changes above are reviewable.

- Twelve symbols, each drawn at any angle.
- Label placement solved from the symbol's oriented bounding box.
