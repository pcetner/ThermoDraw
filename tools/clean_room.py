"""Build the clean room for a gallery run, reproducibly.

`examples/gallery/RERUN.md` says why a clean room has to exist and why it
cannot live inside this checkout: the harness reads `CLAUDE.md` from every
ancestor directory, so a room under this one is not clean. Run 2's room was
built by pasting a block of shell into a terminal, which is fine until the
next person wants to know exactly what the agents could see. This does the
same thing as a script, and then checks its own work.

    python tools/clean_room.py ../room --profile gallery --briefs 06-battery ...
    python tools/clean_room.py ../room --profile review

There are two rooms, because there are two questions and they want opposite
things kept.

**`gallery`** asks whether the vocabulary is sufficient and the schema is
enough to draw from. It removes everything that shows an answer: the tests,
the goldens, the README images, the notation thumbnails, `tools/` (whose
`gen_dictionary.py` carries every symbol's meaning in prose), and every
finished diagram. What it leaves is the library, the named briefs, and
`docs/schema.md`.

**`review`** asks whether the code is any good, and wants the opposite: the
tests and `tools/` are the point, and what goes is everything that argues.
`CLAUDE.md` states forty-odd decisions as settled, `docs/design-record.md`
argues each one for seven hundred lines, the changelog narrates why every
change was made, and the three `FINDINGS` files are prior reviews with their
conclusions attached. A reader who has absorbed those grades the code against
its own stated intentions instead of independently. `git archive` throws away
the sixty-seven commit messages for free, which is the largest single piece
of it.

One residue is deliberate and disclosed rather than removed:
`tests/test_clean_room.py` narrates past findings in its docstrings, because
that is what the guards are for. A review that cannot see the tests is worse
than one that reads why a guard exists.

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
import re
import shutil
import subprocess
import sys

# Everything that would show a gallery agent an answer.
GALLERY_REMOVE = [
    "CLAUDE.md", "README.md", "CHANGELOG.md", "Dictionary.html",
    "docs/design-record.md", "docs/symbol-reference.html",
    "docs/dictionary.template.html", "docs/symbol-reference.template.html",
    ".claude", ".github", "docs/assets", "docs/notation-test", "tests",
    "tools",
    "examples/hero.json", "examples/build_ladder.py",
    "examples/render_demo.py", "examples/render_reference.py",
    "examples/gallery/README.md", "examples/gallery/RERUN.md",
    "examples/gallery/FINDINGS.md", "examples/gallery/FINDINGS-first-run.md",
    "examples/gallery/FINDINGS-run-3.md",
    "examples/gallery/run-3",
]

# Everything that argues, concludes, or narrates. The code, the tests, the
# generated pages and the CI definition all stay: they are the subject.
REVIEW_REMOVE = [
    "CLAUDE.md", "CHANGELOG.md", ".claude",
    "docs/design-record.md",
    # The notation thumbnails exist to settle a bet, and their README argues
    # for one side of it.
    "docs/notation-test",
    "examples/gallery/README.md", "examples/gallery/RERUN.md",
    "examples/gallery/FINDINGS.md", "examples/gallery/FINDINGS-first-run.md",
    "examples/gallery/FINDINGS-run-3.md",
    "examples/gallery/run-3",
]

# Everything a gallery folder keeps. Naming the folders of *past* runs
# instead was wrong within one run of being written: run 3's five diagrams
# landed in the repository, the list still spoke of run 2's, and the next
# room would have handed five finished answers to five agents told there
# were none. The builder's own check caught it, which is the argument for
# having one.
KEEP_IN_A_GALLERY_FOLDER = {"brief.md"}


def _gallery_keeps_brief(name):
    return name == "brief.md"


def _review_keeps_the_drawing(name):
    """A reviewer keeps the diagrams and loses the write-ups.

    The JSON and the SVG are input and output -- real data to run the
    checker over. `findings.md`, `rounds.md` and `transcript.md` are five
    agents' opinions of this library, which is the most anchoring material
    in the repository. `brief.md` goes too: it tells the reader the library
    is being tested and exactly which of its claims are under test.
    """
    return name.endswith(".json") or name.endswith(".svg")


PROFILES = {
    "gallery": {
        "remove": GALLERY_REMOVE,
        "keeps": _gallery_keeps_brief,
        "needs_briefs": True,
        "strip_schema": True,
        "forbidden": ("CLAUDE.md", ".claude", "tests", "tools",
                      "docs/design-record.md", "examples/hero.json"),
        "wanted": (),
    },
    "review": {
        "remove": REVIEW_REMOVE,
        "keeps": _review_keeps_the_drawing,
        "needs_briefs": False,
        "strip_schema": False,
        "forbidden": ("CLAUDE.md", ".claude", "CHANGELOG.md",
                      "docs/design-record.md", "docs/notation-test",
                      "examples/gallery/FINDINGS.md",
                      "examples/gallery/FINDINGS-run-3.md",
                      "examples/gallery/RERUN.md"),
        # A review of a library with no tests in front of it is not a review
        # of this library.
        "wanted": ("src/thermodraw", "tests", "tools", "pyproject.toml",
                   "README.md", "docs/schema.md"),
    },
}

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

# The same file, set the way the schema sets its examples: one element to a
# line, aligned. `json.dumps` explodes every list onto its own lines, which
# reads nothing like the rest of the page. Checked against STUB at build time,
# so the two cannot drift.
STUB_JSON = """{
  "units": {"R": "K/W", "T": "°C", "P": "W"},
  "nodes": [
    {"id": "a",   "label": "Body",      "sub": "a",   "value": "90", "at": [200, 150]},
    {"id": "amb", "kind": "fixed", "label": "Still air", "sub": "amb",
     "value": "25", "at": [520, 150]}
  ],
  "branches": [
    {"from": "a", "to": "amb", "kind": "cond", "label": "Mounting foot",
     "value": "0.5"}
  ],
  "sources": [
    {"to": "a", "kind": "diss", "label": "Dissipation", "value": "130",
     "sub": "d", "at": [60, 150]}
  ]
}"""

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

    ("A power device losing heat to still air by two parallel paths, with "
     "the die\nand sink thermal masses on the rail:",
     "A body losing heat to still air by one path, with the dissipation "
     "that\nputs it there:"),

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
    ap = argparse.ArgumentParser(description="build a clean room")
    ap.add_argument("target", help="the room, a SIBLING of this checkout")
    ap.add_argument("--ref", default="HEAD", help="commit to archive")
    ap.add_argument("--profile", choices=sorted(PROFILES), default="gallery",
                    help="gallery: can it be drawn? review: is it any good?")
    # Which briefs are in this run is a decision, not something to infer from
    # what happens to be on disk. Naming them also puts the run's membership
    # in the shell history and in START-HERE.txt.
    ap.add_argument("--briefs", nargs="+", metavar="FOLDER",
                    help="gallery folders this run uses, e.g. 06-battery")
    args = ap.parse_args(argv)
    profile = PROFILES[args.profile]
    if profile["needs_briefs"] and not args.briefs:
        ap.error("--briefs is required for the gallery profile")
    if not profile["needs_briefs"] and args.briefs:
        ap.error("--briefs means nothing to the {} profile".format(
            args.profile))

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

    for name in profile["remove"]:
        path = target / name
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()

    gallery = target / "examples" / "gallery"
    wanted = set(args.briefs or ())
    if wanted:
        missing = sorted(w for w in wanted
                         if not (gallery / w / "brief.md").is_file())
        if missing:
            sys.exit("error: no brief for " + ", ".join(missing))
    keeps = profile["keeps"]
    for folder in sorted(p for p in gallery.iterdir() if p.is_dir()):
        if wanted and folder.name not in wanted:
            shutil.rmtree(folder)
            continue
        for item in sorted(folder.iterdir()):
            if keeps(item.name):
                continue
            shutil.rmtree(item) if item.is_dir() else item.unlink()

    if profile["strip_schema"]:
        strip_hero(target)
    briefs = sorted(target.glob("examples/gallery/*/brief.md"))
    write_start_here(target, briefs, sha, args.profile)

    git(["init", "-q"], target)
    git(["add", "-A"], target)
    git(["-c", "user.name=clean room", "-c", "user.email=clean@room.invalid",
         "commit", "-qm", "clean room, from " + sha], target)
    verify(target, briefs, len(wanted), profile)
    tail = ("{} briefs".format(len(briefs)) if profile["needs_briefs"]
            else "for review")
    print("clean room at {}, from {}, {}".format(target, sha, tail))


def swap_block(text, after, new, skip=0):
    """Replace a fenced block following `after`, skipping `skip` fences.

    `skip` exists because the anchor is sometimes *inside* a block: the
    describe example is introduced by a ```bash fence holding the command,
    so the first fence after that anchor is the bash block's closing one and
    the block wanted is the next. Getting this wrong does not raise -- it
    quietly replaces the wrong span and leaves the original example in place,
    which is exactly what the first build did.
    """
    i = text.index(after)
    for _ in range(skip + 1):
        open_fence = text.index("```", i)
        i = open_fence + 3
    close_fence = text.index("\n```", i)
    return text[:open_fence] + new + text[close_fence + len("\n```"):]


