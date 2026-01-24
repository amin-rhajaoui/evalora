"""
Router pour la gestion des sessions d'examen
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Optional
import uuid
import logging

from ..models.session import (
    Session, SessionCreate, SessionResponse,
    ExamPhase, PhaseTransition
)
from ..config import AVATARS, settings
from ..services.tavus_service import TavusService

router = APIRouter()
logger = logging.getLogger("evalora.session")

# Stockage en mémoire (à remplacer par une BDD en production)
sessions: Dict[str, Session] = {}


@router.post("", response_model=SessionResponse)
async def create_session(data: SessionCreate):
    """
    Crée une nouvelle session d'examen.

    - Enregistre le prénom et le niveau de l'étudiant
    - Associe l'avatar choisi (ou None pour mode sans avatar)
    - Prépare la session LiveKit (room, token) si configuré
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
        
        # Créer la conversation Tavus si l'avatar a les IDs configurés
        replica_id = avatar_info.get("tavus_replica_id")
        persona_id = avatar_info.get("tavus_persona_id")
        
        if replica_id and persona_id:
            try:
                tavus_service = TavusService()
                if tavus_service.is_configured:
                    conversation_result = await tavus_service.create_conversation(
                        replica_id=replica_id,
                        persona_id=persona_id,
                        conversation_name=f"Session {session_id} - {data.student_name}"
                    )
                    
                    if conversation_result.get("status") == "created":
                        session.tavus_conversation_id = conversation_result.get("conversation_id")
                        session.tavus_conversation_url = conversation_result.get("conversation_url")
                        logger.info(f"Conversation Tavus créée pour session {session_id}: {session.tavus_conversation_id}")
                    else:
                        logger.warning(f"Échec création conversation Tavus: {conversation_result.get('message')}")
            except Exception as e:
                logger.error(f"Erreur lors de la création de la conversation Tavus: {e}")

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
        tavus_conversation_id=session.tavus_conversation_id,
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
        tavus_conversation_id=session.tavus_conversation_id,
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
    previous_phase = session.current_phase

    # Enregistrer la durée de la phase précédente
    if transition.phase_duration:
        if previous_phase == ExamPhase.MONOLOGUE:
            session.monologue_duration = transition.phase_duration
        elif previous_phase == ExamPhase.DEBAT:
            session.debat_duration = transition.phase_duration

    # Mettre à jour la phase
    session.current_phase = transition.new_phase

    return {
        "status": "ok",
        "previous_phase": previous_phase,
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
