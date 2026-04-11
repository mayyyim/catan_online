"""
Catan Online — FastAPI backend
Run with: uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.rooms import router as rooms_router
from app.routers.websocket import router as ws_router
from app.routers.auth import router as auth_router
from app.routers.stats import router as stats_router


app = FastAPI(
    title="Catan Online API",
    version="1.0.0",
    description="Real-time multiplayer Catan — HTTP room management + WebSocket game play",
)

# CORS: allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(auth_router, prefix="/auth")
app.include_router(rooms_router)
app.include_router(ws_router)
app.include_router(stats_router)


@app.on_event("startup")
def startup():
    from app.database import init_db
    init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/maps")
async def list_maps():
    """Return all static map summaries (tile coords + terrain, no tokens)."""
    from app.maps.definitions import MAP_REGISTRY
    result = []
    for map_id, fn in MAP_REGISTRY.items():
        data = fn()
        result.append({
            "map_id": map_id,
            "size": "large" if len(data.tiles) > 20 else "standard",
            "tiles": [
                {"q": t.q, "r": t.r, "tile_type": t.tile_type.value}
                for t in data.tiles
            ],
        })
    return {"maps": [{"map_id": "random", "size": "standard", "tiles": []}] + result}


@app.get("/maps/{map_id}")
async def get_map_detail(map_id: str):
    """Return full map data: tiles (with tokens) + ports."""
    from fastapi import HTTPException
    from app.maps.definitions import get_static_map
    if map_id == "random":
        raise HTTPException(status_code=404, detail="Random map has no static definition")
    try:
        data = get_static_map(map_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "map_id": map_id,
        "size": "large" if len(data.tiles) > 20 else "standard",
        "tiles": [t.to_dict() for t in data.tiles],
        "ports": [p.to_dict() for p in data.ports],
    }
