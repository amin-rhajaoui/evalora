"""
Router pour la gestion des sessions d'examen
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.session import (
    SessionCreate, SessionResponse,
    ExamPhase, PhaseTransition
)
from ..config import AVATARS, settings
from ..db.database import get_db
from ..db.models import ExamSession

router = APIRouter()
logger = logging.getLogger("evalora.session")


@router.post("", response_model=SessionResponse)
async def create_session(data: SessionCreate, db: AsyncSession = Depends(get_db)):
    """
    Crée une nouvelle session d'examen.
    """
    session_id = str(uuid.uuid4())
    room_name = f"evalora-{session_id}"

    session = ExamSession(
        id=session_id,
        student_name=data.student_name,
        level=data.level.value,
        avatar_id=data.avatar_id,
        document_id=data.document_id,
        current_phase=ExamPhase.CONSIGNES.value,
        livekit_room_name=room_name,
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    avatar_info = None
    if data.avatar_id and data.avatar_id in AVATARS:
        avatar_info = AVATARS[data.avatar_id]

    return SessionResponse(
        id=session.id,
        student_name=session.student_name,
        level=session.level,
        avatar_id=session.avatar_id,
        avatar_info=avatar_info,
        document_id=session.document_id,
        current_phase=ExamPhase(session.current_phase),
        livekit_url=settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None,
        created_at=session.created_at,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère les informations d'une session"""
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    avatar_info = None
    if session.avatar_id and session.avatar_id in AVATARS:
        avatar_info = AVATARS[session.avatar_id]

    return SessionResponse(
        id=session.id,
        student_name=session.student_name,
        level=session.level,
        avatar_id=session.avatar_id,
        avatar_info=avatar_info,
        document_id=session.document_id,
        current_phase=ExamPhase(session.current_phase),
        livekit_url=settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None,
        created_at=session.created_at,
    )


@router.put("/{session_id}/document")
async def set_document(session_id: str, document_id: str, db: AsyncSession = Depends(get_db)):
    """Associe un document à la session"""
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    session.document_id = document_id
    await db.commit()
    return {"status": "ok", "document_id": document_id}


@router.post("/{session_id}/transition")
async def transition_phase(session_id: str, transition: PhaseTransition, db: AsyncSession = Depends(get_db)):
    """
    Transition vers une nouvelle phase de l'examen.

    Phases: CONSIGNES -> MONOLOGUE -> DEBAT -> FEEDBACK -> COMPLETED
    """
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    previous_phase = session.current_phase

    # Enregistrer la durée de la phase précédente
    if transition.phase_duration:
        if previous_phase == ExamPhase.MONOLOGUE.value:
            session.monologue_duration = transition.phase_duration
        elif previous_phase == ExamPhase.DEBAT.value:
            session.debat_duration = transition.phase_duration

    session.current_phase = transition.new_phase.value
    session.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "status": "ok",
        "previous_phase": previous_phase,
        "new_phase": transition.new_phase,
        "session_id": session_id,
    }


@router.get("/{session_id}/phase")
async def get_current_phase(session_id: str, db: AsyncSession = Depends(get_db)):
    """Récupère la phase actuelle"""
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    return {
        "phase": session.current_phase,
        "monologue_duration": session.monologue_duration,
        "debat_duration": session.debat_duration,
    }
