"""The version is written in two places, and a release is cut from a tag.

`pyproject.toml` is what PyPI reads and `thermodraw.__version__` is what a
program reads, and nothing tied them: the generated pages bake whichever
one they import. The release workflow refuses a tag that does not match
the package, and this refuses a package that does not match itself or has
no changelog entry.
"""
import pathlib
import re

import thermodraw

ROOT = pathlib.Path(__file__).resolve().parents[1]


def pyproject_version():
    # 3.10 has no tomllib, and the file is ours: one line, one shape.
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"$', text, re.M).group(1)


def test_the_package_and_the_metadata_agree():
    assert thermodraw.__version__ == pyproject_version()


def test_the_version_has_a_changelog_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{thermodraw.__version__}] - " in text


def test_the_generated_pages_carry_this_version():
    for page in ("Dictionary.html", "docs/symbol-reference.html"):
        text = (ROOT / page).read_text(encoding="utf-8")
        assert f"ThermoDraw {thermodraw.__version__}<" in text, page


def test_the_release_workflow_guards_the_tag():
    text = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8")
    assert "thermodraw.__version__" in text
    assert "pypa/gh-action-pypi-publish" in text
    assert "id-token: write" in text
