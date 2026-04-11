"""Tests for bank trade (4:1/3:1/2:1) and P2P trade proposal system."""

import pytest
from app.game.models import (
    GamePhase, TurnStep, Resource, PieceType,
)
from app.game.engine import (
    handle_trade, handle_propose_trade, handle_accept_trade,
    handle_reject_trade, handle_cancel_trade, ActionError,
)
from app.game.board import canonical_vertex
from tests.conftest import make_game, place_settlement


class TestBankTrade:
    def test_4_to_1_basic(self):
        game = make_game(resources={"p0": {Resource.WOOD: 4}})
        result = handle_trade(game, "p0", {"wood": 4}, {"brick": 1})
        assert result["traded"]
        assert game.players[0].resources[Resource.WOOD] == 0
        assert game.players[0].resources[Resource.BRICK] == 1

    def test_not_enough_resources(self):
        game = make_game(resources={"p0": {Resource.WOOD: 3}})
        with pytest.raises(ActionError, match="Not enough"):
            handle_trade(game, "p0", {"wood": 4}, {"brick": 1})

    def test_must_offer_multiples_of_ratio(self):
        game = make_game(resources={"p0": {Resource.WOOD: 5}})
        with pytest.raises(ActionError, match="multiples"):
            handle_trade(game, "p0", {"wood": 5}, {"brick": 1})

    def test_want_must_match_allowed(self):
        game = make_game(resources={"p0": {Resource.WOOD: 8}})
        # 8 wood / 4 = 2 resources allowed
        with pytest.raises(ActionError, match="exactly 2"):
            handle_trade(game, "p0", {"wood": 8}, {"brick": 1})

    def test_3_to_1_generic_port(self):
        """Player with settlement on 3:1 port can trade 3:1."""
        game = make_game(resources={"p0": {Resource.BRICK: 3}})
        # Port: 3:1 generic on tile (0,-1) side 0 → vertices at corners 0 and 1
        vk = canonical_vertex(0, -1, 0)
        place_settlement(game, "p0", 0, -1, 0)

        result = handle_trade(game, "p0", {"brick": 3}, {"ore": 1})
        assert result["traded"]
        assert game.players[0].resources[Resource.BRICK] == 0
        assert game.players[0].resources[Resource.ORE] == 1

    def test_2_to_1_specific_port(self):
        """Player with settlement on 2:1 wood port can trade wood 2:1."""
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        # Port: 2:1 wood on tile (-1,0) side 3 → vertex at corner 3
        place_settlement(game, "p0", -1, 0, 3)

        result = handle_trade(game, "p0", {"wood": 2}, {"ore": 1})
        assert result["traded"]
        assert game.players[0].resources[Resource.WOOD] == 0

    def test_empty_offer_rejected(self):
        game = make_game(resources={"p0": {r: 10 for r in Resource}})
        with pytest.raises(ActionError, match="at least one"):
            handle_trade(game, "p0", {}, {"wood": 1})

    def test_wrong_phase(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL, resources={"p0": {Resource.WOOD: 4}})
        with pytest.raises(ActionError, match="roll"):
            handle_trade(game, "p0", {"wood": 4}, {"brick": 1})


class TestP2PTrade:
    def test_propose_trade(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        result = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        assert "id" in result
        assert result["proposer_id"] == "p0"
        assert game.trade_proposal is not None

    def test_proposer_must_have_resources(self):
        game = make_game()  # no resources
        with pytest.raises(ActionError, match="Not enough"):
            handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})

    def test_accept_trade(self):
        game = make_game(resources={
            "p0": {Resource.WOOD: 2},
            "p1": {Resource.BRICK: 2},
        })
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        result = handle_accept_trade(game, "p1", proposal["id"])

        assert result["proposer_id"] == "p0"
        assert result["accepter_id"] == "p1"
        # p0: gave 1 wood, got 1 brick
        assert game.players[0].resources[Resource.WOOD] == 1
        assert game.players[0].resources[Resource.BRICK] == 1
        # p1: gave 1 brick, got 1 wood
        assert game.players[1].resources[Resource.BRICK] == 1
        assert game.players[1].resources[Resource.WOOD] == 1
        assert game.trade_proposal is None

    def test_cannot_accept_own_trade(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        with pytest.raises(ActionError, match="own trade"):
            handle_accept_trade(game, "p0", proposal["id"])

    def test_accepter_must_have_resources(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        # p1 has no brick
        with pytest.raises(ActionError, match="enough"):
            handle_accept_trade(game, "p1", proposal["id"])

    def test_reject_trade(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        result = handle_reject_trade(game, "p1", proposal["id"])
        # 2 players: p1 is the only other player. All rejected → auto-cancel
        assert result["auto_cancelled"]
        assert game.trade_proposal is None

    def test_partial_reject_no_auto_cancel(self):
        game = make_game(n_players=3, resources={"p0": {Resource.WOOD: 2}})
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        result = handle_reject_trade(game, "p1", proposal["id"])
        assert not result["auto_cancelled"]  # p2 hasn't rejected yet
        assert game.trade_proposal is not None

    def test_cancel_trade(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        proposal = handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        result = handle_cancel_trade(game, "p0")
        assert result["cancelled"]
        assert game.trade_proposal is None

    def test_only_proposer_can_cancel(self):
        game = make_game(resources={"p0": {Resource.WOOD: 2}})
        handle_propose_trade(game, "p0", {"wood": 1}, {"brick": 1})
        with pytest.raises(ActionError, match="proposer"):
            handle_cancel_trade(game, "p1")
