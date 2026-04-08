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
# Registry
# ---------------------------------------------------------------------------

MAP_REGISTRY = {
    "china":       china_map,
    "japan":       japan_map,
    "usa":         usa_map,
    "europe":      europe_map,
    "uk":          uk_map,
    "australia":   australia_map,
    "brazil":      brazil_map,
    "antarctica":  antarctica_map,
    "india":       india_map,
    "canada":      canada_map,
    "russia":      russia_map,
    "egypt":       egypt_map,
    "mexico":      mexico_map,
    "korea":       korea_map,
    "indonesia":   indonesia_map,
    "new_zealand": new_zealand_map,
    "france":      france_map,
    "germany":     germany_map,
}


def get_static_map(map_id: str) -> MapData:
    fn = MAP_REGISTRY.get(map_id)
    if not fn:
        raise ValueError(f"Unknown static map: {map_id}")
    return normalize_ports(fn())
