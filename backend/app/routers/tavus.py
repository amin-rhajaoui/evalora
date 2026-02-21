"""
Router pour l'intégration Tavus (avatar vidéo conversationnel)
"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from ..config import settings
from ..db.database import get_db
from ..db.models import ExamSession
from .avatar import get_phase1_sequences

logger = logging.getLogger("evalora.tavus")

router = APIRouter()

TAVUS_API_BASE = "https://tavusapi.com/v2"

# Mapping avatar_id → Tavus persona_id
TAVUS_PERSONAS = {
    "clea": "p7bd3f982ea9",
    "alex": "p9577cc5b0a7",
    "karim": "p8ae2eacdd84",
    "claire": "p44060ccef7d",
}


class TavusStartRequest(BaseModel):
    avatar_id: str
    student_name: str
    document_title: str = ""


@router.post("/{session_id}/start")
async def start_tavus_conversation(
    session_id: str,
    data: TavusStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crée une conversation Tavus et sauvegarde le conversation_id en BDD."""
    if not settings.TAVUS_API_KEY:
        raise HTTPException(status_code=503, detail="Tavus API key not configured")

    # Vérifier que la session existe
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Résoudre le persona_id
    persona_id = TAVUS_PERSONAS.get(data.avatar_id)
    if not persona_id:
        raise HTTPException(status_code=400, detail=f"Unknown avatar_id: {data.avatar_id}")

    # Construire le greeting avec les consignes complètes
    sequences = get_phase1_sequences(data.avatar_id, data.student_name)
    if sequences:
        consignes_text = " ".join(seq["text"] for seq in sequences)
    else:
        consignes_text = f"Bonjour {data.student_name}, bienvenue à votre examen."

    # Appeler l'API Tavus pour créer la conversation
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TAVUS_API_BASE}/conversations",
                headers={
                    "x-api-key": settings.TAVUS_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "persona_id": persona_id,
                    "custom_greeting": consignes_text,
                    "properties": {
                        "max_call_duration": 2400,
                    },
                },
                timeout=15.0,
            )

            if response.status_code not in (200, 201):
                logger.error(f"Tavus API error: {response.status_code} {response.text}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Tavus API error: {response.status_code}",
                )

            tavus_data = response.json()
            conversation_id = tavus_data.get("conversation_id", "")
            conversation_url = tavus_data.get("conversation_url", "")

    except httpx.RequestError as e:
        logger.error(f"Tavus API request error: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Tavus API")

    # Sauvegarder le conversation_id en BDD
    session.tavus_conversation_id = conversation_id
    await db.commit()

    logger.info(f"Tavus conversation started: {conversation_id} for session {session_id}")

    return {
        "conversation_id": conversation_id,
        "conversation_url": conversation_url,
        "status": "active",
    }


@router.delete("/{session_id}/end")
async def end_tavus_conversation(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Termine la conversation Tavus associée à la session."""
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    conversation_id = session.tavus_conversation_id
    if not conversation_id:
        return {"status": "no_conversation", "session_id": session_id}

    # Appeler l'API Tavus pour terminer la conversation
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{TAVUS_API_BASE}/conversations/{conversation_id}",
                headers={
                    "x-api-key": settings.TAVUS_API_KEY,
                },
                timeout=10.0,
            )

            if response.status_code not in (200, 204):
                logger.warning(f"Tavus end conversation error: {response.status_code}")

    except httpx.RequestError as e:
        logger.warning(f"Tavus API request error on end: {e}")

    # Nettoyer le conversation_id en BDD
    session.tavus_conversation_id = None
    await db.commit()

    logger.info(f"Tavus conversation ended: {conversation_id} for session {session_id}")

    return {"status": "ended", "session_id": session_id}
