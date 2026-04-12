import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { createRoom, joinRoom } from '../api'
import { useRoom } from '../context/RoomContext'
import { useAuth } from '../context/AuthContext'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import styles from './Home.module.css'

type Mode = 'idle' | 'create' | 'join'

export default function Home() {
  const { t } = useTranslation()
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
      setError(err instanceof Error ? err.message : t('home.createFailed'))
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
      setError(err instanceof Error ? err.message : t('home.joinFailed'))
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

        <h1 className={styles.title}>{t('home.title')}</h1>
        <p className={styles.subtitle}>{t('home.subtitle')}</p>

        {user && (
          <div className={styles.userBar}>
            <span className={styles.userName}>{user.display_name}</span>
            <span className={styles.userElo}>{user.elo_rating} {t('home.elo')}</span>
            <button type="button" className={styles.ghostBtn} onClick={logout}>
              {t('home.logout')}
            </button>
          </div>
        )}

        {mode === 'idle' && (
          <div className={styles.actions}>
            <button
              className={styles.primaryBtn}
              onClick={() => setMode('create')}
            >
              {t('home.createRoom')}
            </button>
            <button
              className={styles.secondaryBtn}
              onClick={() => setMode('join')}
            >
              {t('home.joinRoom')}
            </button>
            <Link to="/maps" className={styles.mapGalleryLink}>
              {t('home.mapGallery')}
            </Link>
            <Link to="/leaderboard" className={styles.mapGalleryLink}>
              {t('home.leaderboard')}
            </Link>
            {user && (
              <Link to="/profile" className={styles.mapGalleryLink}>
                {t('home.myStats')}
              </Link>
            )}
            {!user && (
              <Link to="/auth" className={styles.mapGalleryLink}>
                {t('home.loginRegister')}
              </Link>
            )}
            <LanguageSwitcher />
          </div>
        )}

        {mode === 'create' && (
          <form className={styles.form} onSubmit={handleCreate}>
            <h2 className={styles.formTitle}>{t('home.createFormTitle')}</h2>
            <label className={styles.label} htmlFor="create-name">
              {t('home.yourName')}
            </label>
            <input
              id="create-name"
              className={styles.input}
              type="text"
              placeholder={t('home.namePlaceholder')}
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
                {t('common.back')}
              </button>
              <button
                type="submit"
                className={styles.primaryBtn}
                disabled={loading || !playerName.trim()}
              >
                {loading ? t('home.creating') : t('home.createRoom')}
              </button>
            </div>
          </form>
        )}

        {mode === 'join' && (
          <form className={styles.form} onSubmit={handleJoin}>
            <h2 className={styles.formTitle}>{t('home.joinFormTitle')}</h2>
            <label className={styles.label} htmlFor="join-code">
              {t('home.inviteCode')}
            </label>
            <input
              id="join-code"
              className={styles.input}
              type="text"
              placeholder={t('home.inviteCodePlaceholder')}
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value.toUpperCase())}
              maxLength={8}
              autoFocus
            />
            <label className={styles.label} htmlFor="join-name">
              {t('home.yourName')}
            </label>
            <input
              id="join-name"
              className={styles.input}
              type="text"
              placeholder={t('home.namePlaceholder')}
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
                {t('common.back')}
              </button>
              <button
                type="submit"
                className={styles.primaryBtn}
                disabled={loading || !playerName.trim() || !inviteCode.trim()}
              >
                {loading ? t('home.joining') : t('home.joinRoom')}
              </button>
            </div>
          </form>
        )}
      </main>

      <footer className={styles.footer}>
        <span>{t('home.footer')}</span>
      </footer>
    </div>
  )
}
