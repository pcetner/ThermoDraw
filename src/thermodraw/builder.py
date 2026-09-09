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
from typing import Any, Dict, List, Optional, Sequence, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from ._analysis import PhysicsResult
    from ._layout import Placement
    from ._check import Report
    from ._describe import Description

from . import model as M
from . import _render as R


class DiagramBuilder:
    """Builds a `Diagram`. Every method returns self so calls chain."""

    def __init__(self, title: Optional[str] = None, size: Optional[Sequence[float]] = None, scale: Optional[str] = None, **units: str) -> None:
        """`scale` says what `T` is on, "absolute" or "rise"; it is a
        keyword of its own so `**units` cannot mistake it for a quantity."""
        self.diagram = M.Diagram(units={k: v for k, v in units.items() if v},
                                 size=size, title=title, scale=scale)

    # ------------------------------------------------------------- the parts
    def node(self, node_id: str, label: Optional[str] = None, value: Union[str, float, None] = None, at: Optional[Sequence[float]] = None, kind: str = "free",
             sub: str = "", angle: float = 0.0, side: str = "auto", wall: str = "down", label_offset: Optional[Sequence[float]] = None) -> "DiagramBuilder":
        """`wall` turns a `fixed` or `break` node's wall: `down` (default),
        `up`, `left` or `right`."""
        self.diagram.nodes.append(M.Node(
            id=node_id, kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle, side=side, wall=wall, label_offset=label_offset))
        return self

    def branch(self, source: str, target: str, kind: str = "cond",
               label: Optional[str] = None, value: Union[str, float, None] = None,
               sub: str = "", via: Optional[Sequence[Sequence[float]]] = None,
               at: Optional[Sequence[float]] = None, angle: Optional[float] = None,
               side: str = "auto", rate: Union[str, float, None] = None,
               count: Optional[int] = None, arrangement: Optional[str] = None,
               id: Optional[str] = None, label_offset: Optional[Sequence[float]] = None,
               *, mdot: Union[str, float, None] = None, cp: Union[str, float, None] = None) -> "DiagramBuilder":
        """`sub` is only meaningful on a capacitance, where the subscript
        names a place. A resistance carries its own, naming the mechanism."""
        self.diagram.branches.append(M.Branch(
            source=source, target=target, kind=kind, label=label, sub=sub,
            value=value, rate=rate, mdot=mdot, cp=cp, count=count, arrangement=arrangement,
            via=list(via or []), at=at, angle=angle, side=side, id=id, label_offset=label_offset))
        return self

    def source(self, node: str, kind: str = "diss", label: Optional[str] = None,
               value: Union[str, float, None] = None, sub: str = "",
               at: Optional[Sequence[float]] = None, angle: float = 0.0,
               side: str = "auto", outward: bool = False, count: Optional[int] = None,
               id: Optional[str] = None, label_offset: Optional[Sequence[float]] = None) -> "DiagramBuilder":
        """Heat crossing into `node`, or out of it with `outward=True`.

        `outward` is the `from` of the schema against its `to`. Only `flow`
        and `flux` may use it; the other two name their own direction.
        """
        end = {"source" if outward else "target": node}
        self.diagram.sources.append(M.Source(
            kind=kind, label=label, sub=sub, value=value,
            at=at, angle=angle, side=side, count=count, id=id, label_offset=label_offset, **end))
        return self

    def rail(self, reference: str, y: Optional[float] = None, span: Optional[Sequence[float]] = None) -> "DiagramBuilder":
        """The reference rail. Branches may name `rail` as an endpoint.
        `y` left out goes 222 below the lowest node, as in the schema."""
        self.diagram.rail = M.Rail(reference=reference, y=y, span=span)
        return self

    def region(self, id: str, **kwargs: Any) -> "DiagramBuilder":
        self.diagram.regions.append(M.Region(id, **kwargs))
        return self

    def control_volume(self, id: str, **kwargs: Any) -> "DiagramBuilder":
        self.diagram.control_volumes.append(M.ControlVolume(id, **kwargs))
        return self

    def control_surface(self, id: str, volume: str, **kwargs: Any) -> "DiagramBuilder":
        self.diagram.control_surfaces.append(M.ControlSurface(id, volume, **kwargs))
        return self

    def transfer(self, id: str, **kwargs: Any) -> "DiagramBuilder":
        self.diagram.transfers.append(M.Transfer(id, **kwargs))
        return self

    def annotation(self, id: str, **kwargs: Any) -> "DiagramBuilder":
        self.diagram.annotations.append(M.Annotation(id, **kwargs))
        return self

    # ----------------------------------------------------------- the outputs
    def analysis(self, **settings: Any) -> "DiagramBuilder":
        """Set explicit network/CV unknowns and analysis assumptions."""
        import copy
        self.diagram.analysis = copy.deepcopy(settings)
        return self

    def solve_physics(self) -> "PhysicsResult":
        from ._analysis import solve_physics
        return solve_physics(self.build())

    def build(self) -> M.Diagram:
        return self.diagram.validate()

    # Each output is the `Diagram`'s own, on the built data: one
    # implementation, and the same size and padding for all of them, so
    # what `check` reports and `describe` says is what `svg` draws.
    def placements(self) -> List["Placement"]:
        return self.build().placements()

    def svg(self, mode: Optional[str] = None, size: Optional[Sequence[float]] = None, padding: float = R.PADDING, notation: str = "boxes") -> str:
        """SVG for this diagram.

        `mode` picks a baked palette for Word, slides and rasterisers. Without
        it the output carries custom properties and follows the reader's
        light/dark setting. `notation` is `boxes` or `zigzags`.
        """
        return self.build().svg(mode, size=size, padding=padding,
                                notation=notation)

    def check(self, size: Optional[Sequence[float]] = None, padding: float = R.PADDING, physics: bool = False) -> "Report":
        """What is wrong with this diagram, without rendering it to look."""
        return self.build().check(size=size, padding=padding, physics=physics)

    def describe(self, size: Optional[Sequence[float]] = None, padding: float = R.PADDING) -> "Description":
        """What this diagram contains, without rendering it to look.

        `check` says whether the drawing reads well; this says what is in it.
        """
        return self.build().describe(size=size, padding=padding)

    def page(self, size: Optional[Sequence[float]] = None, padding: float = R.PADDING, title: Optional[str] = None,
             notation: str = "boxes") -> str:
        """This diagram as a self-contained HTML page, controls and all."""
        return self.build().page(size=size, padding=padding, title=title,
                                 notation=notation)

    def _repr_svg_(self) -> str:
        return self.svg()

    def to_dict(self) -> Dict[str, Any]:
        return self.build().to_dict()

    def to_json(self, **kw: Any) -> str:
        return self.build().to_json(**kw)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DiagramBuilder":
        self = cls()
        self.diagram = M.Diagram.from_dict(data)
        return self
