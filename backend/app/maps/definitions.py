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
        # 4 ports spread around the perimeter — ore-heavy theme
        _port(-2, -1, ratio=3, side=3),   # 3:1 NW  — left face
        _port( 2, -2, ratio=3, side=1),   # 3:1 NE  — upper-right face
        _port( 2,  1, "ore",   side=0),   # ore 2:1 E — right face
        _port( 0,  2, ratio=3, side=5),   # 3:1 S   — down face
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
        # Many ports — Japan is an island nation; 8 ports on 8 distinct perimeter tiles
        # Island 1
        _port(-3,  0, ratio=3,   side=3),  # 3:1   NW left face
        _port(-2, -1, "wood",    side=2),  # wood  NW upper face
        # Island 2
        _port( 0, -2, ratio=3,   side=2),  # 3:1   N upper face
        _port( 1, -2, "sheep",   side=1),  # sheep NE upper-right face
        _port( 1, -1, ratio=3,   side=0),  # 3:1   E right face
        # Island 3
        _port( 0,  2, "brick",   side=5),  # brick S down face
        _port(-1,  2, ratio=3,   side=3),  # 3:1   SW left face
        # Island 4
        _port( 3,  0, ratio=3,   side=0),  # 3:1   SE right face
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
        # 7 ports on 7 distinct perimeter tiles — wheat/wood/sheep theme
        _port( 0, -2, ratio=3,   side=2),  # 3:1   N  upper face
        _port( 2, -2, "wood",    side=1),  # wood  NE upper-right face
        _port( 2, -1, ratio=3,   side=0),  # 3:1   E  right face
        _port( 2,  1, ratio=3,   side=5),  # 3:1   SE down face
        _port( 1,  2, "sheep",   side=5),  # sheep S  down face  (different tile from above)
        _port(-2,  0, "wheat",   side=3),  # wheat W  left face
        _port(-1, -2, ratio=3,   side=2),  # 3:1   NW upper face (different tile from N)
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
        # 9 ports on 9 distinct perimeter tiles — wheat/sheep/brick/ore theme
        _port(-1, -1, ratio=3,   side=3),  # 3:1   NW left face
        _port( 0, -2, "wheat",   side=2),  # wheat N  upper face
        _port( 1, -2, ratio=3,   side=1),  # 3:1   NE upper-right face
        _port( 2, -1, "sheep",   side=1),  # sheep E  upper-right face  (different tile)
        _port( 3, -1, ratio=3,   side=0),  # 3:1   E  right face
        _port( 3,  0, "brick",   side=1),  # brick SE upper-right face  (different tile)
        _port( 2,  1, ratio=3,   side=0),  # 3:1   SE right face
        _port( 1,  2, "ore",     side=5),  # ore   S  down face
        _port(-1,  2, ratio=3,   side=4),  # 3:1   SW lower-left face
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
        # 8 ports on 8 distinct perimeter tiles — sheep/ore theme
        # Scotland
        _port(-1, -3, ratio=3,  side=2),  # 3:1   N  upper face
        _port( 0, -3, "sheep",  side=2),  # sheep N  upper face  (different tile)
        # England east coast
        _port( 1, -2, ratio=3,  side=1),  # 3:1   NE upper-right face
        _port( 1, -1, ratio=3,  side=0),  # 3:1   E  right face
        _port( 1,  0, "ore",    side=0),  # ore   E  right face  (different tile)
        # England south / Wales
        _port(-2,  1, ratio=3,  side=4),  # 3:1   SW lower-left face
        # Ireland
        _port(-3,  1, "sheep",  side=4),  # sheep W  lower-left face
        _port(-3, -1, ratio=3,  side=3),  # 3:1   W  left face
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
        # 7 ports on 7 distinct perimeter tiles — ore/sheep theme (desert-heavy interior)
        _port(-2, -1, "ore",    side=3),  # ore   W  left face
        _port(-1, -2, ratio=3,  side=2),  # 3:1   NW upper face
        _port( 0, -2, ratio=3,  side=2),  # 3:1   N  upper face  (different tile)
        _port( 2, -2, "sheep",  side=1),  # sheep NE upper-right face
        _port( 2,  0, ratio=3,  side=0),  # 3:1   E  right face
        _port( 0,  2, "ore",    side=5),  # ore   S  down face
        _port(-1,  2, ratio=3,  side=4),  # 3:1   SW lower-left face
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
        # 7 ports on 7 distinct perimeter tiles — wood/wheat theme (forest-heavy)
        _port(-2, -1, "wood",   side=3),  # wood  W  left face
        _port(-1, -2, ratio=3,  side=2),  # 3:1   NW upper face
        _port( 0, -2, ratio=3,  side=2),  # 3:1   N  upper face  (different tile)
        _port( 2, -1, ratio=3,  side=1),  # 3:1   NE upper-right face
        _port( 2,  0, "wheat",  side=0),  # wheat E  right face
        _port( 1,  2, ratio=3,  side=5),  # 3:1   SE down face
        _port(-1,  2, ratio=3,  side=4),  # 3:1   SW lower-left face
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
# fields=6 pasture=5 hills=3 mountains=2 forest=2 desert=1
# ---------------------------------------------------------------------------

