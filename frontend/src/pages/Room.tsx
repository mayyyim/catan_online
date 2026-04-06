import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getRoomState } from '../api'
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
      if (msg.type === 'room_state') setRoom(msg.state)
      if (msg.type === 'player_joined') updatePlayer(msg.player)
      if (msg.type === 'player_left') removePlayer(msg.playerId)
      if (msg.type === 'game_state' && msg.state.phase !== 'waiting') {
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
      gameSocket.send({ type: 'select_map', mapId, seed: seed || undefined })
    },
    [seed],
  )

  const handleStartGame = useCallback(() => {
    gameSocket.send({ type: 'start_game' })
  }, [])

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
