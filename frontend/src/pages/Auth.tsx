import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, Link } from 'react-router-dom'
import { authLogin, authRegister, authGuest } from '../api'
import { useAuth } from '../context/AuthContext'
import styles from './Auth.module.css'

type Tab = 'login' | 'register' | 'guest'

export default function Auth() {
  const { t } = useTranslation()
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
      setError(err instanceof Error ? err.message : t('auth.loginFailed'))
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
      setError(err instanceof Error ? err.message : t('auth.registerFailed'))
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
      setError(err instanceof Error ? err.message : t('auth.guestFailed'))
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

        <h1 className={styles.title}>{t('home.title')}</h1>
        <p className={styles.subtitle}>{t('home.subtitle')}</p>

        <div className={styles.tabs}>
          <button
            className={`${styles.tab} ${tab === 'login' ? styles.tabActive : ''}`}
            onClick={() => { setTab('login'); setError('') }}
            type="button"
          >
            {t('auth.login')}
          </button>
          <button
            className={`${styles.tab} ${tab === 'register' ? styles.tabActive : ''}`}
            onClick={() => { setTab('register'); setError('') }}
            type="button"
          >
            {t('auth.register')}
          </button>
          <button
            className={`${styles.tab} ${tab === 'guest' ? styles.tabActive : ''}`}
            onClick={() => { setTab('guest'); setError('') }}
            type="button"
          >
            {t('auth.guest')}
          </button>
        </div>

        {tab === 'login' && (
          <form className={styles.card} onSubmit={handleLogin}>
            <label className={styles.label} htmlFor="login-username">{t('auth.username')}</label>
            <input
              id="login-username"
              className={styles.input}
              type="text"
              placeholder={t('auth.usernameInputPlaceholder')}
              value={username}
              onChange={e => setUsername(e.target.value)}
              maxLength={30}
              autoFocus
              autoComplete="username"
            />
            <label className={styles.label} htmlFor="login-password">{t('auth.password')}</label>
            <input
              id="login-password"
              className={styles.input}
              type="password"
              placeholder={t('auth.passwordInputPlaceholder')}
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
              {loading ? t('auth.loggingIn') : t('auth.loginBtn')}
            </button>
          </form>
        )}

        {tab === 'register' && (
          <form className={styles.card} onSubmit={handleRegister}>
            <label className={styles.label} htmlFor="reg-username">{t('auth.username')}</label>
            <input
              id="reg-username"
              className={styles.input}
              type="text"
              placeholder={t('auth.chooseUsername')}
              value={username}
              onChange={e => setUsername(e.target.value)}
              maxLength={30}
              autoFocus
              autoComplete="username"
            />
            <label className={styles.label} htmlFor="reg-display">{t('auth.displayName')}</label>
            <input
              id="reg-display"
              className={styles.input}
              type="text"
              placeholder={t('auth.displayNamePlaceholder')}
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              maxLength={20}
            />
            <label className={styles.label} htmlFor="reg-password">{t('auth.password')}</label>
            <input
              id="reg-password"
              className={styles.input}
              type="password"
              placeholder={t('auth.choosePassword')}
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
              {loading ? t('auth.registering') : t('auth.registerBtn')}
            </button>
          </form>
        )}

        {tab === 'guest' && (
          <div className={styles.card}>
            <p className={styles.guestDescription}>
              {t('auth.guestDescription')}
            </p>
            {error && <p className={styles.error}>{error}</p>}
            <button
              type="button"
              className={styles.primaryBtn}
              disabled={loading}
              onClick={handleGuest}
            >
              {loading ? t('auth.loadingGuest') : t('auth.guestBtn')}
            </button>
          </div>
        )}

        <div className={styles.divider}><span>{t('auth.or')}</span></div>

        <Link to="/" className={styles.backLink}>
          {t('auth.continueWithoutAccount')}
        </Link>
      </main>

      <footer className={styles.footer}>
        <span>{t('home.footer')}</span>
      </footer>
    </div>
  )
}
