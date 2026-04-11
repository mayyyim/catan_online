"""Tests for robber flow: discard, place, steal, friendly robber."""

import pytest
from unittest.mock import patch
from app.game.models import (
    GamePhase, TurnStep, Resource, TileType,
)
from app.game.engine import (
    handle_roll_dice, handle_discard, handle_place_robber, handle_steal,
    ActionError,
)
from tests.conftest import make_game, place_settlement


def _roll_7(game, player_id="p0"):
    """Helper: force a roll of 7."""
    with patch("app.game.engine.random") as mock_rng:
        call_count = [0]
        def side_effect(a, b):
            call_count[0] += 1
            return 4 if call_count[0] == 1 else 3
        mock_rng.randint = side_effect
        return handle_roll_dice(game, player_id)


class TestDiscard:
    def test_must_discard_half(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.players[1].resources = {r: 2 for r in Resource}  # 10 total
        _roll_7(game)

        assert game.turn_step == TurnStep.ROBBER_DISCARD
        assert "p1" in game.players_to_discard

        # Must discard exactly 5
        with pytest.raises(ActionError, match="exactly 5"):
            handle_discard(game, "p1", {"wood": 2})

        # Correct discard
        handle_discard(game, "p1", {"wood": 2, "brick": 2, "wheat": 1})
        assert "p1" not in game.players_to_discard
        assert sum(game.players[1].resources.values()) == 5

    def test_discard_transitions_to_robber_place(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.players[1].resources = {r: 2 for r in Resource}
        _roll_7(game)
        handle_discard(game, "p1", {"wood": 2, "brick": 2, "wheat": 1})
        assert game.turn_step == TurnStep.ROBBER_PLACE

    def test_cannot_discard_more_than_owned(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.players[1].resources = {Resource.WOOD: 8, Resource.BRICK: 0, Resource.WHEAT: 0, Resource.SHEEP: 0, Resource.ORE: 0}
        _roll_7(game)
        with pytest.raises(ActionError, match="Not enough"):
            handle_discard(game, "p1", {"brick": 4})

    def test_no_discard_if_7_or_less(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.players[0].resources = {r: 1 for r in Resource}  # 5 total
        game.players[1].resources = {r: 1 for r in Resource}  # 5 total
        _roll_7(game)
        # No one needs to discard → jump to robber_place
        assert game.turn_step == TurnStep.ROBBER_PLACE


class TestPlaceRobber:
    def test_move_robber(self):
        game = make_game(turn_step=TurnStep.ROBBER_PLACE)
        # Robber starts at (0,0) desert
        handle_place_robber(game, "p0", 0, -1)
        assert game.robber_q == 0
        assert game.robber_r == -1

    def test_cannot_stay_same_tile(self):
        game = make_game(turn_step=TurnStep.ROBBER_PLACE)
        with pytest.raises(ActionError, match="different tile"):
            handle_place_robber(game, "p0", 0, 0)

    def test_must_be_land_tile(self):
        game = make_game(turn_step=TurnStep.ROBBER_PLACE)
        with pytest.raises(ActionError, match="land tile"):
            handle_place_robber(game, "p0", 99, 99)

    def test_identifies_steal_targets(self):
        game = make_game(turn_step=TurnStep.ROBBER_PLACE)
        # Place p1 settlement adjacent to tile (0,-1)
        place_settlement(game, "p1", 0, -1, 0)
        handle_place_robber(game, "p0", 0, -1)
        assert game.turn_step == TurnStep.ROBBER_STEAL
        assert "p1" in game.robber_steal_targets

    def test_no_steal_targets_goes_to_post_roll(self):
        game = make_game(turn_step=TurnStep.ROBBER_PLACE)
        handle_place_robber(game, "p0", 0, -1)
        # No settlements near (0,-1) → post_roll
        assert game.turn_step == TurnStep.POST_ROLL


class TestSteal:
    def test_steal_random_resource(self):
        game = make_game(turn_step=TurnStep.ROBBER_STEAL)
        game.robber_steal_targets = ["p1"]
        game.players[1].resources[Resource.WOOD] = 3

        with patch("app.game.engine.random") as mock_rng:
            mock_rng.choice = lambda x: Resource.WOOD
            result = handle_steal(game, "p0", "p1")

        assert result["stolen"] == "wood"
        assert game.players[1].resources[Resource.WOOD] == 2
        assert game.players[0].resources[Resource.WOOD] == 1
        assert game.turn_step == TurnStep.POST_ROLL

    def test_steal_from_empty_hand(self):
        game = make_game(turn_step=TurnStep.ROBBER_STEAL)
        game.robber_steal_targets = ["p1"]
        # p1 has nothing
        result = handle_steal(game, "p0", "p1")
        assert result["stolen"] is None
        assert game.turn_step == TurnStep.POST_ROLL

    def test_invalid_target(self):
        game = make_game(turn_step=TurnStep.ROBBER_STEAL)
        game.robber_steal_targets = ["p1"]
        with pytest.raises(ActionError, match="Invalid steal target"):
            handle_steal(game, "p0", "p0")


class TestFriendlyRobber:
    def test_friendly_robber_skips_flow(self):
        """With friendly robber ON and all players < 4 VP, skip robber flow."""
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.rules.friendly_robber = True
        # All players have 0 VP < 4
        _roll_7(game)
        # Should skip to POST_ROLL
        assert game.turn_step == TurnStep.POST_ROLL

    def test_friendly_robber_disabled_above_threshold(self):
        """With friendly robber ON but a player >= 4 VP, normal robber flow."""
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        game.rules.friendly_robber = True
        game.players[0].victory_points = 5
        game.players[1].resources = {r: 2 for r in Resource}  # 10 cards
        _roll_7(game)
        # Should trigger normal flow (discard or place)
        assert game.turn_step in (TurnStep.ROBBER_DISCARD, TurnStep.ROBBER_PLACE)
