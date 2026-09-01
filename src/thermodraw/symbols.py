"""The ThermoDraw symbol set.

Each symbol is geometry in a local frame — heat along +x, centred on the
origin — plus the metadata the label solver needs: how far the symbol
reaches perpendicular to the branch (``half``) and along it (``half_len``).
"""
import math
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from . import core as S

CSS = """
.w,.sym-box{stroke:var(--sym);stroke-width:1.8;fill:none;stroke-linecap:round;stroke-linejoin:round}
polyline{fill:none;stroke:var(--sym);stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.node-open{fill:var(--panel);stroke:var(--sym);stroke-width:1.8}
.fillsym{fill:var(--sym);stroke:none}
.tex line,.tex polyline{stroke:var(--tex);stroke-width:1.1;fill:none}
.tex polygon{fill:var(--tex)}
.gapfill{fill:var(--panel);stroke:none}
.region{fill:none;stroke:var(--ink-2);stroke-width:1.4;stroke-dasharray:6 5}
.tick{stroke:var(--rule);stroke-width:1}
text{font-family:var(--sans);fill:var(--ink)}
.lbl{font-size:13px;font-style:italic}
.val{font-size:13px;fill:var(--ink);font-style:normal}
.eq{font-size:13px;fill:var(--ink);font-style:normal}
.user{font-size:11.5px;font-weight:600;font-style:normal;fill:var(--ink)}
.ang{font-size:10px;fill:var(--ink-3);font-style:normal}
.reg-lbl{font-size:11.5px;fill:var(--ink-2);font-style:normal;font-weight:600}
"""

ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
CW, CH = 248, 190
LEAD = 20


def canvas(w, h, body, fluid=False):
    """The document. Explicit dimensions by default.

    These are files, and a file loaded through an <img> tag has no column to
    fill, so width="100%" left it with nothing to size from — the demo had to
    rewrite the root tag with a regex to publish anything. Pass fluid=True for
    a fragment inlined in a page that owns its own width.
    """
    size = 'width="100%"' if fluid else f'width="{w}" height="{h}"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'{size} role="img"><style>{CSS}</style>'
            f'{S.hoist_defs(body)}</svg>')


def leads(hb, L=LEAD):
    return (f'<line class="w" x1="{-hb-L}" y1="0" x2="{-hb}" y2="0"/>'
            f'<line class="w" x1="{hb}" y1="0" x2="{hb+L}" y2="0"/>')


def rect(dashed=False):
    d = ' stroke-dasharray="5 4"' if dashed else ""
    return (f'<rect class="sym-box" x="{-S.BW/2}" y="{-S.BH/2}" width="{S.BW}" '
            f'height="{S.BH}" rx="2"{d}/>')


# ------------------------------------------------------------------ textures
# The interior states what the heat is crossing. Kept separate from the box
# that carries it so it can be reused without the outline and the leads —
# the demo had to hand-copy the contact hatching out of g_contact to place a
# box of its own, and two copies of a drafting convention will drift.
def tex_cond():
    """Section hatching: heat crossing solid material."""
    return S.hatch(S.BW, S.BH, 45)


def tex_conv():
    """Streamlines: heat carried by a moving fluid."""
    return S.streamlines(S.BW, S.BH)


def tex_rad():
    """Two wave-arrows spanning the box symmetrically about its centre."""
    span = S.BW / 2 - 11
    return "".join(
        S.wave_arrow(-span, span, amp=3.0, periods=1.6, head=9.5, y=y,
                     taper=0.42, cls="tex", size=3.4)
        for y in (-7, 7))


def tex_spread():
    """Hatching that fans from a point: heat diverging into more section.

    `core.hatch` rules parallel lines, which is the whole distinction being
    drawn here, so the fan is its own construction. Clipped the same way.
    """
    x0, half, n = -S.BW / 2, S.BH / 2, 9
    rules = "".join(
        f'<line x1="{x0}" y1="0" x2="{S.BW / 2}" y2="{-half + i * (S.BH / n):.1f}"/>'
        for i in range(n + 1))
    cid = S.uid("clip", S.BW, S.BH, "spread")
    return (f'<defs><clipPath id="{cid}"><rect x="{-S.BW/2}" y="{-half}" '
            f'width="{S.BW}" height="{S.BH}"/></clipPath></defs>'
            f'<g class="tex" clip-path="url(#{cid})">{rules}</g>')


