#!/usr/bin/env python3
"""CT demo line chart: A, B + three C finals genomes (from demo_pack)."""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "factory" / "fixtures" / "demo_pack.json"
OUT = ROOT / "docs" / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def mean_sd(xs: list[float]) -> tuple[float, float]:
    m = statistics.mean(xs)
    s = statistics.stdev(xs) if len(xs) >= 2 else 0.0
    return m, s


def y_of(score: float, top: float, bottom: float, y0: float, y1: float) -> float:
    return y1 - (score - bottom) / (top - bottom) * (y1 - y0)


def main() -> None:
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    marks = pack.get("marks") or {}
    winner = marks.get("balanced")

    # English display names (chart is English-only)
    EN = {
        "A": "A · floor",
        "B": "B · leak ceiling",
        "var.balanced_philosopher": "C1 · balanced philosopher",
        "var.pragmatic_mentor": "C2 · pragmatic mentor",
        "var.eastwest_sage": "C3 · east-west sage",
    }

    series: list[tuple[str, str, list[float], str, str, bool]] = [
        ("A", EN["A"], pack["baseline_scores"]["A"], "#57534E", "circle", False),
        ("B", EN["B"], pack["baseline_scores"]["B"], "#C2410C", "diamond", False),
    ]
    c_palette = [
        ("#0F766E", "square"),
        ("#2563EB", "circle"),
        ("#7C3AED", "diamond"),
    ]
    for i, vid in enumerate(pack.get("pool") or []):
        color, shape = c_palette[i % len(c_palette)]
        short = EN.get(vid, vid).split(" · ", 1)[-1] if vid in EN else vid
        name = f"C{i+1} · {short}"
        series.append((vid, name, pack["champ_scores"][vid], color, shape, vid == winner))

    w, h = 980, 540
    x0, x1 = 72, 720
    y0, y1 = 96, 420
    bottom, top = 60, 100
    n = 5

    def X(t: int) -> float:
        return x0 + (t - 1) * (x1 - x0) / (n - 1)

    def Y(s: float) -> float:
        return y_of(s, top, bottom, y0, y1)

    out: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">',
        "<title>Critical thinking · A / B / three C finals</title>",
        "<defs>",
        '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">',
        '<stop offset="0%" stop-color="#FFFBF5"/>',
        '<stop offset="100%" stop-color="#F5F0E8"/>',
        "</linearGradient>",
        "</defs>",
        '<rect width="100%" height="100%" fill="url(#bg)"/>',
        '<text x="36" y="40" fill="#1C1917" font-family="ui-sans-serif,system-ui,sans-serif" font-size="22" font-weight="700">Critical thinking · A / B / C×3</text>',
        '<text x="36" y="64" fill="#78716C" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">5 trials each · A floor · B criteria leak · three genome finals (★★★ = perf / stable / balanced)</text>',
        f'<rect x="{x0-16}" y="{y0-16}" width="{x1-x0+32}" height="{y1-y0+32}" rx="14" fill="#FFFCFA" stroke="#E7E5E4"/>',
    ]

    for s in range(60, 101, 5):
        y = Y(s)
        major = s % 10 == 0
        out.append(
            f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{"#D6D3D1" if major else "#F5F5F4"}" stroke-width="1"/>'
        )
        if major:
            out.append(
                f'<text x="{x0-10}" y="{y+4:.1f}" text-anchor="end" fill="#57534E" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">{s}</text>'
            )

    y90 = Y(90)
    out.append(
        f'<line x1="{x0}" y1="{y90:.1f}" x2="{x1}" y2="{y90:.1f}" stroke="#A8A29E" stroke-width="1.3" stroke-dasharray="2 4"/>'
    )
    out.append(
        f'<text x="{x0+6}" y="{y90-6:.1f}" fill="#A8A29E" font-family="ui-sans-serif,system-ui,sans-serif" font-size="11">90</text>'
    )

    for t in range(1, n + 1):
        x = X(t)
        out.append(f'<line x1="{x:.1f}" y1="{y1}" x2="{x:.1f}" y2="{y1+6}" stroke="#A8A29E"/>')
        out.append(
            f'<text x="{x:.1f}" y="{y1+24}" text-anchor="middle" fill="#57534E" font-family="ui-sans-serif,system-ui,sans-serif" font-size="13">#{t}</text>'
        )

    # lines: A/B thicker; C genomes slightly thinner except winner
    for key, _label, vals, color, shape, is_win in series:
        is_ab = key in ("A", "B")
        lw = 3.4 if is_ab or is_win else 2.4
        opacity = 1.0 if is_ab or is_win else 0.85
        pts = []
        for t, v in enumerate(vals, start=1):
            pts.append(f"{X(t):.1f},{Y(v):.1f}")
        out.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="{lw}" stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}" points="{" ".join(pts)}"/>'
        )
        for t, v in enumerate(vals, start=1):
            x, y = X(t), Y(v)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="#FFFCFA" opacity="{opacity}"/>')
            if shape == "circle":
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color}" opacity="{opacity}"/>')
            elif shape == "square":
                out.append(
                    f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" rx="1.5" fill="{color}" opacity="{opacity}"/>'
                )
            else:
                out.append(
                    f'<polygon points="{x:.1f},{y-5.5:.1f} {x+5.5:.1f},{y:.1f} {x:.1f},{y+5.5:.1f} {x-5.5:.1f},{y:.1f}" fill="{color}" opacity="{opacity}"/>'
                )

    # legend panel
    px, py = 748, 80
    out.append(f'<rect x="{px}" y="{py}" width="208" height="360" rx="14" fill="#FFFCFA" stroke="#E7E5E4"/>')
    out.append(
        f'<text x="{px+16}" y="{py+28}" fill="#78716C" font-family="ui-sans-serif,system-ui,sans-serif" font-size="11" font-weight="600">LEGEND</text>'
    )
    row = py + 52
    for key, label, vals, color, _shape, is_win in series:
        m, sd = mean_sd(vals)
        stars = " ★★★" if is_win else ""
        out.append(f'<line x1="{px+16}" y1="{row}" x2="{px+44}" y2="{row}" stroke="{color}" stroke-width="3"/>')
        out.append(f'<circle cx="{px+30}" cy="{row}" r="4" fill="{color}"/>')
        out.append(
            f'<text x="{px+54}" y="{row+4}" fill="#1C1917" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12" font-weight="600">{escape(label)}</text>'
        )
        out.append(
            f'<text x="{px+54}" y="{row+22}" fill="#57534E" font-family="ui-sans-serif,system-ui,sans-serif" font-size="12">{m:.1f} ± {sd:.2f}{stars}</text>'
        )
        row += 56

    a_m = mean_sd(series[0][2])[0]
    b_m = mean_sd(series[1][2])[0]
    c_m = mean_sd(next(s[2] for s in series if s[5]))[0]
    out.append(
        f'<text x="36" y="510" fill="#44403C" font-family="ui-sans-serif,system-ui,sans-serif" font-size="14">'
        f'<tspan font-weight="700" fill="#C2410C">B−A = +{b_m-a_m:.1f}</tspan>'
        f'<tspan fill="#A8A29E">  ·  </tspan>'
        f'<tspan font-weight="700" fill="#0F766E">C★−A = +{c_m-a_m:.1f}</tspan>'
        f'<tspan fill="#78716C">  ·  three genomes in finals, one champion</tspan>'
        f"</text>"
    )
    out.append("</svg>")

    path = OUT / "demo_ct_abc_trials.svg"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote", path)
    for _key, label, vals, _c, _s, is_win in series:
        m, sd = mean_sd(vals)
        stars = " ★★★" if is_win else ""
        print(f"  {label}: {m:.2f}±{sd:.2f}{stars}  {vals}")


if __name__ == "__main__":
    main()
