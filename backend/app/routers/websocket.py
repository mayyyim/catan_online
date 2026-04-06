"""
WebSocket endpoint for real-time game communication.

Protocol:
  Client connects: WS /ws/{room_id}/{player_id}
  On connect: server sends room_update with current state
  Client sends JSON actions; server broadcasts updates.

All incoming messages must be JSON with a "type" field.
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.store import (
    get_room, get_player_in_room, ensure_game_state,
    connect_player, disconnect_player, broadcast, send_to_player,
)
from app.game.engine import (
    ActionError,
    handle_start_game, handle_roll_dice, handle_build,
    handle_end_turn, handle_trade,
)
from app.maps.generator import generate_random_map
from app.maps.definitions import get_static_map


router = APIRouter(tags=["websocket"])


def _room_update_msg(room, game=None):
    """Build a room_update message with player list and current state."""
    from app.store import get_room_players
    players = get_room_players(room.room_id)
    players_data = [
        {
            "player_id": p.player_id,
            "name": p.name,
            "color": p.color,
            "connected": p.player_id in room.connections,
        }
        for p in players
    ]
    state = "waiting"
    map_data = None
    if game:
        state = game.phase.value
        map_data = game.map_data.to_dict()

    return {
        "type": "room_update",
        "data": {
            "players": players_data,
            "map": map_data,
            "state": state,
            "selected_map_id": getattr(room, "selected_map_id", "random"),
            "seed": getattr(room, "random_seed", None),
        },
    }


def _game_state_msg(game, viewer_player_id=None):
    return {
        "type": "game_state",
        "data": game.to_dict(viewer_player_id),
    }


def _error_msg(message: str):
    return {"type": "error", "data": {"message": message}}


def _dice_msg(values, total):
    return {"type": "dice_result", "data": {"values": values, "total": total}}


# ---------------------------------------------------------------------------
# WebSocket handler
# ---------------------------------------------------------------------------

@router.websocket("/ws/{room_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, player_id: str):
    # Validate room and player
    room = get_room(room_id)
    if not room:
        await websocket.close(code=4004, reason="Room not found")
        return

    player = get_player_in_room(room_id, player_id)
    if not player:
        await websocket.close(code=4003, reason="Player not in room")
        return

    # Accept connection
    await connect_player(room, player_id, websocket)

    # Ensure game state object exists (even in waiting phase)
    game = ensure_game_state(room)

    # Send initial state
    await send_to_player(room, player_id, _room_update_msg(room, game))

    # Notify others that this player connected
    await broadcast(room, {
        "type": "room_update",
        "data": {
            "players": [
                {
                    "player_id": p.player_id,
                    "name": p.name,
                    "color": p.color,
                    "connected": p.player_id in room.connections,
                }
                for p in game.players
            ],
            "map": None,
            "state": room.state_label(),
        },
    })

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await send_to_player(room, player_id, _error_msg("Invalid JSON"))
                continue

            msg_type = msg.get("type")
            if not msg_type:
                await send_to_player(room, player_id, _error_msg("Missing 'type' field"))
                continue

            await _dispatch(room, game, player_id, msg_type, msg)

    except WebSocketDisconnect:
        disconnect_player(room, player_id)
        # Notify remaining players
        await broadcast(room, _room_update_msg(room, game))


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------

async def _dispatch(room, game, player_id: str, msg_type: str, msg: dict):
    try:
        if msg_type == "start_game":
            await _handle_start_game(room, game, player_id, msg)

        elif msg_type == "select_map":
            # Host selects which map to use when starting.
            if player_id != room.host_player_id:
                raise ActionError("Only the host can select the map")
            map_id = msg.get("map_id") or msg.get("mapId") or "random"
            seed = msg.get("seed")
            room.selected_map_id = map_id
            room.random_seed = seed
            await broadcast(room, _room_update_msg(room, game))

        elif msg_type == "roll_dice":
            result = handle_roll_dice(game, player_id)
            # Broadcast dice result then full game state
            await broadcast(room, _dice_msg(result["values"], result["total"]))
            await broadcast(room, _game_state_msg(game))

        elif msg_type == "build":
            piece = msg.get("piece")
            position = msg.get("position", {})
            handle_build(game, player_id, piece, position)
            await broadcast(room, _game_state_msg(game))

        elif msg_type == "trade":
            offer = msg.get("offer", {})
            want = msg.get("want", {})
            handle_trade(game, player_id, offer, want)
            await broadcast(room, _game_state_msg(game))

        elif msg_type == "end_turn":
            handle_end_turn(game, player_id)
            await broadcast(room, _game_state_msg(game))

        else:
            await send_to_player(room, player_id, _error_msg(f"Unknown message type: {msg_type}"))

    except ActionError as e:
        await send_to_player(room, player_id, _error_msg(str(e)))
    except Exception as e:
        # Catch-all to prevent crashing the WS loop
        await send_to_player(room, player_id, _error_msg(f"Server error: {str(e)}"))


async def _handle_start_game(room, game, player_id: str, msg: dict):
    """Load map and start the game."""
    if player_id != room.host_player_id:
        raise ActionError("Only the host can start the game")

    map_id = msg.get("map_id") or msg.get("mapId") or getattr(room, "selected_map_id", "random")

    if map_id == "random" or map_id.startswith("random"):
        seed = msg.get("seed") or getattr(room, "random_seed", None)  # optional seed for reproducibility
        map_data = generate_random_map(seed=seed)
    else:
        try:
            map_data = get_static_map(map_id)
        except ValueError as e:
            raise ActionError(str(e))

    handle_start_game(game, map_data, player_id)
    await broadcast(room, _game_state_msg(game))
