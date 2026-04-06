import React from 'react'
import type { ResourceType } from '../../types'
import { RESOURCE_LABELS } from '../../types'
import styles from './ResourceHand.module.css'

interface ResourceHandProps {
  resources: Record<ResourceType, number>
}

const RESOURCE_ORDER: ResourceType[] = ['wood', 'brick', 'wheat', 'sheep', 'ore']

const RESOURCE_COLORS: Record<ResourceType, string> = {
  wood: '#2d6a4f',
  brick: '#b85c38',
  wheat: '#c9a227',
  sheep: '#52b788',
  ore: '#6c757d',
}

const RESOURCE_NAMES: Record<ResourceType, string> = {
  wood: 'Wood',
  brick: 'Brick',
  wheat: 'Wheat',
  sheep: 'Sheep',
  ore: 'Ore',
}

export function ResourceHand({ resources }: ResourceHandProps) {
  const total = RESOURCE_ORDER.reduce((sum, r) => sum + (resources[r] ?? 0), 0)

  return (
    <div className={styles.hand}>
      <div className={styles.header}>
        <span className={styles.label}>Resources</span>
        <span className={styles.total}>{total} cards</span>
      </div>
      <div className={styles.cards}>
        {RESOURCE_ORDER.map(res => {
          const count = resources[res] ?? 0
          return (
            <div
              key={res}
              className={`${styles.card} ${count === 0 ? styles.empty : ''}`}
              style={{ '--res-color': RESOURCE_COLORS[res] } as React.CSSProperties}
            >
              <span className={styles.emoji}>{RESOURCE_LABELS[res]}</span>
              <span className={styles.count}>{count}</span>
              <span className={styles.name}>{RESOURCE_NAMES[res]}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
