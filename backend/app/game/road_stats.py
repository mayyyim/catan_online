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
    Brute-force DFS over edges is fine (<= 15 roads).
    """
    edge_keys = _player_edge_keys(game, player_id)
    if not edge_keys:
        return 0

    # Build adjacency: edge -> neighboring edges that share a vertex.
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

    neighbors: Dict[str, Set[str]] = {ekey: set() for ekey in edge_keys}
    for ekey, (a, b) in edge_vertices.items():
        neighbors[ekey].update(vertex_to_edges.get(a, set()))
        neighbors[ekey].update(vertex_to_edges.get(b, set()))
        neighbors[ekey].discard(ekey)

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
    best_len = 0
    best_pid = None
    for p in game.players:
        length = longest_road_length_for_player(game, p.player_id)
        p.longest_road = length
        if length > best_len:
            best_len = length
            best_pid = p.player_id

    game.longest_road_length = best_len
    game.longest_road_player_id = best_pid

