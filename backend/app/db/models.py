"""
Modèles SQLAlchemy pour la base de données
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"<TranscriptionEntry {self.session_id} {self.role}>"
