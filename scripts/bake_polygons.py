"""
Bake Natural Earth country polygons into per-slug JSON files.

Usage:
    python scripts/bake_polygons.py                 # bake all 28 slugs
    python scripts/bake_polygons.py china           # bake only china (MVP)
    python scripts/bake_polygons.py china japan     # bake a subset

Downloads Natural Earth 1:50m admin_0_countries to
    backend/app/maps/data/ne_50m_admin_0_countries/
and writes simplified polygons to
    backend/app/maps/data/polygons/{slug}.json
"""

from __future__ import annotations

import io
import json
import math
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "backend" / "app" / "maps" / "data"
NE_DIR = DATA_DIR / "ne_50m_admin_0_countries"
POLY_DIR = DATA_DIR / "polygons"
NE_URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"

# ---------------------------------------------------------------------------
# Ramer-Douglas-Peucker simplification (stdlib only)
# ---------------------------------------------------------------------------

def _perp_distance(p, a, b) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def rdp(points, epsilon: float):
    """Ramer-Douglas-Peucker. Input: list of (x,y). Returns simplified list."""
    if len(points) < 3:
        return list(points)
    # iterative to avoid recursion limit
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 <= i0 + 1:
            continue
        a, b = points[i0], points[i1]
        dmax = 0.0
        idx = -1
        for i in range(i0 + 1, i1):
            d = _perp_distance(points[i], a, b)
            if d > dmax:
                dmax = d
                idx = i
        if dmax > epsilon and idx != -1:
            keep[idx] = True
            stack.append((i0, idx))
            stack.append((idx, i1))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring, epsilon: float, target_min: int = 8):
    """Simplify a ring but keep at least target_min points if possible."""
    eps = epsilon
    simplified = rdp(ring, eps)
    # If too aggressive, back off
    for _ in range(6):
        if len(simplified) >= target_min:
            break
        eps *= 0.5
        simplified = rdp(ring, eps)
    return simplified


# ---------------------------------------------------------------------------
# Natural Earth download
# ---------------------------------------------------------------------------

