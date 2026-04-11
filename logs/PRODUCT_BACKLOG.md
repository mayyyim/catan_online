# Catan Online -- Product Optimization Backlog
> Generated: 2026-04-11
> Status: Draft for review
> Auditor: Alex (Product Manager Agent)

## Executive Summary

Catan Online is a functional MVP with solid core mechanics: setup placement, dice rolling, resource production, bank trading, robber flow, development cards, longest road, and largest army are all implemented. The game can be played end-to-end with 2-4 players (humans + bots). However, compared to competitors like Colonist.io and Catan Universe, the product has critical gaps in **player-to-player trading** (a defining Catan mechanic that is completely missing), **game end experience** (no victory screen, no play-again flow), and **mobile usability** (fixed 700x680 map, no responsive layout). The bot AI is naive (random placement), there are no user accounts, and the game lacks sound, animations, and tutorial -- all of which are table-stakes for retention.

**Top 3 priorities:** (1) Player-to-player trading, (2) Victory/game-over screen, (3) Mobile responsiveness.

---

## Priority Matrix

### P0 -- Must Fix (Blocking / Game-Breaking)

- [ ] **P0-01 Player-to-Player Trading** -- The most iconic Catan mechanic is completely absent. Only bank trading (4:1/3:1/2:1) exists. Without P2P trading, the game is fundamentally incomplete. Colonist.io, Catan Universe, and every physical Catan game have this. *Impact: Game-defining mechanic, #1 reason experienced players would bounce.* *Effort: L*

- [ ] **P0-02 Victory / Game Over Screen** -- When a player reaches 10 VP, the game phase changes to `finished` but the frontend has NO victory screen, celebration, or even a clear indication. `winner_id` is set in state but never rendered. Players see... nothing special. *Impact: The climax of every game is a non-event. Massive anti-climax.* *Effort: S*

- [ ] **P0-03 Dev Card Deck Leak in WebSocket Broadcast** -- `GameState.to_dict()` serializes the FULL `dev_card_deck` (all undrawn cards with their types) and broadcasts it to ALL clients. A player opening browser DevTools can see every remaining card in the deck. This is a cheating vector. The log at `dev_cards_backend.md` explicitly flags this as a known issue. *Impact: Competitive integrity destroyed for any tech-savvy player.* *Effort: S*

- [ ] **P0-04 Resource Visibility to All Players** -- `to_dict(hide_resources=False)` is hardcoded in `GameState.to_dict()` (models.py line 388). Every player's exact resource hand is sent to every client. In standard Catan, you only know your own resources and others' total count. Browser DevTools reveals all. *Impact: Fundamental fairness violation. Undermines trading strategy.* *Effort: S*

- [ ] **P0-05 No "Return to Lobby" or "Play Again" Flow** -- After game ends, there is no way to start a new game, return to the room, or go home. The player is stuck on a dead game screen. Must manually navigate. *Impact: 100% of completed games end with user confusion.* *Effort: S*

- [ ] **P0-06 AFK / Disconnected Player Handling During Game** -- If a human player disconnects mid-game (closes browser, loses internet), the game freezes on their turn forever. No timeout, no auto-skip, no bot takeover. The run log notes WebSocket reconnection works, but there is no timeout mechanism. *Impact: One disconnect kills the game for all players.* *Effort: M*

### P1 -- High Priority (Major UX Improvement)

- [ ] **P1-01 Mobile Responsiveness** -- The HexGrid component has hardcoded `width={700} height={680}`. The side panel layout uses a fixed two-column CSS grid. On mobile devices, the game is unplayable. Colonist.io works on mobile; this doesn't. *Impact: Entire mobile audience excluded. ~50% of casual game traffic.* *Effort: L* *Files: `Game.tsx` line 754-768, `HexGrid.tsx` props, `Game.module.css`*

- [ ] **P1-02 Sound Effects** -- Zero audio in the entire application. No dice roll sound, no build sound, no turn notification, no resource collection jingle, no victory fanfare. Sound is a core part of game feel. *Impact: Game feels lifeless compared to every competitor.* *Effort: M*

- [ ] **P1-03 Turn Notification When It's Your Turn** -- No browser notification, no sound, no visual pulse when it becomes your turn. If you alt-tab while waiting, you have no idea it's your turn. *Impact: Multiplayer games drag because players don't know it's their turn.* *Effort: S* *Files: `Game.tsx` WebSocket message handler*