def tex_pipe():
    """Two opposed arrows: vapour out along one face, condensate back along
    the other. It is what a heat pipe is, and it keeps the mechanism in the
    interior rather than reaching for a new outline."""
    span = S.BW / 2 - 10
    out = []
    for y, sign in ((-7, 1), (7, -1)):
        out.append(f'<line class="tex" x1="{-span * sign}" y1="{y}" '
                   f'x2="{(span - 11) * sign}" y2="{y}"/>')
        out.append(f'<g transform="rotate({0 if sign > 0 else 180})">'
                   + S.arrowhead(span, y if sign > 0 else -y, 6.0, 11.0)
                   + '</g>')
    return "".join(out)


def tex_contact():
    """Two solids meeting, hatched in opposing directions.

    The opposing hatch is the drafting convention for two parts meeting in
    section. Without it, contact reads as a solid block.
    """
    g = 4.5
    hw = (S.BW - g) / 2
    return (S.hatch(hw, S.BH, 45, x=-S.BW / 2, y=-S.BH / 2)
            + S.hatch(hw, S.BH, -45, x=g / 2, y=-S.BH / 2)
            + f'<rect class="gapfill" x="{-g/2}" y="{-S.BH/2}" width="{g}" height="{S.BH}"/>'
            + f'<line class="w" x1="{-g/2}" y1="{-S.BH/2}" x2="{-g/2}" y2="{S.BH/2}"/>'
            + f'<line class="w" x1="{g/2}" y1="{-S.BH/2}" x2="{g/2}" y2="{S.BH/2}"/>')


# ------------------------------------------------------------------- symbols
def g_free_node(a):
    return ('<line class="w" x1="-54" y1="0" x2="-5" y2="0"/>'
            '<line class="w" x1="5" y1="0" x2="54" y2="0"/>'
            '<circle class="node-open" cx="0" cy="0" r="5.5"/>')


def g_fixed_node(a):
    return ('<line class="w" x1="-56" y1="0" x2="0" y2="0"/>'
            '<circle class="node-open" cx="0" cy="0" r="5.5"/>'
            '<line class="w" x1="0" y1="5.5" x2="0" y2="12"/>'
            '<g transform="translate(0,12) rotate(90)">'
            + S.hatched_wall(0, 20, depth=12) + '</g>')


def g_cond(a):
    return leads(S.BW / 2) + tex_cond() + rect()


def g_conv(a):
    return leads(S.BW / 2) + tex_conv() + rect()


def g_rad(a):
    return leads(S.BW / 2) + tex_rad() + rect(dashed=True)


def g_contact(a):
    return leads(S.BW / 2) + tex_contact() + rect()


def g_cap(a):
    return ('<line class="w" x1="-40" y1="0" x2="-6" y2="0"/>'
            '<line class="w" x1="-6" y1="-15" x2="-6" y2="15"/>'
            '<line class="w" x1="6" y1="-15" x2="6" y2="15"/>'
            '<line class="w" x1="6" y1="0" x2="40" y2="0"/>')


def g_diss(a):
    return '<line class="w" x1="-32" y1="0" x2="20" y2="0"/>' + S.arrowhead(32)


def g_radin(a):
    return S.wave_arrow(-32, 32, amp=5.0, periods=2.0, head=12.0, taper=0.45)


def g_break(a):
    # g_fixed_node minus the stub, because that is the whole distinction and
    # the data pipeline has always drawn it that way. The gap is wider than a
    # fixed node's stub is long, so it cannot read as a stub that failed.
    return ('<line class="w" x1="-54" y1="0" x2="0" y2="0"/>'
            '<circle class="node-open" cx="0" cy="0" r="5.5"/>'
            '<g transform="translate(0,24) rotate(90)">'
            + S.hatched_wall(0, 22, depth=13) + '</g>')


def g_spread(a):
    return leads(S.BW / 2) + tex_spread() + rect()


def g_pipe(a):
    return leads(S.BW / 2) + tex_pipe() + rect()


def g_mixed(a):
    """No texture at all. In a vocabulary where the interior names the
    mechanism, an empty interior is not an absence — it says the mechanism is
    mixed, or deliberately unstated. A window quoted as "conduction and
    convection at 0.31 K/W" is one number for two mechanisms, and drawing it
    as `cond` names physics that is only half happening."""
    return leads(S.BW / 2) + rect()


