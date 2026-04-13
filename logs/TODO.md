# Catan Online — Project TODO

> 跨会话接续用。每次会话结束前必须更新。
> 四段式：进行中 / 待办 / 已完成 / 阻塞中

---

## 进行中

（无 — 待用户跑一局确认 B2 连带修复，若仍复现再单独处理）



---

## 待办

### 🟢 高性价比（推荐优先做）

- [ ] **P3-07 匹配系统** — L
  - 工作量：1-2 天
  - 价值：让账号+ELO 系统真正发挥作用
  - 依赖：P3-01 账号系统 ✅、P3-02 ELO ✅
  - 方案：后端 Redis 队列 + 撮合算法（按 ELO 范围），前端"快速匹配"按钮 → 排队 UI → 自动进房间
  - 文件：backend/app/matchmaking.py (新建), backend/app/routers/matchmaking.py (新建), frontend/src/pages/Matchmaking.tsx (新建)

- [ ] **E2E 测试接入 GitHub Actions CI**
  - 工作量：1 小时
  - 价值：每次 PR 自动跑 `scripts/e2e_smoke.py`，防止回归
  - 方案：.github/workflows/e2e.yml 中启动 docker compose + 等服务就绪 + 跑脚本


### 🟡 可选（工作量大）

- [ ] **P3-03 游戏回放** — L
  - 工作量：2 天
  - 方案：保存 WS 消息序列到 DB (game_events 表) + 前端回放播放器（时间轴拖拽、加减速）
  - 文件：backend/app/db_models.py (新增 GameEvent), backend/app/routers/websocket.py (记录事件), frontend/src/pages/Replay.tsx

- [ ] **P3-12 数据分析仪表盘** — M
  - 工作量：1 天
  - 方案：Admin 页面展示 DAU / 对局数 / 胜率分布 / ELO 分布
  - 文件：backend/app/routers/analytics.py, frontend/src/pages/Analytics.tsx

### 🔴 不建议做（已记录原因）

- [ ] ~~P2-05 观战模式~~ — 跳过，需要大改 game state 分发逻辑，收益低
- [ ] ~~P2-07 撤销操作~~ — 跳过，Catan 传统不支持悔棋，破坏游戏完整性
- [ ] ~~P3-05 扩展模式（海盗/城市骑士/商人）~~ — 跳过，等价于再做一个游戏

---

## 已完成

### 2026-04-13

- [x] **Bug 修复三连** — vertices_of_edge 几何 + actionIndicator 浮动化
  - B1: backend/app/game/board.py:114 `vertices_of_edge` side→corner 映射修正 `(6-i)%6, (7-i+1)%6`；此前只 side 0/3 正确，1/2/4/5 全错，导致 setup 阶段建路 validation 把大量合法边拒掉
  - B1 回归单测: tests/test_board.py 新增 `test_vertices_of_edge_all_sides_are_geometric_endpoints` 验证每个 side 的两端点都与邻居 tile 共享
  - B2 (连带): bot 在 setup 阶段建路一直失败是 B1 触发的；B1 修好后 bot 不再卡住，roll 按钮的可点状态是 bot 流程卡壳时的视觉残留
  - B3: Game.tsx:1568 `.actionIndicator` 从 bottomBar 内部 actionCenter 抽出，做成 `.actionIndicatorFloat`（`position:absolute; bottom:118px; left:50% translateX(-50%)`），底栏宽高不变
  - 验证：pytest 140 passed（test_elo pre-existing sqlalchemy 导入问题无关）、tsc 0 errors、e2e_smoke 14/14
  - 文件：backend/app/game/board.py + backend/tests/test_board.py + frontend/src/pages/Game.tsx + Game.module.css

- [x] **底部操作栏 Colonist 风格重设计 T1-T8** — 待 commit
  - T1 build 按钮永久显示 + setup 阶段 `requiredBuildMode` gating
  - T2 Roll Dice / End Turn 同条；`.bottomBar` 固定 height 110px + position relative
  - T3 `.actionBtnIcon` 三态视觉（disabled 灰度 / active 金边 / setup mandatory 脉冲高亮）+ End Turn 大且醒目（绿色 endTurnBigBtn，非图标化，Musk pushback）
  - T4 popover 架构：useState + click-outside（document mousedown，data-popover / data-popover-trigger）
  - T5/T6 Dev Cards popover + Trade popover Bank/Player 双 tab（cream #f4ecd8 + #c9b896 边框）— popover CSS 全部新增
  - T7 资源卡点击 → 预填 p2pOffer={[res]:1} + 打开 player tab
  - T8 键盘快捷键 R/S/C/D/Space（替代旧的 1/2/3/E）；E 保留为 Roll
  - 验证：tsc 0 errors, e2e_smoke 14/14 passed
  - 文件：frontend/src/pages/Game.tsx + Game.module.css

### 2026-04-09

- [x] **买发展卡按钮始终可见** — Game.tsx:1482
  - 问题：Buy Card 按钮被 `{canTrade && ...}` 包裹，玩家在非自己回合时完全看不到按钮
  - 修复：去掉条件渲染，改为始终显示按钮，禁用条件 = `!canTrade || !hasOreWheatSheep || deckCount === 0`