- [ ] **P1-04 Tutorial / First-Time User Onboarding** -- No tutorial, no rules explanation, no tooltips on game mechanics. A new player has zero guidance on what to do during setup, what resources are for, how trading works, or what development cards do. *Impact: New player retention will be near-zero without guidance.* *Effort: L*

- [ ] **P1-05 Dice Roll Animation** -- The `DiceDisplay` component shows static numbers. No rolling animation, no 3D dice, no bounce effect. The `rolling` state just shows "Rolling..." text for 600ms. Dice rolling is a core excitement moment in Catan. *Impact: Most frequent game action feels flat.* *Effort: M* *Files: `components/DiceDisplay`, `Game.tsx` line 480*

- [ ] **P1-06 Resource Card Limit (7-card rule on non-robber turns)** -- The 7-card discard rule on rolling a 7 IS implemented. But the standard rule that you cannot hold more than 7 cards at end of turn is NOT enforced (this is actually the same rule -- you discard when 7 is rolled, not at end of turn -- so this is correct per standard rules). However, there is no visual warning when you have >7 cards that you are at risk. *Impact: Players don't realize they should spend down resources.* *Effort: S*

- [ ] **P1-07 Build Cost Reference Always Visible** -- Build costs are only shown as emoji tooltips on build buttons (e.g., `title="Road (1 wood + 1 brick)"`). No always-visible cost reference card like Colonist.io has. New players constantly forget costs. *Impact: Friction on every build decision.* *Effort: S* *Files: `Game.tsx` build panel section*

- [ ] **P1-08 Setup Phase UX Clarity** -- During setup, the only indication of what to do is a small text "Setup: place a settlement" in the turn banner. No arrow pointing to the board, no highlighting of what "your turn in setup" means, no explanation of snake draft order. *Impact: Confusing first experience for every new player.* *Effort: M*

- [ ] **P1-09 Trade Ratio Display Per Port** -- The trade panel shows ratios per resource but there's no visual on the board showing which ports YOUR settlements are connected to. Players must mentally map port positions to their buildings. *Impact: Port strategy is opaque to casual players.* *Effort: M*

- [ ] **P1-10 Game Log Insufficient** -- The log only captures builds, trades, and dev card plays. Missing: dice roll results, resource production details, robber movements, who stole from whom, setup placements. Colonist.io shows a detailed log of every action. *Impact: Can't follow what happened on other players' turns.* *Effort: M* *Files: `Game.tsx` WebSocket message handler, backend broadcast events*

### P2 -- Medium Priority (Polish & Enhancement)

- [ ] **P2-01 Chat System** -- No in-game chat whatsoever. No text chat, no emoji reactions, no quick-chat phrases. Multiplayer social interaction is zero. *Impact: Social deduction and negotiation (core Catan) impossible.* *Effort: M*

- [ ] **P2-02 Building Placement Animation** -- When a settlement, city, or road is placed, it just appears instantly. No drop animation, no glow effect, no "pop" feedback. *Impact: Building feels unrewarding.* *Effort: S* *Files: `HexGrid.tsx` building rendering*

- [ ] **P2-03 Resource Production Notification** -- When dice are rolled and resources are distributed, there is no visual showing which tiles produced and who got what. Resources just silently update in the count. *Impact: Players miss the cause-effect of dice rolls.* *Effort: M*

- [ ] **P2-04 Keyboard Shortcuts** -- No keyboard shortcuts for common actions: R for roll, E for end turn, 1-3 for build modes, T for trade. Power users (who play many games) will want these. *Impact: Slower gameplay for repeat players.* *Effort: S*

- [ ] **P2-05 Spectator Mode** -- No way to watch a game in progress without being a player. Useful for tournaments, learning, and social sharing. *Impact: Limits viral/social potential.* *Effort: M*

