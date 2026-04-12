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
    # Wide continental China: Tibet/Himalayas W, Gobi N, Yangtze center,
    # Guangdong tropical S, Manchuria NE, Taiwan separate SE.
    tiles = [
        # --- N steppe / Manchuria (r=-2) ---
        _tile( 1, -2, "pasture",   9),   # Inner Mongolia grasslands
        _tile( 2, -2, "forest",    6),   # NE Manchuria (Harbin)

        # --- N China (r=-1): Xinjiang → Beijing → Liaodong ---
        _tile(-1, -1, "mountains", 4),   # Tianshan (Xinjiang)
        _tile( 0, -1, "desert"),          # Gobi Desert
        _tile( 1, -1, "fields",   11),   # N China plain (Beijing)
        _tile( 2, -1, "hills",     8),   # Shandong / Liaodong

        # --- Central China (r=0): Tibet → Sichuan → Yangtze → Shanghai ---
        _tile(-2,  0, "mountains", 3),   # W Tibet plateau
        _tile(-1,  0, "mountains",10),   # Himalayas
        _tile( 0,  0, "fields",    5),   # Sichuan basin
        _tile( 1,  0, "fields",    2),   # Middle Yangtze (Wuhan)
        _tile( 2,  0, "hills",     9),   # Yangtze delta / Shanghai

        # --- S China (r=1): Yunnan → Guangdong → Fujian ---
        _tile(-1,  1, "forest",    6),   # Yunnan jungles
        _tile( 0,  1, "hills",     4),   # Guangxi
        _tile( 1,  1, "fields",   11),   # Guangdong (Pearl River Delta)
        _tile( 2,  1, "hills",     5),   # Fujian

        # --- Tropical S coast (r=2) ---
        _tile( 0,  2, "forest",   12),   # Hainan Island (tropical)
        _tile( 1,  2, "pasture",   3),   # S Guangxi

        # --- Taiwan (SEPARATE island E of Fujian) ---
        _tile( 4,  1, "mountains", 8),   # Taiwan (Central Mountain Range)
    ]
    ports = [
        _port( 2, -2, ratio=3),          # NE — Dalian / Bohai
        _port( 2, -1, "ore"),            # E — Qingdao coast
        _port( 2,  0, ratio=3),          # E — Shanghai
        _port( 2,  1, ratio=3),          # SE — Xiamen / Fujian
        _port( 1,  2, "wheat"),          # S — Guangxi S coast
        _port( 0,  2, ratio=3),          # S — Hainan strait
        _port(-2,  0, ratio=3),          # W — Tibet highland border
        _port( 4,  1, ratio=3),          # Taiwan — Kaohsiung
    ]
    return MapData(map_id="china", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Japan — 港口↑↑ 小麦↓ 矿石↓，四岛群岛（海洋分割）
# Shape: diagonal island chain NW→SE (Hokkaido, Honshu, Shikoku+Kyushu, Okinawa)
# ---------------------------------------------------------------------------

def japan_map() -> MapData:
    # Japan's 4 main islands form a curving NE→SW archipelago.
    # Each island is a separate cluster with sea gaps between them.
    tiles = [
        # --- Hokkaido (N island, 4 tiles) ---
        _tile(-1, -4, "mountains", 9),   # Daisetsuzan
        _tile( 0, -4, "hills",     6),   # E Hokkaido (Kushiro)
        _tile(-1, -3, "forest",    4),   # S Hokkaido
        _tile(-1, -2, "pasture",   3),   # SW Hokkaido (dairy)

        # --- sea gap: Tsugaru Strait ---

        # --- Honshu N / Tohoku ---
        _tile( 1, -3, "forest",   11),   # N Tohoku (Aomori)
        _tile( 2, -3, "mountains", 8),   # Ou Mountains
        _tile( 1, -2, "fields",    5),   # Sendai plain

        # --- Honshu Central / Kanto + Chubu ---
        _tile( 2, -2, "fields",   10),   # Kanto plain (Tokyo)
        _tile( 3, -3, "desert"),          # Japanese Alps (rugged, barren)
        _tile( 3, -2, "forest",    2),   # Kiso / Chubu mountains

        # --- Honshu S / Kansai + Chugoku ---
        _tile( 3, -1, "fields",    9),   # Kansai (Osaka/Kyoto)
        _tile( 4, -2, "mountains",12),   # Chugoku Mountains

        # --- sea gap: Inland Sea ---

        # --- Shikoku (small island, 1 tile) ---
        _tile( 3,  1, "hills",     6),   # Shikoku (rugged)

        # --- sea gap: Bungo Channel ---

        # --- Kyushu (SW island, 3 tiles) ---
        _tile( 5, -1, "pasture",   5),   # N Kyushu (Fukuoka)
        _tile( 5,  0, "mountains", 4),   # Mt Aso volcano
        _tile( 5,  1, "forest",   10),   # S Kyushu (Kagoshima)

        # --- sea gap: East China Sea ---

        # --- Okinawa / Ryukyu (far S small island, 1 tile) ---
        _tile( 6,  3, "hills",     8),   # Okinawa
    ]
    ports = [
        _port( 0, -4, ratio=3),          # Hokkaido E — Pacific
        _port(-1, -2, "wood",  ratio=2), # Hokkaido SW — timber
        _port( 1, -3, ratio=3),          # Honshu N — Pacific
        _port( 2, -2, ratio=3),          # Tokyo Bay
        _port( 4, -2, ratio=3),          # Honshu W — Sea of Japan
        _port( 3,  1, ratio=3),          # Shikoku — Inland Sea
        _port( 5,  1, "sheep"),          # Kyushu S — Kagoshima
        _port( 6,  3, "brick"),          # Okinawa — Ryukyu trade
    ]
    return MapData(map_id="japan", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# USA — 小麦↑↑ 木材↑ 资源均衡
# Shape: wide E-W (2.5:1) with slight SE protrusion (Florida/Gulf coast)
# q=-3..3, r=-1..2
# ---------------------------------------------------------------------------

def usa_map() -> MapData:
    # Wide contiguous 48: Pacific → Rockies → Plains → Appalachians → Atlantic.
    # Florida peninsula SE. Great Lakes NE. Alaska NOT represented.
    tiles = [
        # --- N border row (Canada border, r=-1): Pacific NW → Great Lakes ---
        _tile(-3, -1, "forest",    9),   # Pacific NW (Washington/Oregon)
        _tile(-2, -1, "mountains", 6),   # N Rockies (Idaho/Montana)
        _tile(-1, -1, "fields",    4),   # N Plains (Dakotas)
        _tile( 0, -1, "fields",   11),   # Midwest N (Minnesota/Wisconsin)
        _tile( 1, -1, "forest",    3),   # Great Lakes (Michigan)
        _tile( 2, -1, "hills",     8),   # NE (NY/New England)

        # --- Middle row (r=0): widest — Rockies → Plains → Appalachians ---
        _tile(-3,  0, "mountains", 5),   # California (Sierra Nevada)
        _tile(-2,  0, "desert"),          # Great Basin (Nevada)
        _tile(-1,  0, "pasture",  10),   # High Plains (Wyoming/Colorado)
        _tile( 0,  0, "fields",    2),   # Central Plains (Kansas)
        _tile( 1,  0, "fields",    9),   # Ohio Valley (Illinois/Indiana)
        _tile( 2,  0, "hills",     6),   # Appalachians (West Virginia)
        _tile( 3,  0, "pasture",   5),   # E Coast (Virginia/DC)

        # --- S row (r=1): CA coast → SW desert → Gulf → Carolinas ---
        _tile(-3,  1, "fields",   12),   # S California (Central Valley)
        _tile(-2,  1, "desert"),          # Arizona / New Mexico
        _tile(-1,  1, "pasture",   4),   # Texas panhandle
        _tile( 0,  1, "forest",    3),   # E Texas / Louisiana (swamp)
        _tile( 1,  1, "hills",     8),   # Alabama / Georgia
        _tile( 2,  1, "forest",   10),   # Carolinas

        # --- SE protrusion (r=2): Florida peninsula ---
        _tile( 1,  2, "fields",   11),   # N Florida
    ]
    ports = [
        _port(-3, -1, "wood"),           # NW — Seattle / Pacific NW
        _port( 2, -1, ratio=3),          # NE — Boston / New England
        _port( 3,  0, ratio=3),          # E — Chesapeake / Atlantic
        _port( 1,  2, "sheep"),          # SE — Florida
        _port( 1,  1, ratio=3),          # S — Gulf of Mexico
        _port( 0,  1, ratio=3),          # S — New Orleans / Mississippi delta
        _port(-3,  1, "wheat"),          # SW — Los Angeles / Long Beach
        _port(-3,  0, ratio=3),          # W — San Francisco Bay
    ]
    return MapData(map_id="usa", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Europe — 小麦↑ 牧羊↑ 港口多
# Shape: irregular wide blob (1.5:1), from Iberia to Turkey, Scandinavia to Med
# q=-2..3, r=-2..1
# ---------------------------------------------------------------------------

def europe_map() -> MapData:
    # Europe continent + British Isles (separate islands via sea gaps at q=-3, -1).
    # Shape: Iberia SW, Italy boot S (q=1 column extending to r=2),
    # Scandinavia N, British Isles NW (separate), Eastern Europe E, Balkans/Greece SE.
    tiles = [
        # --- British Isles (SEPARATE islands; sea gap at q=-3 and q=-1) ---
        _tile(-4,  1, "forest",    9),   # Ireland N (Ulster)
        _tile(-4,  2, "pasture",  11),   # Ireland S (Munster, sheep)
        _tile(-2, -1, "mountains", 2),   # Scotland Highlands
        _tile(-2,  0, "hills",    10),   # N England (coal, Pennines)
        _tile(-2,  1, "fields",    4),   # S England (London basin)

        # --- Scandinavia (N, q=1..2 top rows) ---
        _tile( 1, -3, "mountains", 9),   # Norway fjords
        _tile( 1, -2, "forest",    4),   # S Sweden / Denmark strait
        _tile( 2, -3, "forest",    8),   # Sweden taiga

        # --- Continental Europe q=0 column: Denmark → France → Iberia SW ---
        _tile( 0, -2, "pasture",   3),   # Denmark / Low Countries
        _tile( 0, -1, "fields",    6),   # N France / Belgium
        _tile( 0,  0, "fields",    5),   # Central France
        _tile( 0,  1, "pasture",  12),   # S France (Provence)
        _tile( 0,  2, "hills",    11),   # Iberia SW (Portugal/Andalusia)

        # --- q=1 column: Germany → Alps → Italy boot (extending far S) ---
        _tile( 1, -1, "forest",   10),   # Germany (Black Forest)
        _tile( 1,  0, "desert"),          # Alps (barren high rock)
        _tile( 1,  1, "fields",    5),   # N Italy (Po valley)
        _tile( 1,  2, "hills",     3),   # Italy boot (S Italy)

        # --- q=2 column: Baltic / Poland / Balkans ---
        _tile( 2, -2, "pasture",  11),   # Baltic / Poland N
        _tile( 2, -1, "fields",    6),   # Poland
        _tile( 2,  1, "hills",     8),   # Balkans / Greece

        # --- q=3..4: Eastern Europe / Ukraine / Caucasus ---
        _tile( 3, -1, "fields",    9),   # Ukraine (breadbasket)
        _tile( 3,  0, "hills",    12),   # Romania / Black Sea
        _tile( 4, -1, "mountains", 2),   # Caucasus / S Russia
    ]
    ports = [
        _port(-4,  1, ratio=3),          # NW — Atlantic (Ireland W)
        _port(-4,  2, "sheep"),          # Ireland — wool export
        _port(-2, -1, ratio=3),          # N Sea (Scotland)
        _port( 1, -3, ratio=3),          # N — Arctic Norway
        _port( 0,  2, "wheat"),          # SW — Iberia (grain)
        _port( 1,  2, ratio=3),          # S — Italy Med
        _port( 2,  1, ratio=3),          # SE — Aegean / Greece
        _port( 3,  0, "ore"),            # E — Black Sea
    ]
    return MapData(map_id="europe", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# UK — 牧羊↑↑ 矿石↑，岛链形状
# Shape: narrow N-S main island (GB) + separate Ireland to the W
# GB: q=0..1, r=-3..1   Ireland: q=-2..-3, r=-1..1  (gap at q=-1)
# ---------------------------------------------------------------------------

def uk_map() -> MapData:
    # Great Britain is a long N-S island, with Ireland as a
    # SEPARATE island to the west (sea gap at q=-1 column).
    tiles = [
        # --- Great Britain (main island, q=0..2) ---
        # Scotland (narrow top)
        _tile( 1, -5, "mountains", 9),   # Highlands (Ben Nevis)
        _tile( 2, -6, "hills",     6),   # NE Scotland coast
        _tile( 1, -4, "pasture",   4),   # Glasgow / Edinburgh belt
        _tile( 2, -5, "mountains",11),   # E Highlands

        # N England
        _tile( 0, -3, "forest",    3),   # Cumbria / Lake District
        _tile( 1, -3, "pasture",   8),   # Yorkshire dales
        _tile( 2, -4, "hills",    10),   # Newcastle / E coast

        # Midlands (widest part of GB)
        _tile( 0, -2, "fields",    5),   # W Midlands / Wales border
        _tile( 1, -2, "fields",    2),   # Central England
        _tile( 2, -3, "pasture",   9),   # Lincolnshire / Fens

        # Wales (W protrusion)
        _tile( 0, -1, "hills",     6),   # Wales (slate, sheep)

        # S England
        _tile( 1, -1, "fields",    4),   # London basin
        _tile( 2, -2, "pasture",  11),   # Kent / SE coast

        # SW England (Cornwall / Devon)
        _tile( 1,  0, "mountains", 3),   # Cornwall tin mines

        # --- Ireland (SEPARATE island, q=-3..-2, sea gap at q=-1) ---
        _tile(-3, -1, "pasture",   8),   # Ulster
        _tile(-2, -1, "forest",   12),   # N Ireland
        _tile(-3,  0, "fields",    5),   # Connacht
        _tile(-2,  0, "hills",    10),   # Munster / Wicklow

        # --- Hebrides / island group (separate small cluster NW) ---
        _tile(-1, -4, "desert"),          # Outer Hebrides (barren)
    ]
    ports = [
        _port( 2, -6, ratio=3),          # N — North Sea (Aberdeen)
        _port( 2, -4, "ore"),            # NE — Newcastle coal
        _port( 2, -2, ratio=3),          # SE — Dover / Channel
        _port( 1,  0, ratio=3),          # S — Plymouth / SW coast
        _port( 0, -1, "sheep"),          # W — Wales (wool export)
        _port(-2,  0, ratio=3),          # Ireland S — Cork
        _port(-3,  0, ratio=3),          # Ireland W — Atlantic
        _port(-3, -1, ratio=3),          # Ireland N — Belfast
    ]
    return MapData(map_id="uk", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Australia — 沙漠↑↑ 矿石↑↑ 牧羊↑
# Shape: wide flat continent (2.5:1), desert interior, coastal resources
# q=-2..4, r=-1..2
# ---------------------------------------------------------------------------

def australia_map() -> MapData:
    # Wide continent with Cape York peninsula (N), desert interior,
    # and Tasmania as a separate island to the south.
    tiles = [
        # --- Cape York peninsula (N protrusion) ---
        _tile( 1, -2, "forest",    9),   # Cape York tip (tropical)
        _tile( 2, -2, "pasture",   6),   # Gulf of Carpentaria

        # --- N coast row (Darwin → Queensland) ---
        _tile(-1, -1, "mountains",10),   # NW Kimberley
        _tile( 0, -1, "pasture",   4),   # Darwin / Kakadu
        _tile( 1, -1, "desert"),          # N Territory interior
        _tile( 2, -1, "pasture",  11),   # Queensland savanna
        _tile( 3, -1, "fields",    3),   # N Queensland (sugar cane)
        _tile( 4, -1, "forest",    8),   # Great Barrier Reef coast

        # --- Desert interior (the Outback) ---
        _tile(-2,  0, "hills",     5),   # W Pilbara ore country
        _tile(-1,  0, "desert"),          # Great Sandy Desert
        _tile( 0,  0, "desert"),          # Gibson Desert
        _tile( 1,  0, "mountains", 2),   # MacDonnell Ranges (Uluru area)
        _tile( 2,  0, "desert"),          # Simpson Desert
        _tile( 3,  0, "pasture",   9),   # Central Queensland
        _tile( 4,  0, "fields",    6),   # Brisbane hinterland

        # --- S coast row (Perth → Adelaide → Sydney → Melbourne) ---
        _tile(-1,  1, "hills",    12),   # SW WA (Perth hills)
        _tile( 0,  1, "fields",    5),   # Nullarbor edge
        _tile( 1,  1, "pasture",   3),   # Adelaide area
        _tile( 2,  1, "fields",    4),   # Victoria wheat belt
        _tile( 3,  1, "hills",    10),   # Blue Mountains / NSW

        # --- Tasmania (SEPARATE island, gap at r=2) ---
        _tile( 1,  3, "forest",   11),   # Tasmania (dense rainforest)
    ]
    ports = [
        _port(-1, -1, ratio=3),          # NW — Broome / Kimberley
        _port( 1, -2, ratio=3),          # N — Cape York / Torres Strait
        _port( 4, -1, "wheat"),          # NE — Great Barrier Reef coast
        _port( 4,  0, ratio=3),          # E — Brisbane
        _port( 3,  1, ratio=3),          # SE — Sydney
        _port( 1,  1, "sheep"),          # S — Adelaide (wool export)
        _port(-1,  1, ratio=3),          # SW — Perth
        _port(-2,  0, "ore"),            # W — Pilbara iron ore
        _port( 1,  3, ratio=3),          # Tasmania — Hobart
    ]
    return MapData(map_id="australia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Brazil — 木材↑↑ 小麦↑
# Shape: large roughly triangular, wide N, narrowing S, Atlantic coast E
# ~19 tiles, q=-2..2, r=-2..2
# ---------------------------------------------------------------------------

def brazil_map() -> MapData:
    # Brazil: huge wedge shape, wider in N (Amazon basin), narrowing
    # SW toward Uruguay border. Bulge on E (Nordeste) along Atlantic.
    tiles = [
        # --- N Amazon (wide top row) ---
        _tile(-2, -2, "forest",    9),   # W Amazon (Acre)
        _tile(-1, -2, "forest",    6),   # Amazonas state
        _tile( 0, -2, "forest",    4),   # N Pará
        _tile( 1, -2, "forest",   11),   # Amapá / Guiana Shield
        _tile( 2, -2, "forest",    3),   # Marajó

        # --- Mid-N (Amazon interior + Nordeste begins) ---
        _tile(-2, -1, "forest",    8),   # Rondônia
        _tile(-1, -1, "forest",   10),   # Tocantins forests
        _tile( 0, -1, "fields",    5),   # Maranhão
        _tile( 1, -1, "hills",     2),   # Piauí
        _tile( 2, -1, "fields",    9),   # Ceará (NE bulge E)

        # --- Middle (Cerrado heartland) ---
        _tile(-1,  0, "fields",    6),   # Mato Grosso (soy belt)
        _tile( 0,  0, "desert"),          # Sertão (dry Nordeste interior)
        _tile( 1,  0, "pasture",   4),   # Bahia interior
        _tile( 2,  0, "hills",    11),   # Salvador coast

        # --- Lower middle (narrowing south) ---
        _tile( 0,  1, "forest",   12),   # Minas Gerais (gold/iron mines)
        _tile( 1,  1, "fields",    3),   # Espírito Santo / Rio

        # --- Southern lobe ---
        _tile( 0,  2, "pasture",   8),   # São Paulo / Paraná
        _tile( 1,  2, "fields",   10),   # Santa Catarina

        # --- Southern tip (Rio Grande do Sul) ---
        _tile( 0,  3, "pasture",   5),   # RS pampas (gaucho country)
    ]
    ports = [
        _port(-2, -2, "wood"),           # NW — Amazon upstream (timber)
        _port( 1, -2, ratio=3),          # N — North coast (Amapá)
        _port( 2, -2, ratio=3),          # NE — Belém / Amazon mouth
        _port( 2, -1, ratio=3),          # E — Fortaleza (NE bulge)
        _port( 2,  0, "wheat"),          # E — Salvador (sugar/grain)
        _port( 1,  1, ratio=3),          # SE — Rio de Janeiro
        _port( 1,  2, ratio=3),          # S — Santos / São Paulo
        _port( 0,  3, ratio=3),          # S — Porto Alegre
    ]
    return MapData(map_id="brazil", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Antarctica — 沙漠↑↑↑ 资源极稀（趣味图）
# Shape: sparse coastal ring, mostly desert interior
# A rough ring of hexes around an icy center
# ---------------------------------------------------------------------------

def antarctica_map() -> MapData:
    # Round/circular continent — a perfect radius-2 hex (19 tiles).
    # Mostly ice (desert) with a few sparse pockets of resources: a coastal
    # penguin colony, lichen on a nunatak, an oasis dry valley, etc.
    # Deliberately hard to play — it's a theme map.
    tiles = [
        # --- Ring 2 (outer coast, 12 tiles, mostly ice shelf) ---
        _tile( 2, -2, "desert"),                          # Weddell Sea ice
        _tile( 2, -1, "desert"),                          # Ronne Ice Shelf
        _tile( 2,  0, "desert"),                          # E coast ice
        _tile( 1,  1, "desert"),                          # SE ice shelf
        _tile( 0,  2, "pasture",   9),                    # Adelie coast (penguin colony)
        _tile(-1,  2, "desert"),                          # Ross Ice Shelf edge
        _tile(-2,  2, "desert"),                          # Ross Sea ice
        _tile(-2,  1, "forest",    4),                    # Coastal lichen / mosses
        _tile(-2,  0, "desert"),                          # Bellingshausen ice
        _tile(-1, -1, "desert"),                          # Antarctic Peninsula base
        _tile( 0, -2, "desert"),                          # NE Wilkes Land
        _tile( 1, -2, "fields",   11),                    # McMurdo Dry Valleys (rare oasis!)
        # --- Ring 1 (inner ring, 6 tiles) ---
        _tile( 1, -1, "mountains", 8),                    # Transantarctic Mtns
        _tile( 1,  0, "desert"),                          # Polar plateau E
        _tile( 0,  1, "desert"),                          # S polar ice
        _tile(-1,  1, "hills",     6),                    # Vinson Massif foothills
        _tile(-1,  0, "desert"),                          # Polar plateau W
        _tile( 0, -1, "desert"),                          # Polar plateau N
        # --- Center: South Pole ---
        _tile( 0,  0, "desert"),                          # South Pole (Amundsen-Scott)
    ]
    ports = [
        # Only 3 ports — trading is brutally hard
        _port( 1, -2, ratio=3),                           # McMurdo Sound
        _port(-2,  1, ratio=3),                           # Antarctic Peninsula tip
        _port( 0,  2, ratio=3),                           # Adelie coast (penguin port)
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
    # Triangular subcontinent: wide at N (Himalayas/Punjab/Bengal),
    # narrowing through Deccan plateau to Cape Comorin at S tip.
    # Sri Lanka as a separate island off the SE.
    tiles = [
        # --- N wide base: Himalayas + Indus/Gangetic plain (r=-2) ---
        _tile(-1, -2, "mountains", 9),   # Punjab Himalayas
        _tile( 0, -2, "mountains", 6),   # Central Himalayas (Everest)
        _tile( 1, -2, "mountains", 4),   # E Himalayas / Nepal border
        _tile( 2, -2, "forest",   11),   # Assam / NE India

        # --- Gangetic plain (r=-1) ---
        _tile(-1, -1, "fields",    3),   # Punjab (wheat breadbasket)
        _tile( 0, -1, "fields",    8),   # Delhi / Gangetic plain
        _tile( 1, -1, "fields",   10),   # UP / Bihar (rice)
        _tile( 2, -1, "pasture",   5),   # Bengal delta (jute)

        # --- Central India / Deccan start (r=0) narrowing ---
        _tile( 0,  0, "desert"),          # Thar Desert (Rajasthan)
        _tile( 1,  0, "hills",     9),   # Central Deccan
        _tile( 2,  0, "fields",    2),   # Odisha coast

        # --- Deccan plateau (r=1) ---
        _tile( 0,  1, "pasture",   6),   # Karnataka / Maharashtra
        _tile( 1,  1, "hills",    11),   # Deccan S
        _tile( 2,  1, "pasture",  12),   # Andhra Pradesh

        # --- S narrowing (r=2) ---
        _tile( 0,  2, "forest",    4),   # Kerala (Malabar coast, spices)
        _tile( 1,  2, "fields",    5),   # Tamil Nadu

        # --- S tip (r=3) ---
        _tile( 0,  3, "hills",     3),   # Cape Comorin

        # --- Sri Lanka (SEPARATE island SE of tip) ---
        _tile( 2,  3, "forest",    8),   # Sri Lanka
    ]
    ports = [
        _port(-1, -2, ratio=3),          # NW — Karachi / Indus mouth
        _port( 2, -2, ratio=3),          # NE — Brahmaputra (Assam)
        _port( 2, -1, "wheat"),          # E — Kolkata (Bengal grain)
        _port( 2,  1, ratio=3),          # E — Andhra coast (Chennai)
        _port( 1,  2, ratio=3),          # SE — Tamil Nadu
        _port( 0,  3, "sheep"),          # S — Cape Comorin
        _port( 0,  2, ratio=3),          # SW — Kerala (Malabar spice)
        _port( 2,  3, ratio=3),          # Sri Lanka — Colombo
    ]
    return MapData(map_id="india", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Canada — 木材↑↑ 小麦↑  (北方森林·大草原)
# Shape: very wide E-W (3:1+), vast but thin N-S
# q=-4..3, r=-1..1
# ---------------------------------------------------------------------------

def canada_map() -> MapData:
    # Canada: very wide E-W continental strip (3:1+).
    # Pacific NW → Rockies → Prairies → Hudson Bay → Great Lakes → Maritimes.
    # Newfoundland as a separate island E.
    tiles = [
        # --- Arctic tundra row (r=-2) ---
        _tile( 0, -2, "desert"),          # Nunavut tundra
        _tile( 1, -2, "mountains", 9),   # Baffin Island mountains

        # --- N boreal row (r=-1) ---
        _tile(-4, -1, "forest",    6),   # Yukon boreal forest
        _tile(-3, -1, "mountains", 4),   # NW Canada Rockies
        _tile(-2, -1, "forest",   11),   # NWT boreal
        _tile(-1, -1, "forest",    3),   # N Alberta forest
        _tile( 2, -1, "forest",    8),   # N Ontario boreal
        _tile( 3, -1, "forest",   10),   # N Quebec

        # --- Main populated belt (r=0): Vancouver → Prairies → Great Lakes → Maritimes ---
        _tile(-4,  0, "pasture",   5),   # BC coast (Vancouver)
        _tile(-3,  0, "mountains", 2),   # BC Rockies
        _tile(-2,  0, "fields",    9),   # Alberta (oil + wheat)
        _tile(-1,  0, "fields",   12),   # Saskatchewan prairies
        _tile( 0,  0, "fields",    6),   # Manitoba wheat
        _tile( 1,  0, "forest",    4),   # NW Ontario (Canadian Shield)
        _tile( 2,  0, "hills",    11),   # S Ontario (Toronto/Great Lakes)
        _tile( 3,  0, "forest",    5),   # Quebec
        _tile( 4,  0, "hills",     3),   # New Brunswick / Nova Scotia

        # --- Newfoundland (SEPARATE island far E) ---
        _tile( 6,  0, "pasture",   8),   # Newfoundland
    ]
    ports = [
        _port(-4, -1, ratio=3),          # NW — Yukon / Alaska border
        _port(-4,  0, "wood"),           # W — Vancouver (Pacific timber)
        _port( 0, -2, ratio=3),          # N — Arctic coast
        _port(-1,  0, "wheat"),          # S — Prairies grain export
        _port( 2,  0, ratio=3),          # SE — Toronto / Great Lakes
        _port( 4,  0, ratio=3),          # E — Halifax / Maritimes
        _port( 6,  0, ratio=3),          # Newfoundland — St John's
    ]
    return MapData(map_id="canada", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Russia — 木材↑ 矿石↑↑  (泰加林·乌拉尔山)
# Shape: extremely wide E-W (4:1), thin N-S strip
# q=-4..4, r=-1..1
# ---------------------------------------------------------------------------

def russia_map() -> MapData:
    # Russia: widest country on earth — extreme E-W continental strip (4:1+).
    # European west → Urals → W Siberia → E Siberia → Kamchatka.
    # Black Sea/Caspian dip at SW. Taiga forests dominate.
    tiles = [
        # --- Arctic row (r=-2): northernmost strip ---
        _tile(-3, -2, "desert"),          # Kola / Arctic tundra
        _tile( 0, -2, "forest",    9),   # Yamal / N Siberia
        _tile( 3, -2, "mountains", 6),   # NE Arctic (Chukotka)

        # --- N boreal (r=-1): taiga ---
        _tile(-4, -1, "forest",    4),   # Karelia
        _tile(-3, -1, "forest",   11),   # Arkhangelsk
        _tile(-2, -1, "mountains", 3),   # N Urals
        _tile(-1, -1, "forest",    8),   # W Siberia
        _tile( 0, -1, "forest",   10),   # C Siberia (Krasnoyarsk)
        _tile( 1, -1, "forest",    5),   # Yakutia forests
        _tile( 2, -1, "mountains", 2),   # Verkhoyansk Range
        _tile( 3, -1, "mountains",12),   # Kamchatka volcanoes
        _tile( 4, -1, "forest",    9),   # Sakhalin / Far East

        # --- Main populated strip (r=0) ---
        _tile(-4,  0, "fields",    6),   # Moscow / European Russia
        _tile(-3,  0, "fields",    4),   # Volga valley
        _tile(-2,  0, "mountains", 9),   # S Urals ore
        _tile(-1,  0, "pasture",  11),   # W Siberia steppe
        _tile( 0,  0, "fields",    5),   # Novosibirsk
        _tile( 1,  0, "hills",     3),   # Irkutsk / Lake Baikal
        _tile( 2,  0, "forest",    8),   # Amur / Trans-Sib E
        _tile( 3,  0, "pasture",  10),   # Primorye (Vladivostok area)

        # --- SW dip (Black Sea / Caspian, r=1) ---
        _tile(-4,  1, "pasture",   5),   # Kuban / N Caucasus
    ]
    ports = [
        _port(-4, -1, ratio=3),          # NW — Murmansk (Arctic)
        _port(-4,  0, ratio=3),          # W — St. Petersburg (Baltic)
        _port(-4,  1, "wheat"),          # SW — Black Sea (grain export)
        _port( 0, -2, ratio=3),          # N — Arctic Ocean
        _port( 3, -2, ratio=3),          # NE — Chukotka Arctic
        _port( 4, -1, "ore"),            # E — Vladivostok / Sakhalin
        _port( 3,  0, ratio=3),          # SE — Japan Sea coast
    ]
    return MapData(map_id="russia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Egypt — 小麦↑↑ 砖块↑  (尼罗河·金字塔)
# Shape: roughly square with Nile delta at N, Sinai peninsula NE
# q=0..3, r=-2..2
# ---------------------------------------------------------------------------

def egypt_map() -> MapData:
    # Egypt: Mediterranean coast N (Nile Delta wide), Sinai peninsula NE,
    # long Nile Valley running N-S through arid desert interior.
    # Red Sea forms E coast; Libyan desert to W.
    tiles = [
        # --- Mediterranean coast (r=-3): Nile Delta wide top ---
        _tile(-1, -3, "fields",    9),   # Alexandria coast (Delta W)
        _tile( 0, -3, "fields",    6),   # Nile Delta center
        _tile( 1, -3, "pasture",  11),   # Delta E (cattle)

        # --- Sinai Peninsula + N Eastern Desert (r=-2) ---
        _tile(-1, -2, "desert"),          # W Delta / Libyan Desert
        _tile( 0, -2, "fields",    4),   # Cairo / Memphis
        _tile( 1, -2, "hills",     8),   # Eastern Desert N
        _tile( 2, -2, "mountains", 3),   # Sinai mountains (Mt Sinai)

        # --- Middle Egypt (r=-1): Nile valley + flanking deserts ---
        _tile(-1, -1, "desert"),          # Western Desert (Bahariya)
        _tile( 0, -1, "fields",    5),   # Middle Egypt (Faiyum)
        _tile( 1, -1, "hills",    10),   # Red Sea mountains

        # --- S Middle Egypt (r=0) ---
        _tile(-1,  0, "desert"),          # Great Sand Sea
        _tile( 0,  0, "fields",    2),   # Luxor / Valley of Kings
        _tile( 1,  0, "hills",    12),   # Red Sea coast

        # --- Upper Egypt / S Nile (r=1) ---
        _tile( 0,  1, "fields",    9),   # Aswan / Lake Nasser
        _tile( 1,  1, "desert"),          # Nubian Desert

        # --- S tip / Sudan border (r=2) ---
        _tile( 0,  2, "pasture",   6),   # N Sudan border
    ]
    ports = [
        _port(-1, -3, ratio=3),          # NW — Alexandria (Med coast)
        _port( 1, -3, ratio=3),          # NE — Port Said / Suez Canal
        _port( 2, -2, "ore"),            # E — Sinai mines
        _port( 1,  0, "wheat"),          # E — Red Sea / Hurghada
        _port( 0,  2, ratio=3),          # S — Abu Simbel
        _port( 0, -2, "brick"),          # Center — Cairo (Nile trade)
    ]
    return MapData(map_id="egypt", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Mexico — 砖块↑↑ 牧羊↑  (白银矿山·牧场)
# Shape: diagonal elongated NW-SE, wider N (Baja + mainland), narrow S (Yucatan)
# q=-2..2, r=-1..3
# ---------------------------------------------------------------------------

def mexico_map() -> MapData:
    # Mexico: wide N (Sonora/Chihuahua deserts), narrowing through central
    # plateau (Mexico City), down to Tehuantepec waist, then Yucatan
    # peninsula juts NE. Baja California is a long thin peninsula W.
    tiles = [
        # --- N border (r=-2): Sonora → Chihuahua → NE ---
        _tile(-1, -2, "desert"),          # Sonora Desert
        _tile( 0, -2, "desert"),          # Chihuahua Desert
        _tile( 1, -2, "pasture",   9),   # Coahuila / Nuevo León

        # --- Baja California (long peninsula, separate column W) ---
        _tile(-3, -1, "desert"),          # Baja N (Mexicali)
        _tile(-3,  0, "hills",     6),   # Baja S (Cabo)

        # --- Mid-N (r=-1): Sierra Madre Occidental → Gulf ---
        _tile(-1, -1, "mountains", 4),   # Sierra Madre Occidental
        _tile( 0, -1, "pasture",  11),   # Durango plateau
        _tile( 1, -1, "mountains", 3),   # Sierra Madre Oriental
        _tile( 2, -1, "fields",    8),   # Tamaulipas (Gulf coast)

        # --- Central plateau (r=0): Mexico City area ---
        _tile( 0,  0, "hills",    10),   # Jalisco / Michoacán
        _tile( 1,  0, "fields",    5),   # Valley of Mexico
        _tile( 2,  0, "mountains", 2),   # Popocatepetl volcanoes

        # --- S narrowing (r=1): Oaxaca → Tehuantepec waist ---
        _tile( 1,  1, "forest",    9),   # Oaxaca
        _tile( 2,  1, "hills",    12),   # Tehuantepec waist

        # --- Yucatan Peninsula (NE bulge, r=0..1 extending q=3..4) ---
        _tile( 3,  0, "forest",    6),   # Campeche / base of Yucatan
        _tile( 4,  0, "forest",   11),   # Cancún / Yucatan N
        _tile( 3,  1, "hills",     4),   # Quintana Roo / Chiapas highlands
    ]
    ports = [
        _port(-3, -1, ratio=3),          # NW — Tijuana / Baja N
        _port(-3,  0, "sheep"),          # W — Baja S (Cabo)
        _port( 1, -2, ratio=3),          # NE — Monterrey
        _port( 2, -1, ratio=3),          # E — Tampico (Gulf)
        _port( 4,  0, "brick"),          # E — Yucatan (Merida/Cancún)
        _port( 3,  1, ratio=3),          # SE — Chiapas / Belize border
        _port( 1,  1, ratio=3),          # S — Acapulco Pacific
        _port( 0,  0, ratio=3),          # W — Puerto Vallarta
    ]
    return MapData(map_id="mexico", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Korea — 矿石↑↑ 砖块↑  (朝鲜半岛山脉)
# Shape: very narrow N-S (2 wide, 4 tall)
# q=0..1, r=-3..1
# ---------------------------------------------------------------------------

def korea_map() -> MapData:
    # Korean peninsula: narrow N-S (only 2 hex wide), with Jeju
    # as a separate island off the S coast.
    tiles = [
        # --- N Korea (Baekdu area, narrow top) ---
        _tile( 0, -4, "mountains", 9),   # Baekdu highlands
        _tile( 1, -4, "forest",    6),   # Amnok river forests

        # --- Pyongyang region ---
        _tile( 0, -3, "mountains", 4),   # Nangnim mountains
        _tile( 1, -3, "fields",   11),   # Pyongyang plain

        # --- DMZ / central ---
        _tile( 0, -2, "mountains", 3),   # Taebaek range N
        _tile( 1, -2, "pasture",   8),   # Hwanghae coast

        # --- Seoul area ---
        _tile( 0, -1, "mountains",10),   # Taebaek central
        _tile( 1, -1, "fields",    5),   # Seoul / Han River plain

        # --- Central S Korea ---
        _tile( 0,  0, "hills",     2),   # Sobaek range
        _tile( 1,  0, "fields",    9),   # Chungcheong plain

        # --- Busan / Gwangju area ---
        _tile( 0,  1, "mountains", 4),   # Jirisan S mountains
        _tile( 1,  1, "hills",    11),   # Gyeongsang (Busan area)

        # --- SW tip (Mokpo) ---
        _tile( 0,  2, "fields",    6),   # Jeolla plain

        # --- Jeju (SEPARATE volcanic island far S) ---
        _tile(-1,  4, "mountains",12),   # Hallasan volcano (Jeju)
    ]
    ports = [
        _port( 0, -4, ratio=3),          # N — Yellow Sea far N
        _port( 1, -4, "ore"),            # NE — East Sea N (Wonsan)
        _port( 1, -2, ratio=3),          # W — Yellow Sea mid
        _port( 1, -1, ratio=3),          # W — Incheon (Seoul port)
        _port( 1,  0, ratio=3),          # E — East Sea (Donghae)
        _port( 1,  1, ratio=3),          # SE — Busan
        _port( 0,  2, "brick"),          # SW — Mokpo / Jeolla
        _port(-1,  4, ratio=3),          # Jeju — volcanic island port
    ]
    return MapData(map_id="korea", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Indonesia — 木材↑↑ 砖块↑  (热带雨林·群岛)
# Shape: E-W island chain (4 island groups with gaps)
# Sumatra(W), Java, Borneo/Sulawesi, Maluku/Papua(E)
# ---------------------------------------------------------------------------

def indonesia_map() -> MapData:
    # Indonesia: long E-W archipelago. 4 main island clusters
    # (Sumatra, Java, Borneo, Sulawesi/Papua) separated by sea gaps.
    tiles = [
        # --- Sumatra (far W island, diagonal NW-SE) ---
        _tile(-5,  0, "forest",    9),   # Aceh (NW tip)
        _tile(-5,  1, "mountains", 6),   # Bukit Barisan
        _tile(-4,  1, "forest",    4),   # Riau forests
        _tile(-4,  2, "hills",    11),   # S Sumatra / Palembang

        # --- Java (S island chain, elongated E-W) ---
        _tile(-2,  2, "fields",    3),   # W Java (Jakarta rice)
        _tile(-1,  2, "forest",    8),   # C Java volcanoes
        _tile( 0,  2, "hills",    10),   # E Java / Surabaya

        # --- Bali / Lombok (small islands between Java and Flores) ---
        _tile( 1,  2, "mountains", 5),   # Bali

        # --- Borneo (large central island, N of Java) ---
        _tile(-1,  0, "forest",    2),   # W Kalimantan
        _tile( 0,  0, "forest",    9),   # C Kalimantan (Dayak forests)
        _tile( 1,  0, "mountains", 6),   # NE Kalimantan

        # --- Sulawesi (K-shaped island E of Borneo) ---
        _tile( 3,  0, "hills",     4),   # N Sulawesi (Manado)
        _tile( 3,  1, "pasture",   5),   # S Sulawesi (Makassar)

        # --- Maluku / Spice Islands (small cluster) ---
        _tile( 5,  0, "forest",   11),   # Maluku (Ternate, nutmeg)

        # --- Papua / New Guinea W half (large E island) ---
        _tile( 6, -1, "mountains",12),   # Jayawijaya Mts
        _tile( 6,  0, "forest",    3),   # Papua lowland rainforest
        _tile( 7, -1, "desert"),          # Merauke savanna (dry S)
        _tile( 7,  0, "fields",    8),   # Papua S plains
    ]
    ports = [
        _port(-5,  0, ratio=3),          # Sumatra NW — Malacca Strait
        _port(-5,  1, "wood"),           # Sumatra W — timber export
        _port(-4,  2, ratio=3),          # Sumatra S — Sunda Strait
        _port(-2,  2, ratio=3),          # Java W — Jakarta
        _port( 0,  2, ratio=3),          # Java E — Surabaya
        _port( 1,  0, ratio=3),          # Borneo N — South China Sea
        _port( 3,  1, ratio=3),          # Sulawesi S — Makassar
        _port( 5,  0, ratio=3),          # Maluku — Spice Islands
        _port( 7,  0, "brick"),          # Papua S — Pacific
    ]
    return MapData(map_id="indonesia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# New Zealand — 牧羊↑↑ 矿石↑
# Shape: two elongated islands separated by Cook Strait (gap at r=0);
#        North Island: volcanoes + dairy; South Island: Southern Alps + Canterbury Plains + Fiordland
# ---------------------------------------------------------------------------

def new_zealand_map() -> MapData:
    # Two elongated islands running NE-SW, separated by Cook Strait.
    # North Island: volcanic plateau + dairy/sheep.
    # South Island: Southern Alps spine + Canterbury Plains E + Fiordland W.
    tiles = [
        # ── North Island (diagonal NE-SW cluster) ──
        _tile(-1, -4, "hills",     9),   # Northland (Cape Reinga tip)
        _tile( 0, -4, "forest",    6),   # Auckland isthmus
        _tile(-1, -3, "fields",   11),   # Waikato (dairy heartland)
        _tile( 0, -3, "mountains", 4),   # Central Plateau (Ruapehu volcano)
        _tile(-1, -2, "pasture",   3),   # Hawke's Bay sheep country
        _tile( 0, -2, "hills",     8),   # Wellington / Wairarapa

        # ── Cook Strait (large sea gap) ──

        # ── South Island (longer, diagonal NE-SW) ──
        _tile( 2,  0, "mountains",10),   # Marlborough Sounds / Kaikoura
        _tile( 3,  0, "fields",    5),   # Marlborough (vineyards)
        _tile( 2,  1, "mountains", 2),   # Southern Alps N (Arthur's Pass)
        _tile( 3,  1, "fields",   11),   # Canterbury Plains (sheep/wheat)
        _tile( 2,  2, "forest",   12),   # Westland rainforest (W Coast)
        _tile( 3,  2, "mountains", 4),   # Mt Cook / Aoraki
        _tile( 4,  2, "pasture",   6),   # Otago (merino country)
        _tile( 3,  3, "mountains", 9),   # Fiordland peaks
        _tile( 4,  3, "pasture",   5),   # Southland sheep

        # ── Stewart Island (SEPARATE far S island) ──
        _tile( 3,  5, "forest",    8),   # Stewart Island / Rakiura
    ]
    ports = [
        _port(-1, -4, ratio=3),          # N — Northland tip
        _port( 0, -4, ratio=3),          # NE — Auckland (Hauraki Gulf)
        _port( 0, -2, "sheep"),          # S N.I. — Wellington (wool!)
        _port( 3,  0, ratio=3),          # N S.I. — Marlborough
        _port( 3,  1, "wheat"),          # E — Lyttelton (Canterbury grain)
        _port( 2,  2, ratio=3),          # W — Hokitika (W Coast fjords)
        _port( 4,  3, ratio=3),          # SE — Dunedin / Otago
        _port( 3,  5, ratio=3),          # Stewart — Bluff strait
    ]
    return MapData(map_id="new_zealand", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# France — 小麦↑ 牧羊↑ 木材↑
# Shape: Brittany protrusion W, roughly hexagonal, Pyrenees S, Alps SE
# N=Normandy/Champagne/Alsace, W=Loire/Landes, C=Massif Central, SE=Alps, S=Pyrenees
# ---------------------------------------------------------------------------

def france_map() -> MapData:
    # France's iconic "hexagon" shape with Brittany protrusion W
    # and Corsica as a separate island SE.
    tiles = [
        # --- Channel coast (N, r=-2) ---
        _tile( 0, -2, "fields",    9),   # Normandy (dairy/grain)
        _tile( 1, -2, "fields",    6),   # Picardie / Flanders

        # --- Brittany + Paris basin (r=-1) ---
        _tile(-2, -1, "hills",    11),   # Brittany (granite bocage)
        _tile(-1, -1, "pasture",   4),   # Normandy W (cattle)
        _tile( 0, -1, "fields",    3),   # Paris Basin
        _tile( 1, -1, "forest",    8),   # Ardennes

        # --- Main body (widest row, with W Brittany tip) ---
        _tile(-3,  0, "mountains", 5),   # Finistère (Brittany far W tip)
        _tile(-2,  0, "pasture",  10),   # Vendée / Loire mouth
        _tile(-1,  0, "fields",    2),   # Loire Valley
        _tile( 0,  0, "forest",    6),   # Burgundy forests
        _tile( 1,  0, "mountains", 9),   # Jura / Vosges
        _tile( 2,  0, "mountains", 4),   # Alps (Mont Blanc)

        # --- Central / South (r=1) ---
        _tile(-2,  1, "forest",    5),   # Landes pine forest
        _tile(-1,  1, "hills",    11),   # Massif Central
        _tile( 0,  1, "fields",    3),   # Rhône Valley
        _tile( 1,  1, "mountains",12),   # French Alps S

        # --- Mediterranean south (r=2) ---
        _tile(-1,  2, "pasture",   8),   # Gascony / Basque
        _tile( 0,  2, "desert"),          # Camargue salt flats
        _tile( 1,  2, "hills",    10),   # Provence / Côte d'Azur

        # --- Corsica (SEPARATE island, SE) ---
        _tile( 3,  2, "mountains", 5),   # Corsica mountains
        _tile( 3,  3, "forest",    4),   # Corsica S
    ]
    ports = [
        _port( 0, -2, ratio=3),          # N — Normandy (English Channel)
        _port(-2, -1, ratio=3),          # NW — Brittany N
        _port(-3,  0, "wood"),           # W — Finistère (timber)
        _port(-2,  1, "sheep"),          # SW — Bay of Biscay (Bordeaux)
        _port( 0,  2, "wheat"),          # S — Marseille grain export
        _port( 1,  2, ratio=3),          # SE — Côte d'Azur
        _port( 2,  0, ratio=3),          # E — Alps border
        _port( 3,  2, ratio=3),          # Corsica — Bastia
    ]
    return MapData(map_id="france", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Germany — 木材↑ 矿石↑
# Shape: wider N (North Sea / Baltic coast), tapers to Bavarian Alps tip S
# N=North German Plain, W=Rhine/Ruhr, C=Thuringia/Harz, E=Saxony, SE=Bavaria, S=Alps
# ---------------------------------------------------------------------------

def germany_map() -> MapData:
    # Germany: wider in N (North Sea / Baltic coast), tapers to Bavarian Alps S.
    # Rhine valley W, Berlin/Saxony C-E, Bavaria S, Alps tip.
    tiles = [
        # --- Danish peninsula tip (r=-3): Schleswig ---
        _tile( 1, -3, "pasture",   9),   # Schleswig (Danish border)

        # --- N coast row (r=-2): North Sea → Baltic ---
        _tile( 0, -2, "pasture",   6),   # Niedersachsen (North Sea coast)
        _tile( 1, -2, "fields",    4),   # Hamburg / Lower Saxony
        _tile( 2, -2, "fields",   11),   # Mecklenburg (Baltic)
        _tile( 3, -2, "forest",    3),   # Pomerania

        # --- Main body (r=-1): Rhine → Berlin → Poland border ---
        _tile(-1, -1, "hills",     8),   # NRW / Rhine Highlands
        _tile( 0, -1, "forest",    5),   # Lower Saxony forest
        _tile( 1, -1, "fields",   10),   # Saxony-Anhalt
        _tile( 2, -1, "fields",    2),   # Brandenburg / Berlin
        _tile( 3, -1, "mountains", 9),   # Erzgebirge (ore mts)

        # --- C-S body (r=0): Rhine Valley → Thuringia → Bohemia border ---
        _tile(-1,  0, "forest",    6),   # Black Forest
        _tile( 0,  0, "hills",     5),   # Swabian Alb
        _tile( 1,  0, "fields",   12),   # Franconia (Nuremberg)
        _tile( 2,  0, "mountains", 4),   # Bavarian Forest

        # --- S Bavaria (r=1) ---
        _tile( 0,  1, "desert"),          # Upper Rhine floodplain
        _tile( 1,  1, "pasture",  11),   # Munich / Allgäu dairy
        _tile( 2,  1, "mountains", 3),   # Bavarian Alps

        # --- Alps tip (r=2) ---
        _tile( 1,  2, "mountains", 8),   # Zugspitze / Austrian border
    ]
    ports = [
        _port( 1, -3, ratio=3),          # N — Kiel / Danish border
        _port( 0, -2, ratio=3),          # NW — Hamburg (North Sea)
        _port( 3, -2, ratio=3),          # NE — Rostock (Baltic)
        _port( 3, -1, "ore"),            # E — Erzgebirge ore export
        _port(-1, -1, ratio=3),          # W — Cologne (Rhine)
        _port(-1,  0, "wood"),           # W — Black Forest timber
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
    # Very elongated N→S country. Wider in the north (Chaco/Pampas),
    # narrowing southward through Patagonia. NW edge = Andes spine.
    # Tierra del Fuego sits as a SEPARATE island off the southern tip.
    tiles = [
        # --- N Argentina: Gran Chaco → Misiones (r=-3) ---
        _tile( 0, -3, "forest",    9),   # Gran Chaco (dry tropical forest)
        _tile( 1, -3, "fields",    6),   # Misiones / Mesopotamia (subtropical)
        _tile( 2, -3, "hills",    11),   # Corrientes / Entre Ríos (hilly NE)
        # --- NW Andes / N interior (r=-2) ---
        _tile(-1, -2, "desert"),          # Puna plateau (Atacama edge, arid 3500m+)
        _tile( 0, -2, "mountains", 4),   # NW Andes (Jujuy / Salta peaks)
        _tile( 1, -2, "fields",   10),   # Tucumán / Santiago del Estero (sugar)
        _tile( 2, -2, "pasture",   3),   # N Chaco / Formosa dry plains
        # --- Mendoza Andes / Pampas heartland (r=-1) ---
        _tile(-1, -1, "mountains", 8),   # Mendoza Andes (wine country)
        _tile( 0, -1, "fields",    5),   # Pampas W (grain, soy)
        _tile( 1, -1, "fields",    2),   # Pampas E (Buenos Aires province)
        _tile( 2, -1, "pasture",   9),   # Pampas S (cattle ranches)
        # --- S Pampas / La Pampa (r=0) ---
        _tile(-1,  0, "pasture",   6),   # La Pampa (cattle, dry grassland)
        _tile( 0,  0, "fields",   12),   # S Pampas (winter wheat)
        _tile( 1,  0, "hills",     4),   # Sierras of Buenos Aires (Tandilia)
        # --- N Patagonia (r=1) — country narrows ---
        _tile(-1,  1, "pasture",  11),   # N Patagonia (Merino sheep)
        _tile( 0,  1, "pasture",  10),   # Patagonia plateau (windswept steppe)
        # --- S Patagonia (r=2) ---
        _tile(-1,  2, "mountains", 3),   # Patagonian Andes (Nahuel Huapi lakes)
        _tile( 0,  2, "forest",    8),   # Andean forests (ancient lenga beech)
        # --- Santa Cruz / S tip (r=3) ---
        _tile( 0,  3, "hills",     5),   # S Patagonia (Santa Cruz, glaciers)
        # --- Tierra del Fuego — SEPARATE island off the south tip ---
        _tile(-2,  5, "hills",     9),   # Tierra del Fuego (Ushuaia, end of world)
    ]
    ports = [
        _port( 2, -3, ratio=3),           # NE — Río de la Plata / Paraná delta
        _port( 2, -1, ratio=3),           # E  — Buenos Aires coast (Atlantic)
        _port( 1,  0, ratio=3),           # SE — Mar del Plata
        _port( 0,  1, "sheep"),           # S  — Patagonian coast (wool export!)
        _port(-1,  2, ratio=3),           # SW — Patagonian fjords (Comahue)
        _port( 0,  3, ratio=3),           # S  — Santa Cruz coast
        _port(-2,  5, ratio=3),           # IS — Tierra del Fuego / Ushuaia
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
    # Italy's iconic boot runs vertically N→S with slight SE lean.
    # Sardinia is a separate island to the W, Sicily is a separate
    # island SW of the boot toe.
    tiles = [
        # --- Sardinia (separate island, far W) ---
        _tile(-3,  0, "hills",     9),   # Sardinia N (cork oak, nuraghi)
        _tile(-3,  1, "forest",    6),   # Sardinia S (coastal macchia)

        # --- Alps (N barrier, horizontal line at top) ---
        _tile(-1, -3, "mountains", 4),   # W Alps (Mont Blanc)
        _tile( 0, -3, "mountains",11),   # Central Alps
        _tile( 1, -3, "mountains", 3),   # Dolomites
        _tile( 2, -4, "hills",     8),   # Friuli / Venetian hills

        # --- Po Valley (the breadbasket row) ---
        _tile(-1, -2, "fields",   10),   # Piedmont (rice)
        _tile( 0, -2, "fields",    5),   # Lombardy (maize)
        _tile( 1, -2, "fields",    2),   # Veneto (corn)
        _tile( 2, -3, "hills",     9),   # Venice / Adriatic coast

        # --- Ligurian / Tuscan coast ---
        _tile( 0, -1, "forest",    6),   # Tuscany (olive, Chianti)

        # --- Central Italy / Umbria ---
        _tile( 1, -1, "hills",     5),   # Umbria / Marche

        # --- Rome / Abruzzo (boot's upper leg) ---
        _tile( 0,  0, "fields",    4),   # Lazio (Rome)
        _tile( 1,  0, "mountains",12),   # Abruzzo Apennines

        # --- Campania / Puglia (boot widens into heel) ---
        _tile( 0,  1, "pasture",  10),   # Campania (Naples)
        _tile( 1,  1, "desert"),          # Puglia Tavoliere (dry heel)

        # --- Basilicata / Calabria (narrow leg) ---
        _tile( 0,  2, "mountains", 3),   # Basilicata Apennines
        _tile( 1,  2, "hills",    11),   # Salento heel tip

        # --- Toe ---
        _tile( 0,  3, "hills",     8),   # Reggio Calabria (toe)

        # --- Sicily (SEPARATE island, SW of toe) ---
        _tile(-2,  5, "mountains",10),   # Sicily N (Mt Etna)
        _tile(-1,  5, "fields",    6),   # Sicily S (ancient granary)
    ]
    ports = [
        _port(-3,  0, ratio=3),          # Sardinia N — Tyrrhenian Sea
        _port(-3,  1, "wood"),           # Sardinia S — timber coast
        _port(-1, -3, ratio=3),          # NW — Ligurian Sea (Genova)
        _port( 2, -3, ratio=3),          # NE — Venice / Adriatic
        _port( 1,  1, "wheat"),          # SE — Puglia grain export
        _port( 0,  3, ratio=3),          # S — Messina strait (toe)
        _port(-2,  5, "ore"),            # Sicily N — Palermo
        _port(-1,  5, ratio=3),          # Sicily S — Catania
    ]
    return MapData(map_id="italy", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Scandinavia — 木材↑↑ 矿石↑
# Shape: elongated N-S peninsula; Norway W (fjord coast + mountains),
#        Sweden E (taiga forests), Finland SE (lake district), Denmark S (farming)
# ---------------------------------------------------------------------------

def scandinavia_map() -> MapData:
    # Elongated N-S peninsula. Norway (q=0, fjord west), Sweden (q=1, taiga center),
    # Finland (q=2, lake district east), Denmark S (attached via Jutland at q=0 south tail).
    # Very narrow E-W: only 3 columns.
    tiles = [
        # --- Norway (q=0) — long W fjord coast from Nordkapp down to Denmark ---
        _tile( 0, -5, "mountains", 9),   # Finnmark / Nordkapp (arctic tundra)
        _tile( 0, -4, "mountains", 4),   # Lofoten / Vesterålen (fjord mts)
        _tile( 0, -3, "forest",   10),   # N Norway (Narvik region)
        _tile( 0, -2, "forest",    3),   # Trondheim fjord forests
        _tile( 0, -1, "pasture",  11),   # Bergen / W fjord coast
        _tile( 0,  0, "fields",    5),   # S Norway (Oslo fjord farmland)
        # --- Denmark (dangling S tail, "attached via Jutland") ---
        _tile( 0,  1, "fields",    8),   # Jutland (Danish mainland)
        _tile( 0,  2, "pasture",  12),   # Danish islands (Funen/Sjælland, dairy)

        # --- Sweden (q=1) — taiga spine ---
        _tile( 1, -5, "desert"),          # Finnmark plateau (sub-arctic barren)
        _tile( 1, -4, "forest",    6),   # Swedish Lapland
        _tile( 1, -3, "forest",    9),   # N Sweden taiga
        _tile( 1, -2, "forest",    5),   # C Sweden
        _tile( 1, -1, "fields",    4),   # Mälaren (Stockholm region)
        _tile( 1,  0, "forest",    2),   # Götaland forests
        _tile( 1,  1, "fields",   10),   # Skåne (most fertile plain)

        # --- Finland (q=2) — lake district, shorter than Sweden ---
        _tile( 2, -4, "forest",    3),   # N Finland / Lapland
        _tile( 2, -3, "forest",    8),   # Finnish lakes (Kainuu)
        _tile( 2, -2, "hills",    11),   # Tampere / central lakes
        _tile( 2, -1, "pasture",   6),   # SW Finland / Turku coast
        _tile( 2,  0, "fields",    9),   # Gulf of Finland (Helsinki)
    ]
    ports = [
        _port( 0, -5, ratio=3),          # N  — Arctic (Nordkapp)
        _port( 0, -4, "ore"),            # NW — Narvik / Kiruna iron ore
        _port( 0, -1, ratio=3),          # W  — Bergen / Stavanger (N Sea)
        _port( 0,  0, "wood"),           # SW — S Norway timber export
        _port( 0,  2, "sheep"),          # S  — Danish islands (dairy/livestock)
        _port( 1,  1, ratio=3),          # SE — Skåne / Øresund strait
        _port( 2,  0, ratio=3),          # E  — Gulf of Finland
        _port( 2, -1, ratio=3),          # E  — Turku / W Finland coast
    ]
    return MapData(map_id="scandinavia", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Spain — 小麦↑ 牧羊↑ 砖块↑
# Shape: rectangular Iberian Peninsula; Galicia NW, Pyrenees NE, Meseta center,
#        Andalusia S, SE Almería (driest place in Europe = desert)
# ---------------------------------------------------------------------------

def spain_map() -> MapData:
    # Iberian Peninsula: rectangular block, Galicia NW, Pyrenees NE,
    # Meseta center, Andalusia S, Gibraltar SW tip. Portugal on W
    # coast is implicit (same landmass).
    tiles = [
        # --- N coast (r=-2): Galicia → Cantabria → Pyrenees ---
        _tile(-2, -2, "hills",     9),   # Galicia (Atlantic coast)
        _tile(-1, -2, "mountains", 6),   # Cantabrian / Picos de Europa
        _tile( 0, -2, "pasture",  11),   # Basque Country
        _tile( 1, -2, "mountains", 4),   # Pyrenees

        # --- N Meseta / Ebro (r=-1) ---
        _tile(-2, -1, "forest",    3),   # Portugal N forests
        _tile(-1, -1, "fields",    8),   # Castile-León (wheat Meseta)
        _tile( 0, -1, "fields",   10),   # Ebro Valley (vineyards)
        _tile( 1, -1, "hills",     5),   # Catalonia

        # --- Central Meseta (r=0) ---
        _tile(-2,  0, "pasture",   9),   # Portugal C / Alentejo
        _tile(-1,  0, "fields",    6),   # Castile La Mancha
        _tile( 0,  0, "hills",     2),   # Aragón / Valencia interior
        _tile( 1,  0, "hills",    11),   # Valencia coast

        # --- S Andalusia (r=1) ---
        _tile(-2,  1, "fields",   12),   # Algarve
        _tile(-1,  1, "pasture",   3),   # Seville / Andalusia
        _tile( 0,  1, "desert"),          # Almería (driest place in Europe)
        _tile( 1,  1, "hills",     8),   # Costa del Sol / Granada

        # --- Balearic Islands (SEPARATE small islands off E coast) ---
        _tile( 3,  0, "hills",     4),   # Mallorca / Menorca

        # --- Canary Islands (SEPARATE volcanic islands far SW) ---
        _tile(-4,  3, "mountains", 5),   # Tenerife / Gran Canaria
    ]
    ports = [
        _port(-2, -2, ratio=3),          # NW — Galicia (A Coruña)
        _port( 0, -2, ratio=3),          # N — Cantabrian Sea (Bilbao)
        _port( 1, -2, ratio=3),          # NE — Pyrenees Med (Barcelona)
        _port( 1,  0, ratio=3),          # E — Valencia (oranges)
        _port( 1,  1, ratio=3),          # S — Costa del Sol (Málaga)
        _port(-1,  1, "wheat"),          # SW — Seville (grain)
        _port(-2,  1, ratio=3),          # SW — Algarve (Lisbon)
        _port(-2,  0, "sheep"),          # W — Portugal (wool)
        _port( 3,  0, ratio=3),          # Balearic — Palma de Mallorca
        _port(-4,  3, ratio=3),          # Canary — Las Palmas
    ]
    return MapData(map_id="spain", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Turkey — 小麦↑ 牧羊↑ 矿石↑
# Shape: wide E-W rectangle (Asia Minor); Black Sea coast N, Aegean W, Med S,
#        Pontus Mts N coast, Taurus Mts S, Central Anatolian plateau = desert steppe
# ---------------------------------------------------------------------------

def turkey_map() -> MapData:
    # Wide E-W rectangle (Asia Minor). Uses diagonal rows so screen y stays banded:
    # each column shifts r down by ~0.5 moving east. 3 stacked hexes per column.
    # Thrace/Istanbul dangles NW at (-1,-1); Ararat at far E (6,-4).
    tiles = [
        # --- Thrace / Istanbul (NW Bosphorus bridge) ---
        _tile(-1, -1, "hills",     5),   # Thrace / Istanbul (Bosphorus)

        # --- Black Sea coast (top screen row) ---
        _tile( 0, -1, "fields",    6),   # Marmara / NW Anatolia (grain)
        _tile( 1, -2, "forest",    3),   # Bithynia (Black Sea W forests)
        _tile( 2, -2, "mountains",11),   # Pontus Mts (W)
        _tile( 3, -3, "mountains", 4),   # Pontus Mts (central)
        _tile( 4, -3, "forest",   10),   # NE Pontus (Trabzon)
        _tile( 5, -4, "forest",    5),   # Rize / NE coast
        _tile( 6, -4, "mountains", 9),   # Mt Ararat (E Turkey / Armenia border)

        # --- Anatolian plateau (middle screen row) ---
        _tile( 0,  0, "fields",   12),   # W Anatolia (Aegean hinterland)
        _tile( 1, -1, "hills",     2),   # Phrygia / Ankara outskirts
        _tile( 2, -1, "desert"),          # Central Anatolia (Konya salt steppe)
        _tile( 3, -2, "hills",     8),   # Cappadocia
        _tile( 4, -2, "pasture",  10),   # E Anatolia plateau (vast pastoral)
        _tile( 5, -3, "pasture",   8),   # Erzurum highlands

        # --- Mediterranean / Taurus coast (bottom screen row) ---
        _tile( 0,  1, "hills",    11),   # SW Turkey / Bodrum (Aegean-Med corner)
        _tile( 1,  0, "pasture",   3),   # Lycia / Antalya
        _tile( 2,  0, "mountains", 4),   # Taurus Mts (S barrier)
        _tile( 3, -1, "fields",    9),   # Pamphylia (Med plain)
        _tile( 4, -1, "fields",    6),   # Çukurova / Cilicia (cotton/grain)
        _tile( 5, -2, "hills",     9),   # SE Turkey / Kurdish highlands
    ]
    ports = [
        _port(-1, -1, ratio=3),          # NW — Istanbul / Bosphorus (strait!)
        _port( 1, -2, ratio=3),          # N  — Black Sea W (Zonguldak)
        _port( 5, -4, ratio=3),          # NE — Rize / E Black Sea
        _port( 6, -4, "ore"),            # E  — Ararat / Caucasus mines
        _port( 0,  0, ratio=3),          # W  — Aegean (Izmir)
        _port( 0,  1, "sheep"),          # SW — Bodrum / Aegean islands trade
        _port( 4, -1, "wheat"),          # S  — Mersin / Çukurova grain
        _port( 5, -2, ratio=3),          # SE — Iskenderun coast
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
    # 39 tiles sculpted as an Africa-shaped continent:
    # Sahara band across the north, West Africa bulge, Horn of Africa east
    # bulge, Congo rainforest heart, Kalahari south, narrow Cape tip, and
    # Madagascar as a separate 2-tile island east of Mozambique.
    tiles = [
        # North: Mediterranean coast / Sahara top edge  (r=-4, 4 tiles)
        _tile(0, -4, "desert"),               # Morocco / Algeria coast (Atlas foothills)
        _tile(1, -4, "desert"),               # Tunisia / Libya coast
        _tile(2, -4, "desert"),               # Egypt / Nile delta edge
        _tile(3, -4, "fields",    8),         # Nile valley (Egypt agriculture)
        # Sahara wide band  (r=-3, 6 tiles)
        _tile(-1, -3, "pasture",  2),         # Senegal / Mauritania coast (Sahel edge)
        _tile(0, -3, "desert"),                # W Sahara
        _tile(1, -3, "desert"),                # Central Sahara (Algeria)
        _tile(2, -3, "desert"),                # Libya interior
        _tile(3, -3, "desert"),                # Egypt south / Nubia
        _tile(4, -3, "fields",    5),         # Red Sea coast / Eritrea
        # Sahel / Horn belt  (r=-2, 6 tiles)
        _tile(-1, -2, "fields",   9),         # Senegal / Guinea (Sahel farmland)
        _tile(0, -2, "pasture",  11),         # Mali / Niger (Sahel pastoral)
        _tile(1, -2, "fields",    4),         # Chad (Lake Chad basin)
        _tile(2, -2, "desert"),                # Sudan desert
        _tile(3, -2, "mountains", 6),         # Ethiopian Highlands (Abyssinia)
        _tile(4, -2, "fields",   10),         # Horn of Africa / Somalia (east bulge)
        # Guinea coast / Sudan belt  (r=-1, 6 tiles)
        _tile(-2, -1, "forest",   3),         # Guinea / Sierra Leone (W Africa bulge)
        _tile(-1, -1, "forest",  11),         # Ivory Coast / Ghana (rainforest)
        _tile(0, -1, "forest",    5),         # Nigeria (Niger delta, tropical forest)
        _tile(1, -1, "pasture",   9),         # Cameroon grasslands
        _tile(2, -1, "forest",    8),         # S Sudan (swamps / jungle)
        _tile(3, -1, "mountains",12),         # Rift Valley / Kenya highlands
        # Equatorial Africa — Congo Basin  (r=0, 5 tiles)
        _tile(-2, 0, "forest",    6),         # Gabon rainforest
        _tile(-1, 0, "forest",    4),         # Congo basin W
        _tile(0, 0, "forest",     9),         # DRC heart of the Congo
        _tile(1, 0, "hills",     10),         # Uganda / Rwanda hills
        _tile(2, 0, "mountains",  3),         # Kilimanjaro / Tanzania
        # Southern Africa upper  (r=1, 4 tiles)
        _tile(-2, 1, "forest",    8),         # Angola forests
        _tile(-1, 1, "pasture",   5),         # Zambia / Copperbelt
        _tile(0, 1, "fields",    11),         # Malawi / Mozambique interior
        _tile(1, 1, "hills",      2),         # Zimbabwe plateau
        # Southern Africa lower  (r=2, 3 tiles)
        _tile(-2, 2, "desert"),                # Namib desert (Kalahari W)
        _tile(-1, 2, "pasture",   6),         # Botswana / Kalahari pastoral
        _tile(0, 2, "hills",      4),         # Transvaal / KwaZulu-Natal
        # Cape tip  (r=3, 2 tiles — narrow taper)
        _tile(-2, 3, "fields",   10),         # Western Cape (vineyards)
        _tile(-1, 3, "mountains",11),         # Drakensberg / Cape of Good Hope
        # Madagascar — separate island chain east of Mozambique
        _tile(3, 1, "forest",     9),         # N Madagascar (rainforest)
        _tile(3, 2, "hills",      3),         # S Madagascar (dry highlands)
    ]
    ports = [
        _port(3, -4, ratio=3),                # Nile delta (Mediterranean)
        _port(4, -3, "wheat"),                # Red Sea coast
        _port(4, -2, ratio=3),                # Horn of Africa (Indian Ocean)
        _port(3, 1, "wood"),                  # Madagascar N
        _port(-1, 3, ratio=3),                # Cape of Good Hope
        _port(-2, 3, ratio=3),                # Western Cape
        _port(-2, 1, "sheep"),                # Angola coast
        _port(-2, -1, ratio=3),               # Guinea coast
        _port(-1, -3, "ore"),                 # Mauritania (iron ore)
        _port(0, -4, ratio=3),                # Morocco coast
    ]
    return MapData(map_id="africa_xl", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Eurasia XL — 资源均衡大陆  (欧亚大陆，从西欧到东亚)
# desert=5, forest=8, fields=7, mountains=7, pasture=6, hills=4
# ---------------------------------------------------------------------------

def eurasia_xl_map() -> MapData:
    # 42 tiles sculpted as the Eurasian supercontinent spanning from
    # Iberia in the west to Far East in the east, with southern bulges
    # for Arabia, India and Southeast Asia. British Isles are a
    # separate NW island pair and Japan is a separate 3-tile island chain
    # off the far east coast.
    tiles = [
        # Arctic Siberia strip (far north)  (r=-4, 6 tiles)
        _tile(0, -4, "forest",    6),         # Scandinavia / Kola
        _tile(1, -4, "forest",    3),         # N Russia tundra
        _tile(2, -4, "forest",    9),         # W Siberia tundra
        _tile(3, -4, "forest",   11),         # Central Siberia
        _tile(4, -4, "forest",    5),         # E Siberia / Yakutia
        _tile(5, -4, "mountains", 8),         # Chukotka / Kamchatka
        # Northern belt — N Russia / Siberia taiga  (r=-3, 7 tiles)
        _tile(-1, -3, "forest",   4),         # N Scandinavia
        _tile(0, -3, "forest",    9),         # NW Russia
        _tile(1, -3, "forest",   10),         # Ural region
        _tile(2, -3, "forest",    6),         # W Siberia taiga
        _tile(3, -3, "mountains", 2),         # Central Siberian plateau
        _tile(4, -3, "forest",   12),         # E Siberia taiga
        _tile(5, -3, "mountains", 4),         # Sakhalin / Sea of Okhotsk coast
        # Temperate main belt — Europe through China  (r=-2, 8 tiles)
        _tile(-2, -2, "pasture",  5),         # Iberia NW (Galicia / Portugal)
        _tile(-1, -2, "fields",   8),         # France / Germany heartland
        _tile(0, -2, "hills",    11),         # Alps / Carpathians
        _tile(1, -2, "pasture",   3),         # Ukraine / S Russia steppe
        _tile(2, -2, "fields",    6),         # Kazakhstan steppe
        _tile(3, -2, "pasture",   9),         # Mongolia steppe
        _tile(4, -2, "fields",    4),         # N China plain
        _tile(5, -2, "hills",    10),         # NE China / Manchuria
        # Southern temperate — Med / Caucasus / Central Asia / China  (r=-1, 8 tiles)
        _tile(-2, -1, "fields",   9),         # Iberia S / Andalusia
        _tile(-1, -1, "hills",    5),         # Italy / Balkans
        _tile(0, -1, "mountains", 8),         # Turkey / Caucasus
        _tile(1, -1, "fields",    2),         # Persia / Iran
        _tile(2, -1, "mountains",12),         # Pamir / Tian Shan
        _tile(3, -1, "mountains", 6),         # Himalayas / Tibet
        _tile(4, -1, "fields",   10),         # Central China (Yellow River)
        _tile(5, -1, "hills",     3),         # S China / Yangtze
        # Southern bulge — Arabia / India / SE Asia  (r=0, 6 tiles)
        _tile(-1, 0, "desert"),                # Arabia N
        _tile(0, 0, "desert"),                 # Arabia heart (Rub' al Khali)
        _tile(1, 0, "pasture",   11),         # Gulf / Oman coast
        _tile(2, 0, "fields",     4),         # Indus / Pakistan
        _tile(3, 0, "forest",     9),         # India (Ganges plain)
        _tile(4, 0, "forest",     5),         # Indochina / Myanmar
        # Far south bulge — Indian peninsula / SE Asia tip  (r=1, 2 tiles)
        _tile(0, 1, "hills",      6),         # Yemen / Hadhramaut
        _tile(1, 1, "forest",     8),         # S India / Kerala — Sri Lanka area
        # British Isles — separate NW island pair
        _tile(-4, -1, "pasture",  4),         # Scotland / N England
        _tile(-4, 0, "fields",   10),         # S England / Ireland
        # Japan — separate E island chain (Hokkaido / Honshu / Kyushu)
        _tile(7, -4, "mountains", 3),         # Hokkaido
        _tile(7, -3, "hills",    11),         # Honshu
        _tile(7, -2, "forest",    2),         # Kyushu / Ryukyu
    ]
    ports = [
        _port(-4, 0, "wheat"),                # British Isles (trade hub)
        _port(-4, -1, ratio=3),               # Scotland
        _port(-2, -2, ratio=3),               # Iberia Atlantic
        _port(-2, -1, "sheep"),               # S Iberia / Gibraltar
        _port(0, 1, ratio=3),                 # Yemen / Red Sea
        _port(1, 1, "wood"),                  # S India / Ceylon
        _port(4, 0, ratio=3),                 # Indochina
        _port(7, -2, "ore"),                  # Japan south
        _port(7, -4, ratio=3),                # Japan north
        _port(5, -4, ratio=3),                # Kamchatka
        _port(0, -4, ratio=3),                # Scandinavia
    ]
    return MapData(map_id="eurasia_xl", tiles=tiles, ports=ports)


# ---------------------------------------------------------------------------
# Americas XL — 木材↑↑ 小麦↑ 牧羊↑  (南北美洲全图)
# desert=3, forest=10, fields=8, pasture=7, hills=5, mountains=4
# ---------------------------------------------------------------------------

def americas_xl_map() -> MapData:
    # 42 tiles sculpted as the Americas — wide North America at top,
    # narrow Central America isthmus, wider South America middle
    # (Amazon / Brazil), tapering to Patagonia and Tierra del Fuego.
    # Caribbean rendered as 2 scattered separate islands east of Mexico.
    tiles = [
        # Canada / Alaska (far north)  (r=-5, 5 tiles)
        _tile(-2, -5, "forest",   9),         # Alaska / Yukon
        _tile(-1, -5, "forest",   6),         # NW Territories
        _tile(0, -5, "forest",    4),         # Hudson Bay / N Canada
        _tile(1, -5, "forest",   11),         # Quebec N / Labrador
        _tile(2, -5, "hills",     3),         # Newfoundland
        # Northern USA / S Canada  (r=-4, 6 tiles)
        _tile(-2, -4, "mountains",8),         # Pacific NW / BC (Cascades)
        _tile(-1, -4, "mountains",5),         # Rocky Mountains
        _tile(0, -4, "pasture",  10),         # Great Plains / Prairies
        _tile(1, -4, "forest",    2),         # Great Lakes / Midwest
        _tile(2, -4, "fields",   12),         # NE USA (New England)
        _tile(3, -4, "forest",    9),         # Maine / Nova Scotia
        # Southern USA  (r=-3, 5 tiles)
        _tile(-1, -3, "pasture",  4),         # California coast
        _tile(0, -3, "desert"),                # Arizona / Nevada (desert SW)
        _tile(1, -3, "fields",    6),         # Texas / Great Plains S
        _tile(2, -3, "fields",    8),         # Deep South / Mississippi
        _tile(3, -3, "pasture",  11),         # Florida / Gulf Coast
        # Mexico narrowing  (r=-2, 3 tiles)
        _tile(0, -2, "desert"),                # Sonora / Chihuahua desert
        _tile(1, -2, "mountains", 5),         # Sierra Madre / Mexico City
        _tile(2, -2, "fields",    9),         # Yucatán / S Mexico
        # Central America isthmus (narrowest)  (r=-1, 2 tiles)
        _tile(0, -1, "forest",   10),         # Guatemala / Honduras jungle
        _tile(1, -1, "forest",    3),         # Panama isthmus
        # Northern S America — widening  (r=0, 4 tiles)
        _tile(-1, 0, "mountains", 6),         # Andes N / Colombia
        _tile(0, 0, "forest",    11),         # Venezuela / Orinoco
        _tile(1, 0, "forest",     4),         # Guyana / Suriname
        _tile(2, 0, "hills",      8),         # Guiana shield
        # Amazon / Brazil wide middle (widest S America)  (r=1, 5 tiles)
        _tile(-2, 1, "fields",    9),         # Peru / Ecuador
        _tile(-1, 1, "mountains",10),         # Andes central / Bolivia
        _tile(0, 1, "forest",     5),         # Amazon W
        _tile(1, 1, "forest",     6),         # Amazon heart
        _tile(2, 1, "forest",     8),         # NE Brazil coast
        # Southern Brazil / Bolivia belt  (r=2, 4 tiles)
        _tile(-2, 2, "mountains", 4),         # Andes S / Chile N
        _tile(-1, 2, "pasture",  11),         # Bolivia / Altiplano
        _tile(0, 2, "fields",     9),         # Paraguay / Gran Chaco
        _tile(1, 2, "pasture",    3),         # S Brazil / Uruguay pampas
        # Argentina / Chile  (r=3, 3 tiles)
        _tile(-2, 3, "pasture",   5),         # Chile central coast
        _tile(-1, 3, "fields",   10),         # Pampas (Argentina heartland)
        _tile(0, 3, "pasture",   12),         # Patagonia N / Río Negro
        # Patagonia  (r=4, 2 tiles)
        _tile(-2, 4, "hills",     6),         # Chilean fjords
        _tile(-1, 4, "pasture",   2),         # Patagonia S (Santa Cruz)
        # Tierra del Fuego (southernmost tip)
        _tile(-2, 5, "mountains",11),         # Tierra del Fuego / Cape Horn
        # Caribbean — separate small islands (Cuba / Hispaniola area)
        _tile(5, -4, "fields",    4),         # Cuba / Bahamas
        _tile(5, -3, "forest",    8),         # Hispaniola / Puerto Rico
    ]
    ports = [
        _port(-2, -5, ratio=3),               # Alaska / Pacific
        _port(-2, -4, "wood"),                # Pacific NW
        _port(2, -5, ratio=3),                # Newfoundland / Atlantic
        _port(3, -4, "sheep"),                # New England
        _port(3, -3, ratio=3),                # Florida
        _port(5, -4, ratio=3),                # Cuba
        _port(5, -3, "wheat"),                # Hispaniola
        _port(2, 1, ratio=3),                 # NE Brazil
        _port(1, 2, "wood"),                  # Rio / S Brazil
        _port(-2, 5, ratio=3),                # Cape Horn
        _port(-2, 3, ratio=3),                # Chile central
        _port(-2, 1, "ore"),                  # Peru (copper / silver)
    ]
    return MapData(map_id="americas_xl", tiles=tiles, ports=ports)


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
