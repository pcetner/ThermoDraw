# Embedded scientific font subset

The regular, semibold and italic faces derive from IBM Plex Sans 3.005,
from the complete TTF files in [IBM/plex](https://github.com/IBM/plex/tree/bf260093582f04622aacc1e9f9ca604d7ccd0c42/packages/plex-sans/fonts/complete/ttf)
at commit `bf260093582f04622aacc1e9f9ca604d7ccd0c42`.

The OFL licence is retained in `OFL.txt`. Modified subsets use the family name
ThermoDraw Sans, respecting the Reserved Font Name. `tools/font_scientific.py`
adds triple prime by composing three glyphs from the same licensed face,
and creates superscript/subscript plus and minus from that face's signs.

Regenerate fonts and metrics together:

```
python tools/subset_font.py PATH_TO_COMPLETE_TTFS
python tools/gen_metrics.py PATH_TO_COMPLETE_TTFS
```

The offered symbols come from `_catalogue.SCIENTIFIC_CHARS`. Font tests require
a cmap entry and matching advance metric for every offered glyph in all three
faces. SVG/PNG/HTML exports embed the required faces and do not rely on a
system font for the catalogue.
