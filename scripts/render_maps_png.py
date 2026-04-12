#!/usr/bin/env python3
"""
Render all Catan maps as PNG images using matplotlib.
Each hex is drawn as a proper hexagon with terrain color + token + port marker.

Usage:
    python scripts/render_maps_png.py              # render all maps to /tmp/catan_maps/
    python scripts/render_maps_png.py italy        # render specific map
    python scripts/render_maps_png.py --out DIR    # custom output directory
"""

import sys
import os
import math
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import RegularPolygon, Circle
except ImportError:
    print("matplotlib not installed. Install with:")
    print("  backend/.venv/bin/pip install matplotlib")
    sys.exit(1)

from app.maps.definitions import MAP_REGISTRY


TERRAIN_COLORS = {
    "forest":    "#2d6a3e",  # dark green
    "hills":     "#a85c2f",  # brick red
    "fields":    "#e8c547",  # wheat yellow
    "pasture":   "#9bd670",  # sheep green
    "mountains": "#6c757d",  # gray
    "desert":    "#e8d8a8",  # sand
    "ocean":     "#2c7ea8",  # blue
}


def hex_center(q, r, size=1.0):
    """Flat-top hex center from axial coords."""
    x = size * 1.5 * q
    y = size * math.sqrt(3) * (q / 2 + r)
    return x, -y  # flip y so 'r positive = south' shows DOWN


def render_map(map_data, out_path, title=""):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect("equal")
    ax.set_facecolor("#1a2332")  # dark background = ocean

    size = 1.0

    # Collect centers for bounds + port lookup
    centers = {}
    for t in map_data.tiles:
        cx, cy = hex_center(t.q, t.r, size)
        centers[(t.q, t.r)] = (cx, cy)

    # Draw hex tiles
    for t in map_data.tiles:
        cx, cy = centers[(t.q, t.r)]
        color = TERRAIN_COLORS.get(t.tile_type.value, "#888888")
        hexagon = RegularPolygon(
            (cx, cy),
            numVertices=6,
            radius=size * 0.95,
            orientation=0,  # flat-top
            facecolor=color,
            edgecolor="#0d1b2a",
            linewidth=2,
        )
        ax.add_patch(hexagon)

        # Token number
        if t.token is not None:
            text_color = "#c0392b" if t.token in (6, 8) else "#1a1a1a"
            fontweight = "bold" if t.token in (6, 8) else "normal"
            ax.text(
                cx, cy,
                str(t.token),
                ha="center", va="center",
                fontsize=14,
                color=text_color,
                fontweight=fontweight,
            )
        elif t.tile_type.value == "desert":
            ax.text(cx, cy, "", ha="center", va="center")

    # Draw ports as yellow circles on their tile, with ratio text
    for p in map_data.ports:
        if (p.q, p.r) not in centers:
            continue
        cx, cy = centers[(p.q, p.r)]
        # Offset slightly toward the coast (use side if available)
        offset_x, offset_y = 0, 0
        if p.side is not None:
            # Side 0=E, going CCW (flat-top: 0=right, 1=upper-right, etc.)
            angles = [0, -60, -120, 180, 120, 60]  # degrees for each side
            angle_rad = math.radians(angles[p.side])
            offset_x = math.cos(angle_rad) * size * 0.6
            offset_y = math.sin(angle_rad) * size * 0.6

        port_circle = Circle(
            (cx + offset_x, cy + offset_y),
            radius=size * 0.25,
            facecolor="#ffd60a",
            edgecolor="#1a1a1a",
            linewidth=1.5,
            zorder=5,
        )
        ax.add_patch(port_circle)

        ratio_label = "3:1" if p.resource is None else f"2:1"
        resource_abbr = "" if p.resource is None else p.resource.value[0].upper()
        label = f"{ratio_label}{resource_abbr}" if resource_abbr else ratio_label
        ax.text(
            cx + offset_x, cy + offset_y,
            label,
            ha="center", va="center",
            fontsize=6,
            color="#0d1b2a",
            fontweight="bold",
            zorder=6,
        )

    # Set bounds
    xs = [c[0] for c in centers.values()]
    ys = [c[1] for c in centers.values()]
    pad = 2
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.axis("off")

    if title:
        ax.set_title(title, fontsize=16, color="#f8f9fa", pad=20)

    plt.tight_layout()
    fig.patch.set_facecolor("#0d1b2a")
    plt.savefig(out_path, dpi=100, bbox_inches="tight", facecolor="#0d1b2a")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("maps", nargs="*", help="Map IDs to render (default: all)")
    parser.add_argument("--out", default="/tmp/catan_maps", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    target = args.maps if args.maps else list(MAP_REGISTRY.keys())

    for map_id in target:
        if map_id not in MAP_REGISTRY:
            print(f"Unknown map: {map_id}")
            continue

        data = MAP_REGISTRY[map_id]()
        tiles = len(data.tiles)
        ports = len(data.ports)
        out_path = os.path.join(args.out, f"{map_id}.png")
        render_map(data, out_path, title=f"{map_id}  ({tiles}T/{ports}P)")
        print(f"  → {out_path}")


if __name__ == "__main__":
    main()
