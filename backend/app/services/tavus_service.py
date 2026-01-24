"""
Service Tavus pour la gestion des conversations vidéo.
"""
import logging
from typing import Optional, Dict, Any
import httpx

from ..config import settings

logger = logging.getLogger("evalora.tavus")


class TavusService:
    """
    Service pour gérer les conversations Tavus.
    
    Permet de créer des conversations vidéo avec les avatars Tavus.
    """

    def __init__(self):
        self.api_key = settings.TAVUS_API_KEY
        # S'assurer que l'URL de base se termine par /v2
        base_url = settings.TAVUS_BASE_URL.rstrip('/')
        if not base_url.endswith('/v2'):
            if base_url.endswith('/v1'):
                base_url = base_url.replace('/v1', '/v2')
            else:
                base_url = f"{base_url}/v2"
        self.base_url = base_url
        if self.is_configured:
            logger.info(f"TavusService initialisé - API key présente, Base URL: {self.base_url}")
        else:
            logger.warning("TavusService: pas de clé API")

    @property
    def is_configured(self) -> bool:
        """Vérifie si Tavus est configuré"""
        return self.api_key is not None and len(self.api_key or "") > 0

    def _build_proxy_config(self) -> Optional[Dict[str, str]]:
        """Construit la configuration proxy si définie"""
        proxies = {}
        if settings.TAVUS_HTTP_PROXY:
            proxies["http://"] = settings.TAVUS_HTTP_PROXY
        if settings.TAVUS_HTTPS_PROXY:
            proxies["https://"] = settings.TAVUS_HTTPS_PROXY
        return proxies if proxies else None

    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers pour les requêtes API Tavus"""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or ""
        }

    async def create_conversation(
        self,
        replica_id: str,
        persona_id: str,
        conversation_name: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée une conversation Tavus.
        
        Args:
            replica_id: ID de la réplique Tavus
            persona_id: ID du persona Tavus
            conversation_name: Nom optionnel de la conversation
            callback_url: URL optionnelle pour les webhooks
            
        Returns:
            Dict contenant conversation_id et conversation_url
        """
        if not self.is_configured:
            logger.warning("Tavus non configuré - mode simulation")
            return {
                "conversation_id": None,
                "conversation_url": None,
                "status": "placeholder",
                "message": "Tavus non configuré"
            }

        url = f"{self.base_url}/conversations"
        payload = {
            "replica_id": replica_id,
            "persona_id": persona_id
        }
        
        if conversation_name:
            payload["conversation_name"] = conversation_name
        if callback_url:
            payload["callback_url"] = callback_url

        logger.info(f"Création conversation Tavus: URL={url}, replica={replica_id}, persona={persona_id}")

        try:
            proxies = self._build_proxy_config()
            # httpx.Timeout nécessite soit un 'default', soit tous les paramètres explicitement
            timeout = httpx.Timeout(
                connect=settings.TAVUS_CONNECT_TIMEOUT,
                read=settings.TAVUS_READ_TIMEOUT,
                write=settings.TAVUS_READ_TIMEOUT,
                pool=settings.TAVUS_CONNECT_TIMEOUT
            )
            
            # Construire les arguments pour AsyncClient
            client_kwargs = {"timeout": timeout}
            if proxies:
                client_kwargs["proxies"] = proxies
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                conversation_id = data.get("conversation_id")
                conversation_url = data.get("conversation_url")
                
                logger.info(f"Conversation Tavus créée: {conversation_id}")
                
                return {
                    "conversation_id": conversation_id,
                    "conversation_url": conversation_url,
                    "status": "created",
                    "message": ""
                }
                
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.text
                # Essayer de parser le JSON pour un message plus clair
                try:
                    import json
                    error_json = json.loads(error_body)
                    error_message = error_json.get("message", error_body)
                    if "Invalid replica" in error_message or "replica_uuid" in error_message:
                        error_msg = f"Replica ID invalide: '{replica_id}'. Vérifiez que ce replica existe dans votre compte Tavus et appartient à votre compte."
                    else:
                        error_msg = f"Erreur HTTP Tavus ({e.response.status_code}): {error_message}"
                except:
                    error_msg = f"Erreur HTTP Tavus: {e.response.status_code} - {error_body}"
            except:
                error_msg = f"Erreur HTTP Tavus: {e.response.status_code} - Impossible de lire le corps de la réponse"
            logger.error(error_msg, exc_info=True)
            return {
                "conversation_id": None,
                "conversation_url": None,
                "status": "error",
                "message": error_msg
            }
        except httpx.ConnectTimeout as e:
            error_msg = f"Timeout de connexion Tavus après {settings.TAVUS_CONNECT_TIMEOUT}s (URL: {url}). Vérifiez l'URL et votre connexion réseau."
            logger.error(error_msg)
            logger.error(f"Détails: {type(e).__name__}: {str(e)}")
            return {
                "conversation_id": None,
                "conversation_url": None,
                "status": "error",
                "message": error_msg
            }
        except httpx.RequestError as e:
            error_msg = f"Erreur de requête Tavus (URL: {url}): {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "conversation_id": None,
                "conversation_url": None,
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Erreur création conversation Tavus: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "conversation_id": None,
                "conversation_url": None,
                "status": "error",
                "message": error_msg
            }

    async def get_conversation_url(self, conversation_id: str) -> Optional[str]:
        """
        Récupère l'URL d'une conversation Tavus.
        
        Args:
            conversation_id: ID de la conversation
            
        Returns:
            URL de la conversation ou None
        """
        if not self.is_configured:
            return None

        # L'URL de conversation est généralement: https://tavus.video/conversation/{conversation_id}
        # On peut aussi récupérer les infos via l'API si nécessaire
        return f"https://tavus.video/conversation/{conversation_id}"

    async def list_replicas(self) -> Dict[str, Any]:
        """
        Liste les replicas disponibles pour le compte Tavus.
        
        Returns:
            Dict contenant la liste des replicas
        """
        if not self.is_configured:
            logger.warning("Tavus non configuré - impossible de lister les replicas")
            return {
                "replicas": [],
                "status": "placeholder",
                "message": "Tavus non configuré"
            }

        url = f"{self.base_url}/replicas"
        logger.info(f"Récupération de la liste des replicas Tavus: {url}")

        try:
            proxies = self._build_proxy_config()
            timeout = httpx.Timeout(
                connect=settings.TAVUS_CONNECT_TIMEOUT,
                read=settings.TAVUS_READ_TIMEOUT,
                write=settings.TAVUS_READ_TIMEOUT,
                pool=settings.TAVUS_CONNECT_TIMEOUT
            )
            
            client_kwargs = {"timeout": timeout}
            if proxies:
                client_kwargs["proxies"] = proxies
            
            async with httpx.AsyncClient(**client_kwargs) as client:
                response = await client.get(
                    url,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                # L'API Tavus retourne les replicas dans "data" ou "replicas"
                replicas = data.get("data", data.get("replicas", []))
                logger.info(f"{len(replicas)} replica(s) trouvé(s)")
                
                return {
                    "replicas": replicas,
                    "status": "success",
                    "message": ""
                }
                
        except httpx.HTTPStatusError as e:
            try:
                error_body = e.response.text
            except:
                error_body = "Impossible de lire le corps de la réponse"
            error_msg = f"Erreur HTTP Tavus: {e.response.status_code} - {error_body}"
            logger.error(error_msg)
            return {
                "replicas": [],
                "status": "error",
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Erreur lors de la récupération des replicas: {type(e).__name__}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "replicas": [],
                "status": "error",
                "message": error_msg
            }
