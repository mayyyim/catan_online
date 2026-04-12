#!/usr/bin/env python3
"""
E2E Smoke Test — Catan Online
==============================
Runs before every commit. Verifies the app actually works end-to-end,
not just that unit tests pass.

Usage:
    python scripts/e2e_smoke.py              # auto-detect environment
    python scripts/e2e_smoke.py --docker     # force Docker mode (nginx at :3000)
    python scripts/e2e_smoke.py --local      # force local mode (backend :8080)
    python scripts/e2e_smoke.py --base http://localhost:3000/api  # custom base URL

Exit code 0 = all passed, 1 = failures found.
"""

import argparse
import json
import random
import string
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class TestRunner:
    base: str = ""
    ws_base: str = ""
    results: list = field(default_factory=list)
    verbose: bool = False

    # State shared across tests
    room_id: str = ""
    host_id: str = ""
    bot_ids: list = field(default_factory=list)

    def api(self, method: str, path: str, body: Optional[dict] = None, timeout: int = 10) -> dict:
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, headers=headers, method=method
        )
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())

    def api_status(self, method: str, path: str, body: Optional[dict] = None) -> int:
        """Return HTTP status code (doesn't raise on 4xx)."""
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            f"{self.base}{path}", data=data, headers=headers, method=method
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def record(self, name: str, passed: bool, detail: str = ""):
        self.results.append(TestResult(name, passed, detail))
        mark = "\033[32m✓\033[0m" if passed else "\033[31m✗\033[0m"
        msg = f"  {mark} {name}"
        if detail:
            msg += f"  ({detail})"
        print(msg)

    def summary(self) -> bool:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print(f"\n{'=' * 55}")
        if failed == 0:
            print(f"\033[32m  ALL {total} TESTS PASSED\033[0m")
        else:
            print(f"\033[31m  {failed} FAILED\033[0m / {total} total")
            print()
            for r in self.results:
                if not r.passed:
                    print(f"  ✗ {r.name}: {r.detail}")
        print(f"{'=' * 55}")
        return failed == 0


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def test_health(t: TestRunner):
    """1. Health check — backend is alive."""
    try:
        resp = t.api("GET", "/health")
        t.record("Health check", resp.get("status") == "ok", f"status={resp.get('status')}")
    except Exception as e:
        t.record("Health check", False, str(e))


def test_create_room(t: TestRunner):
    """2. Create a room."""
    try:
        resp = t.api("POST", "/rooms", {"host_name": "SmokeTest"})
        t.room_id = resp["room_id"]
        t.host_id = resp["host_player_id"]
        ok = bool(t.room_id and t.host_id)
        t.record("Create room", ok, f"room={t.room_id}")
    except Exception as e:
        t.record("Create room", False, str(e))


def test_get_room(t: TestRunner):
    """3. Get room status."""
    if not t.room_id:
        t.record("Get room", False, "no room_id from previous test")
        return
    try:
        resp = t.api("GET", f"/rooms/{t.room_id}")
        ok = resp["player_count"] == 1 and resp["state"] == "waiting"
        t.record("Get room status", ok, f"players={resp['player_count']}, state={resp['state']}")
    except Exception as e:
        t.record("Get room status", False, str(e))


def test_add_bots(t: TestRunner):
    """4. Add 3 bots (easy/medium/hard)."""
    if not t.room_id:
        t.record("Add bots", False, "no room_id")
        return
    try:
        t.bot_ids = []
        for diff in ["easy", "medium", "hard"]:
            resp = t.api("POST", f"/rooms/{t.room_id}/bots", {
                "name": f"Bot_{diff}", "difficulty": diff
            })
            t.bot_ids.append(resp["player_id"])
        t.record("Add 3 bots", len(t.bot_ids) == 3, f"ids={t.bot_ids}")
    except Exception as e:
        t.record("Add 3 bots", False, str(e))


def test_bots_persist(t: TestRunner):
    """5. Bots still in room after 4 seconds (WS disconnect doesn't remove them)."""
    if not t.room_id or not t.bot_ids:
        t.record("Bot persistence", False, "no room or bots")
        return
    try:
        time.sleep(4)
        resp = t.api("GET", f"/rooms/{t.room_id}")
        count = resp["player_count"]
        connected = sum(1 for p in resp["players"] if p.get("connected"))
        ok = count == 4
        t.record("Bot persistence (4s)", ok, f"players={count}, connected={connected}")
    except Exception as e:
        t.record("Bot persistence (4s)", False, str(e))


def test_room_full(t: TestRunner):
    """6. Room full — 5th player rejected."""
    if not t.room_id:
        t.record("Room full check", False, "no room_id")
        return
    try:
        status = t.api_status("POST", f"/rooms/{t.room_id}/bots", {
            "name": "ExtraBot", "difficulty": "easy"
        })
        ok = status == 400
        t.record("Room full (5th bot rejected)", ok, f"HTTP {status}")
    except Exception as e:
        t.record("Room full (5th bot rejected)", False, str(e))


def test_remove_bot(t: TestRunner):
    """7. Remove a bot."""
    if not t.room_id or not t.bot_ids:
        t.record("Remove bot", False, "no room or bots")
        return
    try:
        target = t.bot_ids.pop()
        t.api("DELETE", f"/rooms/{t.room_id}/players/{target}")
        resp = t.api("GET", f"/rooms/{t.room_id}")
        ok = resp["player_count"] == 3
        t.record("Remove bot", ok, f"players={resp['player_count']}")
    except Exception as e:
        t.record("Remove bot", False, str(e))


