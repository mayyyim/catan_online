import type { HexTile, TerrainType, ResourceType } from '../types'
import { STANDARD_LAND_COORDS } from './hexMath'

// Standard Catan distribution
const TERRAIN_DISTRIBUTION: TerrainType[] = [
  'forest', 'forest', 'forest', 'forest',
  'hills', 'hills', 'hills',
  'fields', 'fields', 'fields', 'fields',
  'pasture', 'pasture', 'pasture', 'pasture',
  'mountains', 'mountains', 'mountains',
  'desert',
]

const TOKEN_DISTRIBUTION = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

function seededRandom(seed: number) {
  let s = seed
  return function () {
    s = (s * 1664525 + 1013904223) & 0xffffffff
    return (s >>> 0) / 0xffffffff
  }
}

function shuffleWithSeed<T>(arr: T[], rand: () => number): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export function generateBoard(seed: string | number = Date.now()): HexTile[] {
  const numericSeed = typeof seed === 'string' ? hashString(seed) : seed
  const rand = seededRandom(numericSeed)

  const terrains = shuffleWithSeed(TERRAIN_DISTRIBUTION, rand)
  const tokens = shuffleWithSeed(TOKEN_DISTRIBUTION, rand)

  let tokenIndex = 0
  return STANDARD_LAND_COORDS.map((coord, i) => {
    const terrain = terrains[i]
    const isDesert = terrain === 'desert'
    const token = isDesert ? undefined : tokens[tokenIndex++]
    return {
      q: coord.q,
      r: coord.r,
      s: coord.s,
      terrain,
      token,
      robber: isDesert,
    }
  })
}

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash |= 0
  }
  return Math.abs(hash)
}

export const TERRAIN_TO_RESOURCE: Partial<Record<TerrainType, ResourceType>> = {
  forest: 'wood',
  hills: 'brick',
  fields: 'wheat',
  pasture: 'sheep',
  mountains: 'ore',
}
