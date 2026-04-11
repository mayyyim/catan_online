"""
HTTP API for room management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.store import create_room, join_room, get_room, get_room_players, add_bot_player, ensure_game_state, broadcast, remove_player_from_room, get_player_in_room
from app.bots import start_bot, stop_bot
from app.routers.websocket import _room_update_msg


router = APIRouter(prefix="/rooms", tags=["rooms"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateRoomRequest(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=32, description="Host player display name")
    max_players: int = Field(default=4, ge=2, le=4)


class CreateRoomResponse(BaseModel):
    room_id: str
    invite_code: str
    host_player_id: str


class JoinRoomRequest(BaseModel):
    player_name: str = Field(..., min_length=1, max_length=32)


class JoinRoomResponse(BaseModel):
    room_id: str
    player_id: str
    player_name: str
    color: str


class RoomStatusResponse(BaseModel):
    room_id: str
    invite_code: str
    host_player_id: str
    state: str
    player_count: int
    players: list
    selected_map_id: str = "random"


class AddBotRequest(BaseModel):
    name: str = Field(default="Bot", min_length=1, max_length=32)


class AddBotResponse(BaseModel):
    room_id: str
    player_id: str
    player_name: str
    color: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=CreateRoomResponse, status_code=201)
async def create_room_endpoint(body: CreateRoomRequest):
    """Create a new room. Returns room_id and invite_code for sharing."""
    room = create_room(body.host_name)
    room.max_players = body.max_players

    # Get the host player_id
    from app.store import get_room_players
    players = get_room_players(room.room_id)
    host_player_id = players[0].player_id if players else room.host_player_id

    return CreateRoomResponse(
        room_id=room.room_id,
        invite_code=room.invite_code,
        host_player_id=host_player_id,
    )


@router.get("/{room_id}", response_model=RoomStatusResponse)
async def get_room_status(room_id: str):
    """Get room state: players, status."""
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    players = get_room_players(room_id)
    players_data = [
        {
            "player_id": p.player_id,
            "name": p.name,
            "color": p.color,
            "connected": p.player_id in room.connections,
        }
        for p in players
    ]

    return RoomStatusResponse(
        room_id=room.room_id,
        invite_code=room.invite_code,
        host_player_id=room.host_player_id,
        state=room.state_label(),
        player_count=len(players),
        players=players_data,
        selected_map_id=room.selected_map_id,
    )


@router.post("/{invite_code}/join", response_model=JoinRoomResponse, status_code=200)
async def join_room_endpoint(invite_code: str, body: JoinRoomRequest):
    """Join room via invite code. Returns player_id for subsequent WebSocket auth."""
    result = join_room(invite_code, body.player_name)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Room not found, is full, or game already started",
        )

    room, player = result
    return JoinRoomResponse(
        room_id=room.room_id,
        player_id=player.player_id,
        player_name=player.name,
        color=player.color,
    )


@router.post("/{room_id}/bots", response_model=AddBotResponse, status_code=201)
async def add_bot_endpoint(room_id: str, body: AddBotRequest):
    """
    Add a bot player to a waiting room and start an in-process bot client that connects via WS.
    """
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    player = add_bot_player(room_id, name=body.name)
    if not player:
        raise HTTPException(status_code=400, detail="Room is full or game already started")

    # Ensure game state exists so room_update uses consistent players list
    game = ensure_game_state(room)

    # Start bot loop (connects back to this server)
    start_bot("http://localhost:8080", room_id, player.player_id)

    # Notify connected clients
    await broadcast(room, _room_update_msg(room, game))

    return AddBotResponse(
        room_id=room_id,
        player_id=player.player_id,
        player_name=player.name,
        color=player.color,
    )


@router.delete("/{room_id}/players/{player_id}", status_code=200)
async def remove_player_endpoint(room_id: str, player_id: str):
    """Remove a bot player from a waiting room. Only works before game starts."""
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    player = get_player_in_room(room_id, player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found in room")

    if not player.is_bot:
        raise HTTPException(status_code=400, detail="Can only remove bot players")

    if room.game and room.game.phase.value != "waiting":
        raise HTTPException(status_code=400, detail="Cannot remove players after game started")

    # Stop bot task
    stop_bot(player_id)

    # Remove from room
    remove_player_from_room(room_id, player_id)

    # Sync game state if exists
    game = ensure_game_state(room)
    if game:
        game.players = get_room_players(room_id)
        from app.store import save_game
        save_game(room_id, game)

    # Notify connected clients
    await broadcast(room, _room_update_msg(room, game))

    return {"status": "removed", "player_id": player_id}
