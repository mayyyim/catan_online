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
import type { ResourceType, Port } from '../types'
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
  turn_step: 'pre_roll' | 'post_roll' | 'robber_discard' | 'robber_place' | 'robber_steal'
  current_player_id: string | null
  players: Array<{
    player_id: string
    name: string
    color: string
    resources?: Record<string, number>
    resource_count?: number
    victory_points?: number
  }>
  players_to_discard?: string[]
  robber_steal_targets?: string[]
  map?: {
    tiles?: Array<{ q: number; r: number; tile_type: string; token?: number | null }>
    ports?: Array<{ q: number; r: number; side: number; resource: string | null; ratio: number }>
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
  // Backend and frontend use the same corner numbering (0-5, clockwise from right for flat-top).
  const corner = Number(cornerRaw)
  return `${q},${r},${s}:v${corner}`
}

function edgeKeyToId(ekey: string): string {
  const [qRaw, rRaw, sideRaw] = ekey.split(',')
  const q = Number(qRaw)
  const r = Number(rRaw)
  const s = cubeS(q, r)
  // Backend and frontend use the same side numbering.
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
  // Backend and frontend share the same corner numbering — no offset needed.
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
  // Backend and frontend share the same side numbering — no offset needed.
  const direction = Number(e)
  if (!Number.isFinite(q) || !Number.isFinite(r) || !Number.isFinite(direction)) return null
  return { q, r, direction }
}

// Adjacent corners for each frontend corner index (flat-top, 0=right going clockwise in SVG).
// Corner i shares edges with corners (i-1+6)%6 and (i+1)%6 on the same tile,
// but the physically adjacent vertices on the board can be on neighboring tiles.
// For the distance rule we just need the 3 vertices reachable in one road step.
// We compute them by looking at all land vertices and checking if they share an edge
// (i.e. appear as consecutive corners of the same tile).
function buildAdjacencyMap(
  tiles: Array<{ q: number; r: number; s: number; terrain: string }>,
): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>()
  const ensure = (id: string) => {
    if (!adj.has(id)) adj.set(id, new Set())
    return adj.get(id)!
  }
  for (const t of tiles) {
    if (t.terrain === 'ocean') continue
    for (let c = 0; c < 6; c++) {
      const a = `${t.q},${t.r},${t.s}:v${c}`
      const b = `${t.q},${t.r},${t.s}:v${(c + 1) % 6}`
      ensure(a).add(b)
      ensure(b).add(a)
    }
  }
  return adj
}

