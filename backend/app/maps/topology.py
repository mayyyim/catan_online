"""
Coordinate-free map topology.

This module defines a "topology-first" representation for maps:
- Tiles have stable ids and game properties (type/token/robber)
- Adjacency is expressed via side-based neighbor links (0-5)
- Ports attach to a tile id + side and must be on an open (coastal) side

For gameplay/rendering, we derive a temporary axial embedding (q,r) from the
topology using the same HEX_DIRECTIONS side indexing as the rest of the engine.
The derived coordinates are NOT persisted as part of the topology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.game.board import HEX_DIRECTIONS
from app.game.models import MapData, Port, Resource, Tile, TileType


TileId = str


@dataclass
class TopoTile:
    tile_id: TileId
    tile_type: TileType
    token: Optional[int] = None
    robber: bool = False
    # side -> neighbor tile_id
    neighbors: Dict[int, TileId] = field(default_factory=dict)


@dataclass
class TopoPort:
    tile_id: TileId
    side: int
    ratio: int = 3
    resource: Optional[Resource] = None


@dataclass
class MapTopology:
    map_id: str
    tiles: List[TopoTile] = field(default_factory=list)
    ports: List[TopoPort] = field(default_factory=list)


def _coastal_side(tile: TopoTile, side: int) -> bool:
    return (side % 6) not in {s % 6 for s in tile.neighbors.keys()}


def normalize_topology(topo: MapTopology) -> MapTopology:
    """
    Normalize topology in-place-ish:
    - enforce neighbor reciprocity using opposite side convention (s <-> (s+3)%6)
    - drop neighbor links to unknown tile ids
    - clamp sides to 0-5
    - ensure ports end up on coastal sides (if not, move to first coastal side)
    """
    by_id: Dict[TileId, TopoTile] = {t.tile_id: t for t in topo.tiles}

    # Normalize neighbor links
    for t in topo.tiles:
        cleaned: Dict[int, TileId] = {}
        for raw_side, nid in list(t.neighbors.items()):
            if nid not in by_id:
                continue
            side = int(raw_side) % 6
            cleaned[side] = nid
        t.neighbors = cleaned

    # Enforce reciprocity
    for t in topo.tiles:
        for side, nid in list(t.neighbors.items()):
            other = by_id.get(nid)
            if not other:
                continue
            opp = (int(side) + 3) % 6
            if other.neighbors.get(opp) != t.tile_id:
                other.neighbors[opp] = t.tile_id

    # Normalize ports: ensure coastal
    for p in topo.ports:
        p.side = int(p.side) % 6
        tile = by_id.get(p.tile_id)
        if not tile:
            continue
        if not _coastal_side(tile, p.side):
            coastal = [s for s in range(6) if _coastal_side(tile, s)]
            if coastal:
                p.side = coastal[0]

    return topo


def embed_topology_axial(topo: MapTopology) -> Dict[TileId, Tuple[int, int]]:
    """
    Derive axial coordinates (q,r) for each tile_id from topology.

    Convention: if A.neighbors[side] = B then
      coord[B] = coord[A] + HEX_DIRECTIONS[side]

    Raises ValueError if the graph produces a coordinate conflict.
    """
    by_id: Dict[TileId, TopoTile] = {t.tile_id: t for t in topo.tiles}
    if not by_id:
        return {}

    start = topo.tiles[0].tile_id
    coords: Dict[TileId, Tuple[int, int]] = {start: (0, 0)}
    queue: List[TileId] = [start]

    while queue:
        cur = queue.pop(0)
        cq, cr = coords[cur]
        tile = by_id[cur]
        for side, nid in tile.neighbors.items():
            dq, dr = HEX_DIRECTIONS[int(side) % 6]
            nq, nr = cq + dq, cr + dr
            if nid in coords:
                if coords[nid] != (nq, nr):
                    raise ValueError(
                        f"Topology coordinate conflict for tile {nid}: "
                        f"existing={coords[nid]} implied={(nq, nr)}"
                    )
                continue
            coords[nid] = (nq, nr)
            queue.append(nid)

    # Disconnected components: place them separated to avoid overlap
    # (still coordinate-free storage; this is only for rendering/runtime)
    placed = set(coords.keys())
    offset_q = 10
    for tid in by_id.keys():
        if tid in placed:
            continue
        coords[tid] = (offset_q, 0)
        offset_q += 10
        queue = [tid]
        placed.add(tid)
        while queue:
            cur = queue.pop(0)
            cq, cr = coords[cur]
            tile = by_id[cur]
            for side, nid in tile.neighbors.items():
                dq, dr = HEX_DIRECTIONS[int(side) % 6]
                nq, nr = cq + dq, cr + dr
                if nid in coords:
                    continue
                coords[nid] = (nq, nr)
                placed.add(nid)
                queue.append(nid)

    return coords


def topology_to_mapdata(topo: MapTopology) -> tuple[MapData, Dict[TileId, Tuple[int, int]]]:
    """
    Convert coordinate-free topology to runtime MapData by embedding axially.
    """
    topo = normalize_topology(topo)
    coords = embed_topology_axial(topo)

    tiles: List[Tile] = []
    for t in topo.tiles:
        q, r = coords.get(t.tile_id, (0, 0))
        tiles.append(Tile(q=q, r=r, tile_type=t.tile_type, token=t.token))

    ports: List[Port] = []
    for p in topo.ports:
        q, r = coords.get(p.tile_id, (0, 0))
        ports.append(
            Port(
                q=q,
                r=r,
                side=int(p.side) % 6,
                resource=p.resource,
                ratio=int(p.ratio),
            )
        )

    return MapData(map_id=topo.map_id, tiles=tiles, ports=ports), coords

