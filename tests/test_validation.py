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
    (None, "0.3"),
])
def test_bad_coordinates_are_caught_before_drawing(at, expected):
    with pytest.raises(DiagramError, match=expected):
        Diagram.from_dict({"nodes": [{"id": "a", "at": at}]})


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
def test_nothing_malformed_reaches_the_renderer():
    """Whatever validate accepts, layout and render must survive."""
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
            render(layout(Diagram.from_dict(data)))
