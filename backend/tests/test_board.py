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

    def test_vertices_of_edge_all_sides_are_geometric_endpoints(self):
        """Regression: earlier the (i, i+1) corner mapping was wrong for
        sides 1/2/4/5, which silently broke setup road adjacency. For every
        side of a tile, the edge's two endpoints must each be a vertex the
        neighboring tile on that side also sees — i.e. adjacency through the
        shared edge must round-trip.

        Uses EDGE_NEIGHBORS (geometric edge→neighbor mapping aligned with the
        frontend edge id convention where edge i is between corners i and
        (i+1)%6). HEX_DIRECTIONS is a separate port-side mapping and must
        NOT be used here.
        """
        from app.game.board import EDGE_NEIGHBORS
        for side in range(6):
            ek = canonical_edge(0, 0, side)
            verts = set(vertices_of_edge(ek))
            assert len(verts) == 2, f"side {side} should produce 2 distinct endpoints"
            # Each endpoint vertex must lie on the edge's adjacent tile too.
            dq, dr = EDGE_NEIGHBORS[side]
            neighbor_tile = (dq, dr)
            neighbor_verts = set(vertices_of_tile(*neighbor_tile))
            shared = verts & neighbor_verts
            assert len(shared) == 2, (
                f"side {side}: edge endpoints {verts} should both be shared "
                f"with neighbor tile {neighbor_tile}; got shared={shared}"
            )

    def test_vertices_of_edge_matches_frontend_visual_convention(self):
        """Frontend authority: HexGrid.tsx draws edge `i` between
        hexCorners[i] and hexCorners[(i+1)%6]. The backend's
        vertices_of_edge must return the canonical form of exactly those
        two corners so that a road placed on the clicked edge lines up
        geometrically with the settlement corner the player also clicked.
        """
        for side in range(6):
            ek = (0, 0, side)  # raw, uncanonicalized
            endpoints = vertices_of_edge(ek)
            expected = {
                canonical_vertex(0, 0, side),
                canonical_vertex(0, 0, (side + 1) % 6),
            }
            assert set(endpoints) == expected, (
                f"side {side}: vertices_of_edge returned {endpoints}, "
                f"expected corners {side} and {(side+1) % 6} "
                f"(-> canonical {expected})"
            )

    def test_canonical_edge_neighbor_round_trip_all_sides(self):
        """For every side of a tile, canonicalizing the edge from the tile
        itself and from the opposite tile (through EDGE_NEIGHBORS) must
        produce the same key. Otherwise two distinct clicks on the same
        physical edge canonicalize to different keys and the engine treats
        them as two edges.
        """
        from app.game.board import EDGE_NEIGHBORS
        for side in range(6):
            dq, dr = EDGE_NEIGHBORS[side]
            other_side = (side + 3) % 6
            e_from_a = canonical_edge(0, 0, side)
            e_from_b = canonical_edge(dq, dr, other_side)
            assert e_from_a == e_from_b, (
                f"side {side}: canonical_edge mismatch — "
                f"from (0,0) = {e_from_a}, from neighbor ({dq},{dr}) "
                f"side {other_side} = {e_from_b}"
            )

    def test_setup_road_adjacency_all_sides(self):
        """For each of the 6 sides of a tile, placing a settlement at one of
        its endpoints and a road on that edge must be accepted as a valid
        setup placement (the road must connect to the settlement).

        This covers the setup-phase bug where after the settlement placement
        the subsequent road on a geometrically adjacent edge was rejected
        because vertices_of_edge returned wrong endpoints for sides 1/2/4/5.
        """
        from app.game.board import EDGE_NEIGHBORS
        for side in range(6):
            # Use a tile (0, -1) whose all 6 corners are land vertices on
            # the 7-hex test map.
            base_q, base_r = 0, -1
            # The neighbor through this edge must also be a land tile
            # (otherwise the edge might not be on the valid-edge set).
            dq, dr = EDGE_NEIGHBORS[side]
            neighbor = (base_q + dq, base_r + dr)
            land_tiles = {(0, 0), (0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)}
            if neighbor not in land_tiles:
                continue  # skip map-border edges

            game = make_game()
            # Place settlement at corner `side` of the base tile — this
            # corner is one of the endpoints of edge `side`.
            place_settlement(game, "p0", base_q, base_r, side)
            settlement_vk = canonical_vertex(base_q, base_r, side)

            # Now validate placing a road on that edge.
            ek = canonical_edge(base_q, base_r, side)
            ok, msg = can_place_road(
                ek, "p0", game,
                setup_phase=True, setup_settlement_vk=settlement_vk,
            )
            assert ok, (
                f"side {side}: road on canonical_edge{(base_q, base_r, side)} "
                f"should be valid (settlement is at corner {side}). "
                f"can_place_road said: {msg}"
            )

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
