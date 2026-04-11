"""
SQLAlchemy ORM models for persistent game data.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)

from app.database import Base


def _short_uuid() -> str:
    return str(uuid.uuid4())[:12]


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_short_uuid)
    username = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  # None for guest accounts
    is_guest = Column(Boolean, default=False)
    display_name = Column(String(32), nullable=False)
    elo_rating = Column(Integer, default=1000)
    games_played = Column(Integer, default=0)
    games_won = Column(Integer, default=0)
    total_vp = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)


class GameRecord(Base):
    __tablename__ = "game_records"

    id = Column(String, primary_key=True, default=_short_uuid)
    room_id = Column(String, nullable=False)
    map_id = Column(String, nullable=False)
    winner_id = Column(String, ForeignKey("users.id"), nullable=True)
    player_count = Column(Integer, nullable=False)
    players_data = Column(JSON, nullable=False)  # [{user_id, name, vp, color, is_bot}]
    rules = Column(JSON, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    turns = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
