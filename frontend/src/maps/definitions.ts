import type { MapConfig, TerrainType } from '../types'

// Each preview is a rough 5-row grid of terrain types to visualise
// resource distribution in the lobby map thumbnail.

const standard: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'forest', 'hills', 'ocean'],
  ['ocean', 'fields', 'pasture', 'mountains', 'ocean'],
  ['ocean', 'desert', 'fields', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const seafarers: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'forest', 'ocean', 'hills', 'ocean'],
  ['ocean', 'fields', 'pasture', 'mountains', 'ocean'],
  ['ocean', 'ocean', 'desert', 'ocean', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
]

const australia: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'desert', 'desert', 'ocean'],
  ['ocean', 'hills', 'desert', 'fields', 'ocean'],
  ['ocean', 'pasture', 'forest', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const japan: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'mountains', 'forest', 'ocean', 'ocean'],
  ['ocean', 'forest', 'fields', 'ocean', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
]

const nordic: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'mountains', 'forest', 'ocean'],
  ['ocean', 'mountains', 'forest', 'pasture', 'ocean'],
  ['ocean', 'desert', 'hills', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const tropics: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'pasture', 'fields', 'ocean'],
  ['ocean', 'forest', 'pasture', 'fields', 'ocean'],
  ['ocean', 'desert', 'pasture', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const volcanic: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'hills', 'mountains', 'ocean'],
  ['ocean', 'hills', 'desert', 'mountains', 'ocean'],
  ['ocean', 'forest', 'fields', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const highlands: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'mountains', 'hills', 'ocean'],
  ['ocean', 'mountains', 'pasture', 'fields', 'ocean'],
  ['ocean', 'forest', 'fields', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean'],
]

const archipelago: TerrainType[][] = [
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
  ['ocean', 'forest', 'ocean', 'pasture', 'ocean'],
  ['ocean', 'hills', 'ocean', 'fields', 'ocean'],
  ['ocean', 'ocean', 'mountains', 'ocean', 'ocean'],
  ['ocean', 'ocean', 'ocean', 'ocean', 'ocean'],
]

export const MAP_CONFIGS: MapConfig[] = [
  {
    id: 'standard',
    name: 'Standard',
    description: 'The classic Catan board. Balanced resource distribution.',
    preview: standard,
  },
  {
    id: 'seafarers',
    name: 'Seafarers',
    description: 'Islands scattered across a wide ocean. Exploration required.',
    preview: seafarers,
  },
  {
    id: 'australia',
    name: 'Australia',
    description: 'Desert-heavy interior with resources on the coast.',
    preview: australia,
  },
  {
    id: 'japan',
    name: 'Japan',
    description: 'Narrow landmass surrounded by deep ocean.',
    preview: japan,
  },
  {
    id: 'nordic',
    name: 'Nordic',
    description: 'Mountains and forests dominate this frozen frontier.',
    preview: nordic,
  },
  {
    id: 'tropics',
    name: 'Tropics',
    description: 'Lush pastures and fields in a warm climate.',
    preview: tropics,
  },
  {
    id: 'volcanic',
    name: 'Volcanic',
    description: 'Rich in ore and brick but harsh terrain.',
    preview: volcanic,
  },
  {
    id: 'highlands',
    name: 'Highlands',
    description: 'Rolling hills and mountain peaks.',
    preview: highlands,
  },
  {
    id: 'archipelago',
    name: 'Archipelago',
    description: 'Separate islands — longest road is a challenge.',
    preview: archipelago,
  },
]
