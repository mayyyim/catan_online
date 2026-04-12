# Catan Map Redesign Tracker

**Project**: Redesign all 28 Catan maps so each board's tile layout matches the silhouette of its real-world country/continent.
**Map file**: `backend/app/maps/definitions.py`
**Renderer**: `scripts/render_maps_png.py` -> `/tmp/catan_maps/<map_id>.png`
**Last updated**: 2026-04-11
**Status**: PIVOT — hand-crafting abandoned, switching to polygon-to-hex rasterizer.

---

## 0. Pivot rationale (2026-04-11)

After committing 28 hand-crafted maps (last commit `69ccd2b`), user feedback: *"many country maps are still not good, especially China."* Root causes:

1. **Manual axial-coord editing is error-prone.** Each map = dozens of `(q,r)` tuples hand-tuned; shapes drift into blobs.
2. **Inconsistent quality.** Phase 1 (9 maps) read well; Phase 2 (19 maps) quality degraded as agents raced.
3. **No ground truth.** Without a real-world polygon reference, "does this look like China?" is subjective per agent.
4. **Rework cost is linear.** Fixing China by hand = fix India by hand = fix Russia by hand. No leverage.
5. **Port coords couple to tiles.** Every hand edit risks orphan ports; we've already hit R1 multiple times.

**Decision**: Replace hand-crafting with a **polygon-to-hex rasterizer**. Feed real country GeoJSON/outline polygons into a deterministic function that returns `(q,r)` tile lists + port coords. One pipeline, 28 maps, reproducible.

**Parallel workstreams kicked off**:
- Elon Musk (`visionary-elon-musk`): first-principles technical verdict — is this the right pivot, what can we delete, what's the real bottleneck. **In progress.**
- Software Architect (`engineering-software-architect`): design doc at `logs/map_rasterizer_design.md`. **In progress.**

Phases 1 & 2 (hand-crafted) remain committed as fallback; they will be **replaced wholesale** once Phase 5 ships.

---

## 1. Scope (unchanged)

- **Exactly 28 maps**: 25 standard + 3 XL.
- **Standard (25)**: china, japan, usa, europe, uk, australia, brazil, antarctica, india, canada, russia, egypt, mexico, korea, indonesia, new_zealand, france, germany, argentina, south_africa, italy, scandinavia, spain, turkey, vietnam
- **XL (3)**: africa_xl, eurasia_xl, americas_xl

---

## 2. New phased plan

| Phase | Goal | Owner | Status | Blocks |
|-------|------|-------|--------|--------|
| P1    | Hand-craft 9 maps (legacy)                   | dev team                  | done (committed `484c334`) | — |
| P2    | Hand-craft 19 maps (legacy)                  | dev team                  | done (committed `69ccd2b`)  | — |
| **P3**| **Build rasterizer core module**             | Backend API Dev #1        | pending                      | design doc |
| **P4**| **Author per-country polygon data (28)**     | Backend API Dev #2        | pending                      | design doc + P3 |
| **P5**| **Generate + QA + replace `definitions.py`** | Backend API Dev #3 + QA   | pending                      | P3 + P4 |

### Phase 3 — Rasterizer core
Deliverable: a Python module (target: `backend/app/maps/rasterizer.py`) exposing:
- `polygon_to_hexes(polygon, target_tile_count, hex_size) -> list[(q,r)]`
- `detect_coastal_edges(hexes) -> list[(q,r,dir)]` for port candidates
- `assign_terrains(hexes, distribution) -> dict[(q,r), terrain]`
- `pack_map_definition(map_id, ...) -> dict` in the shape `definitions.py` expects

### Phase 4 — Polygon data
Deliverable: `backend/app/maps/polygons/<map_id>.json` for all 28 maps.
Source: simplified real-world outlines (e.g. Natural Earth 110m admin-0, hand-simplified to ~20–60 vertices per country). Offshore islands included as multipolygons.

