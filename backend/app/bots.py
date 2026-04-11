from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from typing import Any, Dict, List, Optional

import websockets

logger = logging.getLogger("catan.bot")

_bot_tasks: Dict[str, asyncio.Task] = {}  # player_id -> task


def stop_bot(player_id: str):
    """Cancel a running bot task."""
    task = _bot_tasks.pop(player_id, None)
    if task and not task.done():
        task.cancel()

# HEX_DIRECTIONS matching backend board.py
HEX_DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def _find_playable_card(game: Optional[dict], player_id: str, card_type: str) -> Optional[dict]:
    """Find a playable dev card of given type in bot's hand (not bought this turn)."""
    if not game:
        return None
    current_turn = int(game.get("current_turn_number") or 0)
    for p in game.get("players") or []:
        if p.get("player_id") == player_id:
            if p.get("dev_card_played_this_turn"):
                return None
            for c in p.get("dev_cards") or []:
                if c.get("card_type") == card_type and int(c.get("bought_on_turn", -1)) != current_turn:
                    return c
    return None


def _bot_play_dev_cards(game: Optional[dict], player_id: str, send, recv_game_state):
    """Bot plays non-knight dev cards during post_roll. This is a sync helper that returns coroutines to await."""
    # This is a no-op placeholder; actual async plays happen inline in the bot loop
    pass


def start_bot(server_base: str, room_id: str, player_id: str, seed: Optional[int] = None):
    if player_id in _bot_tasks and not _bot_tasks[player_id].done():
        return

    async def _run():
        if seed is not None:
            random.seed(seed)

        ws_url = server_base.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws/{room_id}/{player_id}"

        retries = 0
        while retries < 10:
            try:
                await _bot_loop(ws_url, player_id)
                break
            except websockets.ConnectionClosed:
                retries += 1
                logger.warning(f"Bot {player_id} WS closed, retry {retries}/10")
                await asyncio.sleep(1)
            except Exception as e:
                retries += 1
                logger.error(f"Bot {player_id} error: {e}, retry {retries}/10")
                await asyncio.sleep(1)

    _bot_tasks[player_id] = asyncio.create_task(_run())


