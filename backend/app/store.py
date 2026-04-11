"""
Redis-backed store for rooms + game state, with in-memory WS connections.

Why:
- Docker redeploys restart the backend container, which would otherwise wipe
  in-memory rooms and cause WS 403 rejections.
- Redis persists room/player/game state across restarts.
"""

import asyncio
import json
import logging
import os
import random
import string
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import WebSocket
from redis import Redis

from app.game.models import GameState, Player, GamePhase, TurnStep, Resource, TileType
from app.maps.generator import generate_random_map

logger = logging.getLogger("catan.timer")


# ---------------------------------------------------------------------------
# Room data
# ---------------------------------------------------------------------------

@dataclass
class RoomInfo:
    room_id: str
    invite_code: str
    host_player_id: str
    max_players: int = 4
    selected_map_id: str = "random"
    random_seed: Optional[str] = None
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
# Redis + in-memory WS connections
# ---------------------------------------------------------------------------

_redis: Optional[Redis] = None

# room_id -> {player_id: WebSocket}
_connections: Dict[str, Dict[str, WebSocket]] = {}

# Persist keys for 24h after last update to avoid unbounded growth
ROOM_TTL_SECONDS = 60 * 60 * 24


def _r() -> Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis = Redis.from_url(url, decode_responses=True)
    return _redis


def _k_room(room_id: str) -> str:
    return f"room:{room_id}:info"


def _k_players(room_id: str) -> str:
    return f"room:{room_id}:players"


def _k_game(room_id: str) -> str:
    return f"room:{room_id}:game"


def _k_invite(invite_code: str) -> str:
    return f"invite:{invite_code}"


def _touch(room_id: str):
    r = _r()
    for k in (_k_room(room_id), _k_players(room_id), _k_game(room_id)):
        # keep TTL updated if key exists
        if r.exists(k):
            r.expire(k, ROOM_TTL_SECONDS)


def _generate_invite_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _generate_room_id() -> str:
    return str(uuid.uuid4())[:8]


def create_room(host_player_name: str) -> RoomInfo:
    room_id = _generate_room_id()
    invite_code = _generate_invite_code()
    # Avoid collisions
    r = _r()
    while r.exists(_k_invite(invite_code)):
        invite_code = _generate_invite_code()

    host_player_id = str(uuid.uuid4())[:8]
    colors = ["red", "blue", "green", "orange"]

    room = RoomInfo(room_id=room_id, invite_code=invite_code, host_player_id=host_player_id)

    # Pre-register host player
    host = Player(
        player_id=host_player_id,
        name=host_player_name,
        color=colors[0],
    )

    r.set(_k_invite(invite_code), room_id, ex=ROOM_TTL_SECONDS)
    r.set(
        _k_room(room_id),
        json.dumps(
            {
                "room_id": room_id,
                "invite_code": invite_code,
                "host_player_id": host_player_id,
                "max_players": room.max_players,
                "selected_map_id": room.selected_map_id,
                "random_seed": room.random_seed,
            }
        ),
        ex=ROOM_TTL_SECONDS,
    )
    r.set(_k_players(room_id), json.dumps([host.to_dict(hide_resources=False)]), ex=ROOM_TTL_SECONDS)

    return room


def join_room(invite_code: str, player_name: str) -> Optional[tuple]:
    """Return (room, player) or None if room not found / full / started."""
    r = _r()
    room_id = r.get(_k_invite(invite_code))
    if not room_id:
        return None

    room = get_room(room_id)
    if not room:
        return None

    players = get_room_players(room_id)

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
    r.set(_k_players(room_id), json.dumps([p.to_dict(hide_resources=False) for p in players]), ex=ROOM_TTL_SECONDS)

    # Keep persisted game players in sync if game exists
    if room.game is not None:
        room.game.players = players
        save_game(room_id, room.game)

    _touch(room_id)
    return room, player


def save_room_info(room: RoomInfo):
    """Persist room metadata (selected map, seed, etc.) to Redis."""
    r = _r()
    r.set(
        _k_room(room.room_id),
        json.dumps({
            "room_id": room.room_id,
            "invite_code": room.invite_code,
            "host_player_id": room.host_player_id,
            "max_players": room.max_players,
            "selected_map_id": room.selected_map_id,
            "random_seed": room.random_seed,
        }),
        ex=ROOM_TTL_SECONDS,
    )
    _touch(room.room_id)


def get_room(room_id: str) -> Optional[RoomInfo]:
    r = _r()
    raw = r.get(_k_room(room_id))
    if not raw:
        return None
    d = json.loads(raw)
    room = RoomInfo(
        room_id=d["room_id"],
        invite_code=d["invite_code"],
        host_player_id=d["host_player_id"],
        max_players=int(d.get("max_players", 4)),
        selected_map_id=d.get("selected_map_id", "random"),
        random_seed=d.get("random_seed", None),
    )
    room.connections = _connections.setdefault(room_id, {})
    room.game = load_game(room_id)
    return room


