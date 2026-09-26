from __future__ import annotations

from fastapi import FastAPI
from app.routes.context import router as context_router
from app.routes.health import router as health_router
from app.routes.metadata import router as metadata_router
from app.routes.reply import router as reply_router
from app.routes.tick import router as tick_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Magicpin Vera AI Bot",
    description="Baseline Vera AI Bot implementation for Magicpin Vera AI Challenge",
    version="1.0.0"
)

# Enable CORS for public API access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(health_router)
app.include_router(metadata_router)
app.include_router(context_router)
app.include_router(tick_router)
app.include_router(reply_router)


@app.get("/")
async def root():
    return {
        "service": "Magicpin Vera AI Bot",
        "status": "online",
        "healthz": "/v1/healthz",
        "metadata": "/v1/metadata",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
