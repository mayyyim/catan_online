"""
WebSocket endpoint for real-time game communication.

Protocol:
  Client connects: WS /ws/{room_id}/{player_id}
  On connect: server sends room_update with current state
  Client sends JSON actions; server broadcasts updates.

All incoming messages must be JSON with a "type" field.
"""

import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.store import (
    get_room, get_player_in_room, ensure_game_state,
    connect_player, disconnect_player, broadcast, broadcast_game_state, send_to_player, save_game, load_game,
    delete_room, has_human_players, remove_player_from_room,
    start_turn_timer, cancel_turn_timer,
    start_disconnect_timer, cancel_disconnect_timer,
)
from app.game.engine import (
    ActionError,
    handle_start_game, handle_roll_dice, handle_build,
    handle_end_turn, handle_trade,
    handle_propose_trade, handle_accept_trade, handle_reject_trade, handle_cancel_trade,
    handle_discard, handle_place_robber, handle_steal,
    handle_buy_dev_card, handle_play_dev_card,
)
from app.bots import stop_bot
from app.maps.generator import generate_random_map
from app.maps.definitions import get_static_map
from app.game.models import GamePhase, GameRules

logger = logging.getLogger("catan.ws")


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
            "host_player_id": room.host_player_id,
            "players": players_data,
            "map": map_data,
            "state": state,
            "selected_map_id": getattr(room, "selected_map_id", "random"),
            "seed": getattr(room, "random_seed", None),
            "rules": getattr(room, "rules", {}),
        },
    }


def _game_state_msg(game, viewer_player_id=None):
    return {
        "type": "game_state",
        "data": game.to_dict(viewer_player_id),
    }


def _error_msg(message: str):
    return {"type": "error", "data": {"message": message}}


def _dice_msg(values, total, player_name=""):
    return {"type": "dice_result", "data": {"values": values, "total": total, "player_name": player_name}}


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

    # Cancel any pending bot takeover for this player (they reconnected).
    # Only stop a substitute bot if this is a human player reconnecting —
    # don't kill the bot's own task when the bot connects.
    cancel_disconnect_timer(player_id)
    if not (player and player.is_bot):
        stop_bot(player_id)

    # Ensure game state object exists (even in waiting phase)
    game = ensure_game_state(room)

    # Send initial state
    await send_to_player(room, player_id, _room_update_msg(room, game))
    # If game already started, also send full game state immediately
    if game and game.phase.value != "waiting":
        await send_to_player(room, player_id, _game_state_msg(game, viewer_player_id=player_id))

    # Notify others that this player connected
    await broadcast(room, _room_update_msg(room, game))

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

            # Refresh game from Redis to avoid stale in-memory state
            # (e.g. players added via HTTP while WS connection is alive).
            fresh = load_game(room_id)
            if fresh is None:
                fresh = ensure_game_state(room)
            room.game = fresh
            game = fresh

            await _dispatch(room, game, player_id, msg_type, msg)

    except WebSocketDisconnect:
        disconnect_player(room, player_id)
        # In waiting phase, remove non-host human players so they don't ghost the slot.
        # Keep the host (can reconnect) and bots (managed via HTTP, not WS lifecycle).
        if game is None or game.phase == GamePhase.WAITING:
            is_bot = player is not None and player.is_bot
            if player_id != room.host_player_id and not is_bot:
                remove_player_from_room(room.room_id, player_id)
        else:
            # During active game, start 30s bot takeover timer
            if game.phase in (GamePhase.PLAYING, GamePhase.SETUP_FORWARD, GamePhase.SETUP_BACKWARD):
                start_disconnect_timer(room.room_id, player_id)
        # If no human players remain, destroy the room silently
        if not has_human_players(room.room_id):
            cancel_turn_timer(room.room_id)
            delete_room(room.room_id)
            return
        # Otherwise notify remaining players
        await broadcast(room, _room_update_msg(room, game))


