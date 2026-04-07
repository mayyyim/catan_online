"""
Catan game engine — handles all game actions and state transitions.
"""

import random
from typing import Dict, List, Optional, Tuple

from app.game.models import (
    GameState, GamePhase, TurnStep, Player, PlacedPiece,
    PieceType, Resource, TileType, TILE_RESOURCE,
    BUILD_COST, VP_TABLE, WINNING_VP,
    MapData,
)
from app.game.board import (
    canonical_vertex, canonical_edge,
    vertices_of_tile, edges_of_vertex,
    can_place_settlement, can_place_road, can_upgrade_city,
)


PLAYER_COLORS = ["red", "blue", "green", "orange"]


# ---------------------------------------------------------------------------
# Dice
# ---------------------------------------------------------------------------

def roll_dice() -> Tuple[List[int], int]:
    d1 = random.randint(1, 6)
    d2 = random.randint(1, 6)
    return [d1, d2], d1 + d2


# ---------------------------------------------------------------------------
# Resource production
# ---------------------------------------------------------------------------

def produce_resources(game: GameState, roll: int):
    """Distribute resources to all players based on dice roll."""
    if roll == 7:
        return  # robber — handled separately

    for tile in game.map_data.tiles:
        if tile.token != roll:
            continue
        # Skip if robber is here
        if (tile.q, tile.r) == (game.robber_q, game.robber_r):
            continue
        resource = TILE_RESOURCE.get(tile.tile_type)
        if not resource:
            continue

        for vk in vertices_of_tile(tile.q, tile.r):
            vkey = f"{vk[0]},{vk[1]},{vk[2]}"
            piece = game.vertices.get(vkey)
            if not piece:
                continue
            player = game.player_by_id(piece.player_id)
            if not player:
                continue
            amount = 2 if piece.piece_type == PieceType.CITY else 1
            player.add_resource(resource, amount)


def move_robber_random(game: GameState):
    """Move robber to a random non-desert land tile (not current position)."""
    candidates = [
        (t.q, t.r) for t in game.map_data.tiles
        if t.tile_type != TileType.OCEAN
        and (t.q, t.r) != (game.robber_q, game.robber_r)
    ]
    if candidates:
        game.robber_q, game.robber_r = random.choice(candidates)


# ---------------------------------------------------------------------------
# Setup phase helpers
# ---------------------------------------------------------------------------

def setup_order_for_players(n: int) -> List[int]:
    """Snake draft order with randomized opening: [p0,p1,...,pN,pN,...,p1,p0]."""
    fwd = list(range(n))
    random.shuffle(fwd)
    return fwd + fwd[::-1]


# ---------------------------------------------------------------------------
# Victory point calculation
# ---------------------------------------------------------------------------

def recalculate_vp(game: GameState):
    for player in game.players:
        vp = 0
        for piece in game.vertices.values():
            if piece.player_id == player.player_id:
                vp += VP_TABLE[piece.piece_type]
        player.victory_points = vp


def check_winner(game: GameState) -> Optional[str]:
    for player in game.players:
        if player.victory_points >= WINNING_VP:
            return player.player_id
    return None


# ---------------------------------------------------------------------------
# Main action handlers — called by WebSocket message router
# ---------------------------------------------------------------------------

class ActionError(Exception):
    pass


def handle_start_game(game: GameState, map_data: MapData, requesting_player_id: str):
    """Start the game: set map, initialize turn order, enter setup phase."""
    if game.phase != GamePhase.WAITING:
        raise ActionError("Game already started")
    if len(game.players) < 2:
        raise ActionError("Need at least 2 players to start")

    game.map_data = map_data
    game.phase = GamePhase.SETUP_FORWARD
    game.turn_step = TurnStep.PRE_ROLL  # setup doesn't use dice but keeps pre_roll as "action needed"

    # Set robber on desert tile
    for tile in map_data.tiles:
        if tile.tile_type == TileType.DESERT:
            game.robber_q = tile.q
            game.robber_r = tile.r
            break

    # Build snake draft order
    game.setup_order = setup_order_for_players(len(game.players))
    game.setup_step = 0
    game.current_player_index = game.setup_order[0]


