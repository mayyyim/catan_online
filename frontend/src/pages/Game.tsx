import { useEffect, useState, useCallback, useMemo, useRef, type CSSProperties } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useGame } from '../context/GameContext'
import { useRoom } from '../context/RoomContext'
import { gameSocket } from '../ws/gameSocket'
import { HexGrid } from '../components/HexGrid'
import { DiceDisplay } from '../components/DiceDisplay'
import { PlayerAvatar } from '../components/PlayerAvatar'
import { generateBoard } from '../engine/boardUtils'
import type { ResourceType, Port, DevCard, DevCardType } from '../types'
import { RESOURCE_LABELS } from '../types'
import styles from './Game.module.css'

type BuildMode = 'none' | 'road' | 'settlement' | 'city'

const EMPTY_RESOURCES: Record<ResourceType, number> = {
  wood: 0,
  brick: 0,
  wheat: 0,
  sheep: 0,
  ore: 0,
}

const RES_CARD_COLORS: Record<ResourceType, string> = {
  wood: '#4a8c3f',
  brick: '#c0392b',
  wheat: '#f1c40f',
  sheep: '#7dcea0',
  ore: '#7f8c8d',
}

type BackendGameState = {
  room_id: string
  phase: string
  turn_step: 'pre_roll' | 'post_roll' | 'robber_discard' | 'robber_place' | 'robber_steal' | 'road_building' | 'year_of_plenty' | 'monopoly'
  current_player_id: string | null
  players: Array<{
    player_id: string
    name: string
    color: string
    resources?: Record<string, number>
    resource_count?: number
    victory_points?: number
    settlements_placed?: number
    cities_placed?: number
    roads_placed?: number
    longest_road?: number
    dev_cards?: Array<{ card_type: string; bought_on_turn: number }>
    knights_played?: number
    dev_card_played_this_turn?: boolean
  }>
  dev_card_deck_count?: number
  current_turn_number?: number
  largest_army_holder?: string | null
  largest_army_size?: number
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

  // Dev card state
  const [devCards, setDevCards] = useState<DevCard[]>([])
  const [currentTurn, setCurrentTurn] = useState(0)
  const [devCardPlayed, setDevCardPlayed] = useState(false)
  const [deckCount, setDeckCount] = useState(0)
  const [yopSelection, setYopSelection] = useState<Record<string, number>>({})
  const [monopolyResource, setMonopolyResource] = useState<string>('')
  const [playingCard, setPlayingCard] = useState<DevCardType | null>(null)
  const [rawPlayers, setRawPlayers] = useState<BackendGameState['players']>([])

  // P2P trade state
  const [p2pProposing, setP2pProposing] = useState(false)
  const [p2pOffer, setP2pOffer] = useState<Record<string, number>>({})
  const [p2pWant, setP2pWant] = useState<Record<string, number>>({})
  const [p2pWaiting, setP2pWaiting] = useState(false) // true after sending proposal
  const [p2pSentOffer, setP2pSentOffer] = useState<Record<string, number>>({})
  const [p2pSentWant, setP2pSentWant] = useState<Record<string, number>>({})
  const [tradeProposal, setTradeProposal] = useState<{
    id: string
    proposer_id: string
    proposer_name: string
    offer: Record<string, number>
    want: Record<string, number>
  } | null>(null)

  // Turn notification state
  const prevCurrentPlayerRef = useRef<string | null>(null)
  const [titleFlashing, setTitleFlashing] = useState(false)

  // Request notification permission on first game load
  useEffect(() => {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }
  }, [])

  // Flash browser tab title when it's your turn and tab is hidden
  useEffect(() => {
    if (!titleFlashing) return
    const originalTitle = 'Catan Online'
    let tick = false
    const interval = setInterval(() => {
      document.title = tick ? originalTitle : '\uD83C\uDFB2 Your Turn!'
      tick = !tick
    }, 1000)
    const handleVisibility = () => {
      if (!document.hidden) {
        setTitleFlashing(false)
        document.title = originalTitle
      }
    }
    document.addEventListener('visibilitychange', handleVisibility)
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibility)
      document.title = originalTitle
    }
  }, [titleFlashing])

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
          settlements: Number(p.settlements_placed ?? 0),
          cities: Number(p.cities_placed ?? 0),
          roads: Number(p.roads_placed ?? 0),
          longestRoad: Number(p.longest_road ?? 0),
          resourceCount: Number(p.resource_count ?? 0),
          knightsPlayed: Number(p.knights_played ?? 0),
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
          largestArmyPlayerId: raw.largest_army_holder ?? undefined,
          // carry-through extra fields for UI ordering (optional)
          setupOrder: raw.setup_order,
          setupStep: raw.setup_step,
        } as any

        setGame(mapped)

        // Browser turn notification (P1-03)
        const newCurrentPlayer = raw.current_player_id ?? null
        if (newCurrentPlayer && newCurrentPlayer !== prevCurrentPlayerRef.current && newCurrentPlayer === pid) {
          if (document.hidden && 'Notification' in window && Notification.permission === 'granted') {
            new Notification('Catan Online', { body: "It's your turn!", icon: '/favicon.svg' })
          }
          if (document.hidden) {
            setTitleFlashing(true)
          }
        }
        prevCurrentPlayerRef.current = newCurrentPlayer

        setRawPlayers(raw.players ?? [])
        setPlayersToDiscard(raw.players_to_discard ?? [])

        // Clear P2P trade state on turn change
        if (raw.turn_step === 'pre_roll') {
          setTradeProposal(null)
          setP2pWaiting(false)
          setP2pProposing(false)
          setP2pOffer({})
          setP2pWant({})
        }
        setRobberStealTargets(raw.robber_steal_targets ?? [])

        // Dev card state extraction
        const myPlayerData = (raw.players ?? []).find(p => p.player_id === pid)
        if (myPlayerData?.dev_cards) {
          setDevCards(myPlayerData.dev_cards.map(c => ({
            card_type: c.card_type as DevCardType,
            bought_on_turn: c.bought_on_turn,
          })))
        }
        setCurrentTurn(raw.current_turn_number ?? 0)
        setDevCardPlayed(myPlayerData?.dev_card_played_this_turn ?? false)
        setDeckCount(raw.dev_card_deck_count ?? 0)
      }

      if ((msg as any).type === 'dice_result') {
        const d = (msg as any).data
        appendLog(`\u{1F3B2} ${d.player_name || '?'} rolled ${d.values[0]}+${d.values[1]} = ${d.total}`)
      }

      if ((msg as any).type === 'robber_moved') {
        const rm = (msg as any).data
        appendLog(`\u{1F9B9} ${rm.player_name} moved the robber`)
      }

      if ((msg as any).type === 'resource_stolen') {
        const s = (msg as any).data
        if (s.resource) appendLog(`\u{1F4B0} ${s.player_name} stole ${s.resource} from ${s.target_name}`)
        else appendLog(`\u{1F4B0} ${s.player_name} tried to steal but ${s.target_name} had nothing`)
      }

      if ((msg as any).type === 'turn_start') {
        appendLog(`\u2500\u2500 ${(msg as any).data.player_name}'s turn \u2500\u2500`)
      }

      if ((msg as any).type === 'build_completed') {
        const bd = (msg as any).data
        const PIECE_ICONS: Record<string, string> = { settlement: '🏠', city: '🏙️', road: '🛤️' }
        appendLog(`${PIECE_ICONS[bd.piece] ?? '🔨'} ${bd.player_name} built a ${bd.piece}`)
      }

      if ((msg as any).type === 'trade_completed') {
        const td = (msg as any).data
        const offerStr = Object.entries(td.offer ?? {}).map(([r, n]) => `${n} ${r}`).join(', ')
        const wantStr = Object.entries(td.want ?? {}).map(([r, n]) => `${n} ${r}`).join(', ')
        if (td.with_player_name) {
          appendLog(`🤝 ${td.player_name} traded ${offerStr} with ${td.with_player_name} for ${wantStr}`)
        } else {
          appendLog(`🏦 ${td.player_name} traded ${offerStr} → ${wantStr}`)
        }
        // Clear P2P trade state on completion
        setTradeProposal(null)
        setP2pWaiting(false)
        setP2pProposing(false)
        setP2pOffer({})
        setP2pWant({})
      }

      if ((msg as any).type === 'trade_proposal') {
        const tp = (msg as any).data
        // Only show to non-proposers
        if (tp.proposer_id !== pid) {
          setTradeProposal(tp)
        }
        appendLog(`📢 ${tp.proposer_name} proposed a trade`)
      }

      if ((msg as any).type === 'trade_cancelled') {
        const tc = (msg as any).data
        setTradeProposal(null)
        setP2pWaiting(false)
        setP2pProposing(false)
        appendLog(`❌ ${tc.proposer_name} cancelled their trade proposal`)
      }

      if ((msg as any).type === 'dev_card_played') {
        const CARD_NAMES: Record<string, string> = { knight: '🗡️ Knight', victory_point: '🏆 VP', year_of_plenty: '🌽 Year of Plenty', monopoly: '💰 Monopoly', road_building: '🛤️ Road Building' }
        const dd = (msg as any).data
        appendLog(`${dd.player_name} played ${CARD_NAMES[dd.card_type] ?? dd.card_type}`)
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

  // Helper: get the two vertex endpoints of an edge id
  // Edge "q,r,s:e{i}" connects "q,r,s:v{i}" and "q,r,s:v{(i+1)%6}"
  const edgeEndpoints = useCallback((eid: string): [string, string] | null => {
    const match = eid.match(/^(.+):e(\d)$/)
    if (!match) return null
    const coord = match[1]
    const side = Number(match[2])
    return [`${coord}:v${side}`, `${coord}:v${(side + 1) % 6}`]
  }, [])

  // Build mode: which vertices/edges to highlight
  const buildableVertices = useMemo(() => {
    if (isSetupPhase && isMyTurn && requiredBuildMode === 'settlement') {
      const occupiedIds = new Set(buildings.map(b => b.vertexId))
      return validSettlementVertices(tiles as any, occupiedIds)
    }
    if (!isMyTurn) return []

    // City mode: only vertices where current player has a settlement
    if (buildMode === 'city') {
      return buildings
        .filter(b => b.playerId === myPlayerId && b.type === 'settlement')
        .map(b => b.vertexId)
    }

    // Settlement mode (non-setup): show distance-valid vertices, server validates road adjacency.
    // (Road adjacency check requires canonical vertex matching which the frontend can't do reliably.)
    if (buildMode === 'settlement') {
      const occupiedIds = new Set(buildings.map(b => b.vertexId))
      return validSettlementVertices(tiles as any, occupiedIds)
    }

    return []
  }, [buildMode, isSetupPhase, isMyTurn, requiredBuildMode, tiles, buildings, roads, myPlayerId, edgeEndpoints])

  const buildableEdges = useMemo(() => {
    // In setup, allow clicking any edge; server will validate placement rules.
    if (isSetupPhase && isMyTurn && requiredBuildMode === 'road') {
      return allEdgeIdsFromTiles(tiles as any)
    }
    // Road building dev card: auto-enable road placement
    if (isMyTurn && turnPhase === 'road_building') {
      const allEdges = allEdgeIdsFromTiles(tiles as any)
      const occupiedEdges = new Set(roads.map(r => r.edgeId))
      const myBuildingVertices = new Set(
        buildings.filter(b => b.playerId === myPlayerId).map(b => b.vertexId)
      )
      const myRoadVertices = new Set<string>()
      for (const road of roads) {
        if (road.playerId !== myPlayerId) continue
        const eps = edgeEndpoints(road.edgeId)
        if (eps) {
          myRoadVertices.add(eps[0])
          myRoadVertices.add(eps[1])
        }
      }
      const networkVertices = new Set([...myBuildingVertices, ...myRoadVertices])
      return allEdges.filter(eid => {
        if (occupiedEdges.has(eid)) return false
        const eps = edgeEndpoints(eid)
        if (!eps) return false
        return networkVertices.has(eps[0]) || networkVertices.has(eps[1])
      })
    }
    if (!isMyTurn || buildMode !== 'road') return []

    // Show all unoccupied land edges — server validates connectivity.
    // (Frontend vertex IDs are per-tile, but backend uses canonical IDs,
    // so client-side network matching is unreliable. Let the server decide.)
    const allEdges = allEdgeIdsFromTiles(tiles as any)
    const occupiedEdges = new Set(roads.map(r => r.edgeId))
    return allEdges.filter(eid => !occupiedEdges.has(eid))
  }, [buildMode, isSetupPhase, isMyTurn, requiredBuildMode, turnPhase, tiles, buildings, roads, myPlayerId, edgeEndpoints])

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

  // P2P trade handlers
  const handleP2pOfferChange = useCallback((res: string, delta: number) => {
    setP2pOffer(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, cur + delta)
      return { ...prev, [res]: next }
    })
  }, [])

  const handleP2pWantChange = useCallback((res: string, delta: number) => {
    setP2pWant(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, cur + delta)
      return { ...prev, [res]: next }
    })
  }, [])

  const handleP2pPropose = useCallback(() => {
    const offer: Record<string, number> = {}
    const want: Record<string, number> = {}
    for (const [k, v] of Object.entries(p2pOffer)) {
      if (v > 0) offer[k] = v
    }
    for (const [k, v] of Object.entries(p2pWant)) {
      if (v > 0) want[k] = v
    }
    if (Object.keys(offer).length && Object.keys(want).length) {
      gameSocket.send({ type: 'propose_trade', offer, want } as any)
      setP2pSentOffer(offer)
      setP2pSentWant(want)
      setP2pWaiting(true)
      setP2pProposing(false)
    }
  }, [p2pOffer, p2pWant])

  const handleP2pCancel = useCallback(() => {
    gameSocket.send({ type: 'cancel_trade' } as any)
    setP2pWaiting(false)
    setP2pProposing(false)
    setP2pOffer({})
    setP2pWant({})
  }, [])

  const handleP2pAccept = useCallback((proposalId: string) => {
    gameSocket.send({ type: 'accept_trade', proposal_id: proposalId } as any)
  }, [])

  const handleP2pReject = useCallback((proposalId: string) => {
    gameSocket.send({ type: 'reject_trade', proposal_id: proposalId } as any)
    setTradeProposal(null)
  }, [])

  const p2pOfferTotal = Object.values(p2pOffer).reduce((a, b) => a + b, 0)
  const p2pWantTotal = Object.values(p2pWant).reduce((a, b) => a + b, 0)
  const p2pValid = p2pOfferTotal > 0 && p2pWantTotal > 0 &&
    Object.entries(p2pOffer).every(([res, amt]) => (myResources[res as ResourceType] ?? 0) >= amt)

  // Dev card handlers
  const handleBuyDevCard = useCallback(() => {
    gameSocket.send({ type: 'buy_dev_card' } as any)
  }, [])

  const handlePlayKnight = useCallback(() => {
    gameSocket.send({ type: 'play_dev_card', card_type: 'knight' } as any)
    setPlayingCard(null)
  }, [])

  const handlePlayYearOfPlenty = useCallback(() => {
    gameSocket.send({ type: 'play_dev_card', card_type: 'year_of_plenty', resources: yopSelection } as any)
    setPlayingCard(null)
    setYopSelection({})
  }, [yopSelection])

  const handlePlayMonopoly = useCallback(() => {
    if (!monopolyResource) return
    gameSocket.send({ type: 'play_dev_card', card_type: 'monopoly', resource: monopolyResource } as any)
    setPlayingCard(null)
    setMonopolyResource('')
  }, [monopolyResource])

  const handlePlayRoadBuilding = useCallback(() => {
    gameSocket.send({ type: 'play_dev_card', card_type: 'road_building' } as any)
    setPlayingCard(null)
  }, [])

  const handlePlayDevCard = useCallback((cardType: DevCardType) => {
    if (cardType === 'knight') {
      handlePlayKnight()
    } else if (cardType === 'road_building') {
      handlePlayRoadBuilding()
    } else if (cardType === 'year_of_plenty') {
      setPlayingCard('year_of_plenty')
      setYopSelection({})
    } else if (cardType === 'monopoly') {
      setPlayingCard('monopoly')
      setMonopolyResource('')
    }
  }, [handlePlayKnight, handlePlayRoadBuilding])

  const yopTotal = Object.values(yopSelection).reduce((a, b) => a + b, 0)

  const handleYopChange = useCallback((res: string, delta: number) => {
    setYopSelection(prev => {
      const cur = prev[res] ?? 0
      const next = Math.max(0, cur + delta)
      const total = Object.values(prev).reduce((a, b) => a + b, 0) - cur + next
      if (total > 2) return prev
      return { ...prev, [res]: next }
    })
  }, [])

  const hasOreWheatSheep = (myResources.ore ?? 0) >= 1 && (myResources.wheat ?? 0) >= 1 && (myResources.sheep ?? 0) >= 1

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
      if (mode === 'road' || turnPhase === 'road_building') {
        gameSocket.send({ type: 'build', piece: 'road', position: pos } as any)
        if (!isSetupPhase && turnPhase !== 'road_building') setBuildMode('none')
      }
    },
    [isMyTurn, requiredBuildMode, selectEdge, isSetupPhase, turnPhase],
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
          <button
            className={styles.leaveBtn}
            type="button"
            title="Leave game"
            onClick={() => {
              const isFinished = game?.phase === 'finished' || !!game?.winner
              if (!isFinished && !window.confirm('Leave this game?')) return
              gameSocket.disconnect()
              navigate('/')
            }}
          >
            <span aria-hidden="true">&larr;</span> Leave
          </button>
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
          {/* Bank resources row */}
          <div className={styles.bankRow}>
            <span className={styles.bankLabel}>Bank</span>
            {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
              const knownTotal = players.reduce((sum, p) => {
                const r = p.resources?.[res] ?? 0
                return sum + r
              }, 0)
              const bankRemaining = 19 - knownTotal
              return (
                <span key={res} className={styles.bankItem}>
                  {RESOURCE_LABELS[res]}
                  <span className={`${styles.bankCount} ${bankRemaining <= 3 ? styles.bankCountLow : ''}`}>
                    {bankRemaining}
                  </span>
                </span>
              )
            })}
            <span className={styles.bankDivider} />
            <span className={styles.bankItem}>
              {'🎴'}
              <span className={styles.bankCount}>{deckCount}</span>
            </span>
          </div>

          {/* Turn banner */}
          <div className={isMyTurn ? styles.turnBannerYou : styles.turnBannerWait}>
            <span className={styles.turnBannerLabel}>
              {isMyTurn ? 'YOUR TURN' : `Waiting for ${currentPlayer?.name ?? '...'}...`}
            </span>
            <span className={styles.turnStep}>
              {isSetupPhase
                ? isMyTurn
                  ? `Setup Round ${game?.phase === 'setup_round1' ? '1' : '2'}: Place your ${game?.phase === 'setup_round1' ? '1st' : '2nd'} ${requiredBuildMode}`
                  : `Waiting for ${currentPlayer?.name ?? '...'} to place their ${requiredBuildMode}...`
                : mustDiscard
                  ? 'Discard cards (rolled 7)'
                  : isRobberPlace
                    ? 'Move the robber'
                    : isRobberSteal
                      ? 'Choose who to steal from'
                      : turnPhase === 'robber_discard'
                        ? 'Waiting for others to discard...'
                        : turnPhase === 'pre_roll'
                          ? 'Roll the dice'
                          : turnPhase === 'post_roll'
                            ? 'Build or trade'
                            : turnPhase === 'road_building'
                              ? 'Place free roads'
                              : turnPhase === 'year_of_plenty'
                                ? 'Pick 2 resources'
                                : turnPhase === 'monopoly'
                                  ? 'Choose a resource to monopolize'
                                  : turnPhase}
            </span>
          </div>

          {/* Setup draft order indicator */}
          {isSetupPhase && setupOrder && setupOrder.length > 0 && (
            <div style={{ textAlign: 'center', fontSize: '0.85rem', padding: '4px 8px', opacity: 0.85 }}>
              Order: {setupOrder.map((idx, i) => {
                const p = players[idx]
                const isCurrent = p?.id === game?.currentPlayerId
                return (
                  <span key={i}>
                    {i > 0 && ' \u2192 '}
                    <span style={{ fontWeight: isCurrent ? 'bold' : 'normal', textDecoration: isCurrent ? 'underline' : 'none' }}>
                      {p?.name ?? `P${idx + 1}`}
                    </span>
                  </span>
                )
              })}
            </div>
          )}

          {/* Turn info / dice */}
          <div className={styles.turnSection}>
            <div className={styles.turnHeader}>
              <DiceDisplay
                dice={game?.lastDiceRoll}
                rolling={rolling}
              />
            </div>
          </div>

          {/* Other players' info cards */}
          <div className={styles.playersGrid}>
            {orderedPlayers.filter(p => p.id !== myPlayerId).map(p => {
              const cardCount = p.resourceCount ?? Object.values(p.resources).reduce((a, b) => a + b, 0)
              const hasLongestRoad = game?.longestRoadPlayerId === p.id
              const hasLargestArmy = game?.largestArmyPlayerId === p.id
              const knightsCount = (p as any).knightsPlayed ?? 0
              const isActive = p.id === game?.currentPlayerId
              return (
                <div
                  key={p.id}
                  className={`${styles.playerCard} ${isActive ? styles.playerCardActive : ''}`}
                  style={{ '--player-color': p.color } as CSSProperties}
                >
                  <div className={styles.playerCardHeader}>
                    <div className={styles.playerCardAvatar} style={{ backgroundColor: p.color }}>
                      {p.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                    </div>
                    <span className={styles.playerCardName}>{p.name}</span>
                    <div className={styles.playerCardBadges}>
                      {hasLongestRoad && <span className={styles.playerBadge} title="Longest Road">LR</span>}
                      {hasLargestArmy && <span className={styles.playerBadge} title="Largest Army">LA</span>}
                    </div>
                    <span className={styles.playerCardVP}>{p.victoryPoints}</span>
                  </div>
                  <div className={styles.resCardBacks}>
                    {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as const).map(res => (
                      <div
                        key={res}
                        className={styles.resCardBack}
                        style={{ background: RES_CARD_COLORS[res] }}
                        title={res}
                      >
                        <span className={styles.resCardBackCount}>?</span>
                      </div>
                    ))}
                    <span style={{ fontSize: 11, color: '#8a9bb0', marginLeft: 2 }}>{cardCount}</span>
                    <div className={styles.devCardBack} title="Dev cards">
                      <span className={styles.resCardBackCount}>?</span>
                    </div>
                  </div>
                  <div className={styles.playerCardBuildings}>
                    <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🏠'}</span><span className={styles.buildingCount}>{p.settlements}</span></span>
                    <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🏙️'}</span><span className={styles.buildingCount}>{p.cities}</span></span>
                    <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🛤️'}</span><span className={styles.buildingCount}>{p.roads}</span></span>
                    {knightsCount > 0 && (
                      <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'⚔️'}</span><span className={styles.buildingCount}>{knightsCount}</span></span>
                    )}
                  </div>
                </div>
              )
            })}
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

          {/* Development Cards (collapsible) */}
          <div className={styles.panel}>
            <button
              type="button"
              className={styles.devPanelToggle}
              onClick={() => setTradeOpen(prev => prev)} // dev cards always visible, toggle handled by CSS
            >
              <span>Development Cards ({devCards.length})</span>
            </button>
            <div className={styles.devCardList}>
              {devCards.map((card, i) => {
                const isVP = card.card_type === 'victory_point'
                const isKnight = card.card_type === 'knight'
                const boughtThisTurn = card.bought_on_turn === currentTurn
                const knightPlayable = isKnight && !devCardPlayed && !boughtThisTurn && isMyTurn && (turnPhase === 'pre_roll' || turnPhase === 'post_roll')
                const normalPlayable = !isKnight && !isVP && !devCardPlayed && !boughtThisTurn && isMyTurn && turnPhase === 'post_roll'
                const canPlay = isVP ? false : isKnight ? knightPlayable : normalPlayable

                const CARD_ICONS: Record<string, string> = { knight: '🗡️', victory_point: '🏆', year_of_plenty: '🌽', monopoly: '💰', road_building: '🛤️' }
                const CARD_LABELS: Record<string, string> = { knight: 'Knight', victory_point: 'Victory Point', year_of_plenty: 'Year of Plenty', monopoly: 'Monopoly', road_building: 'Road Building' }

                return (
                  <div
                    key={i}
                    className={`${styles.devCardItem} ${canPlay ? styles.playable : ''}`}
                  >
                    <span className={styles.devCardIcon}>{CARD_ICONS[card.card_type] ?? '?'}</span>
                    <span className={styles.devCardName}>{CARD_LABELS[card.card_type] ?? card.card_type}</span>
                    {boughtThisTurn && <span className={styles.devCardNew}>NEW</span>}
                    {canPlay && (
                      <button
                        type="button"
                        className={styles.devCardPlayBtn}
                        onClick={() => handlePlayDevCard(card.card_type)}
                      >
                        Play
                      </button>
                    )}
                  </div>
                )
              })}
              {devCards.length === 0 && (
                <span style={{ fontSize: 12, color: '#6c757d' }}>No cards yet</span>
              )}
            </div>
            {canTrade && (
              <button
                type="button"
                className={styles.buyDevCardBtn}
                onClick={handleBuyDevCard}
                disabled={!hasOreWheatSheep || deckCount === 0}
              >
                Buy Card ({deckCount} left) — ⛏️🌾🐑
              </button>
            )}
          </div>

          {/* Year of Plenty selection */}
          {playingCard === 'year_of_plenty' && (
            <div className={`${styles.panel} ${styles.yopPanel}`}>
              <p className={styles.panelTitle}>Year of Plenty — Pick 2 resources</p>
              <div className={styles.discardGrid}>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                  const sel = yopSelection[res] ?? 0
                  return (
                    <div key={res} className={styles.discardRow}>
                      <span className={styles.discardLabel}>{res}</span>
                      <button type="button" className={styles.discardBtn} onClick={() => handleYopChange(res, -1)} disabled={sel <= 0}>-</button>
                      <span className={styles.discardCount}>{sel}</span>
                      <button type="button" className={styles.discardBtn} onClick={() => handleYopChange(res, 1)} disabled={yopTotal >= 2}>+</button>
                    </div>
                  )
                })}
              </div>
              <div className={styles.tradeActions}>
                <button
                  type="button"
                  className={styles.tradeSubmitBtn}
                  onClick={handlePlayYearOfPlenty}
                  disabled={yopTotal !== 2}
                >
                  Confirm ({yopTotal}/2)
                </button>
                <button type="button" className={styles.tradeResetBtn} onClick={() => setPlayingCard(null)}>Cancel</button>
              </div>
            </div>
          )}

          {/* Monopoly selection */}
          {playingCard === 'monopoly' && (
            <div className={`${styles.panel} ${styles.monopolyPanel}`}>
              <p className={styles.panelTitle}>Monopoly — Pick a resource</p>
              <div className={styles.devCardList}>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => (
                  <button
                    key={res}
                    type="button"
                    className={`${styles.devCardItem} ${monopolyResource === res ? styles.playable : ''}`}
                    onClick={() => setMonopolyResource(res)}
                    style={{ cursor: 'pointer', textTransform: 'capitalize' }}
                  >
                    {res}
                  </button>
                ))}
              </div>
              <div className={styles.tradeActions} style={{ marginTop: 8 }}>
                <button
                  type="button"
                  className={styles.tradeSubmitBtn}
                  onClick={handlePlayMonopoly}
                  disabled={!monopolyResource}
                >
                  Confirm {monopolyResource || '...'}
                </button>
                <button type="button" className={styles.tradeResetBtn} onClick={() => setPlayingCard(null)}>Cancel</button>
              </div>
            </div>
          )}

          {/* Road Building hint */}
          {turnPhase === 'road_building' && isMyTurn && (
            <div className={`${styles.panel} ${styles.yopPanel}`}>
              <p className={styles.panelTitle}>Road Building</p>
              <p className={styles.roadBuildingHint}>Place 2 free roads on the map.</p>
            </div>
          )}

          {/* Trade with bank (collapsible) */}
          {canTrade && (
            <div className={styles.panel}>
              <button
                type="button"
                className={styles.tradePanelToggle}
                onClick={() => setTradeOpen(prev => !prev)}
              >
                <span>{'🏦'} Bank Trade</span>
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

          {/* P2P Trade: Propose button */}
          {canTrade && !p2pProposing && !p2pWaiting && (
            <button
              type="button"
              className={styles.p2pProposeBtn}
              onClick={() => {
                setP2pProposing(true)
                setP2pOffer({})
                setP2pWant({})
              }}
            >
              {'🤝'} Propose Trade with Players
            </button>
          )}

          {/* P2P Trade: Building a proposal */}
          {p2pProposing && (
            <div className={`${styles.panel} ${styles.p2pTradePanel}`}>
              <p className={styles.panelTitle}>Propose Trade</p>
              <div className={styles.tradeSide}>
                <span className={styles.tradeLabel}>You Give</span>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                  const have = myResources[res] ?? 0
                  const offering = p2pOffer[res] ?? 0
                  return (
                    <div key={res} className={styles.tradeRow}>
                      <span className={styles.tradeRes}>{RESOURCE_LABELS[res]} {res}</span>
                      <button type="button" className={styles.tradeBtn} onClick={() => handleP2pOfferChange(res, -1)} disabled={offering <= 0}>-</button>
                      <span className={styles.tradeCount}>{offering}</span>
                      <button type="button" className={styles.tradeBtn} onClick={() => handleP2pOfferChange(res, 1)} disabled={offering >= have}>+</button>
                    </div>
                  )
                })}
              </div>
              <div className={styles.tradeSide}>
                <span className={styles.tradeLabel}>You Want</span>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as ResourceType[]).map(res => {
                  const wanting = p2pWant[res] ?? 0
                  return (
                    <div key={res} className={styles.tradeRow}>
                      <span className={styles.tradeRes}>{RESOURCE_LABELS[res]} {res}</span>
                      <button type="button" className={styles.tradeBtn} onClick={() => handleP2pWantChange(res, -1)} disabled={wanting <= 0}>-</button>
                      <span className={styles.tradeCount}>{wanting}</span>
                      <button type="button" className={styles.tradeBtn} onClick={() => handleP2pWantChange(res, 1)}>+</button>
                    </div>
                  )
                })}
              </div>
              <div className={styles.tradeActions}>
                <button
                  type="button"
                  className={styles.tradeSubmitBtn}
                  onClick={handleP2pPropose}
                  disabled={!p2pValid}
                >
                  Send Proposal
                </button>
                <button
                  type="button"
                  className={styles.tradeResetBtn}
                  onClick={() => { setP2pProposing(false); setP2pOffer({}); setP2pWant({}) }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* P2P Trade: Waiting for response (proposer view) */}
          {p2pWaiting && (
            <div className={`${styles.panel} ${styles.p2pWaiting}`}>
              <p className={styles.panelTitle}>
                <span className={styles.p2pWaitingSpinner} />
                Waiting for response...
              </p>
              <div className={styles.p2pSummary}>
                <span className={styles.p2pSummaryLabel}>Your offer:</span>
                <span className={styles.p2pSummaryValue}>
                  {Object.entries(p2pSentOffer).filter(([, n]) => n > 0).map(([r, n]) => `${n} ${r}`).join(', ') || 'nothing'}
                </span>
              </div>
              <div className={styles.p2pSummary}>
                <span className={styles.p2pSummaryLabel}>You want:</span>
                <span className={styles.p2pSummaryValue}>
                  {Object.entries(p2pSentWant).filter(([, n]) => n > 0).map(([r, n]) => `${n} ${r}`).join(', ') || 'nothing'}
                </span>
              </div>
              <button
                type="button"
                className={styles.p2pCancelBtn}
                onClick={handleP2pCancel}
              >
                Cancel Proposal
              </button>
            </div>
          )}

          {/* P2P Trade: Incoming proposal (non-proposer view) */}
          {tradeProposal && tradeProposal.proposer_id !== myPlayerId && (
            <div className={`${styles.panel} ${styles.p2pProposalIncoming}`} role="alert">
              <p className={styles.panelTitle}>
                Trade Offer from {tradeProposal.proposer_name}
              </p>
              <div className={styles.p2pSummary}>
                <span className={styles.p2pSummaryLabel}>They offer:</span>
                <span className={styles.p2pSummaryValue}>
                  {Object.entries(tradeProposal.offer).filter(([, n]) => n > 0).map(([r, n]) => `${n} ${r}`).join(', ')}
                </span>
              </div>
              <div className={styles.p2pSummary}>
                <span className={styles.p2pSummaryLabel}>They want:</span>
                <span className={styles.p2pSummaryValue}>
                  {Object.entries(tradeProposal.want).filter(([, n]) => n > 0).map(([r, n]) => `${n} ${r}`).join(', ')}
                </span>
              </div>
              <div className={styles.p2pResponseActions}>
                <button
                  type="button"
                  className={styles.p2pAcceptBtn}
                  onClick={() => handleP2pAccept(tradeProposal.id)}
                >
                  Accept
                </button>
                <button
                  type="button"
                  className={styles.p2pRejectBtn}
                  onClick={() => handleP2pReject(tradeProposal.id)}
                >
                  Reject
                </button>
              </div>
            </div>
          )}

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
                  <span className={styles.buildIcon}>{'🛤️'}</span>
                  <span>Road</span>
                  <span className={styles.cost}>{'🌲🧱'}</span>
                </button>
                <button
                  className={`${styles.buildBtn} ${buildMode === 'settlement' ? styles.active : ''}`}
                  onClick={() => toggleBuildMode('settlement')}
                  disabled={isSetupPhase}
                  type="button"
                  title="Settlement (1 wood + 1 brick + 1 wheat + 1 sheep)"
                >
                  <span className={styles.buildIcon}>{'🏠'}</span>
                  <span>Settlement</span>
                  <span className={styles.cost}>{'🌲🧱🌾🐑'}</span>
                </button>
                <button
                  className={`${styles.buildBtn} ${buildMode === 'city' ? styles.active : ''}`}
                  onClick={() => toggleBuildMode('city')}
                  disabled={isSetupPhase}
                  type="button"
                  title="City (2 wheat + 3 ore)"
                >
                  <span className={styles.buildIcon}>{'🏙️'}</span>
                  <span>City</span>
                  <span className={styles.cost}>{'🌾🌾⛏️⛏️⛏️'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Build Cost Reference Card (P1-07) */}
          <div className={`${styles.panel} ${styles.costRef}`}>
            <p className={styles.panelTitle}>Build Costs</p>
            <div className={styles.costGrid}>
              <div className={styles.costRow}>
                <span className={styles.costPiece}>{'\uD83D\uDEE4\uFE0F'} Road</span>
                <span className={styles.costDots}>
                  <span className={styles.resDot} style={{ background: '#4a8c3f' }} title="Wood" />
                  <span className={styles.resDot} style={{ background: '#c0392b' }} title="Brick" />
                </span>
              </div>
              <div className={styles.costRow}>
                <span className={styles.costPiece}>{'\uD83C\uDFE0'} Settlement</span>
                <span className={styles.costDots}>
                  <span className={styles.resDot} style={{ background: '#4a8c3f' }} title="Wood" />
                  <span className={styles.resDot} style={{ background: '#c0392b' }} title="Brick" />
                  <span className={styles.resDot} style={{ background: '#f1c40f' }} title="Wheat" />
                  <span className={styles.resDot} style={{ background: '#7dcea0' }} title="Sheep" />
                </span>
              </div>
              <div className={styles.costRow}>
                <span className={styles.costPiece}>{'\uD83C\uDFD9\uFE0F'} City</span>
                <span className={styles.costDots}>
                  <span className={styles.resDot} style={{ background: '#f1c40f' }} title="Wheat" />
                  <span className={styles.resDot} style={{ background: '#f1c40f' }} title="Wheat" />
                  <span className={styles.resDot} style={{ background: '#7f8c8d' }} title="Ore" />
                  <span className={styles.resDot} style={{ background: '#7f8c8d' }} title="Ore" />
                  <span className={styles.resDot} style={{ background: '#7f8c8d' }} title="Ore" />
                </span>
              </div>
              <div className={styles.costRow}>
                <span className={styles.costPiece}>{'\uD83C\uDFB4'} Dev Card</span>
                <span className={styles.costDots}>
                  <span className={styles.resDot} style={{ background: '#f1c40f' }} title="Wheat" />
                  <span className={styles.resDot} style={{ background: '#7dcea0' }} title="Sheep" />
                  <span className={styles.resDot} style={{ background: '#7f8c8d' }} title="Ore" />
                </span>
              </div>
            </div>
          </div>

          {/* My player card (at bottom, larger) */}
          {me && (
            <div
              className={`${styles.playerCard} ${styles.playerCardMe} ${isMyTurn ? styles.playerCardActive : ''}`}
              style={{ '--player-color': me.color } as CSSProperties}
            >
              <div className={styles.playerCardHeader}>
                <div className={styles.playerCardAvatar} style={{ backgroundColor: me.color }}>
                  {me.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                </div>
                <span className={styles.playerCardName}>
                  {me.name} <span className={styles.playerCardYouTag}>(you)</span>
                </span>
                <div className={styles.playerCardBadges}>
                  {game?.longestRoadPlayerId === me.id && <span className={styles.playerBadge} title="Longest Road">LR</span>}
                  {game?.largestArmyPlayerId === me.id && <span className={styles.playerBadge} title="Largest Army">LA</span>}
                </div>
                <span className={styles.playerCardVP}>{me.victoryPoints}</span>
              </div>
              <div className={styles.resCardBacks}>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as const).map(res => {
                  const count = myResources[res] ?? 0
                  return (
                    <div
                      key={res}
                      className={`${styles.resCardBack} ${styles.resCardBackMine} ${count === 0 ? styles.resCardBackDimmed : ''}`}
                      style={{ '--card-color': RES_CARD_COLORS[res], background: RES_CARD_COLORS[res] } as CSSProperties}
                      title={`${res}: ${count}`}
                    >
                      <span className={styles.resCardBackCount}>{count}</span>
                      <span className={styles.resCardBackLabel}>{res.slice(0, 2)}</span>
                    </div>
                  )
                })}
                <div className={styles.devCardBack} title={`Dev cards: ${devCards.length}`}>
                  <span className={styles.resCardBackCount}>{devCards.length}</span>
                  <span className={styles.devCardBackLabel}>dev</span>
                </div>
              </div>
              <div className={styles.playerCardBuildings}>
                <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🏠'}</span><span className={styles.buildingCount}>{me.settlements}</span></span>
                <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🏙️'}</span><span className={styles.buildingCount}>{me.cities}</span></span>
                <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'🛤️'}</span><span className={styles.buildingCount}>{me.roads}</span></span>
                {(me as any).knightsPlayed > 0 && (
                  <span className={styles.buildingStat}><span className={styles.buildingIcon}>{'⚔️'}</span><span className={styles.buildingCount}>{(me as any).knightsPlayed}</span></span>
                )}
              </div>
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

      {/* Bottom action bar with large resource cards */}
      <footer className={`${styles.actionBar} ${myHandTotal > 7 ? styles.actionBarDanger : ''}`}>
        <div className={styles.actionLeft}>
          {isSetupPhase ? (
            <span className={styles.buildHint}>
              Setup Round {game?.phase === 'setup_round1' ? '1' : '2'}: place your {game?.phase === 'setup_round1' ? '1st' : '2nd'} {requiredBuildMode}
            </span>
          ) : buildMode !== 'none' ? (
            <span className={styles.buildHint}>
              Click map to place {buildMode}
            </span>
          ) : (
            <div className={styles.bottomResCardsWrap}>
              <div className={styles.bottomResCards}>
                {(['wood', 'brick', 'wheat', 'sheep', 'ore'] as const).map(res => {
                  const count = myResources[res] ?? 0
                  return (
                    <div
                      key={res}
                      className={`${styles.resCard} ${count === 0 ? styles.resCardDimmed : ''}`}
                      style={{ background: RES_CARD_COLORS[res] }}
                      title={`${res}: ${count}`}
                    >
                      <span className={styles.resCardIcon}>{RESOURCE_LABELS[res]}</span>
                      <span className={styles.resCardCount}>{count}</span>
                      <span className={styles.resCardName}>{res}</span>
                    </div>
                  )
                })}
              </div>
              {myHandTotal > 7 && (
                <div className={styles.handWarning}>
                  {'\u26A0\uFE0F'} You have {myHandTotal} cards — risk losing half on a 7!
                </div>
              )}
            </div>
          )}
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

      {/* Victory overlay */}
      {game?.winner && (() => {
        const winnerName = players.find(p => p.id === game.winner)?.name ?? 'Someone'

        // Build VP breakdown sorted by VP descending
        const vpRows = players
          .map(p => {
            const raw = rawPlayers.find(rp => rp.player_id === p.id)
            const settlementsVP = p.settlements
            const citiesVP = p.cities * 2
            const hasLR = game.longestRoadPlayerId === p.id
            const hasLA = game.largestArmyPlayerId === p.id
            const lrVP = hasLR ? 2 : 0
            const laVP = hasLA ? 2 : 0
            const vpCards = (raw?.dev_cards ?? []).filter(c => c.card_type === 'victory_point').length
            const totalVP = p.victoryPoints
            return {
              id: p.id,
              name: p.name,
              color: p.color,
              settlements: p.settlements,
              cities: p.cities,
              settlementsVP,
              citiesVP,
              hasLR,
              hasLA,
              lrVP,
              laVP,
              vpCards,
              totalVP,
              isWinner: p.id === game.winner,
            }
          })
          .sort((a, b) => b.totalVP - a.totalVP)

        return (
          <div className={styles.winnerOverlay} role="dialog" aria-label="Game over">
            {/* Confetti pieces */}
            {Array.from({ length: 10 }).map((_, i) => (
              <span
                key={i}
                className={styles.confetti}
                style={{ '--confetti-x': `${10 + Math.random() * 80}vw`, '--confetti-delay': `${Math.random() * 2}s`, '--confetti-color': ['#ffd60a', '#e63946', '#2a9d8f', '#f4a261', '#6a4c93'][i % 5] } as CSSProperties}
              />
            ))}

            <div className={styles.winnerCard}>
              <span className={styles.winnerEmoji}>🏆</span>
              <h2 className={styles.winnerTitle}>{winnerName} Wins!</h2>

              {/* VP Breakdown Table */}
              <div className={styles.vpTableWrap}>
                <table className={styles.vpTable}>
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Settlements</th>
                      <th>Cities</th>
                      <th>LR</th>
                      <th>LA</th>
                      <th>VP Cards</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {vpRows.map(row => (
                      <tr key={row.id} className={row.isWinner ? styles.vpRowWinner : ''}>
                        <td>
                          <span className={styles.vpPlayerDot} style={{ background: row.color }} />
                          {row.name}{row.isWinner ? ' *' : ''}
                        </td>
                        <td>{row.settlements} ({row.settlementsVP})</td>
                        <td>{row.cities} ({row.citiesVP})</td>
                        <td>{row.hasLR ? '✓ (2)' : '-'}</td>
                        <td>{row.hasLA ? '✓ (2)' : '-'}</td>
                        <td>{row.vpCards}</td>
                        <td className={styles.vpTotal}>{row.totalVP}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className={styles.winnerActions}>
                <button
                  className={styles.playAgainBtn}
                  onClick={() => { gameSocket.disconnect(); navigate('/') }}
                  type="button"
                >
                  Play Again
                </button>
                <button
                  className={styles.homeBtnOutline}
                  onClick={() => { gameSocket.disconnect(); navigate('/') }}
                  type="button"
                >
                  Back to Home
                </button>
              </div>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
