"""
Service pour gérer les transcriptions des conversations vocales avec l'agent (persistance BDD)
"""
from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import logger
from ..db.models import TranscriptionEntry as TranscriptionEntryModel, DebateQA as DebateQAModel


class DebateQAEntry(BaseModel):
    """Une paire question/réponse du débat"""
    question_number: int
    question_text: str
    answer_text: Optional[str] = None


class TranscriptEntry(BaseModel):
    """Une entrée de transcription"""
    role: str  # "user" ou "assistant"
    text: str
    timestamp: Optional[str] = None
    phase: Optional[str] = None  # consignes | monologue | debat


class Transcription(BaseModel):
    """Transcription complète d'une conversation"""
    session_id: str
    room_name: str
    transcript: List[TranscriptEntry]
    created_at: str


class VoiceAgentService:
    """Service de gestion des transcriptions de l'agent vocal (base de données)"""

    @staticmethod
    async def save_transcription(
        db: AsyncSession,
        session_id: str,
        room_name: str,
        transcript: List[dict]
    ) -> Transcription:
        """
        Sauvegarde une transcription (remplace les entrées existantes pour cette session).
        """
        await VoiceAgentService.delete_transcription(db, session_id)
        entries = [TranscriptEntry(**e) for e in transcript]
        created_at = datetime.utcnow().isoformat()
        for e in entries:
            row = TranscriptionEntryModel(
                session_id=session_id,
                room_name=room_name,
                role=e.role,
                text=e.text,
                timestamp=e.timestamp,
                phase=e.phase,
            )
            db.add(row)
        await db.commit()
        logger.info(f"Transcription saved for session {session_id}: {len(entries)} entries")
        return Transcription(
            session_id=session_id,
            room_name=room_name,
            transcript=entries,
            created_at=created_at,
        )

    @staticmethod
    async def append_entry(
        db: AsyncSession,
        session_id: str,
        room_name: str,
        entry: dict
    ) -> Transcription:
        """
        Ajoute une entrée en temps réel (pendant l'appel). Crée la transcription si besoin.
        """
        parsed = TranscriptEntry(**entry)
        row = TranscriptionEntryModel(
            session_id=session_id,
            room_name=room_name,
            role=parsed.role,
            text=parsed.text,
            timestamp=parsed.timestamp,
            phase=parsed.phase,
        )
        db.add(row)
        await db.commit()
        logger.info(f"Transcription append for session {session_id}: {parsed.role}")
        return await VoiceAgentService.get_transcription(db, session_id) or Transcription(
            session_id=session_id,
            room_name=room_name,
            transcript=[parsed],
            created_at=datetime.utcnow().isoformat(),
        )

    @staticmethod
    async def get_transcription(db: AsyncSession, session_id: str) -> Optional[Transcription]:
        """Récupère la transcription par session_id (ordre chronologique)."""
        result = await db.execute(
            select(TranscriptionEntryModel)
            .where(TranscriptionEntryModel.session_id == session_id)
            .order_by(TranscriptionEntryModel.created_at)
        )
        rows = result.scalars().all()
        if not rows:
            return None
        first = rows[0]
        return Transcription(
            session_id=first.session_id,
            room_name=first.room_name,
            transcript=[
                TranscriptEntry(role=r.role, text=r.text, timestamp=r.timestamp, phase=r.phase)
                for r in rows
            ],
            created_at=first.created_at.isoformat() if first.created_at else datetime.utcnow().isoformat(),
        )

    @staticmethod
    async def delete_transcription(db: AsyncSession, session_id: str) -> bool:
        """Supprime toutes les entrées de transcription pour cette session."""
        result = await db.execute(delete(TranscriptionEntryModel).where(TranscriptionEntryModel.session_id == session_id))
        await db.commit()
        deleted = result.rowcount
        if deleted:
            logger.info(f"Transcription deleted for session {session_id}: {deleted} entries")
        return deleted > 0

    @staticmethod
    async def list_transcriptions(db: AsyncSession) -> List[str]:
        """Liste les session_id ayant au moins une entrée."""
        result = await db.execute(
            select(TranscriptionEntryModel.session_id).distinct()
        )
        return [r[0] for r in result.all()]

    @staticmethod
    async def save_debate_qa(
        db: AsyncSession,
        session_id: str,
        question_number: int,
        question_text: str,
        answer_text: Optional[str] = None,
    ) -> DebateQAEntry:
        """Sauvegarde une paire question/réponse du débat."""
        row = DebateQAModel(
            session_id=session_id,
            question_number=question_number,
            question_text=question_text,
            answer_text=answer_text,
        )
        db.add(row)
        await db.commit()
        logger.info(f"DebateQA saved: session={session_id} Q{question_number}")
        return DebateQAEntry(
            question_number=question_number,
            question_text=question_text,
            answer_text=answer_text,
        )

    @staticmethod
    async def get_debate_qa(db: AsyncSession, session_id: str) -> List[DebateQAEntry]:
        """Récupère toutes les paires Q&A d'une session, ordonnées par question_number."""
        result = await db.execute(
            select(DebateQAModel)
            .where(DebateQAModel.session_id == session_id)
            .order_by(DebateQAModel.question_number)
        )
        rows = result.scalars().all()
        return [
            DebateQAEntry(
                question_number=r.question_number,
                question_text=r.question_text,
                answer_text=r.answer_text,
            )
            for r in rows
        ]


voice_agent_service = VoiceAgentService()
