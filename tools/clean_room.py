"""Build the clean room for a gallery run, reproducibly.

`examples/gallery/RERUN.md` says why a clean room has to exist and why it
cannot live inside this checkout: the harness reads `CLAUDE.md` from every
ancestor directory, so a room under this one is not clean. Run 2's room was
built by pasting a block of shell into a terminal, which is fine until the
next person wants to know exactly what the agents could see. This does the
same thing as a script, and then checks its own work.

    python tools/clean_room.py ../ThermoDraw-cleanroom-run3

What it removes is everything that shows an answer: the tests, the goldens,
the README images, the notation thumbnails, `tools/` (whose
`gen_dictionary.py` carries every symbol's meaning in prose), every finished
diagram, and the whole of run 2. What it leaves is the library, five briefs,
and `docs/schema.md`.

It also does one thing run 2's recipe did not. `docs/schema.md` quotes
`examples/hero.json` in full, along with its `describe` output, so every agent
in run 2 had a worked example after all and one found it actively misleading.
Here the worked example is replaced by a deliberately trivial one -- two
nodes, one path, one source, generated and measured by the archived library
itself, so the page still shows real output. That is a recorded deviation:
the agents read a schema no real user reads, which is the price of the
protocol being literally true.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

# Everything that would show an agent an answer.
REMOVE = [
    "CLAUDE.md", "README.md", "CHANGELOG.md", "Dictionary.html",
    "docs/design-record.md", "docs/symbol-reference.html",
    "docs/dictionary.template.html", "docs/symbol-reference.template.html",
    ".claude", ".github", "docs/assets", "docs/notation-test", "tests",
    "tools",
    "examples/hero.json", "examples/build_ladder.py",
    "examples/render_demo.py", "examples/render_reference.py",
    "examples/gallery/README.md", "examples/gallery/RERUN.md",
    "examples/gallery/FINDINGS.md", "examples/gallery/FINDINGS-first-run.md",
    "examples/gallery/01-spacecraft", "examples/gallery/02-building",
    "examples/gallery/03-cryogenic", "examples/gallery/04-immersion",
    "examples/gallery/05-laser-diode",
    "examples/gallery/run-3",
]

# The trivial diagram that replaces the hero in the room's schema. Its own
# numbers close -- 65 K over 0.5 K/W is 130 W -- so the page cannot teach a
# reader that a worked example is allowed not to.
STUB = {
    "units": {"R": "K/W", "T": "°C", "P": "W"},
    "nodes": [
        {"id": "a", "label": "Body", "sub": "a", "value": "90",
         "at": [200, 150]},
        {"id": "amb", "kind": "fixed", "label": "Still air", "sub": "amb",
         "value": "25", "at": [520, 150]},
    ],
    "branches": [
        {"from": "a", "to": "amb", "kind": "cond", "label": "Mounting foot",
         "value": "0.5"},
    ],
    "sources": [
        {"to": "a", "kind": "diss", "label": "Dissipation", "value": "130",
         "sub": "d", "at": [60, 150]},
    ],
}

# (what to find, what to put there). Each must match exactly once, or the
# schema has moved and this script is out of date -- which is the failure
# worth having, rather than a room that quietly still names the hero.
EDITS = [
    ("the hero's `\"angle\": 90` on its ambient node sends that label out to "
     "the\nright rather than straight up, where the branch arriving from the "
     "left would\nhave crowded it.",
     "an `\"angle\": 90` on an ambient node sends that label out to the\n"
     "right rather than straight up, where a branch arriving from the left "
     "would\nhave crowded it."),

    ("A `fixed` node may sit anywhere. The hero puts its ambient node at the "
     "rail's\nown `y` because that is where the diagram's cold end belongs, "
     "not because the\ntwo are connected",
     "A `fixed` node may sit anywhere. Putting an ambient node at the rail's\n"
     "own `y` is where a diagram's cold end belongs, and not a sign that the\n"
     "two are connected"),

    ("  the node it names. The hero turns at `x = 696` for a node at "
     "`x = 648`.\n  Give the turn 40–90 units of clearance. The same is "
     "true of the end a\n  branch *arrives* at: the hero's parallel pair "
     "drops straight down onto its\n  ambient node and gets away with it "
     "only because that node has `angle: 90`\n  and no other traffic. A node "
     "with three branches and a source on it does\n  not, and one reader "
     "traced four findings to copying the hero's arrival.",
     "  the node it names. Turning at `x = 696` for a node at `x = 648` is "
     "about\n  right: give the turn 40–90 units of clearance. The same "
     "is true of the\n  end a branch *arrives* at. A parallel pair dropping "
     "straight down onto a\n  node gets away with it only where that node "
     "has `angle: 90` and no other\n  traffic; a node with three branches "
     "and a source on it does not, and one\n  reader traced four findings to "
     "arriving that way."),

    ("- `parallel-pair-same-side` is a note rather than a warning because the "
     "hero\n  diagram breaks it and is fine.",
     "- `parallel-pair-same-side` is a note rather than a warning because a\n"
     "  well-drawn diagram can break it and be fine."),

    ("When it was written every diagram in this repository fired it, the\n"
     "hero included — its temperatures were not the results of its own "
     "power and\nresistances, and now are. The gallery is left as its agents "
     "drew it.",
     "When it was written every diagram in this repository fired it: their\n"
     "temperatures were not the results of their own power and resistances."),

    ("That file is `examples/hero.json`, and it renders the diagram at the "
     "top of\nthe README.",
     "That is a whole file. Two nodes, one path, one source, and numbers "
     "that\nclose: 65 K over 0.5 K/W is the 130 W the source puts in."),

    ("That is the real output for `examples/hero.json`, not an abridgement.",
     "That is the real output for the file above, not an abridgement."),

    ("`label-collision`. Above, `branch 2` and `branch 3` both went "
     "\"above\", which\nis the parallel pair `check` notes, visible directly "
     "rather than only graded.",
     "`label-collision`. Two branches between one pair of nodes both going\n"
     "\"above\" is the parallel pair `check` notes, visible directly rather "
     "than\nonly graded."),
]


def git(args, cwd, capture=True):
    return subprocess.run(["git"] + args, cwd=str(cwd), check=True, text=True,
                          capture_output=capture)


def room_env():
    """Enough environment to run the archived library, and no more.

    `SYSTEMDRIVE` and the profile variables are on the list because leaving
    them off does not fail loudly: Windows falls back to expanding
    `%SystemDrive%` as a literal directory name, and the first run of this
    script grew a `%SystemDrive%/ProgramData/...` tree inside the room.

    `PYTHONDONTWRITEBYTECODE` keeps `__pycache__` out of it. The room's
    `.gitignore` would stop those being committed, but the room is also read
    by eye, and a directory nobody put there invites the question.
    """
    keep = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC",
            "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA",
            "PROGRAMDATA", "HOME")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env["PYTHONPATH"] = "src"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def main(argv=None):
    ap = argparse.ArgumentParser(description="build a gallery clean room")
    ap.add_argument("target", help="the room, a SIBLING of this checkout")
    ap.add_argument("--ref", default="HEAD", help="commit to archive")
    args = ap.parse_args(argv)

    root = pathlib.Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], check=True, text=True,
        capture_output=True).stdout.strip())
    target = pathlib.Path(args.target).resolve()
    if root == target or root in target.parents:
        sys.exit(f"error: {target} is inside the checkout, so it is not a "
                 "clean room. RERUN.md says why: the harness reads CLAUDE.md "
                 "from every ancestor directory.")
    if target.exists():
        sys.exit(f"error: {target} already exists; move it aside first")
    if git(["status", "--porcelain"], root).stdout.strip():
        sys.exit("error: the working tree is dirty. The room has to be a "
                 "named commit, or the run cannot be reproduced.")

    sha = git(["rev-parse", "--short", args.ref], root).stdout.strip()
    target.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", args.ref], cwd=str(root),
                             check=True, stdout=subprocess.PIPE).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)

    for name in REMOVE:
        path = target / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    strip_hero(target)
    briefs = sorted(target.glob("examples/gallery/*/brief.md"))
    write_start_here(target, briefs, sha)

    git(["init", "-q"], target)
    git(["add", "-A"], target)
    git(["-c", "user.name=clean room", "-c", "user.email=clean@room.invalid",
         "commit", "-qm", "clean room, from " + sha], target)
    verify(target, briefs)
    print("clean room at {}, from {}, {} briefs".format(
        target, sha, len(briefs)))


def swap_block(text, after, new):
    """Replace the first fenced block following `after`."""
    start = text.index(after)
    open_fence = text.index("```", start)
    close_fence = text.index("\n```", open_fence + 3)
    return text[:open_fence] + new + text[close_fence + len("\n```"):]


def strip_hero(target):
    """Replace the worked example, and every sentence that names it."""
    schema = target / "docs" / "schema.md"
    text = schema.read_text(encoding="utf-8")

    stub = target / "_stub.json"
    stub.write_text(json.dumps(STUB, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    described = subprocess.run(
        [sys.executable, "-m", "thermodraw", "describe", "_stub.json"],
        cwd=str(target), env=room_env(), text=True, capture_output=True,
        check=True).stdout.replace("_stub.json:", "diagram.json:")
    stub.unlink()

    body = json.dumps(STUB, indent=2, ensure_ascii=False)
    text = swap_block(text, "## A whole diagram", "```jsonc\n" + body + "\n```")
    text = swap_block(text, "thermodraw describe diagram.json",
                      "```\n" + described.rstrip() + "\n```")

    for find, put in EDITS:
        if text.count(find) != 1:
            sys.exit("error: schema.md has moved; this passage matched {} "
                     "times, not once:\n\n{}...".format(
                         text.count(find), find[:120]))
        text = text.replace(find, put)
    if "hero" in text:
        sys.exit("error: schema.md still says 'hero' after the edits")
    schema.write_text(text, encoding="utf-8")


def write_start_here(target, briefs, sha):
    lines = "\n".join(
        "  Read {} and do exactly what it says.".format(
            b.relative_to(target).as_posix())
        for b in briefs)
    (target / "START-HERE.txt").write_text(
        "Clean room for gallery run 3, from commit {}.\n\n"
        "Start a NEW session in THIS directory for each brief, and give it\n"
        "one line:\n\n{}\n\n"
        "Then, still in that session:\n\n"
        "  Save the whole transcript of this session as\n"
        "  <that folder>/transcript.md, put the model and harness on the\n"
        "  first line of rounds.md, run `PYTHONPATH=src "
        "PYTHONIOENCODING=utf-8\n"
        "  python -m thermodraw check --physics` on the final diagram and\n"
        "  paste its output at the end of rounds.md, and commit everything\n"
        "  under that folder as one commit.\n\n"
        "When all five are done, copy examples/gallery/*/ back into the main\n"
        "repo on a branch, and read RERUN.md's pre-registered outcomes for\n"
        "run 3 BEFORE reading any findings.\n".format(sha, lines),
        encoding="utf-8")


def verify(target, briefs):
    """The room is only worth running if it is actually clean."""
    problems = []
    for forbidden in ("CLAUDE.md", ".claude", "tests", "tools",
                      "docs/design-record.md", "examples/hero.json"):
        if (target / forbidden).exists():
            problems.append(forbidden + " survived")
    if len(briefs) != 5:
        problems.append("{} briefs, expected 5".format(len(briefs)))
    leftover = sorted(p.as_posix() for p in (target / "examples").rglob("*.json"))
    if leftover:
        problems.append("finished diagrams left: " + ", ".join(leftover))
    if "hero" in (target / "docs" / "schema.md").read_text(encoding="utf-8"):
        problems.append("schema.md still names the hero")
    # Anything else at the top level was put there by accident, and the
    # accident worth catching is a subprocess writing into the room.
    expected = {".git", ".gitattributes", ".gitignore", "LICENSE", "NOTICE",
                "START-HERE.txt", "docs", "examples", "pyproject.toml", "src"}
    strays = sorted(p.name for p in target.iterdir() if p.name not in expected)
    if strays:
        problems.append("unexpected at the top level: " + ", ".join(strays))
    got = subprocess.run([sys.executable, "-m", "thermodraw", "check", "--help"],
                         cwd=str(target), env=room_env(), capture_output=True)
    if got.returncode != 0:
        problems.append("the checker does not run in the room")
    if problems:
        sys.exit("error: the room is not clean:\n  " + "\n  ".join(problems))


if __name__ == "__main__":
    main()
