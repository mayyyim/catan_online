"""
In-memory store for rooms and WebSocket connections.
Designed for 100 concurrent users — no external DB required.
"""

import random
import string
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import WebSocket

from app.game.models import GameState, Player, GamePhase
from app.maps.generator import generate_random_map


# ---------------------------------------------------------------------------
# Room data
# ---------------------------------------------------------------------------

@dataclass
class RoomInfo:
    room_id: str
    invite_code: str
    host_player_id: str
    max_players: int = 4
    # WebSocket connections: player_id -> WebSocket
    connections: Dict[str, WebSocket] = field(default_factory=dict)
    # Game state — None until game starts
    game: Optional[GameState] = None

    def player_count(self) -> int:
        return len(self.connections)

    def is_full(self) -> bool:
        return self.player_count() >= self.max_players

    def state_label(self) -> str:
        if self.game is None:
            return "waiting"
        return self.game.phase.value


# ---------------------------------------------------------------------------
# Global store (module-level singletons)
# ---------------------------------------------------------------------------

# room_id -> RoomInfo
_rooms: Dict[str, RoomInfo] = {}

# invite_code -> room_id
_invite_index: Dict[str, str] = {}

# room_id -> list of Player (persisted before game starts)
_room_players: Dict[str, List[Player]] = {}


def _generate_invite_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _generate_room_id() -> str:
    return str(uuid.uuid4())[:8]


def create_room(host_player_name: str) -> RoomInfo:
    room_id = _generate_room_id()
    invite_code = _generate_invite_code()
    # Avoid collisions
    while invite_code in _invite_index:
        invite_code = _generate_invite_code()

    host_player_id = str(uuid.uuid4())[:8]
    colors = ["red", "blue", "green", "orange"]

    room = RoomInfo(room_id=room_id, invite_code=invite_code, host_player_id=host_player_id)
    _rooms[room_id] = room
    _invite_index[invite_code] = room_id

    # Pre-register host player
    host = Player(
        player_id=host_player_id,
        name=host_player_name,
        color=colors[0],
    )
    _room_players[room_id] = [host]

    return room


def join_room(invite_code: str, player_name: str) -> Optional[tuple]:
    """Return (room, player) or None if room not found / full / started."""
    room_id = _invite_index.get(invite_code)
    if not room_id:
        return None

    room = _rooms.get(room_id)
    if not room:
        return None

    players = _room_players.get(room_id, [])

    if len(players) >= room.max_players:
        return None

    if room.game is not None and room.game.phase != GamePhase.WAITING:
        return None

    colors = ["red", "blue", "green", "orange"]
    used_colors = {p.color for p in players}
    available = [c for c in colors if c not in used_colors]
    color = available[0] if available else "purple"

    player = Player(
        player_id=str(uuid.uuid4())[:8],
        name=player_name,
        color=color,
    )
    players.append(player)
    _room_players[room_id] = players
    return room, player


def get_room(room_id: str) -> Optional[RoomInfo]:
    return _rooms.get(room_id)


def get_room_players(room_id: str) -> List[Player]:
    return _room_players.get(room_id, [])


def get_player_in_room(room_id: str, player_id: str) -> Optional[Player]:
    for p in get_room_players(room_id):
        if p.player_id == player_id:
            return p
    return None


def ensure_game_state(room: RoomInfo) -> GameState:
    """Initialize GameState for the room if not already done."""
    if room.game is None:
        players = _room_players.get(room.room_id, [])
        room.game = GameState(
            room_id=room.room_id,
            map_data=generate_random_map(),  # placeholder until start_game sets real map
            players=players,
        )
    return room.game


# ---------------------------------------------------------------------------
# WebSocket connection management
# ---------------------------------------------------------------------------

async def connect_player(room: RoomInfo, player_id: str, ws: WebSocket):
    await ws.accept()
    room.connections[player_id] = ws


def disconnect_player(room: RoomInfo, player_id: str):
    room.connections.pop(player_id, None)


async def broadcast(room: RoomInfo, message: dict):
    """Send message to all connected players in the room."""
    disconnected = []
    for pid, ws in list(room.connections.items()):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(pid)
    for pid in disconnected:
        room.connections.pop(pid, None)


async def send_to_player(room: RoomInfo, player_id: str, message: dict):
    ws = room.connections.get(player_id)
    if ws:
        try:
            await ws.send_json(message)
        except Exception:
            room.connections.pop(player_id, None)