def g_flow_branch(a):
    """Heat carried from one end to the other at a stated rate.

    Chevrons rather than a filled head, because a filled head is the mark a
    source uses to *land on* a node and this is a pass-through. Not a box:
    the interior of a box states what the heat is crossing, and here nothing
    is crossed — the medium is going. Boxes resist, arrows carry.
    """
    return ('<line class="w" x1="-40" y1="0" x2="40" y2="0"/>'
            + "".join(f'<polyline class="w" fill="none" '
                      f'points="{x-7},-10 {x+4},0 {x-7},10"/>'
                      for x in (-6, 6)))


def g_phase_node(a):
    """A node whose temperature is held by a phase change.

    Thermodynamically that is a fixed node which is not at a boundary, so it
    takes the imposed-temperature reading without the boundary wall: the
    standard constant-temperature marking, two short rules beneath.
    """
    return ('<line class="w" x1="-54" y1="0" x2="-5" y2="0"/>'
            '<line class="w" x1="5" y1="0" x2="54" y2="0"/>'
            '<circle class="node-open" cx="0" cy="0" r="5.5"/>'
            '<line class="w" x1="-13" y1="13" x2="13" y2="13"/>'
            '<line class="w" x1="-13" y1="19" x2="13" y2="19"/>')


# The three numbers `g_phase_node` draws, named so `layout` and `render` can
# be pinned against them. `render` holds its own copy for the pipeline path;
# a test asserts the two agree, which is what `g_break` needed and lacked.
PHASE_HALF, PHASE_Y1, PHASE_Y2 = 13, 13, 19


def g_branch_break(a):
    # The open circuit, which is what a mechanical connection carrying no
    # heat actually is. Not a plain wire: a wire says heat flows. Crossbars
    # far apart and short, against a capacitance's tall plates close
    # together, so the gap is what the eye lands on rather than the bars.
    return ('<line class="w" x1="-40" y1="0" x2="-12" y2="0"/>'
            '<line class="w" x1="-12" y1="-8" x2="-12" y2="8"/>'
            '<line class="w" x1="12" y1="-8" x2="12" y2="8"/>'
            '<line class="w" x1="12" y1="0" x2="40" y2="0"/>')


def g_flow(a):
    return '<line class="w" x1="-30" y1="0" x2="18" y2="0"/>' + S.arrowhead(30)


def g_flux(a):
    out = ['<line class="w" x1="-14" y1="-24" x2="-14" y2="24"/>',
           S.hatch(9, 48, 45, 6.5, x=-23, y=-24)]
    for y in (-14, 0, 14):
        out.append(f'<line class="w" x1="-14" y1="{y}" x2="16" y2="{y}"/>')
        out.append(S.arrowhead(28, y, 5.2, 10))
    return "".join(out)


def S_(base, sub=None):
    return S.sym_text(base, sub)


@dataclass(frozen=True)
class Symbol:
    """One symbol: how to draw it, and how much room it takes.

    `half` and `half_len` are how far the geometry reaches perpendicular to
    the branch and along it, and the label solver needs both. They used to
    live in a dict beside the drawing function, so placing a symbol by hand
    meant re-supplying them from memory and getting them right. They travel
    with the geometry now.

    `texture` is set only on the four box symbols, where the interior is a
    thing in its own right and can be placed without the outline.

    `reach` is the other measurement, and it is not the same one. `half` and
    `half_len` say how much room to leave a label; `reach` says how far the
    ink goes, which for six of the twelve is further. A box symbol runs LEAD
    past each end of the box, and a capacitance draws ±40 against a
    `half_len` of 15. Mid-route those leads lie over wire the canvas already
    counts, so nothing shows; at the end of a run the canvas is sized to the
    clearance box and the leads are clipped off with no warning at all.

    Set it only where the geometry exceeds the clearance. `ink` falls back,
    so the two numbers stay one measurement wherever they agree.
    """

    key: str
    name: str
    draw: Callable[[float], str]
    half: float
    half_len: float
    mirror: bool = False
    text: str = ""
    value: Optional[str] = None
    user: Optional[str] = None
    texture: Optional[Callable[[], str]] = None
    note: str = ""
    reach: Optional[Tuple[float, float]] = None

    @property
    def ink(self):
        """(along the branch, across it) — how far the geometry draws."""
        return self.reach if self.reach is not None else (self.half_len,
                                                          self.half)