def india_map() -> MapData:
    tt = [
        ("desert",    None), ("fields",    9),  ("pasture",   6),
        ("fields",    4),    ("pasture",  11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("fields",    5),
        ("pasture",   2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("hills",    12),    ("fields",    3),  ("pasture",   8),
        ("forest",   10),
    ]
    return _from_std("india", tt, [
        _port( 2, -1, "wheat", side=0),
        _port(-2,  1, "sheep", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
        _port( 1,  1, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Canada — 木材↑↑ 小麦↑  (北方森林·大草原)
# forest=6 fields=5 pasture=3 mountains=2 hills=2 desert=1
# ---------------------------------------------------------------------------

def canada_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("fields",    6),
        ("forest",    4),    ("fields",   11),  ("pasture",   3),
        ("forest",    8),    ("mountains",10),  ("forest",    5),
        ("hills",     2),    ("forest",    9),  ("fields",    6),
        ("pasture",   5),    ("mountains", 4),  ("fields",   11),
        ("hills",    12),    ("fields",    3),  ("pasture",   8),
        ("forest",   10),
    ]
    return _from_std("canada", tt, [
        _port( 2, -1, "wood",  side=0),
        _port(-2,  1, "wheat", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  0, ratio=3, side=3),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Russia — 木材↑ 矿石↑↑  (泰加林·乌拉尔山)
# forest=5 mountains=4 fields=3 hills=3 pasture=3 desert=1
# ---------------------------------------------------------------------------

def russia_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("mountains", 6),
        ("forest",    4),    ("mountains",11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("forest",    5),
        ("pasture",   2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("hills",    12),    ("forest",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("russia", tt, [
        _port( 2, -1, "wood", side=0),
        _port( 0, -2, "ore",  side=2),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  0, ratio=3, side=3),
        _port(-2,  2, ratio=3, side=4),
    ])


# ---------------------------------------------------------------------------
# Egypt — 小麦↑↑ 砖块↑  (尼罗河·金字塔)
# fields=6 hills=5 pasture=3 mountains=2 forest=2 desert=1
# ---------------------------------------------------------------------------

def egypt_map() -> MapData:
    tt = [
        ("desert",    None), ("fields",    9),  ("hills",     6),
        ("fields",    4),    ("pasture",  11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("fields",    5),
        ("hills",     2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("hills",    12),    ("fields",    3),  ("pasture",   8),
        ("forest",   10),
    ]
    return _from_std("egypt", tt, [
        _port( 2, -1, "wheat", side=0),
        _port( 0, -2, "brick", side=2),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  1, ratio=3, side=3),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Mexico — 砖块↑↑ 牧羊↑  (白银矿山·牧场)
# hills=5 pasture=5 fields=4 mountains=2 forest=2 desert=1
# ---------------------------------------------------------------------------

def mexico_map() -> MapData:
    tt = [
        ("desert",    None), ("hills",     9),  ("pasture",   6),
        ("hills",     4),    ("pasture",  11),  ("fields",    3),
        ("pasture",   8),    ("mountains",10),  ("hills",     5),
        ("pasture",   2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("fields",   12),    ("forest",    3),  ("fields",    8),
        ("hills",    10),
    ]
    return _from_std("mexico", tt, [
        _port( 2, -1, "brick", side=0),
        _port( 1, -2, "ore",   side=1),
        _port(-2,  1, "sheep", side=3),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Korea — 矿石↑↑ 砖块↑  (朝鲜半岛山脉)
# mountains=6 hills=4 forest=3 fields=3 pasture=2 desert=1
# ---------------------------------------------------------------------------

def korea_map() -> MapData:
    tt = [
        ("desert",    None), ("mountains", 9),  ("mountains", 6),
        ("hills",     4),    ("mountains",11),  ("hills",     3),
        ("mountains", 8),    ("mountains",10),  ("fields",    5),
        ("hills",     2),    ("mountains", 9),  ("forest",    6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("fields",   12),    ("forest",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("korea", tt, [
        _port( 2, -1, "ore",   side=0),
        _port(-1, -1, "brick", side=2),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  0, ratio=3, side=3),
        _port( 1,  1, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Indonesia — 木材↑↑ 砖块↑  (热带雨林·群岛)
# forest=7 hills=4 pasture=3 fields=2 mountains=2 desert=1
# ---------------------------------------------------------------------------

def indonesia_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("forest",    6),
        ("hills",     4),    ("forest",   11),  ("pasture",   3),
        ("forest",    8),    ("mountains",10),  ("forest",    5),
        ("hills",     2),    ("forest",    9),  ("hills",     6),
        ("pasture",   5),    ("mountains", 4),  ("hills",    11),
        ("forest",   12),    ("fields",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("indonesia", tt, [
        _port( 2, -1, "wood",  side=0),
        _port(-2,  1, "brick", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
        _port( 1,  1, ratio=3, side=0),
    ])


# ---------------------------------------------------------------------------
# New Zealand — 牧羊↑↑ 矿石↑  (白羊国·南阿尔卑斯)
# pasture=7 mountains=4 forest=3 hills=2 fields=2 desert=1
# ---------------------------------------------------------------------------

def new_zealand_map() -> MapData:
    tt = [
        ("desert",    None), ("pasture",   9),  ("pasture",   6),
        ("mountains", 4),    ("pasture",  11),  ("forest",    3),
        ("pasture",   8),    ("mountains",10),  ("pasture",   5),
        ("forest",    2),    ("pasture",   9),  ("mountains", 6),
        ("hills",     5),    ("mountains", 4),  ("forest",   11),
        ("hills",    12),    ("pasture",   3),  ("fields",    8),
        ("fields",   10),
    ]
    return _from_std("new_zealand", tt, [
        _port( 2, -1, "sheep", side=0),
        _port( 0, -2, "ore",   side=2),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  0, ratio=3, side=3),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# France — 小麦↑ 牧羊↑ 木材↑  (均衡农业帝国)
# fields=5 pasture=5 forest=4 mountains=2 hills=2 desert=1
# ---------------------------------------------------------------------------

def france_map() -> MapData:
    tt = [
        ("desert",    None), ("fields",    9),  ("pasture",   6),
        ("forest",    4),    ("pasture",  11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("pasture",   5),
        ("forest",    2),    ("fields",    9),  ("mountains", 6),
        ("pasture",   5),    ("forest",    4),  ("fields",   11),
        ("hills",    12),    ("forest",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("france", tt, [
        _port( 2, -1, "wheat", side=0),
        _port( 2, -2, "sheep", side=1),
        _port(-2,  1, "wood",  side=3),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Germany — 木材↑ 矿石↑  (黑森林·鲁尔工业)
# forest=5 mountains=4 fields=4 hills=3 pasture=2 desert=1
# ---------------------------------------------------------------------------

def germany_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("mountains", 6),
        ("fields",    4),    ("forest",   11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("forest",    5),
        ("pasture",   2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("fields",   11),
        ("mountains",12),    ("forest",    3),  ("pasture",   8),
        ("hills",    10),
    ]
    return _from_std("germany", tt, [
        _port( 2, -1, "ore",  side=0),
        _port(-2,  1, "wood", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  0, ratio=3, side=3),
        _port( 0,  2, ratio=3, side=5),
    ])


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
# Argentina — 木材↑↑ 牧羊↑  (巴塔哥尼亚·潘帕斯)
# forest=6 pasture=5 fields=3 mountains=2 hills=2 desert=1
# ---------------------------------------------------------------------------

def argentina_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("pasture",   6),
        ("forest",    4),    ("pasture",  11),  ("hills",     3),
        ("forest",    8),    ("mountains",10),  ("fields",    5),
        ("forest",    2),    ("pasture",   9),  ("forest",    6),
        ("hills",     5),    ("fields",    4),  ("pasture",  11),
        ("mountains",12),    ("fields",    3),  ("forest",    8),
        ("pasture",  10),
    ]
    return _from_std("argentina", tt, [
        _port( 2, -1, "wood",  side=0),
        _port(-2,  1, "sheep", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# South Africa — 矿石↑↑ 砖块↑  (黄金·钻石矿)
# mountains=5 hills=4 fields=4 pasture=3 forest=2 desert=1
# ---------------------------------------------------------------------------

def south_africa_map() -> MapData:
    tt = [
        ("desert",    None), ("mountains", 9),  ("mountains", 6),
        ("hills",     4),    ("mountains",11),  ("fields",    3),
        ("mountains", 8),    ("mountains",10),  ("hills",     5),
        ("fields",    2),    ("mountains", 9),  ("hills",     6),
        ("pasture",   5),    ("fields",    4),  ("hills",    11),
        ("fields",   12),    ("forest",    3),  ("pasture",   8),
        ("forest",   10),
    ]
    return _from_std("south_africa", tt, [
        _port( 2, -1, "ore",   side=0),
        _port(-2,  1, "brick", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port( 0,  2, ratio=3, side=5),
        _port(-2,  2, ratio=3, side=4),
    ])


# ---------------------------------------------------------------------------
# Italy — 砖块↑↑ 矿石↑  (亚平宁山脉·波河平原)
# hills=5 mountains=4 fields=4 pasture=3 forest=2 desert=1
# ---------------------------------------------------------------------------

def italy_map() -> MapData:
    tt = [
        ("desert",    None), ("hills",     9),  ("mountains", 6),
        ("fields",    4),    ("hills",    11),  ("mountains", 3),
        ("fields",    8),    ("mountains",10),  ("hills",     5),
        ("pasture",   2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("fields",   12),    ("forest",    3),  ("pasture",   8),
        ("hills",    10),
    ]
    return _from_std("italy", tt, [
        _port( 2, -1, "brick", side=0),
        _port( 1, -2, "ore",   side=1),
        _port(-2,  1, ratio=3, side=3),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
        _port( 1,  1, ratio=3, side=0),
    ])


# ---------------------------------------------------------------------------
# Scandinavia — 木材↑↑ 矿石↑  (北欧针叶林·斯堪的纳维亚山脉)
# forest=6 mountains=4 hills=4 pasture=2 fields=2 desert=1
# ---------------------------------------------------------------------------

def scandinavia_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("mountains", 6),
        ("forest",    4),    ("mountains",11),  ("hills",     3),
        ("forest",    8),    ("mountains",10),  ("forest",    5),
        ("hills",     2),    ("forest",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("hills",    11),
        ("hills",    12),    ("fields",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("scandinavia", tt, [
        _port( 2, -1, "wood",  side=0),
        _port( 0, -2, "ore",   side=2),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  0, ratio=3, side=3),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Spain — 小麦↑ 牧羊↑ 砖块↑  (伊比利亚半岛)
# fields=5 pasture=5 hills=4 mountains=2 forest=2 desert=1
# ---------------------------------------------------------------------------

def spain_map() -> MapData:
    tt = [
        ("desert",    None), ("fields",    9),  ("pasture",   6),
        ("hills",     4),    ("pasture",  11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("pasture",   5),
        ("hills",     2),    ("fields",    9),  ("mountains", 6),
        ("hills",     5),    ("forest",    4),  ("pasture",  11),
        ("fields",   12),    ("forest",    3),  ("fields",    8),
        ("pasture",  10),
    ]
    return _from_std("spain", tt, [
        _port( 2, -1, "wheat", side=0),
        _port(-2,  1, "sheep", side=3),
        _port( 1, -2, "brick", side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Turkey — 小麦↑ 牧羊↑ 矿石↑  (安纳托利亚高原)
# fields=5 mountains=4 pasture=4 hills=3 forest=2 desert=1
# ---------------------------------------------------------------------------

def turkey_map() -> MapData:
    tt = [
        ("desert",    None), ("fields",    9),  ("mountains", 6),
        ("pasture",   4),    ("fields",   11),  ("hills",     3),
        ("fields",    8),    ("mountains",10),  ("pasture",   5),
        ("hills",     2),    ("fields",    9),  ("mountains", 6),
        ("pasture",   5),    ("forest",    4),  ("hills",    11),
        ("mountains",12),    ("forest",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("turkey", tt, [
        _port( 2, -1, "wheat", side=0),
        _port( 0, -2, "ore",   side=2),
        _port(-2,  1, "sheep", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port(-2,  2, ratio=3, side=4),
        _port( 0,  2, ratio=3, side=5),
    ])


# ---------------------------------------------------------------------------
# Vietnam — 木材↑↑ 砖块↑  (热带雨林·石灰岩丘陵)
# forest=7 hills=4 fields=3 pasture=2 mountains=2 desert=1
# ---------------------------------------------------------------------------

def vietnam_map() -> MapData:
    tt = [
        ("desert",    None), ("forest",    9),  ("forest",    6),
        ("hills",     4),    ("forest",   11),  ("hills",     3),
        ("forest",    8),    ("mountains",10),  ("forest",    5),
        ("fields",    2),    ("forest",    9),  ("hills",     6),
        ("pasture",   5),    ("mountains", 4),  ("hills",    11),
        ("forest",   12),    ("fields",    3),  ("pasture",   8),
        ("fields",   10),
    ]
    return _from_std("vietnam", tt, [
        _port( 2, -1, "wood",  side=0),
        _port(-2,  1, "brick", side=3),
        _port( 2, -2, ratio=3, side=1),
        _port( 0, -2, ratio=3, side=2),
        _port(-2,  2, ratio=3, side=4),
        _port( 1,  1, ratio=3, side=0),
    ])


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
