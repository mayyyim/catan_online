import styles from './DiceDisplay.module.css'

interface DiceDisplayProps {
  dice?: [number, number]
  rolling?: boolean
}

const DICE_FACES = ['', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']

export function DiceDisplay({ dice, rolling }: DiceDisplayProps) {
  if (!dice && !rolling) return null

  const [d1, d2] = dice ?? [0, 0]
  const total = d1 + d2

  return (
    <div className={`${styles.wrapper} ${rolling ? styles.rolling : ''}`}>
      <span className={styles.die} aria-label={`Die 1: ${d1}`}>
        {rolling ? '🎲' : DICE_FACES[d1] ?? d1}
      </span>
      <span className={styles.die} aria-label={`Die 2: ${d2}`}>
        {rolling ? '🎲' : DICE_FACES[d2] ?? d2}
      </span>
      {!rolling && dice && (
        <span
          className={`${styles.total} ${
            total === 7 ? styles.seven : ''
          }`}
        >
          = {total}
        </span>
      )}
    </div>
  )
}
