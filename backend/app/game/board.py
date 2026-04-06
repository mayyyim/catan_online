"""
Board geometry helpers for Catan axial-coordinate hex grid.

Axial coordinates (q, r):
  - Each hex has 6 neighbors
  - Each hex has 6 vertices (corners) and 6 edges (sides)

Vertex (corner) canonical form:
  Each vertex is shared by up to 3 tiles.  We pick the canonical owner tile
  using the smallest (q, r, corner_index) representation so the same physical
  vertex always maps to one key.

Edge (side) canonical form:
  Each edge is shared by 2 tiles.  Same canonical approach.
"""

from typing import List, Set, Tuple, Dict

from app.game.models import (
    GameState, PlacedPiece, PieceType,
    VertexKey, EdgeKey, MapData,
)


# ---------------------------------------------------------------------------
# Axial hex neighbor directions
# ---------------------------------------------------------------------------

HEX_DIRECTIONS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1),
]


def hex_neighbors(q: int, r: int) -> List[Tuple[int, int]]:
    return [(q + dq, r + dr) for dq, dr in HEX_DIRECTIONS]


# ---------------------------------------------------------------------------
# Vertex / Corner geometry
#
# For a hex at (q, r), the 6 corners are numbered 0-5 going clockwise from top.
# Each corner is also a corner of up to 2 neighboring hexes.
# We represent a corner by the canonical tile + index such that (q, r) is the
# lexicographically smallest tile that owns it.
#
# Corner sharing: corner i of (q, r) == corner (i+2)%6 of neighbor[i-1]
#                                      == corner (i+4)%6 of neighbor[i]
# (standard axial corner sharing rules)
# ---------------------------------------------------------------------------

# For each corner index 0-5, the two neighboring (dq, dr, shared_corner) pairs
CORNER_NEIGHBORS: Dict[int, List[Tuple[int, int, int]]] = {
    0: [(0, -1, 4), (1, -1, 2)],
    1: [(1, -1, 3), (1, 0, 5)],
    2: [(1, 0, 4), (0, 1, 0)],
    3: [(0, 1, 5), (-1, 1, 1)],
    4: [(-1, 1, 0), (-1, 0, 2)],
    5: [(-1, 0, 3), (0, -1, 1)],
}


def canonical_vertex(q: int, r: int, corner: int) -> VertexKey:
    """Return the canonical (q, r, corner) representation of a vertex."""
    candidates = [(q, r, corner)]
    for dq, dr, shared_corner in CORNER_NEIGHBORS[corner]:
        candidates.append((q + dq, r + dr, shared_corner))
    return min(candidates)


# ---------------------------------------------------------------------------
# Edge geometry
#
# Each edge (side) is shared between 2 tiles.
# Side i of (q, r) == side (i+3)%6 of neighbor[i].
# ---------------------------------------------------------------------------

def canonical_edge(q: int, r: int, side: int) -> EdgeKey:
    dq, dr = HEX_DIRECTIONS[side]
    neighbor = (q + dq, r + dr, (side + 3) % 6)
    return min((q, r, side), neighbor)


# ---------------------------------------------------------------------------
# Adjacency helpers
# ---------------------------------------------------------------------------

def vertices_of_tile(q: int, r: int) -> List[VertexKey]:
    """All 6 canonical vertices of a tile."""
    return [canonical_vertex(q, r, c) for c in range(6)]


def edges_of_tile(q: int, r: int) -> List[EdgeKey]:
    return [canonical_edge(q, r, s) for s in range(6)]


def edges_of_vertex(vk: VertexKey) -> List[EdgeKey]:
    """The 3 edges adjacent to a vertex."""
    q, r, corner = vk
    # The 3 edges touching corner i are sides (i-1)%6, i, (i+1)%6 of the tile…
    # actually each corner touches edges of potentially different tiles.
    # Easier: derive from the 3 tiles that share this corner.
    tiles = tiles_of_vertex(vk)
    edge_set: Set[EdgeKey] = set()
    for tq, tr in tiles:
        for s in range(6):
            ek = canonical_edge(tq, tr, s)
            # edge is adjacent to vertex if vertex is an endpoint of edge
            if vk in vertices_of_edge(ek):
                edge_set.add(ek)
    return list(edge_set)


def vertices_of_edge(ek: EdgeKey) -> List[VertexKey]:
    """Return the 2 endpoint vertices of an edge."""
    q, r, side = ek
    c1 = side
    c2 = (side + 1) % 6
    return [canonical_vertex(q, r, c1), canonical_vertex(q, r, c2)]