def strip_hero(target):
    """Replace the worked example, and every sentence that names it."""
    schema = target / "docs" / "schema.md"
    text = schema.read_text(encoding="utf-8")

    if json.loads(STUB_JSON) != STUB:
        sys.exit("error: STUB_JSON and STUB have drifted apart")
    stub = target / "_stub.json"
    stub.write_text(STUB_JSON, encoding="utf-8")
    # `encoding` explicitly: PYTHONIOENCODING settles what the child writes,
    # and this settles what the parent reads. Without it a Windows parent
    # decodes as cp1252 and every degree sign in the page becomes "Â°".
    described = subprocess.run(
        [sys.executable, "-m", "thermodraw", "describe", "_stub.json"],
        cwd=str(target), env=room_env(), capture_output=True, check=True,
        encoding="utf-8").stdout.replace("_stub.json:", "diagram.json:")
    stub.unlink()

    text = swap_block(text, "## A whole diagram",
                      "```jsonc\n" + STUB_JSON + "\n```")
    text = swap_block(text, "thermodraw describe diagram.json",
                      "```\n" + described.rstrip() + "\n```", skip=1)

    for find, put in EDITS:
        if text.count(find) != 1:
            sys.exit("error: schema.md has moved; this passage matched {} "
                     "times, not once:\n\n{}...".format(
                         text.count(find), find[:120]))
        text = text.replace(find, put)
    if "hero" in text:
        sys.exit("error: schema.md still says 'hero' after the edits")
    schema.write_text(text, encoding="utf-8")


