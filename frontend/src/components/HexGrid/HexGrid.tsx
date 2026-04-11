import { useMemo, useCallback, useState, useRef, useEffect } from 'react'
import type { HexTile, Building, Road, Player, Port } from '../../types'
import { TERRAIN_LABELS, RESOURCE_LABELS } from '../../types'
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
const PADDING = 40

const SQ3 = Math.sqrt(3)
const SIDE_PIXEL_DIRS: [number, number][] = [
  [ 1.5,         SQ3 / 2],
  [ 1.5,        -SQ3 / 2],
  [ 0,          -SQ3],
  [-1.5,        -SQ3 / 2],
  [-1.5,         SQ3 / 2],
  [ 0,           SQ3],
]

/** Map dice number to probability dot count */
function probabilityDots(token: number): number {
  const dist = Math.abs(token - 7)
  return 6 - dist // 6,8→5  5,9→4  4,10→3  3,11→2  2,12→1
}

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

const MIN_ZOOM = 0.4
const MAX_ZOOM = 3.0

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

  // Compute tile pixel positions relative to origin (0,0)
  const tilePixels = useMemo(() => {
    return tiles.map(tile => {
      const { x, y } = cubeToPixel(tile.q, tile.r, HEX_SIZE)
      return { tile, cx: x, cy: y }
    })
  }, [tiles])

  // Compute content bounding box
  const bounds = useMemo(() => {
    if (!tilePixels.length) return { minX: 0, minY: 0, maxX: width, maxY: height, contentW: width, contentH: height }
    const xs = tilePixels.map(t => t.cx)
    const ys = tilePixels.map(t => t.cy)
    const minX = Math.min(...xs) - HEX_SIZE - PADDING
    const maxX = Math.max(...xs) + HEX_SIZE + PADDING
    const minY = Math.min(...ys) - HEX_SIZE * 0.9 - PADDING
    const maxY = Math.max(...ys) + HEX_SIZE * 0.9 + PADDING
    return { minX, minY, maxX, maxY, contentW: maxX - minX, contentH: maxY - minY }
  }, [tilePixels, width, height])

  // Zoom & pan state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const dragStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-fit zoom on mount or tile change
  useEffect(() => {
    if (!bounds.contentW || !bounds.contentH) return
    const scaleX = width / bounds.contentW
    const scaleY = height / bounds.contentH
    const fitZoom = Math.min(scaleX, scaleY, 1.0)
    setZoom(fitZoom)
    setPan({ x: 0, y: 0 })
  }, [bounds.contentW, bounds.contentH, width, height])

  // Wheel zoom
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = -e.deltaY * 0.001
    setZoom(prev => Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, prev + delta * prev)))
  }, [])

  // Drag pan
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    // Only pan with middle button, or when no game action is expected (touch)
    if (e.button === 1 || e.pointerType === 'touch') {
      setDragging(true)
      dragStart.current = { x: e.clientX, y: e.clientY, panX: pan.x, panY: pan.y }
      ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
    }
  }, [pan])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging) return
    const dx = e.clientX - dragStart.current.x
    const dy = e.clientY - dragStart.current.y
    setPan({ x: dragStart.current.panX + dx / zoom, y: dragStart.current.panY + dy / zoom })
  }, [dragging, zoom])

  const handlePointerUp = useCallback(() => {
    setDragging(false)
  }, [])

  // Compute viewBox centered on content with zoom/pan
  const viewBox = useMemo(() => {
    const cx = (bounds.minX + bounds.maxX) / 2 - pan.x
    const cy = (bounds.minY + bounds.maxY) / 2 - pan.y
    const vw = width / zoom
    const vh = height / zoom
    return `${cx - vw / 2} ${cy - vh / 2} ${vw} ${vh}`
  }, [bounds, zoom, pan, width, height])

  // Pre-compute vertices & edges relative to origin
  const allVertices = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    for (const { tile, cx, cy } of tilePixels) {
      if (tile.terrain === 'ocean') continue
      const corners = hexCorners(cx, cy, HEX_SIZE)
      corners.forEach((pt, i) => {
        const id = vertexId(tile.q, tile.r, tile.s, i)
        if (!map.has(id)) map.set(id, pt)
      })
    }
    return map
  }, [tilePixels])

  const allEdges = useMemo(() => {
    const map = new Map<string, { x1: number; y1: number; x2: number; y2: number }>()
    for (const { tile, cx, cy } of tilePixels) {
      if (tile.terrain === 'ocean') continue
      const corners = hexCorners(cx, cy, HEX_SIZE)
      corners.forEach((pt, i) => {
        const next = corners[(i + 1) % 6]
        const id = edgeId(tile.q, tile.r, tile.s, i)
        if (!map.has(id)) map.set(id, { x1: pt.x, y1: pt.y, x2: next.x, y2: next.y })
      })
    }
    return map
  }, [tilePixels])

  const handleVertexClick = useCallback(
    (id: string) => onVertexClick?.(id),
    [onVertexClick],
  )

  const handleEdgeClick = useCallback(
    (id: string) => onEdgeClick?.(id),
    [onEdgeClick],
  )

  // Reset zoom handler
  const handleResetZoom = useCallback(() => {
    const scaleX = width / bounds.contentW
    const scaleY = height / bounds.contentH
    setZoom(Math.min(scaleX, scaleY, 1.0))
    setPan({ x: 0, y: 0 })
  }, [width, height, bounds])

  return (
    <div
      ref={containerRef}
      className={styles.container}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <svg
        width={width}
        height={height}
        className={styles.grid}
        viewBox={viewBox}
      >
        {/* SVG Definitions: gradients, filters */}
        <defs>
          {/* Terrain radial gradients */}
          <radialGradient id="grad-forest" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#2d8a4e" />
            <stop offset="100%" stopColor="#1a5c32" />
          </radialGradient>
          <radialGradient id="grad-hills" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#d4804a" />
            <stop offset="100%" stopColor="#c46a3a" />
          </radialGradient>
          <radialGradient id="grad-fields" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#e8b830" />
            <stop offset="100%" stopColor="#d4a017" />
          </radialGradient>
          <radialGradient id="grad-pasture" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#5cbf78" />
            <stop offset="100%" stopColor="#4aa564" />
          </radialGradient>
          <radialGradient id="grad-mountains" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#727e8a" />
            <stop offset="100%" stopColor="#5a6570" />
          </radialGradient>
          <radialGradient id="grad-desert" cx="50%" cy="40%">
            <stop offset="0%" stopColor="#e0b870" />
            <stop offset="100%" stopColor="#d4a55a" />
          </radialGradient>
          <radialGradient id="grad-ocean" cx="50%" cy="45%">
            <stop offset="0%" stopColor="#1e5a8a" />
            <stop offset="100%" stopColor="#0f3460" />
          </radialGradient>

          {/* Subtle noise texture filter for land tiles */}
          <filter id="terrain-texture">
            <feTurbulence type="fractalNoise" baseFrequency="0.65" numOctaves="3" result="noise" />
            <feColorMatrix type="saturate" values="0" in="noise" result="gray-noise" />
            <feBlend in="SourceGraphic" in2="gray-noise" mode="soft-light" result="textured" />
            <feComposite in="textured" in2="SourceGraphic" operator="in" />
          </filter>
        </defs>

        {/* Tile polygons */}
        {tilePixels.map(({ tile, cx, cy }) => {
          const corners = hexCorners(cx, cy, HEX_SIZE)
          const points = cornersToSvgPoints(corners)
          const isOcean = tile.terrain === 'ocean'
          const gradId = `url(#grad-${tile.terrain})`
          const isHighProb = tile.token === 6 || tile.token === 8

          return (
            <g
              key={`${tile.q},${tile.r},${tile.s}`}
              onClick={() => !isOcean && onTileClick?.(tile)}
              className={isOcean ? styles.oceanTile : styles.landTile}
            >
              {/* Main terrain fill with gradient */}
              <polygon
                points={points}
                fill={gradId}
                filter={isOcean ? undefined : 'url(#terrain-texture)'}
                stroke={isOcean ? 'rgba(10,20,40,0.5)' : '#0a1520'}
                strokeWidth={isOcean ? 1 : 1.5}
              />
              {/* Subtle inner highlight for depth */}
              {!isOcean && (
                <polygon
                  points={points}
                  fill="none"
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth={1}
                />
              )}

              {/* Robber overlay */}
              {tile.robber && (
                <>
                  <circle cx={cx} cy={cy} r={20} fill="rgba(0,0,0,0.6)" />
                  <text
                    x={cx}
                    y={cy + 1}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={32}
                    className={styles.robberIcon}
                  >
                    🦹
                  </text>
                </>
              )}

              {/* Terrain emoji - larger and repositioned */}
              {!isOcean && !tile.robber && (
                <text
                  x={cx}
                  y={cy - 10}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={26}
                  className={styles.terrainEmoji}
                >
                  {TERRAIN_LABELS[tile.terrain]}
                </text>
              )}

              {/* Number token - redesigned with parchment look and probability dots */}
              {tile.token !== undefined && (
                <>
                  <circle
                    cx={cx}
                    cy={cy + 14}
                    r={17}
                    fill={isHighProb ? '#f5d0c0' : '#f5e6c8'}
                    stroke={isHighProb ? '#c0392b' : '#8b7355'}
                    strokeWidth={1.5}
                  />
                  <text
                    x={cx}
                    y={cy + 14}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={16}
                    fontWeight={800}
                    fill={isHighProb ? '#c0392b' : '#212529'}
                    className={styles.tokenText}
                  >
                    {tile.token}
                  </text>
                  <text
                    x={cx}
                    y={cy + 26}
                    textAnchor="middle"
                    dominantBaseline="central"
                    fontSize={7}
                    fill={isHighProb ? '#c0392b' : '#8b7355'}
                    className={styles.probabilityDots}
                  >
                    {'\u2022'.repeat(probabilityDots(tile.token))}
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
              x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2}
              stroke={color} strokeWidth={ROAD_STROKE} strokeLinecap="round"
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
            <g key={`buildable-edge-${eid}`} onClick={() => handleEdgeClick(eid)} className={styles.buildableEdge}>
              <line
                x1={edge.x1} y1={edge.y1} x2={edge.x2} y2={edge.y2}
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
            const w = 8, roofTop = -13, eaveY = -3, botY = 7
            const pts = [
              `${pt.x},${pt.y + roofTop}`,
              `${pt.x + w},${pt.y + eaveY}`,
              `${pt.x + w},${pt.y + botY}`,
              `${pt.x - w},${pt.y + botY}`,
              `${pt.x - w},${pt.y + eaveY}`,
            ].join(' ')
            return <polygon key={building.vertexId} points={pts} fill={color} stroke="#0d1b2a" strokeWidth={2} className={styles.building} />
          } else {
            const pts = [
              `${pt.x - 11},${pt.y + 9}`,
              `${pt.x - 11},${pt.y - 5}`,
              `${pt.x - 4},${pt.y - 5}`,
              `${pt.x - 4},${pt.y - 12}`,
              `${pt.x + 11},${pt.y - 12}`,
              `${pt.x + 11},${pt.y + 9}`,
            ].join(' ')
            return <polygon key={building.vertexId} points={pts} fill={color} stroke="#0d1b2a" strokeWidth={2} className={styles.building} />
          }
        })}

        {/* Ports */}
        {ports.map((port, idx) => {
          const { x: tilePx, y: tilePy } = cubeToPixel(port.q, port.r, HEX_SIZE)
          const [ddx, ddy] = SIDE_PIXEL_DIRS[port.side] ?? [0, 0]
          const portX = tilePx + ddx * HEX_SIZE * 0.6
          const portY = tilePy + ddy * HEX_SIZE * 0.6
          const label = port.resource ? RESOURCE_LABELS[port.resource] : '?'
          const ratioText = `${port.ratio}:1`
          return (
            <g key={`port-${idx}`} className={styles.port}>
              <circle cx={portX} cy={portY} r={14} fill="#1a3a5c" stroke="#ffd60a" strokeWidth={1.5} />
              <text x={portX} y={portY - 2} textAnchor="middle" fontSize={11} fill="#ffd60a">{label}</text>
              <text x={portX} y={portY + 10} textAnchor="middle" fontSize={9} fill="#cce" fontWeight="bold">{ratioText}</text>
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
              cx={pt.x} cy={pt.y} r={VERTEX_RADIUS}
              fill={isSelected ? '#ffd60a' : 'rgba(255,255,255,0.25)'}
              stroke={isSelected ? '#ffd60a' : 'rgba(255,255,255,0.6)'}
              strokeWidth={2}
              onClick={() => handleVertexClick(vid)}
              className={styles.buildableVertex}
            />
          )
        })}
      </svg>

      {/* Zoom controls */}
      <div className={styles.zoomControls}>
        <button type="button" className={styles.zoomBtn} onClick={() => setZoom(z => Math.min(MAX_ZOOM, z * 1.2))} title="Zoom in">+</button>
        <button type="button" className={styles.zoomBtn} onClick={() => setZoom(z => Math.max(MIN_ZOOM, z / 1.2))} title="Zoom out">−</button>
        <button type="button" className={styles.zoomBtn} onClick={handleResetZoom} title="Reset view">⟲</button>
      </div>
    </div>
  )
}
