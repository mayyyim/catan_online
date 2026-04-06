import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getRoomState, addBot } from '../api'
import { useRoom } from '../context/RoomContext'
import { gameSocket } from '../ws/gameSocket'
import { MapThumbnail } from '../components/MapThumbnail'
import { PlayerAvatar } from '../components/PlayerAvatar'
import { MAP_CONFIGS } from '../maps/definitions'
import styles from './Room.module.css'

export default function Room() {
  const { roomId } = useParams<{ roomId: string }>()
  const navigate = useNavigate()
  const { room, myPlayerId, setRoom, setMyPlayerId, updatePlayer, removePlayer } =
    useRoom()

  const [seed, setSeed] = useState('')
  const [copied, setCopied] = useState(false)
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected' | 'error'>('disconnected')

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
      // Backend sends "room_update" with { players, map, state }
      if ((msg as any).type === 'room_update') {
        const m = msg as any
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

        // Keep invite code from existing room/session (WS payload doesn't include it)
        const inviteCode =
          room?.inviteCode ||
          sessionStorage.getItem('invite_code') ||
          ''

        setRoom({
          roomId: roomId,
          inviteCode,
          hostId: players[0]?.id ?? room?.hostId ?? '',
          players,
          selectedMapId: m.data?.selected_map_id ?? room?.selectedMapId ?? 'random',
          randomSeed: m.data?.seed ?? room?.randomSeed ?? '',
          maxPlayers: room?.maxPlayers ?? 4,
          status: m.data?.state === 'waiting' ? 'waiting' : 'started',
        })
      }

      if (msg.type === 'game_state' && (msg as any).data?.phase !== 'waiting') {
        navigate(`/game/${roomId}`)
      }
    })

    return () => {
      unsubStatus()
      unsubMsg()
      gameSocket.disconnect()
    }
  }, [roomId, myPlayerId, navigate, setRoom, updatePlayer, removePlayer, room])

  const handleMapSelect = useCallback(
    (mapId: string) => {
      // Optimistic UI: highlight immediately, then persist server-side so refresh/other players see it.
      if (room) {
        setRoom({
          ...room,
          selectedMapId: mapId,
          randomSeed: seed || room.randomSeed,
        })
      }
      gameSocket.send({ type: 'select_map', mapId, seed: seed || undefined })
    },
    [seed, room, setRoom],
  )

  const handleStartGame = useCallback(() => {
    // Backend accepts mapId/map_id + seed
    gameSocket.send({
      type: 'start_game',
      map_id: room?.selectedMapId,
      seed: seed || room?.randomSeed || undefined,
    } as any)
  }, [room?.randomSeed, room?.selectedMapId, seed])

  const handleAddBot = useCallback(async () => {
    if (!roomId) return
    try {
      await addBot(roomId, `Bot ${Math.max(1, (room?.players?.length ?? 1))}`)
    } catch (e) {
      // Room will update via WS when successful; show minimal error if not.
      console.error(e)
    }
  }, [roomId, room?.players?.length])

  const handleCopyInvite = useCallback(async () => {
    const link = `${window.location.origin}/room/${roomId}?code=${room?.inviteCode ?? ''}`
    await navigator.clipboard.writeText(link)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [roomId, room?.inviteCode])

  const isHost = room?.hostId === myPlayerId

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
      {/* Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <span className={styles.roomCode}>
            Room: <strong>{room.inviteCode}</strong>
          </span>
          <span
            className={`${styles.wsIndicator} ${styles[wsStatus]}`}
            title={wsStatus}
          />
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
              <MapThumbnail
                key={map.id}
                map={map}
                selected={room.selectedMapId === map.id}
                onClick={() => isHost && handleMapSelect(map.id)}
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
                <PlayerAvatar
                  key={player.id}
                  player={player}
                  isMe={player.id === myPlayerId}
                  compact={false}
                />
              ))}
              {Array.from({
                length: room.maxPlayers - room.players.length,
              }).map((_, i) => (
                <div key={`empty-${i}`} className={styles.emptySlot}>
                  Waiting for player...
                </div>
              ))}
            </div>

            <button
              className={styles.inviteBtn}
              onClick={handleCopyInvite}
              type="button"
            >
              {copied ? 'Copied!' : 'Copy Invite Link'}
            </button>
          </div>

          {isHost && (
            <>
              <button
                className={styles.inviteBtn}
                onClick={handleAddBot}
                disabled={room.players.length >= room.maxPlayers}
                type="button"
              >
                Add Bot
              </button>

              <button
                className={styles.startBtn}
                onClick={handleStartGame}
                disabled={room.players.length < 2}
                type="button"
              >
                Start Game
                {room.players.length < 2 && (
                  <span className={styles.startHint}>
                    (need at least 2 players)
                  </span>
                )}
              </button>
            </>
          )}

          {!isHost && (
            <p className={styles.waitingText}>
              Waiting for host to start the game...
            </p>
          )}
        </section>
      </div>
    </div>
  )
}
