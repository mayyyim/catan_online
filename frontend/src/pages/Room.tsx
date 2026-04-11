import { useEffect, useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { getRoomState, addBot, removeBot, joinRoom, fetchMapSummaries, fetchMapDetail } from '../api'
import type { MapSummary, MapDetailData, MapDetailPort } from '../api'
import { useRoom } from '../context/RoomContext'
import { gameSocket } from '../ws/gameSocket'
import { PlayerAvatar } from '../components/PlayerAvatar'
import { MAP_CONFIGS } from '../maps/definitions'
import { TERRAIN_COLORS, TERRAIN_LABELS, RESOURCE_LABELS } from '../types'
import type { MapConfig } from '../types'
import { cubeToPixel, hexCorners, cornersToSvgPoints } from '../engine/hexMath'
import styles from './Room.module.css'

// ─── Hex thumbnail for map cards ────────────────────────────────────────────

function buildHexSvg(
  tiles: { q: number; r: number; tile_type: string }[],
  hexSize: number,
) {
  if (!tiles.length) return { paths: [] as { cx: number; cy: number; tile_type: string }[], viewBox: '0 0 1 1', w: 1, h: 1 }
  const pts = tiles.map(t => cubeToPixel(t.q, t.r, hexSize))
  const minX = Math.min(...pts.map(p => p.x)) - hexSize
  const minY = Math.min(...pts.map(p => p.y)) - hexSize * 0.9
  const maxX = Math.max(...pts.map(p => p.x)) + hexSize
  const maxY = Math.max(...pts.map(p => p.y)) + hexSize * 0.9
  const w = maxX - minX
  const h = maxY - minY
  const paths = tiles.map((t, i) => ({
    cx: pts[i].x - minX,
    cy: pts[i].y - minY,
    tile_type: t.tile_type,
  }))
  return { paths, viewBox: `0 0 ${w.toFixed(1)} ${h.toFixed(1)}`, w, h }
}

function HexThumbnail({ summary, size = 10 }: { summary: MapSummary; size?: number }) {
  const { paths, viewBox, w, h } = useMemo(
    () => buildHexSvg(summary.tiles, size),
    [summary, size],
  )
  if (!paths.length) return <div className={styles.thumbPlaceholder}>?</div>
  return (
    <svg viewBox={viewBox} width={w} height={h} style={{ maxWidth: '100%', maxHeight: 90 }}>
      {paths.map(({ cx, cy, tile_type }, i) => {
        const corners = hexCorners(cx, cy, size)
        const points = cornersToSvgPoints(corners)
        const fill = TERRAIN_COLORS[tile_type as keyof typeof TERRAIN_COLORS] ?? '#444'
        return (
          <polygon key={i} points={points} fill={fill} stroke="#0d1b2a" strokeWidth={0.6} />
        )
      })}
    </svg>
  )
}

// ─── Detail map (full size with tokens + ports) ─────────────────────────────

const SQ3 = Math.sqrt(3)
const SIDE_DIRS: [number, number][] = [
  [1.5, SQ3 / 2], [1.5, -SQ3 / 2], [0, -SQ3],
  [-1.5, -SQ3 / 2], [-1.5, SQ3 / 2], [0, SQ3],
]

const TERRAIN_RESOURCE: Record<string, string> = {
  forest: 'Wood', hills: 'Brick', fields: 'Wheat',
  pasture: 'Sheep', mountains: 'Ore',
}
const RESOURCE_COLOR: Record<string, string> = {
  Wood: '#2d6a4f', Brick: '#b85c38', Wheat: '#d4aa00',
  Sheep: '#52b788', Ore: '#6c757d',
}

function HexDetailMap({ data }: { data: MapDetailData }) {
  const hexSize = data.size === 'large' ? 20 : 28
  const { paths, viewBox, w, h } = useMemo(() => buildHexSvg(data.tiles, hexSize), [data, hexSize])

  const portMarkers = useMemo(() => {
    const pts = data.tiles.map(t => cubeToPixel(t.q, t.r, hexSize))
    const minX = Math.min(...pts.map(p => p.x)) - hexSize
    const minY = Math.min(...pts.map(p => p.y)) - hexSize * 0.9
    return data.ports.map((port, idx) => {
      const { x, y } = cubeToPixel(port.q, port.r, hexSize)
      const cx = x - minX
      const cy = y - minY
      const [ddx, ddy] = SIDE_DIRS[port.side] ?? [0, 0]
      const px = cx + ddx * hexSize * 0.65
      const py = cy + ddy * hexSize * 0.65
      const label = port.resource ? RESOURCE_LABELS[port.resource as keyof typeof RESOURCE_LABELS] : '?'
      return { idx, px, py, label, ratio: port.ratio }
    })
  }, [data, hexSize])

  if (!paths.length) return null
  return (
    <svg viewBox={viewBox} width={w} height={h} style={{ maxWidth: '100%', maxHeight: 340 }}>
      {paths.map(({ cx, cy, tile_type }, i) => {
        const tile = data.tiles[i]
        const corners = hexCorners(cx, cy, hexSize)
        const points = cornersToSvgPoints(corners)
        const fill = TERRAIN_COLORS[tile_type as keyof typeof TERRAIN_COLORS] ?? '#444'
        const emoji = TERRAIN_LABELS[tile_type as keyof typeof TERRAIN_LABELS] ?? ''
        const isHigh = tile.token === 6 || tile.token === 8
        const tokenY = cy + hexSize * 0.38
        return (
          <g key={i}>
            <polygon points={points} fill={fill} stroke="#0d1b2a" strokeWidth={1.2} />
            {emoji && tile_type !== 'desert' && (
              <text x={cx} y={cy - hexSize * 0.1} textAnchor="middle" dominantBaseline="middle" fontSize={hexSize * 0.72}>{emoji}</text>
            )}
            {tile.token != null && (
              <>
                <circle cx={cx} cy={tokenY} r={hexSize * 0.38} fill="rgba(248,249,250,0.92)" stroke={isHigh ? '#e63946' : '#adb5bd'} strokeWidth={1} />
                <text x={cx} y={tokenY + hexSize * 0.13} textAnchor="middle" dominantBaseline="middle" fontSize={hexSize * 0.42} fontWeight="bold" fill={isHigh ? '#e63946' : '#212529'}>{tile.token}</text>
              </>
            )}
          </g>
        )
      })}
      {portMarkers.map(({ idx, px, py, label, ratio }) => (
        <g key={idx}>
          <circle cx={px} cy={py} r={hexSize * 0.45} fill="#1a3a5c" stroke="#ffd60a" strokeWidth={1.2} />
          <text x={px} y={py - hexSize * 0.08} textAnchor="middle" dominantBaseline="middle" fontSize={hexSize * 0.38}>{label}</text>
          <text x={px} y={py + hexSize * 0.3} textAnchor="middle" fontSize={hexSize * 0.28} fill="#ffd60a" fontWeight="bold">{ratio}:1</text>
        </g>
      ))}
    </svg>
  )
}

function ResourceBars({ tiles }: { tiles: { tile_type: string }[] }) {
  const counts: Record<string, number> = {}
  tiles.forEach(t => {
    const r = TERRAIN_RESOURCE[t.tile_type]
    if (r) counts[r] = (counts[r] ?? 0) + 1
  })
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (!total) return null
  return (
    <div className={styles.resBars}>
      {Object.entries(counts).sort(([, a], [, b]) => b - a).map(([res, cnt]) => (
        <div key={res} className={styles.resRow}>
          <span className={styles.resLabel}>{res}</span>
          <div className={styles.barTrack}>
            <div className={styles.barFill} style={{ width: `${(cnt / total) * 100}%`, background: RESOURCE_COLOR[res] }} />
          </div>
          <span className={styles.resCount}>{cnt}</span>
        </div>
      ))}
    </div>
  )
}

function PortList({ ports }: { ports: MapDetailPort[] }) {
  if (!ports.length) return null
  return (
    <div className={styles.portList}>
      {ports.map((p, i) => (
        <span key={i} className={`${styles.portBadge} ${p.resource ? styles.portSpecific : ''}`}>
          {p.resource ? RESOURCE_LABELS[p.resource as keyof typeof RESOURCE_LABELS] : '?'} {p.ratio}:1
        </span>
      ))}
    </div>
  )
}

// ─── Map detail overlay ─────────────────────────────────────────────────────

function MapDetailOverlay({
  map,
  summary,
  onClose,
}: {
  map: MapConfig
  summary: MapSummary | undefined
  onClose: () => void
}) {
  const [detail, setDetail] = useState<MapDetailData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (map.id === 'random') return
    setLoading(true)
    fetchMapDetail(map.id).then(setDetail).finally(() => setLoading(false))
  }, [map.id])

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.detailPanel} onClick={e => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} type="button">x</button>
        <h2 className={styles.detailName}>{map.name}</h2>
        {map.size === 'large' && <span className={styles.sizeBadge}>Large</span>}
        <p className={styles.detailDesc}>{map.description}</p>
        {map.tags && (
          <div className={styles.tagRow}>
            {map.tags.map(t => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
        )}
        <div className={styles.detailMapWrap}>
          {loading && <span className={styles.detailLoading}>Loading...</span>}
          {!loading && detail && <HexDetailMap data={detail} />}
          {!loading && !detail && summary && summary.tiles.length > 0 && (
            <HexThumbnail summary={summary} size={map.size === 'large' ? 16 : 22} />
          )}
        </div>
        {detail && (
          <div className={styles.detailStats}>
            <div>
              <h3 className={styles.detailStatsTitle}>Resources</h3>
              <ResourceBars tiles={detail.tiles} />
            </div>
            <div>
              <h3 className={styles.detailStatsTitle}>Ports ({detail.ports.length})</h3>
              <PortList ports={detail.ports} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Map card in selection grid ─────────────────────────────────────────────

function MapCard({
  map,
  summary,
  selected,
  onSelect,
  onPreview,
}: {
  map: MapConfig
  summary: MapSummary | undefined
  selected: boolean
  onSelect: () => void
  onPreview: () => void
}) {
  return (
    <div className={`${styles.mapCard} ${selected ? styles.mapCardSelected : ''}`}>
      <button className={styles.mapCardMain} onClick={onSelect} type="button">
        <div className={styles.mapCardPreview}>
          {summary && summary.tiles.length > 0 ? (
            <HexThumbnail summary={summary} size={map.size === 'large' ? 7 : 10} />
          ) : (
            <div className={styles.thumbPlaceholder}>{map.id === 'random' ? '🎲' : '?'}</div>
          )}
        </div>
        <span className={styles.mapCardName}>{map.name}</span>
      </button>
      {map.id !== 'random' && (
        <button
          className={styles.previewBtn}
          onClick={e => { e.stopPropagation(); onPreview() }}
          type="button"
          title="Preview map details"
        >
          Details
        </button>
      )}
    </div>
  )
}

// ─── Room page ──────────────────────────────────────────────────────────────

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { room, myPlayerId, setRoom, setMyPlayerId, updatePlayer, removePlayer } =
    useRoom()

  const [seed, setSeed] = useState('')
  const [copied, setCopied] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected')
  const [wsError, setWsError] = useState('')
  const [summaries, setSummaries] = useState<Map<string, MapSummary>>(new Map())
  const [detailMap, setDetailMap] = useState<MapConfig | null>(null)
  // Join-via-link state
  const [joinName, setJoinName] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinError, setJoinError] = useState('')
  const inviteCodeFromUrl = searchParams.get('code') ?? ''
  const needsJoin = !myPlayerId && !sessionStorage.getItem('player_id') && !!inviteCodeFromUrl

  // Fetch map summaries from API
  useEffect(() => {
    fetchMapSummaries().then(data => {
      setSummaries(new Map(data.maps.map(m => [m.map_id, m])))
    })
  }, [])

  // Restore player_id from session if context was lost (e.g. refresh)
  useEffect(() => {
    const storedId = sessionStorage.getItem('player_id')
    if (storedId && !myPlayerId) setMyPlayerId(storedId)
  }, [myPlayerId, setMyPlayerId])

  // Load room state
  useEffect(() => {
    if (!roomId) return
    getRoomState(roomId).then(setRoom).catch(console.error)
  }, [roomId, setRoom])

  // WebSocket setup
  useEffect(() => {
    const pid = myPlayerId ?? sessionStorage.getItem('player_id')
    if (!roomId || !pid) return

    gameSocket.connect(roomId, pid)

    const unsubStatus = gameSocket.onStatus(setWsStatus)
    const unsubMsg = gameSocket.onMessage(msg => {
      if ((msg as any).type === 'room_update') {
        const m = msg as any
        setWsError('')
        const players = (m.data?.players ?? []).map((p: any, idx: number) => ({
          id: p.player_id,
          name: p.name,
          color: p.color,
          isHost: idx === 0,
          connected: !!p.connected,
          resources: { wood: 0, brick: 0, wheat: 0, sheep: 0, ore: 0 },
          victoryPoints: 0,
          settlements: 0,
          cities: 0,
          roads: 0,
        }))

        setRoom(prev => {
          const inviteCode =
            prev?.inviteCode ||
            sessionStorage.getItem('invite_code') ||
            ''

          return {
            roomId: roomId,
            inviteCode,
            hostId: m.data?.host_player_id ?? players[0]?.id ?? prev?.hostId ?? '',
            players,
            selectedMapId: m.data?.selected_map_id ?? prev?.selectedMapId ?? 'random',
            randomSeed: m.data?.seed ?? prev?.randomSeed ?? '',
            maxPlayers: prev?.maxPlayers ?? 4,
            status: m.data?.state === 'waiting' ? 'waiting' : 'started',
          }
        })
      }

      if ((msg as any).type === 'error') {
        setWsError((msg as any).data?.message ?? (msg as any).message ?? 'Server error')
      }

      if ((msg as any).type === 'game_state' && (msg as any).data?.phase !== 'waiting') {
        navigate(`/game/${roomId}`)
      }
    })

    return () => {
      unsubStatus()
      unsubMsg()
      gameSocket.disconnect()
    }
  }, [roomId, myPlayerId, navigate, setRoom, updatePlayer, removePlayer])

  const handleMapSelect = useCallback(
    (mapId: string) => {
      setRoom(prev => {
        if (!prev) return prev
        return { ...prev, selectedMapId: mapId, randomSeed: seed || prev.randomSeed }
      })
      gameSocket.send({ type: 'select_map', mapId, seed: seed || undefined })
    },
    [seed, setRoom],
  )

  const handleStartGame = useCallback(() => {
    gameSocket.send({
      type: 'start_game',
      map_id: room?.selectedMapId,
      mapId: room?.selectedMapId,
      seed: seed || room?.randomSeed || undefined,
    } as any)
  }, [room?.randomSeed, room?.selectedMapId, seed])

  const handleAddBot = useCallback(async () => {
    if (!roomId) return
    try {
      await addBot(roomId, `Bot ${Math.max(1, (room?.players?.length ?? 1))}`)
    } catch (e) {
      console.error(e)
    }
  }, [roomId, room?.players?.length])

  const handleRemoveBot = useCallback(async (playerId: string) => {
    if (!roomId) return
    try {
      await removeBot(roomId, playerId)
    } catch (e) {
      console.error(e)
    }
  }, [roomId])

  const handleJoinViaLink = useCallback(async () => {
    if (!joinName.trim() || !inviteCodeFromUrl) return
    setJoining(true)
    setJoinError('')
    try {
      const res = await joinRoom(inviteCodeFromUrl.toUpperCase(), joinName.trim())
      setMyPlayerId(res.player_id)
      sessionStorage.setItem('player_id', res.player_id)
      sessionStorage.setItem('player_name', joinName.trim())
      sessionStorage.setItem('invite_code', inviteCodeFromUrl.toUpperCase())
    } catch (e) {
      setJoinError(e instanceof Error ? e.message : 'Failed to join')
    } finally {
      setJoining(false)
    }
  }, [joinName, inviteCodeFromUrl, setMyPlayerId])

  const handleCopyInvite = useCallback(async () => {
    const link = `${window.location.origin}/room/${roomId}?code=${room?.inviteCode ?? ''}`
    await navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [roomId, room?.inviteCode])

  const isHost = room?.hostId === myPlayerId

  const handleLeaveRoom = useCallback(() => {
    gameSocket.disconnect()
    navigate('/')
  }, [navigate])

  // Show join form if arrived via invite link without being in the room
  if (needsJoin) {
    return (
      <div className={styles.loading}>
        <div className={styles.joinCard}>
          <h2 className={styles.joinTitle}>Join Game</h2>
          <p className={styles.joinSubtitle}>You've been invited! Enter your name to join.</p>
          <input
            className={styles.seedInput}
            type="text"
            placeholder="Your name..."
            value={joinName}
            onChange={e => setJoinName(e.target.value)}
            maxLength={20}
            autoFocus
            onKeyDown={e => e.key === 'Enter' && handleJoinViaLink()}
          />
          {joinError && <p style={{ color: '#e63946', fontSize: 13, margin: '8px 0 0' }}>{joinError}</p>}
          <button
            className={styles.startBtn}
            onClick={handleJoinViaLink}
            disabled={joining || !joinName.trim()}
            type="button"
            style={{ marginTop: 12 }}
          >
            {joining ? 'Joining...' : 'Join Room'}
          </button>
        </div>
      </div>
    )
  }

  if (!room) {
    return (
      <div className={styles.loading}>
        <div className={styles.spinner} />
        <p>Loading room...</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <button className={styles.leaveBtn} onClick={handleLeaveRoom} type="button" title="Leave room">
            ← Leave
          </button>
          <span className={styles.roomCode}>
            Room: <strong>{room.inviteCode}</strong>
          </span>
          <span className={`${styles.wsIndicator} ${styles[wsStatus]}`} title={wsStatus} />
        </div>
        <h1 className={styles.pageTitle}>Waiting Room</h1>
        <div className={styles.headerRight} />
      </header>

      <div className={styles.body}>
        {/* Left: Map selection */}
        <section className={styles.mapSection}>
          <h2 className={styles.sectionTitle}>Select Map</h2>
          <div className={styles.mapGrid}>
            {MAP_CONFIGS.map(map => (
              <MapCard
                key={map.id}
                map={map}
                summary={summaries.get(map.id)}
                selected={room.selectedMapId === map.id}
                onSelect={() => isHost && handleMapSelect(map.id)}
                onPreview={() => setDetailMap(map)}
              />
            ))}
          </div>
          <div className={styles.seedRow}>
            <label className={styles.seedLabel} htmlFor="seed-input">
              Random Seed (optional)
            </label>
            <input
              id="seed-input"
              className={styles.seedInput}
              type="text"
              placeholder="Leave blank for random"
              value={seed}
              onChange={e => setSeed(e.target.value)}
              disabled={!isHost}
            />
          </div>
        </section>

        {/* Right: Players + actions */}
        <section className={styles.rightSection}>
          <div className={styles.playerPanel}>
            <h2 className={styles.sectionTitle}>
              Players ({room.players.length}/{room.maxPlayers})
            </h2>
            <div className={styles.playerList}>
              {room.players.map(player => (
                <div key={player.id} className={styles.playerRow}>
                  <PlayerAvatar player={player} isMe={player.id === myPlayerId} compact={false} />
                  {isHost && player.name.startsWith('Bot') && player.id !== myPlayerId && (
                    <button
                      className={styles.removeBotBtn}
                      onClick={() => handleRemoveBot(player.id)}
                      type="button"
                      title="Remove bot"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}
              {Array.from({ length: room.maxPlayers - room.players.length }).map((_, i) => (
                <div key={`empty-${i}`} className={styles.emptySlot}>Waiting for player...</div>
              ))}
            </div>
            <button className={styles.inviteBtn} onClick={handleCopyInvite} type="button">
              {copied ? 'Copied!' : 'Copy Invite Link'}
            </button>
          </div>

          {isHost && (
            <>
              <button className={styles.inviteBtn} onClick={handleAddBot} disabled={room.players.length >= room.maxPlayers} type="button">
                Add Bot
              </button>
              <button className={styles.startBtn} onClick={handleStartGame} disabled={room.players.length < 2} type="button">
                Start Game
                {room.players.length < 2 && <span className={styles.startHint}>(need at least 2 players)</span>}
              </button>
            </>
          )}

          {!isHost && <p className={styles.waitingText}>Waiting for host to start the game...</p>}
          {wsError && <p className={styles.waitingText} style={{ color: '#e63946' }}>{wsError}</p>}
        </section>
      </div>

      {/* Map detail overlay */}
      {detailMap && (
        <MapDetailOverlay
          map={detailMap}
          summary={summaries.get(detailMap.id)}
          onClose={() => setDetailMap(null)}
        />
      )}
    </div>
  )
}
