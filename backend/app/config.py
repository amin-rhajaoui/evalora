"""
Configuration centralisée pour Evalora
"""
import logging
import sys
from pydantic_settings import BaseSettings
from typing import Optional

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("evalora")


class Settings(BaseSettings):
    """Configuration de l'application"""

    # Application
    APP_NAME: str = "Evalora - Chatbot FLE"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LiveKit Configuration
    LIVEKIT_API_KEY: Optional[str] = None
    LIVEKIT_API_SECRET: Optional[str] = None
    LIVEKIT_URL: str = "wss://your-livekit-server.livekit.cloud"

    # Tavus Configuration
    TAVUS_API_KEY: Optional[str] = None
    TAVUS_BASE_URL: str = "https://api.tavus.io/v2"

    class Config:
        env_file = ".env"
        extra = "allow"

    def log_config_status(self):
        """Affiche le statut de la configuration au démarrage"""
        logger.info("=" * 60)
        logger.info("EVALORA - Configuration")
        logger.info("=" * 60)
        logger.info(f"Application     : {self.APP_NAME} v{self.APP_VERSION}")
        logger.info(f"Mode Debug      : {'Oui' if self.DEBUG else 'Non'}")
        logger.info(f"CORS Origins    : {', '.join(self.CORS_ORIGINS)}")
        logger.info("-" * 60)

        # LiveKit
        if self.LIVEKIT_API_KEY and self.LIVEKIT_API_SECRET:
            logger.info(f"LiveKit         : CONFIGURE")
            logger.info(f"  - URL         : {self.LIVEKIT_URL}")
            logger.info(f"  - API Key     : {self.LIVEKIT_API_KEY[:8]}...")
        else:
            logger.warning("LiveKit         : NON CONFIGURE (mode simulation)")

        # Tavus
        if self.TAVUS_API_KEY:
            logger.info(f"Tavus           : CONFIGURE")
            logger.info(f"  - Base URL    : {self.TAVUS_BASE_URL}")
            logger.info(f"  - API Key     : {self.TAVUS_API_KEY[:8]}...")
        else:
            logger.warning("Tavus           : NON CONFIGURE (mode texte)")

        logger.info("=" * 60)


settings = Settings()


# Configuration des avatars
AVATARS = {
    "clea": {
        "id": "clea",
        "name": "Cléa",
        "gender": "femme",
        "age": 30,
        "register": "tutoiement",
        "personality": "Bienveillante, patiente. Encourage toujours positivement.",
        "role": "Met à l'aise l'étudiant, crée un climat de confiance.",
        "behavior": "Sourit souvent, parle calmement, valorise les efforts, reformule pour aider.",
        "feedback_tone": "Chaleureux, empathique et motivant.",
        "tavus_replica_id": "r9fa087897a",
        "placeholder_image": "/assets/avatars/clea.png"
    },
    "alex": {
        "id": "alex",
        "name": "Alex",
        "gender": "homme",
        "age": 20,
        "register": "tutoiement",
        "personality": "Détendu, amical, ton cool mais structuré. Dynamique et souriant.",
        "role": "Rassure, motive, détend l'ambiance pour réduire le stress.",
        "behavior": "Langage familier mais correct. Attitude très amicale.",
        "feedback_tone": "Positif et encourageant.",
        "tavus_replica_id": None,
        "placeholder_image": "/assets/avatars/alex.png"
    },
    "karim": {
        "id": "karim",
        "name": "Karim",
        "gender": "homme",
        "age": 45,
        "register": "vouvoiement",
        "personality": "Posé, professionnel, rigoureux mais juste. Ton académique et mesuré.",
        "role": "Garant du cadre formel de l'examen DU. Donne un retour équilibré.",
        "behavior": "Structure les consignes clairement, parle lentement, garde une distance bienveillante.",
        "feedback_tone": "Neutre et analytique.",
        "tavus_replica_id": None,
        "placeholder_image": "/assets/avatars/karim.png"
    },
    "claire": {
        "id": "claire",
        "name": "Claire",
        "gender": "femme",
        "age": 45,
        "register": "vouvoiement",
        "personality": "Sévère, exigeante, très attentive aux erreurs. Attitude sérieuse et concentrée.",
        "role": "Fait respecter le cadre académique strict. Exigence linguistique élevée.",
        "behavior": "Peu de sourires, ton direct, reformule si nécessaire, exige des réponses complètes.",
        "feedback_tone": "Exigeant mais constructif.",
        "tavus_replica_id": None,
        "placeholder_image": "/assets/avatars/claire.png"
    }
}


# Configuration des phases du timer
TIMER_PHASES = {
    "consignes": {
        "name": "CONSIGNES",
        "color": "#87CEEB",
        "duration": None,
        "description": "Phase d'écoute et préparation"
    },
    "monologue": {
        "name": "MONOLOGUE",
        "color": "#4CAF50",
        "duration": 600,
        "warning_at": 480,
        "warning_color": "#FFC107",
        "end_color": "#F44336",
        "description": "Étudiant parle seul"
    },
    "debat": {
        "name": "DÉBAT",
        "color": "#9C27B0",
        "duration": 600,
        "description": "Phase d'échange interactif"
    },
    "feedback": {
        "name": "FEEDBACK",
        "color": "#FFFFFF",
        "duration": None,
        "description": "Restitution IA"
    }
}


# Grille de notation DU
GRADING_CRITERIA = {
    "monologue": {
        "presentation": {"max": 1.5, "description": "Type, source, auteur, date"},
        "description": {"max": 2.0, "description": "Précision, vocabulaire adapté"},
        "analyse_opinion": {"max": 3.0, "description": "Argumentation, exemples personnels"},
        "coherence": {"max": 1.0, "description": "Structure claire, connecteurs"},
        "aisance": {"max": 1.0, "description": "Fluidité, autonomie, naturel"}
    },
    "debat": {
        "interaction": {"max": 2.5, "description": "Réactivité, reformulation"},
        "argumentation": {"max": 1.5, "description": "Défense d'idées, nuance"},
        "elargissement": {"max": 0.5, "description": "Capacité à ouvrir le débat"}
    },
    "general": {
        "vocabulaire": {"max": 2.0, "description": "Richesse lexicale"},
        "prononciation": {"max": 2.0, "description": "Clarté de prononciation"},
        "grammaire": {"max": 2.0, "description": "Correction grammaticale"},
        "comprehension": {"max": 1.0, "description": "Compréhension des questions"}
    }
}
