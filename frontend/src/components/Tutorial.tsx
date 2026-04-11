import { useState, useCallback, useEffect } from 'react'
import styles from './Tutorial.module.css'

const STORAGE_KEY = 'catan_tutorial_done'

const STEPS = [
  {
    title: 'Welcome to Catan Online!',
    content: 'Build settlements, roads, and cities to reach 10 victory points.',
  },
  {
    title: '\uD83C\uDFE0 Setup Phase',
    content:
      'Each player places 2 settlements and 2 roads in snake draft order.\nClick on the map to place your pieces when it\'s your turn.\nYour 2nd settlement gives you starting resources!',
  },
  {
    title: '\uD83C\uDFB2 Your Turn',
    content:
      '1. Roll the dice \u2192 resources are produced from matching tiles\n2. Trade with the bank (4:1) or other players\n3. Build roads, settlements, cities, or buy dev cards\n4. End your turn',
  },
  {
    title: '\uD83C\uDFD7\uFE0F Building',
    content:
      'Road: \uD83C\uDF32 + \uD83E\uDDF1\nSettlement: \uD83C\uDF32 + \uD83E\uDDF1 + \uD83C\uDF3E + \uD83D\uDC11 (1 VP)\nCity: \uD83C\uDF3E\uD83C\uDF3E + \u26CF\uFE0F\u26CF\uFE0F\u26CF\uFE0F (2 VP, replaces settlement)\nDev Card: \uD83C\uDF3E + \uD83D\uDC11 + \u26CF\uFE0F',
  },
  {
    title: '\uD83C\uDFC6 How to Win',
    content:
      'Reach 10 Victory Points!\n\u2022 Each settlement = 1 VP\n\u2022 Each city = 2 VP\n\u2022 Longest Road (5+) = 2 VP\n\u2022 Largest Army (3+ knights) = 2 VP\n\u2022 VP development cards',
  },
]

interface TutorialProps {
  visible: boolean
  onClose: () => void
}

export function Tutorial({ visible, onClose }: TutorialProps) {
  const [step, setStep] = useState(0)
  const [animating, setAnimating] = useState(false)

  useEffect(() => {
    if (visible) setStep(0)
  }, [visible])

  const dismiss = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, 'true')
    onClose()
  }, [onClose])

  const next = useCallback(() => {
    if (step >= STEPS.length - 1) {
      dismiss()
      return
    }
    setAnimating(true)
    setTimeout(() => {
      setStep(s => s + 1)
      setAnimating(false)
    }, 200)
  }, [step, dismiss])

  if (!visible) return null

  const current = STEPS[step]
  const isLast = step === STEPS.length - 1

  return (
    <div className={styles.overlay} onClick={dismiss} role="dialog" aria-modal="true" aria-label="Game tutorial">
      <div
        className={`${styles.card} ${animating ? styles.fadeOut : styles.fadeIn}`}
        onClick={e => e.stopPropagation()}
      >
        <button className={styles.skipBtn} onClick={dismiss} type="button" aria-label="Skip tutorial">
          Skip
        </button>

        <h2 className={styles.title}>{current.title}</h2>
        <div className={styles.content}>
          {current.content.split('\n').map((line, i) => (
            <p key={i} className={styles.line}>{line}</p>
          ))}
        </div>

        <div className={styles.dots} aria-label={`Step ${step + 1} of ${STEPS.length}`}>
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`${styles.dot} ${i === step ? styles.dotActive : ''}`}
              aria-hidden="true"
            />
          ))}
        </div>

        <button className={styles.nextBtn} onClick={next} type="button">
          {isLast ? 'Got it!' : 'Next \u2192'}
        </button>
      </div>
    </div>
  )
}

export function shouldShowTutorial(): boolean {
  return localStorage.getItem(STORAGE_KEY) !== 'true'
}
