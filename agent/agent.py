"""
Evalora Voice Agent - Conversation vocale avec ElevenLabs TTS

Cet agent rejoint automatiquement les rooms LiveKit "evalora-*" et permet
une conversation vocale en temps réel avec l'utilisateur.

Requiert Python >= 3.10, < 3.14
"""
import os
import logging
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai, silero, elevenlabs

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evalora-agent")

# Configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

# Instructions pour l'agent vocal
AGENT_INSTRUCTIONS = """Tu es un examinateur FLE (Français Langue Étrangère) bienveillant et encourageant.

Tu fais passer un examen oral de niveau B1 à un étudiant. Ton rôle est de:
1. Accueillir l'étudiant chaleureusement
2. Lui poser des questions sur un document ou un thème de société
3. Écouter ses réponses et relancer la conversation
4. Être patient et reformuler si nécessaire
5. Encourager l'étudiant à développer ses idées

Règles importantes:
- Parle en français uniquement
- Utilise un langage clair et adapté au niveau B1
- Sois bienveillant mais garde un cadre d'examen
- Pose des questions ouvertes qui permettent à l'étudiant de s'exprimer
- Ne corrige pas immédiatement les erreurs, laisse l'étudiant finir
- Limite tes réponses à 2-3 phrases maximum pour laisser la parole à l'étudiant

Commence par te présenter brièvement et demander à l'étudiant s'il est prêt."""


def prewarm(proc: JobProcess):
    """Préchargement des modèles pour des réponses plus rapides."""
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """
    Point d'entrée principal de l'agent vocal.
    Appelé automatiquement quand un participant rejoint une room evalora-*.
    """
    logger.info(f"Agent joining room: {ctx.room.name}")

    # Connexion à la room (audio uniquement pour optimiser)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Créer l'agent vocal avec ElevenLabs TTS
    agent = Agent(
        instructions=AGENT_INSTRUCTIONS,
        stt=openai.STT(language="fr"),
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=elevenlabs.TTS(
            voice_id=ELEVENLABS_VOICE_ID,
            model="eleven_turbo_v2_5",
        ),
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=True,
    )

    # Créer la session
    session = AgentSession()

    # Stockage des transcriptions
    transcript_entries = []

    @session.on("conversation_item_added")
    def on_conversation_item(event):
        """Capture tous les messages (user et assistant)"""
        item = event.item
        if hasattr(item, 'role') and hasattr(item, 'content'):
            # Extraire le texte du content
            text = ""
            if isinstance(item.content, list):
                for c in item.content:
                    if hasattr(c, 'text'):
                        text += c.text
            elif hasattr(item.content, 'text'):
                text = item.content.text
            else:
                text = str(item.content)

            if text:
                logger.info(f"{item.role}: {text}")
                transcript_entries.append({
                    "role": "user" if item.role == "user" else "assistant",
                    "text": text,
                    "timestamp": datetime.utcnow().isoformat()
                })

    # Démarrer la session (SANS participant - c'est la nouvelle API)
    await session.start(agent=agent, room=ctx.room)

    logger.info("Voice session started - agent is ready to converse")

    # Envoyer message d'accueil
    await session.say("Bonjour ! Je suis votre examinateur pour cet exercice. Êtes-vous prêt à commencer ?")

    # Attendre que la room soit fermée ou le participant déconnecté
    shutdown_event = asyncio.Event()

    def on_participant_disconnected(participant):
        logger.info(f"Participant disconnected: {participant.identity}")
        shutdown_event.set()

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    # Attendre la déconnexion ou timeout de 30 minutes
    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=1800)
    except asyncio.TimeoutError:
        logger.info("Session timeout after 30 minutes")

    # Envoyer la transcription au backend
    if transcript_entries:
        await send_transcription(ctx.room.name, transcript_entries)

    logger.info(f"Agent finished with {len(transcript_entries)} transcript entries")


async def send_transcription(room_name: str, transcript: list):
    """Envoie la transcription au backend FastAPI."""
    try:
        # Extraire le session_id du nom de la room (format: evalora-{session_id})
        session_id = room_name.replace("evalora-", "")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/voice-agent/transcription",
                json={
                    "session_id": session_id,
                    "room_name": room_name,
                    "transcript": transcript
                },
                timeout=10.0
            )

            if response.status_code == 200:
                logger.info(f"Transcription sent successfully for session {session_id}")
            else:
                logger.error(f"Failed to send transcription: {response.status_code}")

    except Exception as e:
        logger.error(f"Error sending transcription: {e}")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
