"""
Stats and leaderboard API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.db_models import GameRecord, User

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/leaderboard")
def get_leaderboard(limit: int = 20, db: Session = Depends(get_db)):
    """Top players by ELO rating. Minimum 3 games to qualify."""
    users = (
        db.query(User)
        .filter(
            User.is_guest == False,  # noqa: E712
            User.games_played >= 3,
        )
        .order_by(User.elo_rating.desc())
        .limit(min(limit, 100))
        .all()
    )

    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "user_id": u.id,
                "display_name": u.display_name,
                "elo_rating": u.elo_rating,
                "games_played": u.games_played,
                "games_won": u.games_won,
                "win_rate": (
                    round(u.games_won / u.games_played * 100, 1)
                    if u.games_played > 0
                    else 0
                ),
            }
            for i, u in enumerate(users)
        ]
    }


@router.get("/profile/{user_id}")
def get_profile(user_id: str, db: Session = Depends(get_db)):
    """Public profile for any user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch recent games that include this user.
    # JSON contains queries vary by DB; use a simple Python filter for portability.
    all_recent = (
        db.query(GameRecord)
        .order_by(GameRecord.finished_at.desc())
        .limit(200)
        .all()
    )
    user_games = [
        g
        for g in all_recent
        if any(p.get("user_id") == user_id for p in (g.players_data or []))
    ][:10]

    return {
        "user_id": user.id,
        "display_name": user.display_name,
        "elo_rating": user.elo_rating,
        "games_played": user.games_played,
        "games_won": user.games_won,
        "total_vp": user.total_vp,
        "win_rate": (
            round(user.games_won / user.games_played * 100, 1)
            if user.games_played > 0
            else 0
        ),
        "avg_vp": (
            round(user.total_vp / user.games_played, 1)
            if user.games_played > 0
            else 0
        ),
        "recent_games": [
            {
                "id": g.id,
                "map_id": g.map_id,
                "player_count": g.player_count,
                "turns": g.turns,
                "finished_at": (
                    g.finished_at.isoformat() if g.finished_at else None
                ),
                "won": g.winner_id == user_id,
                "players": g.players_data,
            }
            for g in user_games
        ],
    }


@router.get("/my-stats")
def get_my_stats(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Current user's detailed stats (requires auth)."""
    return get_profile(user.id, db)
