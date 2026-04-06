import { useEffect, useState, useCallback, useMemo, type CSSProperties } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGame } from '../context/GameContext'
import { useRoom } from '../context/RoomContext'
import { gameSocket } from '../ws/gameSocket'
import { HexGrid } from '../components/HexGrid'
import { ResourceHand } from '../components/ResourceHand'
import { DiceDisplay } from '../components/DiceDisplay'
import { PlayerAvatar } from '../components/PlayerAvatar'
import { generateBoard } from '../engine/boardUtils'
import type { ResourceType } from '../types'
import styles from './Game.module.css'

type BuildMode = 'none' | 'road' | 'settlement' | 'city'

const EMPTY_RESOURCES: Record<ResourceType, number> = {
  wood: 0,
  brick: 0,
  wheat: 0,
  sheep: 0,
  ore: 0,
}

type BackendGameState = {
  room_id: string
  phase: string
  turn_step: 'pre_roll' | 'post_roll'
  current_player_id: string | null
  players: Array<{
    player_id: string
    name: string
    color: string
    resources?: Record<string, number>
    victory_points?: number
  }>
  map?: {
    tiles?: Array<{ q: number; r: number; tile_type: string; token?: number | null }>
  }
  robber?: { q: number; r: number }
  last_dice?: [number, number] | number[] | null
  winner_id?: string | null
  vertices?: Record<string, { piece_type: string; player_id: string }>
  edges?: Record<string, { piece_type: string; player_id: string }>
  setup_order?: number[]
  setup_step?: number
}

function cubeS(q: number, r: number): number {
  return -q - r
}

function vertexKeyToId(vkey: string): string {
  const [qRaw, rRaw, cornerRaw] = vkey.split(',')
  const q = Number(qRaw)
  const r = Number(rRaw)
  const s = cubeS(q, r)
  const corner = Number(cornerRaw)
  return `${q},${r},${s}:v${corner}`
}

function edgeKeyToId(ekey: string): string {
  const [qRaw, rRaw, sideRaw] = ekey.split(',')
  const q = Number(qRaw)
  const r = Number(rRaw)
  const s = cubeS(q, r)
  const side = Number(sideRaw)
  return `${q},${r},${s}:e${side}`
}

function parseVertexId(id: string): { q: number; r: number; direction: number } | null {
  // format: "q,r,s:v{corner}"
  const [coord, v] = id.split(':v')
  if (!coord || v == null) return null
  const [qRaw, rRaw] = coord.split(',')
  const q = Number(qRaw)
  const r = Number(rRaw)
  const direction = Number(v)
  if (!Number.isFinite(q) || !Number.isFinite(r) || !Number.isFinite(direction)) return null
  return { q, r, direction }
}

function parseEdgeId(id: string): { q: number; r: number; direction: number } | null {
  // format: "q,r,s:e{side}"
  const [coord, e] = id.split(':e')
  if (!coord || e == null) return null
  const [qRaw, rRaw] = coord.split(',')
  const q = Number(qRaw)
  const r = Number(rRaw)
  const direction = Number(e)
  if (!Number.isFinite(q) || !Number.isFinite(r) || !Number.isFinite(direction)) return null
  return { q, r, direction }
}

function allVertexIdsFromTiles(tiles: Array<{ q: number; r: number; s: number; terrain: string }>): string[] {
  const set = new Set<string>()
  for (const t of tiles) {
    if (t.terrain === 'ocean') continue
    for (let corner = 0; corner < 6; corner++) {
      set.add(`${t.q},${t.r},${t.s}:v${corner}`)
    }
  }
  return [...set]
}