async def _bot_loop(ws_url: str, player_id: str):
    async with websockets.connect(ws_url) as ws:
        game: Optional[dict] = None

        async def send(obj: dict):
            await ws.send(json.dumps(obj))

        pending_proposals: List[dict] = []  # trade proposals received while waiting

        async def recv_game_state(timeout: float = 30.0) -> Optional[dict]:
            """Wait for the next game_state message, skip others but capture trade proposals."""
            nonlocal game
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, deadline - time.time()))
                    msg = json.loads(raw)
                    if msg.get("type") == "game_state":
                        data = msg.get("data")
                        if isinstance(data, dict):
                            game = data
                            return data
                    elif msg.get("type") == "trade_proposal":
                        data = msg.get("data")
                        if isinstance(data, dict) and data.get("proposer_id") != player_id:
                            pending_proposals.append(data)
                except asyncio.TimeoutError:
                    return None
                except Exception:
                    continue
            return None

        async def handle_pending_trade_proposals():
            """Evaluate and respond to any pending P2P trade proposals."""
            nonlocal pending_proposals
            for proposal in pending_proposals:
                proposal_id = proposal.get("id", "")
                offer = proposal.get("offer") or {}   # what proposer gives (bot receives)
                want = proposal.get("want") or {}      # what proposer wants (bot gives)

                res = my_resources()
                # Check if bot has the resources the proposer wants
                can_afford = all(res.get(k, 0) >= v for k, v in want.items())
                if not can_afford:
                    await send({"type": "reject_trade", "proposal_id": proposal_id})
                    continue

                # Heuristic: accept if bot receives a resource it has 0 of,
                # and only gives away resources it has 2+ of
                receives_needed = any(res.get(k, 0) == 0 for k in offer if offer[k] > 0)
                gives_surplus = all(res.get(k, 0) >= 2 for k, v in want.items() if v > 0)

                if receives_needed and gives_surplus:
                    await asyncio.sleep(0.5 + random.random())
                    await send({"type": "accept_trade", "proposal_id": proposal_id})
                else:
                    await asyncio.sleep(0.3 + random.random() * 0.5)
                    await send({"type": "reject_trade", "proposal_id": proposal_id})
            pending_proposals = []

        async def try_build_and_wait(piece: str, position: dict, timeout: float = 0.15) -> bool:
            """Send a build command, read response, return True if game state changed."""
            nonlocal game
            old_step = int((game or {}).get("setup_step") or 0)
            old_vertices = len((game or {}).get("vertices") or {})
            old_edges = len((game or {}).get("edges") or {})
            await send({"type": "build", "piece": piece, "position": position})

            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.01, deadline - time.time()))
                    msg = json.loads(raw)
                    if msg.get("type") == "game_state":
                        data = msg.get("data")
                        if isinstance(data, dict):
                            game = data
                            new_step = int(data.get("setup_step") or 0)
                            new_v = len(data.get("vertices") or {})
                            new_e = len(data.get("edges") or {})
                            if new_step != old_step or new_v != old_vertices or new_e != old_edges:
                                return True
                    elif msg.get("type") == "trade_proposal":
                        data = msg.get("data")
                        if isinstance(data, dict) and data.get("proposer_id") != player_id:
                            pending_proposals.append(data)
                except asyncio.TimeoutError:
                    break
                except Exception:
                    break
            return False

        def land_tiles() -> List[dict]:
            tiles = ((game or {}).get("map") or {}).get("tiles") or []
            return [t for t in tiles if t.get("tile_type") not in ("ocean", "desert")]

        def random_build_pos() -> Dict[str, int]:
            tiles = land_tiles()
            if not tiles:
                return {"q": 0, "r": 0, "direction": 0}
            t = random.choice(tiles)
            return {"q": int(t["q"]), "r": int(t["r"]), "direction": random.randint(0, 5)}

        def road_positions_near_settlement() -> List[Dict[str, int]]:
            """Positions for roads adjacent to the bot's last placed settlement."""
            if not game:
                return []
            for p in game.get("players") or []:
                if p.get("player_id") == player_id:
                    settlements = p.get("setup_settlements") or []
                    if not settlements:
                        return []
                    last = settlements[-1]
                    sq, sr = int(last[0]), int(last[1])
                    positions = []
                    for d in range(6):
                        positions.append({"q": sq, "r": sr, "direction": d})
                    for dq, dr in HEX_DIRS:
                        nq, nr = sq + dq, sr + dr
                        for d in range(6):
                            positions.append({"q": nq, "r": nr, "direction": d})
                    random.shuffle(positions)
                    return positions
            return []

        def my_resources() -> Dict[str, int]:
            if not game:
                return {}
            for p in game.get("players") or []:
                if p.get("player_id") == player_id:
                    return p.get("resources") or {}
            return {}

        def has_resources(cost: Dict[str, int]) -> bool:
            res = my_resources()
            return all(res.get(k, 0) >= v for k, v in cost.items())

        # === Main loop: wait for game_state then act ===
        while True:
            if game is None:
                await recv_game_state(timeout=60)
                if game is None:
                    continue

            phase = str(game.get("phase") or "")
            turn_step = str(game.get("turn_step") or "")
            current = game.get("current_player_id")
            setup_step = int(game.get("setup_step") or 0)

            if phase == "finished":
                return

            # Handle discard regardless of whose turn it is
            if phase == "playing" and turn_step == "robber_discard":
                discard_list = game.get("players_to_discard") or []
                if player_id in discard_list:
                    res = my_resources()
                    total = sum(res.values())
                    to_discard = total // 2
                    payload: Dict[str, int] = {}
                    remaining = to_discard
                    for rname, amt in res.items():
                        give = min(amt, remaining)
                        if give > 0:
                            payload[rname] = give
                            remaining -= give
                        if remaining <= 0:
                            break
                    await send({"type": "discard", "resources": payload})
                game = None  # wait for next state
                continue

            # Handle any pending P2P trade proposals from other players
            await handle_pending_trade_proposals()

            if current != player_id:
                game = None  # not our turn, wait for next state
                continue

            # === Setup phase ===
            if phase in ("setup_forward", "setup_backward"):
                piece = "settlement" if (setup_step % 2 == 0) else "road"
                if piece == "road":
                    positions = road_positions_near_settlement()
                    for pos in positions:
                        ok = await try_build_and_wait("road", pos, timeout=0.1)
                        if ok:
                            break
                else:
                    for _ in range(80):
                        ok = await try_build_and_wait("settlement", random_build_pos(), timeout=0.1)
                        if ok:
                            break
                # game is already updated by try_build_and_wait if successful
                # loop back to re-evaluate the new game state
                if game and int(game.get("setup_step") or 0) == setup_step:
                    # Failed to place — wait for next state update
                    game = None
                continue

            # === Playing phase ===
            # Add delays between bot actions so human players can see what's happening
            BOT_DELAY = 0.8  # seconds between major actions

            if phase == "playing":
                if turn_step == "pre_roll":
                    await asyncio.sleep(BOT_DELAY)
                    # Check if bot has a playable knight to play before rolling
                    knight_card = _find_playable_card(game, player_id, "knight")
                    if knight_card:
                        await send({"type": "play_dev_card", "card_type": "knight", "params": {}})
                        await recv_game_state(timeout=2)
                        continue
                    await send({"type": "roll_dice"})
                    await recv_game_state(timeout=2)
                    continue

                if turn_step == "robber_place":
                    await asyncio.sleep(BOT_DELAY)
                    tiles = ((game.get("map") or {}).get("tiles") or [])
                    robber = game.get("robber") or {}
                    rq, rr = robber.get("q", 0), robber.get("r", 0)
                    candidates = [
                        t for t in tiles
                        if t.get("tile_type") not in ("ocean",)
                        and (t.get("q"), t.get("r")) != (rq, rr)
                    ]
                    if candidates:
                        t = random.choice(candidates)
                        await send({"type": "place_robber", "q": t["q"], "r": t["r"]})
                    await recv_game_state(timeout=2)
                    continue

                if turn_step == "robber_steal":
                    await asyncio.sleep(BOT_DELAY * 0.5)
                    targets = game.get("robber_steal_targets") or []
                    if targets:
                        await send({"type": "steal", "target_id": random.choice(targets)})
                    await recv_game_state(timeout=2)
                    continue

                if turn_step == "road_building":
                    # Place free roads from Road Building card
                    for _ in range(20):
                        ok = await try_build_and_wait("road", random_build_pos(), timeout=0.1)
                        if ok:
                            break
                    # After placing, game state updates; loop back to re-evaluate
                    if game and str(game.get("turn_step") or "") == "road_building":
                        # Still need another road
                        for _ in range(20):
                            ok = await try_build_and_wait("road", random_build_pos(), timeout=0.1)
                            if ok:
                                break
                    continue

                if turn_step == "post_roll":
                    await asyncio.sleep(BOT_DELAY)
                    # Play non-knight dev cards before building
                    # Year of Plenty: pick 2 resources the bot needs most
                    yop_card = _find_playable_card(game, player_id, "year_of_plenty")
                    if yop_card:
                        res = my_resources()
                        # Pick the 2 lowest resources
                        sorted_res = sorted(res.items(), key=lambda x: x[1])
                        picks: Dict[str, int] = {}
                        remaining = 2
                        for rname, _ in sorted_res:
                            if remaining <= 0:
                                break
                            picks[rname] = picks.get(rname, 0) + 1
                            remaining -= 1
                        if remaining > 0:
                            # Fill with first resource
                            first = sorted_res[0][0] if sorted_res else "wood"
                            picks[first] = picks.get(first, 0) + remaining
                        await send({"type": "play_dev_card", "card_type": "year_of_plenty", "params": {"resources": picks}})
                        await recv_game_state(timeout=1)

                    # Monopoly: pick resource we have least of (can't see opponents' hands)
                    mono_card = _find_playable_card(game, player_id, "monopoly")
                    if mono_card and game:
                        my_res = my_resources()
                        # Pick the resource we need most (have least of)
                        best_res = min(["wood", "brick", "wheat", "sheep", "ore"], key=lambda r: my_res.get(r, 0))
                        # Only play if opponents have cards (check resource_count)
                        others_have_cards = any(
                            (p.get("resource_count") or 0) > 0
                            for p in game.get("players") or []
                            if p.get("player_id") != player_id
                        )
                        if others_have_cards:
                            await send({"type": "play_dev_card", "card_type": "monopoly", "params": {"resource": best_res}})
                            await recv_game_state(timeout=1)

                    # Road Building: play it and let the road_building handler take over
                    rb_card = _find_playable_card(game, player_id, "road_building")
                    if rb_card:
                        await send({"type": "play_dev_card", "card_type": "road_building", "params": {}})
                        await recv_game_state(timeout=1)
                        continue  # re-evaluate turn_step (should be road_building now)

                    # Maybe buy a dev card (50% chance if affordable and deck has cards)
                    deck_count = int((game or {}).get("dev_card_deck_count") or 0)
                    if deck_count > 0 and has_resources({"ore": 1, "wheat": 1, "sheep": 1}):
                        if random.random() < 0.5:
                            await send({"type": "buy_dev_card"})
                            await recv_game_state(timeout=1)

                    # Try bank trades: trade surplus for what we're missing
                    res = my_resources()
                    settlement_cost = {"wood": 1, "brick": 1, "wheat": 1, "sheep": 1}
                    # Find resources we need (have 0 of) for a settlement
                    need = [r for r, c in settlement_cost.items() if res.get(r, 0) < c]
                    # Find resources we can afford to trade away (have >= 5, keep 1)
                    # or any resource >= 4 that we don't need for building
                    surplus = sorted(
                        [(r, a) for r, a in res.items() if a >= 4],
                        key=lambda x: -x[1],  # most surplus first
                    )
                    if surplus and need:
                        give_res, give_amt = surplus[0]
                        want_res = need[0]
                        # Don't trade away something we need unless we have plenty
                        if give_res in need and give_amt < 5:
                            # Try next surplus
                            surplus2 = [(r, a) for r, a in surplus if r not in need]
                            if surplus2:
                                give_res, give_amt = surplus2[0]
                            else:
                                give_res = None
                        if give_res:
                            await send({"type": "trade", "offer": {give_res: 4}, "want": {want_res: 1}})
                            await recv_game_state(timeout=1)

                    # Try building
                    if has_resources({"wood": 1, "brick": 1, "wheat": 1, "sheep": 1}):
                        for _ in range(20):
                            ok = await try_build_and_wait("settlement", random_build_pos(), timeout=0.1)
                            if ok:
                                break

                    if has_resources({"wood": 1, "brick": 1}):
                        for _ in range(20):
                            ok = await try_build_and_wait("road", random_build_pos(), timeout=0.1)
                            if ok:
                                break

                    await send({"type": "end_turn"})
                    await recv_game_state(timeout=2)
                    continue

            # Unknown state — wait for next update
            game = None
