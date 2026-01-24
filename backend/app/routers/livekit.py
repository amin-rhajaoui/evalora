"""
Router pour LiveKit (communication temps réel)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..config import settings
from ..services.livekit_service import LiveKitService

router = APIRouter()
livekit_service = LiveKitService()


class RoomRequest(BaseModel):
    session_id: str
    participant_name: str


class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    can_publish: bool = True
    can_subscribe: bool = True


@router.get("/status")
async def livekit_status():
    """Vérifie si LiveKit est configuré"""
    return {
        "configured": settings.LIVEKIT_API_KEY is not None,
        "url": settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None
    }


@router.post("/room")
async def create_room(request: RoomRequest):
    """
    Crée une room LiveKit pour la session d'examen.

    PLACEHOLDER: Retourne des données mock si LiveKit n'est pas configuré.
    """
    result = await livekit_service.create_room(request.session_id)

    return {
        "room_name": result["room_name"],
        "session_id": request.session_id,
        "status": "created" if settings.LIVEKIT_API_KEY else "placeholder",
        "message": "" if settings.LIVEKIT_API_KEY else "LiveKit non configuré - mode simulation"
    }


@router.post("/token")
async def generate_token(request: TokenRequest):
    """
    Génère un token d'accès LiveKit pour un participant.

    PLACEHOLDER: Retourne un token vide si LiveKit n'est pas configuré.
    """
    token = await livekit_service.generate_token(
        room_name=request.room_name,
        participant_name=request.participant_name,
        can_publish=request.can_publish,
        can_subscribe=request.can_subscribe
    )

    return {
        "token": token,
        "room_name": request.room_name,
        "participant_name": request.participant_name,
        "ws_url": settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None,
        "configured": settings.LIVEKIT_API_KEY is not None
    }


@router.delete("/room/{room_name}")
async def delete_room(room_name: str):
    """Supprime une room LiveKit"""
    result = await livekit_service.delete_room(room_name)
    return result


@router.get("/room/{room_name}/participants")
async def get_participants(room_name: str):
    """Récupère la liste des participants dans une room"""
    participants = await livekit_service.get_participants(room_name)
    return {
        "room_name": room_name,
        "participants": participants
    }
