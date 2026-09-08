"""Bad input, caught early and explained.

`validate()` promises every reason a diagram cannot be drawn, reported before
drawing. It used to check ids and kinds but nothing about the shape of a
value, so seven ways of writing a bad coordinate got through: six died deep
in the renderer with messages like "Unknown format code 'f' for object of
type 'str'" that named no node and no field, and one drew the wrong picture
in silence.

The flagship input is JSON written by a model, so a near-miss key gets the
best error in the library.
"""
import pytest

from thermodraw import Diagram, DiagramError, layout, render

PAIR = [{"id": "a", "at": [0, 0]}, {"id": "b", "at": [220, 0]}]


def build(**parts):
    return Diagram.from_dict({"nodes": list(PAIR), **parts})


# ------------------------------------------------------- shapes and types
@pytest.mark.parametrize("at, expected", [
    ({"x": 0, "y": 0}, "pair of numbers"),
    (["0", "0"], "must be numbers"),
    ([0, 0, 0], "exactly two"),
    ([0], "exactly two"),
    ("0,0", "pair of numbers"),
])
def test_bad_coordinates_are_caught_before_drawing(at, expected):
    with pytest.raises(DiagramError, match=expected):
        Diagram.from_dict({"nodes": [{"id": "a", "at": at}]})


def test_no_coordinates_is_not_bad_coordinates():
    """`at` left out, or null, is a node for the solver. It used to be
    refused with a promise about the network layer."""
    for node in ({"id": "a"}, {"id": "a", "at": None}):
        render(layout(Diagram.from_dict({"nodes": [node]})))


def test_the_node_and_the_field_are_named():
    with pytest.raises(DiagramError, match=r"node 'sink'.*at"):
        Diagram.from_dict({"nodes": [{"id": "sink", "at": ["0", "0"]}]})


@pytest.mark.parametrize("bad", ["90", None, [90], True])
def test_angle_must_be_a_number(bad):
    with pytest.raises(DiagramError, match="angle must be a number"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0], "angle": bad}]})


def test_via_must_be_points():
    with pytest.raises(DiagramError, match=r"via\[0\]"):
        build(branches=[{"from": "a", "to": "b", "kind": "cond", "via": [5]}])
    with pytest.raises(DiagramError, match="via must be a list"):
        build(branches=[{"from": "a", "to": "b", "kind": "cond", "via": 5}])


def test_rail_geometry_is_checked():
    with pytest.raises(DiagramError, match="rail: y must be a number"):
        build(rail={"reference": "a", "y": "372"},
              branches=[{"from": "b", "to": "rail", "kind": "cap"}])


def test_value_must_be_a_number_or_text():
    with pytest.raises(DiagramError, match="value must be a number or text"):
        build(units={"R": "K/W"},
              branches=[{"from": "a", "to": "b", "kind": "cond",
                         "value": [1]}])


def test_a_true_is_not_a_coordinate():
    """bool is an int in Python, and True is not a position."""
    with pytest.raises(DiagramError, match="must be numbers"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [True, 0]}]})


# ------------------------------------------------------------ finiteness
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_a_coordinate_must_be_finite(bad):
    """`nan` is a float, so it passed the type check and rendered
    `width="nan"` — a blank document, the seventh silent way to write a bad
    `at`."""
    with pytest.raises(DiagramError, match="finite"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [bad, 0]}]})


def test_an_angle_must_be_finite():
    with pytest.raises(DiagramError, match="angle must be a finite number"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0],
                                      "angle": float("nan")}]})


# ------------------------------------------------------------------- ids
def test_an_id_must_not_be_empty():
    with pytest.raises(DiagramError, match="non-empty"):
        Diagram.from_dict({"nodes": [{"id": "", "at": [0, 0]}]})


def test_rail_is_reserved_and_the_error_says_so():
    """`rail` is what a branch names to join the reference rail, so a node
    called that was silently taken for the rail."""
    with pytest.raises(DiagramError, match="names the reference rail"):
        Diagram.from_dict({"nodes": [{"id": "rail", "at": [0, 0]}]})


