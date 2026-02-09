"""
Modèles SQLAlchemy pour la base de données
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class ExamSession(Base):
    """Session d'examen persistée en BDD"""
    __tablename__ = "exam_sessions"

    id = Column(String(64), primary_key=True)
    student_name = Column(String(100), nullable=False)
    level = Column(String(10), nullable=False, default="B1")
    avatar_id = Column(String(32), nullable=True)
    document_id = Column(String(64), nullable=True)
    current_phase = Column(String(32), nullable=False, default="consignes")
    monologue_duration = Column(Integer, nullable=True)
    debat_duration = Column(Integer, nullable=True)
    livekit_room_name = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ExamSession {self.id} {self.student_name}>"


class EvaluationResult(Base):
    """Résultat d'évaluation persisté en BDD"""
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    total_score = Column(Float, nullable=False, default=0.0)
    monologue_scores_json = Column(JSON, nullable=True)
    debat_scores_json = Column(JSON, nullable=True)
    general_scores_json = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    strengths_json = Column(JSON, nullable=True)
    improvements_json = Column(JSON, nullable=True)
    advice_json = Column(JSON, nullable=True)
    avatar_id = Column(String(32), nullable=True)
    feedback_tone = Column(String(64), nullable=True, default="neutral")
    monologue_duration = Column(Integer, nullable=True)
    debat_duration = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<EvaluationResult {self.session_id} score={self.total_score}>"


class User(Base):
    """Modèle utilisateur pour l'authentification"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"


class TranscriptionEntry(Base):
    """Une entrée de transcription (TTS/STT) d'un appel vocal"""
    __tablename__ = "transcription_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(64), nullable=False, index=True)
    room_name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=False)  # "user" | "assistant"
    text = Column(Text, nullable=False)
    timestamp = Column(String(64), nullable=True)  # ISO format from agent
    phase = Column(String(32), nullable=True)  # consignes | monologue | debat
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<TranscriptionEntry {self.session_id} {self.role}>"
