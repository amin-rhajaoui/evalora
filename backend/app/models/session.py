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
    created_at: datetime


class PhaseTransition(BaseModel):
    """Transition entre phases"""
    session_id: Optional[str] = None
    new_phase: ExamPhase
    phase_duration: Optional[int] = None
