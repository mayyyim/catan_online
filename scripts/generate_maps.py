"""
CLI: rasterize polygon JSON -> MapData, optionally render PNG / verify / write.
"""

from __future__ import annotations

import argparse
import ast
import glob
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(HERE, "..", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from rasterizer import build_map, InfeasibleMap, POLYGON_DIR  # noqa: E402
from app.game.models import MapData  # noqa: E402


def _render(map_data: MapData, slug: str, out_dir: str) -> str:
    from render_maps_png import render_map  # type: ignore
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{slug}.png")
    render_map(map_data, path, title=f"{slug} ({len(map_data.tiles)}T/{len(map_data.ports)}P)")
    return path


def _verify_playable(map_data: MapData) -> tuple[bool, str]:
    try:
        from app.game.models import GameState, Player
        from app.game.board import can_place_settlement, valid_vertices, valid_edges

        game = GameState(
            room_id="test",
            map_data=map_data,
            players=[
                Player(player_id="p0", name="A", color="red"),
                Player(player_id="p1", name="B", color="blue"),
            ],
        )
        vv = valid_vertices(map_data)
        if len(vv) < 10:
            return False, f"Too few valid vertices: {len(vv)}"
        ve = valid_edges(map_data)
        if len(ve) < 15:
            return False, f"Too few valid edges: {len(ve)}"
        placeable = 0
        for vk in vv:
            ok, _ = can_place_settlement(vk, "p0", game, setup_phase=True)
            if ok:
                placeable += 1
        if placeable < 5:
            return False, f"Too few placeable settlement positions: {placeable}"
        tile_coords = {(t.q, t.r) for t in map_data.tiles}
        for p in map_data.ports:
            if (p.q, p.r) not in tile_coords:
                return False, f"Port at ({p.q},{p.r}) has no tile"
        deserts = sum(1 for t in map_data.tiles if t.tile_type.value == "desert")
        if deserts not in (1, 2):
            return False, f"Wrong desert count: {deserts}"
        for t in map_data.tiles:
            if t.tile_type.value != "desert" and t.token is None:
                return False, f"Non-desert tile ({t.q},{t.r}) missing token"
        return True, f"vv={len(vv)} ve={len(ve)} placeable={placeable} deserts={deserts}"
    except Exception as e:
        return False, f"Exception: {e}"


def _emit_function_source(slug: str, map_data: MapData) -> str:
    """Produce a python source snippet defining `{slug}_map()` returning MapData."""
    func_name = f"{slug}_map"
    lines = [f"def {func_name}() -> MapData:", "    tiles = ["]
    for t in map_data.tiles:
        token_s = f", {t.token}" if t.token is not None else ""
        lines.append(f'        _tile({t.q}, {t.r}, "{t.tile_type.value}"{token_s}),')
    lines.append("    ]")
    lines.append("    ports = [")
    for p in map_data.ports:
        if p.resource is None:
            lines.append(f"        _port({p.q}, {p.r}, ratio=3, side={p.side}),")
        else:
            lines.append(
                f'        _port({p.q}, {p.r}, "{p.resource.value}", ratio={p.ratio}, side={p.side}),'
            )
    lines.append("    ]")
    lines.append(f'    return normalize_ports(MapData(map_id="{slug}", tiles=tiles, ports=ports))')
    lines.append("")
    return "\n".join(lines)


def _ast_replace_function(source: str, slug: str, new_source: str) -> str:
    """AST-based replacement of a top-level def `{slug}_map` function body."""
    func_name = f"{slug}_map"
    tree = ast.parse(source)
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            target = node
            break
    if target is None:
        # Append new function at end of module.
        return source.rstrip() + "\n\n\n" + new_source + "\n"
    src_lines = source.splitlines(keepends=True)
    start = target.lineno - 1
    end = getattr(target, "end_lineno", None)
    if end is None:
        # Find next top-level def/class after start.
        next_line = len(src_lines)
        for node in tree.body:
            if node is target:
                continue
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                if node.lineno - 1 > start:
                    next_line = min(next_line, node.lineno - 1)
        end = next_line
    prefix = "".join(src_lines[:start])
    suffix = "".join(src_lines[end:])
    replacement = new_source if new_source.endswith("\n") else new_source + "\n"
    return prefix + replacement + suffix


def _write_to_definitions(slug: str, map_data: MapData) -> None:
    defs_path = os.path.join(BACKEND_DIR, "app", "maps", "definitions.py")
    with open(defs_path, "r", encoding="utf-8") as f:
        source = f.read()
    new_func = _emit_function_source(slug, map_data)
    new_source = _ast_replace_function(source, slug, new_func)
    with open(defs_path, "w", encoding="utf-8") as f:
        f.write(new_source)


def _process(slug: str, args) -> bool:
    print(f"[{slug}] building...")
    if args.dry_run:
        print(f"[{slug}] (dry-run) would rasterize and build map")
        return True
    try:
        map_data = build_map(slug)
    except InfeasibleMap as e:
        print(f"[{slug}] FAILED: {e}")
        return False
    except Exception as e:
        print(f"[{slug}] ERROR: {e}")
        traceback.print_exc()
        return False
    print(f"[{slug}] tiles={len(map_data.tiles)} ports={len(map_data.ports)}")
    ok = True
    if args.verify:
        vp, msg = _verify_playable(map_data)
        print(f"[{slug}] Playability: {'PASS' if vp else 'FAIL'} ({msg})")
        ok = ok and vp
    if args.render:
        try:
            path = _render(map_data, slug, "/tmp/catan_maps")
            print(f"[{slug}] rendered -> {path}")
        except Exception as e:
            print(f"[{slug}] render failed: {e}")
            traceback.print_exc()
    if args.write and ok:
        _write_to_definitions(slug, map_data)
        print(f"[{slug}] wrote into definitions.py")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", help="slug to generate")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    slugs: list[str] = []
    if args.all:
        for p in sorted(glob.glob(os.path.join(POLYGON_DIR, "*.json"))):
            slugs.append(os.path.splitext(os.path.basename(p))[0])
    elif args.country:
        slugs.append(args.country)
    else:
        parser.error("--country SLUG or --all required")

    failures = 0
    for slug in slugs:
        ok = _process(slug, args)
        if not ok:
            failures += 1
    if failures:
        print(f"{failures} failure(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
