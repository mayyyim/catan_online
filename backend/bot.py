"""
Minimal local testing bot for Catan Online.

Workflow:
1) You (human) create a room in the frontend.
2) Copy the invite code.
3) Run:
     python3 bot.py --server http://localhost:8080 --code ABC123 --name Bot

The bot will:
- join via HTTP
- connect to WS /ws/{room_id}/{player_id}
- during setup: try random legal placements for settlement+road
- during play: on its turn roll dice then end turn

This is intentionally simple and "dumb" — it's for dev testing loops.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
import urllib.request
from typing import Any, Dict, Optional, Tuple

import websockets


def _http_json(method: str, url: str, body: Optional[dict] = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except Exception as e:
        raise RuntimeError(f"HTTP {method} {url} failed: {e}") from e


def join_room(server: str, invite_code: str, name: str) -> Tuple[str, str]:
    server = server.rstrip("/")
    invite_code = invite_code.strip().upper()
    res = _http_json(
        "POST",
        f"{server}/api/rooms/{invite_code}/join",
        {"player_name": name},
    )
    room_id = res.get("room_id")
    player_id = res.get("player_id")
    if not room_id or not player_id:
        raise RuntimeError(f"Unexpected join response: {res}")
    return room_id, player_id


def _parse_game_state(msg: dict) -> Optional[dict]:
    # backend sends: { type: "game_state", data: { ... } }
    if msg.get("type") != "game_state":
        return None
    data = msg.get("data")
    if isinstance(data, dict):
        return data
    return None


def _is_setup_phase(phase: str) -> bool:
    return phase in ("setup_forward", "setup_backward")


def _setup_expects_settlement(setup_step: int) -> bool:
    # backend increments setup_step each placement; even=settlement, odd=road
    return (setup_step % 2) == 0


def _random_build_position(game_data: dict) -> Dict[str, int]:
    tiles = (game_data.get("map") or {}).get("tiles") or []
    if not tiles:
        return {"q": 0, "r": 0, "direction": 0}
    t = random.choice(tiles)
    q = int(t.get("q", 0))
    r = int(t.get("r", 0))
    direction = random.randint(0, 5)
    return {"q": q, "r": r, "direction": direction}


async def bot_loop(server: str, room_id: str, player_id: str, seed: Optional[int] = None):
    if seed is not None:
        random.seed(seed)

    ws_url = server.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/ws/{room_id}/{player_id}"

    print(f"[bot] connecting ws {ws_url}")
    async with websockets.connect(ws_url) as ws:
        last_game: Optional[dict] = None
        last_error_ts = 0.0

        async def send(obj: dict):
            await ws.send(json.dumps(obj))

        while True:
            raw = await ws.recv()
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            if msg.get("type") == "error":
                # Avoid spamming the console if we brute-force placements.
                now = time.time()
                if now - last_error_ts > 1.0:
                    print(f"[bot] server error: {msg.get('data', {}).get('message') or msg}")
                    last_error_ts = now
                continue

            game = _parse_game_state(msg)
            if not game:
                continue

            last_game = game
            phase = str(game.get("phase") or "")
            turn_step = str(game.get("turn_step") or "")
            current = game.get("current_player_id")
            setup_step = int(game.get("setup_step") or 0)

            if current != player_id:
                continue

            if _is_setup_phase(phase):
                # Place settlement then road.
                if _setup_expects_settlement(setup_step):
                    piece = "settlement"
                else:
                    piece = "road"

                # Brute-force attempt a few random positions until the server accepts.
                for _ in range(80):
                    pos = _random_build_position(game)
                    await send({"type": "build", "piece": piece, "position": pos})
                    # acceptance will come as next game_state; small delay to avoid flooding
                    await asyncio.sleep(0.05)
                    # if setup_step changed, we succeeded
                    if last_game and int(last_game.get("setup_step") or 0) != setup_step:
                        break
                continue

            if phase == "playing":
                if turn_step == "pre_roll":
                    print("[bot] roll_dice")
                    await send({"type": "roll_dice"})
                    continue
                if turn_step == "post_roll":
                    print("[bot] end_turn")
                    await send({"type": "end_turn"})
                    continue


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="http://localhost:8080", help="Backend base URL")
    ap.add_argument("--code", required=True, help="Invite code, e.g. ABC123")
    ap.add_argument("--name", default="Bot", help="Bot player display name")
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducible bot moves")
    args = ap.parse_args(argv)

    room_id, player_id = join_room(args.server, args.code, args.name)
    print(f"[bot] joined room_id={room_id} player_id={player_id}")
    asyncio.run(bot_loop(args.server, room_id, player_id, seed=args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

