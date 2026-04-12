"""
Polygon -> hex raster pipeline for Catan maps.

Given a GeoJSON-like polygon (lon/lat coordinates), produce a MapData:
  - A connected set of hex (q, r) tiles whose centers fall inside the polygon.
  - Terrain assignment biased by biome_hints.
  - Token placement respecting the no-6/8-adjacent rule.
  - Coastal ports greedily distributed around the land edge.

The runtime is stdlib-only (no shapely/geopandas). Coordinate system matches
the project convention: flat-top axial with
    x = 1.5 * q
    y = sqrt(3) * (q/2 + r)
Neighbor directions = board.HEX_DIRECTIONS.

Polygon coordinates (lon, lat) are treated as planar (lon -> x, lat -> y). That
is a cheap equirectangular projection. Good enough for a stylised game map.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

# Support both "imported as app.maps.rasterizer" (normal) and "run from scripts/"
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(_THIS_DIR) == "maps" and os.path.basename(os.path.dirname(_THIS_DIR)) == "app":
    # Imported as app.maps.rasterizer
    POLYGON_DIR = os.path.join(_THIS_DIR, "data", "polygons")
else:
    # Running from scripts/
    _BACKEND_DIR = os.path.join(_THIS_DIR, "..", "backend")
    if _BACKEND_DIR not in sys.path:
        sys.path.insert(0, _BACKEND_DIR)
    POLYGON_DIR = os.path.join(_BACKEND_DIR, "app", "maps", "data", "polygons")

from app.game.board import HEX_DIRECTIONS  # noqa: E402
from app.game.models import (  # noqa: E402
    MapData,
    Port,
    Resource,
    Tile,
    TileType,
)

HexCoord = Tuple[int, int]
Point = Tuple[float, float]


class InfeasibleMap(Exception):
    pass


# ---------------------------------------------------------------------------
# Loading & geometry primitives
# ---------------------------------------------------------------------------

def load_polygon(slug: str) -> dict:
    """Load polygon JSON and flip latitude so north is UP in hex space.

    Natural Earth stores (lon, lat). In flat-top hex rendering, higher r
    maps to higher screen y which appears LOWER on screen. So if we used
    lat directly, north (high lat) would end up at the bottom.

    We negate lat at load time so north becomes low y → low r → top of
    the rendered hex grid. This is a single source of truth for the
    orientation so all downstream stages (rasterize, shift-away, ports)
    inherit the correct N/S orientation.
    """
    path = os.path.join(POLYGON_DIR, f"{slug}.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for poly in data.get("polygons", []):
        poly["exterior"] = [[x, -y] for x, y in poly.get("exterior", [])]
        holes = poly.get("holes") or []
        poly["holes"] = [[[x, -y] for x, y in hole] for hole in holes]
    return data


def point_in_polygon(x: float, y: float, exterior: List[Point], holes: Optional[List[List[Point]]] = None) -> bool:
    """Ray-casting test. exterior/holes are lists of (lon, lat) pairs."""
    if not _ring_contains(x, y, exterior):
        return False
    for hole in holes or []:
        if _ring_contains(x, y, hole):
            return False
    return True


def _ring_contains(x: float, y: float, ring: List[Point]) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _hex_center(q: int, r: int, scale: float) -> Point:
    return (scale * 1.5 * q, scale * math.sqrt(3) * (q / 2 + r))


def _polygon_bbox(polygons: List[dict]) -> Tuple[float, float, float, float]:
    xs, ys = [], []
    for poly in polygons:
        for px, py in poly["exterior"]:
            xs.append(px)
            ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------------------
# Rasterization
# ---------------------------------------------------------------------------

def _hexes_for_scale(polygons: List[dict], scale: float, bbox: Tuple[float, float, float, float]) -> List[List[HexCoord]]:
    """Return a list of hex lists (one per polygon island) where centers land inside."""
    xmin, ymin, xmax, ymax = bbox
    # In axial flat-top, a hex center's q = x / (1.5*s). Width in q: (xmax-xmin)/(1.5*s)
    q_min = int(math.floor(xmin / (1.5 * scale))) - 2
    q_max = int(math.ceil(xmax / (1.5 * scale))) + 2
    sqrt3 = math.sqrt(3)
    results: List[List[HexCoord]] = []
    for poly in polygons:
        island: List[HexCoord] = []
        ext = poly["exterior"]
        holes = poly.get("holes") or []
        for q in range(q_min, q_max + 1):
            # r range from y bounds: y = sqrt3 * (q/2 + r) * s  ->  r = y/(sqrt3*s) - q/2
            r_lo = int(math.floor(ymin / (sqrt3 * scale) - q / 2)) - 2
            r_hi = int(math.ceil(ymax / (sqrt3 * scale) - q / 2)) + 2
            for r in range(r_lo, r_hi + 1):
                cx, cy = _hex_center(q, r, scale)
                if point_in_polygon(cx, cy, ext, holes):
                    island.append((q, r))
        results.append(island)
    return results


def _largest_connected_component(hexes: List[HexCoord]) -> List[HexCoord]:
    hex_set: Set[HexCoord] = set(hexes)
    visited: Set[HexCoord] = set()
    best: List[HexCoord] = []
    for start in hexes:
        if start in visited:
            continue
        # BFS
        comp: List[HexCoord] = []
        dq = deque([start])
        visited.add(start)
        while dq:
            q, r = dq.popleft()
            comp.append((q, r))
            for ddq, ddr in HEX_DIRECTIONS:
                nb = (q + ddq, r + ddr)
                if nb in hex_set and nb not in visited:
                    visited.add(nb)
                    dq.append(nb)
        if len(comp) > len(best):
            best = comp
    return best


def _ensure_island_min(island: List[HexCoord], polygon: dict, scale: float) -> List[HexCoord]:
    """Guarantee at least 2 connected hexes for a polygon island."""
    if len(island) >= 2:
        return island
    # Fall back to centroid-based placement.
    ext = polygon["exterior"]
    cx = sum(p[0] for p in ext) / len(ext)
    cy = sum(p[1] for p in ext) / len(ext)
    # Find closest hex to centroid.
    q_guess = round(cx / (1.5 * scale))
    best = None
    best_d = 1e18
    for dq in range(-3, 4):
        for dr in range(-3, 4):
            q = q_guess + dq
            r = round(cy / (math.sqrt(3) * scale) - q / 2) + dr
            hx, hy = _hex_center(q, r, scale)
            d = (hx - cx) ** 2 + (hy - cy) ** 2
            if d < best_d:
                best_d = d
                best = (q, r)
    q, r = best
    neighbor = (q + HEX_DIRECTIONS[0][0], r + HEX_DIRECTIONS[0][1])
    return [(q, r), neighbor]


def _remove_cross_island_adjacency(islands: List[List[HexCoord]]) -> List[List[HexCoord]]:
    """
    If two different islands contain adjacent hexes, SHIFT the smaller island
    away from the larger one until there's at least one empty hex buffer
    between them. Never erase an island — every polygon component must
    survive as a distinct cluster.
    """
    if len(islands) < 2:
        return islands

    def adjacent_pair(a: List[HexCoord], b: List[HexCoord]) -> bool:
        bset = set(b)
        for q, r in a:
            for dq, dr in HEX_DIRECTIONS:
                if (q + dq, r + dr) in bset:
                    return True
        # Also require a 1-hex buffer: if a contains b or a neighbor within 1 hex
        # of b's hexes, they're too close.
        aset = set(a)
        for q, r in b:
            for dq, dr in HEX_DIRECTIONS:
                if (q + dq, r + dr) in aset:
                    return True
        return False

    def shift(island: List[HexCoord], dq: int, dr: int) -> List[HexCoord]:
        return [(q + dq, r + dr) for q, r in island]

    # Sort by size descending; the biggest island stays fixed, others get shifted.
    order = sorted(range(len(islands)), key=lambda i: -len(islands[i]))
    anchor_idx = order[0]
    result: List[List[HexCoord]] = [None] * len(islands)  # type: ignore
    result[anchor_idx] = list(islands[anchor_idx])

    # Directions to try in order of preference (east, south, west, north, etc).
    shifts_to_try = [
        (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1),
        (2, 0), (0, 2), (-2, 0), (0, -2), (2, -1), (-2, 1),
        (3, 0), (0, 3), (-3, 0), (0, -3),
    ]

    for idx in order[1:]:
        island = list(islands[idx])
        # Keep shifting until it's not adjacent to any already-placed island.
        for _ in range(50):
            conflict = False
            for other_idx, other in enumerate(result):
                if other is None or other_idx == idx:
                    continue
                if adjacent_pair(island, other):
                    conflict = True
                    break
            if not conflict:
                break
            # Move in a progressively larger direction away from the anchor centroid.
            anchor_cx = sum(q for q, _ in result[anchor_idx]) / max(1, len(result[anchor_idx]))
            anchor_cy = sum(r for _, r in result[anchor_idx]) / max(1, len(result[anchor_idx]))
            isl_cx = sum(q for q, _ in island) / max(1, len(island))
            isl_cy = sum(r for _, r in island) / max(1, len(island))
            # Push away from anchor.
            dq = 1 if isl_cx >= anchor_cx else -1
            dr = 1 if isl_cy >= anchor_cy else -1
            island = shift(island, dq, dr)
        result[idx] = island

    return [isl for isl in result if isl]


def _polygon_area(poly: dict) -> float:
    """Approximate area by shoelace of exterior ring."""
    pts = poly["exterior"]
    if len(pts) < 3:
        return 0.0
    a = 0.0
    for i in range(len(pts)):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % len(pts)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5


def _polygon_centroid(poly: dict) -> Point:
    pts = poly["exterior"]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    return (cx, cy)


def _filter_polygons(polygons: List[dict], max_parts: int) -> List[dict]:
    """
    Keep the largest polygon as anchor, then include other parts only if they're
    geographically near it. This prevents overseas territories (French Polynesia,
    Greenland for Denmark, Falklands for UK) from blowing up the bounding box.
    """
    if not polygons:
        return polygons
    sized = sorted(polygons, key=_polygon_area, reverse=True)
    anchor = sized[0]
    ax, ay = _polygon_centroid(anchor)
    # Geographic distance budget — 25 degrees keeps Italy+Sicily+Sardinia,
    # UK+Ireland, China+Taiwan+Hainan, but drops Denmark+Greenland.
    MAX_DEGREES = 25.0
    near: List[dict] = [anchor]
    for p in sized[1:]:
        if len(near) >= max_parts:
            break
        px, py = _polygon_centroid(p)
        dist = math.hypot(px - ax, py - ay)
        if dist <= MAX_DEGREES:
            near.append(p)
    return near


def rasterize(polygon_data: dict, target_tiles: int) -> List[HexCoord]:
    polygons = polygon_data["polygons"]
    # Keep only the largest polygon parts. For standard maps allow up to 6 islands,
    # for XL allow up to 10. This prevents countries with many tiny islands
    # (UK has dozens of tiny islets, Europe has 60 countries) from blowing
    # the tile budget via _ensure_island_min fallback.
    size = polygon_data.get("size", "standard")
    max_parts = 10 if size == "xl" else 6
    polygons = _filter_polygons(polygons, max_parts)
    bbox = _polygon_bbox(polygons)
    # bbox diagonal gives initial scale estimate.
    xmin, ymin, xmax, ymax = bbox
    diag = math.hypot(xmax - xmin, ymax - ymin)
    # Binary search scale between these bounds.
    lo = diag / (40.0 * math.sqrt(max(target_tiles, 1)))
    hi = diag / 1.0
    best: Optional[List[HexCoord]] = None
    best_score = float("-inf")
    for _ in range(28):
        mid = (lo + hi) / 2
        islands = _hexes_for_scale(polygons, mid, bbox)
        # Take largest CC per island.
        processed: List[List[HexCoord]] = []
        for isl, poly in zip(islands, polygons):
            cc = _largest_connected_component(isl) if isl else []
            cc = _ensure_island_min(cc, poly, mid)
            processed.append(cc)
        processed = _remove_cross_island_adjacency(processed)
        total = sum(len(i) for i in processed)
        if total == 0:
            hi = mid
            continue
        if total > target_tiles:
            # Too many tiles -> increase scale (bigger hexes = fewer).
            lo = mid
        else:
            hi = mid
        # Remember the closest.
        score = -abs(total - target_tiles)
        if score > best_score:
            best_score = score
            best = [h for isl in processed for h in isl]
        if target_tiles * 0.9 <= total <= target_tiles * 1.1:
            break
    if not best:
        raise InfeasibleMap(f"Could not rasterize polygon to ~{target_tiles} tiles")
    # Deduplicate while preserving order (islands may have been shifted onto
    # each other by _remove_cross_island_adjacency).
    seen: Set[HexCoord] = set()
    deduped: List[HexCoord] = []
    for h in best:
        if h not in seen:
            seen.add(h)
            deduped.append(h)
    best = deduped
    # Recenter around (0, 0).
    if best:
        mean_q = round(sum(q for q, _ in best) / len(best))
        mean_r = round(sum(r for _, r in best) / len(best))
        best = [(q - mean_q, r - mean_r) for q, r in best]
    return best


# ---------------------------------------------------------------------------
# Terrain assignment
# ---------------------------------------------------------------------------

BASE_DISTRIBUTION = {
    TileType.FOREST: 4,
    TileType.HILLS: 3,
    TileType.FIELDS: 4,
    TileType.PASTURE: 4,
    TileType.MOUNTAINS: 3,
    TileType.DESERT: 1,
}
BIOME_KEYS = {
    "forest": TileType.FOREST,
    "hills": TileType.HILLS,
    "fields": TileType.FIELDS,
    "pasture": TileType.PASTURE,
    "mountains": TileType.MOUNTAINS,
}


def assign_terrain(
    hexes: List[HexCoord],
    biome_hints: Optional[Dict[str, float]],
    seed: int,
) -> Dict[HexCoord, TileType]:
    rng = random.Random(seed)
    n = len(hexes)
    # Desert count.
    desert_count = 2 if n >= 30 else 1
    non_desert = n - desert_count

    # Weight per non-desert terrain.
    base_nd_total = sum(v for k, v in BASE_DISTRIBUTION.items() if k != TileType.DESERT)
    weights: Dict[TileType, float] = {}
    for tt, base in BASE_DISTRIBUTION.items():
        if tt == TileType.DESERT:
            continue
        w = base / base_nd_total
        hint_key = next((k for k, v in BIOME_KEYS.items() if v == tt), None)
        if biome_hints and hint_key and hint_key in biome_hints:
            w = 0.5 * w + 0.5 * float(biome_hints[hint_key])
        weights[tt] = max(w, 0.01)
    # Normalize.
    s = sum(weights.values())
    for tt in weights:
        weights[tt] /= s

    # Target counts (floor + distribute remainder).
    counts: Dict[TileType, int] = {}
    fractional: List[Tuple[float, TileType]] = []
    acc = 0
    for tt, w in weights.items():
        c = int(math.floor(w * non_desert))
        counts[tt] = c
        acc += c
        fractional.append((w * non_desert - c, tt))
    remainder = non_desert - acc
    fractional.sort(reverse=True)
    i = 0
    while remainder > 0:
        counts[fractional[i % len(fractional)][1]] += 1
        remainder -= 1
        i += 1
    # Ensure each resource terrain has >= 1 so game is playable.
    for tt in [TileType.FOREST, TileType.HILLS, TileType.FIELDS, TileType.PASTURE, TileType.MOUNTAINS]:
        if counts[tt] == 0:
            # Borrow from largest.
            donor = max(counts, key=lambda k: counts[k])
            if counts[donor] > 1:
                counts[donor] -= 1
                counts[tt] += 1
    counts[TileType.DESERT] = desert_count

    # Build bag with deserts FIRST so they are never trimmed.
    bag: List[TileType] = [TileType.DESERT] * desert_count
    for tt, c in counts.items():
        if tt == TileType.DESERT:
            continue
        bag.extend([tt] * c)
    # Pad with fields if short.
    while len(bag) < n:
        bag.append(TileType.FIELDS)
    # Trim from the end (which now drops excess resource tiles, never desert).
    bag = bag[:n]
    assert bag.count(TileType.DESERT) == desert_count, (
        f"desert count mismatch: expected {desert_count}, got {bag.count(TileType.DESERT)}"
    )
    rng.shuffle(bag)
    return {h: t for h, t in zip(hexes, bag)}


# ---------------------------------------------------------------------------
# Token placement
# ---------------------------------------------------------------------------

BASE_TOKEN_BAG = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]


def _scale_token_bag(n_needed: int) -> List[int]:
    if n_needed <= len(BASE_TOKEN_BAG):
        return BASE_TOKEN_BAG[:n_needed]
    bag = list(BASE_TOKEN_BAG)
    extra_pool = [3, 4, 5, 9, 10, 11, 6, 8]
    i = 0
    while len(bag) < n_needed:
        bag.append(extra_pool[i % len(extra_pool)])
        i += 1
    return bag


def place_tokens(
    land_hexes: List[HexCoord],
    desert_hexes: Set[HexCoord],
    seed: int,
) -> Dict[HexCoord, int]:
    rng = random.Random(seed + 17)
    targets = [h for h in land_hexes if h not in desert_hexes]
    n = len(targets)
    bag = _scale_token_bag(n)

    neighbors: Dict[HexCoord, List[HexCoord]] = {
        h: [(h[0] + dq, h[1] + dr) for dq, dr in HEX_DIRECTIONS] for h in targets
    }
    target_set = set(targets)

    for attempt in range(100):
        shuffled = bag[:]
        rng.shuffle(shuffled)
        order = targets[:]
        rng.shuffle(order)
        assignment: Dict[HexCoord, int] = {}

        def backtrack(i: int) -> bool:
            if i == len(order):
                return True
            h = order[i]
            # Try each remaining token slot.
            used = set()
            for j, tok in enumerate(shuffled):
                if j in used_slots or tok in used:
                    continue
                used.add(tok)
                if tok in (6, 8):
                    bad = False
                    for nb in neighbors[h]:
                        if nb in assignment and assignment[nb] in (6, 8):
                            bad = True
                            break
                    if bad:
                        continue
                assignment[h] = tok
                used_slots.add(j)
                if backtrack(i + 1):
                    return True
                del assignment[h]
                used_slots.discard(j)
            return False

        used_slots: Set[int] = set()
        if backtrack(0):
            return assignment
    raise InfeasibleMap("Could not place tokens without adjacent 6/8")


# ---------------------------------------------------------------------------
# Port detection
# ---------------------------------------------------------------------------

def _edge_distance(a: Tuple[HexCoord, int], b: Tuple[HexCoord, int]) -> int:
    """Rough hex edge distance via axial."""
    (aq, ar), as_ = a[0], a[1]
    (bq, br), bs = b[0], b[1]
    dq = aq - bq
    dr = ar - br
    ds = (-aq - ar) - (-bq - br)
    hex_d = (abs(dq) + abs(dr) + abs(ds)) // 2
    return hex_d + (0 if as_ == bs else 1)


PORT_RESOURCES = [Resource.WOOD, Resource.BRICK, Resource.SHEEP, Resource.WHEAT, Resource.ORE]


def detect_ports(land_hexes: List[HexCoord], seed: int) -> List[Port]:
    rng = random.Random(seed + 31)
    land_set = set(land_hexes)
    coastal: List[Tuple[HexCoord, int]] = []
    for h in land_hexes:
        for side, (dq, dr) in enumerate(HEX_DIRECTIONS):
            if (h[0] + dq, h[1] + dr) not in land_set:
                coastal.append((h, side))
    if not coastal:
        return []
    rng.shuffle(coastal)

    target = max(4, min(15, round(len(land_hexes) * 0.35)))
    chosen: List[Tuple[HexCoord, int]] = []
    for cand in coastal:
        if len(chosen) >= target:
            break
        if all(_edge_distance(cand, c) >= 2 for c in chosen):
            chosen.append(cand)

    # Assign port types: 1x each specific 2:1, rest 3:1.
    types: List[Tuple[Optional[Resource], int]] = []
    for res in PORT_RESOURCES:
        types.append((res, 2))
    while len(types) < len(chosen):
        types.append((None, 3))
    types = types[: len(chosen)]
    rng.shuffle(types)

    ports: List[Port] = []
    for (h, side), (res, ratio) in zip(chosen, types):
        ports.append(Port(q=h[0], r=h[1], resource=res, ratio=ratio, side=side))
    return ports


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def build_map(slug: str, seed: Optional[int] = None) -> MapData:
    data = load_polygon(slug)
    if seed is None:
        seed = sum(ord(c) for c in data.get("slug", slug)) * 101
    size = data.get("size", "standard")
    target = 37 if size == "xl" else 19
    hexes = rasterize(data, target)
    terrain = assign_terrain(hexes, data.get("biome_hints"), seed)
    desert_hexes = {h for h, t in terrain.items() if t == TileType.DESERT}
    tokens = place_tokens(hexes, desert_hexes, seed)
    ports = detect_ports(hexes, seed)

    tiles: List[Tile] = []
    for h in hexes:
        tt = terrain[h]
        tok = tokens.get(h)
        tiles.append(Tile(q=h[0], r=h[1], tile_type=tt, token=tok))
    return MapData(map_id=data.get("slug", slug), tiles=tiles, ports=ports)