def ensure_natural_earth() -> Path:
    shp = NE_DIR / "ne_50m_admin_0_countries.shp"
    if shp.exists():
        return shp
    NE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[download] {NE_URL}")
    req = urllib.request.Request(NE_URL, headers={"User-Agent": "catan-online/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        blob = resp.read()
    print(f"[download] got {len(blob)} bytes")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            # flatten
            base = os.path.basename(name)
            if not base:
                continue
            out = NE_DIR / base
            with zf.open(name) as src, open(out, "wb") as dst:
                dst.write(src.read())
    if not shp.exists():
        raise RuntimeError(f"Shapefile not found after extract: {shp}")
    return shp


# ---------------------------------------------------------------------------
# Shapefile reading -> per-country polygons
# ---------------------------------------------------------------------------

def _shape_to_polygons(shape):
    """Convert a pyshp Shape (polygon) to list of {'exterior','holes'} rings.

    Natural Earth polygons use clockwise exterior + CCW holes convention,
    but we are permissive: every part is its own polygon with no holes.
    This is sufficient for MVP raster masking of country outlines.
    """
    pts = [tuple(p) for p in shape.points]
    parts = list(shape.parts) + [len(pts)]
    rings = []
    for i in range(len(parts) - 1):
        ring = pts[parts[i]:parts[i + 1]]
        if len(ring) >= 4:
            rings.append(ring)
    return rings


def _iter_country_records(reader):
    fields = [f[0] for f in reader.fields[1:]]  # drop DeletionFlag
    for sr in reader.shapeRecords():
        rec = dict(zip(fields, list(sr.record)))
        yield rec, sr.shape


# ---------------------------------------------------------------------------
# Slug definitions
#   Each slug maps to: list of Natural Earth NAME/ADMIN matches,
#   plus an optional filter that picks specific parts (e.g. biggest N).
# ---------------------------------------------------------------------------

# NAME match -> slug mappings (single country slugs)
SIMPLE_SLUGS = {
    "china":       ["China", "Taiwan"],
    "japan":       ["Japan"],
    "usa":         ["United States of America"],
    "uk":          ["United Kingdom", "Ireland"],
    "australia":   ["Australia"],
    "brazil":      ["Brazil"],
    "antarctica":  ["Antarctica"],
    "india":       ["India"],
    "canada":      ["Canada"],
    "russia":      ["Russia"],
    "egypt":       ["Egypt"],
    "mexico":      ["Mexico"],
    "korea":       ["North Korea", "South Korea"],
    "indonesia":   ["Indonesia"],
    "new_zealand": ["New Zealand"],
    "france":      ["France"],
    "germany":     ["Germany"],
    "argentina":   ["Argentina"],
    "south_africa":["South Africa"],
    "italy":       ["Italy"],
    "spain":       ["Spain"],
    "turkey":      ["Turkey"],
    "vietnam":     ["Vietnam"],
}

# Multi-country unions
SCANDINAVIA = ["Norway", "Sweden", "Finland", "Denmark", "Iceland"]
EUROPE = [
    "France", "Germany", "Italy", "Spain", "Portugal", "Belgium",
    "Netherlands", "Luxembourg", "Switzerland", "Austria", "Poland",
    "Czechia", "Slovakia", "Hungary", "Slovenia", "Croatia",
    "Bosnia and Herzegovina", "Serbia", "Montenegro", "Kosovo",
    "Albania", "North Macedonia", "Greece", "Bulgaria", "Romania",
    "Moldova", "Ukraine", "Belarus", "Lithuania", "Latvia", "Estonia",
    "Finland", "Sweden", "Norway", "Denmark", "Iceland", "Ireland",
    "United Kingdom",
]
AFRICA_XL = [
    "Algeria","Angola","Benin","Botswana","Burkina Faso","Burundi","Cameroon",
    "Central African Republic","Chad","Democratic Republic of the Congo",
    "Republic of the Congo","Djibouti","Egypt","Equatorial Guinea","Eritrea",
    "Eswatini","Ethiopia","Gabon","Gambia","Ghana","Guinea","Guinea-Bissau",
    "Ivory Coast","Kenya","Lesotho","Liberia","Libya","Madagascar","Malawi",
    "Mali","Mauritania","Morocco","Mozambique","Namibia","Niger","Nigeria",
    "Rwanda","Senegal","Sierra Leone","Somalia","South Africa","South Sudan",
    "Sudan","Tanzania","Togo","Tunisia","Uganda","Western Sahara","Zambia","Zimbabwe",
    "Cape Verde","Comoros","Mauritius","Seychelles","Sao Tome and Principe",
]
EURASIA_XL = EUROPE + [
    "Russia","China","Japan","North Korea","South Korea","Mongolia","Kazakhstan",
    "Uzbekistan","Turkmenistan","Tajikistan","Kyrgyzstan","Afghanistan","Pakistan",
    "India","Nepal","Bhutan","Bangladesh","Myanmar","Thailand","Laos","Vietnam",
    "Cambodia","Malaysia","Singapore","Indonesia","Philippines","Taiwan",
    "Iran","Iraq","Syria","Turkey","Lebanon","Israel","Palestine","Jordan",
    "Saudi Arabia","Yemen","Oman","United Arab Emirates","Qatar","Bahrain",
    "Kuwait","Georgia","Armenia","Azerbaijan",
]
AMERICAS_XL = [
    "Canada","United States of America","Mexico","Guatemala","Belize","Honduras",
    "El Salvador","Nicaragua","Costa Rica","Panama","Cuba","Jamaica","Haiti",
    "Dominican Republic","Bahamas","Puerto Rico","Trinidad and Tobago",
    "Colombia","Venezuela","Guyana","Suriname","French Guiana","Ecuador","Peru",
    "Bolivia","Brazil","Paraguay","Uruguay","Argentina","Chile",
]

UNION_SLUGS = {
    "europe":      EUROPE,
    "scandinavia": SCANDINAVIA,
    "africa_xl":   AFRICA_XL,
    "eurasia_xl":  EURASIA_XL,
    "americas_xl": AMERICAS_XL,
}

XL_SLUGS = {"africa_xl", "eurasia_xl", "americas_xl", "europe", "antarctica", "russia"}


def _name_matches(rec, names):
    n = rec.get("NAME") or rec.get("ADMIN") or ""
    n_long = rec.get("NAME_LONG") or ""
    adm = rec.get("ADMIN") or ""
    target = {x.lower() for x in names}
    return (n.lower() in target) or (n_long.lower() in target) or (adm.lower() in target)


def collect_rings_for(reader, names):
    """Return list of rings (list of (lon,lat)) for all matching countries."""
    out = []
    for rec, shape in _iter_country_records(reader):
        if _name_matches(rec, names):
            out.extend(_shape_to_polygons(shape))
    return out


def _ring_area(ring):
    # signed area (shoelace); absolute value used for sorting
    s = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        s += x1 * y2 - x2 * y1
    return abs(s) * 0.5


def _pretty_name(slug: str) -> str:
    specials = {
        "usa": "USA", "uk": "UK", "new_zealand": "New Zealand",
        "south_africa": "South Africa", "africa_xl": "Africa XL",
        "eurasia_xl": "Eurasia XL", "americas_xl": "Americas XL",
    }
    if slug in specials:
        return specials[slug]
    return slug.replace("_", " ").title()


def bake_slug(reader, slug: str) -> dict:
    if slug in SIMPLE_SLUGS:
        names = SIMPLE_SLUGS[slug]
    elif slug in UNION_SLUGS:
        names = UNION_SLUGS[slug]
    else:
        raise KeyError(f"unknown slug: {slug}")

    rings = collect_rings_for(reader, names)
    if not rings:
        raise RuntimeError(f"no rings found for {slug} (names={names[:3]}...)")

    # simplification tolerance: coarser for XL/continent maps
    is_xl = slug in XL_SLUGS or slug in UNION_SLUGS
    eps = 0.9 if is_xl else 0.5

    # Sort by area desc so biggest landmasses come first.
    rings.sort(key=_ring_area, reverse=True)

    # Drop tiny outlying islands: keep up to N largest, and only those above
    # a fraction of the largest area.
    max_polys = 60 if is_xl else 8
    if rings:
        biggest = _ring_area(rings[0])
        min_area = biggest * (0.001 if is_xl else 0.003)
        rings = [r for r in rings if _ring_area(r) >= min_area][:max_polys]

    simplified = []
    for r in rings:
        s = simplify_ring(r, eps)
        if len(s) >= 4:
            simplified.append(s)

    polygons = [{"exterior": [[round(x, 4), round(y, 4)] for (x, y) in r], "holes": []}
                for r in simplified]

    size = "xl" if is_xl else "standard"
    return {
        "slug": slug,
        "name": _pretty_name(slug),
        "size": size,
        "biome_hints": {},
        "polygons": polygons,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_SLUGS = list(SIMPLE_SLUGS.keys()) + list(UNION_SLUGS.keys())


def main(argv):
    try:
        import shapefile  # pyshp
    except ImportError:
        print("ERROR: pyshp not installed. Run: backend/.venv/bin/pip install pyshp",
              file=sys.stderr)
        return 2

    shp = ensure_natural_earth()
    print(f"[shapefile] {shp} ({shp.stat().st_size} bytes)")

    reader = shapefile.Reader(str(shp))
    print(f"[shapefile] {len(reader)} records, fields="
          f"{[f[0] for f in reader.fields[1:]][:6]}...")

    POLY_DIR.mkdir(parents=True, exist_ok=True)

    targets = argv[1:] if len(argv) > 1 else ALL_SLUGS
    ok, fail = [], []
    for slug in targets:
        try:
            data = bake_slug(reader, slug)
            out = POLY_DIR / f"{slug}.json"
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2))
            vcounts = [len(p["exterior"]) for p in data["polygons"]]
            print(f"[ok]   {slug:14s} -> {out.name}  polys={len(vcounts)} verts={vcounts}")
            ok.append(slug)
        except Exception as e:  # noqa: BLE001
            print(f"[fail] {slug:14s} -> {type(e).__name__}: {e}")
            fail.append((slug, str(e)))

    print()
    print(f"Baked {len(ok)}/{len(targets)} slugs OK.")
    if fail:
        print("Failures:")
        for s, e in fail:
            print(f"  - {s}: {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
