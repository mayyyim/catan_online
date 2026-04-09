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
from app.maps.ports import normalize_ports


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _tile(q, r, tile_type, token=None):
    return Tile(q=q, r=r, tile_type=TileType(tile_type), token=token)


def _port(q, r, resource=None, ratio=None, side=None):
    """
    Define a port on land tile (q, r).
    - resource: None means 3:1 generic; a resource string means 2:1 specific.
    - side: coastal edge (0-5) the port faces. Must be the outward-facing coastal
      side of the tile. If omitted, normalize_ports() will infer it automatically.
    All (q, r) must be actual land tiles so there is no snapping ambiguity.
    """
    if resource:
        return Port(q=q, r=r, resource=Resource(resource), ratio=ratio or 2, side=side)
    return Port(q=q, r=r, resource=None, ratio=ratio or 3, side=side)


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
# Shape: wide E-W rectangle, wider in north, NE protrusion
# q=0..5, r=-1..2  →  wide horizontal band
# ---------------------------------------------------------------------------

def china_map() -> MapData:
    tiles = [
        # Northern row (r=-1): wide top edge
        _tile(0, -1, "mountains", 9),  _tile(1, -1, "forest", 6),
        _tile(2, -1, "mountains", 4),  _tile(3, -1, "fields", 11),
        _tile(4, -1, "mountains", 3),  _tile(5, -1, "forest", 8),
        # Middle row (r=0): core of China
        _tile(0,  0, "fields", 10),   _tile(1,  0, "mountains", 5),
        _tile(2,  0, "desert"),        _tile(3,  0, "mountains", 9),
        _tile(4,  0, "fields", 6),    _tile(5,  0, "mountains", 5),
        # Southern row (r=1)
        _tile(1,  1, "hills", 4),     _tile(2,  1, "pasture", 11),
        _tile(3,  1, "forest", 12),   _tile(4,  1, "hills", 3),
        # Far south (r=2): SE coast
        _tile(2,  2, "pasture", 8),   _tile(3,  2, "hills", 10),
        # NE protrusion (Manchuria): extra tile
        _tile(5, -2, "forest", 2),
    ]
    ports = [
        _port(0,  -1, ratio=3),        # W coast
        _port(5,  -2, "ore"),          # NE tip
        _port(5,   0, ratio=3),        # E coast
        _port(3,   2, ratio=3),        # SE coast
        _port(1,   1, "wheat"),        # S coast
    ]
    return MapData(map_id="china", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Japan — 港口↑↑ 小麦↓ 矿石↓，四岛群岛（海洋分割）
# Shape: diagonal island chain NW→SE (Hokkaido, Honshu, Shikoku+Kyushu, Okinawa)
# ---------------------------------------------------------------------------

def japan_map() -> MapData:
    tiles = [
        # Hokkaido (NW island, 2 tiles)
        _tile(-3, -1, "forest", 6),   _tile(-2, -2, "hills", 9),

        # Honshu (main island, 8 tiles, diagonal NW→SE)
        _tile(-1, -2, "mountains", 4), _tile(0, -2, "forest", 11),
        _tile(0,  -1, "pasture", 3),   _tile(1, -2, "mountains", 8),
        _tile(1,  -1, "desert"),        _tile(2, -1, "forest", 10),

        # Shikoku + Kyushu (SW cluster, 5 tiles)
        _tile(1,   0, "hills", 5),    _tile(2,  0, "mountains", 2),
        _tile(2,   1, "pasture", 9),  _tile(3,  0, "hills", 6),
        _tile(3,  -1, "forest", 5),

        # Ryukyu / Okinawa (SE small group, 2 tiles)
        _tile(4,   0, "mountains", 4), _tile(4, -1, "pasture", 12),

        # Extra tile to reach 17 total — small N Honshu
        _tile(-1, -1, "fields", 3),
        # Total: 2+8+5+2+1 = 18 tiles  (add 1 more for 19 is not required, let's use 16+3=19)
        _tile(5,  -1, "hills", 11),   _tile(5, 0, "fields", 8),
    ]
    ports = [
        _port(-3, -1, ratio=3),      # Hokkaido W
        _port(-2, -2, "wood"),       # Hokkaido N
        _port( 1, -2, ratio=3),      # Honshu NE
        _port( 2, -1, ratio=3),      # Honshu E
        _port( 3,  0, "sheep"),      # Kyushu S
        _port( 4,  0, "brick"),      # Ryukyu SE
        _port( 2,  1, ratio=3),      # Kyushu SW
        _port(-1, -2, ratio=3),      # Honshu W
    ]
    return MapData(map_id="japan", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# USA — 小麦↑↑ 木材↑ 资源均衡
# Shape: wide E-W (2.5:1) with slight SE protrusion (Florida/Gulf coast)
# q=-3..3, r=-1..2
# ---------------------------------------------------------------------------

def usa_map() -> MapData:
    tiles = [
        # Northern row (r=-1): wide Canada border strip
        _tile(-3, -1, "forest", 6),  _tile(-2, -1, "forest", 9),
        _tile(-1, -1, "fields", 4),  _tile(0,  -1, "forest", 8),
        _tile(1,  -1, "fields", 3),  _tile(2,  -1, "forest", 10),
        _tile(3,  -1, "fields", 5),
        # Middle row (r=0): main continental body
        _tile(-3,  0, "fields", 2),  _tile(-2,  0, "pasture", 9),
        _tile(-1,  0, "fields", 6),  _tile(0,   0, "desert"),
        _tile(1,   0, "fields", 5),  _tile(2,   0, "pasture", 4),
        _tile(3,   0, "mountains", 11),
        # Southern row (r=1): Gulf + Appalachian
        _tile(-2,  1, "hills", 12),  _tile(-1,  1, "fields", 3),
        _tile(0,   1, "pasture", 8), _tile(1,   1, "hills", 10),
        # SE protrusion (r=2): Florida + SE coast
        _tile(1,   2, "pasture", 11), _tile(2,  1, "fields", 6),
    ]
    ports = [
        _port(-3,  -1, "wood"),      # NW — Pacific coast
        _port( 3,  -1, ratio=3),     # NE — Great Lakes
        _port( 3,   0, ratio=3),     # E  — Atlantic coast
        _port( 1,   2, "sheep"),     # SE — Florida
        _port(-1,   1, ratio=3),     # S  — Gulf coast
        _port(-2,   1, ratio=3),     # SW — Texas coast
        _port(-3,   0, "wheat"),     # W  — Pacific
    ]
    return MapData(map_id="usa", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Europe — 小麦↑ 牧羊↑ 港口多
# Shape: irregular wide blob (1.5:1), from Iberia to Turkey, Scandinavia to Med
# q=-2..3, r=-2..1
# ---------------------------------------------------------------------------

def europe_map() -> MapData:
    tiles = [
        # Northern row (r=-2): Scandinavia + Baltic
        _tile(-1, -2, "forest", 9),  _tile(0, -2, "forest", 6),
        _tile(1,  -2, "mountains", 4),
        # Upper-mid row (r=-1): W+Central Europe
        _tile(-2, -1, "fields", 11), _tile(-1, -1, "pasture", 3),
        _tile(0,  -1, "fields", 8),  _tile(1,  -1, "hills", 10),
        _tile(2,  -1, "mountains", 5),
        # Middle row (r=0): core Europe
        _tile(-2,  0, "pasture", 2), _tile(-1,  0, "fields", 9),
        _tile(0,   0, "desert"),      _tile(1,   0, "fields", 6),
        _tile(2,   0, "pasture", 5), _tile(3,  -1, "mountains", 4),
        # Southern row (r=1): Med coast + Balkans
        _tile(-1,  1, "hills", 11),  _tile(0,   1, "fields", 12),
        _tile(1,   1, "pasture", 3), _tile(2,   1, "hills", 8),
        # Extra tile for 19 total: Turkey/Anatolia
        _tile(3,   0, "mountains", 10),
    ]
    ports = [
        _port(-1,  -2, ratio=3),     # N — Scandinavia
        _port(1,   -2, ratio=3),     # NE — Baltic
        _port(3,   -1, "ore"),       # E — Black Sea
        _port(3,    0, ratio=3),     # SE — Turkey coast
        _port(1,    1, ratio=3),     # S — Med
        _port(-1,   1, "wheat"),     # SW — Iberia
        _port(-2,   0, ratio=3),     # W — Atlantic
        _port(-2,  -1, "sheep"),     # NW — British Isles
    ]
    return MapData(map_id="europe", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# UK — 牧羊↑↑ 矿石↑，岛链形状
# Shape: narrow N-S main island (GB) + separate Ireland to the W
# GB: q=0..1, r=-3..1   Ireland: q=-2..-3, r=-1..1  (gap at q=-1)
# ---------------------------------------------------------------------------

def uk_map() -> MapData:
    tiles = [
        # Great Britain — Scotland (top, narrow)
        _tile(0, -3, "mountains", 9),
        # GB — N England
        _tile(0, -2, "pasture", 6),   _tile(1, -2, "hills", 4),
        # GB — Midlands
        _tile(0, -1, "pasture", 11),  _tile(1, -1, "mountains", 3),
        # GB — England
        _tile(0,  0, "fields", 8),    _tile(1,  0, "pasture", 10),
        # GB — South England + Wales
        _tile(0,  1, "pasture", 5),   _tile(1,  1, "hills", 2),

        # Ireland (separate island: gap of one hex column)
        _tile(-2, -1, "pasture", 9),  _tile(-3, -1, "forest", 6),
        _tile(-2,  0, "hills", 5),    _tile(-3,  0, "pasture", 4),
        _tile(-2,  1, "fields", 11),

        # Scotland Highlands extra tiles
        _tile(0, -4, "mountains", 12), _tile(1, -3, "pasture", 3),

        # Extra tiles to make 19
        _tile(-1, -2, "pasture", 8),  _tile(-1, 0, "forest", 10),
        _tile(2,  0, "desert"),
    ]
    ports = [
        _port(0,   -4, "sheep"),     # N — Scotland top
        _port(1,   -2, ratio=3),     # NE — E coast
        _port(1,    1, ratio=3),     # SE — Channel
        _port(0,    1, ratio=3),     # S  — SW England
        _port(-2,   1, ratio=3),     # SW — Ireland S
        _port(-3,  -1, "ore"),       # W  — Ireland W
        _port(-2,  -1, ratio=3),     # NW — Irish Sea N
    ]
    return MapData(map_id="uk", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Australia — 沙漠↑↑ 矿石↑↑ 牧羊↑
# Shape: wide flat continent (2.5:1), desert interior, coastal resources
# q=-2..4, r=-1..2
# ---------------------------------------------------------------------------

def australia_map() -> MapData:
    tiles = [
        # Northern coast row (r=-1)
        _tile(-1, -1, "mountains", 9), _tile(0, -1, "desert"),
        _tile(1,  -1, "pasture", 6),   _tile(2, -1, "desert"),
        _tile(3,  -1, "mountains", 4), _tile(4, -1, "fields", 11),
        # Middle row (r=0): vast desert interior
        _tile(-2,  0, "desert"),       _tile(-1,  0, "desert"),
        _tile(0,   0, "desert"),       _tile(1,   0, "desert"),
        _tile(2,   0, "mountains", 3), _tile(3,   0, "pasture", 8),
        _tile(4,   0, "mountains", 10),
        # Southern coast row (r=1)
        _tile(-1,  1, "hills", 5),    _tile(0,   1, "fields", 2),
        _tile(1,   1, "pasture", 9),  _tile(2,   1, "hills", 6),
        _tile(3,   1, "fields", 5),
        # SE corner (r=2): Tasmania-like
        _tile(2,   2, "pasture", 12), _tile(3,  2, "hills", 4),
    ]
    ports = [
        _port(-2,   0, ratio=3),     # W  — Perth
        _port(-1,  -1, "ore"),       # NW — Darwin coast
        _port(4,   -1, ratio=3),     # NE — Queensland
        _port(4,    0, ratio=3),     # E  — Sydney
        _port(3,    2, ratio=3),     # SE — Melbourne
        _port(0,    1, "sheep"),     # S  — Adelaide
        _port(-1,   1, ratio=3),     # SW — Albany
    ]
    return MapData(map_id="australia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Brazil — 木材↑↑ 小麦↑
# Shape: large roughly triangular, wide N, narrowing S, Atlantic coast E
# ~19 tiles, q=-2..2, r=-2..2
# ---------------------------------------------------------------------------

def brazil_map() -> MapData:
    tiles = [
        # Top (N): Amazon wide band
        _tile(-2, -1, "forest", 9),  _tile(-1, -2, "forest", 6),
        _tile(0,  -2, "forest", 4),  _tile(1,  -2, "fields", 11),
        _tile(2,  -2, "forest", 3),
        # Upper-mid
        _tile(-2,  0, "forest", 8),  _tile(-1, -1, "forest", 10),
        _tile(0,  -1, "fields", 5),  _tile(1,  -1, "forest", 2),
        _tile(2,  -1, "hills", 9),
        # Middle: Mato Grosso / Cerrado
        _tile(-1,  0, "fields", 6),  _tile(0,   0, "desert"),
        _tile(1,   0, "forest", 5),  _tile(2,   0, "pasture", 4),
        # Lower: narrowing toward south
        _tile(-1,  1, "forest", 11), _tile(0,   1, "fields", 12),
        _tile(1,   1, "hills", 3),
        # Tip: Rio Grande do Sul
        _tile(0,   2, "pasture", 8), _tile(1,   2, "fields", 10),
    ]
    ports = [
        _port(-2,  -1, "wood"),      # W  — Amazon mouth
        _port(0,   -2, ratio=3),     # N  — North coast
        _port(2,   -2, ratio=3),     # NE — Nordeste
        _port(2,    0, ratio=3),     # E  — Salvador coast
        _port(1,    2, "wheat"),     # SE — Rio coast
        _port(0,    2, ratio=3),     # S  — Porto Alegre
        _port(-1,   1, ratio=3),     # SW — Pantanal
    ]
    return MapData(map_id="brazil", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Antarctica — 沙漠↑↑↑ 资源极稀（趣味图）
# Shape: sparse coastal ring, mostly desert interior
# A rough ring of hexes around an icy center
# ---------------------------------------------------------------------------

def antarctica_map() -> MapData:
    tiles = [
        # Outer coast ring (roughly circular perimeter)
        _tile(-2,  0, "desert"),       _tile(-1, -1, "mountains", 6),
        _tile(0,  -2, "desert"),        _tile(1,  -2, "desert"),
        _tile(2,  -2, "desert"),        _tile(3,  -1, "desert"),
        _tile(3,   0, "desert"),        _tile(2,   1, "hills", 9),
        _tile(1,   2, "desert"),        _tile(0,   2, "fields", 11),
        _tile(-1,  2, "desert"),        _tile(-2,  1, "desert"),
        # Inner ring — still mostly desert
        _tile(-1,  0, "desert"),        _tile(0,  -1, "mountains", 4),
        _tile(1,  -1, "desert"),        _tile(2,   0, "desert"),
        _tile(1,   1, "desert"),        _tile(0,   1, "forest", 2),
        # Center
        _tile(0,   0, "desert"),
    ]
    ports = [
        # Very few ports — hard to trade
        _port(-2,  0, ratio=3),
        _port(3,   0, ratio=3),
        _port(0,   2, ratio=3),
    ]
    return MapData(map_id="antarctica", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Helper — build MapData from STANDARD_COORDS
# tt = list of (terrain_str, token_or_None) in STANDARD_COORDS order (len 19)
# Standard token sequence (18 non-desert tiles):
#   pos 1-18: 9,6,4,11,3,8,10,5,2,9,6,5,4,11,12,3,8,10
#   sorted:   2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12  ✓
# ---------------------------------------------------------------------------

def _from_std(map_id: str, tt: List[Tuple[str, object]], ports: List[Port]) -> MapData:
    tiles = [_tile(q, r, t, tok) for (q, r), (t, tok) in zip(STANDARD_COORDS, tt)]
    return MapData(map_id=map_id, tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# India — 小麦↑↑ 牧羊↑  (恒河平原·香料贸易)
# Shape: triangle pointing S (wide N, narrow S)
# q=-1..3, r=-2..3
# ---------------------------------------------------------------------------

def india_map() -> MapData:
    tiles = [
        # Northern wide base (r=-2): Himalayas/Punjab
        _tile(-1, -2, "mountains", 9), _tile(0, -2, "fields", 6),
        _tile(1,  -2, "fields", 4),    _tile(2, -2, "mountains", 11),
        _tile(3,  -2, "pasture", 3),
        # Upper mid (r=-1): Gangetic plain
        _tile(-1, -1, "fields", 8),    _tile(0,  -1, "fields", 10),
        _tile(1,  -1, "pasture", 5),   _tile(2,  -1, "fields", 2),
        # Middle (r=0): Deccan plateau
        _tile(0,   0, "hills", 9),     _tile(1,   0, "desert"),
        _tile(2,   0, "pasture", 6),   _tile(3,  -1, "fields", 5),
        # Lower (r=1): narrowing
        _tile(0,   1, "hills", 4),     _tile(1,   1, "pasture", 11),
        _tile(2,   1, "fields", 12),
        # Bottom (r=2): tip of peninsula
        _tile(1,   2, "hills", 3),     _tile(2,   2, "pasture", 8),
        # Tip (r=3): Kerala/Tamil Nadu
        _tile(1,   3, "forest", 10),
    ]
    ports = [
        _port(-1,  -2, ratio=3),     # NW — Arabian Sea
        _port(3,   -2, ratio=3),     # NE — Bay of Bengal N
        _port(3,   -1, "wheat"),     # E  — East coast
        _port(2,    2, ratio=3),     # SE — Coromandel coast
        _port(1,    3, "sheep"),     # S  — Cape Comorin
        _port(0,    1, ratio=3),     # W  — Malabar coast
    ]
    return MapData(map_id="india", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Canada — 木材↑↑ 小麦↑  (北方森林·大草原)
# Shape: very wide E-W (3:1+), vast but thin N-S
# q=-4..3, r=-1..1
# ---------------------------------------------------------------------------

def canada_map() -> MapData:
    tiles = [
        # Northern row (r=-1): boreal / tundra
        _tile(-4, -1, "forest", 9),   _tile(-3, -1, "mountains", 6),
        _tile(-2, -1, "forest", 4),   _tile(-1, -1, "forest", 11),
        _tile(0,  -1, "forest", 3),   _tile(1,  -1, "fields", 8),
        _tile(2,  -1, "forest", 10),
        # Middle row (r=0): main inhabited belt
        _tile(-4,  0, "desert"),      _tile(-3,  0, "fields", 5),
        _tile(-2,  0, "forest", 2),   _tile(-1,  0, "fields", 9),
        _tile(0,   0, "pasture", 6),  _tile(1,   0, "mountains", 5),
        _tile(2,   0, "fields", 4),   _tile(3,  -1, "hills", 11),
        # Southern fringe (r=1): prairies + Great Lakes
        _tile(-3,  1, "pasture", 12), _tile(-2,  1, "fields", 3),
        _tile(-1,  1, "hills", 8),    _tile(0,   1, "forest", 10),
    ]
    ports = [
        _port(-4,  -1, "wood"),      # W  — Pacific coast
        _port(-4,   0, ratio=3),     # NW — Arctic
        _port(0,   -1, ratio=3),     # N  — Hudson Bay
        _port(3,   -1, ratio=3),     # NE — Atlantic
        _port(2,    0, ratio=3),     # E  — Maritimes
        _port(0,    1, ratio=3),     # SE — Great Lakes
        _port(-3,   1, "wheat"),     # S  — Prairies
    ]
    return MapData(map_id="canada", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Russia — 木材↑ 矿石↑↑  (泰加林·乌拉尔山)
# Shape: extremely wide E-W (4:1), thin N-S strip
# q=-4..4, r=-1..1
# ---------------------------------------------------------------------------

def russia_map() -> MapData:
    tiles = [
        # Northern tundra row (r=-1)
        _tile(-4, -1, "forest", 9),   _tile(-3, -1, "forest", 6),
        _tile(-2, -1, "mountains", 4), _tile(-1, -1, "forest", 11),
        _tile(0,  -1, "forest", 3),   _tile(1,  -1, "mountains", 8),
        _tile(2,  -1, "forest", 10),  _tile(3,  -1, "forest", 5),
        _tile(4,  -1, "mountains", 2),
        # Main body (r=0): Trans-Siberian corridor
        _tile(-4,  0, "fields", 9),   _tile(-3,  0, "mountains", 6),
        _tile(-2,  0, "desert"),      _tile(-1,  0, "pasture", 5),
        _tile(0,   0, "fields", 4),   _tile(1,   0, "mountains", 11),
        _tile(2,   0, "hills", 12),   _tile(3,   0, "fields", 3),
        _tile(4,   0, "mountains", 8),
        # Southern steppe (r=1): only a few tiles
        _tile(-1,  1, "pasture", 10),
    ]
    ports = [
        _port(-4,  -1, ratio=3),     # NW — Baltic
        _port(-4,   0, ratio=3),     # W  — St. Petersburg
        _port(0,   -1, ratio=3),     # N  — Arctic Ocean
        _port(4,   -1, "ore"),       # NE — Pacific Vladivostok
        _port(4,    0, ratio=3),     # E  — Far East
        _port(-1,   1, "wood"),      # S  — Black Sea / Caspian
    ]
    return MapData(map_id="russia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Egypt — 小麦↑↑ 砖块↑  (尼罗河·金字塔)
# Shape: roughly square with Nile delta at N, Sinai peninsula NE
# q=0..3, r=-2..2
# ---------------------------------------------------------------------------

def egypt_map() -> MapData:
    tiles = [
        # Top (r=-2): Mediterranean coast + Sinai
        _tile(0, -2, "fields", 9),   _tile(1, -2, "hills", 6),
        _tile(2, -2, "hills", 4),    _tile(3, -2, "desert"),
        # Upper mid (r=-1): Nile Delta + Eastern Desert
        _tile(0, -1, "fields", 11),  _tile(1, -1, "fields", 3),
        _tile(2, -1, "hills", 8),    _tile(3, -1, "mountains", 10),
        # Middle (r=0): Nile Valley
        _tile(0,  0, "hills", 5),    _tile(1,  0, "fields", 2),
        _tile(2,  0, "desert"),      _tile(3,  0, "fields", 9),
        # Lower (r=1): Upper Egypt / Sudan border
        _tile(0,  1, "fields", 6),   _tile(1,  1, "hills", 5),
        _tile(2,  1, "desert"),      _tile(3,  1, "pasture", 4),
        # Bottom (r=2): S Egypt
        _tile(1,  2, "fields", 11),  _tile(2,  2, "hills", 12),
        # Extra
        _tile(0, -3, "forest", 3),
    ]
    ports = [
        _port(0,   -3, ratio=3),     # N  — Alexandria coast
        _port(3,   -2, ratio=3),     # NE — Sinai
        _port(3,    1, "wheat"),     # E  — Red Sea
        _port(2,    2, ratio=3),     # S  — Aswan
        _port(0,    1, ratio=3),     # W  — Libyan border
        _port(0,   -2, "brick"),     # NW — Nile Delta
    ]
    return MapData(map_id="egypt", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Mexico — 砖块↑↑ 牧羊↑  (白银矿山·牧场)
# Shape: diagonal elongated NW-SE, wider N (Baja + mainland), narrow S (Yucatan)
# q=-2..2, r=-1..3
# ---------------------------------------------------------------------------

def mexico_map() -> MapData:
    tiles = [
        # NW row (r=-1): Sonora + Baja California
        _tile(-2, -1, "desert"),      _tile(-1, -1, "hills", 9),
        _tile(0,  -1, "pasture", 6),  _tile(1,  -1, "mountains", 4),
        # Upper mid (r=0): main plateau
        _tile(-1,  0, "hills", 11),   _tile(0,   0, "fields", 3),
        _tile(1,   0, "pasture", 8),  _tile(2,  -1, "hills", 10),
        # Middle (r=1): Sierra Madre
        _tile(-1,  1, "fields", 5),   _tile(0,   1, "hills", 2),
        _tile(1,   1, "mountains", 9), _tile(2,   0, "pasture", 6),
        # Lower (r=2): Oaxaca + Gulf coast
        _tile(0,   2, "fields", 5),   _tile(1,   2, "hills", 4),
        _tile(2,   1, "forest", 11),
        # Tip (r=3): Yucatan Peninsula
        _tile(0,   3, "forest", 12),  _tile(1,   3, "hills", 3),
        # Extra tile
        _tile(-2,  0, "pasture", 8),
        _tile(2,  -2, "fields", 10),
    ]
    ports = [
        _port(-2,  -1, ratio=3),     # NW — Baja Pacific
        _port(2,   -2, ratio=3),     # NE — Gulf of Mexico
        _port(2,    0, ratio=3),     # E  — Veracruz
        _port(1,    3, "brick"),     # SE — Yucatan
        _port(0,    3, ratio=3),     # S  — Tehuantepec
        _port(-2,   0, "sheep"),     # W  — Pacific coast
    ]
    return MapData(map_id="mexico", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Korea — 矿石↑↑ 砖块↑  (朝鲜半岛山脉)
# Shape: very narrow N-S (2 wide, 4 tall)
# q=0..1, r=-3..1
# ---------------------------------------------------------------------------

def korea_map() -> MapData:
    tiles = [
        # Top N (r=-3): North Korea mountains
        _tile(0, -3, "mountains", 9),  _tile(1, -3, "forest", 6),
        # Upper (r=-2): Pyongyang region
        _tile(0, -2, "mountains", 4),  _tile(1, -2, "mountains", 11),
        # Middle (r=-1): DMZ area
        _tile(0, -1, "hills", 3),     _tile(1, -1, "mountains", 8),
        # Middle (r=0): Seoul / central Korea
        _tile(0,  0, "mountains", 10), _tile(1,  0, "fields", 5),
        # Lower (r=1): South coast / Busan
        _tile(0,  1, "hills", 2),     _tile(1,  1, "mountains", 9),
        # Extra tiles to reach ~14 (still thematic): small islands + Jeju
        _tile(0, -4, "forest", 6),    _tile(1, -4, "desert"),
        _tile(0,  2, "hills", 5),     _tile(1,  2, "fields", 4),
        _tile(0,  3, "pasture", 11),
    ]
    ports = [
        _port(0,  -4, ratio=3),       # N  — Yellow Sea N
        _port(1,  -3, "ore"),         # NE — East Sea N
        _port(1,   0, ratio=3),       # E  — East Sea
        _port(1,   2, ratio=3),       # SE — Busan coast
        _port(0,   3, "brick"),       # S  — Jeju strait
        _port(0,   1, ratio=3),       # W  — Yellow Sea S
    ]
    return MapData(map_id="korea", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Indonesia — 木材↑↑ 砖块↑  (热带雨林·群岛)
# Shape: E-W island chain (4 island groups with gaps)
# Sumatra(W), Java, Borneo/Sulawesi, Maluku/Papua(E)
# ---------------------------------------------------------------------------

def indonesia_map() -> MapData:
    tiles = [
        # Sumatra (W island, 3 tiles)
        _tile(-4,  0, "forest", 9),   _tile(-3,  0, "hills", 6),
        _tile(-3, -1, "forest", 4),

        # Java (central-W, 3 tiles) — gap at q=-2
        _tile(-1,  0, "forest", 11),  _tile(-1,  1, "hills", 3),
        _tile(0,   0, "forest", 8),

        # Borneo + Sulawesi (central, 5 tiles) — gap at q=1
        _tile(2,  -1, "forest", 10),  _tile(2,   0, "mountains", 5),
        _tile(3,  -1, "hills", 2),    _tile(3,   0, "forest", 9),
        _tile(2,   1, "pasture", 6),

        # Papua / Maluku (E island, 4 tiles) — gap at q=4
        _tile(5,  -1, "forest", 5),   _tile(5,   0, "mountains", 4),
        _tile(6,  -1, "desert"),       _tile(6,   0, "fields", 11),

        # Extra tiles
        _tile(-2,  0, "hills", 12),   _tile(4,   0, "forest", 3),
        _tile(-4,  1, "pasture", 8),  _tile(7,  -1, "fields", 10),
    ]
    ports = [
        _port(-4,   1, ratio=3),      # W  — Sumatra S
        _port(-4,   0, "wood"),       # NW — Sumatra W
        _port(-3,  -1, ratio=3),      # N  — Strait of Malacca
        _port(3,   -1, ratio=3),      # N  — Borneo N
        _port(6,  -1, ratio=3),       # NE — Papua N
        _port(7,  -1, "brick"),       # E  — Pacific coast
        _port(2,    1, ratio=3),      # S  — Java Sea
    ]
    return MapData(map_id="indonesia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# New Zealand — 牧羊↑↑ 矿石↑
# Shape: two elongated islands separated by Cook Strait (gap at r=0);
#        North Island: volcanoes + dairy; South Island: Southern Alps + Canterbury Plains + Fiordland
# ---------------------------------------------------------------------------

def new_zealand_map() -> MapData:
    tiles = [
        # ── North Island (r=-4 to r=-1) ──────────────────────────────────────
        _tile(0, -4, "hills",     9),   # Northland (rolling kauri-forest hills)
        _tile(1, -4, "forest",    6),   # Northland E (kauri / coastal forest)
        _tile(0, -3, "fields",   11),   # Auckland volcanic plateau (dairy)
        _tile(1, -3, "hills",     4),   # Bay of Plenty coast
        _tile(0, -2, "fields",    3),   # Waikato (dairy heartland — most productive!)
        _tile(1, -2, "pasture",   8),   # Hawke's Bay (sheep + wine)
        _tile(2, -2, "mountains",10),   # Urewera / East Cape (volcanic, rugged)
        _tile(1, -1, "mountains", 5),   # Tongariro volcanic plateau (Ruapehu, Ngauruhoe!)
        _tile(2, -1, "pasture",   2),   # Wellington / Wairarapa (merino sheep)
        # ── Cook Strait gap (r=0, no tiles) ─────────────────────────────────
        # ── South Island (r=1 to r=4) ────────────────────────────────────────
        _tile(2,  1, "mountains", 9),   # Nelson Lakes / Kaikoura (Alps begin)
        _tile(3,  1, "fields",    6),   # Marlborough (world-famous Sauvignon Blanc!)
        _tile(4,  1, "hills",     5),   # N Canterbury coast
        _tile(2,  2, "mountains", 4),   # Southern Alps (Mt Cook 3754 m!)
        _tile(3,  2, "fields",   11),   # Canterbury Plains (largest flat, wheat/sheep)
        _tile(4,  2, "pasture",  12),   # Otago (merino sheep, gold rush country)
        _tile(3,  3, "mountains", 3),   # Fiordland peaks (Mt Aspiring, remote)
        _tile(4,  3, "pasture",   8),   # Southland (sheep — southernmost farmland)
        _tile(2,  3, "forest",   10),   # W Coast (temperate rainforest, untouched)
        _tile(3,  4, "hills",     4),   # Stewart Island / Rakiura (sub-Antarctic)
    ]
    ports = [
        _port(0, -4, ratio=3),           # NW — Northland W (Tasman Sea)
        _port(2, -2, ratio=3),           # NE — Bay of Plenty (Pacific)
        _port(2, -1, "sheep"),           # S N.I. — Wellington (wool export!)
        _port(3,  1, ratio=3),           # N S.I. — Marlborough Sounds
        _port(3,  2, "wheat"),           # E — Canterbury (grain export, Lyttelton)
        _port(4,  2, ratio=3),           # SE — Otago / Dunedin
        _port(3,  4, ratio=3),           # S  — Bluff / Invercargill
    ]
    return MapData(map_id="new_zealand", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# France — 小麦↑ 牧羊↑ 木材↑
# Shape: Brittany protrusion W, roughly hexagonal, Pyrenees S, Alps SE
# N=Normandy/Champagne/Alsace, W=Loire/Landes, C=Massif Central, SE=Alps, S=Pyrenees
# ---------------------------------------------------------------------------

def france_map() -> MapData:
    tiles = [
        # Northern strip: Brittany → Normandy → Champagne → Alsace  (r=-2)
        _tile(-2, -2, "hills",     9),  # Brittany (granite bocage, hedgerows)
        _tile(-1, -2, "fields",    6),  # Normandy (dairy plains)
        _tile( 0, -2, "fields",   11),  # Champagne / Picardy (grain)
        _tile( 1, -2, "forest",    3),  # Ardennes (dense forest)
        # Main body N: Atlantic coast → Paris → Rhine  (r=-1)
        _tile(-2, -1, "pasture",   8),  # Brittany S coast / Vendée (sheep/cattle)
        _tile(-1, -1, "fields",   10),  # Loire Valley (fertile "garden of France")
        _tile( 0, -1, "fields",    5),  # Paris Basin (grain heartland)
        _tile( 1, -1, "mountains", 4),  # Vosges Mountains
        _tile( 2, -1, "mountains", 2),  # Rhine / Alsace plain + Jura
        # Main body S: Landes → Massif Central → Rhône → Alps  (r=0)
        _tile(-2,  0, "forest",    9),  # Landes (vast Atlantic pine forest)
        _tile(-1,  0, "hills",     6),  # Massif Central (volcanic plateau)
        _tile( 0,  0, "fields",    5),  # Rhône-Alpes valley (fertile corridor)
        _tile( 1,  0, "mountains", 4),  # Alps (Savoie/Grenoble peaks)
        _tile( 2,  0, "mountains",11),  # High Alps near Italy border
        # Southern strip: Basque/Gascony → Pyrenees → Languedoc → Provence  (r=1)
        _tile(-1,  1, "pasture",  12),  # Gascony / Basque country (pasture)
        _tile( 0,  1, "mountains", 3),  # Pyrenees
        _tile( 1,  1, "hills",     8),  # Languedoc / Roussillon (S hills)
        _tile( 2,  1, "desert"),        # Camargue / Crau (arid Provence flats)
        # SE tip: Côte d'Azur  (r=2)
        _tile( 2,  2, "pasture",  10),  # Riviera / Provence (Mediterranean scrubland)
    ]
    ports = [
        _port(-1, -2, ratio=3),         # English Channel (Normandy coast)
        _port(-2, -1, ratio=3),         # Atlantic (Brittany S)
        _port(-2,  0, "wood"),          # Atlantic (Landes coast — timber)
        _port(-1,  1, ratio=3),         # Bay of Biscay (Bordeaux/Basque)
        _port( 2,  2, "wheat"),         # Mediterranean (grain export, Marseille)
        _port( 2, -1, ratio=3),         # Rhine / Alsace (E border trade)
    ]
    return MapData(map_id="france", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Germany — 木材↑ 矿石↑
# Shape: wider N (North Sea / Baltic coast), tapers to Bavarian Alps tip S
# N=North German Plain, W=Rhine/Ruhr, C=Thuringia/Harz, E=Saxony, SE=Bavaria, S=Alps
# ---------------------------------------------------------------------------

def germany_map() -> MapData:
    tiles = [
        # Northern coast: North Sea → Holstein → Mecklenburg → Pomerania  (r=-2)
        _tile(0, -2, "pasture",   9),   # Schleswig-Holstein (North Sea coast, cattle)
        _tile(1, -2, "fields",    6),   # Hamburg / Lower Saxony (grain)
        _tile(2, -2, "fields",   11),   # Brandenburg / Berlin area
        _tile(3, -2, "forest",    4),   # Mecklenburg (lake district forests)
        _tile(4, -2, "fields",    3),   # Pomerania (E grain plains)
        # Main body N: Rhine → Westphalia → Saxony  (r=-1)
        _tile(0, -1, "hills",     8),   # Rhine Highlands (Eifel / Hunsrück)
        _tile(1, -1, "mountains", 5),   # Ruhr hills / Sauerland (ore mining!)
        _tile(2, -1, "forest",   10),   # Harz Mountains + Thuringia forest
        _tile(3, -1, "fields",    2),   # Saxony plains (Leipzig area)
        _tile(4, -1, "mountains", 9),   # Ore Mountains (Erzgebirge — tin/silver)
        # Main body S: Rhine Valley → Swabian Alb → Franconia  (r=0)
        _tile(0,  0, "forest",    6),   # Black Forest (Schwarzwald — dense conifers)
        _tile(1,  0, "desert"),          # Upper Rhine Plain (flat floodplain, old marsh)
        _tile(2,  0, "hills",     5),   # Swabian Alb / Franconian hills
        _tile(3,  0, "fields",    4),   # Franconia (Nuremberg, fertile basin)
        _tile(4,  0, "forest",   11),   # E Bavaria forests (Bohemian Forest)
        # Southern Bavaria strip  (r=1)
        _tile(1,  1, "fields",   12),   # Munich / Bavarian plain (grain)
        _tile(2,  1, "pasture",   3),   # Allgäu (dairy — famous cheese region!)
        _tile(3,  1, "mountains", 8),   # Bavarian Alps (Zugspitze)
        # Extreme S tip  (r=2)
        _tile(2,  2, "mountains", 10),  # Berchtesgaden / Austrian Alps border
    ]
    ports = [
        _port(0, -2, ratio=3),          # North Sea coast (Hamburg area)
        _port(4, -2, ratio=3),          # Baltic coast (Stettin/Rostock)
        _port(4, -1, "ore"),            # E — Erzgebirge ore export
        _port(0,  0, "wood"),           # W — Black Forest timber (Rhine barge)
        _port(0, -1, ratio=3),          # W — Rhine river trade
    ]
    return MapData(map_id="germany", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# LARGE MAP LAYOUT — ring 0 + ring 1 + ring 2 + ring 3 = 37 tiles
# Ring 3 goes clockwise from (3, 0).
# ---------------------------------------------------------------------------

LARGE_HEX_COORDS = [
    # Ring 0
    (0, 0),
    # Ring 1
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
    # Ring 2
    (2, 0), (2, -1), (2, -2), (1, -2), (0, -2),
    (-1, -1), (-2, 0), (-2, 1), (-2, 2), (-1, 2), (0, 2), (1, 1),
    # Ring 3
    (3, 0), (2, 1), (1, 2), (0, 3), (-1, 3), (-2, 3),
    (-3, 3), (-3, 2), (-3, 1), (-3, 0), (-2, -1), (-1, -2),
    (0, -3), (1, -3), (2, -3), (3, -3), (3, -2), (3, -1),
]


def _from_large(map_id: str, tt: List[Tuple[str, object]], ports: List[Port]) -> MapData:
    """Build a MapData from 37-tile LARGE_HEX_COORDS."""
    tiles = [_tile(q, r, t, tok) for (q, r), (t, tok) in zip(LARGE_HEX_COORDS, tt)]
    return MapData(map_id=map_id, tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Argentina — 木材↑ 牧羊↑↑ 小麦↑
# Shape: very elongated N-S; NW Andes mountains, N Gran Chaco forests,
#        C Pampas (grain/cattle), S Patagonia steppe, tip = Tierra del Fuego
# ---------------------------------------------------------------------------

def argentina_map() -> MapData:
    tiles = [
        # N Argentina: Gran Chaco → Misiones → Nordeste  (r=-2)
        _tile(0, -2, "forest",    9),   # Gran Chaco (dry tropical forest)
        _tile(1, -2, "fields",    6),   # Misiones / Mesopotamia (subtropical)
        _tile(2, -2, "hills",    11),   # Corrientes / Entre Ríos (hilly NE)
        # NW Andes → N interior  (r=-1)
        _tile(-1,-1, "desert"),          # Puna plateau (Atacama edge, arid 3500m+)
        _tile( 0,-1, "mountains", 4),   # NW Andes (Jujuy / Salta peaks)
        _tile( 1,-1, "fields",   10),   # Tucumán / Santiago del Estero (sugar, cotton)
        _tile( 2,-1, "pasture",   3),   # Chaco S / Formosa dry plains
        # Pampas — grain and cattle heartland  (r=0)
        _tile(-1, 0, "mountains", 8),   # Andean foothills (Mendoza, wine country)
        _tile( 0, 0, "fields",    5),   # Pampas W (grain, soy)
        _tile( 1, 0, "fields",    2),   # Pampas E (Buenos Aires province)
        _tile( 2, 0, "pasture",   9),   # Pampas S (cattle ranches)
        # S Pampas / N Patagonia  (r=1)
        _tile(-1, 1, "pasture",   6),   # La Pampa (cattle, dry grassland)
        _tile( 0, 1, "fields",    5),   # S Pampas (winter wheat)
        _tile( 1, 1, "hills",     4),   # Sierras of Buenos Aires (Tandilia/Ventania)
        # Patagonia  (r=2, r=3)
        _tile(-1, 2, "pasture",  11),   # N Patagonia (Merino sheep — world famous!)
        _tile( 0, 2, "pasture",  12),   # Patagonia plateau (vast wind-swept steppe)
        _tile(-1, 3, "mountains", 3),   # Patagonian Andes (lakes, Nahuel Huapi)
        _tile( 0, 3, "forest",    8),   # Andean forests (lenga beech, ancient)
        # Tierra del Fuego  (r=4)
        _tile(-1, 4, "hills",    10),   # Tierra del Fuego (Ushuaia, end of the world)
    ]
    ports = [
        _port(2, -2, ratio=3),           # NE — Río de la Plata / Paraná delta
        _port(2,  0, ratio=3),           # E  — Buenos Aires coast (Atlantic)
        _port(1,  1, ratio=3),           # SE — Mar del Plata
        _port(0,  2, "sheep"),           # S  — Patagonian coast (wool export!)
        _port(-1, 3, ratio=3),           # SW — Patagonian fjords (Comahue)
        _port(-1, 4, ratio=3),           # S  — Tierra del Fuego / Ushuaia
    ]
    return MapData(map_id="argentina", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# South Africa — 矿石↑↑ 砖块↑
# Shape: triangular pointing S; N=Limpopo/Highveld, W=Kalahari, E=Drakensberg/KZN,
#        S narrows to Cape of Good Hope; Witwatersrand = gold mines
# ---------------------------------------------------------------------------

def south_africa_map() -> MapData:
    tiles = [
        # N border strip: Limpopo → KZN N  (r=-1)
        _tile(-2,-1, "mountains", 9),   # Limpopo escarpment (N Drakensberg)
        _tile(-1,-1, "pasture",   6),   # Bushveld / Kruger (savanna)
        _tile( 0,-1, "fields",   11),   # Limpopo Valley (subtropical farming)
        _tile( 1,-1, "hills",     3),   # KwaZulu-Natal N (sugarcane hills)
        _tile( 2,-1, "forest",    8),   # Mozambique border forests
        # Main body: Kalahari → Highveld → Drakensberg  (r=0)
        _tile(-3, 0, "desert"),          # Kalahari Desert (NW South Africa)
        _tile(-2, 0, "mountains",10),   # Witwatersrand (GOLD MINES — Johannesburg!)
        _tile(-1, 0, "hills",     5),   # Free State (high grassland hills)
        _tile( 0, 0, "fields",    2),   # KZN midlands (agriculture)
        _tile( 1, 0, "mountains", 9),   # Drakensberg (uKhahlamba, spectacular!)
        _tile( 2, 0, "hills",     6),   # Zululand coast hills
        # Interior → coastal  (r=1)
        _tile(-2, 1, "pasture",   5),   # Great Karoo (semi-arid, sheep)
        _tile(-1, 1, "hills",     4),   # Little Karoo (Oudtshoorn, ostrich!)
        _tile( 0, 1, "fields",   11),   # N Cape / Boland (wheat)
        _tile( 1, 1, "pasture",  12),   # E Cape (Merino sheep — world famous wool)
        _tile( 2, 1, "hills",     3),   # Transkei / Wild Coast
        # Cape region  (r=2)
        _tile(-1, 2, "mountains", 8),   # Cape Fold Mountains (beautiful wine ranges)
        _tile( 0, 2, "pasture",  10),   # Cape Winelands (Stellenbosch, Paarl)
        # Cape of Good Hope tip  (r=3)
        _tile( 0, 3, "hills",     4),   # Cape Peninsula (Cape of Good Hope)
    ]
    ports = [
        _port(-3,  0, ratio=3),          # W  — Atlantic coast (Namaqualand)
        _port(-1,  2, "ore"),            # SW — Cape Town (ore/gold export!)
        _port( 0,  3, ratio=3),          # S  — Cape of Good Hope
        _port( 2,  1, ratio=3),          # E  — Wild Coast / Port Elizabeth
        _port( 2,  0, ratio=3),          # E  — Durban (KZN)
        _port(-2,  1, "sheep"),          # W  — Karoo wool export
    ]
    return MapData(map_id="south_africa", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Italy — 砖块↑↑ 矿石↑
# Shape: iconic boot — Alps N, wide Po Valley, Apennine spine, boot toe SE,
#        Sicily island SE, Sardinia island W (disconnected)
# ---------------------------------------------------------------------------

def italy_map() -> MapData:
    tiles = [
        # Sardinia — separate island far W
        _tile(-3,-1, "forest",    9),   # Sardinia N (cork oak, macchia)
        _tile(-3, 0, "hills",     6),   # Sardinia S (barren plateau, nuraghi)
        # Alps — N barrier
        _tile(-1,-2, "mountains",11),   # W Alps (Mont Blanc, Valle d'Aosta)
        _tile( 0,-2, "mountains", 4),   # Central Alps (Bergamo/Brescia peaks)
        _tile( 1,-2, "mountains", 3),   # Dolomites (spectacular!)
        _tile( 2,-2, "hills",     8),   # Venezia Giulia / Karst plateau
        # Po Valley — Italy's breadbasket
        _tile( 0,-1, "fields",   10),   # Po Valley W (rice, wheat — most fertile!)
        _tile( 1,-1, "fields",    5),   # Po Valley C (Lombardy, maize)
        _tile( 2,-1, "fields",    2),   # Po Valley E (Veneto, corn)
        _tile( 3,-1, "hills",     9),   # Venezia hills + Trieste coast
        # Central Italy — Apennine spine begins
        _tile( 1, 0, "hills",     6),   # Tuscany (olive, wine, Chianti hills)
        _tile( 2, 0, "hills",     5),   # Umbria / Marche (Apennine foothills)
        # S Italy — boot leg
        _tile( 2, 1, "mountains", 4),   # Apennines (rocky spine of the boot)
        _tile( 3, 0, "desert"),          # Puglia Tavoliere (driest flat plain in Italy)
        _tile( 3, 1, "pasture",  11),   # Calabria / Basilicata (rough, sparse)
        _tile( 2, 2, "hills",    12),   # Calabria coast (boot heel area)
        # Boot toe
        _tile( 3, 2, "hills",     3),   # Reggio Calabria (boot toe, Strait of Messina)
        # Sicily — island
        _tile( 4, 0, "mountains", 8),   # Sicily interior (Mt Etna volcano!)
        _tile( 4, 1, "fields",   10),   # Sicily coast (ancient granary of Rome)
    ]
    ports = [
        _port(-3, -1, ratio=3),          # W  — Sardinia (Tyrrhenian Sea)
        _port(-1, -2, ratio=3),          # NW — Genova / Ligurian coast
        _port( 3, -1, ratio=3),          # NE — Venice / Adriatic
        _port( 3,  1, "wheat"),          # SE — Puglia/Taranto (grain export)
        _port( 3,  2, ratio=3),          # S  — Messina strait / boot toe
        _port( 4,  1, ratio=3),          # S  — Sicily S coast
        _port( 2,  1, "ore"),            # W  — Tyrrhenian (Apennine ore mines)
    ]
    return MapData(map_id="italy", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Scandinavia — 木材↑↑ 矿石↑
# Shape: elongated N-S peninsula; Norway W (fjord coast + mountains),
#        Sweden E (taiga forests), Finland SE (lake district), Denmark S (farming)
# ---------------------------------------------------------------------------

def scandinavia_map() -> MapData:
    tiles = [
        # Far N Norway — Arctic  (r=-4)
        _tile(0, -4, "mountains", 9),   # Finnmark plateau (bare arctic tundra)
        _tile(1, -4, "forest",    6),   # N Finland / Lapland (boreal taiga)
        # N Scandinavia  (r=-3)
        _tile(-1,-3, "mountains",11),   # Lofoten / Vesterålen (dramatic fjord mts)
        _tile( 0,-3, "desert"),          # Hardangervidda (sub-arctic high plateau, barren)
        _tile( 1,-3, "forest",    4),   # Swedish Lapland (conifer taiga)
        # Middle  (r=-2)
        _tile(-1,-2, "forest",    3),   # W Norway fjords / Bergen (dense forest)
        _tile( 0,-2, "mountains", 8),   # Jotunheimen / Norwegian Mts (highest peaks)
        _tile( 1,-2, "forest",   10),   # Central Sweden (vast taiga)
        _tile( 2,-2, "forest",    5),   # E Finland (lake district, endless forest)
        # S Scandinavia  (r=-1)
        _tile(-1,-1, "pasture",   2),   # S Norway coast (coastal grazing, fjords)
        _tile( 0,-1, "fields",    9),   # Oslo fjord / E Norway (farmland)
        _tile( 1,-1, "forest",    6),   # S Sweden / Götaland (forests)
        _tile( 2,-1, "fields",    5),   # SE Sweden / W Finland coast (grain)
        # Denmark / S Sweden  (r=0)
        _tile( 0, 0, "fields",    4),   # Central Sweden (Mälaren, fertile plains)
        _tile( 1, 0, "hills",    11),   # Kattegat / Blekinge coast hills
        _tile( 2, 0, "fields",   12),   # Skåne (southernmost, most fertile in Sweden!)
        # Denmark  (r=1, r=2)
        _tile( 0, 1, "fields",    3),   # Jutland (Danish mainland, dairy/grain)
        _tile( 1, 1, "pasture",   8),   # Danish islands (Funen, Sjælland — cattle)
        _tile( 0, 2, "pasture",  10),   # S Jutland tip (livestock coast)
    ]
    ports = [
        _port( 0, -4, ratio=3),          # N  — Arctic Ocean (Nordkapp)
        _port(-1, -2, "wood"),           # W  — Bergen fjords (timber export)
        _port(-1, -1, ratio=3),          # W  — Stavanger (North Sea oil/fishing)
        _port( 2, -2, ratio=3),          # E  — Finnish coast (Baltic)
        _port( 2,  0, ratio=3),          # SE — Skåne / Øresund strait
        _port( 1,  1, ratio=3),          # S  — Danish straits (major trade route!)
        _port( 0, -2, "ore"),            # C  — Iron ore (Kiruna mines via Narvik)
    ]
    return MapData(map_id="scandinavia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Spain — 小麦↑ 牧羊↑ 砖块↑
# Shape: rectangular Iberian Peninsula; Galicia NW, Pyrenees NE, Meseta center,
#        Andalusia S, SE Almería (driest place in Europe = desert)
# ---------------------------------------------------------------------------

def spain_map() -> MapData:
    tiles = [
        # N strip: Galicia → Cantabria → Basque → Pyrenees  (r=-2)
        _tile(-2,-2, "hills",     9),   # Galicia (granite coast, rain, fishing)
        _tile(-1,-2, "mountains", 6),   # Cantabrian Mts (Picos de Europa)
        _tile( 0,-2, "hills",    11),   # Basque Country (Green Spain coast)
        _tile( 1,-2, "mountains", 4),   # Pyrenees (high barrier with France)
        # N interior: Asturias forests → Castile-León → Aragon → Catalonia  (r=-1)
        _tile(-2,-1, "forest",    3),   # Asturias / Galicia S (Atlantic oak forest)
        _tile(-1,-1, "fields",    8),   # Castile-León (Meseta N, vast wheat!)
        _tile( 0,-1, "fields",   10),   # Ebro Valley (fertile, wine/crops)
        _tile( 1,-1, "hills",     5),   # Catalonia hills (Costa Brava)
        _tile( 2,-1, "hills",     2),   # Tarragona coast (S Catalonia)
        # Central Meseta: Extremadura → Castile La Mancha → Valencia  (r=0)
        _tile(-2, 0, "pasture",   9),   # Extremadura (cork oak dehesa, pigs/cattle)
        _tile(-1, 0, "fields",    6),   # Castile La Mancha (Don Quijote's windmills, grain)
        _tile( 0, 0, "hills",     5),   # Aragón interior (plateau, teruel)
        _tile( 1, 0, "hills",     4),   # Valencia hills (orange groves inland)
        _tile( 2, 0, "pasture",  11),   # Murcia N (dry hills)
        # S strip: Andalusia → Granada → Almería  (r=1)
        _tile(-1, 1, "pasture",  12),   # Andalusia W / Seville (sunflower, cattle)
        _tile( 0, 1, "fields",    3),   # Guadalquivir valley (olive, wheat — ancient granary)
        _tile( 1, 1, "desert"),          # Almería / SE coast (driest place in Europe!)
        _tile( 2, 1, "hills",     8),   # Costa del Sol hills (Málaga/Granada)
        # Gibraltar tip  (r=2)
        _tile( 0, 2, "hills",    10),   # Cádiz / Strait of Gibraltar
    ]
    ports = [
        _port(-2, -2, ratio=3),          # NW — Galicia (Atlantic fishing!)
        _port( 0, -2, ratio=3),          # N  — Cantabrian Sea
        _port( 2, -1, ratio=3),          # NE — Barcelona / Catalonia Med
        _port( 2,  0, ratio=3),          # E  — Valencia (oranges)
        _port( 0,  2, ratio=3),          # S  — Cádiz (historic trade port)
        _port(-1,  1, "wheat"),          # SW — Seville / Atlantic (grain export)
        _port(-2,  0, "sheep"),          # W  — Extremadura / Lisbon border (wool)
    ]
    return MapData(map_id="spain", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Turkey — 小麦↑ 牧羊↑ 矿石↑
# Shape: wide E-W rectangle (Asia Minor); Black Sea coast N, Aegean W, Med S,
#        Pontus Mts N coast, Taurus Mts S, Central Anatolian plateau = desert steppe
# ---------------------------------------------------------------------------

def turkey_map() -> MapData:
    tiles = [
        # N strip — Black Sea coast  (r=-1)
        _tile(-2,-1, "hills",     9),   # Thrace / Istanbul (rolling hills, Bosphorus)
        _tile(-1,-1, "fields",    6),   # Marmara region (fertile, near Istanbul)
        _tile( 0,-1, "mountains",11),   # Pontus Mountains (Black Sea coast range)
        _tile( 1,-1, "forest",    4),   # N Anatolian forest (Black Sea coast)
        _tile( 2,-1, "mountains", 3),   # E Pontus Mts (Kaçkar peaks)
        _tile( 3,-1, "mountains", 8),   # NE Turkey / Rize coast mts
        _tile( 4,-1, "mountains",10),   # E Turkey / Caucasus approach (Ararat!)
        # Main body — Anatolian plateau  (r=0)
        _tile(-2, 0, "fields",    5),   # W Anatolia (Aegean coast, fertile, wine/olives)
        _tile(-1, 0, "hills",     2),   # C-W Anatolia (plateau W, Ankara outskirts)
        _tile( 0, 0, "desert"),          # Central Anatolia (Konya / salt lake, arid steppe)
        _tile( 1, 0, "fields",    9),   # C Anatolia (Ankara region, grain)
        _tile( 2, 0, "pasture",   6),   # E Anatolia plateau (vast pastoral lands)
        _tile( 3, 0, "pasture",   5),   # SE Anatolia (Tigris-Euphrates source, sheep)
        _tile( 4, 0, "mountains", 4),   # E Turkey / Armenia border (Mt Ararat 5137m)
        # S strip — Mediterranean / Taurus coast  (r=1)
        _tile(-1, 1, "hills",    11),   # SW Turkey (Aegean / Turkish Riviera hills)
        _tile( 0, 1, "pasture",  12),   # S Anatolia (Taurus foothills, sheep)
        _tile( 1, 1, "mountains", 3),   # Taurus Mountains (S barrier)
        _tile( 2, 1, "fields",    8),   # Çukurova / Cilicia (cotton/grain — very fertile!)
        _tile( 3, 1, "hills",    10),   # SE Turkey (Kurdish Highlands, Diyarbakir)
    ]
    ports = [
        _port(-2, -1, ratio=3),          # NW — Istanbul / Bosphorus (major strait!)
        _port( 4, -1, ratio=3),          # NE — E Black Sea coast
        _port(-2,  0, ratio=3),          # W  — Aegean coast (Izmir)
        _port(-1,  1, ratio=3),          # SW — Antalya / Bodrum (Med)
        _port( 2,  1, "wheat"),          # SE — Mersin / Çukurova (grain port)
        _port( 0, -1, "wood"),           # N  — Zonguldak (Black Sea, coal/timber)
        _port( 3,  1, ratio=3),          # SE — Iskenderun coast
    ]
    return MapData(map_id="turkey", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Vietnam — 木材↑↑ 砖块↑
# Shape: elongated narrow S-curve (N wide, central waist, S Mekong widens);
#        NW mountains (Sapa/Fansipan), Red River Delta N, Annamite spine, Mekong S
# ---------------------------------------------------------------------------

def vietnam_map() -> MapData:
    tiles = [
        # N Vietnam: NW mountains + Red River Delta  (r=-3)
        _tile(-1,-3, "mountains", 9),   # NW Vietnam (Sapa / Fansipan 3143m — highest peak)
        _tile( 0,-3, "fields",    8),   # Red River Delta (Hanoi — intensive rice!)
        _tile( 1,-3, "forest",    6),   # Gulf of Tonkin coast / Quảng Ninh
        # N-Central (r=-2)
        _tile(-1,-2, "mountains", 4),   # NW highlands (Điện Biên Phủ — famous battle site)
        _tile( 0,-2, "forest",    3),   # N highland forests (bamboo / tropical)
        _tile( 1,-2, "hills",     5),   # N-C coast hills (Thanh Hóa)
        # Central — Annamite spine begins  (r=-1)
        _tile(-1,-1, "mountains",10),   # Annamite Range (Trường Sơn, steep & forested)
        _tile( 0,-1, "hills",    11),   # Central coast plain (Huế — ancient capital)
        _tile( 1,-1, "forest",    2),   # Central Highlands N / coastal forest
        # Narrow waist — Da Nang  (r=0)
        _tile( 0, 0, "hills",     9),   # Đà Nẵng coast (famous Marble Mountains)
        _tile( 1, 0, "mountains", 6),   # Central Highlands (Kon Tum, Đà Lạt plateau)
        _tile( 2, 0, "forest",    5),   # S Central forests (coffee growing region!)
        # S Central  (r=1)
        _tile( 1, 1, "hills",     4),   # Nha Trang / Bình Định coast
        _tile( 2, 1, "forest",   11),   # S Highlands (coffee, rubber — major export!)
        # Mekong approach  (r=2)
        _tile( 2, 2, "fields",   12),   # Mekong Delta approach (rice paddies)
        _tile( 3, 1, "pasture",   3),   # S Vietnam plains (Đồng Nai)
        # Mekong Delta  (r=3)
        _tile( 2, 3, "fields",    8),   # Mekong Delta (Cần Thơ — 2nd largest rice delta!)
        _tile( 3, 2, "hills",    10),   # SE Vietnam coast (Vũng Tàu oil coast)
        _tile( 3, 3, "hills",     4),   # Cà Mau peninsula (S tip — mangroves)
    ]
    ports = [
        _port( 1,-3, ratio=3),           # N  — Gulf of Tonkin (Hải Phòng port)
        _port( 1,-2, ratio=3),           # NC — N-C coast
        _port( 0,-1, ratio=3),           # C  — Đà Nẵng / central coast
        _port( 1, 1, ratio=3),           # SC — Nha Trang (fishing / tourism)
        _port( 2, 2, "wheat"),           # S  — Mekong Delta (rice export!)
        _port( 3, 3, ratio=3),           # S  — Cà Mau (S tip fishing coast)
        _port( 0,-3, "wood"),            # NW — Hanoi river port (timber upstream)
    ]
    return MapData(map_id="vietnam", tiles=tiles, ports=ports)


# ===========================================================================
# LARGE MAPS — 37-tile ring-3 layout (LARGE_HEX_COORDS)
# Token distribution for ~30 resource tiles (7 deserts per map):
#   2(2), 3(3), 4(3), 5(4), 6(3), 8(3), 9(4), 10(3), 11(3), 12(2) = 30
# ===========================================================================

# ---------------------------------------------------------------------------
# Africa XL — 矿石↑↑ 木材↑↑  (大型非洲大陆，沙漠横贯北部)
# Layout note: negative r = north, positive r = south, negative q = west
# ---------------------------------------------------------------------------

def africa_xl_map() -> MapData:
    tt = [
        # Ring 0
        ("forest",    9),    # (0,0)  Congo Basin center
        # Ring 1
        ("mountains", 6),    # (1,0)  East Africa Rift
        ("fields",    4),    # (1,-1) Ethiopia/Nile
        ("desert",    None), # (0,-1) Sudan border
        ("forest",   11),    # (-1,0) DRC
        ("hills",     3),    # (-1,1) Angola/Zambia
        ("forest",    8),    # (0,1)  Congo South
        # Ring 2
        ("mountains",10),    # (2,0)  Tanzania/Rift Valley
        ("fields",    5),    # (2,-1) Somalia/Kenya coast
        ("desert",    None), # (2,-2) Horn of Africa
        ("desert",    None), # (1,-2) North Sudan
        ("desert",    None), # (0,-2) Sahara East
        ("desert",    None), # (-1,-1) Sahara Central
        ("forest",    2),    # (-2,0) Nigeria/Cameroon
        ("pasture",   9),    # (-2,1) Gabon/DRC West
        ("hills",     6),    # (-2,2) Namibia
        ("fields",    5),    # (-1,2) Zambia/Zimbabwe
        ("mountains", 4),    # (0,2)  Mozambique
        ("mountains",11),    # (1,1)  Uganda/Kenya
        # Ring 3
        ("mountains",12),    # (3,0)  Madagascar
        ("hills",     3),    # (2,1)  South Africa East
        ("hills",     8),    # (1,2)  KwaZulu-Natal
        ("fields",   10),    # (0,3)  Cape of Good Hope
        ("pasture",   5),    # (-1,3) Botswana/Kalahari
        ("hills",     9),    # (-2,3) Namibia South
        ("forest",    6),    # (-3,3) Angola South
        ("forest",    4),    # (-3,2) DRC South
        ("forest",   11),    # (-3,1) Nigeria/Benin
        ("pasture",   2),    # (-3,0) Ivory Coast/Ghana
        ("forest",    9),    # (-2,-1) West Sahel
        ("desert",    None), # (-1,-2) Mali/Niger
        ("desert",    None), # (0,-3) Algeria/Tunisia
        ("desert",    None), # (1,-3) Libya/Egypt
        ("desert",    None), # (2,-3) Egypt/Sinai
        ("desert",    None), # (3,-3) Arabian peninsula
        ("desert",    None), # (3,-2) Red Sea coast
        ("fields",    8),    # (3,-1) East Africa coast
    ]
    return _from_large("africa_xl", tt, [
        _port( 3,  0, "ore",   side=0),
        _port( 1,  2, ratio=3, side=5),
        _port( 0,  3, ratio=3, side=5),
        _port(-2,  3, "wood",  side=4),
        _port(-3,  1, ratio=3, side=3),
        _port(-3,  0, "sheep", side=3),
        _port(-2, -1, ratio=3, side=2),
        _port( 3, -1, ratio=3, side=1),
        _port( 2,  1, ratio=3, side=0),
    ])


# ---------------------------------------------------------------------------
# Eurasia XL — 资源均衡大陆  (欧亚大陆，从西欧到东亚)
# desert=5, forest=8, fields=7, mountains=7, pasture=6, hills=4
# ---------------------------------------------------------------------------

def eurasia_xl_map() -> MapData:
    tt = [
        # Ring 0
        ("fields",    9),    # (0,0)  Central Asia steppe
        # Ring 1
        ("mountains", 6),    # (1,0)  Himalayas
        ("fields",    4),    # (1,-1) North China
        ("forest",   11),    # (0,-1) Siberia
        ("fields",    3),    # (-1,0) Middle East/Persia
        ("pasture",   8),    # (-1,1) Central Europe
        ("mountains",10),    # (0,1)  South Asia
        # Ring 2
        ("mountains", 5),    # (2,0)  Southeast Asia/China coast
        ("fields",    2),    # (2,-1) Korea/Japan
        ("forest",    9),    # (2,-2) Far East Russia
        ("forest",    6),    # (1,-2) Siberia East
        ("forest",    5),    # (0,-2) West Siberia
        ("desert",    None), # (-1,-1) Sahara/Arabia
        ("desert",    None), # (-2,0) North Africa
        ("pasture",   4),    # (-2,1) Western Europe
        ("fields",   11),    # (-2,2) France/Germany
        ("hills",    12),    # (-1,2) Alpine/Balkans
        ("mountains", 3),    # (0,2)  Turkey/Caucasus
        ("pasture",   8),    # (1,1)  India
        # Ring 3
        ("mountains",10),    # (3,0)  Pacific Rim
        ("mountains", 5),    # (2,1)  Indochina
        ("hills",     9),    # (1,2)  Indian Subcontinent S
        ("pasture",   6),    # (0,3)  Arabian Sea coast
        ("desert",    None), # (-1,3) Gulf region
        ("desert",    None), # (-2,3) North Africa W
        ("desert",    None), # (-3,3) Morocco/Sahara
        ("fields",    4),    # (-3,2) Iberian Peninsula
        ("pasture",  11),    # (-3,1) British Isles
        ("forest",    2),    # (-3,0) Scandinavia/Iceland
        ("forest",    9),    # (-2,-1) Northern Russia
        ("forest",    6),    # (-1,-2) Ural region
        ("forest",    4),    # (0,-3)  North Siberia
        ("forest",   11),    # (1,-3)  Yakutia
        ("forest",    3),    # (2,-3)  Kamchatka
        ("mountains", 8),    # (3,-3) Japan/Sakhalin
        ("mountains",10),    # (3,-2) Taiwan/Philippines
        ("hills",     5),    # (3,-1) South China
    ]
    return _from_large("eurasia_xl", tt, [
        _port( 3,  0, ratio=3, side=0),
        _port( 2,  1, "ore",   side=0),
        _port( 0,  3, ratio=3, side=5),
        _port(-2,  3, ratio=3, side=4),
        _port(-3,  2, "wheat", side=3),
        _port(-3,  0, "wood",  side=3),
        _port(-2, -1, ratio=3, side=2),
        _port( 0, -3, ratio=3, side=2),
        _port( 2, -3, ratio=3, side=1),
        _port( 3, -1, "sheep", side=1),
    ])


# ---------------------------------------------------------------------------
# Americas XL — 木材↑↑ 小麦↑ 牧羊↑  (南北美洲全图)
# desert=3, forest=10, fields=8, pasture=7, hills=5, mountains=4
# ---------------------------------------------------------------------------

def americas_xl_map() -> MapData:
    tt = [
        # Ring 0
        ("forest",    9),    # (0,0)  Amazon Center
        # Ring 1
        ("forest",    6),    # (1,0)  Brazil East
        ("fields",    4),    # (1,-1) Caribbean/Cuba
        ("forest",   11),    # (0,-1) Central America
        ("pasture",   3),    # (-1,0) Pacific Coast
        ("fields",    8),    # (-1,1) Pampas/Uruguay
        ("hills",    10),    # (0,1)  Argentina North
        # Ring 2
        ("mountains", 5),    # (2,0)  Atlantic Coast Brazil
        ("fields",    2),    # (2,-1) Florida/SE USA
        ("forest",    9),    # (2,-2) Eastern USA
        ("fields",    6),    # (1,-2) Great Lakes/NE USA
        ("forest",    5),    # (0,-2) Midwest USA
        ("fields",    4),    # (-1,-1) Great Plains
        ("forest",   11),    # (-2,0) Pacific Northwest
        ("pasture",  12),    # (-2,1) Chilean coast
        ("mountains", 3),    # (-2,2) Andes South
        ("hills",     8),    # (-1,2) Patagonia
        ("pasture",  10),    # (0,2)  Argentina South
        ("hills",     5),    # (1,1)  Atlantic coast S
        # Ring 3
        ("mountains", 9),    # (3,0)  Caribbean Islands
        ("forest",    6),    # (2,1)  Guyana/Suriname
        ("forest",    4),    # (1,2)  Southern Brazil
        ("hills",    11),    # (0,3)  Tierra del Fuego
        ("mountains", 2),    # (-1,3) Cape Horn
        ("pasture",   9),    # (-2,3) West Patagonia
        ("pasture",   6),    # (-3,3) Chilean fjords
        ("mountains", 4),    # (-3,2) Andes Central
        ("fields",   11),    # (-3,1) Peru/Ecuador
        ("forest",    3),    # (-3,0) Colombia
        ("forest",    8),    # (-2,-1) Mexico
        ("desert",    None), # (-1,-2) Sonora Desert
        ("fields",   10),    # (0,-3) California
        ("fields",    5),    # (1,-3) SW USA/Texas
        ("pasture",   9),    # (2,-3) SE USA/Gulf Coast
        ("desert",    None), # (3,-3) Bermuda/Atlantic
        ("desert",    None), # (3,-2) Open Atlantic
        ("forest",    8),    # (3,-1) Labrador/Newfoundland
    ]
    return _from_large("americas_xl", tt, [
        _port( 3,  0, "wood",  side=0),
        _port( 2,  1, ratio=3, side=0),
        _port( 0,  3, ratio=3, side=5),
        _port(-2,  3, "sheep", side=4),
        _port(-3,  1, "ore",   side=3),
        _port(-3,  0, ratio=3, side=3),
        _port(-2, -1, ratio=3, side=2),
        _port( 0, -3, "wheat", side=2),
        _port( 2, -3, ratio=3, side=1),
        _port( 3, -1, ratio=3, side=1),
    ])


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MAP_REGISTRY = {
    # Standard maps (19 tiles)
    "china":        china_map,
    "japan":        japan_map,
    "usa":          usa_map,
    "europe":       europe_map,
    "uk":           uk_map,
    "australia":    australia_map,
    "brazil":       brazil_map,
    "antarctica":   antarctica_map,
    "india":        india_map,
    "canada":       canada_map,
    "russia":       russia_map,
    "egypt":        egypt_map,
    "mexico":       mexico_map,
    "korea":        korea_map,
    "indonesia":    indonesia_map,
    "new_zealand":  new_zealand_map,
    "france":       france_map,
    "germany":      germany_map,
    # New standard maps
    "argentina":    argentina_map,
    "south_africa": south_africa_map,
    "italy":        italy_map,
    "scandinavia":  scandinavia_map,
    "spain":        spain_map,
    "turkey":       turkey_map,
    "vietnam":      vietnam_map,
    # Large maps (37 tiles)
    "africa_xl":    africa_xl_map,
    "eurasia_xl":   eurasia_xl_map,
    "americas_xl":  americas_xl_map,
}


def get_static_map(map_id: str) -> MapData:
    fn = MAP_REGISTRY.get(map_id)
    if not fn:
        raise ValueError(f"Unknown static map: {map_id}")
    return normalize_ports(fn())
