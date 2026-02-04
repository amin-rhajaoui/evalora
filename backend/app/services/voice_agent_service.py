"""
Service pour gérer les transcriptions des conversations vocales avec l'agent
"""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel
from ..config import logger


class TranscriptEntry(BaseModel):
    """Une entrée de transcription"""
    role: str  # "user" ou "assistant"
    text: str
    timestamp: Optional[str] = None


class Transcription(BaseModel):
    """Transcription complète d'une conversation"""
    session_id: str
    room_name: str
    transcript: List[TranscriptEntry]
    created_at: str


# Stockage en mémoire des transcriptions (à remplacer par une BDD en production)
transcriptions: Dict[str, Transcription] = {}


class VoiceAgentService:
    """Service de gestion des transcriptions de l'agent vocal"""

    @staticmethod
    def save_transcription(
        session_id: str,
        room_name: str,
        transcript: List[dict]
    ) -> Transcription:
        """
        Sauvegarde une transcription de conversation.

        Args:
            session_id: ID de la session d'examen
            room_name: Nom de la room LiveKit
            transcript: Liste des entrées de transcription

        Returns:
            Transcription sauvegardée
        """
        entries = [TranscriptEntry(**entry) for entry in transcript]

        transcription = Transcription(
            session_id=session_id,
            room_name=room_name,
            transcript=entries,
            created_at=datetime.utcnow().isoformat()
        )

        transcriptions[session_id] = transcription
        logger.info(f"Transcription saved for session {session_id}: {len(entries)} entries")

        return transcription

    @staticmethod
    def get_transcription(session_id: str) -> Optional[Transcription]:
        """
        Récupère une transcription par session_id.

        Args:
            session_id: ID de la session d'examen

        Returns:
            Transcription si trouvée, None sinon
        """
        return transcriptions.get(session_id)

    @staticmethod
    def delete_transcription(session_id: str) -> bool:
        """
        Supprime une transcription.

        Args:
            session_id: ID de la session d'examen

        Returns:
            True si supprimée, False si non trouvée
        """
        if session_id in transcriptions:
            del transcriptions[session_id]
            logger.info(f"Transcription deleted for session {session_id}")
            return True
        return False

    @staticmethod
    def list_transcriptions() -> List[str]:
        """
        Liste tous les session_ids avec des transcriptions.

        Returns:
            Liste des session_ids
        """
        return list(transcriptions.keys())


# Instance singleton du service
voice_agent_service = VoiceAgentService()