@pytest.mark.parametrize("weird", ["hot side", "o'clock", "a->b", "T_j (°C)"])
def test_any_other_text_is_a_fine_id(weird):
    """No code parses an id back out of a string, so nothing constrains what
    one contains. Forbidding characters would defend a parse that no longer
    exists — and `a->b` really did break two things, for exactly as long as
    the parse did."""
    d = Diagram.from_dict({"nodes": [{"id": weird, "at": [0, 0]},
                                     {"id": "b", "at": [220, 0]}],
                           "branches": [{"from": weird, "to": "b",
                                         "kind": "cond"}]})
    render(layout(d))


# ---------------------------------------------------------- source count
@pytest.mark.parametrize("bad, expected", [("many", "whole number"),
                                           (0, "1 or more"),
                                           (True, "whole number")])
def test_a_source_count_is_checked_like_a_branchs(bad, expected):
    """It went through nothing: `count: 0` drew one and `count: "many"` died
    in `layout` with a TypeError naming no source."""
    with pytest.raises(DiagramError, match=expected):
        build(units={"P": "W"},
              sources=[{"to": "a", "kind": "diss", "value": 5, "count": bad}])


# -------------------------------------------------------------- bad keys
@pytest.mark.parametrize("key, hint", [
    ("name", "label"), ("text", "label"), ("type", "kind"),
    ("position", "at"), ("coordinates", "at"), ("subscript", "sub"),
])
def test_a_near_miss_key_is_named_and_corrected(key, hint):
    with pytest.raises(DiagramError, match=f"did you mean '{hint}'"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0], key: "x"}]})


def test_unknown_key_lists_what_was_expected():
    with pytest.raises(DiagramError, match="Expected:.*label.*sub"):
        Diagram.from_dict({"nodes": [{"id": "a", "at": [0, 0], "zz": 1}]})


def test_top_level_typo_is_corrected():
    with pytest.raises(DiagramError, match="did you mean 'nodes'"):
        Diagram.from_dict({"node": []})


def test_branch_endpoints_keep_their_json_names():
    """The schema says from/to; the dataclass says source/target. Errors
    must speak the schema's language, not the implementation's."""
    with pytest.raises(DiagramError) as caught:
        build(branches=[{"between": ["a", "b"], "kind": "cond"}])
    message = str(caught.value)
    assert "from" in message and "to" in message
    assert "source" not in message and "target" not in message


def test_missing_required_field_says_which():
    with pytest.raises(DiagramError, match="missing required field 'id'"):
        Diagram.from_dict({"nodes": [{"at": [0, 0]}]})


def test_a_diagram_must_be_an_object():
    with pytest.raises(DiagramError, match="a diagram is an object"):
        Diagram.from_dict([{"id": "a"}])


# ------------------------------------------------------------- the promise
def test_bad_input_is_refused_before_layout_sees_it():
    """Every one of these is refused by `Diagram.from_dict` on its own. An
    earlier version wrapped each in `render(layout(...))` and claimed to show
    the renderer survives — but nothing ever reached the renderer, so it
    showed that `from_dict` raises, which the tests above already do."""
    bad = [
        {"nodes": [{"id": "a", "at": {"x": 0}}]},
        {"nodes": [{"id": "a", "at": ["0", "0"]}]},
        {"nodes": [{"id": "a", "at": [0, 0, 0]}]},
        {"nodes": [{"id": "a", "at": [0]}]},
        {"nodes": list(PAIR),
         "branches": [{"from": "a", "to": "b", "kind": "cond", "via": [5]}]},
        {"nodes": list(PAIR), "rail": {"reference": "a", "y": "372"},
         "branches": [{"from": "b", "to": "rail", "kind": "cap"}]},
        {"nodes": [{"id": "a", "at": [0, 0], "angle": "90"}]},
    ]
    for data in bad:
        with pytest.raises(DiagramError):
            Diagram.from_dict(data)


