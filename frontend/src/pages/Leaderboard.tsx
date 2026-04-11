import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchLeaderboard, type LeaderboardEntry } from '../api'
import styles from './Leaderboard.module.css'

export default function Leaderboard() {
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
          &larr; Back to Home
        </Link>

        <h1 className={styles.title}>Leaderboard</h1>
        <p className={styles.subtitle}>Top players by ELO rating (min. 3 games)</p>

        {error && <p className={styles.error}>{error}</p>}

        {loading ? (
          <p className={styles.loading}>Loading rankings...</p>
        ) : entries.length === 0 ? (
          <div className={styles.table}>
            <p className={styles.empty}>No ranked players yet. Play 3+ games to qualify!</p>
          </div>
        ) : (
          <div className={styles.table}>
            <div className={styles.headerRow}>
              <span>#</span>
              <span>Player</span>
              <span style={{ textAlign: 'right' }}>ELO</span>
              <span style={{ textAlign: 'right' }}>Wins</span>
              <span className={styles.headerCol5} style={{ textAlign: 'right' }}>Win %</span>
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
                  <span className={styles.playerGames}>{e.games_played} games</span>
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
