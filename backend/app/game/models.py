"""
Core data models for Catan game state.
All game state is plain Python dataclasses / dicts — no ORM needed (in-memory store).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Resource(str, Enum):
    WOOD = "wood"       # forest tiles
    BRICK = "brick"     # hills tiles
    WHEAT = "wheat"     # fields tiles
    SHEEP = "sheep"     # pasture tiles
    ORE = "ore"         # mountains tiles


class TileType(str, Enum):
    FOREST = "forest"
    HILLS = "hills"
    FIELDS = "fields"
    PASTURE = "pasture"
    MOUNTAINS = "mountains"
    DESERT = "desert"
    OCEAN = "ocean"


TILE_RESOURCE: Dict[TileType, Optional[Resource]] = {
    TileType.FOREST: Resource.WOOD,
    TileType.HILLS: Resource.BRICK,
    TileType.FIELDS: Resource.WHEAT,
    TileType.PASTURE: Resource.SHEEP,
    TileType.MOUNTAINS: Resource.ORE,
    TileType.DESERT: None,
    TileType.OCEAN: None,
}


class PieceType(str, Enum):
    ROAD = "road"
    SETTLEMENT = "settlement"
    CITY = "city"


class GamePhase(str, Enum):
    WAITING = "waiting"             # before game starts
    SETUP_FORWARD = "setup_forward"  # round 1 of initial placement (1→N)
    SETUP_BACKWARD = "setup_backward"  # round 2 (N→1)
    PLAYING = "playing"
    FINISHED = "finished"


class TurnStep(str, Enum):
    PRE_ROLL = "pre_roll"           # player must roll dice first
    ROBBER_DISCARD = "robber_discard"  # players with >7 cards must discard
    ROBBER_PLACE = "robber_place"    # rolling player places robber
    ROBBER_STEAL = "robber_steal"    # rolling player may steal one resource
    POST_ROLL = "post_roll"          # player can build / trade / end turn
    ROAD_BUILDING = "road_building"  # placing free roads from dev card
    YEAR_OF_PLENTY = "year_of_plenty"  # choosing 2 free resources
    MONOPOLY = "monopoly"           # choosing resource to monopolize


class DevCardType(str, Enum):
    KNIGHT = "knight"
    VICTORY_POINT = "victory_point"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"
    ROAD_BUILDING = "road_building"


# ---------------------------------------------------------------------------
# Build costs
# ---------------------------------------------------------------------------

BUILD_COST: Dict[PieceType, Dict[Resource, int]] = {
    PieceType.ROAD: {Resource.WOOD: 1, Resource.BRICK: 1},
    PieceType.SETTLEMENT: {Resource.WOOD: 1, Resource.BRICK: 1, Resource.WHEAT: 1, Resource.SHEEP: 1},
    PieceType.CITY: {Resource.WHEAT: 2, Resource.ORE: 3},
}

DEV_CARD_COST: Dict[Resource, int] = {Resource.ORE: 1, Resource.WHEAT: 1, Resource.SHEEP: 1}

# Victory points per piece
VP_TABLE: Dict[PieceType, int] = {
    PieceType.SETTLEMENT: 1,
    PieceType.CITY: 2,
    PieceType.ROAD: 0,
}

WINNING_VP = 10  # default; overridden by GameRules.victory_points_target


# ---------------------------------------------------------------------------
# Custom game rules
# ---------------------------------------------------------------------------

@dataclass
class GameRules:
    victory_points_target: int = 10  # 8, 10, or 12
    friendly_robber: bool = False     # don't move robber until player has 4+ VP
    starting_resources_double: bool = False  # 2x resources from 2nd setup settlement

    def to_dict(self):
        return {
            "victory_points_target": self.victory_points_target,
            "friendly_robber": self.friendly_robber,
            "starting_resources_double": self.starting_resources_double,
        }

    @staticmethod
    def from_dict(d: dict) -> "GameRules":
        return GameRules(
            victory_points_target=int(d.get("victory_points_target", 10)),
            friendly_robber=bool(d.get("friendly_robber", False)),
            starting_resources_double=bool(d.get("starting_resources_double", False)),
        )

# Piece supply limits per player
MAX_ROADS = 15
MAX_SETTLEMENTS = 5
MAX_CITIES = 4


# ---------------------------------------------------------------------------
# Map structures
# ---------------------------------------------------------------------------

@dataclass
class Port:
    # Tile (q, r) on which the port sits, plus the coastal side (0-5) it faces.
    q: int
    r: int
    resource: Optional[Resource]  # None = 3:1 generic port
    ratio: int = 3               # 2 for specific-resource ports, 3 for generic
    side: Optional[int] = None   # coastal edge index (HEX_DIRECTIONS), set by normalize_ports

    def to_dict(self):
        return {
            "q": self.q,
            "r": self.r,
            "resource": self.resource.value if self.resource else None,
            "ratio": self.ratio,
            "side": self.side,
        }

    @staticmethod
    def from_dict(d: dict) -> "Port":
        return Port(
            q=int(d.get("q", 0)),
            r=int(d.get("r", 0)),
            resource=Resource(d["resource"]) if d.get("resource") else None,
            ratio=int(d.get("ratio", 3)),
            side=int(d["side"]) if d.get("side") is not None else None,
        )


@dataclass
class Tile:
    q: int
    r: int
    tile_type: TileType
    token: Optional[int] = None  # 2-12, None for desert/ocean

    def to_dict(self):
        return {
            "q": self.q,
            "r": self.r,
            "tile_type": self.tile_type.value,
            "token": self.token,
            "resource": TILE_RESOURCE[self.tile_type].value if TILE_RESOURCE[self.tile_type] else None,
        }

    @staticmethod
    def from_dict(d: dict) -> "Tile":
        return Tile(
            q=int(d.get("q", 0)),
            r=int(d.get("r", 0)),
            tile_type=TileType(d.get("tile_type") or d.get("tileType") or "ocean"),
            token=d.get("token", None),
        )


@dataclass
class MapData:
    map_id: str
    tiles: List[Tile] = field(default_factory=list)
    ports: List[Port] = field(default_factory=list)

    def to_dict(self):
        return {
            "map_id": self.map_id,
            "tiles": [t.to_dict() for t in self.tiles],
            "ports": [p.to_dict() for p in self.ports],
        }

    @staticmethod
    def from_dict(d: dict) -> "MapData":
        return MapData(
            map_id=str(d.get("map_id") or d.get("mapId") or "unknown"),
            tiles=[Tile.from_dict(t) for t in (d.get("tiles") or [])],
            ports=[Port.from_dict(p) for p in (d.get("ports") or [])],
        )


# ---------------------------------------------------------------------------
# Piece placement — vertices and edges using axial + direction
# ---------------------------------------------------------------------------
# Vertex key: (q, r, corner) where corner in 0-5
# Edge key:   (q, r, side)   where side in 0-5

VertexKey = Tuple[int, int, int]
EdgeKey = Tuple[int, int, int]


@dataclass
class PlacedPiece:
    piece_type: PieceType
    player_id: str

    def to_dict(self):
        return {"piece_type": self.piece_type.value, "player_id": self.player_id}

    @staticmethod
    def from_dict(d: dict) -> "PlacedPiece":
        return PlacedPiece(
            piece_type=PieceType(d.get("piece_type") or d.get("pieceType") or "road"),
            player_id=str(d.get("player_id") or d.get("playerId") or ""),
        )


@dataclass
class DevCard:
    card_type: DevCardType
    bought_on_turn: int = -1  # turn number when bought, -1 = not yet bought

    def to_dict(self):
        return {"card_type": self.card_type.value, "bought_on_turn": self.bought_on_turn}

    @staticmethod
    def from_dict(d: dict) -> "DevCard":
        return DevCard(
            card_type=DevCardType(d.get("card_type", "knight")),
            bought_on_turn=int(d.get("bought_on_turn", -1)),
        )


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

@dataclass
class Player:
    player_id: str
    name: str
    color: str
    is_bot: bool = False
    resources: Dict[Resource, int] = field(default_factory=lambda: {r: 0 for r in Resource})
    victory_points: int = 0
    # placement counts for rule checking
    settlements_placed: int = 0
    cities_placed: int = 0
    roads_placed: int = 0
    # initial setup tracking
    setup_settlements: List[VertexKey] = field(default_factory=list)
    # longest road cache
    longest_road: int = 0
    # development cards
    dev_cards: List["DevCard"] = field(default_factory=list)
    knights_played: int = 0
    dev_card_played_this_turn: bool = False

    def has_resources(self, cost: Dict[Resource, int]) -> bool:
        return all(self.resources.get(res, 0) >= amt for res, amt in cost.items())

    def deduct(self, cost: Dict[Resource, int]):
        for res, amt in cost.items():
            self.resources[res] = self.resources.get(res, 0) - amt

    def add_resource(self, res: Resource, amt: int = 1):
        self.resources[res] = self.resources.get(res, 0) + amt

    def to_dict(self, hide_resources: bool = False):
        return {
            "player_id": self.player_id,
            "name": self.name,
            "color": self.color,
            "is_bot": self.is_bot,
            "resources": (
                {r.value: v for r, v in self.resources.items()}
                if not hide_resources
                else {r.value: sum(self.resources.values()) for r in [Resource.WOOD]}  # just show total
            ),
            "resource_count": sum(self.resources.values()),
            "victory_points": self.victory_points,
            "settlements_placed": self.settlements_placed,
            "cities_placed": self.cities_placed,
            "roads_placed": self.roads_placed,
            "longest_road": self.longest_road,
            "setup_settlements": [[vk[0], vk[1], vk[2]] for vk in self.setup_settlements],
            "dev_cards": [c.to_dict() for c in self.dev_cards] if not hide_resources else [],
            "dev_card_count": len(self.dev_cards),
            "knights_played": self.knights_played,
            "dev_card_played_this_turn": self.dev_card_played_this_turn,
        }

    @staticmethod
    def from_dict(d: dict) -> "Player":
        # resources are stored as {"wood": 0, ...}
        raw = d.get("resources") or {}
        resources: Dict[Resource, int] = {r: 0 for r in Resource}
        if isinstance(raw, dict):
            for k, v in raw.items():
                try:
                    resources[Resource(k)] = int(v)
                except Exception:
                    continue

        setup_settlements: List[VertexKey] = []
        for raw_vk in (d.get("setup_settlements") or []):
            if isinstance(raw_vk, (list, tuple)) and len(raw_vk) == 3:
                setup_settlements.append((int(raw_vk[0]), int(raw_vk[1]), int(raw_vk[2])))

        dev_cards_raw = d.get("dev_cards") or []
        dev_cards = [DevCard.from_dict(c) for c in dev_cards_raw]

        p = Player(
            player_id=str(d.get("player_id") or d.get("playerId") or ""),
            name=str(d.get("name") or ""),
            color=str(d.get("color") or "red"),
            is_bot=bool(d.get("is_bot", False)),
            resources=resources,
            victory_points=int(d.get("victory_points") or 0),
            settlements_placed=int(d.get("settlements_placed") or 0),
            cities_placed=int(d.get("cities_placed") or 0),
            roads_placed=int(d.get("roads_placed") or 0),
        )
        p.setup_settlements = setup_settlements
        p.longest_road = int(d.get("longest_road") or 0)
        p.dev_cards = dev_cards
        p.knights_played = int(d.get("knights_played") or 0)
        p.dev_card_played_this_turn = bool(d.get("dev_card_played_this_turn", False))
        return p


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class GameState:
    room_id: str
    map_data: MapData
    players: List[Player] = field(default_factory=list)
    phase: GamePhase = GamePhase.WAITING
    turn_step: TurnStep = TurnStep.PRE_ROLL
    current_player_index: int = 0
    setup_order: List[int] = field(default_factory=list)  # indices into players list
    setup_step: int = 0  # how many placements done in setup

    # Board state
    vertices: Dict[str, PlacedPiece] = field(default_factory=dict)  # key = "q,r,corner"
    edges: Dict[str, PlacedPiece] = field(default_factory=dict)    # key = "q,r,side"

    # Robber position
    robber_q: int = 0
    robber_r: int = 0

    # Last dice roll
    last_dice: Optional[List[int]] = None

    winner_id: Optional[str] = None

    # Longest road tracking
    longest_road_holder: Optional[str] = None
    longest_road_length: int = 0

    # Robber flow state
    players_to_discard: List[str] = field(default_factory=list)   # player_ids that still need to discard
    robber_steal_targets: List[str] = field(default_factory=list)  # eligible steal targets at new robber hex

    # Development cards
    dev_card_deck: List["DevCard"] = field(default_factory=list)
    current_turn_number: int = 0
    largest_army_holder: Optional[str] = None
    largest_army_size: int = 0
    road_building_remaining: int = 0  # roads left to place for road building card

    # Custom game rules
    rules: "GameRules" = field(default_factory=lambda: GameRules())

    # Active P2P trade proposal (None if no proposal pending)
    # Format: {"id": str, "proposer_id": str, "offer": {}, "want": {}, "rejected_by": []}
    trade_proposal: Optional[Dict] = None

    # Turn timer state (for AFK timeout)
    turn_timer_start: float = 0.0        # time.time() when current action started
    turn_timer_duration: float = 60.0    # timeout duration in seconds

    def current_player(self) -> Optional[Player]:
        if not self.players:
            return None
        return self.players[self.current_player_index]

    def player_by_id(self, pid: str) -> Optional[Player]:
        for p in self.players:
            if p.player_id == pid:
                return p
        return None

    def vertex_key(self, q: int, r: int, corner: int) -> str:
        return f"{q},{r},{corner}"

    def edge_key(self, q: int, r: int, side: int) -> str:
        return f"{q},{r},{side}"

    def to_dict(self, viewer_player_id: Optional[str] = None):
        players_data = []
        for p in self.players:
            # each player sees their own resources; others see only count
            hide = (viewer_player_id is not None and p.player_id != viewer_player_id)
            d = p.to_dict(hide_resources=hide)
            players_data.append(d)

        return {
            "room_id": self.room_id,
            "map": self.map_data.to_dict(),
            "players": players_data,
            "phase": self.phase.value,
            "turn_step": self.turn_step.value,
            "current_player_index": self.current_player_index,
            "current_player_id": self.current_player().player_id if self.current_player() else None,
            # Setup ordering (snake draft) for UI + rule clarity
            "setup_order": self.setup_order,
            "setup_step": self.setup_step,
            "robber": {"q": self.robber_q, "r": self.robber_r},
            "last_dice": self.last_dice,
            "winner_id": self.winner_id,
            "longest_road_holder": self.longest_road_holder,
            "longest_road_length": self.longest_road_length,
            "players_to_discard": self.players_to_discard,
            "robber_steal_targets": self.robber_steal_targets,
            "vertices": {k: v.to_dict() for k, v in self.vertices.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
            # Only include full deck for Redis persistence (viewer_player_id=None)
            **({"dev_card_deck": [c.to_dict() for c in self.dev_card_deck]} if viewer_player_id is None else {}),
            "dev_card_deck_count": len(self.dev_card_deck),
            "current_turn_number": self.current_turn_number,
            "largest_army_holder": self.largest_army_holder,
            "largest_army_size": self.largest_army_size,
            "road_building_remaining": self.road_building_remaining,
            "rules": self.rules.to_dict(),
            "trade_proposal": self.trade_proposal,
            "turn_timer_start": self.turn_timer_start,
            "turn_timer_duration": self.turn_timer_duration,
        }

    @staticmethod
    def from_dict(d: dict) -> "GameState":
        game = GameState(
            room_id=str(d.get("room_id") or d.get("roomId") or ""),
            map_data=MapData.from_dict(d.get("map") or {}),
            players=[Player.from_dict(p) for p in (d.get("players") or [])],
        )
        game.phase = GamePhase(d.get("phase") or "waiting")
        game.turn_step = TurnStep(d.get("turn_step") or "pre_roll")
        game.current_player_index = int(d.get("current_player_index") or 0)
        game.setup_order = list(d.get("setup_order") or [])
        game.setup_step = int(d.get("setup_step") or 0)
        robber = d.get("robber") or {}
        game.robber_q = int(robber.get("q") or 0)
        game.robber_r = int(robber.get("r") or 0)
        game.last_dice = d.get("last_dice") or None
        game.winner_id = d.get("winner_id") or None
        game.longest_road_holder = d.get("longest_road_holder") or None
        game.longest_road_length = int(d.get("longest_road_length") or 0)
        game.players_to_discard = list(d.get("players_to_discard") or [])
        game.robber_steal_targets = list(d.get("robber_steal_targets") or [])
        game.vertices = {k: PlacedPiece.from_dict(v) for k, v in (d.get("vertices") or {}).items()}
        game.edges = {k: PlacedPiece.from_dict(v) for k, v in (d.get("edges") or {}).items()}
        # Development cards
        game.dev_card_deck = [DevCard.from_dict(c) for c in (d.get("dev_card_deck") or [])]
        game.current_turn_number = int(d.get("current_turn_number") or 0)
        game.largest_army_holder = d.get("largest_army_holder") or None
        game.largest_army_size = int(d.get("largest_army_size") or 0)
        game.road_building_remaining = int(d.get("road_building_remaining") or 0)
        game.rules = GameRules.from_dict(d.get("rules") or {})
        game.trade_proposal = d.get("trade_proposal") or None
        game.turn_timer_start = float(d.get("turn_timer_start") or 0.0)
        game.turn_timer_duration = float(d.get("turn_timer_duration") or 60.0)
        return game
