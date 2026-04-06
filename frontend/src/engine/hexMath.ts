// Flat-top hex grid math
// Cube coordinates (q, r, s) where q + r + s = 0

export interface CubeCoord {
  q: number
  r: number
  s: number
}

export interface PixelPoint {
  x: number
  y: number
}

/**
 * Convert cube coordinates to pixel center (flat-top orientation).
 */
export function cubeToPixel(
  q: number,
  r: number,
  size: number,
): PixelPoint {
  const x = size * (3 / 2) * q
  const y = size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r)
  return { x, y }
}

/**
 * Returns the 6 corner pixel positions of a flat-top hexagon
 * centered at (cx, cy) with the given size.
 * Corners are ordered 0-5 starting from the right-most vertex going clockwise.
 */
export function hexCorners(
  cx: number,
  cy: number,
  size: number,
): PixelPoint[] {
  const corners: PixelPoint[] = []
  for (let i = 0; i < 6; i++) {
    const angleDeg = 60 * i  // flat-top: 0° is right
    const angleRad = (Math.PI / 180) * angleDeg
    corners.push({
      x: cx + size * Math.cos(angleRad),
      y: cy + size * Math.sin(angleRad),
    })
  }
  return corners
}

/**
 * Build a SVG polygon points string from an array of PixelPoints.
 */
export function cornersToSvgPoints(corners: PixelPoint[]): string {
  return corners.map(c => `${c.x.toFixed(2)},${c.y.toFixed(2)}`).join(' ')
}

/**
 * Returns a canonical vertex id string from three adjacent tiles
 * that share the vertex. We use the convention: smallest-tile-id:vertex-index.
 *
 * For rendering purposes we key vertices by (q,r,s) + corner index.
 */
export function vertexId(q: number, r: number, s: number, corner: number): string {
  return `${q},${r},${s}:v${corner}`
}

/**
 * Returns a canonical edge id from tile coords and edge index (0-5).
 */
export function edgeId(q: number, r: number, s: number, edge: number): string {
  return `${q},${r},${s}:e${edge}`
}

/**
 * Midpoint between two PixelPoints.
 */
export function midpoint(a: PixelPoint, b: PixelPoint): PixelPoint {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }
}

/**
 * Distance between two PixelPoints.
 */
export function distance(a: PixelPoint, b: PixelPoint): number {
  return Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)
}

// Standard Catan board layout in cube coordinates (19 land tiles + ring of ocean)
export const STANDARD_LAND_COORDS: CubeCoord[] = [
  // Row 0 (top, 3 tiles)
  { q: 0, r: -2, s: 2 },
  { q: 1, r: -2, s: 1 },
  { q: 2, r: -2, s: 0 },
  // Row 1 (4 tiles)
  { q: -1, r: -1, s: 2 },
  { q: 0, r: -1, s: 1 },
  { q: 1, r: -1, s: 0 },
  { q: 2, r: -1, s: -1 },
  // Row 2 (5 tiles, middle)
  { q: -2, r: 0, s: 2 },
  { q: -1, r: 0, s: 1 },
  { q: 0, r: 0, s: 0 },
  { q: 1, r: 0, s: -1 },
  { q: 2, r: 0, s: -2 },
  // Row 3 (4 tiles)
  { q: -2, r: 1, s: 1 },
  { q: -1, r: 1, s: 0 },
  { q: 0, r: 1, s: -1 },
  { q: 1, r: 1, s: -2 },
  // Row 4 (bottom, 3 tiles)
  { q: -2, r: 2, s: 0 },
  { q: -1, r: 2, s: -1 },
  { q: 0, r: 2, s: -2 },
]
