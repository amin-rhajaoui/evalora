"""
Service Tavus pour les avatars IA vidéo.
Documentation: https://docs.tavus.io
"""
import logging
import httpx
from typing import Optional, Dict, Any

from ..config import settings

logger = logging.getLogger("evalora.tavus")


class TavusService:
    """
    Service pour gérer les avatars Tavus.

    Tavus permet de créer des avatars vidéo réalistes qui peuvent
    parler en temps réel avec une voix synthétisée.
    """

    def __init__(self):
        self.api_key = settings.TAVUS_API_KEY
        self.base_url = settings.TAVUS_BASE_URL
        self.client = httpx.AsyncClient(timeout=30.0)
        if self.is_configured:
            logger.info("TavusService initialise avec API key")
        else:
            logger.warning("TavusService en mode placeholder (pas de cle API)")

    @property
    def is_configured(self) -> bool:
        """Vérifie si Tavus est configuré"""
        return self.api_key is not None and len(self.api_key) > 0

    def _headers(self) -> Dict[str, str]:
        """Headers pour les requêtes Tavus"""
        return {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json"
        }

    async def create_conversation(
        self,
        replica_id: str,
        session_id: str,
        student_name: str,
        avatar_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Crée une conversation Tavus pour l'examen."""

        if not self.is_configured:
            logger.debug(f"Mode placeholder - conversation simulee pour session {session_id}")
            return {
                "conversation_id": f"placeholder-{session_id}",
                "status": "placeholder",
                "message": "Tavus non configure - Mode texte active",
                "replica_id": replica_id,
                "conversation_url": None,
                "stream_url": None
            }

        # Vérifier si replica_id est configuré
        if not replica_id or replica_id == "None":
            logger.warning(f"Replica ID manquant pour avatar {avatar_config.get('name')} - Mode placeholder active")
            return {
                "conversation_id": f"placeholder-{session_id}",
                "status": "placeholder",
                "message": f"Replica ID non configure pour {avatar_config.get('name')} - Mode texte active",
                "replica_id": replica_id,
                "conversation_url": None,
                "stream_url": None
            }

        # Mode Tavus configuré
        logger.info(f"Creation conversation Tavus pour {student_name} (session: {session_id})")

        try:
            response = await self.client.post(
                f"{self.base_url}/conversations",
                headers=self._headers(),
                json={
                    "replica_id": replica_id,
                    "persona_id": None,
                    "custom_greeting": self._get_greeting(student_name, avatar_config),
                    "properties": {
                        "session_id": session_id,
                        "student_name": student_name,
                        "avatar_name": avatar_config.get("name"),
                        "register": avatar_config.get("register")
                    }
                }
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"Conversation Tavus creee: {data.get('conversation_id')}")

            return {
                "conversation_id": data.get("conversation_id"),
                "status": "active",
                "message": "",
                "replica_id": replica_id,
                "conversation_url": data.get("conversation_url"),
                "stream_url": data.get("stream_url")
            }

        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                error_detail += f": {error_body}"
            except:
                error_detail += f": {e.response.text}"
            logger.error(f"Erreur HTTP Tavus {error_detail}")
            return self._error_response(session_id, replica_id, error_detail)
        except httpx.TimeoutException as e:
            logger.error(f"Timeout lors de la creation de la conversation Tavus: {e}")
            return self._error_response(session_id, replica_id, f"Timeout: {str(e)}")
        except Exception as e:
            logger.error(f"Erreur Tavus: {type(e).__name__}: {e}", exc_info=True)
            return self._error_response(session_id, replica_id, str(e))

    def _error_response(self, session_id: str, replica_id: str, error: str) -> Dict[str, Any]:
        """Génère une réponse d'erreur"""
        return {
            "conversation_id": f"error-{session_id}",
            "status": "error",
            "message": f"Erreur Tavus: {error}",
            "replica_id": replica_id,
            "conversation_url": None,
            "stream_url": None
        }

    async def send_message(
        self,
        conversation_id: str,
        text: str,
        avatar_personality: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Envoie un message à l'avatar pour qu'il le prononce."""

        if not self.is_configured or conversation_id.startswith("placeholder"):
            logger.debug(f"Mode placeholder - message: {text[:50]}...")
            return {
                "status": "placeholder",
                "text": text,
                "audio_url": None,
                "video_url": None
            }

        logger.info(f"Envoi message Tavus ({len(text)} chars)")

        try:
            response = await self.client.post(
                f"{self.base_url}/conversations/{conversation_id}/messages",
                headers=self._headers(),
                json={"text": text, "properties": {}}
            )
            response.raise_for_status()
            data = response.json()

            logger.debug("Message Tavus envoye avec succes")

            return {
                "status": "sent",
                "text": text,
                "audio_url": data.get("audio_url"),
                "video_url": data.get("video_url")
            }

        except Exception as e:
            logger.error(f"Erreur envoi message Tavus: {e}")
            return {
                "status": "error",
                "text": text,
                "error": str(e),
                "audio_url": None,
                "video_url": None
            }

    async def end_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Termine une conversation Tavus"""
        if not self.is_configured or conversation_id.startswith("placeholder"):
            logger.debug(f"Fin conversation placeholder: {conversation_id}")
            return {"status": "ended", "conversation_id": conversation_id}

        logger.info(f"Fin conversation Tavus: {conversation_id}")

        try:
            response = await self.client.delete(
                f"{self.base_url}/conversations/{conversation_id}",
                headers=self._headers()
            )
            response.raise_for_status()
            return {"status": "ended", "conversation_id": conversation_id}

        except Exception as e:
            logger.error(f"Erreur fin conversation Tavus: {e}")
            return {
                "status": "error",
                "conversation_id": conversation_id,
                "error": str(e)
            }

    def _get_greeting(self, student_name: str, avatar_config: Dict[str, Any]) -> str:
        """Génère le message d'accueil personnalisé"""
        name = avatar_config.get("name", "l'examinateur")
        is_tu = avatar_config.get("register") == "tutoiement"

        if is_tu:
            return f"Bonjour {student_name} ! Je m'appelle {name}. Je serai ton examinateur pour cette simulation. Comment vas-tu aujourd'hui ?"
        else:
            return f"Bonjour {student_name}. Je m'appelle {name}. Je serai votre examinateur pour cette simulation. Comment allez-vous aujourd'hui ?"

    async def close(self):
        """Ferme le client HTTP"""
        await self.client.aclose()
        logger.debug("Client HTTP Tavus ferme")


# Configuration des réplicas Tavus (à créer dans votre dashboard Tavus)
TAVUS_REPLICAS = {
    "clea": {
        "replica_id": None,
        "voice_settings": {"language": "fr-FR", "pitch": 0, "speed": 1.0},
        "persona": "Bienveillante, patiente, utilise le tutoiement"
    },
    "alex": {
        "replica_id": None,
        "voice_settings": {"language": "fr-FR", "pitch": -2, "speed": 1.1},
        "persona": "Détendu, amical, utilise le tutoiement"
    },
    "karim": {
        "replica_id": None,
        "voice_settings": {"language": "fr-FR", "pitch": -3, "speed": 0.95},
        "persona": "Posé, professionnel, utilise le vouvoiement"
    },
    "claire": {
        "replica_id": None,
        "voice_settings": {"language": "fr-FR", "pitch": 1, "speed": 0.9},
        "persona": "Sévère, exigeante, utilise le vouvoiement"
    }
}