REVIEW_START_HERE = """Clean room for a blind code review, from commit {sha}.

You are the first reader. Nothing here tells you what the author thinks: the
decisions file, the design record, the changelog and every previous review
have been removed, and the archive carries no commit history, so sixty-seven
commit messages of reasoning are gone with it. What is left is the code, its
tests, its tools, the README and the format documentation.

Start ONE session in THIS directory and give it this:

  Review this library as if you were considering depending on it. Read the
  code and the tests. Report what you find, worst first, with a file and a
  line for each. Say what you would not depend on, and why. Do not fix
  anything.

Two things worth knowing before you start.

  Run the suite with `python -m pip install -e ".[dev]"` and then
  `python -m pytest -q`. The library itself has no runtime dependencies.

  `tests/test_clean_room.py` narrates findings from earlier reviews in its
  docstrings. That is deliberate, and it is the one piece of prior opinion
  left in the room: the guards do not make sense without it, and a review
  that cannot see the tests is worse than one that reads why a guard exists.
  Treat it as evidence about the past, not as a verdict on the present.

{dangling}Write the review to REVIEW.md in this directory and commit it. Then copy
that one file back to the main repository, and nothing else: the room is a
snapshot, and its tree is not the branch you are reviewing.
"""



def dangling(target):
    """README links to files this room removed.

    Worth naming rather than leaving to be found. A reviewer who follows
    `docs/design-record.md` and finds nothing has discovered a property of
    the room, not of the library, and reporting it is wasted effort in both
    directions. Computed rather than written down, so it stays true as the
    removal list changes.
    """
    readme = target / "README.md"
    if not readme.is_file():
        return []
    links = re.findall(r"\]\(([^)]+)\)", readme.read_text(encoding="utf-8"))
    return sorted({link for link in links
                   if not link.startswith(("http", "#"))
                   and not (target / link).exists()})


