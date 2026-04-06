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
    PRE_ROLL = "pre_roll"   # player must roll dice first
    POST_ROLL = "post_roll"  # player can build / trade / end turn


# ---------------------------------------------------------------------------
# Build costs
# ---------------------------------------------------------------------------

BUILD_COST: Dict[PieceType, Dict[Resource, int]] = {
    PieceType.ROAD: {Resource.WOOD: 1, Resource.BRICK: 1},
    PieceType.SETTLEMENT: {Resource.WOOD: 1, Resource.BRICK: 1, Resource.WHEAT: 1, Resource.SHEEP: 1},
    PieceType.CITY: {Resource.WHEAT: 2, Resource.ORE: 3},
}

# Victory points per piece
VP_TABLE: Dict[PieceType, int] = {
    PieceType.SETTLEMENT: 1,
    PieceType.CITY: 2,
    PieceType.ROAD: 0,
}

WINNING_VP = 10


# ---------------------------------------------------------------------------
# Map structures
# ---------------------------------------------------------------------------

@dataclass
class Port:
    # The vertex (q, r, direction) closest to the port — used to check eligibility
    q: int
    r: int
    resource: Optional[Resource]  # None = 3:1 generic port
    ratio: int = 3  # 2 for specific-resource ports, 3 for generic

    def to_dict(self):
        return {
            "q": self.q,
            "r": self.r,
            "resource": self.resource.value if self.resource else None,
            "ratio": self.ratio,
        }


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


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

@dataclass
class Player:
    player_id: str
    name: str
    color: str
    resources: Dict[Resource, int] = field(default_factory=lambda: {r: 0 for r in Resource})
    victory_points: int = 0
    # placement counts for rule checking
    settlements_placed: int = 0
    cities_placed: int = 0
    roads_placed: int = 0
    # initial setup tracking
    setup_settlements: List[VertexKey] = field(default_factory=list)

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
        }


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
            d = p.to_dict(hide_resources=False)  # send full state to all for simplicity
            players_data.append(d)

        return {
            "room_id": self.room_id,
            "map": self.map_data.to_dict(),
            "players": players_data,
            "phase": self.phase.value,
            "turn_step": self.turn_step.value,
            "current_player_id": self.current_player().player_id if self.current_player() else None,
            "robber": {"q": self.robber_q, "r": self.robber_r},
            "last_dice": self.last_dice,
            "winner_id": self.winner_id,
            "vertices": {k: v.to_dict() for k, v in self.vertices.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
        }
