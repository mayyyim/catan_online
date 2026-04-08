"""
Catan Online — FastAPI backend
Run with: uvicorn app.main:app --host 0.0.0.0 --port 8080
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.rooms import router as rooms_router
from app.routers.websocket import router as ws_router


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
app.include_router(rooms_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/maps")
async def list_maps():
    """List all available map IDs."""
    return {
        "maps": [
            "random",
            "china", "japan", "usa", "europe", "uk",
            "australia", "brazil", "antarctica",
            "india", "canada", "russia", "egypt", "mexico",
            "korea", "indonesia", "new_zealand", "france", "germany",
        ]
    }
