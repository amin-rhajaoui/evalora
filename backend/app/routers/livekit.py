"""
Router pour LiveKit (communication temps réel)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..config import settings
from ..services.livekit_service import LiveKitService

router = APIRouter()

# Singleton lazy pour éviter l'instanciation au niveau du module
# (qui peut déclencher un formatage automatique et une boucle de rechargement)
_livekit_service: Optional[LiveKitService] = None


def get_livekit_service() -> LiveKitService:
    """Retourne l'instance singleton de LiveKitService (lazy initialization)"""
    global _livekit_service
    if _livekit_service is None:
        _livekit_service = LiveKitService()
    return _livekit_service


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
    result = await get_livekit_service().create_room(request.session_id)

    # Vérifier que la room existe vraiment si elle a été créée
    room_verified = False
    if result.get("status") == "created" and settings.LIVEKIT_API_KEY:
        try:
            room_info = await get_livekit_service().get_room_info(result["room_name"])
            room_verified = room_info.get("exists", False)
        except Exception as e:
            # Si la vérification échoue, on continue quand même
            pass

    response = {
        "room_name": result["room_name"],
        "session_id": request.session_id,
        "status": result.get("status", "unknown"),
        "room_sid": result.get("room_sid"),
        "verified": room_verified if result.get("status") == "created" else None,
        "message": result.get("message", "" if settings.LIVEKIT_API_KEY else "LiveKit non configuré - mode simulation")
    }
    
    return response


@router.post("/token")
async def generate_token(request: TokenRequest):
    """
    Génère un token d'accès LiveKit pour un participant.

    PLACEHOLDER: Retourne un token vide si LiveKit n'est pas configuré.
    """
    token = await get_livekit_service().generate_token(
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
    result = await get_livekit_service().delete_room(room_name)
    return result


@router.get("/room/{room_name}")
async def get_room_info(room_name: str):
    """Vérifie si une room LiveKit existe et retourne ses informations"""
    info = await get_livekit_service().get_room_info(room_name)
    return info


@router.get("/room/{room_name}/participants")
async def get_participants(room_name: str):
    """Récupère la liste des participants dans une room"""
    participants = await get_livekit_service().get_participants(room_name)
    return {
        "room_name": room_name,
        "participants": participants
    }
