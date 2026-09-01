"""The numbers on the page, asked whether they agree with each other.

A prototype behind `check(physics=True)`. These pin what it must do before
its fire rate on real diagrams decides whether it ships: fire on a node whose
stated values do not close, stay quiet on one whose values do, fold `count`
the way the schema says a count folds, and skip what it cannot know.
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
        That is the rack diagram in the gallery."""
        assert "node-does-not-balance" not in codes(
            check(ladder(value="8.0", count=8, arrangement="parallel"),
                  physics=True))
        assert "node-does-not-balance" in codes(
            check(ladder(value="8.0"), physics=True))
        assert "node-does-not-balance" not in codes(
            check(ladder(value="0.125", count=8, arrangement="series"),
                  physics=True))

    def test_a_corner_is_folded_into_the_path_through_it(self):
        b = (DiagramBuilder(R="K/W", T="°C", P="W")
             .node("a", "Hot", "50", at=(0, 0), sub="a")
             .node("k", kind="corner", at=(150, 0))
             .node("b", "Cold", "40", kind="fixed", at=(300, 0), sub="b")
             .branch("a", "k", "cond", "Half", "0.5")
             .branch("k", "b", "cond", "Other half", "0.5")
             .source("a", "diss", "Load", "10", sub="d"))
        assert "node-does-not-balance" not in codes(check(b, physics=True))

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
