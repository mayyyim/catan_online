"""Tests for model serialization/deserialization roundtrips."""

import pytest
from app.game.models import (
    GameState, GamePhase, TurnStep, Player, MapData, Tile, Port,
    TileType, Resource, PlacedPiece, PieceType, DevCard, DevCardType,
    GameRules,
)
from tests.conftest import make_game, place_settlement, place_road


class TestPlayerRoundtrip:
    def test_basic_roundtrip(self):
        p = Player(player_id="p0", name="Alice", color="red")
        p.resources[Resource.WOOD] = 3
        p.resources[Resource.ORE] = 5
        d = p.to_dict()
        p2 = Player.from_dict(d)
        assert p2.player_id == "p0"
        assert p2.name == "Alice"
        assert p2.color == "red"
        assert p2.resources[Resource.WOOD] == 3
        assert p2.resources[Resource.ORE] == 5

    def test_dev_cards_roundtrip(self):
        p = Player(player_id="p0", name="Alice", color="red")
        p.dev_cards = [
            DevCard(card_type=DevCardType.KNIGHT, bought_on_turn=3),
            DevCard(card_type=DevCardType.VICTORY_POINT, bought_on_turn=5),
        ]
        p.knights_played = 2
        d = p.to_dict()
        p2 = Player.from_dict(d)
        assert len(p2.dev_cards) == 2
        assert p2.dev_cards[0].card_type == DevCardType.KNIGHT
        assert p2.dev_cards[0].bought_on_turn == 3
        assert p2.knights_played == 2

    def test_hidden_resources(self):
        """to_dict with hide_resources hides exact resource counts and dev cards."""
        p = Player(player_id="p0", name="Alice", color="red")
        p.resources = {r: 2 for r in Resource}
        p.dev_cards = [DevCard(card_type=DevCardType.KNIGHT)]
        d = p.to_dict(hide_resources=True)
        # Dev cards hidden
        assert d["dev_cards"] == []
        assert d["dev_card_count"] == 1
        # Resource count shown
        assert d["resource_count"] == 10

    def test_setup_settlements_roundtrip(self):
        p = Player(player_id="p0", name="Alice", color="red")
        p.setup_settlements = [(0, -1, 0), (1, 0, 3)]
        d = p.to_dict()
        p2 = Player.from_dict(d)
        assert p2.setup_settlements == [(0, -1, 0), (1, 0, 3)]


class TestTileRoundtrip:
    def test_roundtrip(self):
        t = Tile(0, -1, TileType.FOREST, token=6)
        d = t.to_dict()
        t2 = Tile.from_dict(d)
        assert t2.q == 0
        assert t2.r == -1
        assert t2.tile_type == TileType.FOREST
        assert t2.token == 6
        assert d["resource"] == "wood"

    def test_desert_no_resource(self):
        t = Tile(0, 0, TileType.DESERT, token=None)
        d = t.to_dict()
        assert d["resource"] is None
        t2 = Tile.from_dict(d)
        assert t2.tile_type == TileType.DESERT


class TestPortRoundtrip:
    def test_specific_port(self):
        p = Port(0, -1, resource=Resource.WOOD, ratio=2, side=3)
        d = p.to_dict()
        p2 = Port.from_dict(d)
        assert p2.resource == Resource.WOOD
        assert p2.ratio == 2
        assert p2.side == 3

    def test_generic_port(self):
        p = Port(0, -1, resource=None, ratio=3, side=0)
        d = p.to_dict()
        p2 = Port.from_dict(d)
        assert p2.resource is None
        assert p2.ratio == 3


class TestMapDataRoundtrip:
    def test_roundtrip(self, small_map):
        d = small_map.to_dict()
        m2 = MapData.from_dict(d)
        assert m2.map_id == "test_small"
        assert len(m2.tiles) == 7
        assert len(m2.ports) == 2


class TestGameStateRoundtrip:
    def test_full_roundtrip(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        place_road(game, "p0", 0, -1, 0)
        game.last_dice = [3, 4]
        game.current_turn_number = 7

        d = game.to_dict()
        g2 = GameState.from_dict(d)

        assert g2.room_id == "test_room"
        assert g2.phase == GamePhase.PLAYING
        assert g2.turn_step == TurnStep.POST_ROLL
        assert len(g2.players) == 2
        assert len(g2.vertices) == 1
        assert len(g2.edges) == 1
        assert g2.last_dice == [3, 4]
        assert g2.current_turn_number == 7

    def test_viewer_hides_other_resources(self):
        game = make_game(resources={"p0": {r: 5 for r in Resource}})
        d = game.to_dict(viewer_player_id="p1")
        # p0's resources should be hidden (only count shown)
        p0_data = d["players"][0]
        assert p0_data["resource_count"] == 25
        # p0's dev cards hidden
        assert p0_data["dev_cards"] == []

    def test_dev_card_deck_hidden_for_viewers(self):
        game = make_game()
        game.dev_card_deck = [DevCard(card_type=DevCardType.KNIGHT)]
        d = game.to_dict(viewer_player_id="p0")
        assert "dev_card_deck" not in d
        assert d["dev_card_deck_count"] == 1

    def test_dev_card_deck_included_for_persistence(self):
        game = make_game()
        game.dev_card_deck = [DevCard(card_type=DevCardType.KNIGHT)]
        d = game.to_dict()  # no viewer = full persistence mode
        assert "dev_card_deck" in d
        assert len(d["dev_card_deck"]) == 1

    def test_rules_roundtrip(self):
        game = make_game()
        game.rules.victory_points_target = 12
        game.rules.friendly_robber = True
        game.rules.starting_resources_double = True

        d = game.to_dict()
        g2 = GameState.from_dict(d)
        assert g2.rules.victory_points_target == 12
        assert g2.rules.friendly_robber is True
        assert g2.rules.starting_resources_double is True

    def test_trade_proposal_roundtrip(self):
        game = make_game()
        game.trade_proposal = {
            "id": "abc123",
            "proposer_id": "p0",
            "offer": {"wood": 1},
            "want": {"brick": 1},
            "rejected_by": ["p1"],
        }
        d = game.to_dict()
        g2 = GameState.from_dict(d)
        assert g2.trade_proposal["id"] == "abc123"
        assert g2.trade_proposal["rejected_by"] == ["p1"]


class TestGameRulesRoundtrip:
    def test_defaults(self):
        r = GameRules()
        d = r.to_dict()
        r2 = GameRules.from_dict(d)
        assert r2.victory_points_target == 10
        assert r2.friendly_robber is False
        assert r2.starting_resources_double is False

    def test_custom(self):
        r = GameRules(victory_points_target=8, friendly_robber=True, starting_resources_double=True)
        d = r.to_dict()
        r2 = GameRules.from_dict(d)
        assert r2.victory_points_target == 8
        assert r2.friendly_robber is True