# The order is the specification. At eighteen entries an arbitrary list stops
# being readable, so they are grouped by what kind of statement they make, and
# `render_demo.vocabulary` starts each group on a new row. `GROUPS` below is
# the same order, and a test pins the two to each other.
SYMBOLS = [
    # -- nodes: a place, and what holds its temperature
    Symbol(key="free", name="Free node", draw=g_free_node,
           text=S_("T", "j"), value="112 °C", user="Junction",
           half=5.5, half_len=5.5, reach=(54, 5.5),
           note="Subscript is identity here — you set it, and it defaults to a "
                "bare T. The label names the same thing in words."),
    Symbol(key="fixed", name="Fixed node", draw=g_fixed_node, mirror=True,
           text=S_("T", "amb"), value="40 °C", user="Still air",
           half=22, half_len=19, reach=(56, 24),
           note="Temperature is imposed and the wire connects to the boundary. "
                "Past vertical the symbol mirrors, so the hatch never arrives "
                "upside down."),
    Symbol(key="break", name="Thermal break", draw=g_break, mirror=True,
           text=S_("q"), value="0 W", user="Mounting standoff",
           half=22, half_len=22, reach=(54, 37),
           note="Circle, gap, wall — the fixed node without its stub. A fixed "
                "node connects to its boundary; this one does not, and the "
                "visible gap is the entire distinction."),
    Symbol(key="phase", name="Phase-change node", draw=g_phase_node,
           text=S_("T", "sat"), value="49 °C", user="Boiling surface",
           half=22, half_len=16, reach=(54, 19),
           note="Temperature held by a phase change rather than by a boundary, "
                "so it takes the imposed-temperature marking without the wall. "
                "Latent heat crosses it at no temperature drop at all, which is "
                "the whole reason a two-phase system exists. The hold lasts "
                "only while the phase change does, and the symbol does not say "
                "how long that is."),

    # -- paths: the interior states what the heat is crossing
    Symbol(key="cond", name="Conduction", draw=g_cond, texture=tex_cond,
           text=S_("R", "cond"), value="0.35 K/W", user="Die attach",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Subscript is structural and fixed. Which conduction path this "
                "is lives in your label, so nothing is named twice."),
    Symbol(key="conv", name="Convection", draw=g_conv, texture=tex_conv,
           text=S_("R", "conv"), value="1.80 K/W", user="Sink → Ambient",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Streamlines rotate with the block, since flow along the path is "
                "what they mean."),
    Symbol(key="rad", name="Radiation", draw=g_rad, texture=tex_rad,
           text=S_("R", "rad"), value="6.40 K/W", user="Case → Ambient",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Arrows now span the box symmetrically. Dashed outline marks the "
                "one path that is not linear in temperature."),
    Symbol(key="contact", name="Contact", draw=g_contact, texture=tex_contact,
           text=S_("R", "contact"), value="0.15 K/W", user="Grease",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Contact rather than TIM: the other three subscripts name "
                "mechanisms, and a TIM is a material."),

    # -- paths: shape, two-phase, unstated, and storage
    Symbol(key="spread", name="Spreading resistance", draw=g_spread,
           texture=tex_spread,
           text=S_("R", "spread"), value="0.15 K/W", user="CuW submount",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Hatching that fans from a point rather than running parallel: "
                "the cross-section grows as the heat goes. Drawn as `cond` it "
                "asserts one-dimensional conduction, which is exactly what a "
                "spreading path is not."),
    Symbol(key="pipe", name="Isothermal link", draw=g_pipe, texture=tex_pipe,
           text=S_("R", "pipe"), value="0.10 K/W", user="Heat pipe",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="Vapour out along one face, condensate back along the other. It "
                "still takes a resistance, because a heat pipe has a small one; "
                "what it stops doing is wearing solid-conduction hatching on a "
                "two-phase device."),
    Symbol(key="mixed", name="Unstated mechanism", draw=g_mixed,
           text=S_("R", "window"), value="0.31 K/W", user="Double glazing",
           half=S.BH / 2, half_len=S.BW / 2,
           reach=(S.BW / 2 + LEAD, S.BH / 2),
           note="The one kind whose mechanism the library does not know, so the "
                "subscript is yours to set. An empty interior is not an absence "
                "here: it says mixed, or deliberately unstated. A window quoted "
                "as one number for conduction and convection together is this."),
    Symbol(key="cap", name="Capacitance", draw=g_cap,
           text=S_("C", "j"), value="0.9 mJ/K", user="Die",
           half=15, half_len=15, reach=(40, 15),
           note="On a near-vertical branch the block moves to whichever side has "
                "room, and stays whole."),

    # -- paths that carry a rate, or carry nothing
    Symbol(key="flow-branch", name="Heat flow, along a path",
           draw=g_flow_branch, text=S_("q"), value="3.2 kW",
           user="Technical water", half=10, half_len=22, reach=(40, 10),
           note="Boxes resist; arrows carry. Chevrons rather than a filled head, "
                "because a filled head is the mark a source uses to land on a "
                "node and this is a pass-through. Directed — `from` and `to` are "
                "the way the heat goes — so `angle` is refused on one."),
    Symbol(key="break-branch", name="Thermal break, in line",
           draw=g_branch_break, text="", value=None, user="Nylon standoff",
           half=10, half_len=12, reach=(40, 8),
           note="An open circuit: a mechanical connection carrying no heat. A "
                "plain wire would say heat flows and a resistance would say "
                "how much, so it is neither. It names no quantity either, and "
                "the label is the user's line alone."),

    # -- sources: heat crossing into or out of one node
    Symbol(key="diss", name="Dissipation", draw=g_diss,
           text=S_("P", "d"), value="45 W", user="Switching loss",
           half=7, half_len=32,
           note="Geometry is centred on its own span, so the block sits evenly "
                "against the shaft."),
    Symbol(key="radin", name="Radiative input", draw=g_radin,
           text=S_("q", "sol"), value="3.2 W", user="Solar gain",
           half=9, half_len=32,
           note="Amplitude now ramps linearly to zero, so the shaft flattens "
                "into the head instead of easing out of it."),
    Symbol(key="flow", name="Heat flow", draw=g_flow,
           text=S_("q"), value="38 W", user=None, half=7, half_len=30,
           note="An annotation, sized to the arrow alone so the block sits close."),
    Symbol(key="flux", name="Heat flux", draw=g_flux,
           text="q″", value="1.4 W/cm²", user="Die surface",
           half=25, half_len=26, reach=(28, 24),
           note="Several arrows leaving a surface. Flux is per unit area, so it "
                "has no single line of action to borrow heat flow's symbol."),
]

