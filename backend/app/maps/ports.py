from __future__ import annotations

from typing import Dict, Optional, Set, Tuple

from app.game.models import MapData, Port
from app.game.board import HEX_DIRECTIONS


def _axial_distance(aq: int, ar: int, bq: int, br: int) -> int:
    # cube: (q,r,s) where s=-q-r; distance = max(|dq|,|dr|,|ds|)
    dq = aq - bq
    dr = ar - br
    ds = (-aq - ar) - (-bq - br)
    return max(abs(dq), abs(dr), abs(ds))


def _snap_to_existing_tile(map_data: MapData, q: int, r: int) -> tuple[int, int]:
    coords = [(t.q, t.r) for t in map_data.tiles]
    if (q, r) in set(coords):
        return q, r
    # Choose nearest land tile.
    best = coords[0] if coords else (q, r)
    best_d = 10**9
    for tq, tr in coords:
        d = _axial_distance(q, r, tq, tr)
        if d < best_d:
            best_d = d
            best = (tq, tr)
    return best


def infer_port_side(map_data: MapData, q: int, r: int) -> int:
    """
    Infer which side of tile (q, r) faces the sea (no neighboring land tile).
    If multiple sides are exposed, pick the one most outward from the map centroid.
    """
    coords = {(t.q, t.r) for t in map_data.tiles}
    exposed: list[int] = []
    for side, (dq, dr) in enumerate(HEX_DIRECTIONS):
        if (q + dq, r + dr) not in coords:
            exposed.append(side)

    if not exposed:
        return 0
    if len(exposed) == 1:
        return exposed[0]

    # Choose the exposed side that points most "outward" relative to center.
    # Dot((dq,dr), (q,r)) with a mild axial weighting works well visually.
    best_side = exposed[0]
    best_score = float("-inf")
    for side in exposed:
        dq, dr = HEX_DIRECTIONS[side]
        score = dq * q + dr * r + 0.25 * dq * r + 0.25 * dr * q
        if score > best_score:
            best_score = score
            best_side = side
    return best_side


ConnectedSides = Dict[Tuple[int, int], Set[int]]


def _is_coastal_side_by_edges(connected_sides: Optional[ConnectedSides], q: int, r: int, side: int) -> bool:
    """
    If `connected_sides` is provided, treat an edge as coastal iff it is NOT connected.
    This makes the adjacency graph the source of truth (useful for custom assembly).
    """
    if not connected_sides:
        return False
    return (side % 6) not in connected_sides.get((q, r), set())


def is_coastal_side(map_data: MapData, q: int, r: int, side: int) -> bool:
    coords = {(t.q, t.r) for t in map_data.tiles}
    dq, dr = HEX_DIRECTIONS[side % 6]
    return (q + dq, r + dr) not in coords


def infer_port_side_from_edges(map_data: MapData, q: int, r: int, connected_sides: ConnectedSides) -> int:
    """
    Infer which side of tile (q, r) faces the sea based on explicit edge connectivity.
    Exposed side = not connected in `connected_sides`.
    """
    exposed: list[int] = []
    for side in range(6):
        if _is_coastal_side_by_edges(connected_sides, q, r, side):
            exposed.append(side)

    if not exposed:
        return 0
    if len(exposed) == 1:
        return exposed[0]

    best_side = exposed[0]
    best_score = float("-inf")
    for side in exposed:
        dq, dr = HEX_DIRECTIONS[side]
        score = dq * q + dr * r + 0.25 * dq * r + 0.25 * dr * q
        if score > best_score:
            best_score = score
            best_side = side
    return best_side


def normalize_ports_by_edges(map_data: MapData, connected_sides: ConnectedSides) -> MapData:
    """
    Ensure all ports have a `side` that points to the coast, using explicit edge
    connectivity as the source of truth (not derived from coordinates).
    """
    normalized: list[Port] = []
    for p in map_data.ports:
        q, r = _snap_to_existing_tile(map_data, p.q, p.r)

        side = getattr(p, "side", None)
        if side is None or not _is_coastal_side_by_edges(connected_sides, q, r, int(side)):
            side = infer_port_side_from_edges(map_data, q, r, connected_sides)
        normalized.append(Port(q=q, r=r, side=int(side), resource=p.resource, ratio=p.ratio))

    map_data.ports = normalized
    return map_data


def normalize_ports(map_data: MapData) -> MapData:
    """
    Ensure all ports have a `side` that points to the coast.
    Safe to call multiple times.
    """
    normalized: list[Port] = []
    for p in map_data.ports:
        # Some legacy port definitions point at a nearby coordinate that isn't an actual tile.
        # Snap them to the nearest existing land tile so the port attaches to a real edge.
        q, r = _snap_to_existing_tile(map_data, p.q, p.r)

        side = getattr(p, "side", None)
        # If side wasn't explicitly set, infer it.
        if side is None or not is_coastal_side(map_data, q, r, int(side)):
            # Force ports to be on a coastal edge (i.e., adjacent hex is water).
            side = infer_port_side(map_data, q, r)
        normalized.append(
            Port(q=q, r=r, side=int(side), resource=p.resource, ratio=p.ratio)
        )
    map_data.ports = normalized
    return map_data

