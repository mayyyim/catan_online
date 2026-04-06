"""
HTTP API for room management.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.store import create_room, join_room, get_room, get_room_players


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
    state: str
    player_count: int
    players: list


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
        state=room.state_label(),
        player_count=len(players),
        players=players_data,
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
