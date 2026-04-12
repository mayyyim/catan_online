import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { fetchProfile, fetchMyStats, type PlayerProfile } from '../api'
import { useAuth } from '../context/AuthContext'
import styles from './Profile.module.css'

export default function Profile() {
  const { t } = useTranslation()
  const { userId } = useParams<{ userId: string }>()
  const { user, token } = useAuth()
  const [profile, setProfile] = useState<PlayerProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const isMe = !userId || userId === user?.user_id

  useEffect(() => {
    setLoading(true)
    setError('')

    const promise = isMe && token
      ? fetchMyStats(token)
      : userId
        ? fetchProfile(userId)
        : Promise.reject(new Error('Not logged in'))

    promise
      .then(setProfile)
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [userId, isMe, token])

  const formatDate = (iso: string | null) => {
    if (!iso) return ''
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className={styles.page}>
      <div className={styles.hexBg} aria-hidden />
      <main className={styles.main}>
        <Link to="/" className={styles.backLink}>
          &larr; {t('profile.backToHome')}
        </Link>

        {error && <p className={styles.error}>{error}</p>}

        {loading ? (
          <p className={styles.loading}>{t('profile.loading')}</p>
        ) : profile ? (
          <>
            <div className={styles.header}>
              <h1 className={styles.displayName}>{profile.display_name}</h1>
              <span className={styles.eloBadge}>{profile.elo_rating} {t('home.elo')}</span>
            </div>

            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <span className={styles.statValue}>{profile.games_played}</span>
                <span className={styles.statLabel}>{t('profile.stats.games')}</span>
              </div>
              <div className={styles.statCard}>
                <span className={`${styles.statValue} ${styles.green}`}>{profile.games_won}</span>
                <span className={styles.statLabel}>{t('profile.stats.wins')}</span>
              </div>
              <div className={styles.statCard}>
                <span className={`${styles.statValue} ${styles.gold}`}>{profile.win_rate}%</span>
                <span className={styles.statLabel}>{t('profile.stats.winRate')}</span>
              </div>
              <div className={styles.statCard}>
                <span className={`${styles.statValue} ${styles.blue}`}>{profile.avg_vp}</span>
                <span className={styles.statLabel}>{t('profile.stats.avgVp')}</span>
              </div>
            </div>

            <h2 className={styles.sectionTitle}>{t('profile.recentGames')}</h2>

            {profile.recent_games.length === 0 ? (
              <p className={styles.noGames}>{t('profile.noGames')}</p>
            ) : (
              <div className={styles.gamesList}>
                {profile.recent_games.map(g => (
                  <div key={g.id} className={styles.gameCard}>
                    <span className={`${styles.gameResult} ${g.won ? styles.won : styles.lost}`}>
                      {g.won ? t('profile.result.won') : t('profile.result.lost')}
                    </span>
                    <div className={styles.gameDetails}>
                      <span className={styles.gameMap}>{g.map_id}</span>
                      <span className={styles.gameMeta}>
                        {t('profile.meta', { count: g.player_count, turns: g.turns })} &middot; {formatDate(g.finished_at)}
                      </span>
                      <div className={styles.gamePlayers}>
                        {g.players.map(p => (
                          <span
                            key={p.player_id}
                            className={`${styles.playerTag} ${
                              g.won && p.user_id === profile.user_id ? styles.winner : ''
                            }`}
                          >
                            {p.name} ({p.victory_points}VP)
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : null}
      </main>
    </div>
  )
}
