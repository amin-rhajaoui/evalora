"""
Router pour la gestion des sessions d'examen
"""
from fastapi import APIRouter, HTTPException
from typing import Dict
import uuid

from ..models.session import (
    Session, SessionCreate, SessionResponse,
    ExamPhase, PhaseTransition
)
from ..config import AVATARS, settings

router = APIRouter()

# Stockage en mémoire (à remplacer par une BDD en production)
sessions: Dict[str, Session] = {}


@router.post("", response_model=SessionResponse)
async def create_session(data: SessionCreate):
    """
    Crée une nouvelle session d'examen.

    - Enregistre le prénom et le niveau de l'étudiant
    - Associe l'avatar choisi (ou None pour mode sans avatar)
    - Prépare la session LiveKit et Tavus si configurés
    """
    session_id = str(uuid.uuid4())

    session = Session(
        id=session_id,
        student_name=data.student_name,
        level=data.level,
        avatar_id=data.avatar_id,
        document_id=data.document_id,
        current_phase=ExamPhase.CONSIGNES,
        livekit_room_name=f"evalora-{session_id}"
    )

    sessions[session_id] = session

    # Préparer les infos avatar
    avatar_info = None
    if data.avatar_id and data.avatar_id in AVATARS:
        avatar_info = AVATARS[data.avatar_id]

    return SessionResponse(
        id=session.id,
        student_name=session.student_name,
        level=session.level.value,
        avatar_id=session.avatar_id,
        avatar_info=avatar_info,
        document_id=session.document_id,
        current_phase=session.current_phase,
        livekit_token=session.livekit_token,
        livekit_url=settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None,
        tavus_conversation_url=session.tavus_conversation_url,
        created_at=session.created_at
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Récupère les informations d'une session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    session = sessions[session_id]
    avatar_info = None
    if session.avatar_id and session.avatar_id in AVATARS:
        avatar_info = AVATARS[session.avatar_id]

    return SessionResponse(
        id=session.id,
        student_name=session.student_name,
        level=session.level.value,
        avatar_id=session.avatar_id,
        avatar_info=avatar_info,
        document_id=session.document_id,
        current_phase=session.current_phase,
        livekit_token=session.livekit_token,
        livekit_url=settings.LIVEKIT_URL if settings.LIVEKIT_API_KEY else None,
        tavus_conversation_url=session.tavus_conversation_url,
        created_at=session.created_at
    )


@router.put("/{session_id}/document")
async def set_document(session_id: str, document_id: str):
    """Associe un document à la session"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    sessions[session_id].document_id = document_id
    return {"status": "ok", "document_id": document_id}


@router.post("/{session_id}/transition")
async def transition_phase(session_id: str, transition: PhaseTransition):
    """
    Transition vers une nouvelle phase de l'examen.

    Phases: CONSIGNES -> MONOLOGUE -> DEBAT -> FEEDBACK -> COMPLETED
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    session = sessions[session_id]

    # Enregistrer la durée de la phase précédente
    if transition.phase_duration:
        if session.current_phase == ExamPhase.MONOLOGUE:
            session.monologue_duration = transition.phase_duration
        elif session.current_phase == ExamPhase.DEBAT:
            session.debat_duration = transition.phase_duration

    # Mettre à jour la phase
    session.current_phase = transition.new_phase

    return {
        "status": "ok",
        "previous_phase": session.current_phase,
        "new_phase": transition.new_phase,
        "session_id": session_id
    }


@router.get("/{session_id}/phase")
async def get_current_phase(session_id: str):
    """Récupère la phase actuelle"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session non trouvée")

    session = sessions[session_id]
    return {
        "phase": session.current_phase,
        "monologue_duration": session.monologue_duration,
        "debat_duration": session.debat_duration
    }
