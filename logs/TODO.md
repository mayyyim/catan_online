# Catan Online — Project TODO

> 跨会话接续用。每次会话结束前必须更新。
> 四段式：进行中 / 待办 / 已完成 / 阻塞中

---

## 进行中

（无）

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

### 2026-04-12

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