def write_start_here(target, briefs, sha, profile):
    if profile == "review":
        gone = dangling(target)
        note = ""
        if gone:
            nl = chr(10)
            note = ("  The README links these, and this room removed"
                    " them. A dead link" + nl
                    + "  here is a property of the room, not of the"
                    " library:" + nl + nl
                    + "".join("    " + g + nl for g in gone) + nl)
        (target / "START-HERE.txt").write_text(
            REVIEW_START_HERE.format(sha=sha, dangling=note), encoding="utf-8")
        return
    lines = "\n".join(
        "  Read {} and do exactly what it says.".format(
            b.relative_to(target).as_posix())
        for b in briefs)
    (target / "START-HERE.txt").write_text(
        "Clean room for a gallery run, from commit {}.\n\n"
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
        "When all are done, copy examples/gallery/*/ back into the main\n"
        "repo on a branch, and read RERUN.md's pre-registered outcomes for\n"
        "this run BEFORE reading any findings.\n".format(sha, lines),
        encoding="utf-8")


def verify(target, briefs, expected, profile):
    """The room is only worth running if it is actually clean."""
    problems = []
    for forbidden in profile["forbidden"]:
        if (target / forbidden).exists():
            problems.append(forbidden + " survived")
    # A review room can fail the other way round, by removing the thing
    # under review. Nothing checked that until the review profile existed.
    for needed in profile["wanted"]:
        if not (target / needed).exists():
            problems.append(needed + " is missing, and is the subject")
    if profile["needs_briefs"] and len(briefs) != expected:
        problems.append("{} briefs, expected {}".format(len(briefs), expected))
    # Gallery-only: a review room keeps the gallery diagrams as data
    # to run the checker over, and reads the schema as it ships,
    # hero and all.
    if profile["strip_schema"]:
        leftover = sorted(p.as_posix() for p in (target / "examples").rglob("*.json"))
        if leftover:
            problems.append("finished diagrams left: " + ", ".join(leftover))
        schema = (target / "docs" / "schema.md").read_text(encoding="utf-8")
        if "hero" in schema:
            problems.append("schema.md still names the hero")
        # Naming it is one leak; showing it is the other. A bad fence swap
        # replaced the wrong span once and left the whole worked example behind.
        # Markers that appear *only* inside the two replaced blocks. "Die attach"
        # and "Switching loss" are not on the list: they are also the one-line
        # snippets that introduce Branches and Sources, which every schema needs
        # and which show one element rather than a diagram to copy.
        for shown in ("j --cond-- c", "canvas 1042 x 431", "Sink base"):
            if shown in schema:
                problems.append("schema.md still shows the hero: " + shown)
        if "Â" in schema:
            problems.append("schema.md has mojibake: something was decoded twice")
    # Anything else at the top level was put there by accident, and the
    # accident worth catching is a subprocess writing into the room.
    expected = {".git", ".gitattributes", ".gitignore", "LICENSE",
                "NOTICE", "START-HERE.txt", "docs", "examples",
                "pyproject.toml", "src"}
    if not profile["strip_schema"]:
        # A review reads the CI definition, the generated pages and the
        # public README; only the arguing is gone.
        expected |= {".github", "Dictionary.html", "README.md", "tests",
                     "tools"}
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
