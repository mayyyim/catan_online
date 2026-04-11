"""
Authentication endpoints: register, login, guest login, profile.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.db_models import User

router = APIRouter(tags=["auth"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=6)
    display_name: str = Field(min_length=1, max_length=32)


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    token: str
    elo_rating: int
    games_played: int
    games_won: int


class GuestResponse(BaseModel):
    user_id: str
    username: str
    display_name: str
    token: str
    is_guest: bool = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        is_guest=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        token=token,
        elo_rating=user.elo_rating,
        games_played=user.games_played,
        games_won=user.games_won,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_access_token(user.id, user.username)
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        token=token,
        elo_rating=user.elo_rating,
        games_played=user.games_played,
        games_won=user.games_won,
    )


@router.post("/guest", response_model=GuestResponse)
def guest_login(db: Session = Depends(get_db)):
    """Create a temporary guest account."""
    guest_id = str(uuid.uuid4())[:8]
    username = f"guest_{guest_id}"
    user = User(
        username=username,
        display_name=f"Guest {guest_id[:4].upper()}",
        is_guest=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return GuestResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        token=token,
    )


@router.get("/me", response_model=AuthResponse)
def get_me(user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        token="",
        elo_rating=user.elo_rating,
        games_played=user.games_played,
        games_won=user.games_won,
    )
