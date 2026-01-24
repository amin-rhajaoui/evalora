"""
Modèles pour les sessions d'examen
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime
import uuid


class ExamPhase(str, Enum):
    """Phases de l'examen"""
    CONSIGNES = "consignes"
    MONOLOGUE = "monologue"
    DEBAT = "debat"
    FEEDBACK = "feedback"
    COMPLETED = "completed"


class StudentLevel(str, Enum):
    """Niveaux FLE"""
    A2_PLUS = "A2+"
    B1 = "B1"


class SessionCreate(BaseModel):
    """Données pour créer une session"""
    student_name: str = Field(..., min_length=1, max_length=50, description="Prénom de l'étudiant")
    level: StudentLevel = Field(default=StudentLevel.B1, description="Niveau estimé")
    avatar_id: Optional[str] = Field(default=None, description="ID de l'avatar choisi (null = sans avatar)")
    document_id: Optional[str] = Field(default=None, description="ID du document choisi")


class Session(BaseModel):
    """Session d'examen complète"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_name: str
    level: StudentLevel
    avatar_id: Optional[str] = None
    document_id: Optional[str] = None
    current_phase: ExamPhase = ExamPhase.CONSIGNES
    phase_start_time: Optional[datetime] = None
    monologue_duration: Optional[int] = None  # en secondes
    debat_duration: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)

    # LiveKit
    livekit_room_name: Optional[str] = None
    livekit_token: Optional[str] = None
    
    # Tavus
    tavus_conversation_id: Optional[str] = None
    tavus_conversation_url: Optional[str] = None


class SessionResponse(BaseModel):
    """Réponse API pour une session"""
    id: str
    student_name: str
    level: str
    avatar_id: Optional[str]
    avatar_info: Optional[dict] = None
    document_id: Optional[str]
    current_phase: ExamPhase
    livekit_token: Optional[str] = None
    livekit_url: Optional[str] = None
    tavus_conversation_id: Optional[str] = None
    tavus_conversation_url: Optional[str] = None
    created_at: datetime


class PhaseTransition(BaseModel):
    """Transition entre phases"""
    session_id: str
    new_phase: ExamPhase
    phase_duration: Optional[int] = None  # Durée de la phase précédente
