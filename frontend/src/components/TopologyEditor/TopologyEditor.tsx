import { useEffect, useMemo, useState } from 'react'
import { getMapTopology, setMapTopology } from '../../api'
import type { MapTopologyPayload, ResourceType, TileType, TopologyTilePayload } from '../../types'
import { TERRAIN_LABELS } from '../../types'
import styles from './TopologyEditor.module.css'

type TileId = string

const TILE_TYPES: TileType[] = ['forest', 'hills', 'fields', 'pasture', 'mountains', 'desert']
const PORT_RATIOS = [3, 2] as const
const RESOURCES: Array<ResourceType> = ['wood', 'brick', 'wheat', 'sheep', 'ore']

function makeId(): string {
  return `t_${Math.random().toString(16).slice(2, 8)}${Date.now().toString(16).slice(-4)}`
}

function oppositeSide(side: number): number {
  return ((side % 6) + 3) % 6
}

function coastalSides(tile: TopologyTilePayload): number[] {
  const used = new Set(Object.keys(tile.neighbors ?? {}).map(k => ((Number(k) % 6) + 6) % 6))
  return Array.from({ length: 6 }).map((_, i) => i).filter(i => !used.has(i))
}

export function TopologyEditor({ roomId }: { roomId: string }) {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [config, setConfig] = useState<MapTopologyPayload | null>(null)

  const [activeTileId, setActiveTileId] = useState<TileId | null>(null)
  const [connectSide, setConnectSide] = useState<number>(0)
  const [connectTarget, setConnectTarget] = useState<TileId>('')
  const [activePortSide, setActivePortSide] = useState<number>(0)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError('')
    getMapTopology(roomId)
      .then(topo => {
        if (!mounted) return
        setConfig(topo)
        setActiveTileId(topo.tiles[0]?.tile_id ?? null)
      })
      .catch(e => {
        if (!mounted) return
        setError(e instanceof Error ? e.message : 'Failed to load map topology')
      })
      .finally(() => mounted && setLoading(false))
    return () => {
      mounted = false
    }
  }, [roomId])

  const tileById = useMemo(() => {
    const m = new Map<TileId, TopologyTilePayload>()
    for (const t of config?.tiles ?? []) m.set(t.tile_id, t)
    return m
  }, [config])

  const activeTile = useMemo(() => {
    if (!activeTileId) return null
    return tileById.get(activeTileId) ?? null
  }, [activeTileId, tileById])

  const portsForActiveTile = useMemo(() => {
    if (!config || !activeTileId) return []
    return (config.ports ?? []).filter(p => p.tile_id === activeTileId)
  }, [config, activeTileId])

  const activePort = useMemo(() => {
    return portsForActiveTile.find(p => p.side === activePortSide) ?? null
  }, [portsForActiveTile, activePortSide])

  const handleSave = async () => {
    if (!config) return
    setSaving(true)
    setError('')
    try {
      const saved = await setMapTopology(roomId, config)
      setConfig(saved)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save topology')
    } finally {
      setSaving(false)
    }
  }

  const setTileField = (patch: Partial<TopologyTilePayload>) => {
    if (!config || !activeTile) return
    const nextTiles = config.tiles.map(t => (t.tile_id === activeTile.tile_id ? { ...t, ...patch } : t))
    setConfig({ ...config, tiles: nextTiles })
  }

  const addTile = () => {
    if (!config) return
    const id = makeId()
    const next: TopologyTilePayload = {
      tile_id: id,
      tile_type: 'forest',
      token: 9,
      robber: false,
      neighbors: {},
    }
    setConfig({ ...config, tiles: [...config.tiles, next] })
    setActiveTileId(id)
  }

  const removeTile = (tileId: string) => {
    if (!config) return
    const nextTiles = config.tiles.filter(t => t.tile_id !== tileId)
    // Remove references from neighbors
    const cleanedTiles = nextTiles.map(t => {
      const n: Record<number, string> = {}
      for (const [s, nid] of Object.entries(t.neighbors ?? {})) {
        if (nid !== tileId) n[Number(s)] = nid
      }
      return { ...t, neighbors: n }
    })
    const nextPorts = (config.ports ?? []).filter(p => p.tile_id !== tileId)
    setConfig({ ...config, tiles: cleanedTiles, ports: nextPorts })
    setActiveTileId(cleanedTiles[0]?.tile_id ?? null)
  }

  const linkTiles = () => {
    if (!config || !activeTile) return
    const side = ((connectSide % 6) + 6) % 6
    const targetId = connectTarget.trim()
    if (!targetId || targetId === activeTile.tile_id) return
    const target = tileById.get(targetId)
    if (!target) return

    const opp = oppositeSide(side)
    const nextTiles = config.tiles.map(t => {
      if (t.tile_id === activeTile.tile_id) {
        return { ...t, neighbors: { ...(t.neighbors ?? {}), [side]: targetId } }
      }
      if (t.tile_id === targetId) {
        return { ...t, neighbors: { ...(t.neighbors ?? {}), [opp]: activeTile.tile_id } }
      }
      return t
    })

    // Ports must live on coastal sides only. If we just linked a side, remove any port that sat there.
    const nextPorts = (config.ports ?? []).filter(p => {
      if (p.tile_id === activeTile.tile_id && p.side === side) return false
      if (p.tile_id === targetId && p.side === opp) return false
      return true
    })

    setConfig({ ...config, tiles: nextTiles, ports: nextPorts })
  }

  const unlinkSide = (side: number) => {
    if (!config || !activeTile) return
    const s = ((side % 6) + 6) % 6
    const neighborId = activeTile.neighbors?.[s]
    if (!neighborId) return
    const opp = oppositeSide(s)

    const nextTiles = config.tiles.map(t => {
      if (t.tile_id === activeTile.tile_id) {
        const n = { ...(t.neighbors ?? {}) }
        delete n[s]
        return { ...t, neighbors: n }
      }
      if (t.tile_id === neighborId) {
        const n = { ...(t.neighbors ?? {}) }
        if (n[opp] === activeTile.tile_id) delete n[opp]
        return { ...t, neighbors: n }
      }
      return t
    })
    setConfig({ ...config, tiles: nextTiles })
  }

  const togglePort = (side: number) => {
    if (!config || !activeTile) return
    const s = ((side % 6) + 6) % 6
    if ((activeTile.neighbors ?? {})[s]) return // not coastal
    setActivePortSide(s)
    const exists = (config.ports ?? []).some(p => p.tile_id === activeTile.tile_id && p.side === s)
    if (exists) {
      setConfig({
        ...config,
        ports: (config.ports ?? []).filter(p => !(p.tile_id === activeTile.tile_id && p.side === s)),
      })
    } else {
      setConfig({
        ...config,
        ports: [...(config.ports ?? []), { tile_id: activeTile.tile_id, side: s, ratio: 3, resource: null }],
      })
    }
  }

  const setActivePortField = (patch: Partial<MapTopologyPayload['ports'][number]>) => {
    if (!config || !activeTile) return
    const nextPorts = (config.ports ?? []).map(p => {
      if (p.tile_id === activeTile.tile_id && p.side === activePortSide) return { ...p, ...patch }
      return p
    })
    setConfig({ ...config, ports: nextPorts })
  }

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.header}>
          <div className={styles.title}>Topology Editor</div>
        </div>
        <div className={styles.hint}>Loading...</div>
      </div>
    )
  }

  if (!config) {
    return (
      <div className={styles.wrap}>
        <div className={styles.header}>
          <div className={styles.title}>Topology Editor</div>
        </div>
        <div className={styles.hint}>{error || 'No topology'}</div>
      </div>
    )
  }

  const activeCoastal = activeTile ? new Set(coastalSides(activeTile)) : new Set<number>()

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <div className={styles.title}>Topology Editor (host)</div>
        <div className={styles.btnRow}>
          <button className={styles.btn} type="button" onClick={addTile}>
            + Tile
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
        {(config.tiles ?? []).map(t => {
          const active = t.tile_id === activeTileId
          const c = coastalSides(t).length
          return (
            <button
              key={t.tile_id}
              type="button"
              className={`${styles.tile} ${active ? styles.tileActive : ''}`}
              onClick={() => setActiveTileId(t.tile_id)}
              title={t.tile_id}
            >
              <div className={styles.tileTop}>
                <span>{TERRAIN_LABELS[t.tile_type]}</span>
                <span>{t.token ?? '—'}</span>
              </div>
              <div className={styles.tileMeta}>
                {t.tile_id} {t.robber ? '🦹' : ''} · coastal {c}/6
              </div>
            </button>
          )
        })}
      </div>

      {activeTile && (
        <div className={styles.panel}>
          <div className={styles.row}>
            <div className={styles.label}>Tile</div>
            <div className={styles.hint}>
              <strong>{activeTile.tile_id}</strong>
              <button
                type="button"
                className={styles.dangerBtn}
                onClick={() => removeTile(activeTile.tile_id)}
                disabled={(config.tiles ?? []).length <= 1}
                title="Remove tile (will also remove links/ports)"
              >
                Remove
              </button>
            </div>
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Terrain</div>
            <select
              className={styles.select}
              value={activeTile.tile_type}
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
              value={activeTile.token ?? ''}
              onChange={e => setTileField({ token: e.target.value ? Number(e.target.value) : null })}
              placeholder="2-12 (blank for desert)"
            />
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Blocked</div>
            <input
              type="checkbox"
              checked={!!activeTile.robber}
              onChange={e => setTileField({ robber: e.target.checked })}
            />
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Link</div>
            <div className={styles.linkRow}>
              <select className={styles.select} value={connectSide} onChange={e => setConnectSide(Number(e.target.value))}>
                {Array.from({ length: 6 }).map((_, s) => (
                  <option key={s} value={s}>
                    side {s}
                  </option>
                ))}
              </select>
              <select className={styles.select} value={connectTarget} onChange={e => setConnectTarget(e.target.value)}>
                <option value="">target tile…</option>
                {(config.tiles ?? [])
                  .filter(t => t.tile_id !== activeTile.tile_id)
                  .map(t => (
                    <option key={t.tile_id} value={t.tile_id}>
                      {t.tile_id}
                    </option>
                  ))}
              </select>
              <button className={styles.btn} type="button" onClick={linkTiles}>
                Connect
              </button>
            </div>
            <div className={styles.hint}>
              Rule: `side` 连接会自动写入对方 `side+3`（对边）回连。连接后的边不再允许放 port。
            </div>
          </div>

          <div className={styles.row}>
            <div className={styles.label}>Edges</div>
            <div className={styles.edges}>
              {Array.from({ length: 6 }).map((_, s) => {
                const nid = activeTile.neighbors?.[s]
                const isCoastal = !nid
                return (
                  <div key={s} className={styles.edgeRow}>
                    <div className={styles.edgeSide}>side {s}</div>
                    <div className={styles.edgeVal}>
                      {nid ? (
                        <>
                          <span className={styles.edgeNeighbor}>{nid}</span>
                          <button className={styles.smallBtn} type="button" onClick={() => unlinkSide(s)}>
                            Unlink
                          </button>
                        </>
                      ) : (
                        <span className={styles.edgeCoastal}>coastal</span>
                      )}
                    </div>
                    <button
                      className={`${styles.smallBtn} ${styles.portBtn}`}
                      type="button"
                      onClick={() => togglePort(s)}
                      disabled={!isCoastal}
                      title={isCoastal ? 'Toggle port on this coastal side' : 'Ports only on coastal sides'}
                    >
                      Port
                    </button>
                  </div>
                )
              })}
            </div>
          </div>

          {activePort && (
            <>
              <div className={styles.row}>
                <div className={styles.label}>Port side</div>
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
                  onChange={e =>
                    setActivePortField({
                      resource: e.target.value ? (e.target.value as ResourceType) : null,
                    })
                  }
                >
                  <option value="">generic (3:1)</option>
                  {RESOURCES.map(r => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
              {!activeCoastal.has(activePortSide) && (
                <div className={styles.hint}>This port side is no longer coastal; save will auto-normalize.</div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

