# Dev Cards Frontend Implementation

**Date**: 2026-04-10  
**Agent**: Frontend Developer

## What was implemented

1. **Types** (`src/types/index.ts`):
   - Added `DevCardType` union type and `DevCard` interface
   - Added `road_building`, `year_of_plenty`, `monopoly` to `TurnPhase`

2. **Game.tsx** — BackendGameState updates:
   - Player type: `dev_cards`, `knights_played`, `dev_card_played_this_turn`
   - Root: `dev_card_deck_count`, `current_turn_number`, `largest_army_holder`, `largest_army_size`

3. **Game.tsx** — State and handlers:
   - State: `devCards`, `currentTurn`, `devCardPlayed`, `deckCount`, `yopSelection`, `monopolyResource`, `playingCard`
   - Handlers: `handleBuyDevCard`, `handlePlayKnight`, `handlePlayYearOfPlenty`, `handlePlayMonopoly`, `handlePlayRoadBuilding`, `handlePlayDevCard`, `handleYopChange`
   - Game state message handler extracts dev card data from own player
   - `dev_card_played` WS message handler for log notifications
   - `buildableEdges` extended for `road_building` turn phase

4. **Game.tsx** — UI:
   - Dev Card Hand panel with card list, play buttons, buy button
   - Year of Plenty resource picker (2 resources, +/- controls)
   - Monopoly resource picker (click-to-select)
   - Road Building hint during `road_building` turn phase
   - Turn step display shows dev card phases
   - Players panel shows knights played count and Largest Army badge
   - Largest Army special card display

5. **Game.module.css** — New styles:
   - `.devCardList`, `.devCardItem`, `.devCardItem.playable`
   - `.devCardIcon`, `.devCardName`, `.devCardNew`, `.devCardPlayBtn`
   - `.buyDevCardBtn`
   - `.yopPanel`, `.monopolyPanel`, `.roadBuildingHint`

## Files changed
- `frontend/src/types/index.ts`
- `frontend/src/pages/Game.tsx`
- `frontend/src/pages/Game.module.css`

## UI design decisions
- Dev card panel placed between Resources and Build panels for easy access
- Year of Plenty uses same +/- control pattern as discard UI for consistency
- Monopoly uses clickable items (reuses devCardItem styling)
- Knight playable in both pre_roll and post_roll phases
- VP cards shown but not playable (no Play button)
- Cards bought this turn marked with "NEW" badge
- Road Building auto-enables edge placement (no build mode toggle needed)
- Green accent for Year of Plenty panel, orange for Monopoly — distinct from red robber panels

## Known limitations
- VP card auto-reveal at game end not implemented (needs backend support)
- No animation when a card is played
- Dev card count in other players' hands not shown (needs backend to send dev_card_count per player)
- No tooltip showing card effect descriptions