# ---------------------------------------------------------------------------
# Message dispatcher
# ---------------------------------------------------------------------------

def _try_save_game_result(game):
    """Persist finished game record to the database. Fire-and-forget."""
    if not game or game.phase != GamePhase.FINISHED:
        return
    try:
        from app.database import SessionLocal
        from app.game_records import save_game_result

        db = SessionLocal()
        try:
            save_game_result(db, game.to_dict())
        finally:
            db.close()
    except Exception as e:
        logger.error("Failed to save game result for room=%s: %s", game.room_id, e)


async def _maybe_restart_timer(room, game):
    """Restart the turn timer if the game is in playing phase."""
    if game and game.phase == GamePhase.PLAYING and not game.winner_id:
        await start_turn_timer(room.room_id)
    elif game and game.phase == GamePhase.FINISHED:
        cancel_turn_timer(room.room_id)


async def _dispatch(room, game, player_id: str, msg_type: str, msg: dict):
    try:
        if msg_type == "start_game":
            await _handle_start_game(room, game, player_id, msg)
            save_game(room.room_id, game)
            # Start timer when game transitions to playing phase after setup
            # (setup is handled by bots; timer starts when playing begins)
            await _maybe_restart_timer(room, game)

        elif msg_type == "select_map":
            # Host selects which map to use when starting.
            if player_id != room.host_player_id:
                raise ActionError("Only the host can select the map")
            map_id = msg.get("map_id") or msg.get("mapId") or "random"
            seed = msg.get("seed")
            room.selected_map_id = map_id
            room.random_seed = seed
            # Persist to Redis so selection survives WS reconnects
            from app.store import save_room_info
            save_room_info(room)
            await broadcast(room, _room_update_msg(room, game))

        elif msg_type == "chat":
            text = str(msg.get("text", ""))[:200]
            if not text.strip():
                return
            player = game.player_by_id(player_id) if game else None
            chat_msg = {
                "type": "chat",
                "data": {
                    "player_id": player_id,
                    "player_name": player.name if player else "?",
                    "player_color": player.color if player else "gray",
                    "text": text.strip(),
                },
            }
            await broadcast(room, chat_msg)

        elif msg_type == "roll_dice":
            result = handle_roll_dice(game, player_id)
            # Broadcast dice result then full game state
            player = game.player_by_id(player_id)
            await broadcast(room, _dice_msg(result["values"], result["total"], player.name if player else "?"))
            # Broadcast production details
            if result.get("production"):
                await broadcast(room, {
                    "type": "resource_production",
                    "data": {"production": result["production"]},
                })
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "build":
            piece = msg.get("piece")
            position = msg.get("position", {})
            handle_build(game, player_id, piece, position)
            # Broadcast build event for game log
            player = game.player_by_id(player_id)
            build_event = {
                "type": "build_completed",
                "data": {
                    "player_id": player_id,
                    "player_name": player.name if player else "?",
                    "piece": piece,
                },
            }
            await broadcast(room, build_event)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "trade":
            offer = msg.get("offer", {})
            want = msg.get("want", {})
            handle_trade(game, player_id, offer, want)
            # Notify all players about the trade
            player = game.player_by_id(player_id)
            trade_msg = {
                "type": "trade_completed",
                "data": {
                    "player_id": player_id,
                    "player_name": player.name if player else "?",
                    "offer": offer,
                    "want": want,
                },
            }
            await broadcast(room, trade_msg)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "discard":
            resources = msg.get("resources", {})
            handle_discard(game, player_id, resources)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "place_robber":
            q = int(msg.get("q", 0))
            r = int(msg.get("r", 0))
            handle_place_robber(game, player_id, q, r)
            player = game.player_by_id(player_id)
            await broadcast(room, {"type": "robber_moved", "data": {"player_name": player.name if player else "?", "q": q, "r": r}})
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "steal":
            target_id = msg.get("target_id", "")
            result = handle_steal(game, player_id, target_id)
            player = game.player_by_id(player_id)
            target = game.player_by_id(target_id)
            await broadcast(room, {
                "type": "resource_stolen",
                "data": {
                    "player_name": player.name if player else "?",
                    "target_name": target.name if target else "?",
                    "resource": result.get("stolen"),
                },
            })
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "propose_trade":
            offer = msg.get("offer", {})
            want = msg.get("want", {})
            proposal = handle_propose_trade(game, player_id, offer, want)
            proposer = game.player_by_id(player_id)
            trade_proposal_event = {
                "type": "trade_proposal",
                "data": {
                    "id": proposal["id"],
                    "proposer_id": player_id,
                    "proposer_name": proposer.name if proposer else "?",
                    "offer": proposal["offer"],
                    "want": proposal["want"],
                },
            }
            await broadcast(room, trade_proposal_event)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "accept_trade":
            proposal_id = msg.get("proposal_id", "")
            result = handle_accept_trade(game, player_id, proposal_id)
            proposer = game.player_by_id(result["proposer_id"])
            accepter = game.player_by_id(result["accepter_id"])
            trade_completed_event = {
                "type": "trade_completed",
                "data": {
                    "player_id": result["accepter_id"],
                    "player_name": accepter.name if accepter else "?",
                    "with_player_name": proposer.name if proposer else "?",
                    "offer": result["offer"],
                    "want": result["want"],
                },
            }
            await broadcast(room, trade_completed_event)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "reject_trade":
            proposal_id = msg.get("proposal_id", "")
            result = handle_reject_trade(game, player_id, proposal_id)
            if result["auto_cancelled"]:
                await broadcast(room, {"type": "trade_cancelled", "data": {"reason": "all_rejected"}})
            else:
                # Broadcast updated proposal with rejection info
                player = game.player_by_id(player_id)
                await broadcast(room, {
                    "type": "trade_rejected",
                    "data": {
                        "player_id": player_id,
                        "player_name": player.name if player else "?",
                        "proposal_id": proposal_id,
                    },
                })
            save_game(room.room_id, game)

        elif msg_type == "cancel_trade":
            handle_cancel_trade(game, player_id)
            await broadcast(room, {"type": "trade_cancelled", "data": {"reason": "proposer_cancelled"}})
            save_game(room.room_id, game)

        elif msg_type == "end_turn":
            handle_end_turn(game, player_id)
            if game.phase == GamePhase.FINISHED:
                _try_save_game_result(game)
            next_player = game.current_player()
            await broadcast(room, {"type": "turn_start", "data": {"player_name": next_player.name if next_player else "?"}})
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "buy_dev_card":
            result = handle_buy_dev_card(game, player_id)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

        elif msg_type == "set_rules":
            if player_id != room.host_player_id:
                raise ActionError("Only the host can set rules")
            if game and game.phase != GamePhase.WAITING:
                raise ActionError("Cannot change rules after game started")
            rules_data = msg.get("rules", {})
            room.rules = rules_data
            from app.store import save_room_info as _save_room
            _save_room(room)
            await broadcast(room, _room_update_msg(room, game))

        elif msg_type == "play_dev_card":
            card_type = msg.get("card_type", "")
            params = msg.get("params") or {}
            result = handle_play_dev_card(game, player_id, card_type, params)
            # Broadcast event for game log display
            player = game.player_by_id(player_id)
            dev_event = {
                "type": "dev_card_played",
                "data": {
                    "player_id": player_id,
                    "player_name": player.name if player else "?",
                    "card_type": card_type,
                },
            }
            await broadcast(room, dev_event)
            await broadcast_game_state(room, game)
            save_game(room.room_id, game)
            await _maybe_restart_timer(room, game)

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
    game.rules = GameRules.from_dict(getattr(room, 'rules', {}) or {})
    await broadcast_game_state(room, game)
