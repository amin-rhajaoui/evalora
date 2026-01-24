"""
Service LiveKit pour la communication temps réel.
Documentation: https://docs.livekit.io
"""
import logging
from datetime import timedelta
from typing import Optional, Dict, Any, List

from ..config import settings

logger = logging.getLogger("evalora.livekit")

# Import conditionnel de livekit
try:
    from livekit import api
    LIVEKIT_AVAILABLE = True
    logger.debug("Module livekit-api importe avec succes")
except ImportError:
    LIVEKIT_AVAILABLE = False
    logger.warning("Module livekit-api non disponible - installez avec: pip install livekit-api")


class LiveKitService:
    """
    Service pour gérer les communications temps réel via LiveKit.

    LiveKit permet:
    - Capture audio de l'étudiant
    - Rooms par session d'examen
    - Tokens d'authentification sécurisés
    """

    def __init__(self):
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET
        self.ws_url = settings.LIVEKIT_URL

        if self.is_configured:
            logger.info(f"LiveKitService initialise - URL: {self.ws_url}")
        else:
            if not LIVEKIT_AVAILABLE:
                logger.warning("LiveKitService: module livekit-api manquant")
            else:
                logger.warning("LiveKitService: credentials manquantes (mode simulation)")

    @property
    def is_configured(self) -> bool:
        """Vérifie si LiveKit est configuré"""
        return (
            self.api_key is not None
            and self.api_secret is not None
            and LIVEKIT_AVAILABLE
        )

    async def create_room(self, session_id: str) -> Dict[str, Any]:
        """Crée une room LiveKit pour une session d'examen."""
        room_name = f"evalora-{session_id}"

        if not self.is_configured:
            logger.debug(f"Mode simulation - room fictive: {room_name}")
            return {
                "room_name": room_name,
                "token": None,
                "status": "placeholder",
                "message": "LiveKit non configure - Mode simulation"
            }

        logger.info(f"Creation room LiveKit: {room_name}")

        try:
            room_service = api.RoomServiceClient(
                self.ws_url,
                self.api_key,
                self.api_secret
            )

            room = await room_service.create_room(
                api.CreateRoomRequest(
                    name=room_name,
                    empty_timeout=300,
                    max_participants=2
                )
            )

            logger.info(f"Room LiveKit creee: {room_name} (SID: {room.sid})")

            return {
                "room_name": room_name,
                "room_sid": room.sid,
                "status": "created",
                "message": ""
            }

        except Exception as e:
            logger.error(f"Erreur creation room LiveKit: {e}")
            return {
                "room_name": room_name,
                "status": "error",
                "message": f"Erreur LiveKit: {str(e)}"
            }

    async def generate_token(
        self,
        room_name: str,
        participant_name: str,
        can_publish: bool = True,
        can_subscribe: bool = True
    ) -> Optional[str]:
        """Génère un token d'accès LiveKit pour un participant."""

        if not self.is_configured:
            logger.debug(f"Mode simulation - pas de token pour {participant_name}")
            return None

        logger.info(f"Generation token LiveKit pour {participant_name} dans {room_name}")

        try:
            token = api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(participant_name)
            token.with_name(participant_name)

            grant = api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=can_publish,
                can_subscribe=can_subscribe,
                can_publish_data=True
            )
            token.with_grants(grant)
            token.with_ttl(timedelta(hours=1))

            jwt_token = token.to_jwt()
            logger.debug(f"Token genere pour {participant_name}")
            return jwt_token

        except Exception as e:
            logger.error(f"Erreur generation token LiveKit: {e}")
            return None

    async def delete_room(self, room_name: str) -> Dict[str, Any]:
        """Supprime une room LiveKit"""
        if not self.is_configured:
            logger.debug(f"Mode simulation - suppression fictive: {room_name}")
            return {"status": "placeholder", "room_name": room_name}

        logger.info(f"Suppression room LiveKit: {room_name}")

        try:
            room_service = api.RoomServiceClient(
                self.ws_url,
                self.api_key,
                self.api_secret
            )

            await room_service.delete_room(
                api.DeleteRoomRequest(room=room_name)
            )

            logger.info(f"Room supprimee: {room_name}")
            return {"status": "deleted", "room_name": room_name}

        except Exception as e:
            logger.error(f"Erreur suppression room LiveKit: {e}")
            return {
                "status": "error",
                "room_name": room_name,
                "error": str(e)
            }

    async def get_participants(self, room_name: str) -> List[Dict[str, Any]]:
        """Récupère la liste des participants dans une room"""
        if not self.is_configured:
            return []

        logger.debug(f"Recuperation participants pour {room_name}")

        try:
            room_service = api.RoomServiceClient(
                self.ws_url,
                self.api_key,
                self.api_secret
            )

            participants = await room_service.list_participants(
                api.ListParticipantsRequest(room=room_name)
            )

            result = [
                {
                    "identity": p.identity,
                    "name": p.name,
                    "state": p.state,
                    "joined_at": p.joined_at
                }
                for p in participants.participants
            ]

            logger.debug(f"{len(result)} participant(s) dans {room_name}")
            return result

        except Exception as e:
            logger.error(f"Erreur recuperation participants: {e}")
            return []

    async def send_data(
        self,
        room_name: str,
        data: bytes,
        destination_identities: Optional[List[str]] = None
    ) -> bool:
        """Envoie des données à des participants"""
        if not self.is_configured:
            return False

        logger.debug(f"Envoi data vers {room_name} ({len(data)} bytes)")

        try:
            room_service = api.RoomServiceClient(
                self.ws_url,
                self.api_key,
                self.api_secret
            )

            await room_service.send_data(
                api.SendDataRequest(
                    room=room_name,
                    data=data,
                    kind=api.DataPacket.Kind.RELIABLE,
                    destination_identities=destination_identities or []
                )
            )

            return True

        except Exception as e:
            logger.error(f"Erreur envoi data LiveKit: {e}")
            return False
