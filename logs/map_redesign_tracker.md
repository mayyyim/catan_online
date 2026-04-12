# Catan Map Redesign Tracker

**Project**: Redesign all 28 Catan maps so each board's tile layout matches the silhouette of its real-world country/continent.
**Map file**: `backend/app/maps/definitions.py`
**Renderer**: `scripts/render_maps_png.py` -> `/tmp/catan_maps/<map_id>.png`
**Last updated**: 2026-04-11

---

## 1. Scope

- **Exactly 28 maps**: 25 standard + 3 XL.
- **Standard (25)**: china, japan, usa, europe, uk, australia, brazil, antarctica, india, canada, russia, egypt, mexico, korea, indonesia, new_zealand, france, germany, argentina, south_africa, italy, scandinavia, spain, turkey, vietnam
- **XL (3)**: africa_xl, eurasia_xl, americas_xl

### Completion criteria (per map)
A map is **done** only when **all four** are true:
1. **Shape recognizable** — silhouette reads as the target country at a glance from the rendered PNG.
2. **Ports valid** — every `_port(q, r, ...)` references a tile actually present in the layout (no orphan ports).
3. **Unit tests pass** — `pytest tests/` shows 144/144 passed.
4. **E2E passes** — `python scripts/e2e_smoke.py` shows 14/14 passed.

### Tile-count budget
- Standard maps: **14–24 tiles** (target ~18–21).
- XL maps: **37–45 tiles**.
- Number-token count must equal non-desert tile count.

---

## 2. Task list (per map)

| # | map_id        | phase | status        | commit   | notes |
|---|---------------|-------|---------------|----------|-------|
| 1 | italy         | P1    | done          | 484c334  | Boot+leg shape clear, Sicily/Sardinia islands present, ports on coast. |
| 2 | uk            | P1    | done          | 484c334  | GB main island + Ireland separated; one stray empty desert hex top-left, verify intentional. |
| 3 | japan         | P1    | done          | 484c334  | Diagonal arc reads as Honshu; Hokkaido + Kyushu + Okinawa fragments present. |
| 4 | australia     | P1    | done          | 484c334  | Solid landmass + Tasmania below; outline reads well. |
| 5 | france        | P1    | done          | 484c334  | Hexagon shape correct; Corsica fragment SE. |
| 6 | korea         | P1    | done          | 484c334  | Vertical peninsula + Jeju island; clean. |
| 7 | indonesia     | P1    | done          | 484c334  | Archipelago of 5 island clusters; reads well. |
| 8 | new_zealand   | P1    | done          | 484c334  | North + South + Stewart islands, separated; clean. |
| 9 | brazil        | P1    | done          | 484c334  | Bulky South American silhouette; coast on east. |
|10 | china         | P2-b1 | done          | pending  | Diamond bulk + Hainan/Taiwan offshoot; acceptable. |
|11 | usa           | P2-b1 | done          | pending  | Continental sweep w/ Alaska?-not visible; verify Alaska/Hawaii intent. |
|12 | india         | P2-b1 | done          | pending  | Diamond/triangle subcontinent + Sri Lanka fragment SE; good. |
|13 | egypt         | P2-b1 | done          | pending  | Rectangular desert block + Nile strip; reads well. |
|14 | canada        | P2-b1 | done          | pending  | Wide diagonal sweep, sparse east; acceptable, possibly too thin. |
|15 | russia        | P2-b1 | done          | pending  | Long horizontal sweep west->east; good. |
|16 | germany       | P2-b1 | done          | pending  | Compact central block; acceptable. |
|17 | spain         | P2-b1 | done          | pending  | Iberia square + Balearics + Canaries; good. |
|18 | mexico        | P2-b1 | done          | pending  | Diagonal funnel + Baja peninsula upper-left; acceptable. |
|19 | europe        | P2-b2 | done          | pending  | Continental cluster, rendered; verify against spec. |
|20 | scandinavia   | P2-b2 | in-progress   | -        | Agent running. |
|21 | turkey        | P2-b2 | in-progress   | -        | Agent running. |
|22 | vietnam       | P2-b2 | in-progress   | -        | Agent running. |
|23 | argentina     | P2-b2 | in-progress   | -        | Agent running. |
|24 | south_africa  | P2-b2 | in-progress   | -        | Agent running. |
|25 | antarctica    | P2-b2 | in-progress   | -        | Agent running. |
|26 | africa_xl     | P2-b2 | in-progress   | -        | XL, agent running. |
|27 | eurasia_xl    | P2-b2 | in-progress   | -        | XL, agent running. |
|28 | americas_xl   | P2-b2 | in-progress   | -        | XL, agent running. |

Status legend: `done` (edited & QA-passed) / `in-progress` (agent running) / `pending` (not started) / `needs-fix` (rejected in QA).

---

## 3. QA checklist (per map)

For each rendered PNG verify:

