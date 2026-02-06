"""
Evalora Voice Agent - Phase 1: Accueil et Consignes

Joins LiveKit rooms "evalora-*", speaks 7 scripted sequences,
detects "Je suis prêt", then transitions to listening mode (Phase 2).

Requires Python >= 3.10, < 3.14
"""
import os
import json
import logging
import asyncio
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import Agent, AgentSession
from livekit.plugins import openai, silero, elevenlabs

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evalora-agent")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "8qnuneLiGjGrT4A62CCe")

# Mots-clés pour détecter "Je suis prêt"
READY_KEYWORDS = [
    "je suis prêt", "je suis prête", "prêt", "prête",
    "c'est bon", "on y va", "allons-y", "je suis pret",
    "pret", "prete", "ready", "go"
]


async def fetch_session_context(session_id: str) -> dict | None:
    """Fetches student_name, avatar_id from the backend."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BACKEND_URL}/api/session/{session_id}",
                timeout=5.0,
            )
            if r.status_code != 200:
                logger.warning(f"Session fetch failed: {r.status_code}")
                return None
            data = r.json()
            return {
                "student_name": data.get("student_name") or "etudiant",
                "avatar_id": data.get("avatar_id") or "clea",
            }
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        return None


async def fetch_avatar_config(avatar_id: str) -> dict | None:
    """Fetches avatar config including elevenlabs_voice_id and register."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BACKEND_URL}/api/avatar/{avatar_id}",
                timeout=5.0,
            )
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching avatar config: {e}")
        return None


async def fetch_phase1_sequences(avatar_id: str, student_name: str) -> list[dict] | None:
    """Fetches the 7 Phase 1 sequences for the avatar."""
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BACKEND_URL}/api/avatar/{avatar_id}/phase-1-sequences",
                params={"student_name": student_name},
                timeout=5.0,
            )
            if r.status_code != 200:
                logger.warning(f"Phase 1 sequences fetch failed: {r.status_code}")
                return None
            data = r.json()
            return data.get("sequences", [])
    except Exception as e:
        logger.error(f"Error fetching Phase 1 sequences: {e}")
        return None


async def send_transcription_entry(room_name: str, entry: dict):
    """Envoie une entrée de transcription au backend en temps réel."""
    session_id = room_name.replace("evalora-", "")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BACKEND_URL}/api/voice-agent/transcription/append",
                json={
                    "session_id": session_id,
                    "room_name": room_name,
                    "entry": entry,
                },
                timeout=5.0,
            )
            if response.status_code != 200:
                logger.warning(f"Append transcription: {response.status_code}")
    except Exception as e:
        logger.warning(f"Error appending transcription entry: {e}")


async def send_event(room: rtc.Room, event_type: str, data: dict = None):
    """Envoie un event au frontend via DataChannel."""
    payload = {"event": event_type}
    if data:
        payload.update(data)
    try:
        await room.local_participant.publish_data(
            json.dumps(payload).encode(),
            topic="exam",
        )
        logger.info(f"Event sent: {event_type}")
    except Exception as e:
        logger.warning(f"Error sending event: {e}")


