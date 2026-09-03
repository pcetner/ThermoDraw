"""The numbers on the page, asked whether they agree with each other.

Behind `check(physics=True)`, opt-in by choice. These pin what it must do:
fire on a node whose stated values do not close, stay quiet on one whose
values do, fold `count` the way the schema says a count folds, and say what
it could not know rather than skip it silently.
"""
import pytest

from thermodraw import DiagramBuilder, check
from thermodraw.__main__ import main


def codes(report):
    return [f.code for f in report.findings]


def ladder(t_b="40", **branch):
    """10 W into `a`, one resistance of 1 K/W to a fixed `b`."""
    return (DiagramBuilder(R="K/W", T="°C", P="W")
            .node("a", "Hot", "50", at=(0, 0), sub="a")
            .node("b", "Cold", t_b, kind="fixed", at=(300, 0), sub="b")
            .branch("a", "b", "cond", "Slab", branch.pop("value", "1.0"),
                    **branch)
            .source("a", "diss", "Load", "10", sub="d"))


class TestKirchhoffAtANode:
    def test_a_node_whose_numbers_close_is_quiet(self):
        assert "node-does-not-balance" not in codes(check(ladder(), physics=True))

    def test_a_node_whose_numbers_do_not_close_is_reported(self):
        """10 W in, and a 20 K drop over 1 K/W says 20 W out."""
        found = [f for f in check(ladder("30"), physics=True).findings
                 if f.code == "node-does-not-balance"]
        assert len(found) == 1
        assert found[0].where == "node 'a'"
        assert "10 W arrives" in found[0].message
        assert "20 W leaves" in found[0].message
        assert "`count`" in found[0].remedy

    def test_it_is_off_unless_asked(self):
        assert "node-does-not-balance" not in codes(check(ladder("30")))

    def test_a_count_folds_the_group_the_way_the_schema_says(self):
        """`value` is per item. Eight 8 K/W paths in parallel are 1 K/W, so
        the drawing that says so balances and the one that leaves `count`
        off — a box captioned "each of 8" with no field behind it — does not.
        That was the rack diagram in the first gallery run."""
        assert "node-does-not-balance" not in codes(
            check(ladder(value="8.0", count=8, arrangement="parallel"),
                  physics=True))
        assert "node-does-not-balance" in codes(
            check(ladder(value="8.0"), physics=True))
        assert "node-does-not-balance" not in codes(
            check(ladder(value="0.125", count=8, arrangement="series"),
                  physics=True))

    def test_a_junction_with_no_temperature_is_named_not_folded(self):
        """`corner` used to fold the two resistances through it into one.
        The kind is gone: a junction between two paths is a free node, and
        one that states no temperature is reported by name as unchecked —
        and so is its neighbour — rather than folded away or skipped
        without a word."""
        b = (DiagramBuilder(R="K/W", T="°C", P="W")
             .node("a", "Hot", "50", at=(0, 0), sub="a")
             .node("k", "Mid", at=(150, 0), sub="k")
             .node("b", "Cold", "40", kind="fixed", at=(300, 0), sub="b")
             .branch("a", "k", "cond", "Half", "0.5")
             .branch("k", "b", "cond", "Other half", "0.5")
             .source("a", "diss", "Load", "10", sub="d"))
        report = check(b, physics=True)
        assert "node-does-not-balance" not in codes(report)
        note = [f for f in report.findings if f.code == "physics-not-checked"]
        assert len(note) == 1
        assert "k (it has no temperature)" in note[0].message
        assert "a (neighbour 'k' has no temperature)" in note[0].message

    def test_a_flow_branch_carries_its_stated_rate(self):
        b = (DiagramBuilder(R="K/W", T="°C", P="W", q="W")
             .node("a", "Hot", "50", at=(0, 0), sub="a")
             .node("b", "Cold", "40", at=(300, 0), sub="b")
             .branch("a", "b", "flow", "Pumped", "10")
             .source("a", "diss", "Load", "10", sub="d")
             .source("b", "flow", "Out", "10", outward=True))
        assert "node-does-not-balance" not in codes(check(b, physics=True))

    def test_a_capacitance_and_a_break_carry_nothing(self):
        b = (ladder()
             .rail("b", y=200)
             .branch("a", "rail", "cap", "Mass", "5", sub="a")
             .branch("a", "b", "break", "Standoff"))
        b.diagram.units["C"] = "J/K"
        assert "node-does-not-balance" not in codes(check(b, physics=True))

    def test_a_resistance_to_the_rail_uses_the_reference_temperature(self):
        b = (DiagramBuilder(R="K/W", T="°C", P="W")
             .node("a", "Hot", "50", at=(0, 0), sub="a")
             .node("b", "Ref", "40", kind="fixed", at=(300, 0), sub="b")
             .rail("b", y=200)
             .branch("a", "rail", "cond", "Down", "1.0")
             .source("a", "diss", "Load", "10", sub="d"))
        assert "node-does-not-balance" not in codes(check(b, physics=True))


