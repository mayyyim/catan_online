import { useEffect, useMemo, useState } from 'react'
import { getMapConfig, setMapConfig } from '../../api'
import { STANDARD_LAND_COORDS } from '../../engine/hexMath'
import { TERRAIN_LABELS, type MapConfigPayload, type ResourceType, type TileType } from '../../types'
import styles from './MapEditor.module.css'

type TileKey = `${number},${number}`

function keyOf(q: number, r: number): TileKey {
  return `${q},${r}`
}

const TILE_TYPES: TileType[] = ['forest', 'hills', 'fields', 'pasture', 'mountains', 'desert']
const PORT_RATIOS = [3, 2] as const

const RESOURCES: Array<ResourceType> = ['wood', 'brick', 'wheat', 'sheep', 'ore']

// Must match backend's HEX_DIRECTIONS indexing (side 0-5).
const HEX_DIRS: Array<{ dq: number; dr: number }> = [
  { dq: 1, dr: 0 },
  { dq: 1, dr: -1 },
  { dq: 0, dr: -1 },
  { dq: -1, dr: 0 },
  { dq: -1, dr: 1 },
  { dq: 0, dr: 1 },
]

export function MapEditor({ roomId }: { roomId: string }) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [config, setConfigState] = useState<MapConfigPayload | null>(null)
  const [activeTile, setActiveTile] = useState<TileKey | null>(null)
  const [activePortSide, setActivePortSide] = useState<number>(0)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError('')
    getMapConfig(roomId)
      .then(cfg => {
        if (!mounted) return
        setConfigState(cfg)
        const first = cfg.tiles[0]
        setActiveTile(first ? keyOf(first.q, first.r) : null)
      })
      .catch(e => {
        if (!mounted) return
        setError(e instanceof Error ? e.message : 'Failed to load map config')
      })
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [roomId])

  const tileMap = useMemo(() => {
    const m = new Map<TileKey, MapConfigPayload['tiles'][number]>()
    for (const t of config?.tiles ?? []) m.set(keyOf(t.q, t.r), t)
    return m
  }, [config])

  const portsForActiveTile = useMemo(() => {
    if (!config || !activeTile) return []
    const [q, r] = activeTile.split(',').map(Number)
    return (config.ports ?? []).filter(p => p.q === q && p.r === r)
  }, [config, activeTile])

  const coastalSidesForActiveTile = useMemo(() => {
    if (!config || !activeTile) return new Set<number>()
    const [q, r] = activeTile.split(',').map(Number)
    const land = new Set(config.tiles.map(t => keyOf(t.q, t.r)))
    const coastal = new Set<number>()
    for (let side = 0; side < 6; side++) {
      const { dq, dr } = HEX_DIRS[side]
      const neighbor = keyOf(q + dq, r + dr)
      if (!land.has(neighbor)) coastal.add(side)
    }
    return coastal
  }, [config, activeTile])

  const activePort = useMemo(() => {
    return portsForActiveTile.find(p => p.side === activePortSide) ?? null
  }, [portsForActiveTile, activePortSide])

  const activeTileObj = useMemo(() => {
    if (!activeTile) return null
    return tileMap.get(activeTile) ?? null
  }, [activeTile, tileMap])

  const setTileField = (patch: Partial<MapConfigPayload['tiles'][number]>) => {
    if (!config || !activeTileObj) return
    const nextTiles = config.tiles.map(t =>
      t.q === activeTileObj.q && t.r === activeTileObj.r ? { ...t, ...patch } : t,
    )
    setConfigState({ ...config, tiles: nextTiles })
  }

  const togglePortSide = (side: number) => {
    if (!config || !activeTileObj) return
    if (!coastalSidesForActiveTile.has(side)) return
    setActivePortSide(side)
    const exists = config.ports.some(p => p.q === activeTileObj.q && p.r === activeTileObj.r && p.side === side)
    if (exists) {
      setConfigState({
        ...config,
        ports: config.ports.filter(p => !(p.q === activeTileObj.q && p.r === activeTileObj.r && p.side === side)),
      })
    } else {
      setConfigState({
        ...config,
        ports: [
          ...config.ports,
          { q: activeTileObj.q, r: activeTileObj.r, side, ratio: 3, resource: null },
        ],
      })
    }
  }

  const setActivePortField = (patch: Partial<MapConfigPayload['ports'][number]>) => {
    if (!config || !activeTileObj) return
    const nextPorts = config.ports.map(p => {
      if (p.q === activeTileObj.q && p.r === activeTileObj.r && p.side === activePortSide) {
        return { ...p, ...patch }
      }
      return p
    })
    setConfigState({ ...config, ports: nextPorts })
  }

  const handleSave = async () => {
    if (!config) return
    setSaving(true)
    setError('')
    try {
      const saved = await setMapConfig(roomId, config)
      setConfigState(saved)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save map config')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.header}>
          <div className={styles.title}>Map Editor</div>
        </div>
        <div className={styles.hint}>Loading...</div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className={styles.wrap}>
        <div className={styles.header}>
          <div className={styles.title}>Map Editor</div>
        </div>
        <div className={styles.hint}>{error || 'No config'}</div>
      </div>
    )
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <div className={styles.title}>Map Editor (host)</div>
        <div className={styles.btnRow}>
          <button className={styles.btn} type="button" onClick={() => window.location.reload()}>
            Reload
          </button>
          <button
            className={`${styles.btn} ${styles.btnPrimary}`}
            type="button"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {error && <div className={styles.hint}>{error}</div>}

      <div className={styles.grid}>
        {STANDARD_LAND_COORDS.map(c => {
          const t = tileMap.get(keyOf(c.q, c.r))
          if (!t) return null
          const k = keyOf(t.q, t.r)
          const active = k === activeTile
          return (
            <button
              key={k}
              type="button"
              className={`${styles.tile} ${active ? styles.tileActive : ''}`}
              onClick={() => setActiveTile(k)}
            >
              <div className={styles.tileTop}>
                <span>{TERRAIN_LABELS[t.tile_type]}</span>
                <span>{t.token ?? '—'}</span>
              </div>
              <div className={styles.tileMeta}>
                ({t.q},{t.r}) {t.robber ? '🦹' : ''}
              </div>
            </button>
          )
        })}
      </div>

      {activeTileObj && (
        <div className={styles.panel}>
          <div className={styles.row}>
            <div className={styles.label}>Terrain</div>
            <select
              className={styles.select}
              value={activeTileObj.tile_type}
              onChange={e => setTileField({ tile_type: e.target.value as TileType })}
            >
              {TILE_TYPES.map(tt => (
                <option key={tt} value={tt}>
                  {tt}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Token</div>
            <input
              className={styles.input}
              type="number"
              min={2}
              max={12}
              value={activeTileObj.token ?? ''}
              onChange={e => setTileField({ token: e.target.value ? Number(e.target.value) : null })}
              placeholder="2-12 (blank for desert)"
            />
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Robber</div>
            <input
              type="checkbox"
              checked={!!activeTileObj.robber}
              onChange={e => setTileField({ robber: e.target.checked })}
            />
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Ports</div>
            <div>
              <div className={styles.portsGrid}>
                {Array.from({ length: 6 }).map((_, side) => {
                  const enabled = portsForActiveTile.some(p => p.side === side)
                  const coastal = coastalSidesForActiveTile.has(side)
                  return (
                    <button
                      key={side}
                      type="button"
                      className={`${styles.sideBtn} ${enabled ? styles.sideBtnActive : ''}`}
                      onClick={() => togglePortSide(side)}
                      disabled={!coastal}
                      title={
                        coastal
                          ? `Toggle port on side ${side}`
                          : `Side ${side} is not coastal (must face ocean)`
                      }
                    >
                      {side}
                    </button>
                  )
                })}
              </div>
              <div className={styles.hint}>
                Tip: ports can only be placed on coastal sides (facing ocean).
              </div>
            </div>
          </div>

          {activePort && (
            <>
              <div className={styles.row}>
                <div className={styles.label}>Side</div>
                <div className={styles.hint}>{activePortSide}</div>
              </div>
              <div className={styles.row}>
                <div className={styles.label}>Ratio</div>
                <select
                  className={styles.select}
                  value={activePort.ratio}
                  onChange={e => setActivePortField({ ratio: Number(e.target.value) })}
                >
                  {PORT_RATIOS.map(r => (
                    <option key={r} value={r}>
                      {r}:1
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.row}>
                <div className={styles.label}>Resource</div>
                <select
                  className={styles.select}
                  value={activePort.resource ?? ''}
                  onChange={e => setActivePortField({ resource: e.target.value ? (e.target.value as ResourceType) : null })}
                >
                  <option value="">generic (3:1)</option>
                  {RESOURCES.map(r => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

