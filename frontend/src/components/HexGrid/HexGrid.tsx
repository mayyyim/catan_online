import { useMemo, useCallback } from 'react'
import type { HexTile, Building, Road, Player, Port } from '../../types'
import { TERRAIN_COLORS, TERRAIN_LABELS, RESOURCE_LABELS } from '../../types'
import {
  cubeToPixel,
  hexCorners,
  cornersToSvgPoints,
  vertexId,
  edgeId,
} from '../../engine/hexMath'
import styles from './HexGrid.module.css'

const HEX_SIZE = 60
const VERTEX_RADIUS = 8
const ROAD_STROKE = 8

// Pixel direction vectors for each backend side index (flat-top hex, SVG y-down).
// Derived from cubeToPixel(dq, dr, 1): x = 1.5*dq, y = (√3/2)*dq + √3*dr
// Backend HEX_DIRECTIONS = [(1,0),(1,-1),(0,-1),(-1,0),(-1,1),(0,1)]
const SQ3 = Math.sqrt(3)
const SIDE_PIXEL_DIRS: [number, number][] = [
  [ 1.5,         SQ3 / 2],   // side 0: (1,  0)
  [ 1.5,        -SQ3 / 2],   // side 1: (1, -1)
  [ 0,          -SQ3],       // side 2: (0, -1)
  [-1.5,        -SQ3 / 2],   // side 3: (-1, 0)
  [-1.5,         SQ3 / 2],   // side 4: (-1, 1)
  [ 0,           SQ3],       // side 5: (0,  1)
]

interface HexGridProps {
  tiles: HexTile[]
  ports?: Port[]
  buildings: Building[]
  roads: Road[]
  players: Player[]
  selectedVertexId?: string | null
  selectedEdgeId?: string | null
  buildableVertices?: string[]
  buildableEdges?: string[]
  onVertexClick?: (id: string) => void
  onEdgeClick?: (id: string) => void
  onTileClick?: (tile: HexTile) => void
  width?: number
  height?: number
}

function playerColor(players: Player[], playerId: string): string {
  return players.find(p => p.id === playerId)?.color ?? '#fff'
}

