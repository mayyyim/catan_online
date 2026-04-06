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
                    if turn_step == "post_roll":
                        await send({"type": "end_turn"})
                        continue

    _bot_tasks[player_id] = asyncio.create_task(_run())

