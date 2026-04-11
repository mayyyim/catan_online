"""
Catan game engine — handles all game actions and state transitions.
"""

import random
import uuid
from typing import Dict, List, Optional, Tuple

from app.game.models import (
    GameState, GamePhase, TurnStep, Player, PlacedPiece,
    PieceType, Resource, TileType, TILE_RESOURCE,
    BUILD_COST, VP_TABLE, WINNING_VP,
    MAX_ROADS, MAX_SETTLEMENTS, MAX_CITIES,
    MapData, DevCard, DevCardType, DEV_CARD_COST,
    GameRules,
)
from app.game.board import (
    canonical_vertex, canonical_edge,
    vertices_of_tile, edges_of_vertex, vertices_of_edge,
    can_place_settlement, can_place_road, can_upgrade_city,
)
from app.game.road_stats import recompute_longest_road


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

def produce_resources(game: GameState, roll: int) -> Dict[str, Dict[str, int]]:
    """Distribute resources to all players based on dice roll.

    Returns ``{player_id: {resource_name: amount}}`` production log.
    """
    if roll == 7:
        return {}  # robber — handled separately

    production: Dict[str, Dict[str, int]] = {}

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

            pid = piece.player_id
            if pid not in production:
                production[pid] = {}
            production[pid][resource.value] = production[pid].get(resource.value, 0) + amount

    return production


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
# Development card deck
# ---------------------------------------------------------------------------

def create_dev_card_deck() -> list:
    """Create and shuffle a standard 25-card development deck."""
    deck: list = []
    for _ in range(14):
        deck.append(DevCard(card_type=DevCardType.KNIGHT))
    for _ in range(5):
        deck.append(DevCard(card_type=DevCardType.VICTORY_POINT))
    for _ in range(2):
        deck.append(DevCard(card_type=DevCardType.YEAR_OF_PLENTY))
    for _ in range(2):
        deck.append(DevCard(card_type=DevCardType.MONOPOLY))
    for _ in range(2):
        deck.append(DevCard(card_type=DevCardType.ROAD_BUILDING))
    random.shuffle(deck)
    return deck


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
    recompute_longest_road(game)
    for player in game.players:
        vp = 0
        for piece in game.vertices.values():
            if piece.player_id == player.player_id:
                vp += VP_TABLE[piece.piece_type]
        if (game.longest_road_holder == player.player_id
                and game.longest_road_length >= 5):
            vp += 2
        # VP from dev cards (auto-counted, not played manually)
        vp += sum(1 for c in player.dev_cards if c.card_type == DevCardType.VICTORY_POINT)
        # Largest army bonus
        if game.largest_army_holder == player.player_id:
            vp += 2
        player.victory_points = vp


def check_winner(game: GameState) -> Optional[str]:
    target = game.rules.victory_points_target
    for player in game.players:
        if player.victory_points >= target:
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

    # Initialize development card deck
    game.dev_card_deck = create_dev_card_deck()
    game.current_turn_number = 0

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
        # Friendly robber: if enabled and ALL players have < 4 VP,
        # auto-move robber to desert and skip the robber flow entirely.
        friendly = game.rules.friendly_robber
        all_below_threshold = all(p.victory_points < 4 for p in game.players)

        if friendly and all_below_threshold:
            # Move robber back to desert
            for tile in game.map_data.tiles:
                if tile.tile_type == TileType.DESERT:
                    game.robber_q = tile.q
                    game.robber_r = tile.r
                    break
            game.turn_step = TurnStep.POST_ROLL
        else:
            # Normal robber flow
            game.players_to_discard = [
                p.player_id
                for p in game.players
                if sum(p.resources.values()) > 7
            ]
            if game.players_to_discard:
                game.turn_step = TurnStep.ROBBER_DISCARD
            else:
                game.turn_step = TurnStep.ROBBER_PLACE
    else:
        production = produce_resources(game, total)
        game.turn_step = TurnStep.POST_ROLL

    return {"values": values, "total": total, "production": production if total != 7 else {}}


