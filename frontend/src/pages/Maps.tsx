import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { MAP_CONFIGS } from '../maps/definitions'
import { TERRAIN_COLORS } from '../types'
import type { MapConfig, TerrainType } from '../types'
import styles from './Maps.module.css'

// ─── Resource filter options ──────────────────────────────────────────────────

type Filter = 'all' | 'wood' | 'brick' | 'wheat' | 'sheep' | 'ore' | 'large'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all',   label: 'All Maps' },
  { id: 'large', label: '🗺 Large' },
  { id: 'wood',  label: '🌲 Wood' },
  { id: 'brick', label: '🧱 Brick' },
  { id: 'wheat', label: '🌾 Wheat' },
  { id: 'sheep', label: '🐑 Sheep' },
  { id: 'ore',   label: '⛰ Ore' },
]

function matchesFilter(map: MapConfig, filter: Filter): boolean {
  if (filter === 'all') return map.id !== 'random'
  if (filter === 'large') return map.size === 'large'
  return map.tags?.some(t => t.toLowerCase().includes(filter)) ?? false
}

// ─── Thumbnail ────────────────────────────────────────────────────────────────

function PreviewGrid({ rows, cellSize = 13 }: { rows: TerrainType[][]; cellSize?: number }) {
  const gap = 2
  const maxCols = Math.max(...rows.map(r => r.length))
  const w = maxCols * (cellSize + gap)
  const h = rows.length * (cellSize + gap)
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className={styles.previewSvg}>
      {rows.map((row, ri) =>
        row.map((terrain, ci) => (
          <rect
            key={`${ri}-${ci}`}
            x={ci * (cellSize + gap)}
            y={ri * (cellSize + gap)}
            width={cellSize}
            height={cellSize}
            rx={2}
            fill={TERRAIN_COLORS[terrain]}
            opacity={0.9}
          />
        )),
      )}
    </svg>
  )
}

// ─── Resource distribution bar ────────────────────────────────────────────────

const TERRAIN_TO_RESOURCE: Record<TerrainType, string | null> = {
  forest:    'Wood',
  hills:     'Brick',
  fields:    'Wheat',
  pasture:   'Sheep',
  mountains: 'Ore',
  desert:    null,
  ocean:     null,
}

const RESOURCE_COLOR: Record<string, string> = {
  Wood:  '#2d6a4f',
  Brick: '#b85c38',
  Wheat: '#ffd60a',
  Sheep: '#74c69d',
  Ore:   '#6c757d',
}

function ResourceBars({ preview }: { preview: TerrainType[][] }) {
  const counts: Record<string, number> = { Wood: 0, Brick: 0, Wheat: 0, Sheep: 0, Ore: 0 }
  preview.flat().forEach(t => {
    const r = TERRAIN_TO_RESOURCE[t]
    if (r) counts[r]++
  })
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (total === 0) return null
  return (
    <div className={styles.resBars}>
      {Object.entries(counts)
        .filter(([, v]) => v > 0)
        .sort(([, a], [, b]) => b - a)
        .map(([res, cnt]) => (
          <div key={res} className={styles.resRow}>
            <span className={styles.resLabel}>{res}</span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ width: `${(cnt / total) * 100}%`, background: RESOURCE_COLOR[res] }}
              />
            </div>
            <span className={styles.resCount}>{cnt}</span>
          </div>
        ))}
    </div>
  )
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function DetailPanel({ map, onClose }: { map: MapConfig; onClose: () => void }) {
  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close">×</button>

        <div className={styles.panelHeader}>
          <h2 className={styles.panelName}>{map.name}</h2>
          {map.size === 'large' && (
            <span className={styles.sizeBadge}>Large</span>
          )}
        </div>

        <p className={styles.panelDesc}>{map.description}</p>

        <div className={styles.panelPreviewWrap}>
          <PreviewGrid rows={map.preview} cellSize={map.size === 'large' ? 10 : 16} />
        </div>

        {map.tags && map.tags.length > 0 && (
          <div className={styles.tagRow}>
            {map.tags.map(t => (
              <span key={t} className={styles.tag}>{t}</span>
            ))}
          </div>
        )}

        <div className={styles.divider} />

        <h3 className={styles.sectionTitle}>Resource Distribution</h3>
        <ResourceBars preview={map.preview} />
      </div>
    </div>
  )
}

// ─── Map card ─────────────────────────────────────────────────────────────────

function MapCard({ map, onClick }: { map: MapConfig; onClick: () => void }) {
  return (
    <button className={styles.card} onClick={onClick} type="button">
      <div className={styles.cardPreview}>
        <PreviewGrid rows={map.preview} cellSize={map.size === 'large' ? 8 : 11} />
      </div>
      <div className={styles.cardBody}>
        <span className={styles.cardName}>{map.name}</span>
        <span className={styles.cardDesc}>{map.description}</span>
        {map.tags && (
          <div className={styles.cardTags}>
            {map.tags.slice(0, 3).map(t => (
              <span key={t} className={styles.cardTag}>{t}</span>
            ))}
          </div>
        )}
      </div>
    </button>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function Maps() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState<Filter>('all')
  const [detail, setDetail] = useState<MapConfig | null>(null)

  const filtered = useMemo(
    () => MAP_CONFIGS.filter(m => matchesFilter(m, filter)),
    [filter],
  )

  return (
    <div className={styles.page}>
      <div className={styles.hexBg} aria-hidden />

      <header className={styles.header}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>← Back</button>
        <div>
          <h1 className={styles.title}>Map Gallery</h1>
          <p className={styles.subtitle}>{MAP_CONFIGS.length - 1} maps available</p>
        </div>
      </header>

      <div className={styles.filters}>
        {FILTERS.map(f => (
          <button
            key={f.id}
            className={`${styles.filterBtn} ${filter === f.id ? styles.filterActive : ''}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p className={styles.empty}>No maps match this filter.</p>
      ) : (
        <div className={styles.grid}>
          {filtered.map(map => (
            <MapCard key={map.id} map={map} onClick={() => setDetail(map)} />
          ))}
        </div>
      )}

      {detail && <DetailPanel map={detail} onClose={() => setDetail(null)} />}
    </div>
  )
}