@pytest.mark.parametrize("data", [
    {"nodes": []},
    {"nodes": [{"id": "a", "at": [0, 0]}]},
    {"nodes": list(PAIR)},
    {"nodes": list(PAIR),
     "branches": [{"from": "a", "to": "b", "kind": "break"}]},
    {"nodes": [{"id": "a", "at": [0, 0], "sub": "a"},
               {"id": "b", "at": [220, 0]}],
     "branches": [{"from": "a", "to": "b", "kind": "cond"}]},
    {"nodes": list(PAIR), "units": {"P": "W"},
     "sources": [{"to": "a", "kind": "diss", "value": "5"}]},
], ids=["empty", "one node", "two nodes, nothing between",
        "a break with no label", "a node with a sub and no value",
        "a source and no branch"])
def test_whatever_validate_accepts_renders(data):
    """The actual promise: an accepted diagram survives layout and render,
    however little is in it."""
    render(layout(Diagram.from_dict(data)))


def test_a_retired_kind_names_its_replacement():
    """`corner` was a node kind until 1.0: a coordinate that drew nothing, so
    a wire had somewhere to bend. `via` does that, and a junction that has a
    name and no temperature is a `free` node with a `sub`. A file written
    before the removal is told so, not handed "unknown kind" beside a list
    the kind used to be on."""
    with pytest.raises(DiagramError, match="removed in 1.0") as caught:
        Diagram.from_dict({"nodes": [{"id": "k", "kind": "corner",
                                      "at": [420, 260]}]})
    assert "`via`" in str(caught.value)
    assert "`free`" in str(caught.value)


# ------------------------------------------------------------- 1.0 fields
def test_a_wall_is_for_the_kinds_that_draw_one():
    for kind in ("free", "phase"):
        with pytest.raises(DiagramError, match="no wall to turn"):
            Diagram.from_dict({"nodes": [{"id": "a", "kind": kind,
                                          "at": [0, 0], "wall": "up"}]})
    for kind in ("fixed", "break"):
        Diagram.from_dict({"nodes": [{"id": "a", "kind": kind,
                                      "at": [0, 0], "wall": "left"}]})


def test_a_wall_faces_one_of_four_ways():
    with pytest.raises(DiagramError, match="wall must be one of"):
        Diagram.from_dict({"nodes": [{"id": "a", "kind": "fixed",
                                      "at": [0, 0], "wall": "north"}]})


def test_the_temperature_scale_is_one_of_two():
    with pytest.raises(DiagramError, match="scale must be one of"):
        Diagram.from_dict({"units": {"T": {"unit": "K", "scale": "kelvin"}},
                           "nodes": [{"id": "a", "at": [0, 0]}]})


def test_a_temperature_object_takes_unit_and_scale_only():
    with pytest.raises(DiagramError, match="takes `unit` and `scale`"):
        Diagram.from_dict({"units": {"T": {"scale": "rise"}},
                           "nodes": [{"id": "a", "at": [0, 0]}]})
    with pytest.raises(DiagramError, match="takes `unit` and `scale`"):
        Diagram.from_dict({"units": {"T": {"unit": "K", "zero": 273}},
                           "nodes": [{"id": "a", "at": [0, 0]}]})


def test_a_scale_needs_a_temperature_unit_to_sit_on():
    from thermodraw import DiagramBuilder
    with pytest.raises(DiagramError, match="no entry for 'T'"):
        DiagramBuilder(R="K/W", scale="rise").node("a", at=(0, 0)).build()


# ------------------------------------------------- the 1.1 vocabulary adds
class TestALinkStatesNothing:
    """A link's whole claim is that there is nothing between its ends.

    So it names no quantity, and a number on one would be a number about
    something the element says does not exist. The refusal is the same shape
    as a `break`'s and gives its own reason, because the two name no quantity
    for opposite reasons: a break carries no heat, a link carries it with
    nothing in the way.
    """

    @pytest.mark.parametrize("field", ["value", "rate"])
    def test_it_refuses_a_number(self, field):
        with pytest.raises(DiagramError) as exc:
            build(units={"R": "K/W", "q": "W"},
                  branches=[{"from": "a", "to": "b", "kind": "link",
                             field: "0.1"}])
        assert "ideal joint" in str(exc.value)
        assert f"states no {field}" in str(exc.value)

    def test_a_break_keeps_its_own_reason(self):
        """Both go through one check now; the break's wording is unmoved."""
        with pytest.raises(DiagramError) as exc:
            build(units={"R": "K/W"},
                  branches=[{"from": "a", "to": "b", "kind": "break",
                             "value": "1"}])
        assert "carries no heat" in str(exc.value)

    def test_a_label_alone_is_enough(self):
        d = build(branches=[{"from": "a", "to": "b", "kind": "link",
                             "label": "Bolted flange"}])
        assert layout(d) and render(layout(d))


