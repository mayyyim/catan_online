import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  type ReactNode,
} from 'react'
import type { GameState, Building, Road } from '../types'

interface GameContextValue {
  game: GameState | null
  myPlayerId: string | null
  selectedVertexId: string | null
  selectedEdgeId: string | null
  setGame: (state: GameState) => void
  setMyPlayerId: (id: string) => void
  selectVertex: (id: string | null) => void
  selectEdge: (id: string | null) => void
}

type GameAction =
  | { type: 'SET_GAME'; state: GameState }
  | { type: 'SET_PLAYER_ID'; id: string }
  | { type: 'SELECT_VERTEX'; id: string | null }
  | { type: 'SELECT_EDGE'; id: string | null }
  | { type: 'ADD_BUILDING'; building: Building }
  | { type: 'ADD_ROAD'; road: Road }

interface GameStore {
  game: GameState | null
  myPlayerId: string | null
  selectedVertexId: string | null
  selectedEdgeId: string | null
}

function gameReducer(state: GameStore, action: GameAction): GameStore {
  switch (action.type) {
    case 'SET_GAME':
      return { ...state, game: action.state }
    case 'SET_PLAYER_ID':
      return { ...state, myPlayerId: action.id }
    case 'SELECT_VERTEX':
      return { ...state, selectedVertexId: action.id, selectedEdgeId: null }
    case 'SELECT_EDGE':
      return { ...state, selectedEdgeId: action.id, selectedVertexId: null }
    case 'ADD_BUILDING': {
      if (!state.game) return state
      const buildings = [...state.game.buildings, action.building]
      return { ...state, game: { ...state.game, buildings } }
    }
    case 'ADD_ROAD': {
      if (!state.game) return state
      const roads = [...state.game.roads, action.road]
      return { ...state, game: { ...state.game, roads } }
    }
    default:
      return state
  }
}

const GameContext = createContext<GameContextValue | null>(null)

export function GameProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(gameReducer, {
    game: null,
    myPlayerId: null,
    selectedVertexId: null,
    selectedEdgeId: null,
  })

  const setGame = useCallback((gs: GameState) => {
    dispatch({ type: 'SET_GAME', state: gs })
  }, [])

  const setMyPlayerId = useCallback((id: string) => {
    dispatch({ type: 'SET_PLAYER_ID', id })
  }, [])

  const selectVertex = useCallback((id: string | null) => {
    dispatch({ type: 'SELECT_VERTEX', id })
  }, [])

  const selectEdge = useCallback((id: string | null) => {
    dispatch({ type: 'SELECT_EDGE', id })
  }, [])

  return (
    <GameContext.Provider
      value={{
        game: state.game,
        myPlayerId: state.myPlayerId,
        selectedVertexId: state.selectedVertexId,
        selectedEdgeId: state.selectedEdgeId,
        setGame,
        setMyPlayerId,
        selectVertex,
        selectEdge,
      }}
    >
      {children}
    </GameContext.Provider>
  )
}

export function useGame(): GameContextValue {
  const ctx = useContext(GameContext)
  if (!ctx) throw new Error('useGame must be used inside GameProvider')
  return ctx
}