function allEdgeIdsFromTiles(tiles: Array<{ q: number; r: number; s: number; terrain: string }>): string[] {
  const set = new Set<string>()
  for (const t of tiles) {
    if (t.terrain === 'ocean') continue
    for (let side = 0; side < 6; side++) {
      set.add(`${t.q},${t.r},${t.s}:e${side}`)
    }
  }
  return [...set]
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
      if ((msg as any).type === 'game_state') {
        const raw = (msg as any).data as BackendGameState | undefined
        if (!raw) return

        const players = (raw.players ?? []).map(p => ({
          id: p.player_id,
          name: p.name,
          color: p.color as any,
          isHost: false,
          connected: true,
          resources: {
            wood: Number(p.resources?.wood ?? 0),
            brick: Number(p.resources?.brick ?? 0),
            wheat: Number(p.resources?.wheat ?? 0),
            sheep: Number(p.resources?.sheep ?? 0),
            ore: Number(p.resources?.ore ?? 0),
          },
          victoryPoints: Number(p.victory_points ?? 0),
          settlements: 0,
          cities: 0,
          roads: 0,
        }))

        const robberPos = raw.robber ?? { q: 0, r: 0 }
        const tiles =
          raw.map?.tiles?.map(t => ({
            q: t.q,
            r: t.r,
            s: cubeS(t.q, t.r),
            terrain: t.tile_type as any,
            token: t.token == null ? undefined : Number(t.token),
            robber: robberPos.q === t.q && robberPos.r === t.r,
          })) ?? []

        const buildings = Object.entries(raw.vertices ?? {})
          .filter(([, v]) => v.piece_type === 'settlement' || v.piece_type === 'city')
          .map(([k, v]) => ({
            vertexId: vertexKeyToId(k),
            playerId: v.player_id,
            type: v.piece_type,
          }))

        const roads = Object.entries(raw.edges ?? {})
          .filter(([, v]) => v.piece_type === 'road')
          .map(([k, v]) => ({
            edgeId: edgeKeyToId(k),
            playerId: v.player_id,
          }))

        // Prefer server tiles; fall back to demo board if server didn't include map yet.
        const mapped = {
          roomId: raw.room_id ?? roomId,
          phase:
            raw.phase === 'setup_forward'
              ? 'setup_round1'
              : raw.phase === 'setup_backward'
                ? 'setup_round2'
                : raw.phase,
          turnPhase: raw.turn_step,
          currentPlayerId: raw.current_player_id ?? '',
          players,
          tiles,
          buildings,
          roads,
          lastDiceRoll: Array.isArray(raw.last_dice) && raw.last_dice.length === 2
            ? ([Number(raw.last_dice[0]), Number(raw.last_dice[1])] as [number, number])
            : undefined,
          winner: raw.winner_id ?? undefined,
          // carry-through extra fields for UI ordering (optional)
          setupOrder: raw.setup_order,
          setupStep: raw.setup_step,
        } as any

        setGame(mapped)
      }

      if ((msg as any).type === 'error') {
        appendLog(`Error: ${(msg as any).data?.message ?? (msg as any).message ?? 'Unknown error'}`)
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

  const tiles = (game?.tiles?.length ? game.tiles : demoTiles) ?? demoTiles
  const buildings = game?.buildings ?? []
  const roads = game?.roads ?? []
  const players = game?.players ?? []

  const me = players.find(p => p.id === myPlayerId)
  const myResources = me?.resources ?? EMPTY_RESOURCES
  const isMyTurn = game?.currentPlayerId === myPlayerId
  const turnPhase = game?.turnPhase ?? 'pre_roll'
  const currentPlayer = players.find(p => p.id === game?.currentPlayerId)
  const isSetupPhase = game?.phase === 'setup_round1' || game?.phase === 'setup_round2'
  const setupStep = (game as any)?.setupStep as number | undefined
  const setupNeedsSettlement = isSetupPhase && (setupStep == null ? true : setupStep % 2 === 0)
  const requiredBuildMode: BuildMode = !isSetupPhase
    ? buildMode
    : setupNeedsSettlement
      ? 'settlement'
      : 'road'

  const setupOrder = (game as any)?.setupOrder as number[] | undefined
  const orderedPlayers = useMemo(() => {
    if (!players.length) return players
    if (!setupOrder || setupOrder.length === 0) return players
    // Opening order is the first N unique indices in setupOrder (snake draft).
    const seen = new Set<number>()
    const opening: number[] = []
    for (const idx of setupOrder) {
      if (!seen.has(idx)) {
        opening.push(idx)
        seen.add(idx)
      }
      if (opening.length >= players.length) break
    }
    const byIdx = opening.map(i => players[i]).filter(Boolean)
    return byIdx.length === players.length ? byIdx : players
  }, [players, setupOrder])

  const appendLog = useCallback((msg: string) => {
    setLog(prev => [...prev.slice(-49), msg])
  }, [])

  // Build mode: which vertices/edges to highlight
  // Server drives valid placements; client just needs the mode active to route clicks.
  const buildableVertices = useMemo(() => {
    // In setup, allow clicking any vertex; server will validate placement rules.
    if (isSetupPhase && isMyTurn && requiredBuildMode === 'settlement') {
      return allVertexIdsFromTiles(tiles as any)
    }
    if (buildMode !== 'settlement' && buildMode !== 'city') return []
    return [] // future: server-driven valid vertex list
  }, [buildMode, isSetupPhase, isMyTurn, requiredBuildMode, tiles])

  const buildableEdges = useMemo(() => {
    // In setup, allow clicking any edge; server will validate placement rules.
    if (isSetupPhase && isMyTurn && requiredBuildMode === 'road') {
      return allEdgeIdsFromTiles(tiles as any)
    }
    if (buildMode !== 'road') return []
    return [] // future: server-driven valid edge list
  }, [buildMode, isSetupPhase, isMyTurn, requiredBuildMode, tiles])

  // Action handlers
  const handleRollDice = useCallback(() => {
    if (isSetupPhase) return
    if (!isMyTurn || turnPhase !== 'pre_roll') return
    setRolling(true)
    gameSocket.send({ type: 'roll_dice' })
    setTimeout(() => setRolling(false), 600)
  }, [isMyTurn, turnPhase, isSetupPhase])

  const handleEndTurn = useCallback(() => {
    if (isSetupPhase) return
    if (!isMyTurn) return
    gameSocket.send({ type: 'end_turn' })
    setBuildMode('none')
    selectVertex(null)
    selectEdge(null)
  }, [isMyTurn, selectVertex, selectEdge, isSetupPhase])

  const handleVertexClick = useCallback(
    (vid: string) => {
      if (!isMyTurn) return
      selectVertex(vid)
      const pos = parseVertexId(vid)
      if (!pos) return

      const mode = requiredBuildMode
      if (mode === 'settlement') {
        gameSocket.send({ type: 'build', piece: 'settlement', position: pos } as any)
        if (!isSetupPhase) setBuildMode('none')
      } else if (mode === 'city') {
        gameSocket.send({ type: 'build', piece: 'city', position: pos } as any)
        setBuildMode('none')
      }
    },
    [isMyTurn, requiredBuildMode, selectVertex, isSetupPhase],
  )

  const handleEdgeClick = useCallback(
    (eid: string) => {
      if (!isMyTurn) return
      selectEdge(eid)
      const pos = parseEdgeId(eid)
      if (!pos) return

      const mode = requiredBuildMode
      if (mode === 'road') {
        gameSocket.send({ type: 'build', piece: 'road', position: pos } as any)
        if (!isSetupPhase) setBuildMode('none')
      }
    },
    [isMyTurn, requiredBuildMode, selectEdge, isSetupPhase],
  )

  const toggleBuildMode = useCallback(
    (mode: BuildMode) => {
      if (isSetupPhase) return
      setBuildMode(prev => (prev === mode ? 'none' : mode))
      selectVertex(null)
      selectEdge(null)
    },
    [selectVertex, selectEdge, isSetupPhase],
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
          {orderedPlayers.map(p => (
            <div
              key={p.id}
              className={`${styles.scoreCard} ${
                p.id === game?.currentPlayerId ? styles.activeScore : ''
              } ${p.id === myPlayerId ? styles.myScore : ''}`}
              style={{ '--player-color': p.color } as CSSProperties}
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
                {isSetupPhase
                  ? isMyTurn
                    ? `Setup: Your turn — place a ${requiredBuildMode}`
                    : `Setup: ${currentPlayer?.name ?? '...'} — place a ${requiredBuildMode}`
                  : isMyTurn
                    ? 'Your Turn'
                    : `${currentPlayer?.name ?? '...'}'s Turn`}
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
                  disabled={isSetupPhase}
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
                  disabled={isSetupPhase}
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
                  disabled={isSetupPhase}
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
          {isSetupPhase ? (
            <span className={styles.buildHint}>
              Setup phase: click the map to place your {requiredBuildMode}. Order is 1→N then N→1.
            </span>
          ) : buildMode !== 'none' ? (
            <span className={styles.buildHint}>
              Click on the map to place your {buildMode}. Press again to cancel.
            </span>
          ) : null}
        </div>
        <div className={styles.actionRight}>
          <button
            className={styles.rollBtn}
            onClick={handleRollDice}
            disabled={isSetupPhase || !isMyTurn || turnPhase !== 'pre_roll' || rolling}
            type="button"
          >
            {rolling ? 'Rolling...' : 'Roll Dice'}
          </button>
          <button
            className={styles.endTurnBtn}
            onClick={handleEndTurn}
            disabled={isSetupPhase || !isMyTurn || turnPhase === 'pre_roll'}
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