# The same order, with the boundaries that make it legible. The vocabulary
# sheet starts a new row at each group; `tests/test_model.py` pins this list
# against SYMBOLS so neither can drift from the other.
GROUPS = [
    ("Nodes", ("free", "fixed", "break", "phase")),
    ("Paths: what the heat crosses",
     ("cond", "conv", "rad", "contact")),
    ("Paths: shape, phase, mechanism, storage",
     ("spread", "pipe", "mixed", "cap")),
    ("Paths that carry a rate, or carry nothing",
     ("flow-branch", "break-branch")),
    ("Sources", ("diss", "radin", "flow", "flux")),
]


def strip(sym, fluid=False):
    body = []
    for i, a in enumerate(ANGLES):
        cx, cy = CW * i + CW / 2, CH / 2 - 8
        mir = sym.mirror and S.flips(a)
        body.append(f'<g transform="{S.xf(cx, cy, a, mir)}">{sym.draw(a)}</g>')
        S.annotate(cx, cy, a, body, user=sym.user, name=sym.text,
                   value=sym.value, half=sym.half, half_len=sym.half_len)
        body.append(f'<text class="ang" x="{cx}" y="{CH-6}" '
                    f'text-anchor="middle">{a}°</text>')
        if i:
            body.append(f'<line class="tick" x1="{CW*i}" y1="10" '
                        f'x2="{CW*i}" y2="{CH-20}"/>')
    return canvas(CW * len(ANGLES), CH, "".join(body), fluid)


# One card, for the dictionary: a single symbol at 0° with its label.
#
# The width is the same for every card and the height is not, which is the
# whole trick. A card is published at width="100%", so the width alone fixes
# the scale: every glyph on the page is drawn at one size and a reader
# comparing two cards is comparing the drawings rather than two zoom levels.
# The height is then free to fit each symbol, and it should — a free node
# padded out to a thermal break's depth sits in a third of its own frame with
# nothing under it.
#
# 76 is measured, not guessed: a box symbol's leads reach 62 either side and
# the widest label is a heat pipe's at 58.
DW, DPAD = 152, 12
DCX = DW / 2


# "use the Symbol's own sample", which None cannot say: None is a real value
# for all three of these and means "draw no such line".
SAMPLE = object()


