import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authLogin, authRegister, authGuest } from '../api'
import { useAuth } from '../context/AuthContext'
import styles from './Auth.module.css'

type Tab = 'login' | 'register' | 'guest'

export default function Auth() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [tab, setTab] = useState<Tab>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password) return
    setLoading(true)
    setError('')
    try {
      const user = await authLogin(username.trim(), password)
      login(user)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    if (!username.trim() || !password || !displayName.trim()) return
    setLoading(true)
    setError('')
    try {
      const user = await authRegister(username.trim(), password, displayName.trim())
      login(user)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGuest = async () => {
    setLoading(true)
    setError('')
    try {
      const user = await authGuest()
      login(user)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create guest account')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.page}>
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

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${tab === 'login' ? styles.tabActive : ''}`}
            onClick={() => { setTab('login'); setError('') }}
            type="button"
          >
            Login
          </button>
          <button
            className={`${styles.tab} ${tab === 'register' ? styles.tabActive : ''}`}
            onClick={() => { setTab('register'); setError('') }}
            type="button"
          >
            Register
          </button>
          <button
            className={`${styles.tab} ${tab === 'guest' ? styles.tabActive : ''}`}
            onClick={() => { setTab('guest'); setError('') }}
            type="button"
          >
            Guest
          </button>
        </div>

        {tab === 'login' && (
          <form className={styles.card} onSubmit={handleLogin}>
            <label className={styles.label} htmlFor="login-username">Username</label>
            <input
              id="login-username"
              className={styles.input}
              type="text"
              placeholder="Enter username..."
              value={username}
              onChange={e => setUsername(e.target.value)}
              maxLength={30}
              autoFocus
              autoComplete="username"
            />
            <label className={styles.label} htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className={styles.input}
              type="password"
              placeholder="Enter password..."
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
            />
            {error && <p className={styles.error}>{error}</p>}
            <button
              type="submit"
              className={styles.primaryBtn}
              disabled={loading || !username.trim() || !password}
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>
        )}

        {tab === 'register' && (
          <form className={styles.card} onSubmit={handleRegister}>
            <label className={styles.label} htmlFor="reg-username">Username</label>
            <input
              id="reg-username"
              className={styles.input}
              type="text"
              placeholder="Choose a username..."
              value={username}
              onChange={e => setUsername(e.target.value)}
              maxLength={30}
              autoFocus
              autoComplete="username"
            />
            <label className={styles.label} htmlFor="reg-display">Display Name</label>
            <input
              id="reg-display"
              className={styles.input}
              type="text"
              placeholder="How others see you..."
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              maxLength={20}
            />
            <label className={styles.label} htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              className={styles.input}
              type="password"
              placeholder="Choose a password..."
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="new-password"
            />
            {error && <p className={styles.error}>{error}</p>}
            <button
              type="submit"
              className={styles.primaryBtn}
              disabled={loading || !username.trim() || !password || !displayName.trim()}
            >
              {loading ? 'Creating account...' : 'Register'}
            </button>
          </form>
        )}

        {tab === 'guest' && (
          <div className={styles.card}>
            <p className={styles.guestDescription}>
              Play instantly without creating an account. Your stats will not be saved.
            </p>
            {error && <p className={styles.error}>{error}</p>}
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={loading}
              onClick={handleGuest}
            >
              {loading ? 'Creating guest...' : 'Play as Guest'}
            </button>
          </div>
        )}

        <div className={styles.divider}><span>or</span></div>

        <Link to="/" className={styles.backLink}>
          Continue without account
        </Link>
      </main>

      <footer className={styles.footer}>
        <span>Built with React + TypeScript</span>
      </footer>
    </div>
  )
}