def handle_discard(game: GameState, player_id: str, resources: Dict) -> None:
    """Player discards half their cards when a 7 is rolled."""
    if game.turn_step != TurnStep.ROBBER_DISCARD:
        raise ActionError("No discard required right now")
    if player_id not in game.players_to_discard:
        raise ActionError("You don't need to discard")

    player = game.player_by_id(player_id)
    if not player:
        raise ActionError("Player not found")

    hand_size = sum(player.resources.values())
    required = hand_size // 2
    discard_res = {Resource(k): v for k, v in resources.items() if v > 0}
    discard_total = sum(discard_res.values())

    if discard_total != required:
        raise ActionError(f"Must discard exactly {required} cards (you have {hand_size})")

    for res, amt in discard_res.items():
        if player.resources.get(res, 0) < amt:
            raise ActionError(f"Not enough {res.value} to discard")
        player.resources[res] -= amt

    game.players_to_discard.remove(player_id)
    if not game.players_to_discard:
        game.turn_step = TurnStep.ROBBER_PLACE


def handle_place_robber(game: GameState, player_id: str, q: int, r: int) -> None:
    """Rolling player moves the robber to a chosen land tile."""
    if game.turn_step != TurnStep.ROBBER_PLACE:
        raise ActionError("Not time to place the robber")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    from app.game.models import TileType
    tile_coords = {(t.q, t.r) for t in game.map_data.tiles if t.tile_type != TileType.OCEAN}
    if (q, r) not in tile_coords:
        raise ActionError("Must place robber on a land tile")
    if (q, r) == (game.robber_q, game.robber_r):
        raise ActionError("Must move robber to a different tile")

    game.robber_q, game.robber_r = q, r

    # Find players (other than roller) with buildings adjacent to new robber hex
    from app.game.board import vertices_of_tile as _vot
    steal_targets: set = set()
    for vk in _vot(q, r):
        vkey = f"{vk[0]},{vk[1]},{vk[2]}"
        piece = game.vertices.get(vkey)
        if piece and piece.player_id != player_id:
            steal_targets.add(piece.player_id)

    game.robber_steal_targets = list(steal_targets)
    if game.robber_steal_targets:
        game.turn_step = TurnStep.ROBBER_STEAL
    else:
        game.turn_step = TurnStep.POST_ROLL


def handle_steal(game: GameState, player_id: str, target_id: str) -> Dict:
    """Rolling player steals one random resource from a target player."""
    if game.turn_step != TurnStep.ROBBER_STEAL:
        raise ActionError("Not time to steal")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")
    if target_id not in game.robber_steal_targets:
        raise ActionError("Invalid steal target")

    target = game.player_by_id(target_id)
    if not target:
        raise ActionError("Target player not found")

    available = [res for res, amt in target.resources.items() for _ in range(amt)]
    if not available:
        game.robber_steal_targets = []
        game.turn_step = TurnStep.POST_ROLL
        return {"stolen": None}

    import random
    stolen = random.choice(available)
    target.resources[stolen] -= 1
    game.player_by_id(player_id).add_resource(stolen, 1)

    game.robber_steal_targets = []
    game.turn_step = TurnStep.POST_ROLL
    return {"stolen": stolen.value}


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
        # Allow building roads during ROAD_BUILDING step, otherwise require POST_ROLL
        is_road_building = (game.turn_step == TurnStep.ROAD_BUILDING
                            and (piece == PieceType.ROAD or piece == "road"))
        if not is_road_building and game.turn_step != TurnStep.POST_ROLL:
            raise ActionError("Must roll dice first")
        if game.current_player().player_id != player_id:
            raise ActionError("Not your turn")

    if piece == PieceType.SETTLEMENT or piece == "settlement":
        if player.settlements_placed >= MAX_SETTLEMENTS:
            raise ActionError("No settlements remaining")

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
        if player.roads_placed >= MAX_ROADS:
            raise ActionError("No roads remaining")

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

        is_free_road = (not is_setup and game.turn_step == TurnStep.ROAD_BUILDING)
        if not is_setup and not is_free_road:
            cost = BUILD_COST[PieceType.ROAD]
            if not player.has_resources(cost):
                raise ActionError("Not enough resources")
            player.deduct(cost)

        game.edges[ekey] = PlacedPiece(PieceType.ROAD, player_id)
        player.roads_placed += 1

        if is_free_road:
            game.road_building_remaining -= 1
            if game.road_building_remaining <= 0:
                game.turn_step = TurnStep.POST_ROLL

        if not is_setup:
            recalculate_vp(game)

        if is_setup:
            was_backward = (game.phase == GamePhase.SETUP_BACKWARD)
            game.setup_step += 1
            _check_setup_advance(game)

            # Second round: give initial resources when road is placed (capture phase before advance)
            _maybe_grant_setup_resources(game, player, is_second_round=was_backward)

        return {"placed": "road", "ek": ekey}

    elif piece == PieceType.CITY or piece == "city":
        if player.cities_placed >= MAX_CITIES:
            raise ActionError("No cities remaining")

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
    """In the second setup round, each settlement grants 1 of each adjacent resource.

    If ``game.rules.starting_resources_double`` is True, grant 2x instead.
    """
    if not is_second_round:
        return
    # Grant resources for the last placed settlement (last in setup_settlements)
    if not player.setup_settlements:
        return
    amount = 2 if game.rules.starting_resources_double else 1
    last_settlement = player.setup_settlements[-1]
    for tile in game.map_data.tiles:
        # check if tile is adjacent to this vertex
        verts = vertices_of_tile(tile.q, tile.r)
        if last_settlement in verts:
            res = TILE_RESOURCE.get(tile.tile_type)
            if res:
                player.add_resource(res, amount)


