"""
Router pour les endpoints de l'agent vocal et des transcriptions
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional

from ..db.database import get_db
from ..services.voice_agent_service import voice_agent_service, TranscriptEntry, Transcription, DebateQAEntry
from ..config import logger, settings
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class TranscriptionRequest(BaseModel):
    """Requête pour sauvegarder une transcription (envoyée par l'agent)"""
    session_id: str
    room_name: str
    transcript: List[dict]


class AppendEntryRequest(BaseModel):
    """Requête pour ajouter une entrée en temps réel (TTS retranscrit pendant l'appel)"""
    session_id: str
    room_name: str
    entry: dict  # {role, text, timestamp?}


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
async def save_transcription(request: TranscriptionRequest, db: AsyncSession = Depends(get_db)):
    """
    Sauvegarde une transcription de conversation (appelé par l'agent).
    """
    try:
        await voice_agent_service.save_transcription(
            db,
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


@router.post("/transcription/append", response_model=StatusResponse)
async def append_transcription_entry(request: AppendEntryRequest, db: AsyncSession = Depends(get_db)):
    """
    Ajoute une entrée de transcription en temps réel (pendant l'appel).
    Appelé par l'agent à chaque fois qu'un tour de parole (TTS ou STT) est produit.
    """
    try:
        await voice_agent_service.append_entry(
            db,
            session_id=request.session_id,
            room_name=request.room_name,
            entry=request.entry
        )
        return StatusResponse(
            status="success",
            message="Entry appended"
        )
    except Exception as e:
        logger.error(f"Error appending transcription entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error appending transcription entry: {str(e)}"
        )


@router.get("/transcription/{session_id}", response_model=TranscriptionResponse)
async def get_transcription(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Récupère la transcription d'une session (depuis la BDD).
    """
    transcription = await voice_agent_service.get_transcription(db, session_id)
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


class DebateQARequest(BaseModel):
    """Requête pour sauvegarder une paire question/réponse du débat"""
    session_id: str
    question_number: int
    question_text: str
    answer_text: Optional[str] = None


@router.post("/debate-qa", response_model=StatusResponse)
async def save_debate_qa(request: DebateQARequest, db: AsyncSession = Depends(get_db)):
    """
    Sauvegarde une paire question/réponse du débat (appelé par l'agent).
    """
    try:
        await voice_agent_service.save_debate_qa(
            db,
            session_id=request.session_id,
            question_number=request.question_number,
            question_text=request.question_text,
            answer_text=request.answer_text,
        )
        return StatusResponse(
            status="success",
            message=f"Debate QA #{request.question_number} saved"
        )
    except Exception as e:
        logger.error(f"Error saving debate QA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving debate QA: {str(e)}"
        )


@router.get("/debate-qa/{session_id}", response_model=List[DebateQAEntry])
async def get_debate_qa(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Récupère toutes les paires Q&A d'une session de débat.
    """
    try:
        return await voice_agent_service.get_debate_qa(db, session_id)
    except Exception as e:
        logger.error(f"Error fetching debate QA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching debate QA: {str(e)}"
        )


@router.delete("/transcription/{session_id}", response_model=StatusResponse)
async def delete_transcription(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    Supprime la transcription d'une session.
    """
    deleted = await voice_agent_service.delete_transcription(db, session_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transcription found for session {session_id}"
        )
    return StatusResponse(
        status="success",
        message=f"Transcription deleted for session {session_id}"
    )