def handle_roll_dice(game: GameState, player_id: str) -> Dict:
    """Player rolls dice — produces resources or triggers robber."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.turn_step != TurnStep.PRE_ROLL:
        raise ActionError("Already rolled this turn")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    values, total = roll_dice()
    game.last_dice = values

    if total == 7:
        move_robber_random(game)
    else:
        produce_resources(game, total)

    game.turn_step = TurnStep.POST_ROLL
    return {"values": values, "total": total}


def handle_build(
    game: GameState,
    player_id: str,
    piece: str,
    position: Dict,
) -> Dict:
    """Place road / settlement / city."""
    player = game.player_by_id(player_id)
    if not player:
        raise ActionError("Player not found")

    q = position.get("q", 0)
    r = position.get("r", 0)
    direction = position.get("direction", 0)

    is_setup = game.phase in (GamePhase.SETUP_FORWARD, GamePhase.SETUP_BACKWARD)

    # Determine whose turn it is
    if is_setup:
        current_idx = game.setup_order[game.setup_step // 2]  # each player places settlement then road
        current_pid = game.players[current_idx].player_id
        if player_id != current_pid:
            raise ActionError("Not your turn in setup")

        # Enforce setup action order: settlement then road (per player, snake draft).
        # setup_step is incremented after each placement:
        #   even  -> settlement
        #   odd   -> road
        normalized = piece.value if isinstance(piece, PieceType) else str(piece)
        expected = "settlement" if (game.setup_step % 2 == 0) else "road"
        if normalized != expected:
            raise ActionError(f"Setup requires placing a {expected} now")
    else:
        if game.phase != GamePhase.PLAYING:
            raise ActionError("Game not in playing phase")
        if game.turn_step != TurnStep.POST_ROLL:
            raise ActionError("Must roll dice first")
        if game.current_player().player_id != player_id:
            raise ActionError("Not your turn")

    if piece == PieceType.SETTLEMENT or piece == "settlement":
        vk = canonical_vertex(q, r, direction)
        vkey = f"{vk[0]},{vk[1]},{vk[2]}"

        ok, msg = can_place_settlement(vk, player_id, game, setup_phase=is_setup)
        if not ok:
            raise ActionError(msg)

        if not is_setup:
            cost = BUILD_COST[PieceType.SETTLEMENT]
            if not player.has_resources(cost):
                raise ActionError("Not enough resources")
            player.deduct(cost)

        game.vertices[vkey] = PlacedPiece(PieceType.SETTLEMENT, player_id)
        player.settlements_placed += 1

        # During setup: remember this settlement for road adjacency check
        if is_setup:
            player.setup_settlements.append(vk)
            # setup_step: even = settlement, odd = road
            game.setup_step += 1
            _check_setup_advance(game)

        recalculate_vp(game)
        return {"placed": "settlement", "vk": vkey}

    elif piece == PieceType.ROAD or piece == "road":
        ek = canonical_edge(q, r, direction)
        ekey = f"{ek[0]},{ek[1]},{ek[2]}"

        # In setup, road must connect to last placed settlement
        setup_settlement_vk = None
        if is_setup:
            # find player's last placed settlement
            if player.setup_settlements:
                setup_settlement_vk = player.setup_settlements[-1]

        ok, msg = can_place_road(ek, player_id, game, setup_phase=is_setup, setup_settlement_vk=setup_settlement_vk)
        if not ok:
            raise ActionError(msg)

        if not is_setup:
            cost = BUILD_COST[PieceType.ROAD]
            if not player.has_resources(cost):
                raise ActionError("Not enough resources")
            player.deduct(cost)

        game.edges[ekey] = PlacedPiece(PieceType.ROAD, player_id)
        player.roads_placed += 1

        if is_setup:
            was_backward = (game.phase == GamePhase.SETUP_BACKWARD)
            game.setup_step += 1
            _check_setup_advance(game)

            # Second round: give initial resources when road is placed (capture phase before advance)
            _maybe_grant_setup_resources(game, player, is_second_round=was_backward)

        return {"placed": "road", "ek": ekey}

    elif piece == PieceType.CITY or piece == "city":
        vk = canonical_vertex(q, r, direction)
        ok, msg = can_upgrade_city(vk, player_id, game)
        if not ok:
            raise ActionError(msg)

        cost = BUILD_COST[PieceType.CITY]
        if not player.has_resources(cost):
            raise ActionError("Not enough resources")
        player.deduct(cost)

        vkey = f"{vk[0]},{vk[1]},{vk[2]}"
        game.vertices[vkey] = PlacedPiece(PieceType.CITY, player_id)
        player.cities_placed += 1
        player.settlements_placed -= 1

        recalculate_vp(game)
        return {"placed": "city", "vk": vkey}

    else:
        raise ActionError(f"Unknown piece type: {piece}")


def _check_setup_advance(game: GameState):
    """After each setup placement, advance to next player or switch to playing."""
    total_placements = len(game.players) * 2 * 2  # 2 settlements + 2 roads per player

    if game.setup_step >= total_placements:
        # All setup done — switch to playing
        game.phase = GamePhase.PLAYING
        game.current_player_index = 0
        game.turn_step = TurnStep.PRE_ROLL
        return

    # setup_step // 2 = which turn in draft order
    turn_in_order = game.setup_step // 2
    total_turns = len(game.players) * 2  # forward + backward

    if turn_in_order < len(game.players):
        game.phase = GamePhase.SETUP_FORWARD
    else:
        game.phase = GamePhase.SETUP_BACKWARD

    if turn_in_order < total_turns:
        game.current_player_index = game.setup_order[turn_in_order]


def _maybe_grant_setup_resources(game: GameState, player: Player, is_second_round: bool):
    """In the second setup round, each settlement grants 1 of each adjacent resource."""
    if not is_second_round:
        return
    # Grant resources for the last placed settlement (last in setup_settlements)
    if not player.setup_settlements:
        return
    last_settlement = player.setup_settlements[-1]
    for tile in game.map_data.tiles:
        # check if tile is adjacent to this vertex
        verts = vertices_of_tile(tile.q, tile.r)
        if last_settlement in verts:
            res = TILE_RESOURCE.get(tile.tile_type)
            if res:
                player.add_resource(res, 1)


def handle_end_turn(game: GameState, player_id: str):
    """End current player's turn and advance to next."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")
    if game.turn_step == TurnStep.PRE_ROLL:
        raise ActionError("Must roll dice before ending turn")

    # Check for winner
    recalculate_vp(game)
    winner = check_winner(game)
    if winner:
        game.winner_id = winner
        game.phase = GamePhase.FINISHED
        return

    # Advance to next player
    game.current_player_index = (game.current_player_index + 1) % len(game.players)
    game.turn_step = TurnStep.PRE_ROLL
    game.last_dice = None


