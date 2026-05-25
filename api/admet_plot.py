"""BOILED-Egg + Bioavailability Radar SVG plot generators for ADME visualization."""
import math
from typing import Dict, List


def boiled_egg_svg(molecules: List[Dict]) -> str:
    """Generate BOILED-Egg plot as inline SVG.

    molecules: [{"wlogp": float, "tpsa": float, "pgp_substrate": bool, "label": str}, ...]
    """
    w, h = 480, 420
    m = 60

    def x(t):
        return m + (t / 300) * (w - 2 * m)

    def y(lg):
        return h - m - ((lg + 3) / 10) * (h - 2 * m)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        f'<rect width="{w}" height="{h}" fill="none"/>',
    ]

    # White ellipse (GI zone) — polygon approximation
    wpts = []
    for lg in [-3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7]:
        lo = max(0, 12.5 * lg - 25)
        hi = min(300, 300 - 12.5 * lg)
        if lo < hi:
            wpts.insert(0, f"{x(hi)},{y(lg)}")
            wpts.append(f"{x(lo)},{y(lg)}")
    if wpts:
        parts.append(
            f'<polygon points="{" ".join(wpts)}" fill="rgba(180,210,255,0.15)" stroke="rgba(180,210,255,0.35)" stroke-width="1.5" stroke-dasharray="5,3"/>'
        )

    # Yolk ellipse (BBB zone)
    ypts = []
    for lg in [-2, -1, 0, 1, 2, 3, 4]:
        lo = max(0, 5 * lg - 15)
        hi = min(300, 200 - 8 * lg)
        if lo < hi:
            ypts.insert(0, f"{x(hi)},{y(lg)}")
            ypts.append(f"{x(lo)},{y(lg)}")
    if ypts:
        parts.append(
            f'<polygon points="{" ".join(ypts)}" fill="rgba(255,210,100,0.15)" stroke="rgba(255,210,100,0.35)" stroke-width="1.5" stroke-dasharray="5,3"/>'
        )

    # Axes
    parts.extend(
        [
            f'<line x1="{m}" y1="{y(-3)}" x2="{m}" y2="{y(7)}" stroke="#555" stroke-width="1"/>',
            f'<line x1="{x(0)}" y1="{y(-3)}" x2="{x(300)}" y2="{y(-3)}" stroke="#555" stroke-width="1"/>',
            f'<text x="{x(150)}" y="{h-10}" text-anchor="middle" fill="#888" font-family="sans-serif" font-size="11">TPSA (Å²)</text>',
            f'<text x="16" y="{y(2)}" text-anchor="middle" fill="#888" font-family="sans-serif" font-size="11" transform="rotate(-90,16,{y(2)})">WLOGP</text>',
        ]
    )

    # Molecules
    for mol in molecules:
        px, py = x(mol["tpsa"]), y(mol["wlogp"])
        color = "#4fc3f7" if mol.get("pgp_substrate") else "#ef5350"
        stroke = "#0288d1" if mol.get("pgp_substrate") else "#c62828"
        parts.append(
            f'<circle cx="{px}" cy="{py}" r="6" fill="{color}" stroke="{stroke}" stroke-width="1.5"/>'
        )
        if mol.get("label"):
            parts.append(
                f'<text x="{px+9}" y="{py+4}" fill="#ccc" font-family="sans-serif" font-size="9">{mol["label"]}</text>'
            )

    # Legend
    lx, ly = w - 160, 40
    parts.extend(
        [
            f'<rect x="{lx}" y="{ly}" width="148" height="58" rx="6" fill="rgba(16,16,24,0.92)" stroke="#444" stroke-width="1"/>',
            f'<circle cx="{lx+14}" cy="{ly+18}" r="5" fill="#4fc3f7" stroke="#0288d1" stroke-width="1"/>',
            f'<text x="{lx+24}" y="{ly+22}" fill="#aaa" font-family="sans-serif" font-size="10">PGP+ (substrate)</text>',
            f'<circle cx="{lx+14}" cy="{ly+40}" r="5" fill="#ef5350" stroke="#c62828" stroke-width="1"/>',
            f'<text x="{lx+24}" y="{ly+44}" fill="#aaa" font-family="sans-serif" font-size="10">PGP- (non-substrate)</text>',
        ]
    )

    parts.append("</svg>")
    return "\n".join(parts)


def bioavailability_radar_svg(result: Dict) -> str:
    """Generate Bioavailability Radar as inline SVG spider chart.

    result: dict from compute_swiss_adme
    """
    w, h = 360, 360
    cx, cy = w // 2, h // 2
    r = 125

    phys = result.get("physicochemical", {})
    lipo = result.get("lipophilicity", {})
    sol = result.get("solubility", {})

    clp = lipo.get("consensus_logp", 0)
    mw_val = phys.get("mw", 300)
    tpsa = phys.get("tpsa", 100)
    esol = sol.get("esol_logs", -5)
    fcsp3 = phys.get("fraction_csp3", 0.3)
    rot = phys.get("rotatable_bonds", 5)

    # Normalize to 0-1 (optimal = 1)
    values = {
        "LIPO": min(1.0, max(0.0, 1 - abs(clp - 3) / 5)),
        "SIZE": min(1.0, max(0.0, 1 - abs(mw_val - 350) / 500)),
        "POLAR": min(1.0, max(0.0, 1 - tpsa / 200)),
        "INSOLU": min(1.0, max(0.0, (esol + 10) / 10)),
        "INSATU": min(1.0, max(0.0, fcsp3 * 3)),
        "FLEX": min(1.0, max(0.0, 1 - rot / 15)),
    }

    axes = [
        ("LIPO", -90),
        ("SIZE", -30),
        ("POLAR", 30),
        ("INSOLU", 90),
        ("INSATU", 150),
        ("FLEX", 210),
    ]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
        f'<rect width="{w}" height="{h}" fill="none"/>',
    ]

    # Grid rings
    for level in [0.2, 0.4, 0.6, 0.8, 1.0]:
        lr = r * level
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{lr}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="0.5"/>'
        )

    # Axis lines + labels
    for label, angle in axes:
        rad = math.radians(angle)
        ex = cx + r * math.cos(rad)
        ey = cy - r * math.sin(rad)
        parts.append(
            f'<line x1="{cx}" y1="{cy}" x2="{ex}" y2="{ey}" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>'
        )
        lx = cx + r * 1.16 * math.cos(rad)
        ly = cy - r * 1.16 * math.sin(rad)
        dy = "4" if 60 < abs(angle) < 120 else ("-4" if abs(angle) < 30 or abs(angle) > 150 else "0")
        parts.append(
            f'<text x="{lx}" y="{ly}" dy="{dy}" text-anchor="middle" fill="#888" font-family="sans-serif" font-size="10">{label}</text>'
        )

    # Data polygon + dots
    pts = []
    for label, angle in axes:
        v = max(0.02, values.get(label, 0))
        rad = math.radians(angle)
        px = cx + r * v * math.cos(rad)
        py = cy - r * v * math.sin(rad)
        pts.append(f"{px},{py}")
        parts.append(f'<circle cx="{px}" cy="{py}" r="3" fill="#4fc3f7" stroke="#fff" stroke-width="1"/>')

    parts.append(
        f'<polygon points="{" ".join(pts)}" fill="rgba(79,195,247,0.2)" stroke="#4fc3f7" stroke-width="2"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
