# Polygon-to-Hex Map Rasterizer — Design Doc

Status: Proposed · Owner: Architect · Replaces: hand-crafted `backend/app/maps/definitions.py`

## 1. Pipeline stages

```
country.json (polygon)
      │
      ▼
[1 load]──►[2 rasterize]──►[3 cluster islands]──►[4 assign terrain]
                                                        │
                                                        ▼
                                      [5 place tokens]──►[6 detect ports]──►MapData
```
Each stage is a pure function; stages 4–6 take a `seed: int` for reproducibility.

## 2. Polygon data format

JSON, GeoJSON-compatible subset. One file per map under `backend/app/maps/data/polygons/<slug>.json`.

```json
{
  "slug": "italy",
  "name": "Italy",
  "size": "standard",            // standard | xl
  "biome_hints": {"hills": 0.25, "mountains": 0.25, "fields": 0.3, "forest": 0.15, "pasture": 0.05},
  "polygons": [                  // MultiPolygon: each entry is one island
    {"exterior": [[x,y], ...], "holes": [[[x,y], ...]]},
    {"exterior": [[x,y], ...], "holes": []}
  ]
}
```
Coordinates are arbitrary 2D (lon/lat from Natural Earth works directly). Multi-part polygons map 1:1 to islands.

## 3. Point-in-polygon → hex mapping

```python
def rasterize(poly: MultiPolygon, target_tiles: int, seed: int) -> list[Hex]:
    bbox = poly.bounds
    # binary-search hex scale s so that #covered ≈ target_tiles
    s = fit_scale(poly, target_tiles)        # 15–25 or 35–45
    hexes = set()
    for q, r in hex_grid_covering(bbox, s):
        cx, cy = 1.5*q*s, math.sqrt(3)*(q/2 + r)*s
        if poly.contains(Point(cx, cy)):
            hexes.add((q, r))
    # island pass: any polygon part with 0 hexes → force nearest hex
    for part in poly.parts:
        if not any(h in part for h in hexes):
            hexes.add(nearest_hex_to_centroid(part, s))
    return recenter(hexes)                   # shift so centroid ≈ (0,0)
```
- **Scale fit**: binary search on `s` until `|covered| ∈ [target·0.9, target·1.1]`.
- **Tiny islands**: guaranteed ≥1 hex via centroid fallback; disjoint components separated by ≥1 empty hex ring so topology sees them as distinct (no `neighbor()` edges cross the gap).
- **Cluster detection**: BFS on hex adjacency after rasterization to label islands.

## 4. Terrain assignment

Deterministic given `(slug, seed)`. Default seed = `hash(slug)`.

```python
def assign_terrain(hexes, hints, seed) -> dict[Hex, str]:
    rng = Random(seed)
    n = len(hexes)
    counts = scale_distribution(CATAN_BASE, n, hints)  # 1 desert + 5 resources
    bag = shuffle(expand(counts), rng)
    return dict(zip(sorted(hexes), bag))               # sorted → stable
```
`biome_hints` nudges base ratios (e.g. Switzerland → more mountains) but desert count is fixed (1 standard, 2 XL). Fully reproducible; no hand-tuning per map beyond hints.

## 5. Token placement

Standard Catan bag scaled to `n_land - n_desert`: `[2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12]`. Desert gets no token.

Algorithm — **constraint-driven backtracking** (classic "no red numbers touching" rule):
```python
def place_tokens(land_hexes, seed) -> dict[Hex, int]:
    rng = Random(seed)
    for _ in range(100):
        bag = shuffle(token_bag(len(land_hexes)), rng)
        assignment = try_assign(land_hexes, bag)       # DFS, reject if 6/8 adjacent
        if assignment: return assignment
    raise InfeasibleMap(slug)                           # caller falls back
```
Adjacency via existing `topology.neighbors()`. 100 shuffles is empirically sufficient for n≤45.

## 6. Port detection

```python
def detect_ports(land: set[Hex], seed) -> list[Port]:
    coastal = [(h, d) for h in land for d in DIRS if neighbor(h,d) not in land]
    rng = Random(seed)
    rng.shuffle(coastal)
    target = round(len(land) * 0.35)                   # ~7 for 19 tiles, ~15 for 45
    picked = pick_spaced(coastal, min_gap=2)[:target]  # greedy, ≥2 edges apart
    types = balanced_port_types(target)                # 1 of each resource + 3:1s
    return [Port(h, r=3 if t=="any" else 2, side=d, resource=t)
            for (h,d), t in zip(picked, types)]
```
`min_gap` prevents port clumping. Islands get ports proportional to their land share.

## 7. File structure

```
backend/app/maps/
  data/polygons/*.json                  # 28 files, ~30 lines each
  rasterizer/
    __init__.py
    polygon.py          ~120  # load, MultiPolygon, point-in-poly
    hex_raster.py       ~150  # rasterize(), fit_scale, island cluster
    terrain.py          ~100  # assign_terrain, distribution scaling
    tokens.py           ~120  # bag, backtracking placer
    ports.py            ~ 90  # coastal detect + spacing
    pipeline.py         ~ 80  # build_map(slug) → MapData
  definitions.py        ~ 40  # now just: MAPS = {slug: build_map(slug) for slug in list_polygons()}
  generator.py                # unchanged, consumes MapData
```
Total new code ≈ 660 LOC, replacing ~1500 LOC of hand-crafted definitions.

## 8. Data source

**Pick: (a) Natural Earth 1:50m `admin_0_countries` shapefile**, pre-processed once into the JSON schema above, then checked into the repo. Rationale:

| Option | Time-to-28-maps | Dep weight | Editable | Accuracy |
|---|---|---|---|---|
| Natural Earth (baked JSON) | hours | zero at runtime | yes | high |
| Hand-coded literals | days | zero | painful | low |
| ASCII-art | days | zero | ok | very low |

Conversion is a one-shot dev script (`scripts/bake_polygons.py`, uses `shapefile` lib in dev only). Runtime has **no GIS dependencies** — just stdlib JSON + math. Best of both worlds.

## 9. Validation / QA

Three-layer gate:
1. **Hard invariants (CI)**: every generated map passes `validate(MapData)` — correct tile counts, token bag conservation, zero 6/8 adjacency, ports on true coastal edges, all land reachable within each island.
2. **Shape fidelity metric**: IoU between union of hex centers (buffered) and source polygon ≥ 0.6 for standard, ≥ 0.7 for XL. Logged per map; regression if it drops.
3. **Visual review**: `scripts/render_maps.py` outputs PNG per map to `logs/map_previews/`. Manual eyeball pass once, then only on IoU regressions.

No per-map golden files — that just recreates the hand-crafting problem.

## 10. Migration plan

1. Land rasterizer + pipeline behind feature flag `USE_RASTERIZER` (default off).
2. Bake 28 polygons; run pipeline; diff against current `definitions.py`. Expect differences — that's the point.
3. Playtest 3 maps (small/medium/XL) end-to-end in the game engine.
4. Flip flag on; keep old `definitions.py` as `definitions_legacy.py` for one release as fallback on `InfeasibleMap`.
5. CI job runs `pytest tests/maps/test_rasterizer.py` which regenerates all 28 maps and asserts invariants + IoU thresholds. Generated maps are **not** checked in — they're built at server startup and cached in memory.
6. Remove legacy after one green release.

**Reversibility**: every stage is pure and seeded, so any bad map is fixed by either tweaking `biome_hints` or bumping `seed` in the polygon JSON — no code changes.