class TestWhatItWillNotGuess:
    def test_a_flux_source_has_no_area_so_its_node_is_skipped(self):
        b = ladder("30").source("a", "flux", "Face", "800", outward=True)
        b.diagram.units["q″"] = "W/cm²"
        assert "node-does-not-balance" not in codes(check(b, physics=True))

    def test_a_unit_it_does_not_know_skips_the_diagram(self):
        b = ladder("30")
        b.diagram.units["R"] = "K/BTU"
        assert "node-does-not-balance" not in codes(check(b, physics=True))

    def test_a_value_that_is_not_a_number_skips_the_node(self):
        assert "node-does-not-balance" not in codes(
            check(ladder("cold"), physics=True))

    def test_a_fixed_node_is_a_reservoir_and_is_not_asked(self):
        found = check(ladder("30"), physics=True).findings
        assert all(f.where != "node 'b'" for f in found)

    def test_placements_cannot_ask_for_it(self):
        from thermodraw import layout
        with pytest.raises(ValueError, match="needs a Diagram"):
            check(layout(ladder().build()), physics=True)


class TestARateAgainstItsEnds:
    def test_a_rate_its_ends_agree_with_is_quiet(self):
        b = ladder()
        b.diagram.units["q"] = "W"
        b.diagram.branches[0].rate = "10"
        assert "rate-does-not-match" not in codes(check(b, physics=True))

    def test_a_rate_its_ends_contradict_is_reported(self):
        b = ladder()
        b.diagram.units["q"] = "W"
        b.diagram.branches[0].rate = "25"
        found = [f for f in check(b, physics=True).findings
                 if f.code == "rate-does-not-match"]
        assert len(found) == 1 and "25 W" in found[0].message
        assert "10 W" in found[0].message


def test_the_cli_exposes_it(capsys, tmp_path):
    path = tmp_path / "d.json"
    path.write_text(ladder("30").to_json(), encoding="utf-8")
    assert main(["check", str(path)]) == 0
    assert main(["check", "--physics", str(path)]) == 1
    assert "node-does-not-balance" in capsys.readouterr().out


class TestARadiationValueOnARise:
    """A radiation resistance is linearised at a pair of absolute
    temperatures. A diagram that declares its temperatures as a rise above
    ambient has no absolute temperature on the page to have taken it at, so
    a `rad` value there gets one note — and only there: an undeclared scale
    is undeclared, and a note on every `rad` would be a footnote wearing a
    severity."""

    @staticmethod
    def sink(scale=None, kind="rad"):
        b = (DiagramBuilder(R="K/W", T="K", P="W", scale=scale)
             .node("s", "Sink", "60", at=(0, 0), sub="s")
             .node("amb", "Ambient", "20", kind="fixed", at=(300, 0), sub="a")
             .branch("s", "amb", kind, "Path", "4.0")
             .source("s", "diss", "Load", "10", sub="d"))
        return b

    def test_a_rise_with_a_rad_value_is_noted(self):
        found = [f for f in check(self.sink("rise"), physics=True).findings
                 if f.code == "rad-needs-absolute-scale"]
        assert len(found) == 1
        assert found[0].severity == "note"
        assert found[0].where == "branch 0 s->amb"
        assert "absolute" in found[0].remedy

    def test_absolute_is_quiet(self):
        assert "rad-needs-absolute-scale" not in codes(
            check(self.sink("absolute"), physics=True))

    def test_undeclared_is_quiet(self):
        assert "rad-needs-absolute-scale" not in codes(
            check(self.sink(), physics=True))

    def test_a_rise_with_no_radiation_is_quiet(self):
        assert "rad-needs-absolute-scale" not in codes(
            check(self.sink("rise", "conv"), physics=True))

    def test_the_balance_itself_does_not_care(self):
        """Differences only: 10 W over 4 K/W is the 40 K drop on either
        scale, and neither declaration changes the answer."""
        for scale in (None, "absolute", "rise"):
            assert "node-does-not-balance" not in codes(
                check(self.sink(scale), physics=True))
