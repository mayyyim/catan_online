"""
Shared test fixtures for Catan backend tests.

Provides a deterministic 7-hex map (1 center + 6 ring) and factory functions
to quickly create game states at various phases.
"""

import sys
import os
import pytest
from typing import Dict, List, Optional

# Ensure `app` package is importable without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.game.models import (
    GameState, GamePhase, TurnStep, Player, MapData, Tile, Port,
    TileType, Resource, PlacedPiece, PieceType, DevCard, DevCardType,
    GameRules,
)
from app.game.board import canonical_vertex, canonical_edge


# ---------------------------------------------------------------------------
# Small deterministic map: 7 hexes (center + ring of 6)
#
# Layout (axial coords):
#        (0,-1)  (1,-1)
#    (-1,0)  (0,0)  (1,0)
#        (-1,1)  (0,1)
#
# Center (0,0) = DESERT (robber starts here)
# Ring: forest, hills, fields, pasture, mountains, fields
# Tokens assigned for deterministic production testing
# ---------------------------------------------------------------------------

SMALL_MAP_TILES = [
    Tile(0, 0, TileType.DESERT, token=None),
    Tile(0, -1, TileType.FOREST, token=6),     # wood
    Tile(1, -1, TileType.HILLS, token=8),       # brick
    Tile(1, 0, TileType.FIELDS, token=5),       # wheat
    Tile(0, 1, TileType.PASTURE, token=9),      # sheep
    Tile(-1, 1, TileType.MOUNTAINS, token=10),  # ore
    Tile(-1, 0, TileType.FIELDS, token=4),      # wheat
]

SMALL_MAP_PORTS = [
    # One 3:1 generic port on tile (0,-1) side 0
    Port(0, -1, resource=None, ratio=3, side=0),
    # One 2:1 wood port on tile (-1,0) side 3
    Port(-1, 0, resource=Resource.WOOD, ratio=2, side=3),
]


@pytest.fixture
def small_map() -> MapData:
    """7-hex test map with known tile types/tokens."""
    return MapData(
        map_id="test_small",
        tiles=list(SMALL_MAP_TILES),
        ports=list(SMALL_MAP_PORTS),
    )


def make_players(n: int = 2) -> List[Player]:
    """Create n players with default resources."""
    colors = ["red", "blue", "green", "orange"]
    return [
        Player(
            player_id=f"p{i}",
            name=f"Player{i}",
            color=colors[i % 4],
        )
        for i in range(n)
    ]


@pytest.fixture
def two_players() -> List[Player]:
    return make_players(2)


@pytest.fixture
def four_players() -> List[Player]:
    return make_players(4)


def make_game(
    n_players: int = 2,
    phase: GamePhase = GamePhase.PLAYING,
    turn_step: TurnStep = TurnStep.POST_ROLL,
    current_player: int = 0,
    map_data: Optional[MapData] = None,
    resources: Optional[Dict[str, Dict[Resource, int]]] = None,
) -> GameState:
    """Create a GameState at a given phase with optional resource overrides.

    Args:
        n_players: Number of players.
        phase: Game phase.
        turn_step: Current turn step.
        current_player: Index of current player.
        map_data: Map to use (defaults to small 7-hex map).
        resources: Dict of player_id -> {Resource: amount} overrides.
    """
    players = make_players(n_players)
    if map_data is None:
        map_data = MapData(
            map_id="test_small",
            tiles=list(SMALL_MAP_TILES),
            ports=list(SMALL_MAP_PORTS),
        )

    game = GameState(
        room_id="test_room",
        map_data=map_data,
        players=players,
        phase=phase,
        turn_step=turn_step,
        current_player_index=current_player,
    )

    # Place robber on desert
    for tile in map_data.tiles:
        if tile.tile_type == TileType.DESERT:
            game.robber_q = tile.q
            game.robber_r = tile.r
            break

    # Apply resource overrides
    if resources:
        for pid, res_map in resources.items():
            player = game.player_by_id(pid)
            if player:
                for res, amt in res_map.items():
                    player.resources[res] = amt

    return game


@pytest.fixture
def playing_game() -> GameState:
    """A 2-player game in PLAYING/POST_ROLL phase, ready for builds/trades."""
    return make_game()


@pytest.fixture
def rich_game() -> GameState:
    """A 2-player game where both players have plenty of resources."""
    return make_game(resources={
        "p0": {r: 10 for r in Resource},
        "p1": {r: 10 for r in Resource},
    })


def place_settlement(game: GameState, player_id: str, q: int, r: int, corner: int):
    """Directly place a settlement on the board (bypasses rules)."""
    vk = canonical_vertex(q, r, corner)
    vkey = f"{vk[0]},{vk[1]},{vk[2]}"
    game.vertices[vkey] = PlacedPiece(PieceType.SETTLEMENT, player_id)
    player = game.player_by_id(player_id)
    if player:
        player.settlements_placed += 1


def place_city(game: GameState, player_id: str, q: int, r: int, corner: int):
    """Directly place a city on the board (bypasses rules)."""
    vk = canonical_vertex(q, r, corner)
    vkey = f"{vk[0]},{vk[1]},{vk[2]}"
    game.vertices[vkey] = PlacedPiece(PieceType.CITY, player_id)
    player = game.player_by_id(player_id)
    if player:
        player.cities_placed += 1


def place_road(game: GameState, player_id: str, q: int, r: int, side: int):
    """Directly place a road on the board (bypasses rules)."""
    ek = canonical_edge(q, r, side)
    ekey = f"{ek[0]},{ek[1]},{ek[2]}"
    game.edges[ekey] = PlacedPiece(PieceType.ROAD, player_id)
    player = game.player_by_id(player_id)
    if player:
        player.roads_placed += 1


def valid_edge_of_vertex(vk, map_data):
    """Return valid land edges adjacent to a vertex, filtering out off-map edges."""
    from app.game.board import edges_of_vertex, valid_edges
    ve = valid_edges(map_data)
    return [e for e in edges_of_vertex(vk) if e in ve]
