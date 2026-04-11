"""Tests for board geometry: canonical keys, adjacency, placement validation."""

import pytest
from app.game.board import (
    canonical_vertex, canonical_edge,
    hex_neighbors, vertices_of_tile, edges_of_tile,
    vertices_of_edge, edges_of_vertex, adjacent_vertices,
    tiles_of_vertex, valid_vertices, valid_edges,
    can_place_settlement, can_place_road, can_upgrade_city,
)
from app.game.models import PieceType
from tests.conftest import make_game, place_settlement, place_road, valid_edge_of_vertex


# ---------------------------------------------------------------------------
# Canonical vertex / edge
# ---------------------------------------------------------------------------

class TestCanonicalVertex:
    def test_same_physical_vertex_from_different_tiles(self):
        """Corner 0 of (0,0) should canonicalize the same as shared corners
        of its two neighboring hexes."""
        v1 = canonical_vertex(0, 0, 0)
        # Corner 0 is shared with neighbor (1,-1) corner 2 and neighbor (1,0) corner 4
        v2 = canonical_vertex(1, -1, 2)
        v3 = canonical_vertex(1, 0, 4)
        assert v1 == v2 == v3

    def test_all_6_corners_distinct(self):
        """All 6 corners of a center tile should be distinct canonical vertices."""
        verts = set()
        for c in range(6):
            verts.add(canonical_vertex(0, 0, c))
        assert len(verts) == 6

    def test_canonical_is_min(self):
        """Canonical form should be the lexicographically smallest representation."""
        v = canonical_vertex(0, 0, 0)
        assert v <= (0, 0, 0)


class TestCanonicalEdge:
    def test_same_edge_from_both_sides(self):
        """Side 0 of (0,0) should equal side 3 of its neighbor (1,0)."""
        e1 = canonical_edge(0, 0, 0)
        e2 = canonical_edge(1, 0, 3)
        assert e1 == e2

    def test_all_6_edges_distinct(self):
        edges = set()
        for s in range(6):
            edges.add(canonical_edge(0, 0, s))
        assert len(edges) == 6


# ---------------------------------------------------------------------------
# Adjacency
# ---------------------------------------------------------------------------

class TestAdjacency:
    def test_hex_neighbors_count(self):
        assert len(hex_neighbors(0, 0)) == 6

    def test_vertices_of_tile_count(self):
        assert len(vertices_of_tile(0, 0)) == 6

    def test_edges_of_tile_count(self):
        assert len(edges_of_tile(0, 0)) == 6

    def test_vertices_of_edge(self):
        ek = canonical_edge(0, 0, 0)
        verts = vertices_of_edge(ek)
        assert len(verts) == 2
        assert verts[0] != verts[1]

    def test_adjacent_vertices(self):
        """Each vertex should have 2 or 3 adjacent vertices."""
        vk = canonical_vertex(0, 0, 0)
        adj = adjacent_vertices(vk)
        assert 2 <= len(adj) <= 3

    def test_tiles_of_vertex(self):
        """A vertex touches up to 3 tiles."""
        vk = canonical_vertex(0, 0, 0)
        tiles = tiles_of_vertex(vk)
        assert len(tiles) == 3  # center vertex touches 3 hexes

    def test_edges_of_vertex(self):
        """A vertex has 3 adjacent edges."""
        vk = canonical_vertex(0, 0, 0)
        edges = edges_of_vertex(vk)
        assert len(edges) == 3


# ---------------------------------------------------------------------------
# Valid vertices / edges on map
# ---------------------------------------------------------------------------

class TestValidPositions:
    def test_valid_vertices_nonempty(self, small_map):
        vv = valid_vertices(small_map)
        assert len(vv) > 0
        # 7 hex center+ring: interior vertex count
        # Each hex has 6 corners; with sharing, 7 hexes produce 18 unique vertices on land
        # (may vary — just sanity check)
        assert len(vv) >= 18

    def test_valid_edges_nonempty(self, small_map):
        ve = valid_edges(small_map)
        assert len(ve) > 0