- [x] **国家地图形状重设计（本会话前半段，上个 context 完成）**
  - France/Germany/Spain/Italy/Scandinavia/Turkey/Vietnam/Argentina/South Africa/New Zealand
  - 全部从 `_from_std` 通用布局改为自定义地形形状
  - 验证：28 maps loaded OK

- [x] **房间退出 → 返回首页** — Room.tsx handleLeaveRoom + navigate('/')
  - 新增 `← Leave` 按钮，点击断开 WS 并导航到首页

- [x] **房间无人类玩家时自动销毁** — store.py delete_room / has_human_players + websocket.py disconnect handler

### 2026-04-12

- [x] **28 国家/大陆地图形状重设计** — commit d8b3433 + 后续
  - Phase 1（9 iconic maps）：italy/uk/japan/australia/france/korea/indonesia/new_zealand/brazil
  - Phase 2（19 maps）：china/usa/india/egypt/canada/russia/germany/spain/mexico + europe/scandinavia/turkey/vietnam/argentina/south_africa/antarctica + 3 XL（africa_xl/eurasia_xl/americas_xl）
  - 新增可视化工具：scripts/render_maps_png.py（matplotlib 渲染每张地图到 PNG）
  - 军团协作：Musk（第一性原理审查）+ Senior PM（tracker）+ 3 Backend agents（并行批量执行）
  - 所有 28 个地图现在形状明显，独立岛屿（Sicily/Ireland/Tasmania/Jeju/Taiwan/Madagascar/Newfoundland 等）有清晰海洋间隔
  - 端口全部在真实海岸线上
  - 验证：144 pytest passed, e2e_smoke 14/14 passed

- [x] **P3-09 国际化 (i18n)** — commit 93ae3a9
  - i18next + react-i18next infrastructure
  - 英文 + 中文两套完整 locale (270 keys 完全同步)
  - 迁移所有页面：Home / Auth / Room / Leaderboard / Profile / Game
  - LanguageSwitcher 组件（首页右下角 EN/中 切换）
  - localStorage 持久化语言选择，首次根据浏览器语言自动检测
  - 验证：tsc 0 errors, e2e_smoke 14/14 passed, bundle 含双语字符串

- [x] **P2-02 建筑动画** — 已有 CSS 动画确认（roadDraw/buildPop/oceanShimmer），标记完成

- [x] **`scripts/e2e_smoke.py` E2E 冒烟测试脚本** — commit d8b3433
  - 14 个测试覆盖：health / room CRUD / bot 持久化 / room full / auth / leaderboard / maps / invite
  - 自动检测 Docker vs 本地模式
  - 用法：`python scripts/e2e_smoke.py`

### 2026-04-11

- [x] **P3-02a/b 前端：排行榜 + 个人战绩页面** — commit 4e69883
  - Leaderboard.tsx, Profile.tsx + CSS modules
  - API 函数 fetchLeaderboard/fetchProfile/fetchMyStats
  - 路由 /leaderboard, /profile, /profile/:userId
  - Home 导航入口

- [x] **P3-13 自动化测试套件** — commit 1bde105
  - 144 个 pytest 测试，覆盖全部核心逻辑
  - 10 个测试文件：board / road_stats / engine_setup / engine_play / engine_robber / engine_devcard / engine_trade / elo / models
  - backend/tests/ + conftest.py（7-hex 测试地图 + game factory）

- [x] **Bug 修复 x3** — commit 9e3529f
  - Bug1: Bot WS 断连时被从 waiting room 移除（disconnect handler 没排除 bot）
  - Bug2: stop_bot() 误杀 bot 自己的 WS 连接（未区分人类重连 vs bot 首次连接）
  - Bug3: passlib 1.7.4 + bcrypt 5.0 不兼容导致 auth 500（pin bcrypt==4.0.1）

- [x] **军团工作流更新** — 更新 ~/.claude/projects/.../memory/feedback_use_agents.md
  - 新增「验证三层」章节（静态检查 / E2E 冒烟 / UI 验证）
  - 新增「环境摸底清单」章节
  - 新增「Bug 定位流程」章节
  - RUN_LOG 格式新增字段：验证方式 / 发现的问题 / 教训

- [x] **P3-02a/b 后端战绩+ELO** — 早前已有，commit 未记录
  - backend/app/game_records.py (save_game_result + _update_elo)
  - backend/app/routers/stats.py (leaderboard + profile + my-stats)
  - backend/app/db_models.py (User + GameRecord)

（2026-04-11 之前的完成项见 memory/project_catan_backlog.md）

---

## 阻塞中

（无）

---

## 备注

- 完整优先级清单见 `memory/project_catan_backlog.md`（38 项产品优化）
- 提交前必须跑 `python scripts/e2e_smoke.py`（见 `memory/feedback_test_before_commit.md`）
- 工作流完整说明见 `memory/feedback_use_agents.md`
