import type { MapConfigPayload, MapTopologyPayload, RoomState } from '../types'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface CreateRoomResponse {
  room_id: string
  invite_code: string
  host_player_id: string
}

export interface JoinRoomResponse {
  room_id: string
  player_id: string
  player_name: string
  color: string
}

export function createRoom(playerName: string): Promise<CreateRoomResponse> {
  return request<CreateRoomResponse>('/rooms', {
    method: 'POST',
    body: JSON.stringify({ host_name: playerName }),
  })
}

export function joinRoom(
  inviteCode: string,
  playerName: string,
): Promise<JoinRoomResponse> {
  return request<JoinRoomResponse>(`/rooms/${inviteCode}/join`, {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName }),
  })
}

type BackendRoomStatusResponse = {
  room_id: string
  invite_code: string
  host_player_id: string
  state: string
  player_count: number
  players: Array<{
    player_id: string
    name: string
    color: string
    connected: boolean
  }>
  selected_map_id?: string
}

export async function getRoomState(roomId: string): Promise<RoomState> {
  const raw = await request<BackendRoomStatusResponse>(`/rooms/${roomId}`)
  return {
    roomId: raw.room_id,
    inviteCode: raw.invite_code,
    hostId: raw.host_player_id,
    players: (raw.players ?? []).map((p, idx) => ({
      id: p.player_id,
      name: p.name,
      color: p.color as any,
      isHost: p.player_id === raw.host_player_id || idx === 0,
      connected: !!p.connected,
      resources: { wood: 0, brick: 0, wheat: 0, sheep: 0, ore: 0 },
      victoryPoints: 0,
      settlements: 0,
      cities: 0,
      roads: 0,
    })),
    selectedMapId: raw.selected_map_id ?? 'random',
    randomSeed: '',
    maxPlayers: 4,
    status: raw.state === 'waiting' ? 'waiting' : 'started',
    rules: { victory_points_target: 10, friendly_robber: false, starting_resources_double: false },
  }
}

export interface AddBotResponse {
  room_id: string
  player_id: string
  player_name: string
  color: string
}

export function addBot(roomId: string, name = 'Bot', difficulty = 'medium'): Promise<AddBotResponse> {
  return request<AddBotResponse>(`/rooms/${roomId}/bots`, {
    method: 'POST',
    body: JSON.stringify({ name, difficulty }),
  })
}

export function removeBot(roomId: string, playerId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/rooms/${roomId}/players/${playerId}`, {
    method: 'DELETE',
  })
}

// ─── Auth endpoints ─────────────────────────────────────────────────────────

export interface AuthUser {
  user_id: string
  username: string
  display_name: string
  token: string
  elo_rating: number
  games_played: number
  games_won: number
  is_guest?: boolean
}

export function authRegister(username: string, password: string, displayName: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password, display_name: displayName }),
  })
}

export function authLogin(username: string, password: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function authGuest(): Promise<AuthUser> {
  return request<AuthUser>('/auth/guest', { method: 'POST' })
}

export function authMe(token: string): Promise<AuthUser> {
  return request<AuthUser>('/auth/me', {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  })
}

// ─── Stats / Leaderboard endpoints ───────────────────────────────────────────

export interface LeaderboardEntry {
  rank: number
  user_id: string
  display_name: string
  elo_rating: number
  games_played: number
  games_won: number
  win_rate: number
}

export interface PlayerProfile {
  user_id: string
  display_name: string
  elo_rating: number
  games_played: number
  games_won: number
  total_vp: number
  win_rate: number
  avg_vp: number
  recent_games: Array<{
    id: string
    map_id: string
    player_count: number
    turns: number
    finished_at: string | null
    won: boolean
    players: Array<{
      user_id: string | null
      name: string
      player_id: string
      color: string
      victory_points: number
      is_bot: boolean
    }>
  }>
}

export function fetchLeaderboard(limit = 20): Promise<{ leaderboard: LeaderboardEntry[] }> {
  return request<{ leaderboard: LeaderboardEntry[] }>(`/stats/leaderboard?limit=${limit}`)
}

export function fetchProfile(userId: string): Promise<PlayerProfile> {
  return request<PlayerProfile>(`/stats/profile/${userId}`)
}

export function fetchMyStats(token: string): Promise<PlayerProfile> {
  return request<PlayerProfile>('/stats/my-stats', {
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
  })
}

// ─── Map gallery endpoints ────────────────────────────────────────────────────

export interface MapSummaryTile { q: number; r: number; tile_type: string }
export interface MapSummary { map_id: string; size: 'standard' | 'large'; tiles: MapSummaryTile[] }
export interface MapSummaryList { maps: MapSummary[] }

export function fetchMapSummaries(): Promise<MapSummaryList> {
  return request<MapSummaryList>('/maps')
}

export interface MapDetailTile {
  q: number; r: number
  tile_type: string; token: number | null; resource: string | null
}
export interface MapDetailPort {
  q: number; r: number; side: number; resource: string | null; ratio: number
}
export interface MapDetailData {
  map_id: string; size: 'standard' | 'large'
  tiles: MapDetailTile[]; ports: MapDetailPort[]
}

export function fetchMapDetail(mapId: string): Promise<MapDetailData> {
  return request<MapDetailData>(`/maps/${mapId}`)
}

// ─── Map editor endpoints (dev/admin) ─────────────────────────────────────────
// These endpoints may be served by the backend when map editing is enabled.

export function getMapConfig(roomId: string): Promise<MapConfigPayload> {
  return request<MapConfigPayload>(`/rooms/${roomId}/map`)
}

export function setMapConfig(roomId: string, payload: MapConfigPayload): Promise<MapConfigPayload> {
  return request<MapConfigPayload>(`/rooms/${roomId}/map`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function getMapTopology(roomId: string): Promise<MapTopologyPayload> {
  return request<MapTopologyPayload>(`/rooms/${roomId}/topology`)
}

export function setMapTopology(roomId: string, payload: MapTopologyPayload): Promise<MapTopologyPayload> {
  return request<MapTopologyPayload>(`/rooms/${roomId}/topology`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
