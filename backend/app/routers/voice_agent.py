"""
Router pour les endpoints de l'agent vocal et des transcriptions
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from ..services.voice_agent_service import voice_agent_service, TranscriptEntry, Transcription
from ..config import logger, settings

router = APIRouter()


class TranscriptionRequest(BaseModel):
    """Requête pour sauvegarder une transcription (envoyée par l'agent)"""
    session_id: str
    room_name: str
    transcript: List[dict]


class TranscriptionResponse(BaseModel):
    """Réponse avec la transcription"""
    session_id: str
    transcript: List[TranscriptEntry]
    created_at: str


class StatusResponse(BaseModel):
    """Réponse de statut"""
    status: str
    message: str


@router.get("/status")
async def get_voice_agent_status():
    """
    Vérifie si l'agent vocal est configuré.

    Returns:
        Statut de configuration de l'agent vocal
    """
    openai_configured = bool(settings.OPENAI_API_KEY)
    livekit_configured = bool(settings.LIVEKIT_API_KEY and settings.LIVEKIT_API_SECRET)

    return {
        "configured": openai_configured and livekit_configured,
        "openai_configured": openai_configured,
        "livekit_configured": livekit_configured,
        "message": "Voice agent ready" if (openai_configured and livekit_configured) else "Missing API keys"
    }


@router.post("/transcription", response_model=StatusResponse)
async def save_transcription(request: TranscriptionRequest):
    """
    Sauvegarde une transcription de conversation (appelé par l'agent).

    Args:
        request: Données de transcription

    Returns:
        Statut de la sauvegarde
    """
    try:
        voice_agent_service.save_transcription(
            session_id=request.session_id,
            room_name=request.room_name,
            transcript=request.transcript
        )

        return StatusResponse(
            status="success",
            message=f"Transcription saved with {len(request.transcript)} entries"
        )

    except Exception as e:
        logger.error(f"Error saving transcription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving transcription: {str(e)}"
        )


@router.get("/transcription/{session_id}", response_model=TranscriptionResponse)
async def get_transcription(session_id: str):
    """
    Récupère la transcription d'une session.

    Args:
        session_id: ID de la session d'examen

    Returns:
        Transcription de la conversation
    """
    transcription = voice_agent_service.get_transcription(session_id)

    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transcription found for session {session_id}"
        )

    return TranscriptionResponse(
        session_id=transcription.session_id,
        transcript=transcription.transcript,
        created_at=transcription.created_at
    )


@router.delete("/transcription/{session_id}", response_model=StatusResponse)
async def delete_transcription(session_id: str):
    """
    Supprime la transcription d'une session.

    Args:
        session_id: ID de la session d'examen

    Returns:
        Statut de la suppression
    """
    deleted = voice_agent_service.delete_transcription(session_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transcription found for session {session_id}"
        )

    return StatusResponse(
        status="success",
        message=f"Transcription deleted for session {session_id}"
    )