export function HexGrid({
  tiles,
  ports = [],
  buildings,
  roads,
  players,
  selectedVertexId,
  selectedEdgeId,
  buildableVertices = [],
  buildableEdges = [],
  onVertexClick,
  onEdgeClick,
  onTileClick,
  width = 700,
  height = 680,
}: HexGridProps) {
  const centerX = width / 2
  const centerY = height / 2

  // Pre-compute pixel centers for every tile
  const tileCenters = useMemo(() => {
    return tiles.map(tile => {
      const { x, y } = cubeToPixel(tile.q, tile.r, HEX_SIZE)
      return { tile, cx: centerX + x, cy: centerY + y }
    })
  }, [tiles, centerX, centerY])

  // Collect unique vertices across all land tiles
  const allVertices = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    for (const { tile, cx, cy } of tileCenters) {
      if (tile.terrain === 'ocean') continue
      const corners = hexCorners(cx, cy, HEX_SIZE)
      corners.forEach((pt, i) => {
        const id = vertexId(tile.q, tile.r, tile.s, i)
        if (!map.has(id)) map.set(id, pt)
      })
    }
    return map
  }, [tileCenters])

  // Collect unique edges across all land tiles
  const allEdges = useMemo(() => {
    const map = new Map<string, { x1: number; y1: number; x2: number; y2: number }>()
    for (const { tile, cx, cy } of tileCenters) {
      if (tile.terrain === 'ocean') continue
      const corners = hexCorners(cx, cy, HEX_SIZE)
      corners.forEach((pt, i) => {
        const next = corners[(i + 1) % 6]
        const id = edgeId(tile.q, tile.r, tile.s, i)
        if (!map.has(id)) {
          map.set(id, { x1: pt.x, y1: pt.y, x2: next.x, y2: next.y })
        }
      })
    }
    return map
  }, [tileCenters])

  const handleVertexClick = useCallback(
    (id: string) => onVertexClick?.(id),
    [onVertexClick],
  )

  const handleEdgeClick = useCallback(
    (id: string) => onEdgeClick?.(id),
    [onEdgeClick],
  )

  return (
    <svg
      width={width}
      height={height}
      className={styles.grid}
      viewBox={`0 0 ${width} ${height}`}
    >
      {/* Tile polygons */}
      {tileCenters.map(({ tile, cx, cy }) => {
        const corners = hexCorners(cx, cy, HEX_SIZE)
        const points = cornersToSvgPoints(corners)
        const color = TERRAIN_COLORS[tile.terrain]
        const isOcean = tile.terrain === 'ocean'

        return (
          <g
            key={`${tile.q},${tile.r},${tile.s}`}
            onClick={() => !isOcean && onTileClick?.(tile)}
            className={isOcean ? styles.oceanTile : styles.landTile}
          >
            <polygon
              points={points}
              fill={color}
              stroke="#0d1b2a"
              strokeWidth={2}
            />
            {/* Robber */}
            {tile.robber && (
              <text
                x={cx}
                y={cy + 6}
                textAnchor="middle"
                fontSize={28}
                className={styles.robberIcon}
              >
                🦹
              </text>
            )}
            {/* Resource emoji */}
            {!isOcean && !tile.robber && (
              <text
                x={cx}
                y={cy - 8}
                textAnchor="middle"
                fontSize={22}
                className={styles.terrainEmoji}
              >
                {TERRAIN_LABELS[tile.terrain]}
              </text>
            )}
            {/* Number token */}
            {tile.token !== undefined && (
              <>
                <circle
                  cx={cx}
                  cy={cy + 16}
                  r={16}
                  fill="#f8f9fa"
                  stroke="#dee2e6"
                  strokeWidth={1}
                />
                <text
                  x={cx}
                  y={cy + 22}
                  textAnchor="middle"
                  fontSize={14}
                  fontWeight="bold"
                  fill={
                    tile.token === 6 || tile.token === 8 ? '#e63946' : '#212529'
                  }
                  className={styles.tokenText}
                >
                  {tile.token}
                </text>
              </>
            )}
          </g>
        )
      })}

      {/* Roads */}
      {roads.map(road => {
        const edge = allEdges.get(road.edgeId)
        if (!edge) return null
        const color = playerColor(players, road.playerId)
        return (
          <line
            key={road.edgeId}
            x1={edge.x1}
            y1={edge.y1}
            x2={edge.x2}
            y2={edge.y2}
            stroke={color}
            strokeWidth={ROAD_STROKE}
            strokeLinecap="round"
            className={styles.road}
          />
        )
      })}

      {/* Buildable edge indicators */}
      {buildableEdges.map(eid => {
        const edge = allEdges.get(eid)
        if (!edge) return null
        const isSelected = selectedEdgeId === eid
        return (
          <g
            key={`buildable-edge-${eid}`}
            onClick={() => handleEdgeClick(eid)}
            className={styles.buildableEdge}
          >
            <line
              x1={edge.x1}
              y1={edge.y1}
              x2={edge.x2}
              y2={edge.y2}
              stroke={isSelected ? '#ffd60a' : 'rgba(255,255,255,0.4)'}
              strokeWidth={isSelected ? ROAD_STROKE : 5}
              strokeLinecap="round"
            />
          </g>
        )
      })}

      {/* Buildings */}
      {buildings.map(building => {
        const pt = allVertices.get(building.vertexId)
        if (!pt) return null
        const color = playerColor(players, building.playerId)
        if (building.type === 'settlement') {
          // Triangle pointing up
          const s = 10
          const points = `${pt.x},${pt.y - s} ${pt.x - s},${pt.y + s} ${pt.x + s},${pt.y + s}`
          return (
            <polygon
              key={building.vertexId}
              points={points}
              fill={color}
              stroke="#0d1b2a"
              strokeWidth={2}
              className={styles.building}
            />
          )
        } else {
          // City: small square
          const s = 10
          return (
            <rect
              key={building.vertexId}
              x={pt.x - s}
              y={pt.y - s}
              width={s * 2}
              height={s * 2}
              fill={color}
              stroke="#0d1b2a"
              strokeWidth={2}
              className={styles.building}
            />
          )
        }
      })}

      {/* Ports */}
      {ports.map((port, idx) => {
        const { x: tilePx, y: tilePy } = cubeToPixel(port.q, port.r, HEX_SIZE)
        const cx = centerX + tilePx
        const cy = centerY + tilePy
        const [ddx, ddy] = SIDE_PIXEL_DIRS[port.side] ?? [0, 0]
        // Place badge at ~60 % of the way toward the ocean neighbor (just outside the edge)
        const portX = cx + ddx * HEX_SIZE * 0.6
        const portY = cy + ddy * HEX_SIZE * 0.6
        const label = port.resource ? RESOURCE_LABELS[port.resource] : '?'
        const ratioText = `${port.ratio}:1`
        return (
          <g key={`port-${idx}`} className={styles.port}>
            <circle cx={portX} cy={portY} r={14} fill="#1a3a5c" stroke="#ffd60a" strokeWidth={1.5} />
            <text x={portX} y={portY - 2} textAnchor="middle" fontSize={11} fill="#ffd60a">
              {label}
            </text>
            <text x={portX} y={portY + 10} textAnchor="middle" fontSize={9} fill="#cce" fontWeight="bold">
              {ratioText}
            </text>
          </g>
        )
      })}

      {/* Buildable vertex indicators */}
      {buildableVertices.map(vid => {
        const pt = allVertices.get(vid)
        if (!pt) return null
        const isSelected = selectedVertexId === vid
        return (
          <circle
            key={`buildable-${vid}`}
            cx={pt.x}
            cy={pt.y}
            r={VERTEX_RADIUS}
            fill={isSelected ? '#ffd60a' : 'rgba(255,255,255,0.25)'}
            stroke={isSelected ? '#ffd60a' : 'rgba(255,255,255,0.6)'}
            strokeWidth={2}
            onClick={() => handleVertexClick(vid)}
            className={styles.buildableVertex}
          />
        )
      })}
    </svg>
  )
}
