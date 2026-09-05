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
    # ...and then makes the GitHub Release from the changelog's section
    assert "tools/release_notes.py" in text
    assert "gh release create" in text
    assert "contents: write" in text


class TestTheReleaseNotesAreTheChangelogsSection:
    @staticmethod
    def tool():
        import importlib
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        return importlib.import_module("release_notes")

    def test_this_versions_section_comes_back_whole(self):
        notes = self.tool().section(
            thermodraw.__version__,
            (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
        assert notes.startswith("The first release whose promises")
        assert "### Added" in notes and "### Removed" in notes
        assert "## [" not in notes, "ran into the next version's section"

    def test_a_version_with_no_section_is_refused_by_name(self, capsys):
        assert self.tool().main(["9.9.9"]) == 1
        assert "9.9.9" in capsys.readouterr().err

    def test_the_text_between_two_headings_is_exact(self):
        text = "## [Unreleased]\n\nnothing\n\n## [1.2.3] - 2026-01-01\n\nbody\n\n### Fixed\n\n- x\n\n## [1.0.0] - 2025-01-01\n\nold\n"
        assert self.tool().section("1.2.3", text) == "body\n\n### Fixed\n\n- x\n"
        assert self.tool().section("1.0.0", text) == "old\n"