def is_ready_command(text: str) -> bool:
    """Vérifie si le texte contient une commande 'Je suis prêt'."""
    text_lower = text.lower().strip()
    for keyword in READY_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"Agent joining room: {ctx.room.name}")

    session_id = ctx.room.name.replace("evalora-", "")
    if not session_id:
        logger.error("Invalid room name")
        return

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Get session context
    ctx_data = await fetch_session_context(session_id)
    if not ctx_data:
        ctx_data = {"student_name": "etudiant", "avatar_id": "clea"}
    student_name = ctx_data["student_name"]
    avatar_id = ctx_data["avatar_id"]
    logger.info(f"Session context: student={student_name}, avatar={avatar_id}")

    # Get avatar config for voice
    avatar_config = await fetch_avatar_config(avatar_id)
    voice_id = ELEVENLABS_VOICE_ID
    if avatar_config and avatar_config.get("elevenlabs_voice_id"):
        voice_id = avatar_config["elevenlabs_voice_id"]

    is_tu = avatar_config and avatar_config.get("register") == "tutoiement"
    logger.info(f"Avatar config: voice_id={voice_id}, register={'tu' if is_tu else 'vous'}")

    # Fetch Phase 1 sequences
    sequences = await fetch_phase1_sequences(avatar_id, student_name)
    if not sequences:
        logger.error("Failed to fetch Phase 1 sequences, using fallback")
        sequences = [{"id": 1, "text": f"Bonjour {student_name}! Bienvenue à cette simulation d'examen."}]

    logger.info(f"Loaded {len(sequences)} Phase 1 sequences")

    # Transcript storage
    transcript_entries = []
    ready_detected = False

    # Build initial system prompt for Phase 1 (scripted mode)
    system_prompt = f"""Tu es un examinateur FLE bienveillant. Tu dois lire les consignes à l'étudiant {student_name}.
Pour l'instant, tu ne fais que lire les séquences qu'on te donne. Ne réponds pas aux questions, reste sur ton script.
Après avoir lu toutes les consignes, tu attendras que l'étudiant dise "Je suis prêt"."""

    # Create TTS and STT
    tts = elevenlabs.TTS(
        voice_id=voice_id,
        model="eleven_turbo_v2_5",
    )
    stt = openai.STT(language="fr")

    # Create agent
    agent = Agent(
        instructions=system_prompt,
        stt=stt,
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=False,  # Don't allow interruptions during consignes
    )

    # Create session
    session = AgentSession()

    # Track conversation for transcription
    @session.on("agent_speech_committed")
    def on_agent_speech(msg):
        text = msg.content if hasattr(msg, 'content') else str(msg)
        if text:
            logger.info(f"Agent said: {text[:50]}...")
            entry = {
                "role": "assistant",
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "consignes" if not ready_detected else "monologue",
            }
            transcript_entries.append(entry)
            asyncio.create_task(send_transcription_entry(ctx.room.name, entry))

    @session.on("user_speech_committed")
    def on_user_speech(msg):
        nonlocal ready_detected
        text = msg.content if hasattr(msg, 'content') else str(msg)
        if text:
            logger.info(f"User said: {text}")
            entry = {
                "role": "user",
                "text": text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "consignes" if not ready_detected else "monologue",
            }
            transcript_entries.append(entry)
            asyncio.create_task(send_transcription_entry(ctx.room.name, entry))

            # Check for ready command during Phase 1
            if not ready_detected and is_ready_command(text):
                ready_detected = True
                logger.info("'Je suis prêt' detected!")
                asyncio.create_task(send_event(ctx.room, "ready_detected"))
                asyncio.create_task(send_event(ctx.room, "transition_to_monologue"))

    # Start session
    await session.start(agent=agent, room=ctx.room)
    logger.info("Agent session started")

    # Send phase started event
    await send_event(ctx.room, "phase_started", {"phase": "consignes"})

    # ========== PHASE 1: Speak the 7 sequences ==========
    logger.info("Starting Phase 1: Consignes")

    for seq in sequences:
        seq_id = seq.get("id", 0)
        seq_text = seq.get("text", "")

        if not seq_text:
            continue

        logger.info(f"Speaking sequence {seq_id}: {seq_text[:50]}...")

        try:
            # Use session.say() which handles TTS properly
            await session.say(seq_text, allow_interruptions=False)
            logger.info(f"Completed sequence {seq_id}")
        except Exception as e:
            logger.error(f"Error speaking sequence {seq_id}: {e}")

        # Pause between sequences
        await asyncio.sleep(1.5)

    # ========== Listen for "Je suis prêt" ==========
    logger.info("Phase 1 sequences complete. Listening for 'Je suis prêt'...")
    await send_event(ctx.room, "listening_for_ready", {"active": True})

    # Wait for ready command (detected in user_speech_committed handler) or timeout
    timeout = 120  # 2 minutes
    start_time = asyncio.get_event_loop().time()

    while not ready_detected:
        await asyncio.sleep(0.5)
        if asyncio.get_event_loop().time() - start_time > timeout:
            logger.info("Timeout waiting for 'Je suis prêt', proceeding anyway")
            ready_detected = True
            await send_event(ctx.room, "transition_to_monologue")
            break

    # ========== Transition to Phase 2: Monologue ==========
    logger.info("Transitioning to Phase 2: Monologue")

    # Update agent instructions for Phase 2 (listening mode)
    if is_tu:
        phase2_prompt = f"""Tu es un examinateur FLE. L'étudiant {student_name} est maintenant en phase de monologue.
Tu dois rester SILENCIEUX pendant qu'il présente son document.
Ne parle PAS sauf si l'étudiant te pose une question directe ou dit "j'ai terminé".
Écoute attentivement et prends des notes mentales pour le débat qui suivra."""
    else:
        phase2_prompt = f"""Vous êtes un examinateur FLE. L'étudiant {student_name} est maintenant en phase de monologue.
Vous devez rester SILENCIEUX pendant qu'il présente son document.
Ne parlez PAS sauf si l'étudiant vous pose une question directe ou dit "j'ai terminé".
Écoutez attentivement et prenez des notes mentales pour le débat qui suivra."""

    # Update agent with new instructions
    agent.instructions = phase2_prompt
    agent.allow_interruptions = True

    logger.info("Phase 2 started - Listening mode")

    # Wait for disconnection or timeout (30 min max)
    shutdown_event = asyncio.Event()

    def on_participant_disconnected(participant):
        logger.info(f"Participant disconnected: {participant.identity}")
        shutdown_event.set()

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=1800)
    except asyncio.TimeoutError:
        logger.info("Session timeout after 30 minutes")

    logger.info(f"Agent finished. Total transcript entries: {len(transcript_entries)}")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