def handle_end_turn(game: GameState, player_id: str):
    """End current player's turn and advance to next."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")
    if game.turn_step != TurnStep.POST_ROLL:
        raise ActionError("Must complete all actions before ending turn")

    # Check for winner
    recalculate_vp(game)
    winner = check_winner(game)
    if winner:
        game.winner_id = winner
        game.phase = GamePhase.FINISHED
        return

    # Clear any active trade proposal
    game.trade_proposal = None

    # Reset dev card state and advance turn
    cur = game.current_player()
    if cur:
        cur.dev_card_played_this_turn = False
    game.current_turn_number += 1

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

    # Validate each offered resource meets its ratio and is offered in exact multiples
    want_allowed = 0
    for res, amt in offer_res.items():
        ratio = port_ratios.get(res, generic_ratio)
        if amt % ratio != 0:
            raise ActionError(f"Must offer multiples of {ratio} {res.value}")
        want_allowed += amt // ratio

    want_total = sum(want_res.values())
    if want_total != want_allowed:
        raise ActionError(
            f"This trade allows exactly {want_allowed} resource(s) in return, not {want_total}"
        )

    # Execute trade
    for res, amt in offer_res.items():
        player.resources[res] -= amt
    for res, amt in want_res.items():
        player.add_resource(res, amt)

    return {"traded": True}


# ---------------------------------------------------------------------------
# P2P trade handlers
# ---------------------------------------------------------------------------

def handle_propose_trade(game: GameState, player_id: str, offer: Dict, want: Dict) -> Dict:
    """Active player proposes a trade to other players."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.turn_step != TurnStep.POST_ROLL:
        raise ActionError("Must roll before trading")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    player = game.player_by_id(player_id)
    if not player:
        raise ActionError("Player not found")

    offer_res = {Resource(k): v for k, v in offer.items() if v > 0}
    want_res = {Resource(k): v for k, v in want.items() if v > 0}

    if not offer_res or not want_res:
        raise ActionError("Trade must have at least one resource on each side")

    # Validate proposer has offered resources
    for res, amt in offer_res.items():
        if player.resources.get(res, 0) < amt:
            raise ActionError(f"Not enough {res.value}")

    # Auto-cancel any existing proposal
    proposal_id = uuid.uuid4().hex[:8]
    game.trade_proposal = {
        "id": proposal_id,
        "proposer_id": player_id,
        "offer": {k.value: v for k, v in offer_res.items()},
        "want": {k.value: v for k, v in want_res.items()},
        "rejected_by": [],
    }

    return game.trade_proposal