def test_re_add_bot(t: TestRunner):
    """8. Re-add bot after removal (back to 4)."""
    if not t.room_id:
        t.record("Re-add bot", False, "no room_id")
        return
    try:
        resp = t.api("POST", f"/rooms/{t.room_id}/bots", {
            "name": "Bot_refill", "difficulty": "medium"
        })
        t.bot_ids.append(resp["player_id"])
        status = t.api("GET", f"/rooms/{t.room_id}")
        ok = status["player_count"] == 4
        t.record("Re-add bot", ok, f"players={status['player_count']}")
    except Exception as e:
        t.record("Re-add bot", False, str(e))


def test_auth_register(t: TestRunner):
    """9. Register a new user."""
    try:
        uname = "smoke_" + "".join(random.choices(string.ascii_lowercase, k=5))
        resp = t.api("POST", "/auth/register", {
            "username": uname, "password": "test1234", "display_name": "Smoke User"
        })
        ok = "token" in resp and "user_id" in resp
        t.record("Auth register", ok, f"user={uname}")
        return resp  # for login test
    except urllib.error.HTTPError as e:
        body = e.read().decode() if hasattr(e, "read") else ""
        t.record("Auth register", False, f"HTTP {e.code}: {body[:100]}")
        return None
    except Exception as e:
        t.record("Auth register", False, str(e))
        return None


def test_auth_login(t: TestRunner, register_resp: Optional[dict]):
    """10. Login with registered credentials."""
    if not register_resp:
        t.record("Auth login", False, "register failed, skipping")
        return
    try:
        uname = register_resp["username"]
        resp = t.api("POST", "/auth/login", {
            "username": uname, "password": "test1234"
        })
        ok = resp["user_id"] == register_resp["user_id"]
        t.record("Auth login", ok, f"user_id match={ok}")
    except Exception as e:
        t.record("Auth login", False, str(e))


def test_auth_guest(t: TestRunner):
    """11. Guest login."""
    try:
        resp = t.api("POST", "/auth/guest")
        ok = "token" in resp and resp.get("is_guest") is True
        t.record("Auth guest", ok)
    except Exception as e:
        t.record("Auth guest", False, str(e))


def test_leaderboard(t: TestRunner):
    """12. Leaderboard API."""
    try:
        resp = t.api("GET", "/stats/leaderboard")
        ok = "leaderboard" in resp and isinstance(resp["leaderboard"], list)
        t.record("Leaderboard API", ok, f"{len(resp['leaderboard'])} entries")
    except Exception as e:
        t.record("Leaderboard API", False, str(e))


def test_maps(t: TestRunner):
    """13. Map gallery API."""
    try:
        resp = t.api("GET", "/maps")
        maps = resp.get("maps", [])
        ok = len(maps) >= 2  # at least 'random' + 1 static map
        t.record("Maps API", ok, f"{len(maps)} maps")
    except Exception as e:
        t.record("Maps API", False, str(e))


def test_join_via_invite(t: TestRunner):
    """14. Join room via invite code."""
    try:
        # Create a fresh room for this test
        room = t.api("POST", "/rooms", {"host_name": "InviteHost"})
        invite = room["invite_code"]
        joined = t.api("POST", f"/rooms/{invite}/join", {"player_name": "Joiner"})
        ok = joined["room_id"] == room["room_id"] and joined["player_id"] != room["host_player_id"]
        t.record("Join via invite", ok, f"code={invite}")
    except Exception as e:
        t.record("Join via invite", False, str(e))


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def detect_base_url() -> str:
    """Try Docker (nginx at :3000/api) first, then local (backend at :8080)."""
    for candidate in [
        "http://localhost:3000/api",  # Docker: nginx proxy
        "http://localhost:8080",       # Local: direct backend
    ]:
        try:
            req = urllib.request.Request(f"{candidate}/health", method="GET")
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read())
            if data.get("status") == "ok":
                return candidate
        except Exception:
            continue
    return ""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Catan Online E2E Smoke Test")
    parser.add_argument("--base", help="Base API URL (e.g. http://localhost:3000/api)")
    parser.add_argument("--docker", action="store_true", help="Force Docker mode (:3000/api)")
    parser.add_argument("--local", action="store_true", help="Force local mode (:8080)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.base:
        base = args.base.rstrip("/")
    elif args.docker:
        base = "http://localhost:3000/api"
    elif args.local:
        base = "http://localhost:8080"
    else:
        base = detect_base_url()

    if not base:
        print("\033[31mERROR: Cannot reach backend. Start the app first:\033[0m")
        print("  Docker:  docker compose up -d")
        print("  Local:   cd backend && python main.py")
        sys.exit(1)

    mode = "Docker" if ":3000" in base else "Local"
    print(f"\n  Catan E2E Smoke Test")
    print(f"  Base: {base} ({mode} mode)")
    print(f"{'─' * 55}\n")

    t = TestRunner(base=base, verbose=args.verbose)

    # Run all tests in order
    test_health(t)
    test_create_room(t)
    test_get_room(t)
    test_add_bots(t)
    test_bots_persist(t)
    test_room_full(t)
    test_remove_bot(t)
    test_re_add_bot(t)
    reg = test_auth_register(t)
    test_auth_login(t, reg)
    test_auth_guest(t)
    test_leaderboard(t)
    test_maps(t)
    test_join_via_invite(t)

    all_passed = t.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
