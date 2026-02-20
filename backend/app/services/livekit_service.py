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
        # LiveKitAPI (REST) attend https, pas wss
        self._api_url = (
            self.ws_url.replace("wss://", "https://", 1).replace("ws://", "http://", 1)
            if self.ws_url else None
        )

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
            async with api.LiveKitAPI(
                url=self._api_url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            ) as lkapi:
                room = await lkapi.room.create_room(
                    api.CreateRoomRequest(
                        name=room_name,
                        empty_timeout=300,  # 5 min pour laisser le temps aux checks + mic test
                        max_participants=2,
                    )
                )

            room_sid = getattr(room, "sid", None)
            logger.info(f"Room LiveKit creee: {room_name} (SID: {room_sid})")

            return {
                "room_name": room_name,
                "room_sid": room_sid,
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
            async with api.LiveKitAPI(
                url=self._api_url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            ) as lkapi:
                await lkapi.room.delete_room(api.DeleteRoomRequest(room=room_name))

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
            async with api.LiveKitAPI(
                url=self._api_url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            ) as lkapi:
                resp = await lkapi.room.list_participants(
                    api.ListParticipantsRequest(room=room_name)
                )

            participants_list = getattr(resp, "participants", []) or []
            result = [
                {
                    "identity": getattr(p, "identity", ""),
                    "name": getattr(p, "name", ""),
                    "state": str(getattr(p, "state", "")),
                    "joined_at": getattr(p, "joined_at", None),
                }
                for p in participants_list
            ]

            logger.debug(f"{len(result)} participant(s) dans {room_name}")
            return result

        except Exception as e:
            logger.error(f"Erreur recuperation participants: {e}")
            return []

    async def get_room_info(self, room_name: str) -> Dict[str, Any]:
        """Récupère les informations d'une room LiveKit (existe, participants, etc.)"""
        if not self.is_configured:
            return {
                "exists": False,
                "room_name": room_name,
                "message": "LiveKit non configuré"
            }

        logger.debug(f"Verification room LiveKit: {room_name}")

        try:
            async with api.LiveKitAPI(
                url=self._api_url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            ) as lkapi:
                # Essayer de lister les participants - si la room n'existe pas, cela lèvera une exception
                resp = await lkapi.room.list_participants(
                    api.ListParticipantsRequest(room=room_name)
                )

                participants_list = getattr(resp, "participants", []) or []
                num_participants = len(participants_list)

                # Essayer de récupérer les infos de la room
                try:
                    rooms_resp = await lkapi.room.list_rooms(
                        api.ListRoomsRequest(names=[room_name])
                    )
                    rooms = getattr(rooms_resp, "rooms", []) or []
                    room_info = rooms[0] if rooms else None
                    
                    if room_info:
                        return {
                            "exists": True,
                            "room_name": room_name,
                            "room_sid": getattr(room_info, "sid", None),
                            "num_participants": num_participants,
                            "creation_time": getattr(room_info, "creation_time", None),
                            "empty_timeout": getattr(room_info, "empty_timeout", None),
                            "max_participants": getattr(room_info, "max_participants", None),
                            "participants": [
                                {
                                    "identity": getattr(p, "identity", ""),
                                    "name": getattr(p, "name", ""),
                                    "state": str(getattr(p, "state", "")),
                                }
                                for p in participants_list
                            ]
                        }
                    else:
                        return {
                            "exists": False,
                            "room_name": room_name,
                            "message": "Room non trouvée dans LiveKit"
                        }
                except Exception as e:
                    # Si list_rooms n'est pas disponible, on retourne juste les infos des participants
                    logger.debug(f"list_rooms non disponible, utilisation des participants uniquement: {e}")
                    return {
                        "exists": True,
                        "room_name": room_name,
                        "num_participants": num_participants,
                        "participants": [
                            {
                                "identity": getattr(p, "identity", ""),
                                "name": getattr(p, "name", ""),
                                "state": str(getattr(p, "state", "")),
                            }
                            for p in participants_list
                        ]
                    }

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Erreur verification room LiveKit {room_name}: {error_msg}")
            # Si l'erreur indique que la room n'existe pas
            if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                return {
                    "exists": False,
                    "room_name": room_name,
                    "message": f"Room non trouvée: {error_msg}"
                }
            else:
                return {
                    "exists": None,  # Incertain
                    "room_name": room_name,
                    "message": f"Erreur lors de la vérification: {error_msg}",
                    "error": error_msg
                }

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
            async with api.LiveKitAPI(
                url=self._api_url,
                api_key=self.api_key,
                api_secret=self.api_secret,
            ) as lkapi:
                await lkapi.room.send_data(
                    api.SendDataRequest(
                        room=room_name,
                        data=data,
                        kind=api.DataPacket.Kind.RELIABLE,
                        destination_identities=destination_identities or [],
                    )
                )

            return True

        except Exception as e:
            logger.error(f"Erreur envoi data LiveKit: {e}")
            return False