def handle_trade(game: GameState, player_id: str, offer: Dict, want: Dict) -> Dict:
    """Bank trade (4:1, 3:1, 2:1 based on ports)."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.turn_step != TurnStep.POST_ROLL:
        raise ActionError("Must roll before trading")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    player = game.player_by_id(player_id)

    # Determine best trade ratio for each resource.
    # A player can use a port if they have a settlement/city on either of the
    # two vertices that border the port's coastal edge.
    port_ratios: Dict[Optional[Resource], int] = {}
    for port in game.map_data.ports:
        if port.side is not None:
            # Exact check: only the two vertices of the coastal edge.
            port_corners = (port.side, (port.side + 1) % 6)
        else:
            # Fallback: any corner of the tile (legacy data without side).
            port_corners = range(6)
        for corner in port_corners:
            cvk = canonical_vertex(port.q, port.r, corner)
            ckey = f"{cvk[0]},{cvk[1]},{cvk[2]}"
            piece = game.vertices.get(ckey)
            if piece and piece.player_id == player_id:
                if port.resource is None:
                    port_ratios[None] = min(port_ratios.get(None, 3), port.ratio)
                else:
                    port_ratios[port.resource] = min(port_ratios.get(port.resource, 4), port.ratio)

    generic_ratio = port_ratios.get(None, 4)

    # Parse offer / want
    offer_res = {Resource(k): v for k, v in offer.items() if v > 0}
    want_res = {Resource(k): v for k, v in want.items() if v > 0}

    if not offer_res or not want_res:
        raise ActionError("Trade must have at least one resource on each side")

    # Check player has offered resources
    for res, amt in offer_res.items():
        if player.resources.get(res, 0) < amt:
            raise ActionError(f"Not enough {res.value}")

    # Validate ratio: sum(offer) / sum(want) must meet ratio requirements
    # We check each offered resource individually
    for res, amt in offer_res.items():
        ratio = port_ratios.get(res, generic_ratio)
        want_total = sum(want_res.values())
        offer_total = amt  # simplified: treat each resource separately
        if offer_total < ratio:
            raise ActionError(f"Need {ratio} {res.value} to trade")

    # Execute trade
    for res, amt in offer_res.items():
        player.resources[res] -= amt
    for res, amt in want_res.items():
        player.add_resource(res, amt)

    return {"traded": True}
