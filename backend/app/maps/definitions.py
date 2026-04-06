"""
Static map definitions for all 9 Catan maps.
Axial coordinates (q, r). Standard hex layout.
Resource biases per map are encoded in tile counts.

Standard Catan tile counts (reference):
  4 forest, 3 mountains, 4 pasture, 4 fields, 3 hills, 1 desert = 19 land tiles
Standard token distribution:
  2×1, 3×2, 4×2, 5×2, 6×2, 8×2, 9×2, 10×2, 11×2, 12×1 = 18 tokens
"""

from typing import List, Tuple
from app.game.models import Tile, Port, MapData, TileType, Resource


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tile(q, r, tile_type, token=None):
    return Tile(q=q, r=r, tile_type=TileType(tile_type), token=token)


def _port(q, r, resource=None, ratio=None):
    if resource:
        return Port(q=q, r=r, resource=Resource(resource), ratio=ratio or 2)
    return Port(q=q, r=r, resource=None, ratio=ratio or 3)


# ---------------------------------------------------------------------------
# Standard ring layout helper (3-4-5-4-3)
# ---------------------------------------------------------------------------

STANDARD_COORDS = [
    # Ring 0 (center)
    (0, 0),
    # Ring 1
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
    # Ring 2
    (2, 0), (2, -1), (2, -2), (1, -2), (0, -2),
    (-1, -1), (-2, 0), (-2, 1), (-2, 2), (-1, 2), (0, 2), (1, 1),
]


# ---------------------------------------------------------------------------
# Random map (generated at runtime — see maps/generator.py)
# Placeholder definition; actual generation is in generator.py
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# China — 矿石↑↑ 小麦↑ 木材↑，港口少
# Shape: roughly elongated horizontal (approximates mainland China)
# ---------------------------------------------------------------------------

