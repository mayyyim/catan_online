import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { fetchLeaderboard, type LeaderboardEntry } from '../api'
import styles from './Leaderboard.module.css'

export default function Leaderboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchLeaderboard(50)
      .then(data => setEntries(data.leaderboard))
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className={styles.page}>
      <div className={styles.hexBg} aria-hidden />
      <main className={styles.main}>
        <Link to="/" className={styles.backLink}>
          &larr; {t('leaderboard.backToHome')}
        </Link>

        <h1 className={styles.title}>{t('leaderboard.title')}</h1>
        <p className={styles.subtitle}>{t('leaderboard.subtitle')}</p>

        {error && <p className={styles.error}>{error}</p>}

        {loading ? (
          <p className={styles.loading}>{t('leaderboard.loading')}</p>
        ) : entries.length === 0 ? (
          <div className={styles.table}>
            <p className={styles.empty}>{t('leaderboard.empty')}</p>
          </div>
        ) : (
          <div className={styles.table}>
            <div className={styles.headerRow}>
              <span>{t('leaderboard.rank')}</span>
              <span>{t('leaderboard.player')}</span>
              <span style={{ textAlign: 'right' }}>{t('leaderboard.elo')}</span>
              <span style={{ textAlign: 'right' }}>{t('leaderboard.wins')}</span>
              <span className={styles.headerCol5} style={{ textAlign: 'right' }}>{t('leaderboard.winRate')}</span>
            </div>
            {entries.map(e => (
              <div
                key={e.user_id}
                className={styles.row}
                onClick={() => navigate(`/profile/${e.user_id}`)}
              >
                <span
                  className={`${styles.rank} ${
                    e.rank === 1 ? styles.rank1 : e.rank === 2 ? styles.rank2 : e.rank === 3 ? styles.rank3 : ''
                  }`}
                >
                  {e.rank}
                </span>
                <div className={styles.playerInfo}>
                  <span className={styles.playerName}>{e.display_name}</span>
                  <span className={styles.playerGames}>{e.games_played} {t('leaderboard.games')}</span>
                </div>
                <span className={styles.elo}>{e.elo_rating}</span>
                <span className={styles.wins}>{e.games_won}</span>
                <span className={styles.winRate}>{e.win_rate}%</span>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
