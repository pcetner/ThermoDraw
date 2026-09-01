"""The command line, which is the whole point of the checker being reachable.

Exit status is the interface here. A CI step, a Makefile or a model driving
the library reads the number, not the prose, so the number is what these pin.
"""
import json
import pathlib

import pytest

from thermodraw.__main__ import main

ROOT = pathlib.Path(__file__).resolve().parents[1]
HERO = ROOT / "examples" / "hero.json"
ADRIFT = ROOT / "tests" / "data" / "adrift.json"


def run(capsys, *argv):
    """main(argv), returning (exit code, stdout)."""
    try:
        code = main(list(argv))
    except SystemExit as exit_:
        code = exit_.code
    return code, capsys.readouterr().out


class TestCheck:
    def test_a_clean_diagram_exits_zero(self, capsys):
        code, out = run(capsys, "check", str(HERO))
        assert code == 0
        assert "0 errors, 0 warnings" in out

    def test_findings_exit_one_and_name_the_element(self, capsys):
        code, out = run(capsys, "check", str(ADRIFT))
        assert code == 1
        assert "label-adrift" in out and "node 'h'" in out

    def test_strict_promotes_a_note_into_a_failure(self, capsys):
        assert run(capsys, "check", str(HERO))[0] == 0
        code, out = run(capsys, "check", str(HERO), "--strict")
        assert code == 1
        assert "warning: [parallel-pair-same-side]" in out

    def test_quiet_drops_the_summary_but_keeps_the_findings(self, capsys):
        """A note still prints: `ok` and "nothing to report" differ."""
        code, out = run(capsys, "check", str(HERO), "--quiet")
        assert code == 0
        assert out.splitlines() == [l for l in out.splitlines()
                                    if l.startswith("note:")]

    def test_quiet_is_silent_when_there_is_nothing_at_all(self, capsys,
                                                          tmp_path):
        path = tmp_path / "plain.json"
        path.write_text(json.dumps({
            "units": {"R": "K/W", "T": "C"},
            "nodes": [{"id": "a", "label": "Hot", "value": "100",
                       "at": [0, 0]},
                      {"id": "b", "label": "Cold", "value": "20",
                       "at": [300, 0]}],
            "branches": [{"from": "a", "to": "b", "kind": "cond",
                          "label": "Slab", "value": "0.3"}]}),
            encoding="utf-8")
        code, out = run(capsys, "check", str(path), "--quiet")
        assert code == 0 and out.strip() == ""

    def test_json_is_machine_readable(self, capsys):
        code, out = run(capsys, "check", str(ADRIFT), "--json")
        data = json.loads(out)
        assert code == 1 and data["ok"] is False
        assert "label-adrift" in {f["code"] for f in data["findings"]}

    def test_a_size_that_clips_is_reported(self, capsys):
        code, out = run(capsys, "check", str(HERO), "--size", "200", "200")
        assert code == 1 and "off-canvas" in out


class TestDescribe:
    """It reports; it does not judge, so it exits 0 whatever it finds."""

    def test_it_says_what_is_on_the_page(self, capsys):
        code, out = run(capsys, "describe", str(HERO))
        assert code == 0
        assert "canvas 1042 x 431, 11 labels" in out
        assert "symbol/cap x2" in out and "node 'amb'" in out

    def test_a_diagram_with_findings_still_exits_zero(self, capsys):
        """`check` is what grades. Two exit codes for two questions."""
        assert run(capsys, "check", str(ADRIFT))[0] == 1
        assert run(capsys, "describe", str(ADRIFT))[0] == 0

    def test_json_is_machine_readable(self, capsys):
        code, out = run(capsys, "describe", str(HERO), "--json")
        data = json.loads(out)
        assert code == 0 and data["canvas"] == [1041.7, 430.8]
        assert data["counts"]["node"] == 4

    def test_a_missing_file_is_still_exit_two(self, capsys):
        assert run(capsys, "describe", "no-such-file.json")[0] == 2


class TestRender:
    def test_it_writes_an_svg(self, capsys, tmp_path):
        out_file = tmp_path / "hero.svg"
        code, _ = run(capsys, "render", str(HERO), "-o", str(out_file))
        assert code == 0
        text = out_file.read_text(encoding="utf-8")
        assert text.startswith("<?xml") and "<svg" in text

    def test_mode_bakes_the_palette(self, capsys, tmp_path):
        plain, baked = tmp_path / "a.svg", tmp_path / "b.svg"
        run(capsys, "render", str(HERO), "-o", str(plain))
        run(capsys, "render", str(HERO), "-o", str(baked), "--mode", "light")
        assert "var(--" in plain.read_text(encoding="utf-8")
        assert "var(--" not in baked.read_text(encoding="utf-8")

    def test_dash_writes_the_same_bytes_to_stdout_as_to_a_file(
            self, capsys, tmp_path):
        """One writer. `-o -` used to leave out the XML declaration that the
        file got, because the file path typed the declaration out by hand."""
        out_file = tmp_path / "hero.svg"
        run(capsys, "render", str(HERO), "-o", str(out_file))
        code, out = run(capsys, "render", str(HERO), "-o", "-")
        assert code == 0
        assert out == out_file.read_text(encoding="utf-8")


class TestBadInput:
    """Exit 2 is neither "clean" nor "findings" — it is "no answer"."""

    def test_a_missing_file(self, capsys):
        assert run(capsys, "check", "no-such-file.json")[0] == 2

    def test_a_file_that_is_not_utf8(self, capsys, tmp_path):
        """UnicodeDecodeError is a ValueError, not an OSError, so a cp1252
        diagram used to escape as a traceback with exit 1 — the code that
        means "findings". Exactly the failure io.py's docstring is about,
        unhandled on the read side."""
        bad = tmp_path / "latin.json"
        bad.write_bytes('{"units": {"T": "°C"}, "nodes": []}'.encode("cp1252"))
        # `run` keeps stdout only; the reason lands on stderr, so read it here.
        with pytest.raises(SystemExit) as exit_:
            main(["check", str(bad)])
        assert exit_.value.code == 2
        assert "not UTF-8" in capsys.readouterr().err

    def test_a_bom_is_not_an_error(self, capsys, tmp_path):
        """PowerShell's Out-File writes one, and the file is no less UTF-8."""
        good = tmp_path / "bom.json"
        good.write_bytes(b"\xef\xbb\xbf" + HERO.read_bytes())
        assert run(capsys, "check", str(good))[0] != 2

    def test_something_that_is_not_json(self, capsys, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json at all", encoding="utf-8")
        assert run(capsys, "check", str(path))[0] == 2

    def test_json_that_is_not_a_diagram(self, capsys, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"nodes": [{"id": "a", "at": [0, 0],'
                        ' "kind": "nonsense"}]}', encoding="utf-8")
        code = run(capsys, "check", str(path))[0]
        assert code == 2

    def test_no_subcommand_is_a_usage_error(self, capsys):
        with pytest.raises(SystemExit) as exit_:
            main([])
        assert exit_.value.code == 2
