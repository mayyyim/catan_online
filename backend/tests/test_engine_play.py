"""Tests for core turn flow: dice, resources, building, end turn, victory."""

import pytest
from unittest.mock import patch
from app.game.models import (
    GamePhase, TurnStep, Resource, PieceType, DevCardType, DevCard,
)
from app.game.engine import (
    handle_roll_dice, handle_build, handle_end_turn,
    produce_resources, recalculate_vp, check_winner,
    ActionError,
)
from app.game.board import canonical_vertex, canonical_edge, edges_of_vertex
from tests.conftest import make_game, place_settlement, place_city, place_road, valid_edge_of_vertex


class TestRollDice:
    def test_roll_produces_resources(self):
        """Rolling a number matching a tile token produces resources."""
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        # Place p0 settlement on tile (0,-1) which has token=6, type=forest→wood
        place_settlement(game, "p0", 0, -1, 0)

        with patch("app.game.engine.random") as mock_rng:
            mock_rng.randint = lambda a, b: 3  # 3+3=6
            result = handle_roll_dice(game, "p0")

        assert result["total"] == 6
        assert game.turn_step == TurnStep.POST_ROLL
        assert game.players[0].resources[Resource.WOOD] > 0

    def test_roll_7_triggers_robber(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        # Give p1 more than 7 cards
        game.players[1].resources = {r: 2 for r in Resource}  # 10 total

        with patch("app.game.engine.random") as mock_rng:
            mock_rng.randint = lambda a, b: (4 if mock_rng.randint.call_count <= 1 else 3)
            # Need 3+4=7
            call_count = [0]
            def side_effect(a, b):
                call_count[0] += 1
                return 4 if call_count[0] == 1 else 3
            mock_rng.randint = side_effect
            result = handle_roll_dice(game, "p0")

        assert result["total"] == 7
        # p1 has 10 cards > 7, so must discard
        assert game.turn_step == TurnStep.ROBBER_DISCARD
        assert "p1" in game.players_to_discard

    def test_wrong_phase_rejected(self):
        game = make_game(phase=GamePhase.SETUP_FORWARD, turn_step=TurnStep.PRE_ROLL)
        with pytest.raises(ActionError, match="Not in playing"):
            handle_roll_dice(game, "p0")

    def test_already_rolled_rejected(self):
        game = make_game(turn_step=TurnStep.POST_ROLL)
        with pytest.raises(ActionError, match="Already rolled"):
            handle_roll_dice(game, "p0")

    def test_not_your_turn(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        with pytest.raises(ActionError, match="Not your turn"):
            handle_roll_dice(game, "p1")


class TestProduceResources:
    def test_settlement_gets_1(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        production = produce_resources(game, 6)  # tile (0,-1) has token 6
        assert "p0" in production
        assert production["p0"].get("wood", 0) >= 1

    def test_city_gets_2(self):
        game = make_game()
        place_city(game, "p0", 0, -1, 0)
        production = produce_resources(game, 6)
        assert production.get("p0", {}).get("wood", 0) >= 2

    def test_robber_blocks_production(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        # Move robber to tile (0,-1)
        game.robber_q, game.robber_r = 0, -1
        production = produce_resources(game, 6)
        assert production.get("p0", {}).get("wood", 0) == 0

    def test_roll_7_no_production(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        production = produce_resources(game, 7)
        assert production == {}


class TestBuild:
    def test_build_settlement(self):
        game = make_game(resources={"p0": {r: 10 for r in Resource}})
        # Need road connected first
        vk = canonical_vertex(0, -1, 0)
        adj_edges = edges_of_vertex(vk)
        place_road(game, "p0", adj_edges[0][0], adj_edges[0][1], adj_edges[0][2])

        result = handle_build(game, "p0", "settlement", {"q": 0, "r": -1, "direction": 0})
        assert result["placed"] == "settlement"
        # Resources deducted
        p0 = game.players[0]
        assert p0.resources[Resource.WOOD] == 9
        assert p0.resources[Resource.BRICK] == 9
        assert p0.resources[Resource.WHEAT] == 9
        assert p0.resources[Resource.SHEEP] == 9

    def test_build_road(self):
        game = make_game(resources={"p0": {r: 10 for r in Resource}})
        # Place a settlement first so road has connection
        place_settlement(game, "p0", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        adj_edges = valid_edge_of_vertex(vk, game.map_data)
        ek = adj_edges[0]

        result = handle_build(game, "p0", "road", {"q": ek[0], "r": ek[1], "direction": ek[2]})
        assert result["placed"] == "road"
        assert game.players[0].resources[Resource.WOOD] == 9
        assert game.players[0].resources[Resource.BRICK] == 9

    def test_build_city(self):
        game = make_game(resources={"p0": {r: 10 for r in Resource}})
        place_settlement(game, "p0", 0, -1, 0)
        result = handle_build(game, "p0", "city", {"q": 0, "r": -1, "direction": 0})
        assert result["placed"] == "city"
        assert game.players[0].resources[Resource.WHEAT] == 8  # cost 2
        assert game.players[0].resources[Resource.ORE] == 7    # cost 3

    def test_not_enough_resources(self):
        game = make_game()  # no resources
        place_settlement(game, "p0", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        adj_edges = edges_of_vertex(vk)
        place_road(game, "p0", adj_edges[0][0], adj_edges[0][1], adj_edges[0][2])

        # Try to build settlement with no resources
        vk2 = canonical_vertex(0, -1, 5)
        adj2 = edges_of_vertex(vk2)
        # Connect road
        from app.game.board import vertices_of_edge
        # Find a vertex 2 edges away to avoid distance rule
        # Just test the resource check directly
        with pytest.raises(ActionError, match="Not enough resources"):
            handle_build(game, "p0", "city", {"q": 0, "r": -1, "direction": 0})

    def test_must_roll_first(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL, resources={"p0": {r: 10 for r in Resource}})
        with pytest.raises(ActionError, match="roll dice"):
            handle_build(game, "p0", "settlement", {"q": 0, "r": -1, "direction": 0})


class TestEndTurn:
    def test_advance_to_next_player(self):
        game = make_game()
        handle_end_turn(game, "p0")
        assert game.current_player_index == 1
        assert game.turn_step == TurnStep.PRE_ROLL

    def test_wraps_around(self):
        game = make_game(current_player=1)
        handle_end_turn(game, "p1")
        assert game.current_player_index == 0

    def test_not_your_turn(self):
        game = make_game()
        with pytest.raises(ActionError, match="Not your turn"):
            handle_end_turn(game, "p1")

    def test_must_be_post_roll(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL)
        with pytest.raises(ActionError, match="complete all actions"):
            handle_end_turn(game, "p0")

    def test_increments_turn_number(self):
        game = make_game()
        game.current_turn_number = 5
        handle_end_turn(game, "p0")
        assert game.current_turn_number == 6

    def test_clears_dev_card_flag(self):
        game = make_game()
        game.players[0].dev_card_played_this_turn = True
        handle_end_turn(game, "p0")
        assert not game.players[0].dev_card_played_this_turn


class TestVictory:
    def test_check_winner_at_target(self):
        game = make_game()
        game.players[0].victory_points = 10
        assert check_winner(game) == "p0"

    def test_no_winner_below_target(self):
        game = make_game()
        game.players[0].victory_points = 9
        assert check_winner(game) is None

    def test_custom_vp_target(self):
        game = make_game()
        game.rules.victory_points_target = 8
        game.players[0].victory_points = 8
        assert check_winner(game) == "p0"

    def test_end_turn_triggers_win(self):
        game = make_game()
        # Give p0 enough VPs via buildings
        for i in range(5):
            place_settlement(game, "p0", 0, -1, i)
        # 5 settlements = 5 VP, plus we need more
        for i in range(4):
            place_city(game, "p0", 0, 1, i)
        # Manually set a high VP that will trigger on recalculate
        # Actually let's just place enough pieces
        game.rules.victory_points_target = 3
        recalculate_vp(game)
        handle_end_turn(game, "p0")
        assert game.phase == GamePhase.FINISHED
        assert game.winner_id == "p0"
