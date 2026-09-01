"""ThermoDraw from the command line.

    thermodraw check    diagram.json
    thermodraw describe diagram.json
    thermodraw render   diagram.json -o out.svg --mode light

    python -m thermodraw check diagram.json      # from a checkout, no install

`check` is the reason this exists, and `describe` is the half it could not
cover: the checker says nothing is wrong with the drawing and cannot say it is
the drawing you meant.

`check` is the reason this exists. Finding out whether a diagram was any good
used to mean rendering it, serving it over HTTP, opening a browser, taking a
screenshot and looking — five sequential steps, none of which a script or a
model can do cheaply. This is one call whose output is text, and whose exit
status is the answer.

Exit codes: 0 clean, 1 findings, 2 the file could not be read or was invalid.

Stdlib only, and SVG only. PNG needs a rasteriser, a rasteriser is a
dependency, and the library has none.
"""
import argparse
import json
import pathlib
import sys

from . import theme
from .check import ORDER, Finding, check
from .describe import describe
from .layout import layout
from .model import Diagram, DiagramError
from .render import render


def _die(message):
    """Exit 2, which is neither "clean" nor "findings" but "no answer"."""
    print(f"error: {message}", file=_soften(sys.stderr))
    raise SystemExit(2)


def _load(path):
    """The diagram at `path`, or exit 2 saying why."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        _die(f"cannot read {path}: {exc.strerror}")
    try:
        return Diagram.from_json(text)
    except DiagramError as exc:
        _die(f"{path}: {exc}")
    except ValueError as exc:                       # not JSON at all
        _die(f"{path} is not valid JSON: {exc}")


def _soften(stream):
    """Let a cp1252 console print a diagram's own labels without dying.

    Findings quote node ids, branch endpoints and units keys, which come from
    the file and can hold anything. The fixed text is ASCII; this covers the
    rest.

    `backslashreplace`, not `replace`. The units quantity for a heat flux is
    `q` followed by U+2033, and on a cp1252 console `replace` printed "units
    names 'q?'" — an error naming a key the reader cannot copy, about a
    character they most likely mistyped in the first place. This prints
    'q\\u2033', which is ugly and recoverable.
    """
    try:
        stream.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):            # not a real tty, or piped
        pass
    return stream


def _strict(report):
    """Promote every note to a warning, so advice fails the run too."""
    report.findings = [
        f if f.severity != "note" else Finding(
            f.code, "warning", f.where, f.message, f.remedy, f.at)
        for f in report.findings]
    report.findings.sort(key=lambda f: (ORDER[f.severity], f.code, f.where or ""))
    return report


def do_check(args):
    report = check(_load(args.diagram), size=args.size, source=args.diagram)
    if args.strict:
        report = _strict(report)
    out = _soften(sys.stdout)
    if args.json:
        json.dump(report.to_dict(), out, indent=2, ensure_ascii=False)
        out.write("\n")
    elif args.quiet:
        for finding in report.findings:
            print(finding.line(out.isatty()), file=out)
    else:
        print(report.text(colour=out.isatty()), file=out)
    return 0 if report.ok else 1


def do_describe(args):
    """What got drawn. Always exit 0: this reports, it does not judge."""
    out = _soften(sys.stdout)
    description = describe(_load(args.diagram), size=args.size,
                           source=args.diagram)
    if args.json:
        json.dump(description.to_dict(), out, indent=2, ensure_ascii=False)
        out.write("\n")
    else:
        print(description.text(), file=out)
    return 0


def do_render(args):
    diagram = _load(args.diagram)
    svg = render(layout(diagram), size=args.size or diagram.size)
    svg = theme.bake(svg, args.mode) if args.mode else theme.with_variables(svg)

    if args.out == "-":
        _soften(sys.stdout).write(svg)
        return 0
    path = pathlib.Path(args.out or pathlib.Path(args.diagram).with_suffix(".svg"))
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg)
    print(f"{path} ({len(svg):,} bytes)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="thermodraw",
                                 description=__doc__.split("\n\n")[0])
    subs = ap.add_subparsers(dest="command", required=True)

    def size(sub):
        sub.add_argument("--size", nargs=2, type=float, metavar=("W", "H"),
                         help="fix the canvas instead of measuring it")

    c = subs.add_parser("check", help="report what is wrong with a diagram")
    c.add_argument("diagram")
    c.add_argument("--json", action="store_true", help="machine-readable")
    c.add_argument("--strict", action="store_true",
                   help="treat notes as warnings, so they fail too")
    c.add_argument("--quiet", action="store_true",
                   help="findings only, no summary line; silent when there "
                        "is nothing at all to report")
    size(c)
    c.set_defaults(fn=do_check)

    d = subs.add_parser("describe", help="say what the drawing contains")
    d.add_argument("diagram")
    d.add_argument("--json", action="store_true", help="machine-readable")
    size(d)
    d.set_defaults(fn=do_describe)

    r = subs.add_parser("render", help="write the diagram as SVG")
    r.add_argument("diagram")
    r.add_argument("-o", "--out", help='output path, or "-" for stdout')
    r.add_argument("--mode", choices=["light", "dark"],
                   help="bake the palette, for Word, slides and rasterisers")
    size(r)
    r.set_defaults(fn=do_render)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
