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
from . import layout as L
from . import model as M
from . import render as R
from . import theme as T


class DiagramBuilder:
    """Builds a `Diagram`. Every method returns self so calls chain."""

    def __init__(self, title=None, size=None, **units):
        self.diagram = M.Diagram(units={k: v for k, v in units.items() if v},
                                 size=size, title=title)

    # ------------------------------------------------------------- the parts
    def node(self, node_id, label=None, value=None, at=None, kind="free",
             sub="", angle=0.0):
        self.diagram.nodes.append(M.Node(
            id=node_id, kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle))
        return self

    def branch(self, source, target, kind="cond", label=None, value=None,
               via=None, at=None, angle=None):
        self.diagram.branches.append(M.Branch(
            source=source, target=target, kind=kind, label=label, value=value,
            via=list(via or []), at=at, angle=angle))
        return self

    def source(self, target, kind="diss", label=None, value=None, sub="",
               at=None, angle=0.0):
        self.diagram.sources.append(M.Source(
            target=target, kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle))
        return self

    def rail(self, reference, y, span=None):
        """The reference rail. Branches may name `rail` as an endpoint."""
        self.diagram.rail = M.Rail(reference=reference, y=y, span=span)
        return self

    # ----------------------------------------------------------- the outputs
    def build(self):
        return self.diagram.validate()

    def placements(self):
        return L.layout(self.build())

    def svg(self, mode=None, size=None, padding=R.PADDING):
        """SVG for this diagram.

        `mode` picks a baked palette for Word, slides and rasterisers. Without
        it the output carries custom properties and follows the reader's
        light/dark setting.
        """
        out = R.render(self.placements(), size=size or self.diagram.size,
                       padding=padding)
        return T.bake(out, mode) if mode else T.with_variables(out)

    def to_dict(self):
        return self.build().to_dict()

    def to_json(self, **kw):
        return self.build().to_json(**kw)

    @classmethod
    def from_dict(cls, data):
        self = cls()
        self.diagram = M.Diagram.from_dict(data)
        return self