def card(sym, fluid=False, user=SAMPLE, name=SAMPLE, value=SAMPLE):
    """One symbol at 0°, labelled as the library would label it.

    Measured twice: once to find where the solver put the text, and again to
    draw it once the frame that holds both is known.

    The three text overrides are for the dictionary, where each entry carries
    a worked example and the drawing should say what the example says rather
    than repeating a sample from somewhere else. The geometry is the
    library's either way — only the words change.
    """
    user = sym.user if user is SAMPLE else user
    name = sym.text if name is SAMPLE else name
    value = sym.value if value is SAMPLE else value

    def place(cy, out):
        out.append(f'<g transform="{S.xf(DCX, cy, 0)}">{sym.draw(0)}</g>')
        return S.annotate(DCX, cy, 0, out, user=user, name=name,
                          value=value, half=sym.half,
                          half_len=sym.half_len)

    across = sym.ink[1]
    rect = place(0.0, [])
    if rect is None:
        # Nothing to say: `annotate` places no block and returns no
        # rectangle, so the frame is the ink alone. A symbol always has some.
        y0, y1 = -across, across
    else:
        _, top, _, bh = rect
        y0, y1 = min(-across, top), max(across, top + bh)
    body = []
    place(DPAD - y0, body)
    return canvas(DW, (y1 - y0) + 2 * DPAD, "".join(body), fluid)


REGION_SLOTS = ["top left", "top", "top right", "left", "centre", "right",
                "bottom left", "bottom", "bottom right"]


def region_grid(fluid=False):
    cw, ch, cols, pad = 232, 158, 3, 11
    rows = (len(REGION_SLOTS) + cols - 1) // cols
    body = []
    for i, nm in enumerate(REGION_SLOTS):
        ox, oy = (i % cols) * cw, (i // cols) * ch
        bw, bh = 176, 104
        x0, y0 = ox + (cw - bw) / 2, oy + 16
        wy = y0 + 60
        parts = nm.split()
        vert = parts[0] if parts[0] in ("top", "bottom") else "middle"
        horiz = parts[-1] if parts[-1] in ("left", "right") else "centre"
        anch = {"left": "start", "centre": "middle", "right": "end"}[horiz]
        tx = {"start": x0 + pad, "middle": x0 + bw / 2, "end": x0 + bw - pad}[anch]
        ty = {"top": y0 + pad + 9, "middle": y0 + 40, "bottom": y0 + bh - pad}[vert]
        body += [
            f'<rect class="region" x="{x0}" y="{y0}" width="{bw}" height="{bh}" rx="5"/>',
            f'<line class="w" x1="{x0+26}" y1="{wy}" x2="{x0+bw-26}" y2="{wy}"/>',
            f'<circle class="node-open" cx="{x0+42}" cy="{wy}" r="4.5"/>',
            f'<circle class="node-open" cx="{x0+bw-42}" cy="{wy}" r="4.5"/>',
            f'<text class="reg-lbl" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anch}">Heatsink</text>',
            f'<text class="ang" x="{ox+cw/2}" y="{oy+ch-12}" text-anchor="middle">{nm}</text>',
        ]
    return canvas(cw * cols, ch * rows, "".join(body), fluid)


def diagonal_demo(fluid=False):
    W, H = 800, 320
    body = []
    pts = [(80, 252), (268, 156), (452, 156), (616, 60)]
    specs = [(tex_cond(), S_("R", "cond"), "0.35 K/W", "Die attach", False),
             (tex_conv(), S_("R", "conv"), "1.80 K/W", "Radiator", False),
             (tex_rad(), S_("R", "rad"), "6.40 K/W", None, True)]
    for (x0, y0), (x1, y1), (inner, nm, val, usr, dash) in zip(pts, pts[1:], specs):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        a = math.degrees(math.atan2(y1 - y0, x1 - x0))
        L = math.hypot(x1 - x0, y1 - y0)
        geom = (f'<line class="w" x1="{-L/2}" y1="0" x2="{-S.BW/2}" y2="0"/>'
                f'<line class="w" x1="{S.BW/2}" y1="0" x2="{L/2}" y2="0"/>'
                + inner + rect(dashed=dash))
        body.append(f'<g transform="{S.xf(cx, cy, a)}">{geom}</g>')
        S.annotate(cx, cy, a, body, user=usr, name=nm, value=val,
                   half=S.BH / 2, half_len=S.BW / 2)
    labels = [(S_("T", "j"), "Junction"), (S_("T", "c"), None),
              (S_("T", "s"), None), (S_("T", "amb"), "Still air")]
    for (x, y), (n, u) in zip(pts, labels):
        body.append(f'<circle class="node-open" cx="{x}" cy="{y}" r="5.5"/>')
        S.annotate(x, y, 0, body, user=u, name=n, value=None,
                   half=5.5, half_len=5.5)
    return canvas(W, H, "".join(body), fluid)
