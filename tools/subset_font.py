"""Subset the text faces and vendor them as woff2.

    python tools/subset_font.py <dir-of-ttfs> -o src/thermodraw/fonts

Baked SVGs exist for Word, PowerPoint and rasterisers — targets that fetch
nothing. Naming a font they do not have means the text renders in Arial and
the solver's clearances, computed against different metrics, are wrong. An
embedded face removes the mismatch.

IBM Plex is OFL-1.1 with Reserved Font Name "Plex". A subset is a Modified
Version under clause 3, so the embedded faces are renamed. The CSS stack
still asks for "IBM Plex Sans" first, so anyone who has the real font gets
it, and the metrics are identical either way.
"""
import argparse
import pathlib

from fontTools import subset
from fontTools.ttLib import TTFont

RENAMED = "ThermoDraw Sans"

# Latin-1 plus the characters the symbol set reaches for. Generous on
# purpose: a glyph outside the subset falls through to the next family in
# the stack, and user labels are arbitrary text.
CHARS = ("".join(chr(c) for c in range(32, 127))
         + "".join(chr(c) for c in range(160, 256))
         + "°→″²³×±−–—‴·ΔΘΩλμ‘’“”…†‡‰€№⁄")

FACES = {"IBMPlexSans-Regular.ttf": ("normal", 400),
         "IBMPlexSans-Italic.ttf": ("italic", 400),
         "IBMPlexSans-SemiBold.ttf": ("normal", 600)}


def rename(font, style, weight):
    """Strip the reserved name from every name record, as OFL 3 requires."""
    sub = "Italic" if style == "italic" else (
        "SemiBold" if weight >= 600 else "Regular")
    full = f"{RENAMED} {sub}"
    postscript = full.replace(" ", "")
    for rec in font["name"].names:
        if rec.nameID == 1:
            rec.string = RENAMED
        elif rec.nameID == 2:
            rec.string = sub
        elif rec.nameID == 4:
            rec.string = full
        elif rec.nameID == 6:
            rec.string = postscript
        elif rec.nameID in (16, 17):
            rec.string = RENAMED if rec.nameID == 16 else sub
        elif rec.nameID == 3:
            rec.string = f"{postscript};thermodraw"
    for rec in list(font["name"].names):
        if "Plex" in str(rec):
            font["name"].names.remove(rec)


def build(src, out):
    out.mkdir(parents=True, exist_ok=True)
    made = []
    for name, (style, weight) in FACES.items():
        path = src / name
        if not path.exists():
            raise SystemExit(f"missing {path}")
        font = TTFont(path)
        options = subset.Options()
        options.flavor = "woff2"
        options.desubroutinize = True
        options.notdef_outline = True
        options.name_IDs = ["*"]
        options.name_legacy = True
        options.name_languages = ["*"]
        options.drop_tables += ["meta"]
        # Hinting is for pixel grids and these files are drawn at arbitrary
        # sizes in vector space. Dropping the layout features costs kerning,
        # which is the point: `core.text_w` sums advances and cannot see a
        # kern pair, so a font without GPOS is the one the solver is actually
        # modelling. Together they take the face from 54KB to 17KB.
        options.hinting = False
        options.layout_features = []
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=CHARS)
        subsetter.subset(font)
        rename(font, style, weight)
        dest = out / f"thermodraw-sans-{'italic' if style == 'italic' else weight}.woff2"
        font.save(dest)
        made.append((dest, style, weight))
        print(f"{name:28} -> {dest.name:34} {dest.stat().st_size:>7,} bytes")
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src", type=pathlib.Path, help="directory holding the TTFs")
    ap.add_argument("-o", "--out", type=pathlib.Path,
                    default=pathlib.Path("src/thermodraw/fonts"))
    args = ap.parse_args(argv)
    build(args.src, args.out)


if __name__ == "__main__":
    main()
