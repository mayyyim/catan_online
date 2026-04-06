import type { Player } from '../../types'
import styles from './PlayerAvatar.module.css'

interface PlayerAvatarProps {
  player: Player
  isMe?: boolean
  isCurrent?: boolean
  compact?: boolean
}

function initials(name: string): string {
  return name
    .split(' ')
    .map(w => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

export function PlayerAvatar({
  player,
  isMe,
  isCurrent,
  compact,
}: PlayerAvatarProps) {
  return (
    <div
      className={[
        styles.wrapper,
        isCurrent ? styles.current : '',
        compact ? styles.compact : '',
        !player.connected ? styles.disconnected : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div
        className={styles.avatar}
        style={{ backgroundColor: player.color }}
        title={player.name}
      >
        <span className={styles.initials}>{initials(player.name)}</span>
      </div>
      {!compact && (
        <div className={styles.info}>
          <span className={styles.name}>
            {player.name}
            {isMe && <span className={styles.meTag}> (you)</span>}
            {player.isHost && <span className={styles.hostTag}> 👑</span>}
          </span>
          {!player.connected && (
            <span className={styles.offlineTag}>offline</span>
          )}
        </div>
      )}
    </div>
  )
}
