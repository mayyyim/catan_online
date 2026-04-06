import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGame } from '../context/GameContext'
import { useRoom } from '../context/RoomContext'
import { gameSocket } from '../ws/gameSocket'
import { HexGrid } from '../components/HexGrid'
import { ResourceHand } from '../components/ResourceHand'
import { DiceDisplay } from '../components/DiceDisplay'
import { PlayerAvatar } from '../components/PlayerAvatar'
import { generateBoard } from '../engine/boardUtils'
import type { GameState, ResourceType } from '../types'
import styles from './Game.module.css'

type BuildMode = 'none' | 'road' | 'settlement' | 'city'

const EMPTY_RESOURCES: Record<ResourceType, number> = {
  wood: 0,
  brick: 0,
  wheat: 0,
  sheep: 0,
  ore: 0,
}

export default function Game() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()
  const { game, myPlayerId, setGame, setMyPlayerId, selectedVertexId, selectedEdgeId, selectVertex, selectEdge } =
    useGame()
  const { setMyPlayerId: setRoomPlayerId } = useRoom()

  const [buildMode, setBuildMode] = useState<BuildMode>('none')
  const [rolling, setRolling] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected')
  const [log, setLog] = useState<string[]>([])

  // Restore identity
  useEffect(() => {
    const storedId = sessionStorage.getItem('player_id')
    if (storedId && !myPlayerId) {
      setMyPlayerId(storedId)
      setRoomPlayerId(storedId)
    }
  }, [myPlayerId, setMyPlayerId, setRoomPlayerId])

  // Connect WebSocket
  useEffect(() => {
    const pid = myPlayerId ?? sessionStorage.getItem('player_id')
    if (!roomId || !pid) return

    gameSocket.connect(roomId, pid)
    const unsubStatus = gameSocket.onStatus(setWsStatus)
    const unsubMsg = gameSocket.onMessage(msg => {
      if (msg.type === 'game_state') {
        setGame(msg.state)
      }
      if (msg.type === 'error') {
        appendLog(`Error: ${msg.message}`)
      }
    })

    return () => {
      unsubStatus()
      unsubMsg()
      gameSocket.disconnect()
    }
  }, [roomId, myPlayerId, setGame])

  // Demo board when there is no server state yet
  const demoTiles = useMemo(() => generateBoard('demo'), [])

  const tiles = game?.tiles ?? demoTiles
  const buildings = game?.buildings ?? []
  const roads = game?.roads ?? []
  const players = game?.players ?? []

  const me = players.find(p => p.id === myPlayerId)
  const myResources = me?.resources ?? EMPTY_RESOURCES
  const isMyTurn = game?.currentPlayerId === myPlayerId
  const turnPhase = game?.turnPhase ?? 'pre_roll'
  const currentPlayer = players.find(p => p.id === game?.currentPlayerId)

  const appendLog = useCallback((msg: string) => {
    setLog(prev => [...prev.slice(-49), msg])
  }, [])

  // Build mode: which vertices/edges to highlight
  // Server drives valid placements; client just needs the mode active to route clicks.
  const buildableVertices = useMemo(() => {
    if (buildMode !== 'settlement' && buildMode !== 'city') return []
    return [] // server sends the actual valid vertex list via game_state
  }, [buildMode])

  const buildableEdges = useMemo(() => {
    if (buildMode !== 'road') return []
    return [] // server drives valid placements
  }, [buildMode])

  // Action handlers
  const handleRollDice = useCallback(() => {
    if (!isMyTurn || turnPhase !== 'pre_roll') return
    setRolling(true)
    gameSocket.send({ type: 'roll_dice' })
    setTimeout(() => setRolling(false), 600)
  }, [isMyTurn, turnPhase])

  const handleEndTurn = useCallback(() => {
    if (!isMyTurn) return
    gameSocket.send({ type: 'end_turn' })
    setBuildMode('none')
    selectVertex(null)
    selectEdge(null)
  }, [isMyTurn, selectVertex, selectEdge])

  const handleVertexClick = useCallback(
    (vid: string) => {
      if (!isMyTurn) return
      selectVertex(vid)
      if (buildMode === 'settlement') {
        gameSocket.send({ type: 'build_settlement', vertexId: vid })
        setBuildMode('none')
      } else if (buildMode === 'city') {
        gameSocket.send({ type: 'build_city', vertexId: vid })
        setBuildMode('none')
      }
    },
    [isMyTurn, buildMode, selectVertex],
  )

  const handleEdgeClick = useCallback(
    (eid: string) => {
      if (!isMyTurn) return
      selectEdge(eid)
      if (buildMode === 'road') {
        gameSocket.send({ type: 'build_road', edgeId: eid })
        setBuildMode('none')
      }
    },
    [isMyTurn, buildMode, selectEdge],
  )

  const toggleBuildMode = useCallback(
    (mode: BuildMode) => {
      setBuildMode(prev => (prev === mode ? 'none' : mode))
      selectVertex(null)
      selectEdge(null)
    },
    [selectVertex, selectEdge],
  )

  if (!game && !demoTiles.length) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <p>Connecting to game...</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      {/* Top score bar */}
      <header className={styles.topBar}>
        <div className={styles.topLeft}>
          <span className={styles.roomLabel}>Room {roomId}</span>
          <span
            className={`${styles.wsIndicator} ${styles[wsStatus]}`}
            title={wsStatus}
          />
        </div>

        <div className={styles.scoreboard}>
          {players.map(p => (
            <div
              key={p.id}
              className={`${styles.scoreCard} ${
                p.id === game?.currentPlayerId ? styles.activeScore : ''
              } ${p.id === myPlayerId ? styles.myScore : ''}`}
              style={{ '--player-color': p.color } as React.CSSProperties}
            >
              <PlayerAvatar player={p} isMe={p.id === myPlayerId} compact />
              <span className={styles.scoreVP}>{p.victoryPoints} VP</span>
            </div>
          ))}
        </div>

        <div className={styles.topRight}>
          {game?.phase && (
            <span className={styles.phaseTag}>{game.phase.replace(/_/g, ' ')}</span>
          )}
        </div>
      </header>

      <div className={styles.body}>
        {/* Main map area */}
        <main className={styles.mapArea}>
          <HexGrid
            tiles={tiles}
            buildings={buildings}
            roads={roads}
            players={players}
            selectedVertexId={selectedVertexId}
            selectedEdgeId={selectedEdgeId}
            buildableVertices={buildableVertices}
            buildableEdges={buildableEdges}
            onVertexClick={handleVertexClick}
            onEdgeClick={handleEdgeClick}
            width={700}
            height={680}
          />
        </main>

        {/* Right panel */}
        <aside className={styles.sidePanel}>
          {/* Turn info */}
          <div className={styles.turnSection}>
            <div className={styles.turnHeader}>
              <span className={styles.turnLabel}>
                {isMyTurn ? 'Your Turn' : `${currentPlayer?.name ?? '...'}'s Turn`}
              </span>
              <DiceDisplay
                dice={game?.lastDiceRoll}
                rolling={rolling}
              />
            </div>
          </div>

          {/* Resources */}
          <div className={styles.panel}>
            <ResourceHand resources={myResources} />
          </div>

          {/* Build actions */}
          {isMyTurn && (
            <div className={styles.panel}>
              <p className={styles.panelTitle}>Build</p>
              <div className={styles.buildGrid}>
                <button
                  className={`${styles.buildBtn} ${buildMode === 'road' ? styles.active : ''}`}
                  onClick={() => toggleBuildMode('road')}
                  type="button"
                  title="Road (1 wood + 1 brick)"
                >
                  <span className={styles.buildIcon}>🛤️</span>
                  <span>Road</span>
                  <span className={styles.cost}>🌲🧱</span>
                </button>
                <button
                  className={`${styles.buildBtn} ${buildMode === 'settlement' ? styles.active : ''}`}
                  onClick={() => toggleBuildMode('settlement')}
                  type="button"
                  title="Settlement (1 wood + 1 brick + 1 wheat + 1 sheep)"
                >
                  <span className={styles.buildIcon}>🏠</span>
                  <span>Settlement</span>
                  <span className={styles.cost}>🌲🧱🌾🐑</span>
                </button>
                <button
                  className={`${styles.buildBtn} ${buildMode === 'city' ? styles.active : ''}`}
                  onClick={() => toggleBuildMode('city')}
                  type="button"
                  title="City (2 wheat + 3 ore)"
                >
                  <span className={styles.buildIcon}>🏙️</span>
                  <span>City</span>
                  <span className={styles.cost}>🌾🌾⛏️⛏️⛏️</span>
                </button>
              </div>
            </div>
          )}

          {/* Special cards */}
          {game?.longestRoadPlayerId && (
            <div className={styles.specialCard}>
              🛤️ Longest Road —{' '}
              {players.find(p => p.id === game.longestRoadPlayerId)?.name}
            </div>
          )}
          {game?.largestArmyPlayerId && (
            <div className={styles.specialCard}>
              ⚔️ Largest Army —{' '}
              {players.find(p => p.id === game.largestArmyPlayerId)?.name}
            </div>
          )}

          {/* Event log */}
          <div className={styles.logPanel}>
            <p className={styles.panelTitle}>Log</p>
            <div className={styles.logScroll}>
              {log.length === 0 && (
                <span className={styles.logEmpty}>No events yet.</span>
              )}
              {[...log].reverse().map((entry, i) => (
                <div key={i} className={styles.logEntry}>
                  {entry}
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>

      {/* Bottom action bar */}
      <footer className={styles.actionBar}>
        <div className={styles.actionLeft}>
          {buildMode !== 'none' && (
            <span className={styles.buildHint}>
              Click on the map to place your {buildMode}. Press again to cancel.
            </span>
          )}
        </div>
        <div className={styles.actionRight}>
          <button
            className={styles.rollBtn}
            onClick={handleRollDice}
            disabled={!isMyTurn || turnPhase !== 'pre_roll' || rolling}
            type="button"
          >
            {rolling ? 'Rolling...' : 'Roll Dice'}
          </button>
          <button
            className={styles.endTurnBtn}
            onClick={handleEndTurn}
            disabled={!isMyTurn || turnPhase === 'pre_roll'}
            type="button"
          >
            End Turn
          </button>
        </div>
      </footer>

      {/* Winner overlay */}
      {game?.winner && (
        <div className={styles.winnerOverlay}>
          <div className={styles.winnerCard}>
            <span className={styles.winnerEmoji}>🏆</span>
            <h2 className={styles.winnerTitle}>
              {players.find(p => p.id === game.winner)?.name ?? 'Someone'} wins!
            </h2>
            <button
              className={styles.homeBtn}
              onClick={() => navigate('/')}
              type="button"
            >
              Back to Home
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
