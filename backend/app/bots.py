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


def start_bot(server_base: str, room_id: str, player_id: str, seed: Optional[int] = None):
    """
    Start an in-process bot that connects to this server's WS endpoint.
    Idempotent per player_id.
    """
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
                break  # clean exit (game finished)
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
        last_game: Optional[dict] = None

        async def send(obj: dict):
            await ws.send(json.dumps(obj))

        async def drain(timeout: float = 0.15) -> Optional[dict]:
            """Read all pending messages, return latest game_state data or None."""
            nonlocal last_game
            latest = None
            deadline = time.time() + timeout
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=max(0.01, remaining))
                    msg = json.loads(raw)
                    if msg.get("type") == "game_state":
                        data = msg.get("data")
                        if isinstance(data, dict):
                            last_game = data
                            latest = data
                except asyncio.TimeoutError:
                    break
                except Exception:
                    break
            return latest

        def land_tiles(game_data: dict) -> List[dict]:
            tiles = (game_data.get("map") or {}).get("tiles") or []
            return [t for t in tiles if t.get("tile_type") not in ("ocean", "desert")]

        def random_build_position(game_data: dict) -> Dict[str, int]:
            tiles = land_tiles(game_data)
            if not tiles:
                tiles = (game_data.get("map") or {}).get("tiles") or []
            if not tiles:
                return {"q": 0, "r": 0, "direction": 0}
            t = random.choice(tiles)
            return {"q": int(t.get("q", 0)), "r": int(t.get("r", 0)), "direction": random.randint(0, 5)}

        def my_resources(game_data: dict) -> Dict[str, int]:
            for p in game_data.get("players") or []:
                if p.get("player_id") == player_id:
                    return p.get("resources") or {}
            return {}

        def has_resources(res: Dict[str, int], cost: Dict[str, int]) -> bool:
            return all(res.get(k, 0) >= v for k, v in cost.items())

        while True:
            raw = await ws.recv()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "error":
                continue

            game = msg.get("data") if msg.get("type") == "game_state" else None
            if not game or not isinstance(game, dict):
                continue

            last_game = game
            phase = str(game.get("phase") or "")
            turn_step = str(game.get("turn_step") or "")
            current = game.get("current_player_id")
            setup_step = int(game.get("setup_step") or 0)

            # Game finished — exit cleanly
            if phase == "finished":
                return

            # Handle discard regardless of whose turn it is
            if phase == "playing" and turn_step == "robber_discard":
                discard_list = game.get("players_to_discard") or []
                if player_id in discard_list:
                    res = my_resources(game)
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
                continue

            if current != player_id:
                continue

            # === Setup phase: place settlement then road ===
            if phase in ("setup_forward", "setup_backward"):
                piece = "settlement" if (setup_step % 2 == 0) else "road"
                for attempt in range(80):
                    await send({"type": "build", "piece": piece, "position": random_build_position(game)})
                    # Read response to check if placement succeeded
                    updated = await drain(0.08)
                    if updated and int(updated.get("setup_step") or 0) != setup_step:
                        break  # Success! Step advanced.
                continue

            # === Playing phase ===
            if phase == "playing":
                if turn_step == "pre_roll":
                    await send({"type": "roll_dice"})
                    await drain(0.3)
                    continue

                if turn_step == "robber_place":
                    tiles = (game.get("map") or {}).get("tiles") or []
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
                        await drain(0.3)
                    continue

                if turn_step == "robber_steal":
                    targets = game.get("robber_steal_targets") or []
                    if targets:
                        await send({"type": "steal", "target_id": random.choice(targets)})
                        await drain(0.3)
                    continue

                if turn_step == "post_roll":
                    # Try to build before ending turn
                    res = my_resources(last_game or game)

                    # Try settlement
                    if has_resources(res, {"wood": 1, "brick": 1, "wheat": 1, "sheep": 1}):
                        for _ in range(20):
                            await send({"type": "build", "piece": "settlement", "position": random_build_position(game)})
                            updated = await drain(0.08)
                            if updated:
                                new_res = my_resources(updated)
                                if new_res != res:
                                    res = new_res
                                    break

                    # Try road
                    if has_resources(res, {"wood": 1, "brick": 1}):
                        for _ in range(20):
                            await send({"type": "build", "piece": "road", "position": random_build_position(game)})
                            updated = await drain(0.08)
                            if updated:
                                new_res = my_resources(updated)
                                if new_res != res:
                                    res = new_res
                                    break

                    await send({"type": "end_turn"})
                    continue
