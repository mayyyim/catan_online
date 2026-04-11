"""
Game result persistence — saves finished game records and updates player stats + ELO.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.db_models import GameRecord, User

logger = logging.getLogger("catan.game_records")


def save_game_result(
    db: Session,
    game_state: dict,
    duration_seconds: int = 0,
    player_user_map: Optional[Dict[str, str]] = None,
) -> GameRecord:
    """Save a finished game result and update player stats.

    Args:
        db: SQLAlchemy session.
        game_state: The full game state dict (from GameState.to_dict()).
        duration_seconds: How long the game lasted.
        player_user_map: Optional mapping of player_id -> user_id for linking
                         game players to registered accounts.

    Returns:
        The created GameRecord.
    """
    if player_user_map is None:
        player_user_map = {}

    winner_player_id = game_state.get("winner_id")
    players = game_state.get("players", [])

    # Build players_data for the record
    players_data: List[dict] = []
    for p in players:
        pid = p.get("player_id", "")
        uid = player_user_map.get(pid)
        players_data.append({
            "user_id": uid,
            "name": p.get("name"),
            "player_id": pid,
            "color": p.get("color"),
            "victory_points": p.get("victory_points", 0),
            "is_bot": p.get("is_bot", False),
        })

    record = GameRecord(
        room_id=game_state.get("room_id", ""),
        map_id=(game_state.get("map") or {}).get("map_id", "unknown"),
        winner_id=None,
        player_count=len(players),
        players_data=players_data,
        rules=game_state.get("rules"),
        turns=game_state.get("current_turn_number", 0),
        duration_seconds=duration_seconds,
        finished_at=datetime.utcnow(),
    )
    db.add(record)

    # Update user stats for registered players
    human_players = [p for p in players_data if not p.get("is_bot")]
    user_ids = [p.get("user_id") for p in human_players if p.get("user_id")]

    if user_ids:
        users = {
            u.id: u
            for u in db.query(User).filter(User.id.in_(user_ids)).all()
        }

        for p in human_players:
            uid = p.get("user_id")
            if uid and uid in users:
                user = users[uid]
                user.games_played += 1
                user.total_vp += p.get("victory_points", 0)
                if p.get("player_id") == winner_player_id:
                    user.games_won += 1
                    record.winner_id = uid

        # ELO calculation
        _update_elo(users, human_players, winner_player_id)

    db.commit()
    logger.info(
        "Saved game record room=%s winner=%s players=%d turns=%d",
        record.room_id,
        record.winner_id,
        record.player_count,
        record.turns or 0,
    )
    return record


def _update_elo(
    users: Dict[str, "User"],
    players: List[dict],
    winner_player_id: Optional[str],
) -> None:
    """Simple ELO update for all registered human players. K-factor = 32."""
    K = 32
    human_with_elo = [
        (p, users[p["user_id"]])
        for p in players
        if p.get("user_id") in users
    ]
    if len(human_with_elo) < 2:
        return

    n = len(human_with_elo)
    avg_elo = sum(u.elo_rating for _, u in human_with_elo) / n

    for p, user in human_with_elo:
        expected = 1 / (1 + 10 ** ((avg_elo - user.elo_rating) / 400))
        actual = 1.0 if p.get("player_id") == winner_player_id else 0.0
        user.elo_rating = max(100, int(user.elo_rating + K * (actual - expected)))
