"""The ThermoDraw symbol set.

Each symbol is geometry in a local frame — heat along +x, centred on the
origin — plus the metadata the label solver needs: how far the symbol
reaches perpendicular to the branch (``half``) and along it (``half_len``).
"""
import math
from dataclasses import dataclass
from typing import Callable, Optional

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
    return ('<line class="w" x1="-54" y1="0" x2="-12" y2="0"/>'
            '<line class="w" x1="-12" y1="-7" x2="-12" y2="7"/>'
            + S.hatched_wall(0, 22, depth=13))


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


SYMBOLS = [
    Symbol(key="free", name="Free node", draw=g_free_node,
           text=S_("T", "j"), value="112 °C", user="Junction",
           half=5.5, half_len=5.5,
           note="Subscript is identity here — you set it, and it defaults to a "
                "bare T. The label names the same thing in words."),
    Symbol(key="fixed", name="Fixed node", draw=g_fixed_node, mirror=True,
           text=S_("T", "amb"), value="40 °C", user="Still air",
           half=22, half_len=19,
           note="Temperature is imposed and the wire connects to the boundary. "
                "Past vertical the symbol mirrors, so the hatch never arrives "
                "upside down."),
    Symbol(key="cond", name="Conduction", draw=g_cond, texture=tex_cond,
           text=S_("R", "cond"), value="0.35 K/W", user="Die attach",
           half=S.BH / 2, half_len=S.BW / 2,
           note="Subscript is structural and fixed. Which conduction path this "
                "is lives in your label, so nothing is named twice."),
    Symbol(key="conv", name="Convection", draw=g_conv, texture=tex_conv,
           text=S_("R", "conv"), value="1.80 K/W", user="Sink → Ambient",
           half=S.BH / 2, half_len=S.BW / 2,
           note="Streamlines rotate with the block, since flow along the path is "
                "what they mean."),
    Symbol(key="rad", name="Radiation", draw=g_rad, texture=tex_rad,
           text=S_("R", "rad"), value="6.40 K/W", user="Case → Ambient",
           half=S.BH / 2, half_len=S.BW / 2,
           note="Arrows now span the box symmetrically. Dashed outline marks the "
                "one path that is not linear in temperature."),
    Symbol(key="contact", name="Contact", draw=g_contact, texture=tex_contact,
           text=S_("R", "contact"), value="0.15 K/W", user="Grease",
           half=S.BH / 2, half_len=S.BW / 2,
           note="Contact rather than TIM: the other three subscripts name "
                "mechanisms, and a TIM is a material."),
    Symbol(key="cap", name="Capacitance", draw=g_cap,
           text=S_("C", "j"), value="0.9 mJ/K", user="Die",
           half=15, half_len=15,
           note="On a near-vertical branch the block moves to whichever side has "
                "room, and stays whole."),
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
    Symbol(key="break", name="Thermal break", draw=g_break, mirror=True,
           text=S_("q"), value="0 W", user="Mounting standoff",
           half=22, half_len=22,
           note="The wire stops short of the wall. A fixed node connects to its "
                "boundary; this one does not."),
    Symbol(key="flow", name="Heat flow", draw=g_flow,
           text=S_("q"), value="38 W", user=None, half=7, half_len=30,
           note="An annotation, sized to the arrow alone so the block sits close."),
    Symbol(key="flux", name="Heat flux", draw=g_flux,
           text="q″", value="1.4 W/cm²", user="Die surface",
           half=25, half_len=26,
           note="Several arrows leaving a surface. Flux is per unit area, so it "
                "has no single line of action to borrow heat flow's symbol."),
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
