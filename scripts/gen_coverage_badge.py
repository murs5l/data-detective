"""Generates a flat coverage badge SVG from the coverage tool's own JSON report.

Replaces the third-party coverage-badge package, which imports pkg_resources
internally without declaring setuptools as a dependency; recent setuptools
releases (83+) removed pkg_resources entirely, breaking it outright.
"""
from __future__ import annotations

import json
import subprocess
import sys

_COLOR_THRESHOLDS = (
    (90, "#4c1"),
    (75, "#97CA00"),
    (50, "#dfb317"),
    (0, "#e05d44"),
)


def _color_for(pct: float) -> str:
    for threshold, color in _COLOR_THRESHOLDS:
        if pct >= threshold:
            return color
    return _COLOR_THRESHOLDS[-1][1]


def _coverage_percent() -> float:
    result = subprocess.run(
        ["coverage", "json", "-o", "-"],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout)
    return round(data["totals"]["percent_covered"])


def _render_svg(pct: int) -> str:
    label, value = "coverage", f"{pct}%"
    label_width, value_width = 61, 38
    total_width = label_width + value_width
    color = _color_for(pct)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20">
    <linearGradient id="b" x2="0" y2="100%">
        <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
        <stop offset="1" stop-opacity=".1"/>
    </linearGradient>
    <mask id="a">
        <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
    </mask>
    <g mask="url(#a)">
        <path fill="#555" d="M0 0h{label_width}v20H0z"/>
        <path fill="{color}" d="M{label_width} 0h{value_width}v20H{label_width}z"/>
        <path fill="url(#b)" d="M0 0h{total_width}v20H0z"/>
    </g>
    <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
        <text x="{label_width / 2}" y="15" fill="#010101" fill-opacity=".3">{label}</text>
        <text x="{label_width / 2}" y="14">{label}</text>
        <text x="{label_width + value_width / 2}" y="15" fill="#010101" fill-opacity=".3">{value}</text>
        <text x="{label_width + value_width / 2}" y="14">{value}</text>
    </g>
</svg>
"""


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gen_coverage_badge.py <output-path>", file=sys.stderr)
        return 1

    pct = _coverage_percent()
    svg = _render_svg(round(pct))
    with open(sys.argv[1], "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Saved badge ({pct}%) to {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
