import styles from './DiceDisplay.module.css'

interface DiceDisplayProps {
  dice?: [number, number]
  rolling?: boolean
}

/**
 * Dot position maps for each dice face (1-6).
 * Grid is 3x3, positions: tl tc tr | ml mc mr | bl bc br
 */
const DOT_PATTERNS: Record<number, string[]> = {
  1: ['mc'],
  2: ['tr', 'bl'],
  3: ['tr', 'mc', 'bl'],
  4: ['tl', 'tr', 'bl', 'br'],
  5: ['tl', 'tr', 'mc', 'bl', 'br'],
  6: ['tl', 'ml', 'bl', 'tr', 'mr', 'br'],
}

function DieFace({ value }: { value: number }) {
  const dots = DOT_PATTERNS[value] ?? []
  return (
    <div className={styles.faceGrid}>
      {['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br'].map((pos) => (
        <span
          key={pos}
          className={`${styles.dotSlot} ${dots.includes(pos) ? styles.dotVisible : ''}`}
        />
      ))}
    </div>
  )
}

export function DiceDisplay({ dice, rolling }: DiceDisplayProps) {
  if (!dice && !rolling) return null

  const [d1, d2] = dice ?? [1, 1]
  const total = d1 + d2

  return (
    <div className={styles.wrapper}>
      <div className={styles.diceRow}>
        <div
          className={`${styles.die} ${rolling ? styles.rolling : ''}`}
          aria-label={`Die 1: ${d1}`}
        >
          <DieFace value={d1} />
        </div>
        <div
          className={`${styles.die} ${rolling ? styles.rolling : ''}`}
          aria-label={`Die 2: ${d2}`}
          style={{ animationDelay: rolling ? '0.05s' : undefined }}
        >
          <DieFace value={d2} />
        </div>
      </div>
      {!rolling && dice && (
        <span
          className={`${styles.total} ${total === 7 ? styles.seven : ''}`}
        >
          = {total}
        </span>
      )}
    </div>
  )
}