# ---------------------------------------------------------------------------
# Placement validation
# ---------------------------------------------------------------------------

class TestCanPlaceSettlement:
    def test_valid_empty_vertex_setup(self):
        game = make_game(phase="setup_forward" if False else None)
        # Use playing phase but test with setup=True
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_place_settlement(vk, "p0", game, setup_phase=True)
        assert ok, msg

    def test_occupied_vertex_rejected(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_place_settlement(vk, "p1", game, setup_phase=True)
        assert not ok
        assert "occupied" in msg.lower()

    def test_distance_rule(self):
        """Cannot place settlement adjacent to another settlement."""
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        # Adjacent vertex
        adj = adjacent_vertices(canonical_vertex(0, -1, 0))
        for av in adj:
            ok, msg = can_place_settlement(av, "p1", game, setup_phase=True)
            assert not ok, f"Should fail distance rule at {av}"
            assert "distance" in msg.lower() or "close" in msg.lower()

    def test_must_connect_to_road_outside_setup(self):
        """Non-setup settlement must connect to player's road."""
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_place_settlement(vk, "p0", game, setup_phase=False)
        assert not ok
        assert "road" in msg.lower()

    def test_connected_to_road_ok(self):
        """Settlement adjacent to own road is valid."""
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        # Place a road on an edge adjacent to this vertex
        adj_edges = edges_of_vertex(vk)
        place_road(game, "p0", adj_edges[0][0], adj_edges[0][1], adj_edges[0][2])
        ok, msg = can_place_settlement(vk, "p0", game, setup_phase=False)
        assert ok, msg


class TestCanPlaceRoad:
    def test_valid_setup_road(self):
        game = make_game()
        # Place settlement first
        vk = canonical_vertex(0, -1, 0)
        place_settlement(game, "p0", 0, -1, 0)
        # Road must connect to settlement — pick a valid land edge
        adj_edges = valid_edge_of_vertex(vk, game.map_data)
        assert len(adj_edges) > 0
        ek = adj_edges[0]
        ok, msg = can_place_road(ek, "p0", game, setup_phase=True, setup_settlement_vk=vk)
        assert ok, msg

    def test_setup_road_must_touch_settlement(self):
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        place_settlement(game, "p0", 0, -1, 0)
        # Pick an edge NOT adjacent to the settlement
        far_vk = canonical_vertex(0, 1, 3)
        far_edges = edges_of_vertex(far_vk)
        ek = far_edges[0]
        ok, msg = can_place_road(ek, "p0", game, setup_phase=True, setup_settlement_vk=vk)
        assert not ok

    def test_occupied_edge_rejected(self):
        game = make_game()
        place_road(game, "p0", 0, -1, 0)
        ek = canonical_edge(0, -1, 0)
        ok, msg = can_place_road(ek, "p1", game)
        assert not ok
        assert "occupied" in msg.lower()

    def test_road_must_connect_to_network(self):
        """Non-setup road must connect to existing road or settlement."""
        game = make_game()
        ek = canonical_edge(0, 1, 3)
        ok, msg = can_place_road(ek, "p0", game)
        assert not ok
        assert "connect" in msg.lower()


class TestCanUpgradeCity:
    def test_upgrade_own_settlement(self):
        game = make_game()
        place_settlement(game, "p0", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_upgrade_city(vk, "p0", game)
        assert ok, msg

    def test_cannot_upgrade_opponent(self):
        game = make_game()
        place_settlement(game, "p1", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_upgrade_city(vk, "p0", game)
        assert not ok

    def test_cannot_upgrade_empty(self):
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_upgrade_city(vk, "p0", game)
        assert not ok

    def test_cannot_upgrade_city_again(self):
        from tests.conftest import place_city
        game = make_game()
        place_city(game, "p0", 0, -1, 0)
        vk = canonical_vertex(0, -1, 0)
        ok, msg = can_upgrade_city(vk, "p0", game)
        assert not ok
        assert "already" in msg.lower()
