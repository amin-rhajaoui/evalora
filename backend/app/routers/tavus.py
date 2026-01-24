"""
Router pour la gestion des conversations Tavus
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..services.tavus_service import TavusService
from ..config import AVATARS, settings

router = APIRouter()

# Singleton lazy pour éviter l'instanciation au niveau du module
_tavus_service: Optional[TavusService] = None


def get_tavus_service() -> TavusService:
    """Retourne l'instance singleton de TavusService (lazy initialization)"""
    global _tavus_service
    if _tavus_service is None:
        _tavus_service = TavusService()
    return _tavus_service


class ConversationRequest(BaseModel):
    session_id: str
    avatar_id: str
    conversation_name: Optional[str] = None
    callback_url: Optional[str] = None


class ConversationResponse(BaseModel):
    conversation_id: Optional[str] = None
    conversation_url: Optional[str] = None
    status: str
    message: str


@router.get("/status")
async def tavus_status():
    """Vérifie si Tavus est configuré"""
    return {
        "configured": settings.TAVUS_API_KEY is not None,
        "base_url": settings.TAVUS_BASE_URL if settings.TAVUS_API_KEY else None
    }


@router.get("/replicas")
async def list_replicas():
    """
    Liste les replicas disponibles pour le compte Tavus.
    
    Utile pour vérifier les IDs de replicas valides.
    """
    result = await get_tavus_service().list_replicas()
    return result


@router.post("/conversation", response_model=ConversationResponse)
async def create_conversation(request: ConversationRequest):
    """
    Crée une conversation Tavus pour une session.
    
    Utilise le replica_id et persona_id de l'avatar sélectionné.
    """
    # Vérifier que l'avatar existe
    if request.avatar_id not in AVATARS:
        raise HTTPException(status_code=404, detail="Avatar non trouvé")
    
    avatar = AVATARS[request.avatar_id]
    replica_id = avatar.get("tavus_replica_id")
    persona_id = avatar.get("tavus_persona_id")
    
    # Vérifier que l'avatar a les IDs Tavus configurés
    if not replica_id:
        raise HTTPException(
            status_code=400,
            detail=f"L'avatar {request.avatar_id} n'a pas de tavus_replica_id configuré"
        )
    
    if not persona_id:
        raise HTTPException(
            status_code=400,
            detail=f"L'avatar {request.avatar_id} n'a pas de tavus_persona_id configuré"
        )
    
    # Générer un nom de conversation si non fourni
    conversation_name = request.conversation_name or f"Session {request.session_id}"
    
    # Créer la conversation
    result = await get_tavus_service().create_conversation(
        replica_id=replica_id,
        persona_id=persona_id,
        conversation_name=conversation_name,
        callback_url=request.callback_url
    )
    
    return ConversationResponse(
        conversation_id=result.get("conversation_id"),
        conversation_url=result.get("conversation_url"),
        status=result.get("status", "unknown"),
        message=result.get("message", "")
    )
