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

# HEX_DIRECTIONS matching backend board.py
HEX_DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


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

        async def recv_game_state(timeout: float = 30.0) -> Optional[dict]:
            """Wait for the next game_state message, skip others."""
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
                except asyncio.TimeoutError:
                    return None
                except Exception:
                    continue
            return None

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
            if phase == "playing":
                if turn_step == "pre_roll":
                    await send({"type": "roll_dice"})
                    await recv_game_state(timeout=2)
                    continue

                if turn_step == "robber_place":
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
                    targets = game.get("robber_steal_targets") or []
                    if targets:
                        await send({"type": "steal", "target_id": random.choice(targets)})
                    await recv_game_state(timeout=2)
                    continue

                if turn_step == "post_roll":
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