def china_map() -> MapData:
    tiles = [
        # Row r=-2
        _tile(-2, -1, "mountains", 9), _tile(-1, -2, "mountains", 6), _tile(0, -2, "forest", 5),
        _tile(1, -2, "mountains", 10), _tile(2, -2, "forest", 3),
        # Row r=-1
        _tile(-2, 0, "mountains", 8), _tile(-1, -1, "fields", 4), _tile(0, -1, "mountains", 11),
        _tile(1, -1, "forest", 6), _tile(2, -1, "fields", 3),
        # Row r=0 (middle)
        _tile(-1, 0, "mountains", 5), _tile(0, 0, "desert"), _tile(1, 0, "mountains", 9),
        _tile(2, 0, "fields", 8),
        # Row r=1
        _tile(-1, 1, "hills", 2), _tile(0, 1, "pasture", 10), _tile(1, 1, "forest", 4),
        _tile(2, 1, "hills", 11),
        # Row r=2
        _tile(0, 2, "pasture", 12), _tile(1, 2, "hills", 5),
    ]
    ports = [
        _port(-2, -2, ratio=3),   # generic port NW
        _port(3, -2, ratio=3),    # generic port NE
        _port(3, 1, "ore"),       # ore 2:1 port (mountains heavy)
        _port(0, 3, ratio=3),     # generic port S
    ]
    return MapData(map_id="china", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Japan — 港口↑↑ 小麦↓ 矿石↓，四岛群岛（海洋分割）
# ---------------------------------------------------------------------------

def japan_map() -> MapData:
    # Four island groups separated by ocean
    tiles = [
        # Island 1 (NW — Hokkaido-like)
        _tile(-3, 0, "forest", 6), _tile(-2, -1, "pasture", 9), _tile(-3, 1, "hills", 4),

        # Island 2 (central — Honshu-like, largest)
        _tile(-1, -1, "forest", 8), _tile(0, -2, "forest", 5), _tile(1, -2, "pasture", 10),
        _tile(-1, 0, "hills", 3), _tile(0, -1, "desert"), _tile(1, -1, "pasture", 11),
        _tile(0, 0, "forest", 6), _tile(1, 0, "hills", 4),

        # Island 3 (SW — Shikoku/Kyushu-like)
        _tile(-1, 2, "pasture", 9), _tile(0, 2, "hills", 5), _tile(-1, 3, "fields", 2),

        # Island 4 (SE — small)
        _tile(2, 1, "mountains", 8), _tile(3, 0, "mountains", 10), _tile(2, 0, "fields", 3),
    ]
    ports = [
        # Many ports — Japan is an island nation
        _port(-3, -1, ratio=3),
        _port(-2, -2, "wood"),
        _port(2, -3, ratio=3),
        _port(3, -2, "sheep"),
        _port(4, -1, ratio=3),
        _port(3, 1, ratio=3),
        _port(1, 3, "brick"),
        _port(-2, 3, ratio=3),
    ]
    return MapData(map_id="japan", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# USA — 小麦↑↑ 木材↑ 资源均衡
# Shape: wide horizontal spread
# ---------------------------------------------------------------------------

def usa_map() -> MapData:
    tiles = [
        # Northern tier
        _tile(-2, -1, "forest", 6), _tile(-1, -2, "fields", 9), _tile(0, -2, "forest", 4),
        _tile(1, -2, "fields", 8), _tile(2, -2, "forest", 3),
        # Middle tier
        _tile(-2, 0, "fields", 10), _tile(-1, -1, "pasture", 5), _tile(0, -1, "fields", 6),
        _tile(1, -1, "pasture", 11), _tile(2, -1, "fields", 4),
        # Central
        _tile(-1, 0, "fields", 9), _tile(0, 0, "desert"), _tile(1, 0, "forest", 2),
        _tile(2, 0, "mountains", 10),
        # Southern tier
        _tile(-1, 1, "hills", 5), _tile(0, 1, "fields", 8), _tile(1, 1, "pasture", 3),
        _tile(2, 1, "hills", 11),
        # Far south
        _tile(0, 2, "pasture", 12), _tile(1, 2, "fields", 6),
    ]
    ports = [
        _port(-3, 0, ratio=3),
        _port(-2, -2, "wheat"),
        _port(0, -3, ratio=3),
        _port(3, -2, "wood"),
        _port(3, 1, ratio=3),
        _port(0, 3, "sheep"),
        _port(-1, 2, ratio=3),
    ]
    return MapData(map_id="usa", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Europe — 小麦↑ 牧羊↑ 港口多
# Shape: roughly compact central mass
# ---------------------------------------------------------------------------

def europe_map() -> MapData:
    tiles = [
        _tile(0, -2, "fields", 9), _tile(1, -2, "pasture", 6), _tile(-1, -1, "fields", 5),
        _tile(0, -1, "pasture", 10), _tile(1, -1, "fields", 8), _tile(2, -1, "hills", 3),
        _tile(-1, 0, "pasture", 4), _tile(0, 0, "fields", 11), _tile(1, 0, "desert"),
        _tile(2, 0, "pasture", 9), _tile(-1, 1, "mountains", 2), _tile(0, 1, "fields", 5),
        _tile(1, 1, "pasture", 6), _tile(2, 1, "hills", 10), _tile(0, 2, "mountains", 4),
        _tile(1, 2, "forest", 8), _tile(-1, 2, "pasture", 12), _tile(3, -1, "forest", 3),
        _tile(3, 0, "mountains", 11),
    ]
    ports = [
        _port(-2, 0, ratio=3), _port(-1, -2, "wheat"), _port(1, -3, ratio=3),
        _port(3, -2, "sheep"), _port(4, -1, ratio=3), _port(4, 0, "brick"),
        _port(2, 2, ratio=3), _port(0, 3, "ore"), _port(-1, 3, ratio=3),
    ]
    return MapData(map_id="europe", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# UK — 牧羊↑↑ 矿石↑，岛链形状
# ---------------------------------------------------------------------------

def uk_map() -> MapData:
    tiles = [
        # Scotland/North (narrow)
        _tile(-1, -3, "pasture", 9), _tile(0, -3, "mountains", 6),
        # England (wider middle)
        _tile(-1, -2, "pasture", 5), _tile(0, -2, "hills", 10), _tile(1, -2, "pasture", 4),
        _tile(-2, -1, "mountains", 8), _tile(-1, -1, "pasture", 3), _tile(0, -1, "fields", 11),
        _tile(1, -1, "pasture", 9),
        # England South
        _tile(-2, 0, "mountains", 6), _tile(-1, 0, "pasture", 5), _tile(0, 0, "desert"),
        _tile(1, 0, "mountains", 4),
        # Wales + SW
        _tile(-2, 1, "hills", 2), _tile(-1, 1, "pasture", 8), _tile(0, 1, "fields", 10),
        # Ireland (separate island)
        _tile(-3, 1, "pasture", 12), _tile(-3, 0, "hills", 3), _tile(-3, -1, "forest", 11),
    ]
    ports = [
        _port(-2, -3, ratio=3), _port(1, -3, "sheep"), _port(2, -2, ratio=3),
        _port(2, 0, "ore"), _port(1, 2, ratio=3), _port(-2, 2, ratio=3),
        _port(-4, 1, "sheep"), _port(-4, -1, ratio=3),
    ]
    return MapData(map_id="uk", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Australia — 沙漠↑↑ 矿石↑↑ 牧羊↑
# Shape: wide, flat continent
# ---------------------------------------------------------------------------

def australia_map() -> MapData:
    tiles = [
        # North
        _tile(-2, -1, "mountains", 6), _tile(-1, -2, "desert"), _tile(0, -2, "mountains", 9),
        _tile(1, -2, "pasture", 5), _tile(2, -2, "desert"),
        # Middle
        _tile(-2, 0, "desert"), _tile(-1, -1, "mountains", 8), _tile(0, -1, "desert"),
        _tile(1, -1, "mountains", 4), _tile(2, -1, "pasture", 10),
        # Central (huge desert)
        _tile(-1, 0, "desert"), _tile(0, 0, "desert"), _tile(1, 0, "mountains", 3),
        _tile(2, 0, "pasture", 11),
        # South (coastal)
        _tile(-1, 1, "hills", 2), _tile(0, 1, "fields", 6), _tile(1, 1, "pasture", 8),
        _tile(-1, 2, "fields", 5), _tile(0, 2, "hills", 12),
    ]
    ports = [
        _port(-3, 0, "ore"), _port(-2, -2, ratio=3), _port(0, -3, ratio=3),
        _port(3, -2, "sheep"), _port(3, 0, ratio=3), _port(1, 2, "ore"),
        _port(-2, 3, ratio=3),
    ]
    return MapData(map_id="australia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Brazil — 木材↑↑ 小麦↑
# Shape: large triangular blob
# ---------------------------------------------------------------------------

def brazil_map() -> MapData:
    tiles = [
        _tile(-1, -2, "forest", 6), _tile(0, -2, "forest", 9), _tile(1, -2, "fields", 4),
        _tile(-2, -1, "forest", 8), _tile(-1, -1, "forest", 5), _tile(0, -1, "fields", 10),
        _tile(1, -1, "forest", 3), _tile(2, -1, "hills", 11),
        _tile(-2, 0, "fields", 6), _tile(-1, 0, "forest", 4), _tile(0, 0, "desert"),
        _tile(1, 0, "fields", 9), _tile(2, 0, "pasture", 2),
        _tile(-1, 1, "forest", 8), _tile(0, 1, "fields", 5), _tile(1, 1, "mountains", 10),
        _tile(0, 2, "pasture", 12), _tile(1, 2, "hills", 3),
        _tile(-1, 2, "forest", 11),
    ]
    ports = [
        _port(-3, 0, "wood"), _port(-2, -2, ratio=3), _port(0, -3, ratio=3),
        _port(3, -1, ratio=3), _port(3, 0, "wheat"), _port(1, 3, ratio=3),
        _port(-1, 3, ratio=3),
    ]
    return MapData(map_id="brazil", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Antarctica — 沙漠↑↑↑ 资源极稀（趣味图）
# ---------------------------------------------------------------------------

def antarctica_map() -> MapData:
    tiles = [
        # Mostly desert with tiny bits of resources
        _tile(0, -2, "desert"), _tile(1, -2, "desert"), _tile(-1, -1, "desert"),
        _tile(0, -1, "mountains", 6), _tile(1, -1, "desert"), _tile(2, -1, "desert"),
        _tile(-1, 0, "desert"), _tile(0, 0, "desert"), _tile(1, 0, "hills", 9),
        _tile(2, 0, "desert"), _tile(-1, 1, "desert"), _tile(0, 1, "desert"),
        _tile(1, 1, "desert"), _tile(2, 1, "pasture", 4), _tile(-1, 2, "desert"),
        _tile(0, 2, "fields", 11), _tile(1, 2, "desert"),
        _tile(0, -3, "forest", 2), _tile(3, -1, "desert"),
    ]
    ports = [
        # Very few ports — hard to trade
        _port(-2, 0, ratio=3), _port(4, -1, ratio=3), _port(1, 3, ratio=3),
    ]
    return MapData(map_id="antarctica", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MAP_REGISTRY = {
    "china": china_map,
    "japan": japan_map,
    "usa": usa_map,
    "europe": europe_map,
    "uk": uk_map,
    "australia": australia_map,
    "brazil": brazil_map,
    "antarctica": antarctica_map,
}


def get_static_map(map_id: str) -> MapData:
    fn = MAP_REGISTRY.get(map_id)
    if not fn:
        raise ValueError(f"Unknown static map: {map_id}")
    return fn()