function validSettlementVertices(
  tiles: Array<{ q: number; r: number; s: number; terrain: string }>,
  occupiedVertexIds: Set<string>,
): string[] {
  const adj = buildAdjacencyMap(tiles)
  // A vertex is blocked if it or any neighbour is occupied.
  const blocked = new Set<string>()
  for (const vid of occupiedVertexIds) {
    blocked.add(vid)
    for (const nb of (adj.get(vid) ?? [])) {
      blocked.add(nb)
    }
  }
  return [...adj.keys()].filter(vid => !blocked.has(vid))
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
  const [playersToDiscard, setPlayersToDiscard] = useState<string[]>([])
  const [robberStealTargets, setRobberStealTargets] = useState<string[]>([])
  const [discardSelection, setDiscardSelection] = useState<Record<string, number>>({})
  const [tradeOpen, setTradeOpen] = useState(false)
  const [tradeOffer, setTradeOffer] = useState<Record<string, number>>({})
  const [tradeWant, setTradeWant] = useState<Record<string, number>>({})

  // Restore identity
  useEffect(() => {
    const storedId = sessionStorage.getItem('player_id')
    if (storedId && !myPlayerId) {
      setMyPlayerId(storedId)
      setRoomPlayerId(storedId)
    }
  }, [myPlayerId, setMyPlayerId, setRoomPlayerId])

  const appendLog = useCallback((msg: string) => {
    setLog(prev => [...prev.slice(-49), msg])
  }, [])

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

        const ports: Port[] = (raw.map?.ports ?? [])
          .filter(p => p.side != null)
          .map(p => ({
            q: p.q,
            r: p.r,
            side: p.side,
            resource: p.resource as Port['resource'],
            ratio: p.ratio,
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
          ports,
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
        setPlayersToDiscard(raw.players_to_discard ?? [])
        setRobberStealTargets(raw.robber_steal_targets ?? [])
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
  }, [roomId, myPlayerId, setGame, appendLog])

  // Demo board when there is no server state yet
  const demoTiles = useMemo(() => generateBoard('demo'), [])

  const tiles = (game?.tiles?.length ? game.tiles : demoTiles) ?? demoTiles
  const ports = game?.ports ?? []
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

  // appendLog moved before WebSocket useEffect — see above

  // Build mode: which vertices/edges to highlight
  const buildableVertices = useMemo(() => {
    if (isSetupPhase && isMyTurn && requiredBuildMode === 'settlement') {
      // Filter out vertices that violate the distance rule.
      const occupiedIds = new Set(buildings.map(b => b.vertexId))
      return validSettlementVertices(tiles as any, occupiedIds)
    }
    if (buildMode !== 'settlement' && buildMode !== 'city') return []
    return [] // future: server-driven valid vertex list
  }, [buildMode, isSetupPhase, isMyTurn, requiredBuildMode, tiles, buildings])

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

  // Robber: discard
  const mustDiscard = turnPhase === 'robber_discard' && playersToDiscard.includes(myPlayerId ?? '')
  const myHandTotal = Object.values(myResources).reduce((a, b) => a + b, 0)
  const discardRequired = Math.floor(myHandTotal / 2)
  const discardTotal = Object.values(discardSelection).reduce((a, b) => a + b, 0)

  const handleDiscardChange = useCallback((res: string, delta: number) => {
    setDiscardSelection(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, Math.min(cur + delta, myResources[res as ResourceType] ?? 0))
      return { ...prev, [res]: next }
    })
  }, [myResources])

  const handleDiscardSubmit = useCallback(() => {
    const payload: Record<string, number> = {}
    for (const [k, v] of Object.entries(discardSelection)) {
      if (v > 0) payload[k] = v
    }
    gameSocket.send({ type: 'discard', resources: payload } as any)
    setDiscardSelection({})
  }, [discardSelection])

  // Robber: place on tile click
  const isRobberPlace = turnPhase === 'robber_place' && isMyTurn
  const handleTileClick = useCallback((tile: { q: number; r: number }) => {
    if (!isRobberPlace) return
    gameSocket.send({ type: 'place_robber', q: tile.q, r: tile.r } as any)
  }, [isRobberPlace])

  // Robber: steal
  const isRobberSteal = turnPhase === 'robber_steal' && isMyTurn
  const handleSteal = useCallback((targetId: string) => {
    gameSocket.send({ type: 'steal', target_id: targetId } as any)
  }, [])

  // Trade handlers
  const canTrade = isMyTurn && turnPhase === 'post_roll' && !isSetupPhase

  const handleTradeOfferChange = useCallback((res: string, delta: number) => {
    setTradeOffer(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, cur + delta)
      return { ...prev, [res]: next }
    })
  }, [])

  const handleTradeWantChange = useCallback((res: string, delta: number) => {
    setTradeWant(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, cur + delta)
      return { ...prev, [res]: next }
    })
  }, [])

  const handleTradeSubmit = useCallback(() => {
    const offer: Record<string, number> = {}
    const want: Record<string, number> = {}
    for (const [k, v] of Object.entries(tradeOffer)) {
      if (v > 0) offer[k] = v
    }
    for (const [k, v] of Object.entries(tradeWant)) {
      if (v > 0) want[k] = v
    }
    if (Object.keys(offer).length && Object.keys(want).length) {
      gameSocket.send({ type: 'trade', offer, want } as any)
      setTradeOffer({})
      setTradeWant({})
    }
  }, [tradeOffer, tradeWant])

  const handleTradeReset = useCallback(() => {
    setTradeOffer({})
    setTradeWant({})
  }, [])

  // Compute trade ratios from ports
  const tradeRatios = useMemo(() => {
    const ratios: Record<string, number> = { wood: 4, brick: 4, wheat: 4, sheep: 4, ore: 4 }
    let genericRatio = 4
    // ports data is available; backend already validates but we compute for display
    for (const port of ports) {
      if (!port.resource) {
        genericRatio = Math.min(genericRatio, port.ratio)
      } else {
        ratios[port.resource] = Math.min(ratios[port.resource] ?? 4, port.ratio)
      }
    }
    // Apply generic to all that are still > generic
    for (const r of Object.keys(ratios)) {
      ratios[r] = Math.min(ratios[r], genericRatio)
    }
    return ratios
  }, [ports])

  const tradeOfferTotal = Object.values(tradeOffer).reduce((a, b) => a + b, 0)
  const tradeWantTotal = Object.values(tradeWant).reduce((a, b) => a + b, 0)

  // Calculate how many "want" credits the offer gives
  const tradeCredits = useMemo(() => {
    let credits = 0
    for (const [res, amt] of Object.entries(tradeOffer)) {
      const ratio = tradeRatios[res] ?? 4
      credits += Math.floor(amt / ratio)
    }
    return credits
  }, [tradeOffer, tradeRatios])

  const tradeValid = tradeCredits > 0 && tradeWantTotal === tradeCredits &&
    Object.entries(tradeOffer).every(([res, amt]) => {
      const ratio = tradeRatios[res] ?? 4
      return amt % ratio === 0 && (myResources[res as ResourceType] ?? 0) >= amt
    })

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
            ports={ports}
            buildings={buildings}
            roads={roads}
            players={players}
            selectedVertexId={selectedVertexId}
            selectedEdgeId={selectedEdgeId}
            buildableVertices={buildableVertices}
            buildableEdges={buildableEdges}
            onVertexClick={handleVertexClick}
            onEdgeClick={handleEdgeClick}
            onTileClick={isRobberPlace ? handleTileClick : undefined}
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
                  : mustDiscard
                    ? 'You must discard cards!'
                    : isRobberPlace
                      ? 'Move the robber!'
                      : isRobberSteal
                        ? 'Choose who to steal from!'
                        : turnPhase === 'robber_discard'
                          ? 'Waiting for others to discard...'
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

          {/* Robber: discard panel */}
          {mustDiscard && (
            <div className={`${styles.panel} ${styles.robberPanel}`}>
              <p className={styles.panelTitle}>Discard {discardRequired} cards (rolled 7)</p>
              <div className={styles.discardGrid}>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                  const have = myResources[res] ?? 0
                  const sel = discardSelection[res] ?? 0
                  if (have === 0) return null
                  return (
                    <div key={res} className={styles.discardRow}>
                      <span className={styles.discardLabel}>{res}</span>
                      <button type="button" className={styles.discardBtn} onClick={() => handleDiscardChange(res, -1)} disabled={sel <= 0}>-</button>
                      <span className={styles.discardCount}>{sel}</span>
                      <button type="button" className={styles.discardBtn} onClick={() => handleDiscardChange(res, 1)} disabled={sel >= have}>+</button>
                      <span className={styles.discardHave}>/{have}</span>
                    </div>
                  )
                })}
              </div>
              <button
                type="button"
                className={styles.discardSubmitBtn}
                onClick={handleDiscardSubmit}
                disabled={discardTotal !== discardRequired}
              >
                Discard {discardTotal}/{discardRequired}
              </button>
            </div>
          )}

          {/* Robber: place indicator */}
          {isRobberPlace && (
            <div className={`${styles.panel} ${styles.robberPanel}`}>
              <p className={styles.panelTitle}>Move the Robber</p>
              <p className={styles.robberHint}>Click a land tile on the map to move the robber.</p>
            </div>
          )}

          {/* Robber: steal target */}
          {isRobberSteal && robberStealTargets.length > 0 && (
            <div className={`${styles.panel} ${styles.robberPanel}`}>
              <p className={styles.panelTitle}>Steal a resource</p>
              <div className={styles.stealGrid}>
                {robberStealTargets.map(tid => {
                  const target = players.find(p => p.id === tid)
                  return (
                    <button
                      key={tid}
                      type="button"
                      className={styles.stealBtn}
                      onClick={() => handleSteal(tid)}
                      style={{ borderColor: target?.color }}
                    >
                      Steal from {target?.name ?? tid}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

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

          {/* Trade with bank */}
          {canTrade && (
            <div className={styles.panel}>
              <button
                type="button"
                className={styles.tradePanelToggle}
                onClick={() => setTradeOpen(prev => !prev)}
              >
                <span>🏦 Bank Trade</span>
                <span className={styles.toggleArrow}>{tradeOpen ? '▲' : '▼'}</span>
              </button>
              {tradeOpen && (
                <div className={styles.tradeBody}>
                  {/* Offer (give) */}
                  <div className={styles.tradeSide}>
                    <span className={styles.tradeLabel}>You give</span>
                    {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                      const have = myResources[res] ?? 0
                      const offering = tradeOffer[res] ?? 0
                      const ratio = tradeRatios[res] ?? 4
                      return (
                        <div key={res} className={styles.tradeRow}>
                          <span className={styles.tradeRes}>{res} <span className={styles.tradeRatio}>{ratio}:1</span></span>
                          <button type="button" className={styles.tradeBtn} onClick={() => handleTradeOfferChange(res, -ratio)} disabled={offering < ratio}>-</button>
                          <span className={styles.tradeCount}>{offering}</span>
                          <button type="button" className={styles.tradeBtn} onClick={() => handleTradeOfferChange(res, ratio)} disabled={have - offering < ratio}>+</button>
                        </div>
                      )
                    })}
                  </div>
                  {/* Want (receive) */}
                  <div className={styles.tradeSide}>
                    <span className={styles.tradeLabel}>You get <span className={styles.tradeCredits}>({tradeCredits} available)</span></span>
                    {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                      const wanting = tradeWant[res] ?? 0
                      return (
                        <div key={res} className={styles.tradeRow}>
                          <span className={styles.tradeRes}>{res}</span>
                          <button type="button" className={styles.tradeBtn} onClick={() => handleTradeWantChange(res, -1)} disabled={wanting <= 0}>-</button>
                          <span className={styles.tradeCount}>{wanting}</span>
                          <button type="button" className={styles.tradeBtn} onClick={() => handleTradeWantChange(res, 1)} disabled={tradeWantTotal >= tradeCredits}>+</button>
                        </div>
                      )
                    })}
                  </div>
                  {/* Actions */}
                  <div className={styles.tradeActions}>
                    <button type="button" className={styles.tradeSubmitBtn} onClick={handleTradeSubmit} disabled={!tradeValid}>
                      Trade {tradeOfferTotal} → {tradeWantTotal}
                    </button>
                    <button type="button" className={styles.tradeResetBtn} onClick={handleTradeReset}>Clear</button>
                  </div>
                </div>
              )}
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
            disabled={isSetupPhase || !isMyTurn || turnPhase !== 'post_roll'}
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
