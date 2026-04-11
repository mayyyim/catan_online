import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { createRoom, joinRoom } from '../api'
import { useRoom } from '../context/RoomContext'
import { useAuth } from '../context/AuthContext'
import styles from './Home.module.css'

type Mode = 'idle' | 'create' | 'join'

export default function Home() {
  const navigate = useNavigate()
  const { setMyPlayerId } = useRoom()
  const { user, logout } = useAuth()

  const [mode, setMode] = useState<Mode>('idle')
  const [playerName, setPlayerName] = useState(user?.display_name ?? '')
  const [inviteCode, setInviteCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async (e: FormEvent) => {
    e.preventDefault()
    if (!playerName.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await createRoom(playerName.trim())
      setMyPlayerId(res.host_player_id)
      // Store player_id in sessionStorage so it survives page navigation
      sessionStorage.setItem('player_id', res.host_player_id)
      sessionStorage.setItem('player_name', playerName.trim())
      sessionStorage.setItem('invite_code', res.invite_code)
      navigate(`/room/${res.room_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create room')
    } finally {
      setLoading(false)
    }
  }

  const handleJoin = async (e: FormEvent) => {
    e.preventDefault()
    if (!playerName.trim() || !inviteCode.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await joinRoom(inviteCode.trim().toUpperCase(), playerName.trim())
      setMyPlayerId(res.player_id)
      sessionStorage.setItem('player_id', res.player_id)
      sessionStorage.setItem('player_name', playerName.trim())
      sessionStorage.setItem('invite_code', inviteCode.trim().toUpperCase())
      navigate(`/room/${res.room_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to join room')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
      {/* Decorative hex background */}
      <div className={styles.hexBg} aria-hidden />

      <main className={styles.main}>
        <div className={styles.logo}>
          <svg width="60" height="52" viewBox="0 0 60 52" fill="none">
            <polygon
              points="30,2 56,16 56,44 30,58 4,44 4,16"
              fill="#ffd60a"
              stroke="#f0a500"
              strokeWidth="2"
            />
            <text x="30" y="35" textAnchor="middle" fontSize="22" fill="#1a1a2e" fontWeight="bold">
              C
            </text>
          </svg>
        </div>

        <h1 className={styles.title}>Catan Online</h1>
        <p className={styles.subtitle}>Trade, Build, Settle</p>

        {user && (
          <div className={styles.userBar}>
            <span className={styles.userName}>{user.display_name}</span>
            <span className={styles.userElo}>{user.elo_rating} ELO</span>
            <button type="button" className={styles.ghostBtn} onClick={logout}>
              Logout
            </button>
          </div>
        )}

        {mode === 'idle' && (
          <div className={styles.actions}>
            <button
              className={styles.primaryBtn}
              onClick={() => setMode('create')}
            >
              Create Room
            </button>
            <button
              className={styles.secondaryBtn}
              onClick={() => setMode('join')}
            >
              Join Room
            </button>
            <Link to="/maps" className={styles.mapGalleryLink}>
              Map Gallery
            </Link>
            {!user && (
              <Link to="/auth" className={styles.mapGalleryLink}>
                Login / Register
              </Link>
            )}
          </div>
        )}

        {mode === 'create' && (
          <form className={styles.form} onSubmit={handleCreate}>
            <h2 className={styles.formTitle}>Create a Room</h2>
            <label className={styles.label} htmlFor="create-name">
              Your Name
            </label>
            <input
              id="create-name"
              className={styles.input}
              type="text"
              placeholder="Enter your name..."
              value={playerName}
              onChange={e => setPlayerName(e.target.value)}
              maxLength={20}
              autoFocus
            />
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.formActions}>
              <button
                type="button"
                className={styles.ghostBtn}
                onClick={() => { setMode('idle'); setError('') }}
              >
                Back
              </button>
              <button
                type="submit"
                className={styles.primaryBtn}
                disabled={loading || !playerName.trim()}
              >
                {loading ? 'Creating...' : 'Create Room'}
              </button>
            </div>
          </form>
        )}

        {mode === 'join' && (
          <form className={styles.form} onSubmit={handleJoin}>
            <h2 className={styles.formTitle}>Join a Room</h2>
            <label className={styles.label} htmlFor="join-code">
              Invite Code
            </label>
            <input
              id="join-code"
              className={styles.input}
              type="text"
              placeholder="e.g. ABCD12"
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value.toUpperCase())}
              maxLength={8}
              autoFocus
            />
            <label className={styles.label} htmlFor="join-name">
              Your Name
            </label>
            <input
              id="join-name"
              className={styles.input}
              type="text"
              placeholder="Enter your name..."
              value={playerName}
              onChange={e => setPlayerName(e.target.value)}
              maxLength={20}
            />
            {error && <p className={styles.error}>{error}</p>}
            <div className={styles.formActions}>
              <button
                type="button"
                className={styles.ghostBtn}
                onClick={() => { setMode('idle'); setError('') }}
              >
                Back
              </button>
              <button
                type="submit"
                className={styles.primaryBtn}
                disabled={loading || !playerName.trim() || !inviteCode.trim()}
              >
                {loading ? 'Joining...' : 'Join Room'}
              </button>
            </div>
          </form>
        )}
      </main>

      <footer className={styles.footer}>
        <span>Built with React + TypeScript</span>
      </footer>
    </div>
  )
}