def get_room_players(room_id: str) -> List[Player]:
    r = _r()
    raw = r.get(_k_players(room_id))
    if not raw:
        return []
    arr = json.loads(raw)
    return [Player.from_dict(p) for p in arr]


def get_player_in_room(room_id: str, player_id: str) -> Optional[Player]:
    for p in get_room_players(room_id):
        if p.player_id == player_id:
            return p
    return None


def ensure_game_state(room: RoomInfo) -> GameState:
    """Initialize GameState for the room if not already done."""
    if room.game is None:
        players = get_room_players(room.room_id)
        room.game = GameState(
            room_id=room.room_id,
            map_data=generate_random_map(),  # placeholder until start_game sets real map
            players=players,
        )
        save_game(room.room_id, room.game)
    return room.game


def save_game(room_id: str, game: GameState):
    r = _r()
    r.set(_k_game(room_id), json.dumps(game.to_dict()), ex=ROOM_TTL_SECONDS)
    _touch(room_id)


def load_game(room_id: str) -> Optional[GameState]:
    r = _r()
    raw = r.get(_k_game(room_id))
    if not raw:
        return None
    try:
        return GameState.from_dict(json.loads(raw))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Bot / programmatic players
# ---------------------------------------------------------------------------

def add_bot_player(room_id: str, name: str = "Bot") -> Optional[Player]:
    """
    Add a new player entry to an existing room without using invite codes.
    Returns the created Player, or None if room not found / full / started.
    """
    room = get_room(room_id)
    if not room:
        return None

    players = get_room_players(room_id)
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
        name=name,
        color=color,
        is_bot=True,
    )
    players.append(player)
    r = _r()
    r.set(_k_players(room_id), json.dumps([p.to_dict(hide_resources=False) for p in players]), ex=ROOM_TTL_SECONDS)

    # If a GameState object already exists (created by WS connect), keep it in sync.
    if room.game is not None:
        room.game.players = players
        save_game(room_id, room.game)

    _touch(room_id)
    return player


# ---------------------------------------------------------------------------
# Room lifecycle
# ---------------------------------------------------------------------------

def delete_room(room_id: str):
    """Remove all Redis keys for a room (called when no human players remain)."""
    r = _r()
    room = get_room(room_id)
    if room:
        # Remove invite code reverse lookup
        invite_key = _k_invite(room.invite_code)
        r.delete(invite_key)
    r.delete(_k_room(room_id))
    r.delete(_k_players(room_id))
    r.delete(_k_game(room_id))


def has_human_players(room_id: str) -> bool:
    """Return True if any non-bot player is registered in the room."""
    players = get_room_players(room_id)
    return any(not p.is_bot for p in players)


def remove_player_from_room(room_id: str, player_id: str):
    """Remove a player from the Redis players list (used on disconnect in waiting phase)."""
    r = _r()
    players = get_room_players(room_id)
    players = [p for p in players if p.player_id != player_id]
    r.set(_k_players(room_id), json.dumps([p.to_dict(hide_resources=False) for p in players]), ex=ROOM_TTL_SECONDS)
    _touch(room_id)


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


async def broadcast_game_state(room: RoomInfo, game):
    """Send personalized game_state to each player (hides opponents' resources and deck)."""
    disconnected = []
    for pid, ws in list(room.connections.items()):
        try:
            msg = {"type": "game_state", "data": game.to_dict(viewer_player_id=pid)}
            await ws.send_json(msg)
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


# ---------------------------------------------------------------------------
# Turn timer (AFK timeout)
# ---------------------------------------------------------------------------

_turn_timers: Dict[str, asyncio.Task] = {}  # room_id -> timer task

TURN_TIMEOUT = 60.0  # seconds


async def start_turn_timer(room_id: str, timeout: float = TURN_TIMEOUT):
    """Start/restart the turn timer for a room."""
    cancel_turn_timer(room_id)

    # Stamp the game state with timer info
    game = load_game(room_id)
    if game:
        game.turn_timer_start = time.time()
        game.turn_timer_duration = timeout
        save_game(room_id, game)

    async def _timer():
        try:
            await asyncio.sleep(timeout)
            await _auto_act(room_id)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Turn timer error for room {room_id}: {e}")

    _turn_timers[room_id] = asyncio.create_task(_timer())


def cancel_turn_timer(room_id: str):
    """Cancel the turn timer for a room."""
    old = _turn_timers.pop(room_id, None)
    if old and not old.done():
        old.cancel()


