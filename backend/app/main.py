"""
Evalora - Chatbot FLE Backend
Point d'entrée FastAPI
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, logger
from .routers import session, documents, avatar, livekit, evaluation


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    settings.log_config_status()
    logger.info("Demarrage du serveur Evalora...")
    logger.info(f"Documentation API : http://localhost:8000/docs")
    yield
    # Shutdown
    logger.info("Arret du serveur Evalora...")


# Création de l'application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API pour le simulateur d'examen de production orale DU FLE",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion des routers
app.include_router(session.router, prefix="/api/session", tags=["Session"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(avatar.router, prefix="/api/avatar", tags=["Avatar"])
app.include_router(livekit.router, prefix="/api/livekit", tags=["LiveKit"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["Evaluation"])


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else "disabled"
    }


@app.get("/health")
async def health_check():
    """Vérification de santé"""
    livekit_ok = bool(settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET)
    tavus_ok = bool(settings.TAVUS_API_KEY)

    return {
        "status": "healthy",
        "services": {
            "livekit": {
                "configured": livekit_ok,
                "url": settings.LIVEKIT_URL if livekit_ok else None
            },
            "tavus": {
                "configured": tavus_ok,
                "url": settings.TAVUS_BASE_URL if tavus_ok else None
            }
        }
    }


# Point d'entrée pour uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
