"""ThermoDraw from the command line.

    thermodraw check    diagram.json
    thermodraw describe diagram.json
    thermodraw render   diagram.json -o out.svg --mode light
    thermodraw page     diagram.json -o out.html
    thermodraw solve    diagram.json -o placed.json

    python -m thermodraw check diagram.json      # from a checkout, no install

`check` is the reason this exists, and `describe` is the half it could not
cover: the checker says nothing is wrong with the drawing and cannot say it is
the drawing you meant. `page` is the same drawing with its controls, for a
repeated group a reader may want to expand.

Finding out whether a diagram was any good
used to mean rendering it, serving it over HTTP, opening a browser, taking a
screenshot and looking — five sequential steps, none of which a script or a
model can do cheaply. This is one call whose output is text, and whose exit
status is the answer.

Exit codes: 0 clean, 1 findings, 2 no answer — the file could not be read or
was invalid. Only `check` can exit 1. 2 is also what argparse exits with for a
bad command line; a script that needs to tell the two apart has stderr.

Stdlib only. SVG and HTML; PNG needs a rasteriser, a rasteriser is a
dependency, and the library has none.
"""
import argparse
import json
import pathlib
import sys

from . import theme
from ._check import ORDER, Finding, check
from ._describe import describe
from ._layout import layout
from ._page import page
from ._render import render
from ._solve import solve
from .io import DECLARATION, save
from .model import Diagram, DiagramError


def _die(message):
    """Exit 2, which is neither "clean" nor "findings" but "no answer"."""
    print(f"error: {message}", file=_soften(sys.stderr))
    raise SystemExit(2)


def _load(path):
    """The diagram at `path`, or exit 2 saying why."""
    # `utf-8-sig`: PowerShell's Out-File and older Notepads write a BOM, and
    # the file is no less UTF-8 for it. A file that is not UTF-8 at all used
    # to escape as a traceback with exit 1 — the code reserved for "findings"
    # — because UnicodeDecodeError is a ValueError, not an OSError.
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8-sig")
    except OSError as exc:
        _die(f"cannot read {path}: {exc.strerror or exc}")
    except UnicodeDecodeError as exc:
        _die(f"{path} is not UTF-8: {exc.reason} at byte {exc.start}. "
             "Save it as UTF-8")
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
    report = check(_load(args.diagram), size=args.size, source=args.diagram,
                   physics=args.physics)
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


def do_page(args):
    """The diagram as a page: the same SVG inline, plus its controls."""
    diagram = _load(args.diagram)
    out = page(diagram, size=args.size or diagram.size, title=args.title,
               notation=args.notation)
    if args.out == "-":
        _soften(sys.stdout).write(out)
        return 0
    path = save(out, args.out or pathlib.Path(args.diagram).with_suffix(".html"))
    print(f"{path} ({len(out):,} bytes)")
    return 0


def do_render(args):
    diagram = _load(args.diagram)
    svg = render(layout(diagram), size=args.size or diagram.size,
                 notation=args.notation)
    svg = theme.bake(svg, args.mode) if args.mode else theme.with_variables(svg)

    # The same bytes to stdout as to a file. `save` is the library's one
    # writer and adds the declaration; stdout gets it too. They used to
    # differ, because this function typed the declaration out a second time.
    if args.out == "-":
        _soften(sys.stdout).write(DECLARATION + svg)
        return 0
    path = save(svg, args.out or pathlib.Path(args.diagram).with_suffix(".svg"))
    print(f"{path} ({len(svg):,} bytes)")
    return 0


def do_solve(args):
    """The same diagram with every node placed, as JSON to edit from.

    The workflow this exists for: write the network without coordinates,
    solve it, then move what the solver put somewhere you would not have.
    Everything the author set is kept; only the `at` that were missing are
    added, and the `via` a parallel pair needed.
    """
    diagram = _load(args.diagram)
    out = solve(diagram).to_json() + "\n"
    if args.out == "-":
        _soften(sys.stdout).write(out)
        return 0
    path = save(out, args.out or pathlib.Path(args.diagram).with_name(
        pathlib.Path(args.diagram).stem + ".solved.json"))
    print(f"{path} ({len(out):,} bytes)")
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
    c.add_argument("--physics", action="store_true",
                   help="also ask whether the stated numbers close at each "
                        "node")
    size(c)
    c.set_defaults(fn=do_check)

    d = subs.add_parser("describe", help="say what the drawing contains")
    d.add_argument("diagram")
    d.add_argument("--json", action="store_true", help="machine-readable")
    size(d)
    d.set_defaults(fn=do_describe)

    g = subs.add_parser("page", help="write the diagram as an HTML page")
    g.add_argument("diagram")
    g.add_argument("-o", "--out", help='output path, or "-" for stdout')
    g.add_argument("--title", help="heading for the page")
    g.add_argument("--notation", choices=["boxes", "zigzags"],
                   default="boxes",
                   help="draw resistances as textured boxes (default) or "
                        "as circuit zigzags")
    size(g)
    g.set_defaults(fn=do_page)

    r = subs.add_parser("render", help="write the diagram as SVG")
    r.add_argument("diagram")
    r.add_argument("-o", "--out", help='output path, or "-" for stdout')
    r.add_argument("--mode", choices=["light", "dark"],
                   help="bake the palette, for Word, slides and rasterisers")
    r.add_argument("--notation", choices=["boxes", "zigzags"],
                   default="boxes",
                   help="draw resistances as textured boxes (default) or "
                        "as circuit zigzags")
    size(r)
    r.set_defaults(fn=do_render)

    s = subs.add_parser("solve", help="write the diagram back with every "
                                      "node placed, to edit from")
    s.add_argument("diagram")
    s.add_argument("-o", "--out", help='output path, or "-" for stdout')
    s.set_defaults(fn=do_solve)

    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except SystemExit:
        raise
    except DiagramError as exc:
        # A refusal from the solver comes out of `check`, `describe`,
        # `render` and `page`, after `_load` has accepted the file. It is
        # the library declining a diagram it does not place, which the
        # schema documents; the net below called it a bug in thermodraw,
        # in the same sentence as telling the reader what to type instead.
        _die(str(exc))
    except Exception as exc:                       # pragma: no cover - a net
        # Exit 1 means findings. An uncaught exception used to reach the
        # shell as 1 through Python's own handler, so a script gating on the
        # status read a crash as a diagram with warnings. Every known cause
        # is now refused by `validate`; this is the net under the unknown
        # ones, and it says 2 -- no answer -- which is what a crash is.
        _die(f"{type(exc).__name__}: {exc}. This is a bug in thermodraw; "
             "the diagram was accepted and then could not be drawn")


if __name__ == "__main__":
    raise SystemExit(main())