- [ ] **Silhouette match** — outline reads as the target country without the title label.
- [ ] **Port placement** — every port hex sits on a coastal edge (not landlocked).
- [ ] **Port validity** — every `_port(q, r, dir)` coord exists in the tile list.
- [ ] **Island separation** — offshore islands (Sicily, Hainan, Tasmania, etc.) are visually disconnected from the mainland.
- [ ] **Tile count** — 14–24 (standard) or 37–45 (XL).
- [ ] **Token count == non-desert tile count.**
- [ ] **Terrain distribution reasonable** — no map is 100% desert; resources roughly balanced (≥3 distinct terrains for standard).
- [ ] **No floating singletons** — except intentional small islands.
- [ ] **Robber starts on a desert tile.**

---

## 4. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Port `_port(q,r,...)` references a tile that doesn't exist after redesign | High | Game crash on load | Validation pass after each batch; unit test for orphan ports. |
| R2 | Bad/unrecognizable shape — looks like a blob, not the country | Medium | Player confusion, rework | Visual QA pass on every render before commit. |
| R3 | Game balance broken — terrain/number distribution skewed | Medium | Bad gameplay | Enforce token-count and terrain-mix checks per map. |
| R4 | Coordinate math mistakes in axial (q,r) — tiles overlap or leave gaps | Medium | Rendering bug | Render PNG immediately after each edit; reject overlaps. |
| R5 | Tile count outside 14–24 / 37–45 budget | Low | Test failures | Tile-count assert in tests. |
| R6 | Three parallel agents conflict on the same file | Medium | Merge conflict | Each agent owns disjoint map_ids; rebase per agent before commit. |
| R7 | Renderer caches old PNGs, masking regressions | Low | False QA pass | Force-regenerate before QA. |
| R8 | E2E suite hits maps not yet in test fixture, fails post-rename | Low | CI red | Run `e2e_smoke.py` before single P2 commit. |
| R9 | XL maps blow tile budget (37–45) | Medium | Test failure | Strict count check on africa_xl/eurasia_xl/americas_xl. |
| R10| Stale empty hex artifacts (e.g. empty desert top-left of uk render) | Low | Visual noise | Re-inspect after fix round. |

---

## 5. Next steps (after the 3 in-progress agents finish)

1. **Visual QA sweep** — re-render `/tmp/catan_maps/` and view all 28 PNGs; mark any as `needs-fix` in the table above.
2. **Fix round** — dispatch fixes for any rejected maps; re-render; re-QA.
3. **Port validation pass** — grep `_port(` and confirm every coord exists in the tile list of its map.
4. **Run unit tests** — `pytest tests/` must be **144 passed**.
5. **Run e2e** — `python scripts/e2e_smoke.py` must be **14/14 passed**.
6. **Single Phase 2 commit** — stage `backend/app/maps/definitions.py` and any test updates; one commit covering all 19 Phase 2 maps with message `feat(maps): redesign 19 maps to country shapes (Phase 2)`.
7. **Update `logs/TODO.md`** — close the map-redesign task.
8. **Update memory backlog** — mark the redesign initiative complete in `project_catan_backlog.md`.

---

## 6. Initial QA verdicts (already-rendered maps)

Verdict scale: PASS / MINOR / FIX.

### Phase 1 (committed, `484c334`)
- italy — **PASS**. Boot + Sicily + Sardinia clear.
- uk — **MINOR**. GB+Ireland fine, but a stray empty desert hex floats top-left of mainland; confirm intentional or remove.
- japan — **PASS**. Honshu arc + Hokkaido + Kyushu + Okinawa fragment present.
- australia — **PASS**. Mainland + Tasmania.
- france — **PASS**. Hexagon body + Corsica.
- korea — **PASS**. Vertical peninsula + Jeju islet.
- indonesia — **PASS**. 5 distinct island groups, reads as archipelago.
- new_zealand — **PASS**. North + South + Stewart, well separated.
- brazil — **PASS**. South-America bulk silhouette.

### Phase 2 batch 1 (edited, not committed)
- china — **PASS**. Diamond mainland + offshore SE fragment (Hainan/Taiwan).
- usa — **MINOR**. Continental sweep good; **verify Alaska/Hawaii intent** — none visible in render.
- india — **PASS**. Subcontinent triangle + Sri Lanka fragment.
- egypt — **PASS**. Rectangular block w/ Nile-aligned strip.
- canada — **MINOR**. Diagonal sweep; eastern provinces look thin/sparse — confirm Maritimes present.
- russia — **PASS**. Long west-east sweep, recognizable.
- germany — **PASS**. Compact central-Euro block.
- spain — **PASS**. Iberia + Balearics + Canaries fragments.
- mexico — **PASS**. Diagonal funnel + Baja peninsula offshoot.

### Phase 2 batch 2 (rendered so far)
- europe — **PASS**. Continental cluster present (one of 3 batch-2 agents already wrote it). Re-confirm against spec when full batch completes.
- scandinavia, turkey, vietnam, argentina, south_africa, antarctica, africa_xl, eurasia_xl, americas_xl — **PENDING render**.
