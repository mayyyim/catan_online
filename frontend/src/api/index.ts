import type { RoomState } from '../types'

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
  player_id: string
}

export interface JoinRoomResponse {
  room_id: string
  player_id: string
}

export function createRoom(playerName: string): Promise<CreateRoomResponse> {
  return request<CreateRoomResponse>('/rooms', {
    method: 'POST',
    body: JSON.stringify({ player_name: playerName }),
  })
}

export function joinRoom(
  inviteCode: string,
  playerName: string,
): Promise<JoinRoomResponse> {
  return request<JoinRoomResponse>('/rooms/join', {
    method: 'POST',
    body: JSON.stringify({ invite_code: inviteCode, player_name: playerName }),
  })
}

export function getRoomState(roomId: string): Promise<RoomState> {
  return request<RoomState>(`/rooms/${roomId}`)
}
