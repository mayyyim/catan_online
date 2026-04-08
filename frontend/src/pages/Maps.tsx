import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { MAP_CONFIGS } from '../maps/definitions'
import { TERRAIN_COLORS, TERRAIN_LABELS, RESOURCE_LABELS } from '../types'
import type { MapConfig } from '../types'
import {
  fetchMapSummaries, fetchMapDetail,
  type MapSummary, type MapDetailData, type MapDetailPort,
} from '../api'
import { cubeToPixel, hexCorners, cornersToSvgPoints } from '../engine/hexMath'
import styles from './Maps.module.css'

// ─── Helpers ──────────────────────────────────────────────────────────────────

type Filter = 'all' | 'wood' | 'brick' | 'wheat' | 'sheep' | 'ore' | 'large'

const FILTERS: { id: Filter; label: string }[] = [
  { id: 'all',   label: 'All' },
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

// Convert axial (q,r) tiles into a centred SVG hex grid string
function buildHexSvg(
  tiles: { q: number; r: number; tile_type: string }[],
  hexSize: number,
) {
  if (!tiles.length) return { paths: [], viewBox: '0 0 1 1' }
  const pts = tiles.map(t => cubeToPixel(t.q, t.r, hexSize))
  const minX = Math.min(...pts.map(p => p.x)) - hexSize
  const minY = Math.min(...pts.map(p => p.y)) - hexSize * 0.9
  const maxX = Math.max(...pts.map(p => p.x)) + hexSize
  const maxY = Math.max(...pts.map(p => p.y)) + hexSize * 0.9
  const w = maxX - minX
  const h = maxY - minY
  const paths = tiles.map((t, i) => {
    const { x, y } = pts[i]
    const cx = x - minX
    const cy = y - minY
    return { cx, cy, tile_type: t.tile_type }
  })
  return { paths, viewBox: `0 0 ${w.toFixed(1)} ${h.toFixed(1)}`, w, h }
}

// Resource distribution from tile list
const TERRAIN_RESOURCE: Record<string, string> = {
  forest: 'Wood', hills: 'Brick', fields: 'Wheat',
  pasture: 'Sheep', mountains: 'Ore',
}
const RESOURCE_COLOR: Record<string, string> = {
  Wood: '#2d6a4f', Brick: '#b85c38', Wheat: '#d4aa00',
  Sheep: '#52b788', Ore: '#6c757d',
}

// Side direction vectors for flat-top hex (same as HexGrid.tsx)
const SQ3 = Math.sqrt(3)
const SIDE_DIRS: [number, number][] = [
  [1.5, SQ3 / 2], [1.5, -SQ3 / 2], [0, -SQ3],
  [-1.5, -SQ3 / 2], [-1.5, SQ3 / 2], [0, SQ3],
]

// ─── Small hex thumbnail (for cards) ─────────────────────────────────────────

function HexThumbnail({ summary, size = 12 }: { summary: MapSummary; size?: number }) {
  const { paths, viewBox, w, h } = useMemo(
    () => buildHexSvg(summary.tiles, size),
    [summary, size],
  )
  if (!paths.length) {
    return <div className={styles.thumbPlaceholder}>?</div>
  }
  return (
    <svg
      viewBox={viewBox}
      width={w}
      height={h}
      className={styles.thumbSvg}
      style={{ maxWidth: '100%', maxHeight: 120 }}
    >
      {paths.map(({ cx, cy, tile_type }, i) => {
        const corners = hexCorners(cx, cy, size)
        const points = cornersToSvgPoints(corners)
        const fill = TERRAIN_COLORS[tile_type as keyof typeof TERRAIN_COLORS] ?? '#444'
        return (
          <polygon
            key={i}
            points={points}
            fill={fill}
            stroke="#0d1b2a"
            strokeWidth={0.8}
          />
        )
      })}
    </svg>
  )
}

// ─── Full hex detail map (for panel) ─────────────────────────────────────────

function HexDetailMap({ data }: { data: MapDetailData }) {
  const hexSize = data.size === 'large' ? 20 : 28
  const { paths, viewBox, w, h } = useMemo(
    () => buildHexSvg(data.tiles, hexSize),
    [data, hexSize],
  )

  // Port positions
  const portMarkers = useMemo(() => {
    return data.ports.map((port, idx) => {
      const { x, y } = cubeToPixel(port.q, port.r, hexSize)
      const minX = Math.min(...data.tiles.map(t => cubeToPixel(t.q, t.r, hexSize).x)) - hexSize
      const minY = Math.min(...data.tiles.map(t => cubeToPixel(t.q, t.r, hexSize).y)) - hexSize * 0.9
      const cx = x - minX
      const cy = y - minY
      const [ddx, ddy] = SIDE_DIRS[port.side] ?? [0, 0]
      const px = cx + ddx * hexSize * 0.65
      const py = cy + ddy * hexSize * 0.65
      const label = port.resource ? RESOURCE_LABELS[port.resource as keyof typeof RESOURCE_LABELS] : '?'
      return { idx, px, py, label, ratio: port.ratio, resource: port.resource }
    })
  }, [data, hexSize])

  if (!paths.length) return null

  return (
    <svg
      viewBox={viewBox}
      width={w}
      height={h}
      className={styles.detailSvg}
      style={{ maxWidth: '100%', maxHeight: 340 }}
    >
      {/* Tiles */}
      {paths.map(({ cx, cy, tile_type }, i) => {
        const tile = data.tiles[i]
        const corners = hexCorners(cx, cy, hexSize)
        const points = cornersToSvgPoints(corners)
        const fill = TERRAIN_COLORS[tile_type as keyof typeof TERRAIN_COLORS] ?? '#444'
        const emoji = TERRAIN_LABELS[tile_type as keyof typeof TERRAIN_LABELS] ?? ''
        const isHighProbToken = tile.token === 6 || tile.token === 8
        const emojiSize = hexSize * 0.72
        const tokenY = cy + hexSize * 0.38

        return (
          <g key={i}>
            <polygon
              points={points}
              fill={fill}
              stroke="#0d1b2a"
              strokeWidth={1.2}
            />
            {emoji && tile_type !== 'desert' && (
              <text
                x={cx}
                y={cy - hexSize * 0.1}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={emojiSize}
              >
                {emoji}
              </text>
            )}
            {tile.token != null && (
              <>
                <circle
                  cx={cx}
                  cy={tokenY}
                  r={hexSize * 0.38}
                  fill="rgba(248,249,250,0.92)"
                  stroke={isHighProbToken ? '#e63946' : '#adb5bd'}
                  strokeWidth={1}
                />
                <text
                  x={cx}
                  y={tokenY + hexSize * 0.13}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={hexSize * 0.42}
                  fontWeight="bold"
                  fill={isHighProbToken ? '#e63946' : '#212529'}
                >
                  {tile.token}
                </text>
              </>
            )}
          </g>
        )
      })}

      {/* Port badges */}
      {portMarkers.map(({ idx, px, py, label, ratio }) => (
        <g key={idx}>
          <circle cx={px} cy={py} r={hexSize * 0.45}
            fill="#1a3a5c" stroke="#ffd60a" strokeWidth={1.2} />
          <text x={px} y={py - hexSize * 0.08}
            textAnchor="middle" dominantBaseline="middle" fontSize={hexSize * 0.38}>
            {label}
          </text>
          <text x={px} y={py + hexSize * 0.3}
            textAnchor="middle" fontSize={hexSize * 0.28}
            fill="#ffd60a" fontWeight="bold">
            {ratio}:1
          </text>
        </g>
      ))}
    </svg>
  )
}

// ─── Resource distribution ────────────────────────────────────────────────────

function ResourceBars({ tiles }: { tiles: { tile_type: string }[] }) {
  const counts: Record<string, number> = {}
  tiles.forEach(t => {
    const r = TERRAIN_RESOURCE[t.tile_type]
    if (r) counts[r] = (counts[r] ?? 0) + 1
  })
  const total = Object.values(counts).reduce((a, b) => a + b, 0)
  if (!total) return null
  return (
    <div className={styles.resBars}>
      {Object.entries(counts).sort(([, a], [, b]) => b - a).map(([res, cnt]) => (
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

// ─── Port list ────────────────────────────────────────────────────────────────

function PortList({ ports }: { ports: MapDetailPort[] }) {
  if (!ports.length) return null
  return (
    <div className={styles.portList}>
      {ports.map((p, i) => (
        <span key={i} className={`${styles.portBadge} ${p.resource ? styles.portSpecific : ''}`}>
          {p.resource ? RESOURCE_LABELS[p.resource as keyof typeof RESOURCE_LABELS] : '?'} {p.ratio}:1
        </span>
      ))}
    </div>
  )
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function DetailPanel({
  map,
  summary,
  onClose,
}: {
  map: MapConfig
  summary: MapSummary | undefined
  onClose: () => void
}) {
  const [detail, setDetail] = useState<MapDetailData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (map.id === 'random') return
    setLoading(true)
    fetchMapDetail(map.id)
      .then(setDetail)
      .finally(() => setLoading(false))
  }, [map.id])

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={e => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close">×</button>

        <div className={styles.panelHeader}>
          <h2 className={styles.panelName}>{map.name}</h2>
          {map.size === 'large' && <span className={styles.sizeBadge}>Large · 37 tiles</span>}
          {map.size !== 'large' && <span className={styles.sizeBadgeSm}>Standard · 19 tiles</span>}
        </div>

        <p className={styles.panelDesc}>{map.description}</p>

        {map.tags && (
          <div className={styles.tagRow}>
            {map.tags.map(t => <span key={t} className={styles.tag}>{t}</span>)}
          </div>
        )}

        <div className={styles.divider} />

        {/* Map render */}
        <div className={styles.mapWrap}>
          {loading && <span className={styles.loadingText}>Loading map…</span>}
          {!loading && detail && <HexDetailMap data={detail} />}
          {!loading && !detail && summary && summary.tiles.length > 0 && (
            <HexThumbnail summary={summary} size={map.size === 'large' ? 16 : 22} />
          )}
        </div>

        {detail && (
          <>
            <div className={styles.divider} />
            <div className={styles.statsRow}>
              <div>
                <h3 className={styles.sectionTitle}>Resources</h3>
                <ResourceBars tiles={detail.tiles} />
              </div>
              <div>
                <h3 className={styles.sectionTitle}>Ports ({detail.ports.length})</h3>
                <PortList ports={detail.ports} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Map card ─────────────────────────────────────────────────────────────────

function MapCard({
  map,
  summary,
  onClick,
}: {
  map: MapConfig
  summary: MapSummary | undefined
  onClick: () => void
}) {
  return (
    <button className={styles.card} onClick={onClick} type="button">
      <div className={styles.cardPreview}>
        {summary && summary.tiles.length > 0 ? (
          <HexThumbnail summary={summary} size={map.size === 'large' ? 8 : 11} />
        ) : (
          <div className={styles.thumbPlaceholder}>🎲</div>
        )}
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
  const [summaries, setSummaries] = useState<Map<string, MapSummary>>(new Map())

  useEffect(() => {
    fetchMapSummaries().then(data => {
      setSummaries(new Map(data.maps.map(m => [m.map_id, m])))
    })
  }, [])

  const filtered = useMemo(
    () => MAP_CONFIGS.filter(m => matchesFilter(m, filter)),
    [filter],
  )

  const detailSummary = detail ? summaries.get(detail.id) : undefined

  return (
    <div className={styles.page}>
      <div className={styles.hexBg} aria-hidden />

      <header className={styles.header}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>← Back</button>
        <div>
          <h1 className={styles.title}>Map Gallery</h1>
          <p className={styles.subtitle}>{MAP_CONFIGS.length - 1} maps · click to preview</p>
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
            <MapCard
              key={map.id}
              map={map}
              summary={summaries.get(map.id)}
              onClick={() => setDetail(map)}
            />
          ))}
        </div>
      )}

      {detail && (
        <DetailPanel
          map={detail}
          summary={detailSummary}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  )
}
