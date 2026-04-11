"""Tests for ELO rating calculation."""

import pytest
from unittest.mock import MagicMock
from app.game_records import _update_elo


def _make_user(user_id, elo=1000):
    """Create a mock User object for ELO testing."""
    user = MagicMock()
    user.id = user_id
    user.elo_rating = elo
    user.games_played = 0
    user.games_won = 0
    user.total_vp = 0
    return user


class TestEloCalculation:
    def test_winner_gains_loser_drops(self):
        u1 = _make_user("u1", 1000)
        u2 = _make_user("u2", 1000)
        users = {"u1": u1, "u2": u2}
        players = [
            {"user_id": "u1", "player_id": "p0"},
            {"user_id": "u2", "player_id": "p1"},
        ]
        _update_elo(users, players, winner_player_id="p0")

        assert u1.elo_rating > 1000  # winner gains
        assert u2.elo_rating < 1000  # loser drops

    def test_equal_elo_symmetric(self):
        """With equal starting ELO, winner gain == loser loss."""
        u1 = _make_user("u1", 1000)
        u2 = _make_user("u2", 1000)
        users = {"u1": u1, "u2": u2}
        players = [
            {"user_id": "u1", "player_id": "p0"},
            {"user_id": "u2", "player_id": "p1"},
        ]
        _update_elo(users, players, winner_player_id="p0")

        gain = u1.elo_rating - 1000
        loss = 1000 - u2.elo_rating
        assert abs(gain - loss) <= 1  # rounding

    def test_underdog_wins_big_gain(self):
        """Lower-rated player beating higher-rated → bigger gain."""
        u1 = _make_user("u1", 800)
        u2 = _make_user("u2", 1200)
        users = {"u1": u1, "u2": u2}
        players = [
            {"user_id": "u1", "player_id": "p0"},
            {"user_id": "u2", "player_id": "p1"},
        ]
        _update_elo(users, players, winner_player_id="p0")

        u1_gain = u1.elo_rating - 800
        # Underdog wins → larger gain than K/2
        assert u1_gain > 16

    def test_minimum_100(self):
        """ELO should never drop below 100."""
        u1 = _make_user("u1", 2000)
        u2 = _make_user("u2", 100)
        users = {"u1": u1, "u2": u2}
        players = [
            {"user_id": "u1", "player_id": "p0"},
            {"user_id": "u2", "player_id": "p1"},
        ]
        _update_elo(users, players, winner_player_id="p0")
        assert u2.elo_rating >= 100

    def test_single_player_no_update(self):
        """With fewer than 2 human players, no ELO change."""
        u1 = _make_user("u1", 1000)
        users = {"u1": u1}
        players = [{"user_id": "u1", "player_id": "p0"}]
        _update_elo(users, players, winner_player_id="p0")
        assert u1.elo_rating == 1000

    def test_four_player_game(self):
        """ELO updates work with 4 human players."""
        users_data = {f"u{i}": _make_user(f"u{i}", 1000 + i * 50) for i in range(4)}
        players = [
            {"user_id": f"u{i}", "player_id": f"p{i}"}
            for i in range(4)
        ]
        _update_elo(users_data, players, winner_player_id="p0")

        # Winner should gain
        assert users_data["u0"].elo_rating > 1000
        # All ratings should be integers
        for u in users_data.values():
            assert isinstance(u.elo_rating, int)
