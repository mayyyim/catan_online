"""
Static map definitions for all 28 Catan maps.

This is now a thin wrapper over `app.maps.rasterizer`, which generates maps
from polygon data in `backend/app/maps/data/polygons/<slug>.json`.

Historical note: the file used to contain hand-placed `_tile(q, r, ...)` lists
for every country. That approach didn't scale — see `logs/map_rasterizer_design.md`
for the pivot rationale.
"""

from typing import Callable, Dict

from app.game.models import MapData
from app.maps.rasterizer import build_map as _build_map


# Registry of all supported map slugs. Each entry lazily builds the map from
# its polygon file when called; cached on first build.
_MAP_CACHE: Dict[str, MapData] = {}


def _cached_builder(slug: str) -> Callable[[], MapData]:
    def build() -> MapData:
        if slug not in _MAP_CACHE:
            _MAP_CACHE[slug] = _build_map(slug)
        return _MAP_CACHE[slug]
    return build


# All 28 supported map slugs. Keep order stable for /maps API output.
_SLUGS = [
    # Standard maps (25)
    "china", "japan", "usa", "europe", "uk",
    "australia", "brazil", "antarctica", "india", "canada",
    "russia", "egypt", "mexico", "korea", "indonesia",
    "new_zealand", "france", "germany", "argentina", "south_africa",
    "italy", "scandinavia", "spain", "turkey", "vietnam",
    # XL maps (3)
    "africa_xl", "eurasia_xl", "americas_xl",
]


MAP_REGISTRY: Dict[str, Callable[[], MapData]] = {
    slug: _cached_builder(slug) for slug in _SLUGS
}


def get_static_map(map_id: str) -> MapData:
    fn = MAP_REGISTRY.get(map_id)
    if fn is None:
        raise ValueError(f"Unknown map: {map_id}")
    return fn()
