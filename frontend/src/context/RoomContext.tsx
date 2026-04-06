import { createContext, useContext, useReducer, useCallback, type ReactNode } from 'react'
import type { RoomState, Player } from '../types'

type RoomUpdater = (prev: RoomState | null) => RoomState | null

interface RoomContextValue {
  room: RoomState | null
  myPlayerId: string | null
  setRoom: (room: RoomState | RoomUpdater) => void
  setMyPlayerId: (id: string) => void
  updatePlayer: (player: Player) => void
  removePlayer: (playerId: string) => void
}

type RoomAction =
  | { type: 'SET_ROOM'; room: RoomState }
  | { type: 'UPDATE_ROOM'; updater: RoomUpdater }
  | { type: 'SET_PLAYER_ID'; id: string }
  | { type: 'UPDATE_PLAYER'; player: Player }
  | { type: 'REMOVE_PLAYER'; playerId: string }

interface RoomStore {
  room: RoomState | null
  myPlayerId: string | null
}

function roomReducer(state: RoomStore, action: RoomAction): RoomStore {
  switch (action.type) {
    case 'SET_ROOM':
      return { ...state, room: action.room }
    case 'UPDATE_ROOM':
      return { ...state, room: action.updater(state.room) }
    case 'SET_PLAYER_ID':
      return { ...state, myPlayerId: action.id }
    case 'UPDATE_PLAYER': {
      if (!state.room) return state
      const players = state.room.players.map(p =>
        p.id === action.player.id ? action.player : p,
      )
      return { ...state, room: { ...state.room, players } }
    }
    case 'REMOVE_PLAYER': {
      if (!state.room) return state
      const players = state.room.players.filter(p => p.id !== action.playerId)
      return { ...state, room: { ...state.room, players } }
    }
    default:
      return state
  }
}

const RoomContext = createContext<RoomContextValue | null>(null)

export function RoomProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(roomReducer, {
    room: null,
    myPlayerId: null,
  })

  const setRoom = useCallback((roomOrUpdater: RoomState | RoomUpdater) => {
    if (typeof roomOrUpdater === 'function') {
      dispatch({ type: 'UPDATE_ROOM', updater: roomOrUpdater as RoomUpdater })
      return
    }
    dispatch({ type: 'SET_ROOM', room: roomOrUpdater })
  }, [])

  const setMyPlayerId = useCallback((id: string) => {
    dispatch({ type: 'SET_PLAYER_ID', id })
  }, [])

  const updatePlayer = useCallback((player: Player) => {
    dispatch({ type: 'UPDATE_PLAYER', player })
  }, [])

  const removePlayer = useCallback((playerId: string) => {
    dispatch({ type: 'REMOVE_PLAYER', playerId })
  }, [])

  return (
    <RoomContext.Provider
      value={{
        room: state.room,
        myPlayerId: state.myPlayerId,
        setRoom,
        setMyPlayerId,
        updatePlayer,
        removePlayer,
      }}
    >
      {children}
    </RoomContext.Provider>
  )
}

export function useRoom(): RoomContextValue {
  const ctx = useContext(RoomContext)
  if (!ctx) throw new Error('useRoom must be used inside RoomProvider')
  return ctx
}
