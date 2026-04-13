"""Tests for inland ports — explicit ports in polygon JSON.

Regression coverage for the "inland ports as a general capability" feature:
any map can now pin its ports at arbitrary hex coords + sides via the
`"ports"` field of its polygon JSON, bypassing the coastal auto-detection.
Backward compat: maps without the field still go through `detect_ports`.
"""

import json
import pytest

from app.game.board import HEX_DIRECTIONS
from app.game.models import Resource
from app.maps.rasterizer import build_map, POLYGON_DIR


def _load_polygon(slug: str) -> dict:
    import os
    with open(os.path.join(POLYGON_DIR, f"{slug}.json")) as fh:
        return json.load(fh)


class TestCzechInlandPorts:
    def test_czech_map_loads(self):
        m = build_map("czech_republic")
        assert len(m.tiles) >= 12, "czech should have enough tiles to be playable"
        assert len(m.tiles) <= 24, "czech should be small, not comparable to Germany"

    def test_czech_has_exactly_five_explicit_ports(self):
        m = build_map("czech_republic")
        assert len(m.ports) == 5

    def test_czech_port_mix_three_two_to_one_two_three_to_one(self):
        m = build_map("czech_republic")
        resource_ports = [p for p in m.ports if p.resource is not None]
        generic_ports = [p for p in m.ports if p.resource is None]
        assert len(resource_ports) == 3
        assert len(generic_ports) == 2
        assert all(p.ratio == 2 for p in resource_ports)
        assert all(p.ratio == 3 for p in generic_ports)

    def test_czech_port_coords_match_json(self):
        raw = _load_polygon("czech_republic")
        m = build_map("czech_republic")
        json_keys = {
            (int(p["q"]), int(p["r"]), int(p["side"]))
            for p in raw["ports"]
        }
        built_keys = {(p.q, p.r, p.side) for p in m.ports}
        assert json_keys == built_keys

    def test_czech_ports_anchored_on_real_land_tiles(self):
        m = build_map("czech_republic")
        land = {(t.q, t.r) for t in m.tiles}
        for p in m.ports:
            assert (p.q, p.r) in land, (
                f"port at ({p.q},{p.r}) is not on a land tile"
            )
            assert 0 <= p.side <= 5

    def test_at_least_one_inland_facing_side(self):
        """Proves inland sides are allowed — at least one czech port has
        its side pointing at another land hex (i.e. NOT facing the void).
        Coastal auto-detect would never produce such a port."""
        m = build_map("czech_republic")
        land = {(t.q, t.r) for t in m.tiles}
        inland_facing = 0
        for p in m.ports:
            dq, dr = HEX_DIRECTIONS[p.side]
            if (p.q + dq, p.r + dr) in land:
                inland_facing += 1
        assert inland_facing >= 1, (
            "inland ports feature should allow sides pointing at land"
        )

    def test_czech_resource_types_parsed(self):
        m = build_map("czech_republic")
        resources = {p.resource for p in m.ports if p.resource is not None}
        assert Resource.WHEAT in resources
        assert Resource.SHEEP in resources
        assert Resource.ORE in resources


class TestGermanyStillAutoDetects:
    def test_germany_has_no_explicit_ports_in_json(self):
        raw = _load_polygon("germany")
        assert "ports" not in raw or not raw.get("ports")

    def test_germany_still_produces_coastal_ports(self):
        m = build_map("germany")
        assert len(m.ports) > 0, "germany should still get auto-detected ports"

    def test_germany_ports_face_void(self):
        m = build_map("germany")
        land = {(t.q, t.r) for t in m.tiles}
        for p in m.ports:
            dq, dr = HEX_DIRECTIONS[p.side]
            assert (p.q + dq, p.r + dr) not in land, (
                f"germany port at ({p.q},{p.r},side={p.side}) faces a land "
                f"hex — auto-detect should only produce coastal ports"
            )


class TestRegistration:
    def test_czech_in_registry(self):
        from app.maps.definitions import MAP_REGISTRY
        assert "czech_republic" in MAP_REGISTRY
        m = MAP_REGISTRY["czech_republic"]()
        assert m.map_id == "czech_republic"
