import type { MapConfig, TerrainType } from '../../types'
import { TERRAIN_COLORS } from '../../types'
import styles from './MapThumbnail.module.css'

interface MapThumbnailProps {
  map: MapConfig
  selected?: boolean
  onClick?: () => void
}

const CELL_SIZE = 14
const GAP = 2

export function MapThumbnail({ map, selected, onClick }: MapThumbnailProps) {
  const rows = map.preview
  const maxCols = Math.max(...rows.map(r => r.length))
  const svgW = maxCols * (CELL_SIZE + GAP)
  const svgH = rows.length * (CELL_SIZE + GAP)

  return (
    <button
      className={`${styles.card} ${selected ? styles.selected : ''}`}
      onClick={onClick}
      type="button"
      aria-pressed={selected}
    >
      <svg
        width={svgW}
        height={svgH}
        className={styles.preview}
        viewBox={`0 0 ${svgW} ${svgH}`}
      >
        {rows.map((row, ri) =>
          row.map((terrain: TerrainType, ci) => (
            <rect
              key={`${ri}-${ci}`}
              x={ci * (CELL_SIZE + GAP)}
              y={ri * (CELL_SIZE + GAP)}
              width={CELL_SIZE}
              height={CELL_SIZE}
              rx={2}
              fill={TERRAIN_COLORS[terrain]}
              opacity={0.9}
            />
          )),
        )}
      </svg>
      <span className={styles.name}>{map.name}</span>
      <span className={styles.desc}>{map.description}</span>
    </button>
  )
}
