"""Tests for game setup phase: start, snake draft, initial resources."""

import pytest
from unittest.mock import patch
from app.game.models import (
    GameState, GamePhase, TurnStep, Resource, PieceType, MapData,
)
from app.game.engine import (
    handle_start_game, handle_build, setup_order_for_players,
    ActionError,
)
from app.game.board import canonical_vertex, canonical_edge, edges_of_vertex
from tests.conftest import make_game, SMALL_MAP_TILES, SMALL_MAP_PORTS, make_players, valid_edge_of_vertex


class TestSetupOrderForPlayers:
    def test_two_players_snake(self):
        with patch("app.game.engine.random") as mock_rng:
            mock_rng.shuffle = lambda x: None  # no shuffle → [0,1]
            mock_rng.randint = lambda a, b: a
            order = setup_order_for_players(2)
        assert order == [0, 1, 1, 0]

    def test_four_players_snake(self):
        with patch("app.game.engine.random") as mock_rng:
            mock_rng.shuffle = lambda x: None
            mock_rng.randint = lambda a, b: a
            order = setup_order_for_players(4)
        assert order == [0, 1, 2, 3, 3, 2, 1, 0]

    def test_length(self):
        """Snake draft has 2*n entries."""
        for n in [2, 3, 4]:
            order = setup_order_for_players(n)
            assert len(order) == 2 * n


class TestHandleStartGame:
    def test_starts_game(self):
        game = make_game(phase=GamePhase.WAITING, turn_step=TurnStep.PRE_ROLL)
        map_data = MapData(map_id="test", tiles=list(SMALL_MAP_TILES), ports=list(SMALL_MAP_PORTS))
        handle_start_game(game, map_data, "p0")

        assert game.phase == GamePhase.SETUP_FORWARD
        assert len(game.setup_order) == 4  # 2 players * 2
        assert len(game.dev_card_deck) == 25
        assert game.current_turn_number == 0

    def test_cannot_start_twice(self):
        game = make_game(phase=GamePhase.PLAYING)
        map_data = MapData(map_id="test", tiles=list(SMALL_MAP_TILES), ports=[])
        with pytest.raises(ActionError, match="already started"):
            handle_start_game(game, map_data, "p0")

    def test_need_two_players(self):
        game = make_game(n_players=1, phase=GamePhase.WAITING, turn_step=TurnStep.PRE_ROLL)
        map_data = MapData(map_id="test", tiles=list(SMALL_MAP_TILES), ports=[])
        with pytest.raises(ActionError, match="at least 2"):
            handle_start_game(game, map_data, "p0")

    def test_robber_on_desert(self):
        game = make_game(phase=GamePhase.WAITING, turn_step=TurnStep.PRE_ROLL)
        map_data = MapData(map_id="test", tiles=list(SMALL_MAP_TILES), ports=[])
        handle_start_game(game, map_data, "p0")
        assert (game.robber_q, game.robber_r) == (0, 0)  # desert is at (0,0)


class TestSetupPlacement:
    def _setup_game(self):
        """Create a game in SETUP_FORWARD with known order [0,1,1,0]."""
        game = make_game(phase=GamePhase.WAITING, turn_step=TurnStep.PRE_ROLL)
        map_data = MapData(map_id="test", tiles=list(SMALL_MAP_TILES), ports=list(SMALL_MAP_PORTS))

        with patch("app.game.engine.random") as mock_rng:
            mock_rng.shuffle = lambda x: None
            mock_rng.randint = lambda a, b: a
            mock_rng.choice = lambda x: x[0]
            handle_start_game(game, map_data, "p0")

        return game

    def test_first_player_places_settlement_then_road(self):
        game = self._setup_game()
        assert game.phase == GamePhase.SETUP_FORWARD
        # setup_order should be [0,1,1,0]
        assert game.setup_order == [0, 1, 1, 0]
        # First player (p0) places settlement
        current_pid = game.players[game.current_player_index].player_id
        assert current_pid == "p0"

        # Must place settlement first (not road)
        vk = canonical_vertex(0, -1, 0)
        with pytest.raises(ActionError, match="settlement"):
            handle_build(game, "p0", "road", {"q": 0, "r": -1, "direction": 0})

        # Place settlement
        result = handle_build(game, "p0", "settlement", {"q": 0, "r": -1, "direction": 0})
        assert result["placed"] == "settlement"

        # Now must place road
        with pytest.raises(ActionError, match="road"):
            handle_build(game, "p0", "settlement", {"q": 1, "r": -1, "direction": 2})

        # Place road adjacent to settlement (must be valid land edge)
        adj_edges = valid_edge_of_vertex(vk, game.map_data)
        ek = adj_edges[0]
        result = handle_build(game, "p0", "road", {"q": ek[0], "r": ek[1], "direction": ek[2]})
        assert result["placed"] == "road"

    def test_wrong_player_rejected(self):
        game = self._setup_game()
        # p1 tries to go when it's p0's turn
        with pytest.raises(ActionError, match="Not your turn"):
            handle_build(game, "p1", "settlement", {"q": 0, "r": -1, "direction": 0})

    def test_full_setup_transitions_to_playing(self):
        """Complete all 8 setup placements → game transitions to PLAYING."""
        game = self._setup_game()

        # We need 4 non-adjacent settlement locations on the small map
        settlement_spots = [
            (0, -1, 0),   # p0 first
            (0, 1, 3),    # p1 first
            (1, 0, 1),    # p1 second (backward)
            (-1, 0, 3),   # p0 second (backward)
        ]

        for i, (sq, sr, sc) in enumerate(settlement_spots):
            # Determine current player from setup_order
            turn_idx = game.setup_step // 2
            pid = game.players[game.setup_order[turn_idx]].player_id

            # Place settlement
            handle_build(game, pid, "settlement", {"q": sq, "r": sr, "direction": sc})

            if game.phase == GamePhase.FINISHED:
                break

            # Place road adjacent to that settlement
            vk = canonical_vertex(sq, sr, sc)
            adj_edges = valid_edge_of_vertex(vk, game.map_data)
            ek = adj_edges[0]
            handle_build(game, pid, "road", {"q": ek[0], "r": ek[1], "direction": ek[2]})

        assert game.phase == GamePhase.PLAYING
        assert game.turn_step == TurnStep.PRE_ROLL

    def test_second_round_grants_resources(self):
        """Second setup round should grant resources from adjacent tiles."""
        game = self._setup_game()

        settlement_spots = [
            (0, -1, 0),
            (0, 1, 3),
            (1, 0, 1),   # p1 second round
            (-1, 0, 3),  # p0 second round
        ]

        for i, (sq, sr, sc) in enumerate(settlement_spots):
            turn_idx = game.setup_step // 2
            pid = game.players[game.setup_order[turn_idx]].player_id

            handle_build(game, pid, "settlement", {"q": sq, "r": sr, "direction": sc})
            if game.phase == GamePhase.FINISHED:
                break
            vk = canonical_vertex(sq, sr, sc)
            adj_edges = valid_edge_of_vertex(vk, game.map_data)
            ek = adj_edges[0]
            handle_build(game, pid, "road", {"q": ek[0], "r": ek[1], "direction": ek[2]})

        # After setup, players should have some resources from 2nd settlement
        p0 = game.player_by_id("p0")
        p1 = game.player_by_id("p1")
        p0_total = sum(p0.resources.values())
        p1_total = sum(p1.resources.values())
        # Second round settlements are adjacent to resource tiles, so > 0
        assert p0_total > 0 or p1_total > 0, "At least one player should get setup resources"
