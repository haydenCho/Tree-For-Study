"""FastAPI application entry point.

All routes live under /api so the frontend uses a single same-origin base
(VITE_API_BASE_URL=/api), proxied by Vite in dev and Caddy in production.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Tree for Study API", version="0.0.0")

# Same-origin in production (Caddy) / dev (Vite proxy); CORS allows a direct
# cross-origin frontend only for local convenience.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")


@app.get("/api")
async def root() -> dict:
    return {"service": "tree-for-study", "status": "ok"}