async def _auto_act(room_id: str):
    """Execute the default action for the current player when they time out."""
    from app.game.engine import (
        handle_roll_dice, handle_end_turn, handle_discard,
        handle_place_robber, handle_steal, move_robber_random,
        recalculate_vp, check_winner,
    )

    room = get_room(room_id)
    if not room:
        return
    game = room.game
    if not game:
        return
    if game.phase != GamePhase.PLAYING:
        return
    if game.winner_id:
        return

    player = game.current_player()
    if not player:
        return

    player_id = player.player_id
    step = game.turn_step

    try:
        if step == TurnStep.PRE_ROLL:
            # Auto roll dice
            handle_roll_dice(game, player_id)

        elif step == TurnStep.ROBBER_DISCARD:
            # Auto discard for ALL players who still need to discard
            for pid in list(game.players_to_discard):
                p = game.player_by_id(pid)
                if not p:
                    continue
                hand_size = sum(p.resources.values())
                required = hand_size // 2
                if required <= 0:
                    game.players_to_discard.remove(pid)
                    continue
                # Discard largest stacks first
                sorted_res = sorted(
                    p.resources.items(), key=lambda x: -x[1]
                )
                remaining = required
                discard_map: Dict[Resource, int] = {}
                for res, amt in sorted_res:
                    give = min(amt, remaining)
                    if give > 0:
                        discard_map[res] = give
                        remaining -= give
                    if remaining <= 0:
                        break
                # Apply discard
                for res, amt in discard_map.items():
                    p.resources[res] -= amt
                game.players_to_discard.remove(pid)

            # After all discards, advance to robber placement
            if not game.players_to_discard:
                game.turn_step = TurnStep.ROBBER_PLACE

        elif step == TurnStep.ROBBER_PLACE:
            # Move robber to random land tile
            move_robber_random(game)
            # Check for steal targets at new position
            from app.game.board import vertices_of_tile as _vot
            steal_targets: set = set()
            for vk in _vot(game.robber_q, game.robber_r):
                vkey = f"{vk[0]},{vk[1]},{vk[2]}"
                piece = game.vertices.get(vkey)
                if piece and piece.player_id != player_id:
                    steal_targets.add(piece.player_id)
            game.robber_steal_targets = list(steal_targets)
            if game.robber_steal_targets:
                game.turn_step = TurnStep.ROBBER_STEAL
            else:
                game.turn_step = TurnStep.POST_ROLL

        elif step == TurnStep.ROBBER_STEAL:
            # Steal from random target or skip
            targets = game.robber_steal_targets
            if targets:
                target_id = random.choice(targets)
                target = game.player_by_id(target_id)
                if target:
                    available = [
                        res for res, amt in target.resources.items()
                        for _ in range(amt)
                    ]
                    if available:
                        stolen = random.choice(available)
                        target.resources[stolen] -= 1
                        player.add_resource(stolen, 1)
            game.robber_steal_targets = []
            game.turn_step = TurnStep.POST_ROLL

        elif step == TurnStep.POST_ROLL:
            # Auto end turn
            handle_end_turn(game, player_id)

        elif step == TurnStep.ROAD_BUILDING:
            # Skip road building, return to post_roll and end turn
            game.road_building_remaining = 0
            game.turn_step = TurnStep.POST_ROLL
            handle_end_turn(game, player_id)

        elif step == TurnStep.YEAR_OF_PLENTY:
            # Skip year of plenty
            game.turn_step = TurnStep.POST_ROLL

        elif step == TurnStep.MONOPOLY:
            # Skip monopoly
            game.turn_step = TurnStep.POST_ROLL

        else:
            return  # Unknown step, do nothing

    except Exception as e:
        logger.error(f"Auto-act error room={room_id} step={step}: {e}")
        return

    # Save and broadcast
    save_game(room_id, game)
    await broadcast_game_state(room, game)

    # Start new timer if game is still in playing phase
    if game.phase == GamePhase.PLAYING and not game.winner_id:
        await start_turn_timer(room_id)


# ---------------------------------------------------------------------------
# Disconnect bot takeover (30s grace period)
# ---------------------------------------------------------------------------

_disconnect_timers: Dict[str, asyncio.Task] = {}  # player_id -> delayed bot task


def start_disconnect_timer(room_id: str, player_id: str, timeout: float = 30.0):
    """After a player disconnects, start a 30s timer to replace them with a bot."""
    cancel_disconnect_timer(player_id)

    async def _takeover():
        try:
            await asyncio.sleep(timeout)
            # Check if player reconnected
            conns = _connections.get(room_id, {})
            if player_id in conns:
                return  # Player reconnected
            # Check game is still active
            game = load_game(room_id)
            if not game or game.phase not in (GamePhase.PLAYING, GamePhase.SETUP_FORWARD, GamePhase.SETUP_BACKWARD):
                return
            # Start bot for this player
            from app.bots import start_bot
            server_base = os.getenv("SERVER_BASE_URL", "http://localhost:8000")
            start_bot(server_base, room_id, player_id)
            logger.info(f"Bot takeover for disconnected player {player_id} in room {room_id}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Disconnect timer error player={player_id}: {e}")

    _disconnect_timers[player_id] = asyncio.create_task(_takeover())


def cancel_disconnect_timer(player_id: str):
    """Cancel the disconnect bot takeover timer (e.g. on reconnect)."""
    old = _disconnect_timers.pop(player_id, None)
    if old and not old.done():
        old.cancel()
