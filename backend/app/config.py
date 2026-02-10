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

    # Database - Neon PostgreSQL (using psycopg async driver)
    DATABASE_URL: str = "postgresql+psycopg://neondb_owner:npg_d9ASaKywX1VE@ep-tiny-art-agr0j92a-pooler.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require"

    # JWT Configuration
    JWT_SECRET_KEY: str = "evalora-secret-key-change-in-production-2024"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OpenAI Configuration (for voice conversation)
    OPENAI_API_KEY: Optional[str] = None

    # ElevenLabs Configuration (optional - for custom voices)
    ELEVENLABS_API_KEY: Optional[str] = None

    # LiveKit Configuration
    LIVEKIT_API_KEY: Optional[str] = None
    LIVEKIT_API_SECRET: Optional[str] = None
    LIVEKIT_URL: str = "wss://your-livekit-server.livekit.cloud"

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

        # Database
        if self.DATABASE_URL:
            # Masquer le mot de passe dans les logs
            db_url = self.DATABASE_URL
            if "@" in db_url:
                parts = db_url.split("@")
                prefix = parts[0].rsplit(":", 1)[0]
                logger.info(f"Database        : CONFIGURE")
                logger.info(f"  - Host        : {parts[1].split('/')[0]}")
            else:
                logger.info(f"Database        : CONFIGURE")
        else:
            logger.warning("Database        : NON CONFIGURE")

        logger.info("-" * 60)

        # LiveKit
        if self.LIVEKIT_API_KEY and self.LIVEKIT_API_SECRET:
            logger.info(f"LiveKit         : CONFIGURE")
            logger.info(f"  - URL         : {self.LIVEKIT_URL}")
            logger.info(f"  - API Key     : {self.LIVEKIT_API_KEY[:8]}...")
        else:
            logger.warning("LiveKit         : NON CONFIGURE (mode simulation)")

        # OpenAI
        if self.OPENAI_API_KEY:
            logger.info(f"OpenAI          : CONFIGURE")
            logger.info(f"  - API Key     : {self.OPENAI_API_KEY[:8]}...")
        else:
            logger.warning("OpenAI          : NON CONFIGURE (voice agent disabled)")

        # ElevenLabs
        if self.ELEVENLABS_API_KEY:
            logger.info(f"ElevenLabs      : CONFIGURE")
            logger.info(f"  - API Key     : {self.ELEVENLABS_API_KEY[:8]}...")
        else:
            logger.info("ElevenLabs      : NON CONFIGURE (using OpenAI TTS)")

        logger.info("=" * 60)


settings = Settings()


# Configuration des avatars
# Champs optionnels ElevenLabs (elevenlabs_voice_id, stability, similarity_boost, etc.)
# pour Phase 1 TTS : Cléa→Charlotte, Alex→Antoine, Karim→Pierre, Claire→Jacqueline (noms voix cahier des charges)
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
        "placeholder_image": "/assets/avatars/clea.png",
        "elevenlabs_voice_id": "WQKwBV2Uzw1gSGr69N8I",
        "elevenlabs_stability": 0.5,
        "elevenlabs_similarity_boost": 0.75,
        "elevenlabs_style_exaggeration": None,
        "elevenlabs_speaker_boost": True,
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
        "placeholder_image": "/assets/avatars/alex.png",
        "elevenlabs_voice_id": "IbbR6Av0dWuQJS0b8JVT",  # voix Alex
        "elevenlabs_stability": 0.5,
        "elevenlabs_similarity_boost": 0.75,
        "elevenlabs_style_exaggeration": None,
        "elevenlabs_speaker_boost": True,
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
        "placeholder_image": "/assets/avatars/karim.png",
        # Nouveau voice Karim (à activer quand validé sur ton compte ElevenLabs) : imDSDag6GbkW8mdzqJ0D
        "elevenlabs_voice_id": "5Qfm4RqcAer0xoyWtoHC",  # Karim (Guillaume – fallback tant que le nouveau ID n’est pas OK)
        "elevenlabs_stability": 0.6,
        "elevenlabs_similarity_boost": 0.75,
        "elevenlabs_style_exaggeration": None,
        "elevenlabs_speaker_boost": True,
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
        "placeholder_image": "/assets/avatars/claire.png",
        "elevenlabs_voice_id": "QbsdzCokdlo98elkq4Pc",  # voix Claire
        "elevenlabs_stability": 0.6,
        "elevenlabs_similarity_boost": 0.75,
        "elevenlabs_style_exaggeration": None,
        "elevenlabs_speaker_boost": True,
    }
}


# Configuration des phases du timer
TIMER_PHASES = {
    "consignes": {
        "name": "PHASE : CONSIGNES",
        "color": "#ADD8E6",  # bleu clair spec
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