def tiles_of_vertex(vk: VertexKey) -> List[Tuple[int, int]]:
    """All tiles (up to 3) that share a vertex."""
    q, r, corner = vk
    tiles = [(q, r)]
    for dq, dr, _ in CORNER_NEIGHBORS[corner]:
        tiles.append((q + dq, r + dr))
    return tiles


def adjacent_vertices(vk: VertexKey) -> List[VertexKey]:
    """Vertices connected to this vertex by one edge."""
    result = []
    for ek in edges_of_vertex(vk):
        for v in vertices_of_edge(ek):
            if v != vk:
                result.append(v)
    return result


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def land_tiles(map_data: MapData):
    from app.game.models import TileType
    return {(t.q, t.r) for t in map_data.tiles if t.tile_type not in (TileType.OCEAN,)}


def valid_vertices(map_data: MapData) -> Set[VertexKey]:
    """All vertices that touch at least one land tile."""
    lt = land_tiles(map_data)
    result: Set[VertexKey] = set()
    for (q, r) in lt:
        for c in range(6):
            result.add(canonical_vertex(q, r, c))
    return result


def valid_edges(map_data: MapData) -> Set[EdgeKey]:
    """All edges that touch at least one land tile."""
    lt = land_tiles(map_data)
    result: Set[EdgeKey] = set()
    for (q, r) in lt:
        for s in range(6):
            result.add(canonical_edge(q, r, s))
    return result


def can_place_settlement(
    vk: VertexKey,
    player_id: str,
    game: GameState,
    setup_phase: bool = False,
) -> Tuple[bool, str]:
    """Check if player can place a settlement at vertex vk."""
    vkey = f"{vk[0]},{vk[1]},{vk[2]}"

    # Must be on valid vertex
    if vk not in valid_vertices(game.map_data):
        return False, "Not a valid land vertex"

    # Vertex must be empty
    if vkey in game.vertices:
        return False, "Vertex already occupied"

    # Distance rule: no adjacent vertex can have a settlement/city
    for adj in adjacent_vertices(vk):
        adj_key = f"{adj[0]},{adj[1]},{adj[2]}"
        if adj_key in game.vertices:
            return False, "Too close to another settlement (distance rule)"

    # Outside setup: must be connected to player's road
    if not setup_phase:
        adj_edges = edges_of_vertex(vk)
        connected = any(
            f"{e[0]},{e[1]},{e[2]}" in game.edges
            and game.edges[f"{e[0]},{e[1]},{e[2]}"].player_id == player_id
            for e in adj_edges
        )
        if not connected:
            return False, "Settlement must connect to your road"

    return True, "ok"


def can_place_road(
    ek: EdgeKey,
    player_id: str,
    game: GameState,
    setup_phase: bool = False,
    setup_settlement_vk: VertexKey = None,
) -> Tuple[bool, str]:
    """Check if player can place a road at edge ek."""
    ekey = f"{ek[0]},{ek[1]},{ek[2]}"

    if ek not in valid_edges(game.map_data):
        return False, "Not a valid land edge"

    if ekey in game.edges:
        return False, "Edge already occupied"

    # Must connect to player's existing road or settlement
    endpoints = vertices_of_edge(ek)

    if setup_phase and setup_settlement_vk is not None:
        # During setup, road must connect to the just-placed settlement
        if setup_settlement_vk not in endpoints:
            return False, "Setup road must connect to your new settlement"
        return True, "ok"

    for vk in endpoints:
        vkey = f"{vk[0]},{vk[1]},{vk[2]}"
        piece = game.vertices.get(vkey)
        if piece and piece.player_id == player_id:
            return True, "ok"
        # connected via another road
        for adj_ek in edges_of_vertex(vk):
            adj_ekey = f"{adj_ek[0]},{adj_ek[1]},{adj_ek[2]}"
            if adj_ekey != ekey and adj_ekey in game.edges and game.edges[adj_ekey].player_id == player_id:
                return True, "ok"

    return False, "Road must connect to your network"


def can_upgrade_city(vk: VertexKey, player_id: str, game: GameState) -> Tuple[bool, str]:
    vkey = f"{vk[0]},{vk[1]},{vk[2]}"
    piece = game.vertices.get(vkey)
    if not piece:
        return False, "No settlement at this vertex"
    if piece.player_id != player_id:
        return False, "Not your settlement"
    if piece.piece_type != PieceType.SETTLEMENT:
        return False, "Already a city"
    return True, "ok"
