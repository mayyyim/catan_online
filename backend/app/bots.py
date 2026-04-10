from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any, Dict, Optional

import websockets


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

        async with websockets.connect(ws_url) as ws:
            last_game: Optional[dict] = None
            last_error_ts = 0.0

            async def send(obj: dict):
                await ws.send(json.dumps(obj))

            def parse_game_state(msg: dict) -> Optional[dict]:
                if msg.get("type") != "game_state":
                    return None
                data = msg.get("data")
                return data if isinstance(data, dict) else None

            def is_setup(phase: str) -> bool:
                return phase in ("setup_forward", "setup_backward")

            def expects_settlement(setup_step: int) -> bool:
                return (setup_step % 2) == 0

            def random_build_position(game_data: dict) -> Dict[str, int]:
                tiles = (game_data.get("map") or {}).get("tiles") or []
                if not tiles:
                    return {"q": 0, "r": 0, "direction": 0}
                t = random.choice(tiles)
                q = int(t.get("q", 0))
                r = int(t.get("r", 0))
                direction = random.randint(0, 5)
                return {"q": q, "r": r, "direction": direction}

            def my_resources(game_data: dict) -> Dict[str, int]:
                for p in game_data.get("players") or []:
                    if p.get("player_id") == player_id:
                        return p.get("resources") or {}
                return {}

            def my_player(game_data: dict) -> Optional[dict]:
                for p in game_data.get("players") or []:
                    if p.get("player_id") == player_id:
                        return p
                return None

            def has_resources(res: Dict[str, int], cost: Dict[str, int]) -> bool:
                return all(res.get(k, 0) >= v for k, v in cost.items())

            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue

                if msg.get("type") == "error":
                    now = time.time()
                    if now - last_error_ts > 1.0:
                        last_error_ts = now
                    continue

                game = parse_game_state(msg)
                if not game:
                    continue

                last_game = game
                phase = str(game.get("phase") or "")
                turn_step = str(game.get("turn_step") or "")
                current = game.get("current_player_id")
                setup_step = int(game.get("setup_step") or 0)

                # Handle discard even when it's not our "turn" — all players with >7 must discard
                if phase == "playing" and turn_step == "robber_discard":
                    discard_list = game.get("players_to_discard") or []
                    if player_id in discard_list:
                        res = my_resources(game)
                        total = sum(res.values())
                        to_discard = total // 2
                        discard_payload: Dict[str, int] = {}
                        remaining = to_discard
                        for rname, amt in res.items():
                            give = min(amt, remaining)
                            if give > 0:
                                discard_payload[rname] = give
                                remaining -= give
                            if remaining <= 0:
                                break
                        await send({"type": "discard", "resources": discard_payload})
                    continue

                if current != player_id:
                    continue

                if is_setup(phase):
                    piece = "settlement" if expects_settlement(setup_step) else "road"
                    for _ in range(120):
                        await send({"type": "build", "piece": piece, "position": random_build_position(game)})
                        await asyncio.sleep(0.05)
                        if last_game and int(last_game.get("setup_step") or 0) != setup_step:
                            break
                    continue

                if phase == "playing":
                    if turn_step == "pre_roll":
                        await send({"type": "roll_dice"})
                        continue

                    if turn_step == "robber_place":
                        # Move robber to a random land tile (not current position)
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
                        continue

                    if turn_step == "robber_steal":
                        targets = game.get("robber_steal_targets") or []
                        if targets:
                            await send({"type": "steal", "target_id": random.choice(targets)})
                        continue

                    if turn_step == "post_roll":
                        # Try to build something before ending turn
                        res = my_resources(game)
                        built = False

                        # Try settlement: wood+brick+wheat+sheep
                        if has_resources(res, {"wood": 1, "brick": 1, "wheat": 1, "sheep": 1}):
                            for _ in range(30):
                                await send({"type": "build", "piece": "settlement", "position": random_build_position(game)})
                                await asyncio.sleep(0.05)
                                # Check if state changed
                                try:
                                    peek = await asyncio.wait_for(ws.recv(), timeout=0.1)
                                    peek_msg = json.loads(peek)
                                    if peek_msg.get("type") == "game_state":
                                        last_game = peek_msg.get("data")
                                        new_res = my_resources(last_game or {})
                                        if new_res != res:
                                            built = True
                                            break
                                except (asyncio.TimeoutError, Exception):
                                    pass

                        # Try road: wood+brick
                        res = my_resources(last_game or game)
                        if has_resources(res, {"wood": 1, "brick": 1}):
                            for _ in range(30):
                                await send({"type": "build", "piece": "road", "position": random_build_position(game)})
                                await asyncio.sleep(0.05)
                                try:
                                    peek = await asyncio.wait_for(ws.recv(), timeout=0.1)
                                    peek_msg = json.loads(peek)
                                    if peek_msg.get("type") == "game_state":
                                        last_game = peek_msg.get("data")
                                        new_res = my_resources(last_game or {})
                                        if new_res != res:
                                            built = True
                                            break
                                except (asyncio.TimeoutError, Exception):
                                    pass

                        await send({"type": "end_turn"})
                        continue

    _bot_tasks[player_id] = asyncio.create_task(_run())