def handle_accept_trade(game: GameState, player_id: str, proposal_id: str) -> Dict:
    """Another player accepts the active trade proposal."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")

    if not game.trade_proposal:
        raise ActionError("No active trade proposal")
    if game.trade_proposal["id"] != proposal_id:
        raise ActionError("Proposal ID mismatch")
    if game.trade_proposal["proposer_id"] == player_id:
        raise ActionError("Cannot accept your own trade")

    proposer = game.player_by_id(game.trade_proposal["proposer_id"])
    accepter = game.player_by_id(player_id)
    if not proposer or not accepter:
        raise ActionError("Player not found")

    offer = {Resource(k): v for k, v in game.trade_proposal["offer"].items()}
    want = {Resource(k): v for k, v in game.trade_proposal["want"].items()}

    # Verify proposer still has the offered resources
    for res, amt in offer.items():
        if proposer.resources.get(res, 0) < amt:
            game.trade_proposal = None
            raise ActionError("Proposer no longer has the offered resources")

    # Verify accepter has the wanted resources
    for res, amt in want.items():
        if accepter.resources.get(res, 0) < amt:
            raise ActionError(f"You don't have enough {res.value}")

    # Execute swap
    for res, amt in offer.items():
        proposer.resources[res] -= amt
        accepter.add_resource(res, amt)
    for res, amt in want.items():
        accepter.resources[res] -= amt
        proposer.add_resource(res, amt)

    result = {
        "proposer_id": game.trade_proposal["proposer_id"],
        "accepter_id": player_id,
        "offer": game.trade_proposal["offer"],
        "want": game.trade_proposal["want"],
    }
    game.trade_proposal = None
    return result


def handle_reject_trade(game: GameState, player_id: str, proposal_id: str) -> Dict:
    """A player rejects the active trade proposal."""
    if not game.trade_proposal:
        raise ActionError("No active trade proposal")
    if game.trade_proposal["id"] != proposal_id:
        raise ActionError("Proposal ID mismatch")
    if game.trade_proposal["proposer_id"] == player_id:
        raise ActionError("Cannot reject your own trade (use cancel)")

    if player_id not in game.trade_proposal["rejected_by"]:
        game.trade_proposal["rejected_by"].append(player_id)

    # Check if all other players rejected
    other_ids = [
        p.player_id for p in game.players
        if p.player_id != game.trade_proposal["proposer_id"]
    ]
    all_rejected = all(pid in game.trade_proposal["rejected_by"] for pid in other_ids)

    if all_rejected:
        game.trade_proposal = None
        return {"auto_cancelled": True}

    return {"auto_cancelled": False}


def handle_cancel_trade(game: GameState, player_id: str) -> Dict:
    """Proposer cancels the active trade proposal."""
    if not game.trade_proposal:
        raise ActionError("No active trade proposal")
    if game.trade_proposal["proposer_id"] != player_id:
        raise ActionError("Only the proposer can cancel")

    game.trade_proposal = None
    return {"cancelled": True}


# ---------------------------------------------------------------------------
# Development card handlers
# ---------------------------------------------------------------------------

def check_largest_army(game: GameState):
    """Update largest army holder if someone has >= 3 knights and beats current holder."""
    best_pid = game.largest_army_holder
    best_count = game.largest_army_size

    for player in game.players:
        if player.knights_played >= 3 and player.knights_played > best_count:
            best_pid = player.player_id
            best_count = player.knights_played

    if best_pid != game.largest_army_holder or best_count != game.largest_army_size:
        game.largest_army_holder = best_pid
        game.largest_army_size = best_count


def handle_buy_dev_card(game: GameState, player_id: str) -> Dict:
    """Buy a development card from the deck."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.turn_step != TurnStep.POST_ROLL:
        raise ActionError("Can only buy dev cards after rolling")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    player = game.player_by_id(player_id)
    if not player:
        raise ActionError("Player not found")

    if not player.has_resources(DEV_CARD_COST):
        raise ActionError("Not enough resources (need ore, wheat, sheep)")

    if not game.dev_card_deck:
        raise ActionError("No development cards remaining")

    player.deduct(DEV_CARD_COST)
    card = game.dev_card_deck.pop()
    card.bought_on_turn = game.current_turn_number
    player.dev_cards.append(card)

    recalculate_vp(game)
    return {"bought": card.card_type.value}