### Phase 5 — Generation + QA + cutover
Deliverable: regenerated `definitions.py` for all 28 maps, PNGs in `/tmp/catan_maps/`, all tests green. Single commit replacing the hand-crafted definitions.

---

## 3. Task breakdown with owners

| # | Task | Owner | Status | Blocked on |
|---|------|-------|--------|-----------|
| T1 | Technical verdict on rasterizer pivot (first principles) | `visionary-elon-musk` | **in-progress** | — |
| T2 | Design doc `logs/map_rasterizer_design.md` (algorithm, data shapes, API surface) | `engineering-software-architect` | **in-progress** | — |
| T3 | Implement rasterizer core (`polygon_to_hexes`, hex rounding, connected-component filter) | Backend API Dev #1 | pending | T2 |
| T4 | Implement coastal-edge / port detection + terrain assignment | Backend API Dev #3 | pending | T2 |
| T5 | Author 28 polygon JSON files under `backend/app/maps/polygons/` | Backend API Dev #2 | pending | T2 |
| T6 | Integration: CLI `scripts/generate_maps.py` that consumes polygons → writes `definitions.py` | Backend API Dev #1 | pending | T3, T4 |
| T7 | Generate all 28 maps + render PNGs | Backend API Dev #3 | pending | T5, T6 |
| T8 | Visual QA sweep across all 28 PNGs | QA | pending | T7 |
| T9 | Fix-round for any rejected maps (polygon tweaks only, no code) | Backend API Dev #2 | pending | T8 |
| T10| Run `pytest tests/` (expect 144 passed) + `python scripts/e2e_smoke.py` (expect 14/14) | QA | pending | T9 |
| T11| Single commit replacing `definitions.py`; update `project_catan_backlog.md` | Backend API Dev #1 | pending | T10 |

---

## 4. Acceptance criteria (per generated map)

Each of the 28 maps must satisfy **all** of:

| # | Criterion | Check |
|---|-----------|-------|
| A1 | PNG visually matches the real country silhouette | Human QA on `/tmp/catan_maps/<map_id>.png` |
| A2 | Every `_port(q,r,dir)` references a tile present in the layout | Static lint in rasterizer |
| A3 | Ports sit on coastal (non-interior) edges | `detect_coastal_edges` output |
| A4 | Tile count in range — standard: **16–24**, XL: **36–45** | Assert in generator |
| A5 | Number-token count == non-desert tile count | Assert in generator |
| A6 | At least 3 distinct terrains (standard) / 4 (XL) | Assert in generator |
| A7 | Robber starts on a desert tile | Assert in generator |
| A8 | `pytest tests/` → **144 passed** | CI |
| A9 | `python scripts/e2e_smoke.py` → **14/14 passed** | CI |
| A10| Tile layout is a single connected component (except intentional offshore islands declared in polygon) | Rasterizer post-check |

---

## 5. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Polygon data quality — simplified outlines lose recognizable features (Italy's boot, Korea's peninsula) | High | Map fails A1 | Hand-tune vertex count per country; preview overlay before commit |
| R2 | Hex rounding edge cases — tiles appear/disappear near polygon boundary depending on centroid test | High | Flaky tile count, jagged coast | Use cube-coord rounding + area-overlap threshold (not just centroid-in) |
| R3 | Missing/misnamed country in source data (e.g. antarctica, scandinavia as non-ISO, XL composites) | Medium | No polygon for 3+ maps | Manual polygon authoring fallback for XL + antarctica + scandinavia |
| R4 | Rasterizer bugs — off-by-one in q/r, wrong orientation (pointy vs flat top) | Medium | All 28 maps wrong | Unit tests for rasterizer on synthetic shapes (square, circle) before real data |
| R5 | Hand-crafted maps regress mid-pivot — someone edits `definitions.py` while rasterizer is in-flight | Medium | Merge conflict, lost fixes | Freeze `definitions.py` until Phase 5 cutover; pivot branch if needed |
| R6 | Port detection places ports on internal lakes or inland seas | Medium | A3 fails | Coastal edge = edge adjacent to a non-tile hex, not just any edge |
| R7 | Terrain distribution skews (all desert Egypt, all forest Canada) | Low | A6 fails | Distribution config per climate zone; override per map |
| R8 | Generated tile count outside budget for small countries (e.g. uk, korea) | Medium | A4 fails | Tunable `target_tile_count` per map; rasterizer scales hex_size to fit |
| R9 | XL composites (africa_xl, eurasia_xl, americas_xl) need multi-country polygon unions | Medium | Generation fails | Polygon JSON supports multipolygon; union at load time |
| R10| Pivot takes longer than hand-fixing the worst 5 maps | Medium | Wasted effort | Elon verdict (T1) gates Phase 3 start; abort if verdict says "just fix China" |

