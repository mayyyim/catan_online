#!/usr/bin/env python3
"""
ASCII visualizer for Catan map definitions.
Renders each map's tile layout + port positions to help verify country shapes.

Usage:
    python scripts/visualize_maps.py                 # render all maps
    python scripts/visualize_maps.py italy japan     # render specific maps
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.maps.definitions import MAP_REGISTRY


TERRAIN_CHARS = {
    "forest":    "🌲",
    "hills":     "⛰",
    "fields":    "🌾",
    "pasture":   "🐑",
    "mountains": "⛰",
    "desert":    "🏜",
    "ocean":     "🌊",
}

TERRAIN_ASCII = {
    "forest":    "F",  # wood
    "hills":     "H",  # brick
    "fields":    "W",  # wheat
    "pasture":   "S",  # sheep
    "mountains": "M",  # ore
    "desert":    ".",
    "ocean":     "~",
}


def render_map(map_data):
    """Render a map to ASCII art using axial (q,r) → grid coords.

    For flat-top hexes, each increment of q shifts right by 3 columns
    and down/up by 1 row depending on q parity. Each increment of r
    shifts down by 2 rows.
    """
    # Scale: per-hex width = 5 cols, height = 3 rows
    COL_STEP = 5
    ROW_STEP = 3

    # Collect all (grid_row, grid_col) positions for tiles + ports
    tiles_by_pos = {}
    port_positions = set()

    for t in map_data.tiles:
        q, r = t.q, t.r
        # Flat-top axial → grid
        # x = 1.5 * q → col = q * COL_STEP (rounded nicely since 1.5*COL_STEP/1.5 = COL_STEP)
        # y = sqrt(3) * (q/2 + r) → row depends on q parity
        col = q * COL_STEP
        row = (q + 2 * r) * (ROW_STEP // 2) + (q * ROW_STEP // 2 if ROW_STEP % 2 else 0)
        # Simpler: row = q * (ROW_STEP//2) + r * ROW_STEP, but ROW_STEP=3 means half of 3 ≈ 1.5
        # Use: row = q + 2*r (each r step = 2 rows, each q step = 1 row offset for staggered)
        row = q + 2 * r
        char = TERRAIN_ASCII.get(t.tile_type.value, "?")
        tok = str(t.token) if t.token is not None else "--"
        tiles_by_pos[(row, col)] = (char, tok)

    for p in map_data.ports:
        col = p.q * COL_STEP
        row = p.q + 2 * p.r
        port_positions.add((row, col))

    if not tiles_by_pos:
        return "(empty map)"

    rows = [r for (r, c) in tiles_by_pos]
    cols = [c for (r, c) in tiles_by_pos]
    min_r, max_r = min(rows), max(rows)
    min_c, max_c = min(cols), max(cols)

    # Each hex takes 1 row on the canvas (with q creating stagger),
    # and COL_STEP horizontal chars.
    canvas_w = max_c - min_c + 6
    canvas_h = max_r - min_r + 2
    canvas = [[" "] * canvas_w for _ in range(canvas_h)]

    for (row, col), (ch, tok) in tiles_by_pos.items():
        r = row - min_r
        c = col - min_c + 1
        # Write "[Xnn]" block
        port_mark = "(" if (row, col) in port_positions else "["
        port_close = ")" if (row, col) in port_positions else "]"
        block = f"{port_mark}{ch}{tok:>2}{port_close}"
        for i, cc in enumerate(block):
            if 0 <= r < canvas_h and 0 <= c + i < canvas_w:
                canvas[r][c + i] = cc

    return "\n".join("".join(row).rstrip() for row in canvas)


def map_info(map_data):
    tile_count = len(map_data.tiles)
    port_count = len(map_data.ports)
    terrain_counts = {}
    for t in map_data.tiles:
        terrain_counts[t.tile_type.value] = terrain_counts.get(t.tile_type.value, 0) + 1

    q_min = min(t.q for t in map_data.tiles)
    q_max = max(t.q for t in map_data.tiles)
    r_min = min(t.r for t in map_data.tiles)
    r_max = max(t.r for t in map_data.tiles)

    return {
        "tiles": tile_count,
        "ports": port_count,
        "terrains": terrain_counts,
        "bounds": f"q=[{q_min}..{q_max}] r=[{r_min}..{r_max}]",
        "span_q": q_max - q_min + 1,
        "span_r": r_max - r_min + 1,
    }


def main():
    target_maps = sys.argv[1:] if len(sys.argv) > 1 else list(MAP_REGISTRY.keys())

    for map_id in target_maps:
        if map_id not in MAP_REGISTRY:
            print(f"Unknown map: {map_id}")
            continue

        data = MAP_REGISTRY[map_id]()
        info = map_info(data)
        print("=" * 70)
        print(f"  {map_id.upper()}  —  {info['tiles']} tiles, {info['ports']} ports")
        print(f"  {info['bounds']}  span q={info['span_q']}  r={info['span_r']}")
        print(f"  terrain: {info['terrains']}")
        print("-" * 70)
        print(render_map(data))
        print()

    print("=" * 70)
    print("Legend: F=forest H=hills W=fields S=pasture M=mountains .=desert")
    print("        <>=port markers")


if __name__ == "__main__":
    main()
