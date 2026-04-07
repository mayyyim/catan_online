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
            "setup_settlements": [[vk[0], vk[1], vk[2]] for vk in self.setup_settlements],
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

        p = Player(
            player_id=str(d.get("player_id") or d.get("playerId") or ""),
            name=str(d.get("name") or ""),
            color=str(d.get("color") or "red"),
            resources=resources,
            victory_points=int(d.get("victory_points") or 0),
            settlements_placed=int(d.get("settlements_placed") or 0),
            cities_placed=int(d.get("cities_placed") or 0),
            roads_placed=int(d.get("roads_placed") or 0),
        )
        p.setup_settlements = setup_settlements
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
            # Setup ordering (snake draft) for UI + rule clarity
            "setup_order": self.setup_order,
            "setup_step": self.setup_step,
            "robber": {"q": self.robber_q, "r": self.robber_r},
            "last_dice": self.last_dice,
            "winner_id": self.winner_id,
            "vertices": {k: v.to_dict() for k, v in self.vertices.items()},
            "edges": {k: v.to_dict() for k, v in self.edges.items()},
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
        game.vertices = {k: PlacedPiece.from_dict(v) for k, v in (d.get("vertices") or {}).items()}
        game.edges = {k: PlacedPiece.from_dict(v) for k, v in (d.get("edges") or {}).items()}
        return game
