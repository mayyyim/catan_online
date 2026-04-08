from __future__ import annotations

from typing import Dict, List, Set, Tuple

from app.game.board import vertices_of_edge
from app.game.models import GameState


def _player_edge_keys(game: GameState, player_id: str) -> List[str]:
    return [ekey for ekey, piece in game.edges.items() if piece.player_id == player_id]


def _edge_key_to_edge(ekey: str) -> Tuple[int, int, int]:
    q, r, side = ekey.split(",")
    return int(q), int(r), int(side)


def longest_road_length_for_player(game: GameState, player_id: str) -> int:
    """
    Compute longest continuous road length for a player.
    Brute-force DFS over edges (≤15 roads per player).
    Opponent settlements on shared vertices break road continuity.
    """
    edge_keys = _player_edge_keys(game, player_id)
    if not edge_keys:
        return 0

    # Map each edge to its two endpoint vertex keys
    edge_vertices: Dict[str, Tuple[str, str]] = {}
    vertex_to_edges: Dict[str, Set[str]] = {}

    for ekey in edge_keys:
        ek = _edge_key_to_edge(ekey)
        v1, v2 = vertices_of_edge(ek)
        v1k = f"{v1[0]},{v1[1]},{v1[2]}"
        v2k = f"{v2[0]},{v2[1]},{v2[2]}"
        edge_vertices[ekey] = (v1k, v2k)
        vertex_to_edges.setdefault(v1k, set()).add(ekey)
        vertex_to_edges.setdefault(v2k, set()).add(ekey)

    # Build adjacency graph.
    # Two edges are neighbors only if their shared vertex is NOT occupied by an opponent.
    neighbors: Dict[str, Set[str]] = {ekey: set() for ekey in edge_keys}
    for vkey, edges_at_v in vertex_to_edges.items():
        piece = game.vertices.get(vkey)
        if piece and piece.player_id != player_id:
            # Opponent's building severs road continuity at this vertex
            continue
        for e1 in edges_at_v:
            for e2 in edges_at_v:
                if e1 != e2:
                    neighbors[e1].add(e2)

    best = 0

    def dfs(cur: str, used: Set[str]) -> None:
        nonlocal best
        best = max(best, len(used))
        for nxt in neighbors[cur]:
            if nxt in used:
                continue
            used.add(nxt)
            dfs(nxt, used)
            used.remove(nxt)

    for start in edge_keys:
        dfs(start, {start})

    return best


def recompute_longest_road(game: GameState) -> None:
    """
    Recompute longest road for all players and update the game-level holder.
    The holder must have ≥5 roads. In case of a tie, the current holder keeps it.
    """
    for p in game.players:
        p.longest_road = longest_road_length_for_player(game, p.player_id)

    # Determine new best length (ignoring current holder for initial comparison)
    best_len = max((p.longest_road for p in game.players), default=0)

    if best_len < 5:
        game.longest_road_holder = None
        game.longest_road_length = best_len
        return

    # Find who has the best length; current holder keeps title on tie
    new_holder = game.longest_road_holder
    current_holder_len = 0
    if game.longest_road_holder:
        for p in game.players:
            if p.player_id == game.longest_road_holder:
                current_holder_len = p.longest_road
                break

    if best_len > current_holder_len:
        # Someone beat the current holder — find who (first match wins)
        for p in game.players:
            if p.longest_road == best_len and p.player_id != game.longest_road_holder:
                new_holder = p.player_id
                break

    game.longest_road_holder = new_holder
    game.longest_road_length = best_len