- [ ] **P2-06 Game Timer / Turn Timer** -- No time limit per turn. A player can sit on their turn indefinitely (if they don't disconnect). Colonist.io has configurable turn timers. *Impact: Games can drag. Griefing vector.* *Effort: M* *Files: backend `engine.py` turn handling, frontend timer display*

- [ ] **P2-07 Undo Last Action** -- No undo support for misclicks. If you accidentally place a settlement on the wrong vertex, it's permanent. At minimum, allow undo during setup phase. *Impact: Frustrating misclicks, especially on mobile.* *Effort: M*

- [ ] **P2-08 VP Card Auto-Reveal at Game End** -- The frontend dev cards log explicitly notes: "VP card auto-reveal at game end not implemented." When a player wins with VP cards, other players can't see them. *Impact: Confusing win condition for observers.* *Effort: S* *Files: `Game.tsx` winner handling, backend `engine.py` game finish*

- [ ] **P2-09 Dev Card Tooltips** -- No tooltip showing what each development card does. A player holding "Year of Plenty" gets no explanation of the effect. *Impact: New players don't know what their cards do.* *Effort: S* *Files: `Game.tsx` dev card list rendering*

- [ ] **P2-10 Robber Placement Highlight** -- When placing the robber, land tiles should have a hover highlight showing they're clickable. Currently, clicking a tile works but there's no visual affordance. The tile cursor is not changed either. *Impact: Players don't know where to click.* *Effort: S* *Files: `HexGrid.tsx` tile rendering, `HexGrid.module.css`*

- [ ] **P2-11 Bank Resource Depletion Warning** -- Bank row shows remaining resources but no visual warning when a resource is completely depleted (0 in bank). Standard Catan: when bank runs out of a resource, nobody can collect it. Not sure if backend enforces this. *Impact: Players may not realize production is blocked.* *Effort: S* *Files: `Game.tsx` bank row, `engine.py` produce_resources*

- [ ] **P2-12 Other Players' Dev Card Count Display** -- The frontend log notes: "Dev card count in other players' hands not shown (needs backend to send dev_card_count per player)." Backend DOES send `dev_card_count` but the frontend opponent cards show `?` instead of the count. *Impact: Can't assess opponent threat level.* *Effort: S* *Files: `Game.tsx` opponent player cards*

- [ ] **P2-13 Largest Army / Longest Road Visual Indicators** -- The LR/LA badges on player cards are tiny "LR" and "LA" text spans. No trophy icon, no special card display like the physical game has. The game does track these, but the UI is minimal. *Impact: Major achievements feel invisible.* *Effort: S*

- [ ] **P2-14 Map Size Support in Game** -- Large maps (37 tiles) exist in the gallery and backend but the HexGrid auto-fit may not work well for very large maps in the fixed 700x680 viewport. Need testing and potentially different zoom defaults. *Impact: Large maps may be cramped or broken.* *Effort: S*

- [ ] **P2-15 Trade History in Log** -- Trades show in log but with limited detail. Should show exact resources exchanged and whether it was bank or P2P (once P0-01 is implemented). *Impact: Can't track trading patterns.* *Effort: S*

### P3 -- Nice to Have (Future Vision)

- [ ] **P3-01 User Accounts & Authentication** -- No auth system. Players are ephemeral (sessionStorage only). Closing the browser = identity gone. No persistent profile, no game history, no stats. *Impact: Zero retention mechanism. Can't build a community.* *Effort: XL*

- [ ] **P3-02 ELO / Rating System & Leaderboard** -- No competitive ranking. Without accounts (P3-01), this is impossible. But it's what keeps competitive players coming back to Colonist.io. *Impact: No competitive motivation for repeat play.* *Effort: L (depends on P3-01)*

- [ ] **P3-03 Game Replay / History** -- No way to review a completed game. No move history saved. When game ends, all state is lost. *Impact: Can't learn from past games or share great moments.* *Effort: L*

- [ ] **P3-04 Custom Rules / House Rules** -- No configurable rule variants: friendly robber, starting resources, VP target, map randomization options. Colonist.io offers many of these. *Impact: Limits replayability for friend groups.* *Effort: M*

- [ ] **P3-05 Multiple Game Modes** -- Only standard Catan. No Cities & Knights, no Seafarers expansion logic, no speed mode, no 1v1 mode. *Impact: Content ceiling for experienced players.* *Effort: XL*

- [ ] **P3-06 Bot Difficulty Levels** -- Bots have one difficulty: random/basic. No easy/medium/hard selection. Bot settlement placement is pure random retry (80 attempts). Bot trading is simplistic (4:1 only, no port awareness). *Impact: Bots are either too easy for experienced players or confusing for new ones.* *Effort: L*

- [ ] **P3-07 Quick Match / Matchmaking** -- No way to find opponents without sharing an invite link. No public lobby, no matchmaking queue, no "play now" button. *Impact: Solo visitors have no way to find a game.* *Effort: L*

- [ ] **P3-08 PWA / Installable App** -- No service worker, no manifest for installable web app. Would enable push notifications and home screen install on mobile. *Impact: Mobile engagement boost.* *Effort: M*

- [ ] **P3-09 Internationalization (i18n)** -- All strings are hardcoded in English. No localization framework. The map names suggest global appeal (country-themed maps). *Impact: Limits non-English audience.* *Effort: L*

- [ ] **P3-10 Dark/Light Theme Toggle** -- Currently dark theme only. Some players prefer light themes. No toggle. *Impact: Accessibility preference gap.* *Effort: S*

- [ ] **P3-11 Reconnection Grace Period with State Sync** -- WebSocket reconnection works but is basic. No explicit grace period, no queued messages during disconnect, no "reconnecting..." UI overlay. *Impact: Brief network blips may lose state.* *Effort: M*

- [ ] **P3-12 Analytics & Telemetry** -- No analytics integration. No way to measure feature adoption, session length, funnel completion, or error rates in production. *Impact: Flying blind on product decisions.* *Effort: M*

- [ ] **P3-13 Automated Testing Suite** -- No frontend tests, no E2E tests visible. Backend has some manual QA (57 test cases from run log) but no automated test runner in CI. *Impact: Regression risk increases with every feature.* *Effort: L*

---

## Detailed Specs

### P0-01 Player-to-Player Trading
**Problem:** The defining social mechanic of Catan is completely absent. The only trading available is bank trading (4:1 default, improved by ports). In standard Catan, on your turn during post_roll, you can propose a trade to other players: "I'll give you 1 wheat for 1 ore." Other players can accept, counter-offer, or reject. This negotiation is what makes Catan a social game rather than a pure optimization puzzle.
**Solution:** Implement a full P2P trading flow:
1. Active player opens "Trade with Players" panel, selects resources to offer and resources they want
2. Trade proposal is broadcast to all other players via WebSocket
3. Other players see a trade offer popup with Accept / Reject / Counter buttons
4. If accepted, resources swap. If countered, the counter-offer appears on the active player's screen
5. Active player can cancel the trade at any time
**Acceptance Criteria:**
- [ ] Active player can propose a trade specifying give/want resources during post_roll
- [ ] All other players see the trade proposal in real-time
- [ ] Any player can accept (resources swap atomically)
- [ ] Any player can reject (UI dismissed)
- [ ] Trade proposal can be cancelled by the proposer
- [ ] Backend validates both players have sufficient resources before executing
- [ ] Trade appears in game log with full details
**Files likely affected:** `backend/app/game/engine.py` (new `handle_player_trade`), `backend/app/routers/websocket.py` (new message types: `propose_trade`, `accept_trade`, `reject_trade`), `frontend/src/pages/Game.tsx` (trade UI), `frontend/src/ws/gameSocket.ts`
**Estimated effort:** L (3-5 days)

### P0-02 Victory / Game Over Screen
**Problem:** When `winner_id` is set and phase is `finished`, the frontend shows nothing special. The game just stops. No celebration, no stats summary, no call to action.
**Solution:** Render a full-screen overlay when `game.winner` is set:
1. Winner announcement with player name and color
2. Final scoreboard showing all players' VP breakdown (settlements, cities, longest road, largest army, VP cards)
3. MVP stats: most roads built, most resources collected, etc.
4. "Play Again" button (creates new room with same players)
5. "Back to Home" button
**Acceptance Criteria:**
- [ ] Overlay appears within 1 second of game ending
- [ ] Shows winner name, color, and final VP total
- [ ] Shows VP breakdown for all players
- [ ] "Play Again" navigates to new room with same player group
- [ ] "Back to Home" navigates to `/`
- [ ] Confetti or celebration animation for the winner
**Files likely affected:** `frontend/src/pages/Game.tsx` (new VictoryOverlay component), `frontend/src/pages/Game.module.css`
**Estimated effort:** S (0.5-1 day)

### P0-03 Dev Card Deck Leak in WebSocket Broadcast
**Problem:** `GameState.to_dict()` at models.py line 413 includes `"dev_card_deck": [c.to_dict() for c in self.dev_card_deck]`. This serializes every undrawn card type and broadcasts to all clients. Opening DevTools > Network > WS frames reveals the entire deck order.
**Solution:** Strip `dev_card_deck` from the broadcast payload. Only include `dev_card_deck_count`. Keep full serialization only for Redis persistence (use a separate `to_dict_for_storage()` or add a parameter).
**Acceptance Criteria:**
- [ ] WebSocket `game_state` messages do NOT contain `dev_card_deck` array
- [ ] `dev_card_deck_count` integer is still included
- [ ] Redis persistence still stores the full deck for game restoration
- [ ] Game continues to function correctly after page refresh
**Files likely affected:** `backend/app/game/models.py` (`GameState.to_dict`), `backend/app/routers/websocket.py` (broadcast call)
**Estimated effort:** S (1-2 hours)

### P0-04 Resource Visibility to All Players
**Problem:** `GameState.to_dict()` at models.py line 388 passes `hide_resources=False` for ALL players. Every player's exact resource hand is visible in WebSocket messages. Standard Catan: you know your own resources and others' total card count only.
**Solution:** Pass `viewer_player_id` to `to_dict()` and set `hide_resources=True` for all players except the viewer. The backend already has this parameter but it's unused.
**Acceptance Criteria:**
- [ ] Each player's WS `game_state` only contains their own resource breakdown
- [ ] Other players show `resource_count` (total) but individual resource amounts are hidden
- [ ] Dev cards for other players remain hidden (already working via `hide_resources`)
- [ ] Bot monopoly strategy updated to not rely on visible opponent resources (use resource_count heuristic instead)
**Files likely affected:** `backend/app/game/models.py` line 388, `backend/app/routers/websocket.py` (_game_state_msg), `backend/app/bots.py` (monopoly logic)
**Estimated effort:** S (2-3 hours)

### P0-05 No "Return to Lobby" or "Play Again" Flow
**Problem:** After game phase becomes `finished`, the UI has no navigation options. Players are stranded.
**Solution:** Add buttons to the victory overlay (P0-02) and also add a persistent "Leave Game" button in the top bar that works at any time (with confirmation dialog during active game).
**Acceptance Criteria:**
- [ ] "Leave Game" button visible in top bar during all game phases
- [ ] Confirmation dialog if game is in progress
- [ ] "Play Again" creates a new room and redirects all players
- [ ] "Back to Home" navigates to `/`
**Files likely affected:** `frontend/src/pages/Game.tsx` (top bar, victory overlay)
**Estimated effort:** S (half day)

### P0-06 AFK / Disconnected Player Handling During Game
**Problem:** If a player disconnects during their turn, the game halts indefinitely. No timeout, no bot takeover, no skip mechanism.
**Solution:** Implement a server-side turn timer:
1. When a player's turn starts, start a 60-second timer (configurable)
2. If the player doesn't act within the timer, auto-perform a default action (roll dice, end turn, discard randomly)
3. If a player is disconnected for >30 seconds during their turn, replace them with a bot for the remainder of the game
4. Broadcast timer state to all clients for display
**Acceptance Criteria:**
- [ ] Server tracks per-turn elapsed time
- [ ] After 60s of inactivity, auto-action is taken
- [ ] After 30s disconnect, bot takes over
- [ ] Reconnecting player resumes control (bot stops)
- [ ] Timer countdown visible in UI
**Files likely affected:** `backend/app/routers/websocket.py`, `backend/app/store.py`, `backend/app/bots.py`, `frontend/src/pages/Game.tsx`
**Estimated effort:** M (2-3 days)

### P1-05 Dice Roll Animation
**Problem:** DiceDisplay shows static text. The 600ms "Rolling..." state is a placeholder.
**Solution:** Replace with animated 3D-style dice using CSS transforms or a lightweight canvas animation. Show two dice faces tumbling and landing on the rolled values. Add a dice roll sound effect (pairs with P1-02).
**Acceptance Criteria:**
- [ ] Dice animate for ~1 second showing tumbling faces
- [ ] Final values clearly visible after animation
- [ ] Animation skippable by clicking
- [ ] Works on mobile (no WebGL dependency)
**Files likely affected:** `frontend/src/components/DiceDisplay/`, `frontend/src/pages/Game.tsx`
**Estimated effort:** M (1-2 days)

### P1-10 Game Log Insufficient
**Problem:** Log only captures: builds, trades, dev card plays, errors. Missing: dice results, resource gains, robber moves, steals, setup placements, turn starts/ends, bank depletion events.
**Solution:** Add backend broadcast events for all missing actions. Frontend appends them to the log with icons and player colors.
**Acceptance Criteria:**
- [ ] Dice roll results appear in log: "Player rolled 8 (4+4)"
- [ ] Resource production: "Player gained 2 wheat, 1 ore"
- [ ] Robber placement: "Player moved robber to (q,r)"
- [ ] Steal: "Player stole from Target"
- [ ] Setup: "Player placed settlement at ..."
- [ ] Turn boundaries: "--- Player's turn ---"
**Files likely affected:** `backend/app/routers/websocket.py` (broadcast events), `frontend/src/pages/Game.tsx` (log rendering)
**Estimated effort:** M (1-2 days)

### P3-06 Bot Difficulty Levels
**Problem:** Bots use random placement (up to 80 random attempts for settlement), no strategic evaluation, random robber placement, 50% random dev card purchase, no port-aware trading. This makes bots boring for experienced players and unpredictable (not in a fun way) for beginners.
**Solution:** Implement three difficulty levels:
- **Easy:** Current behavior, but with slight improvements (prefer hexes with tokens)
- **Medium:** Score vertices by resource diversity and probability. Use ports. Target opponents with robber.
- **Hard:** Full strategic AI: probability-weighted placement, road-toward-port planning, adaptive robber targeting (target leader), strategic dev card usage, counter-trading.
**Acceptance Criteria:**
- [ ] Room UI allows selecting bot difficulty when adding a bot
- [ ] Easy bots prefer tiles with tokens but are otherwise simple
- [ ] Medium bots evaluate vertex scores (sum of adjacent tile probabilities)
- [ ] Hard bots plan road networks toward ports and high-value vertices
- [ ] All difficulty levels complete games without errors
**Files likely affected:** `backend/app/bots.py` (major rewrite), `backend/app/routers/rest.py` (bot add endpoint), `frontend/src/pages/Room.tsx`
**Estimated effort:** L (5+ days)

---

## Competitive Gap Analysis

| Feature | Catan Online (This) | Colonist.io | Catan Universe |
|---------|---------------------|-------------|----------------|
| P2P Trading | Missing | Full with counter-offers | Full |
| Bank Trading | Done (4:1, ports) | Done | Done |
| Dev Cards | Done (all 5 types) | Done | Done |
| Robber | Done | Done | Done |
| Longest Road | Done | Done | Done |
| Largest Army | Done | Done | Done |
| Sound Effects | None | Full | Full |
| Dice Animation | None | Animated | 3D animated |
| Chat | None | Text + emoji | Text |
| Tutorial | None | Interactive tutorial | Video + guided |
| Accounts | None | Full + social | Full |
| Leaderboard | None | ELO + seasons | Ranking |
| Mobile | Broken | Full responsive | Native app |
| Spectator | None | Yes | Limited |
| Turn Timer | None | Configurable | Yes |
| Game Replay | None | Premium feature | No |
| Bot Quality | Random | Strategic (3 levels) | Strategic |
| Victory Screen | None | Celebration + stats | Celebration |
| Custom Rules | None | Many options | Limited |

---

## Recommended Execution Order

**Sprint 1 (Week 1): Critical Integrity & Game Completion**
1. P0-03 Dev card deck leak fix (2 hours)
2. P0-04 Resource visibility fix (3 hours)
3. P0-02 Victory screen (1 day)
4. P0-05 Play again / leave game flow (half day)

**Sprint 2 (Week 2): Core Missing Mechanic**
5. P0-01 Player-to-player trading (3-5 days)

**Sprint 3 (Week 3): Resilience & Responsiveness**
6. P0-06 AFK/disconnect handling (2-3 days)
7. P1-01 Mobile responsiveness (2-3 days)

**Sprint 4 (Week 4): Game Feel**
8. P1-02 Sound effects (2 days)
9. P1-05 Dice animation (1-2 days)
10. P1-03 Turn notification (half day)
11. P2-02 Building animation (1 day)

**Sprint 5 (Week 5): Onboarding & Polish**
12. P1-04 Tutorial (3-5 days)
13. P1-07 Build cost reference (half day)
14. P1-10 Game log improvement (1-2 days)
15. P2-09 Dev card tooltips (half day)
