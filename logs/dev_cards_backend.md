# Development Cards - Backend Implementation Log

**Date:** 2026-04-10
**Agent:** engineering-backend-api-developer

## What was implemented

Full development card system for Catan: models, deck creation, purchase/play handlers, all 5 card effects, largest army tracking, and VP recalculation.

### Card types implemented
- **Knight** (14 cards): Playable in PRE_ROLL or POST_ROLL. Moves robber (reuses existing robber flow). Tracks knights_played for largest army.
- **Victory Point** (5 cards): Auto-counted in VP calculation, cannot be played manually.
- **Year of Plenty** (2 cards): POST_ROLL only. Player picks exactly 2 resources from bank.
- **Monopoly** (2 cards): POST_ROLL only. Player names a resource, takes all of it from every other player.
- **Road Building** (2 cards): POST_ROLL only. Enters ROAD_BUILDING turn step, allows 2 free roads.

### Largest Army
- Minimum 3 knights to qualify.
- Checked after every knight play.
- Awards 2 VP to holder.

## Files changed

### backend/app/game/models.py
- Lines ~58-75: Added `ROAD_BUILDING`, `YEAR_OF_PLENTY`, `MONOPOLY` to `TurnStep` enum; new `DevCardType` enum
- Lines ~77-78: Added `DEV_CARD_COST` constant
- Lines ~197-213: Added `DevCard` dataclass with `to_dict`/`from_dict`
- Player dataclass: Added `dev_cards`, `knights_played`, `dev_card_played_this_turn` fields
- Player.to_dict(): Added `dev_cards` (hidden for other players), `dev_card_count`, `knights_played`, `dev_card_played_this_turn`
- Player.from_dict(): Restores all new fields
- GameState: Added `dev_card_deck`, `current_turn_number`, `largest_army_holder`, `largest_army_size`, `road_building_remaining`
- GameState.to_dict(): Serializes deck for Redis persistence + exposes `dev_card_deck_count` for clients
- GameState.from_dict(): Restores all new fields

### backend/app/game/engine.py
- `create_dev_card_deck()`: Creates standard 25-card deck, shuffled
- `handle_start_game()`: Initializes deck and turn number
- `recalculate_vp()`: Now includes VP cards and largest army bonus
- `handle_end_turn()`: Resets `dev_card_played_this_turn`, increments `current_turn_number`
- `handle_build()`: Supports free road placement during ROAD_BUILDING step
- `check_largest_army()`: Evaluates all players for >= 3 knights
- `handle_buy_dev_card()`: Validates resources/deck, deducts cost, pops card
- `handle_play_dev_card()`: Full dispatch for all 5 card types with validation

### backend/app/routers/websocket.py
- Added `buy_dev_card` message handler
- Added `play_dev_card` message handler with `dev_card_played` broadcast event

### backend/app/bots.py
- PRE_ROLL: Bot checks for playable knight, plays it before rolling
- POST_ROLL: Bot plays Year of Plenty (picks 2 lowest resources), Monopoly (picks resource others have most of), Road Building
- POST_ROLL: 50% chance to buy dev card if affordable and deck has cards
- ROAD_BUILDING: Bot places 2 free roads

## Design decisions

1. **Dev card deck serialized to Redis**: Full deck is included in `to_dict()` so `from_dict()` can restore it. Clients receive `dev_card_deck_count` only.
2. **Player dev_cards hidden from opponents**: `to_dict(hide_resources=True)` returns empty list for dev_cards but shows `dev_card_count`.
3. **Card play validation with rollback**: If params are invalid (e.g., Year of Plenty not totaling 2), card is put back in hand and `dev_card_played_this_turn` is reset.
4. **Knight reuses robber flow**: Playing a knight sets `turn_step = ROBBER_PLACE`, which feeds into the existing robber placement and steal flow.
5. **Bot dev card AI is simple**: Buys with 50% probability, plays all available non-VP cards opportunistically.

## Known limitations

- Bot monopoly strategy only considers raw resource counts from game state (which are visible in current implementation since hide_resources is False).
- Road Building for bots uses random placement; no pathfinding toward good positions.
- No player-to-player trading of dev cards (standard Catan rules forbid this anyway).
- The `dev_card_deck` is fully serialized in `to_dict()` -- the WebSocket broadcast currently sends this to all clients. Frontend should ignore the `dev_card_deck` field and use `dev_card_deck_count` only. A future improvement would strip the deck from the broadcast payload.
