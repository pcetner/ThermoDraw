"""The ThermoDraw symbol set.

Each symbol is geometry in a local frame — heat along +x, centred on the
origin — plus the metadata the label solver needs: how far the symbol
reaches perpendicular to the branch (``half``) and along it (``half_len``).
"""
import math
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


def canvas(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="100%" role="img"><style>{CSS}</style>{body}</svg>')


def leads(hb, L=LEAD):
    return (f'<line class="w" x1="{-hb-L}" y1="0" x2="{-hb}" y2="0"/>'
            f'<line class="w" x1="{hb}" y1="0" x2="{hb+L}" y2="0"/>')


def rect(dashed=False):
    d = ' stroke-dasharray="5 4"' if dashed else ""
    return (f'<rect class="sym-box" x="{-S.BW/2}" y="{-S.BH/2}" width="{S.BW}" '
            f'height="{S.BH}" rx="2"{d}/>')


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
    return leads(S.BW / 2) + S.hatch(S.BW, S.BH, 45) + rect()


def g_conv(a):
    return leads(S.BW / 2) + S.streamlines(S.BW, S.BH) + rect()


def rad_arrows():
    """Two wave-arrows spanning the box symmetrically about its centre."""
    span = S.BW / 2 - 11
    return "".join(
        S.wave_arrow(-span, span, amp=3.0, periods=1.6, head=9.5, y=y,
                     taper=0.42, cls="tex", size=3.4)
        for y in (-7, 7))


def g_rad(a):
    return leads(S.BW / 2) + rad_arrows() + rect(dashed=True)


def g_contact(a):
    g = 4.5
    hw = (S.BW - g) / 2
    return (leads(S.BW / 2)
            + S.hatch(hw, S.BH, 45, x=-S.BW / 2, y=-S.BH / 2)
            + S.hatch(hw, S.BH, -45, x=g / 2, y=-S.BH / 2)
            + f'<rect class="gapfill" x="{-g/2}" y="{-S.BH/2}" width="{g}" height="{S.BH}"/>'
            + f'<line class="w" x1="{-g/2}" y1="{-S.BH/2}" x2="{-g/2}" y2="{S.BH/2}"/>'
            + f'<line class="w" x1="{g/2}" y1="{-S.BH/2}" x2="{g/2}" y2="{S.BH/2}"/>'
            + rect())


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


SYMBOLS = [
    dict(key="free", name="Free node", g=g_free_node, mirror=False,
         text=S_("T", "j"), val="112 °C", user="Junction", half=5.5, hl=5.5,
         note="Subscript is identity here — you set it, and it defaults to a "
              "bare T. The label names the same thing in words."),
    dict(key="fixed", name="Fixed node", g=g_fixed_node, mirror=True,
         text=S_("T", "amb"), val="40 °C", user="Still air", half=22, hl=19,
         note="Temperature is imposed and the wire connects to the boundary. "
              "Past vertical the symbol mirrors, so the hatch never arrives "
              "upside down."),
    dict(key="cond", name="Conduction", g=g_cond, mirror=False,
         text=S_("R", "cond"), val="0.35 K/W", user="Die attach",
         half=S.BH / 2, hl=S.BW / 2,
         note="Subscript is structural and fixed. Which conduction path this "
              "is lives in your label, so nothing is named twice."),
    dict(key="conv", name="Convection", g=g_conv, mirror=False,
         text=S_("R", "conv"), val="1.80 K/W", user="Sink → Ambient",
         half=S.BH / 2, hl=S.BW / 2,
         note="Streamlines rotate with the block, since flow along the path is "
              "what they mean."),
    dict(key="rad", name="Radiation", g=g_rad, mirror=False,
         text=S_("R", "rad"), val="6.40 K/W", user="Case → Ambient",
         half=S.BH / 2, hl=S.BW / 2,
         note="Arrows now span the box symmetrically. Dashed outline marks the "
              "one path that is not linear in temperature."),
    dict(key="contact", name="Contact", g=g_contact, mirror=False,
         text=S_("R", "contact"), val="0.15 K/W", user="Grease",
         half=S.BH / 2, hl=S.BW / 2,
         note="Contact rather than TIM: the other three subscripts name "
              "mechanisms, and a TIM is a material."),
    dict(key="cap", name="Capacitance", g=g_cap, mirror=False,
         text=S_("C", "j"), val="0.9 mJ/K", user="Die", half=15, hl=15,
         note="On a near-vertical branch the block moves to whichever side has "
              "room, and stays whole."),
    dict(key="diss", name="Dissipation", g=g_diss, mirror=False,
         text=S_("P", "d"), val="45 W", user="Switching loss", half=7, hl=32,
         note="Geometry is centred on its own span, so the block sits evenly "
              "against the shaft."),
    dict(key="radin", name="Radiative input", g=g_radin, mirror=False,
         text=S_("q", "sol"), val="3.2 W", user="Solar gain", half=9, hl=32,
         note="Amplitude now ramps linearly to zero, so the shaft flattens "
              "into the head instead of easing out of it."),
    dict(key="break", name="Thermal break", g=g_break, mirror=True,
         text=S_("q"), val="0 W", user="Mounting standoff", half=22, hl=22,
         note="The wire stops short of the wall. A fixed node connects to its "
              "boundary; this one does not."),
    dict(key="flow", name="Heat flow", g=g_flow, mirror=False,
         text=S_("q"), val="38 W", user=None, half=7, hl=30,
         note="An annotation, sized to the arrow alone so the block sits close."),
    dict(key="flux", name="Heat flux", g=g_flux, mirror=False,
         text="q″", val="1.4 W/cm²", user="Die surface", half=25, hl=26,
         note="Several arrows leaving a surface. Flux is per unit area, so it "
              "has no single line of action to borrow heat flow's symbol."),
]


def strip(sym):
    body = []
    for i, a in enumerate(ANGLES):
        cx, cy = CW * i + CW / 2, CH / 2 - 8
        mir = sym["mirror"] and S.flips(a)
        body.append(f'<g transform="{S.xf(cx, cy, a, mir)}">{sym["g"](a)}</g>')
        S.annotate(cx, cy, a, body, user=sym["user"], name=sym["text"],
                   value=sym["val"], half=sym["half"], half_len=sym["hl"])
        body.append(f'<text class="ang" x="{cx}" y="{CH-6}" '
                    f'text-anchor="middle">{a}°</text>')
        if i:
            body.append(f'<line class="tick" x1="{CW*i}" y1="10" '
                        f'x2="{CW*i}" y2="{CH-20}"/>')
    return canvas(CW * len(ANGLES), CH, "".join(body))


REGION_SLOTS = ["top left", "top", "top right", "left", "centre", "right",
                "bottom left", "bottom", "bottom right"]


def region_grid():
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
    return canvas(cw * cols, ch * rows, "".join(body))


def diagonal_demo():
    W, H = 800, 320
    body = []
    pts = [(80, 252), (268, 156), (452, 156), (616, 60)]
    specs = [(S.hatch(S.BW, S.BH, 45), S_("R", "cond"), "0.35 K/W", "Die attach", False),
             (S.streamlines(S.BW, S.BH), S_("R", "conv"), "1.80 K/W", "Radiator", False),
             (rad_arrows(), S_("R", "rad"), "6.40 K/W", None, True)]
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
        S.annotate(x, y, 0, body, user=u, name=n, value=None, half=5.5, half_len=5.5)
    return canvas(W, H, "".join(body))
