"""A builder, over the data.

Sugar only. Everything it does is `Diagram` construction, so anything the
builder can say is also expressible as a dict, and a diagram that came from
JSON is indistinguishable from one that came from here. That is the point:
the data is the representation, not a serialisation of some object.

    d = (DiagramBuilder(R="K/W", T="°C", P="W")
         .node("j", "Junction", 112, at=(200, 150), sub="j")
         .node("c", "Case", 78, at=(424, 150), sub="c")
         .branch("j", "c", "cond", "Die attach", "0.35")
         .source("j", "diss", "Switching loss", 45, sub="d"))
    open("out.svg", "w").write(d.svg())
"""
from . import model as M
from . import _render as R


class DiagramBuilder:
    """Builds a `Diagram`. Every method returns self so calls chain."""

    def __init__(self, title=None, size=None, scale=None, **units):
        """`scale` says what `T` is on, "absolute" or "rise"; it is a
        keyword of its own so `**units` cannot mistake it for a quantity."""
        self.diagram = M.Diagram(units={k: v for k, v in units.items() if v},
                                 size=size, title=title, scale=scale)

    # ------------------------------------------------------------- the parts
    def node(self, node_id, label=None, value=None, at=None, kind="free",
             sub="", angle=0.0, side="auto", wall="down"):
        """`wall` turns a `fixed` or `break` node's wall: `down` (default),
        `up`, `left` or `right`."""
        self.diagram.nodes.append(M.Node(
            id=node_id, kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle, side=side, wall=wall))
        return self

    def branch(self, source, target, kind="cond", label=None, value=None,
               sub="", via=None, at=None, angle=None, side="auto",
               rate=None, count=None, arrangement=None):
        """`sub` is only meaningful on a capacitance, where the subscript
        names a place. A resistance carries its own, naming the mechanism."""
        self.diagram.branches.append(M.Branch(
            source=source, target=target, kind=kind, label=label, sub=sub,
            value=value, rate=rate, count=count, arrangement=arrangement,
            via=list(via or []), at=at, angle=angle, side=side))
        return self

    def source(self, node, kind="diss", label=None, value=None, sub="",
               at=None, angle=0.0, side="auto", outward=False, count=None):
        """Heat crossing into `node`, or out of it with `outward=True`.

        `outward` is the `from` of the schema against its `to`. Only `flow`
        and `flux` may use it; the other two name their own direction.
        """
        end = {"source" if outward else "target": node}
        self.diagram.sources.append(M.Source(
            kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle, side=side, count=count, **end))
        return self

    def rail(self, reference, y=None, span=None):
        """The reference rail. Branches may name `rail` as an endpoint.
        `y` left out goes 222 below the lowest node, as in the schema."""
        self.diagram.rail = M.Rail(reference=reference, y=y, span=span)
        return self

    # ----------------------------------------------------------- the outputs
    def build(self):
        return self.diagram.validate()

    # Each output is the `Diagram`'s own, on the built data: one
    # implementation, and the same size and padding for all of them, so
    # what `check` reports and `describe` says is what `svg` draws.
    def placements(self):
        return self.build().placements()

    def svg(self, mode=None, size=None, padding=R.PADDING):
        """SVG for this diagram.

        `mode` picks a baked palette for Word, slides and rasterisers. Without
        it the output carries custom properties and follows the reader's
        light/dark setting.
        """
        return self.build().svg(mode, size=size, padding=padding)

    def check(self, size=None, padding=R.PADDING, physics=False):
        """What is wrong with this diagram, without rendering it to look."""
        return self.build().check(size=size, padding=padding, physics=physics)

    def describe(self, size=None, padding=R.PADDING):
        """What this diagram contains, without rendering it to look.

        `check` says whether the drawing reads well; this says what is in it.
        """
        return self.build().describe(size=size, padding=padding)

    def page(self, size=None, padding=R.PADDING, title=None):
        """This diagram as a self-contained HTML page, controls and all."""
        return self.build().page(size=size, padding=padding, title=title)

    def _repr_svg_(self):
        return self.svg()

    def to_dict(self):
        return self.build().to_dict()

    def to_json(self, **kw):
        return self.build().to_json(**kw)

    @classmethod
    def from_dict(cls, data):
        self = cls()
        self.diagram = M.Diagram.from_dict(data)
        return self