---

## 6. Map status table

All 28 maps are currently **hand-crafted-committed**; all need **rasterize**. `rasterize-complete` flips true only after A1–A10 all pass.

| # | map_id        | size | legacy state              | polygon authored | rasterized | PNG QA | final |
|---|---------------|------|---------------------------|------------------|------------|--------|-------|
| 1 | italy         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 2 | uk            | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 3 | japan         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 4 | australia     | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 5 | france        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 6 | korea         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 7 | indonesia     | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 8 | new_zealand   | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
| 9 | brazil        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|10 | china         | std  | hand-crafted-committed (flagged by user) | [ ] | [ ]        | [ ]    | [ ]   |
|11 | usa           | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|12 | india         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|13 | egypt         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|14 | canada        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|15 | russia        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|16 | germany       | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|17 | spain         | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|18 | mexico        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|19 | europe        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|20 | scandinavia   | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|21 | turkey        | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|22 | vietnam       | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|23 | argentina     | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|24 | south_africa  | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|25 | antarctica    | std  | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|26 | africa_xl     | XL   | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|27 | eurasia_xl    | XL   | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |
|28 | americas_xl   | XL   | hand-crafted-committed    | [ ]              | [ ]        | [ ]    | [ ]   |

Legend: `[ ]` pending · `[x]` done · `[!]` needs-fix

---

## 7. Next actions (immediate)

1. **Wait on T1 (Elon verdict)** — if verdict is "abort pivot, just fix China", fall back to hand-fix on flagged maps.
2. **Wait on T2 (design doc)** — unblocks T3/T4/T5.
3. **Freeze `backend/app/maps/definitions.py`** — no hand edits until Phase 5 cutover.
4. **Queue T3/T4/T5 agents** — dispatch in parallel once T2 lands.
5. **Update `project_catan_backlog.md`** — mark map-redesign initiative as "pivot in progress".

<!--
STATUS SUMMARY (for user):
Rewrote tracker to reflect the pivot. Phases 1-2 (28 hand-crafted maps, committed through 69ccd2b) are frozen as fallback. New plan is Phase 3 rasterizer core, Phase 4 polygon data (28 JSON files), Phase 5 generate + QA + single-commit cutover replacing definitions.py. Tasks T1-T11 assigned: Elon (verdict, in-progress), Software Architect (design doc, in-progress), three Backend API Devs split across rasterizer core / polygon data / port+terrain, QA for visual sweep + test gates. Acceptance criteria A1-A10 enforce silhouette match, valid ports, tile-count budget (16-24 std / 36-45 XL), 144 pytest, 14/14 e2e. Risk register focuses on polygon data quality, hex rounding, missing countries (antarctica/scandinavia/XL composites), rasterizer bugs, and regression freeze on definitions.py. All 28 maps tabled as hand-crafted-committed needing rasterize; china flagged per user feedback. Immediate blocker: waiting on Elon verdict + design doc before dispatching T3/T4/T5.
-->
