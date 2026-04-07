"""
Random Catan map generator.
Follows standard resource and token distribution with balance checks.
"""

import random
from typing import List, Optional, Set, Tuple

from app.game.models import Tile, Port, MapData, TileType, Resource
from app.maps.ports import normalize_ports


# Standard Catan resource counts
STANDARD_TILES = (
    [TileType.FOREST] * 4 +
    [TileType.MOUNTAINS] * 3 +
    [TileType.PASTURE] * 4 +
    [TileType.FIELDS] * 4 +
    [TileType.HILLS] * 3 +
    [TileType.DESERT] * 1
)

# Standard token distribution (18 tokens for 18 non-desert tiles)
STANDARD_TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

# Standard hex ring layout (19 tiles: 3-4-5-4-3)
STANDARD_COORDS = [
    (0, 0),
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
    (2, 0), (2, -1), (2, -2), (1, -2), (0, -2),
    (-1, -1), (-2, 0), (-2, 1), (-2, 2), (-1, 2), (0, 2), (1, 1),
]

# Port definitions: (q, r, resource_or_None)
# All coordinates are ring-2 (perimeter) land tiles so there is no snapping ambiguity.
# normalize_ports() will assign the correct coastal side automatically.
STANDARD_PORTS = [
    (0, -2, None),              # 3:1  — top
    (2, -2, Resource.ORE),      # ore  — top-right corner
    (2, -1, None),              # 3:1  — right-upper
    (2,  0, None),              # 3:1  — right
    (1,  1, Resource.WHEAT),    # wheat — lower-right
    (-1, 2, Resource.SHEEP),    # sheep — lower-left
    (-2, 2, None),              # 3:1  — bottom-left corner
    (-2, 0, Resource.BRICK),    # brick — left
    (-1,-1, Resource.WOOD),     # wood  — upper-left
]

HEX_DIRECTIONS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1),
]


def _neighbors_of(q, r, coord_set: Set[Tuple[int, int]]) -> List[Tuple[int, int]]:
    return [
        (q + dq, r + dr)
        for dq, dr in HEX_DIRECTIONS
        if (q + dq, r + dr) in coord_set
    ]


def _high_probability(token: Optional[int]) -> bool:
    """6 and 8 are high probability tokens that should not be adjacent."""
    return token in (6, 8)


def _tokens_are_balanced(tiles: List[Tile]) -> bool:
    """Check that no two 6/8 tokens are adjacent."""
    tile_map = {(t.q, t.r): t for t in tiles}
    coord_set = set(tile_map.keys())
    for t in tiles:
        if not _high_probability(t.token):
            continue
        for nq, nr in _neighbors_of(t.q, t.r, coord_set):
            neighbor = tile_map.get((nq, nr))
            if neighbor and _high_probability(neighbor.token):
                return False
    return True


def generate_random_map(seed: Optional[int] = None) -> MapData:
    """
    Generate a balanced random Catan map.
    Retries token assignment up to 100 times to satisfy balance constraint.
    """
    rng = random.Random(seed)

    # Shuffle tiles
    tile_types = STANDARD_TILES[:]
    rng.shuffle(tile_types)

    coords = STANDARD_COORDS
    tiles: List[Tile] = []
    desert_q, desert_r = 0, 0

    token_pool = STANDARD_TOKENS[:]

    # Try up to 100 times to get balanced token placement
    for attempt in range(100):
        rng.shuffle(token_pool)
        tmp_tiles: List[Tile] = []
        token_idx = 0

        for i, (q, r) in enumerate(coords):
            ttype = tile_types[i]
            if ttype == TileType.DESERT:
                tmp_tiles.append(Tile(q=q, r=r, tile_type=ttype, token=None))
                desert_q, desert_r = q, r
            else:
                tmp_tiles.append(Tile(q=q, r=r, tile_type=ttype, token=token_pool[token_idx]))
                token_idx += 1

        if _tokens_are_balanced(tmp_tiles):
            tiles = tmp_tiles
            break
    else:
        # Give up balancing, use last attempt
        tiles = tmp_tiles  # type: ignore

    # Build ports
    ports: List[Port] = []
    for q, r, res in STANDARD_PORTS:
        if res is None:
            ports.append(Port(q=q, r=r, resource=None, ratio=3))
        else:
            ports.append(Port(q=q, r=r, resource=res, ratio=2))

    map_id = f"random_{seed}" if seed is not None else "random"
    map_data = MapData(map_id=map_id, tiles=tiles, ports=ports)
    return normalize_ports(map_data)
