// ─── Resource & Terrain ──────────────────────────────────────────────────────

export type TerrainType =
  | 'forest'
  | 'hills'
  | 'fields'
  | 'pasture'
  | 'mountains'
  | 'desert'
  | 'ocean'

export type ResourceType = 'wood' | 'brick' | 'wheat' | 'sheep' | 'ore'

export const TERRAIN_COLORS: Record<TerrainType, string> = {
  forest: '#2d6a4f',
  hills: '#b85c38',
  fields: '#ffd60a',
  pasture: '#74c69d',
  mountains: '#6c757d',
  desert: '#e9c46a',
  ocean: '#023e8a',
}

export const TERRAIN_LABELS: Record<TerrainType, string> = {
  forest: '🌲',
  hills: '🧱',
  fields: '🌾',
  pasture: '🐑',
  mountains: '⛰️',
  desert: '🏜️',
  ocean: '🌊',
}

export const RESOURCE_LABELS: Record<ResourceType, string> = {
  wood: '🌲',
  brick: '🧱',
  wheat: '🌾',
  sheep: '🐑',
  ore: '⛏️',
}

// ─── Map / Hex ────────────────────────────────────────────────────────────────

export interface HexTile {
  q: number   // cube coordinate
  r: number
  s: number
  terrain: TerrainType
  token?: number  // dice number token (2-12, absent for desert/ocean)
  robber?: boolean
}

export interface HexVertex {
  id: string         // "q,r,s:v0" through ":v5"
  tiles: string[]    // adjacent tile ids
}

export interface HexEdge {
  id: string         // "q,r,s:e0" through ":e5"
  vertices: [string, string]
}

// ─── Players ─────────────────────────────────────────────────────────────────

export type PlayerColor = '#e63946' | '#f4a261' | '#2a9d8f' | '#6a4c93'

export const PLAYER_COLORS: PlayerColor[] = [
  '#e63946',
  '#f4a261',
  '#2a9d8f',
  '#6a4c93',
]

export interface Player {
  id: string
  name: string
  color: PlayerColor
  isHost: boolean
  connected: boolean
  resources: Record<ResourceType, number>
  victoryPoints: number
  settlements: number  // remaining to place
  cities: number       // remaining to place
  roads: number        // remaining to place
}

// ─── Buildings ───────────────────────────────────────────────────────────────

export type BuildingType = 'settlement' | 'city'

export interface Building {
  vertexId: string
  playerId: string
  type: BuildingType
}

export interface Road {
  edgeId: string
  playerId: string
}

// ─── Game State ───────────────────────────────────────────────────────────────

export type GamePhase =
  | 'waiting'
  | 'setup_round1'
  | 'setup_round2'
  | 'playing'
  | 'finished'

export type TurnPhase =
  | 'pre_roll'
  | 'post_roll'
  | 'robber'
  | 'discard'
  | 'building'
  | 'done'

export interface GameState {
  roomId: string
  phase: GamePhase
  turnPhase: TurnPhase
  currentPlayerId: string
  players: Player[]
  tiles: HexTile[]
  buildings: Building[]
  roads: Road[]
  lastDiceRoll?: [number, number]
  longestRoadPlayerId?: string
  largestArmyPlayerId?: string
  winner?: string
}

// ─── Room ─────────────────────────────────────────────────────────────────────

export interface MapConfig {
  id: string
  name: string
  description: string
  preview: TerrainType[][]  // rough grid for thumbnail
}

export interface RoomState {
  roomId: string
  inviteCode: string
  hostId: string
  players: Player[]
  selectedMapId: string
  randomSeed: string
  maxPlayers: number
  status: 'waiting' | 'started'
}

// ─── WebSocket Messages ───────────────────────────────────────────────────────

export type ClientMessage =
  | { type: 'roll_dice' }
  | { type: 'build_settlement'; vertexId: string }
  | { type: 'build_city'; vertexId: string }
  | { type: 'build_road'; edgeId: string }
  | { type: 'end_turn' }
  | { type: 'move_robber'; tileId: string; stealFrom?: string }
  | { type: 'discard_resources'; resources: Partial<Record<ResourceType, number>> }
  | { type: 'maritime_trade'; give: ResourceType; receive: ResourceType }
  | { type: 'select_map'; mapId: string; seed?: string }
  | { type: 'start_game' }
  | { type: 'ping' }

export type ServerMessage =
  | { type: 'game_state'; state: GameState }
  | { type: 'room_state'; state: RoomState }
  | { type: 'player_joined'; player: Player }
  | { type: 'player_left'; playerId: string }
  | { type: 'error'; message: string }
  | { type: 'pong' }