class TestAStreamStatesAFlowAndAHeatAndNothingElse:
    """A stream is the one branch whose number is worked out rather than
    written down, so every field that would state it a second way is
    refused, and each refusal names what a stream does state."""

    UNITS = {"R": "K/kW", "T": "K", "P": "kW", "q": "kW",
             "mdot": "kg/s", "cp": "kJ/kg·K"}

    def stream(self, **extra):
        return build(units=dict(self.UNITS),
                     branches=[{"from": "a", "to": "b", "kind": "stream",
                                "mdot": "2.5", "cp": "0.665", **extra}])

    @pytest.mark.parametrize("field", ["value", "rate"])
    def test_it_refuses_a_number_it_would_work_out_itself(self, field):
        with pytest.raises(DiagramError) as exc:
            self.stream(**{field: "1579"})
        assert "worked out from them" in str(exc.value)
        assert "come to disagree" in str(exc.value)

    @pytest.mark.parametrize("missing,named", [("mdot", "cp"), ("cp", "mdot")])
    def test_one_of_the_two_alone_states_nothing(self, missing, named):
        with pytest.raises(DiagramError) as exc:
            self.stream(**{missing: None})
        assert f"`{missing}` and `{named}` together or neither" in str(exc.value)

    def test_neither_is_a_stream_that_draws_its_label_alone(self):
        """Every other path may carry no number; so may this one. It is also
        what the editor drops: a gesture must not write a diagram that
        cannot be drawn, and a dropped path arrives named and unnumbered."""
        d = build(branches=[{"from": "a", "to": "b", "kind": "stream",
                             "label": "Steel strip"}])
        assert render(layout(d))
        assert "mdot" not in d.to_dict()["branches"][0]

    def test_a_unit_it_would_render_bare_is_refused(self):
        with pytest.raises(DiagramError) as exc:
            build(units={k: v for k, v in self.UNITS.items() if k != "cp"},
                  branches=[{"from": "a", "to": "b", "kind": "stream",
                             "mdot": "2.5", "cp": "0.665"}])
        assert "units has no entry for 'cp'" in str(exc.value)

    def test_a_unit_the_check_does_not_know_still_draws(self):
        """`--physics` skips a diagram whose units it cannot scale; it does
        not refuse to draw one. `R` has always worked that way."""
        d = build(units={**self.UNITS, "cp": "BTU/lb·F"},
                  branches=[{"from": "a", "to": "b", "kind": "stream",
                             "mdot": "2.5", "cp": "0.16"}])
        assert render(layout(d))

    def test_it_refuses_angle_like_every_directed_kind(self):
        with pytest.raises(DiagramError) as exc:
            self.stream(angle=90)
        assert "carries heat from one end to the other" in str(exc.value)

    def test_it_refuses_count_because_the_group_would_have_no_number(self):
        with pytest.raises(DiagramError) as exc:
            self.stream(count=4, arrangement="parallel")
        assert "does not take `count`" in str(exc.value)
        assert "write the strands out" in str(exc.value)

    def test_the_two_fields_belong_to_no_other_kind(self):
        with pytest.raises(DiagramError) as exc:
            build(units=dict(self.UNITS),
                  branches=[{"from": "a", "to": "b", "kind": "cond",
                             "value": "1", "cp": "0.665"}])
        assert "`cp` belongs to a `stream`" in str(exc.value)

    def test_what_it_does_state_draws(self):
        d = self.stream()
        assert layout(d) and render(layout(d))
        assert d.to_dict()["branches"][0]["mdot"] == "2.5"

