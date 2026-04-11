"""Tests for development cards: buy, play, largest army."""

import pytest
from unittest.mock import patch
from app.game.models import (
    GamePhase, TurnStep, Resource, DevCard, DevCardType,
)
from app.game.engine import (
    handle_buy_dev_card, handle_play_dev_card, check_largest_army,
    create_dev_card_deck, ActionError,
)
from tests.conftest import make_game


class TestCreateDeck:
    def test_deck_size(self):
        deck = create_dev_card_deck()
        assert len(deck) == 25

    def test_deck_composition(self):
        deck = create_dev_card_deck()
        counts = {}
        for c in deck:
            counts[c.card_type] = counts.get(c.card_type, 0) + 1
        assert counts[DevCardType.KNIGHT] == 14
        assert counts[DevCardType.VICTORY_POINT] == 5
        assert counts[DevCardType.YEAR_OF_PLENTY] == 2
        assert counts[DevCardType.MONOPOLY] == 2
        assert counts[DevCardType.ROAD_BUILDING] == 2


class TestBuyDevCard:
    def test_buy_success(self):
        game = make_game(resources={"p0": {Resource.ORE: 1, Resource.WHEAT: 1, Resource.SHEEP: 1}})
        game.dev_card_deck = [DevCard(card_type=DevCardType.KNIGHT)]
        result = handle_buy_dev_card(game, "p0")
        assert result["bought"] == "knight"
        assert len(game.players[0].dev_cards) == 1
        assert game.players[0].dev_cards[0].bought_on_turn == game.current_turn_number
        # Resources spent
        assert game.players[0].resources[Resource.ORE] == 0

    def test_not_enough_resources(self):
        game = make_game()  # no resources
        game.dev_card_deck = [DevCard(card_type=DevCardType.KNIGHT)]
        with pytest.raises(ActionError, match="Not enough resources"):
            handle_buy_dev_card(game, "p0")

    def test_empty_deck(self):
        game = make_game(resources={"p0": {r: 10 for r in Resource}})
        game.dev_card_deck = []
        with pytest.raises(ActionError, match="No development cards"):
            handle_buy_dev_card(game, "p0")

    def test_must_be_post_roll(self):
        game = make_game(turn_step=TurnStep.PRE_ROLL, resources={"p0": {r: 10 for r in Resource}})
        game.dev_card_deck = [DevCard(card_type=DevCardType.KNIGHT)]
        with pytest.raises(ActionError, match="after rolling"):
            handle_buy_dev_card(game, "p0")


class TestPlayKnight:
    def _game_with_knight(self, turn_step=TurnStep.PRE_ROLL):
        game = make_game(turn_step=turn_step)
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.KNIGHT, bought_on_turn=-1)
        ]
        return game

    def test_play_knight_pre_roll(self):
        game = self._game_with_knight(TurnStep.PRE_ROLL)
        result = handle_play_dev_card(game, "p0", "knight", {})
        assert result["action"] == "robber_place"
        assert game.turn_step == TurnStep.ROBBER_PLACE
        assert game.players[0].knights_played == 1
        assert len(game.players[0].dev_cards) == 0

    def test_play_knight_post_roll(self):
        game = self._game_with_knight(TurnStep.POST_ROLL)
        result = handle_play_dev_card(game, "p0", "knight", {})
        assert result["action"] == "robber_place"

    def test_cannot_play_card_bought_this_turn(self):
        game = make_game()
        game.current_turn_number = 5
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.KNIGHT, bought_on_turn=5)
        ]
        with pytest.raises(ActionError, match="not be bought this turn"):
            handle_play_dev_card(game, "p0", "knight", {})

    def test_one_card_per_turn(self):
        game = self._game_with_knight(TurnStep.POST_ROLL)
        game.players[0].dev_card_played_this_turn = True
        with pytest.raises(ActionError, match="Already played"):
            handle_play_dev_card(game, "p0", "knight", {})

    def test_cannot_play_vp_manually(self):
        game = make_game()
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.VICTORY_POINT, bought_on_turn=-1)
        ]
        with pytest.raises(ActionError, match="cannot be played manually"):
            handle_play_dev_card(game, "p0", "victory_point", {})


class TestYearOfPlenty:
    def test_gain_two_resources(self):
        game = make_game()
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.YEAR_OF_PLENTY, bought_on_turn=-1)
        ]
        result = handle_play_dev_card(game, "p0", "year_of_plenty", {
            "resources": {"wood": 1, "ore": 1}
        })
        assert result["action"] == "resources_gained"
        assert game.players[0].resources[Resource.WOOD] == 1
        assert game.players[0].resources[Resource.ORE] == 1

    def test_must_choose_exactly_2(self):
        game = make_game()
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.YEAR_OF_PLENTY, bought_on_turn=-1)
        ]
        with pytest.raises(ActionError, match="exactly 2"):
            handle_play_dev_card(game, "p0", "year_of_plenty", {
                "resources": {"wood": 3}
            })
        # Card should be returned to hand
        assert len(game.players[0].dev_cards) == 1


class TestMonopoly:
    def test_steal_all_of_resource(self):
        game = make_game(resources={
            "p0": {Resource.WOOD: 0},
            "p1": {Resource.WOOD: 5},
        })
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.MONOPOLY, bought_on_turn=-1)
        ]
        result = handle_play_dev_card(game, "p0", "monopoly", {"resource": "wood"})
        assert result["amount"] == 5
        assert game.players[0].resources[Resource.WOOD] == 5
        assert game.players[1].resources[Resource.WOOD] == 0

    def test_must_specify_resource(self):
        game = make_game()
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.MONOPOLY, bought_on_turn=-1)
        ]
        with pytest.raises(ActionError, match="must specify"):
            handle_play_dev_card(game, "p0", "monopoly", {})
        assert len(game.players[0].dev_cards) == 1


class TestRoadBuilding:
    def test_enters_road_building_step(self):
        game = make_game()
        game.players[0].dev_cards = [
            DevCard(card_type=DevCardType.ROAD_BUILDING, bought_on_turn=-1)
        ]
        result = handle_play_dev_card(game, "p0", "road_building", {})
        assert result["action"] == "road_building"
        assert game.turn_step == TurnStep.ROAD_BUILDING
        assert game.road_building_remaining == 2


class TestLargestArmy:
    def test_three_knights_claims_army(self):
        game = make_game()
        game.players[0].knights_played = 3
        check_largest_army(game)
        assert game.largest_army_holder == "p0"
        assert game.largest_army_size == 3

    def test_below_three_no_army(self):
        game = make_game()
        game.players[0].knights_played = 2
        check_largest_army(game)
        assert game.largest_army_holder is None

    def test_must_beat_current_holder(self):
        game = make_game()
        game.largest_army_holder = "p0"
        game.largest_army_size = 4
        game.players[0].knights_played = 4
        game.players[1].knights_played = 4  # tied, doesn't take
        check_largest_army(game)
        assert game.largest_army_holder == "p0"

    def test_overtake(self):
        game = make_game()
        game.largest_army_holder = "p0"
        game.largest_army_size = 3
        game.players[0].knights_played = 3
        game.players[1].knights_played = 4
        check_largest_army(game)
        assert game.largest_army_holder == "p1"
        assert game.largest_army_size == 4
