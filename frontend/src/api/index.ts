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

export function getRoomState(roomId: string): Promise<RoomState> {
  return request<RoomState>(`/rooms/${roomId}`)
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