def handle_play_dev_card(game: GameState, player_id: str, card_type_str: str, params: Dict) -> Dict:
    """Play a development card from the player's hand."""
    if game.phase != GamePhase.PLAYING:
        raise ActionError("Not in playing phase")
    if game.current_player().player_id != player_id:
        raise ActionError("Not your turn")

    player = game.player_by_id(player_id)
    if not player:
        raise ActionError("Player not found")

    try:
        card_type = DevCardType(card_type_str)
    except ValueError:
        raise ActionError(f"Unknown card type: {card_type_str}")

    if card_type == DevCardType.VICTORY_POINT:
        raise ActionError("Victory Point cards cannot be played manually")

    if player.dev_card_played_this_turn:
        raise ActionError("Already played a development card this turn")

    # Find a playable card (in hand and not bought this turn)
    card_index = None
    for i, c in enumerate(player.dev_cards):
        if c.card_type == card_type and c.bought_on_turn != game.current_turn_number:
            card_index = i
            break

    if card_index is None:
        raise ActionError("No playable card of that type (must not be bought this turn)")

    # Knight can be played PRE_ROLL or POST_ROLL; others only POST_ROLL
    if card_type == DevCardType.KNIGHT:
        if game.turn_step not in (TurnStep.PRE_ROLL, TurnStep.POST_ROLL):
            raise ActionError("Knight can only be played before or after rolling")
    else:
        if game.turn_step != TurnStep.POST_ROLL:
            raise ActionError("This card can only be played after rolling")

    # Remove card from hand and mark played
    player.dev_cards.pop(card_index)
    player.dev_card_played_this_turn = True

    result: Dict = {"card_type": card_type.value}

    if card_type == DevCardType.KNIGHT:
        player.knights_played += 1
        check_largest_army(game)
        # Enter robber placement flow (reuse existing robber flow)
        game.turn_step = TurnStep.ROBBER_PLACE
        result["action"] = "robber_place"

    elif card_type == DevCardType.YEAR_OF_PLENTY:
        resources = params.get("resources") or {}
        total = sum(int(v) for v in resources.values())
        if total != 2:
            # Undo: put card back
            player.dev_cards.append(DevCard(card_type=card_type, bought_on_turn=-1))
            player.dev_card_played_this_turn = False
            raise ActionError("Year of Plenty: must choose exactly 2 resources")
        for res_str, amt in resources.items():
            amt = int(amt)
            if amt > 0:
                try:
                    res = Resource(res_str)
                except ValueError:
                    player.dev_cards.append(DevCard(card_type=card_type, bought_on_turn=-1))
                    player.dev_card_played_this_turn = False
                    raise ActionError(f"Invalid resource: {res_str}")
                player.add_resource(res, amt)
        result["action"] = "resources_gained"

    elif card_type == DevCardType.MONOPOLY:
        res_str = params.get("resource")
        if not res_str:
            player.dev_cards.append(DevCard(card_type=card_type, bought_on_turn=-1))
            player.dev_card_played_this_turn = False
            raise ActionError("Monopoly: must specify a resource")
        try:
            res = Resource(res_str)
        except ValueError:
            player.dev_cards.append(DevCard(card_type=card_type, bought_on_turn=-1))
            player.dev_card_played_this_turn = False
            raise ActionError(f"Invalid resource: {res_str}")
        stolen_total = 0
        for other in game.players:
            if other.player_id != player_id:
                amt = other.resources.get(res, 0)
                if amt > 0:
                    other.resources[res] = 0
                    stolen_total += amt
        player.add_resource(res, stolen_total)
        result["action"] = "monopoly"
        result["resource"] = res.value
        result["amount"] = stolen_total

    elif card_type == DevCardType.ROAD_BUILDING:
        game.road_building_remaining = 2
        game.turn_step = TurnStep.ROAD_BUILDING
        result["action"] = "road_building"

    recalculate_vp(game)
    return result
