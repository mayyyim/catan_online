"""Tests for longest road calculation."""

import pytest
from app.game.board import canonical_edge, canonical_vertex, edges_of_vertex
from app.game.road_stats import longest_road_length_for_player, recompute_longest_road
from tests.conftest import make_game, place_road, place_settlement


class TestLongestRoadLength:
    def test_no_roads(self):
        game = make_game()
        assert longest_road_length_for_player(game, "p0") == 0

    def test_single_road(self):
        game = make_game()
        place_road(game, "p0", 0, -1, 0)
        assert longest_road_length_for_player(game, "p0") == 1

    def test_chain_of_three(self):
        """Three connected roads in a line = length 3."""
        game = make_game()
        # Place 3 connected roads along the top edge of tile (0,-1)
        # edge 0 → edge vertices → pick adjacent edge → continue
        vk = canonical_vertex(0, -1, 0)
        adj_edges = edges_of_vertex(vk)
        # Place first two edges meeting at vk
        e1, e2 = adj_edges[0], adj_edges[1]
        place_road(game, "p0", e1[0], e1[1], e1[2])
        place_road(game, "p0", e2[0], e2[1], e2[2])
        assert longest_road_length_for_player(game, "p0") == 2

        # Extend from e2 — find another edge connected to e2 but not through vk
        from app.game.board import vertices_of_edge
        v2a, v2b = vertices_of_edge(e2)
        extend_vertex = v2b if v2a == vk else v2a
        ext_edges = edges_of_vertex(extend_vertex)
        e3 = [e for e in ext_edges if e != e2 and e != e1][0]
        place_road(game, "p0", e3[0], e3[1], e3[2])
        assert longest_road_length_for_player(game, "p0") == 3

    def test_opponent_building_cuts_road(self):
        """An opponent settlement on a shared vertex severs road continuity."""
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        adj_edges = edges_of_vertex(vk)
        e1, e2 = adj_edges[0], adj_edges[1]
        place_road(game, "p0", e1[0], e1[1], e1[2])
        place_road(game, "p0", e2[0], e2[1], e2[2])
        # Without opponent building: continuous = 2
        assert longest_road_length_for_player(game, "p0") == 2

        # Place opponent settlement at the junction vertex
        place_settlement(game, "p1", vk[0], vk[1], vk[2])
        # Now road is severed: each segment is length 1
        assert longest_road_length_for_player(game, "p0") == 1

    def test_own_building_does_not_cut(self):
        """Own settlement at a junction does NOT sever road."""
        game = make_game()
        vk = canonical_vertex(0, -1, 0)
        adj_edges = edges_of_vertex(vk)
        e1, e2 = adj_edges[0], adj_edges[1]
        place_road(game, "p0", e1[0], e1[1], e1[2])
        place_road(game, "p0", e2[0], e2[1], e2[2])
        place_settlement(game, "p0", vk[0], vk[1], vk[2])
        assert longest_road_length_for_player(game, "p0") == 2


class TestRecomputeLongestRoad:
    def test_no_holder_below_5(self):
        game = make_game()
        # Place 4 roads for p0 — below threshold
        vk = canonical_vertex(0, -1, 0)
        edges = edges_of_vertex(vk)
        for e in edges[:2]:
            place_road(game, "p0", e[0], e[1], e[2])
        recompute_longest_road(game)
        assert game.longest_road_holder is None

    def test_holder_at_5(self):
        """Build 5 connected roads for p0 → should claim longest road."""
        game = make_game()
        # Build a chain of 5 roads by walking along edges
        from app.game.board import vertices_of_edge
        # Start at an edge of tile (0,-1)
        current_edge = canonical_edge(0, -1, 0)
        placed_edges = set()

        place_road(game, "p0", current_edge[0], current_edge[1], current_edge[2])
        placed_edges.add(current_edge)

        for _ in range(4):
            # Walk to next edge
            v1, v2 = vertices_of_edge(current_edge)
            found = False
            for v in [v2, v1]:
                for e in edges_of_vertex(v):
                    if e not in placed_edges:
                        # Check it's on a valid land tile (in our small map)
                        place_road(game, "p0", e[0], e[1], e[2])
                        placed_edges.add(e)
                        current_edge = e
                        found = True
                        break
                if found:
                    break

        assert longest_road_length_for_player(game, "p0") >= 5
        recompute_longest_road(game)
        assert game.longest_road_holder == "p0"

    def test_tie_keeps_current_holder(self):
        """On tie, current holder retains longest road.

        We build 5 connected roads for each player and verify the
        pre-existing holder keeps the title.
        """
        game = make_game()
        game.longest_road_holder = "p0"
        game.longest_road_length = 5

        # Build 5-road chains for both players using walk strategy
        from app.game.board import vertices_of_edge, valid_edges
        ve = valid_edges(game.map_data)

        for pid in ["p0", "p1"]:
            # Find a starting edge
            placed = set()
            # Use different starting tiles for each player
            start_side = 0 if pid == "p0" else 3
            start_edge = canonical_edge(0, -1, start_side)
            if start_edge not in ve:
                start_edge = canonical_edge(0, 1, start_side)

            place_road(game, pid, start_edge[0], start_edge[1], start_edge[2])
            placed.add(start_edge)
            current = start_edge

            for _ in range(4):
                v1, v2 = vertices_of_edge(current)
                found = False
                for v in [v2, v1]:
                    for e in edges_of_vertex(v):
                        if e not in placed and e in ve and f"{e[0]},{e[1]},{e[2]}" not in game.edges:
                            place_road(game, pid, e[0], e[1], e[2])
                            placed.add(e)
                            current = e
                            found = True
                            break
                    if found:
                        break

        recompute_longest_road(game)
        # Both should have 5; p0 was holder → keeps it
        assert game.longest_road_holder == "p0"
