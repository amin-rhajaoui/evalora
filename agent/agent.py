"""
Evalora Voice Agent - Multi-agent architecture for FLE exam simulation

ConsignesAgent → MonologueAgent → DebatAgent → FeedbackAgent

Requires Python >= 3.10, < 3.14
"""
import os
import json
import logging
import asyncio
import unicodedata
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
    Agent,
    AgentSession,
)
from livekit.plugins import openai, silero, elevenlabs

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evalora-agent")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "8qnuneLiGjGrT4A62CCe")

# Keywords for detecting "Je suis prêt"
READY_KEYWORDS = [
    "je suis pret", "je suis prete", "pret", "prete",
    "c'est bon", "on y va", "allons-y", "ready", "go",
]

# Keywords for detecting "J'ai terminé"
FINISHED_KEYWORDS = [
    "j'ai termine", "j'ai terminee", "j'ai fini",
    "c'est fini", "c'est termine",
    "j'ai fini ma presentation", "j'ai fini mon monologue",
    "voila c'est fini",
]


def normalize_text(text: str) -> str:
    """Normalize unicode accents and lowercase for keyword matching."""
    nfkd = unicodedata.normalize("NFKD", text.lower().strip())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def is_ready_command(text: str) -> bool:
    normalized = normalize_text(text)
    return any(kw in normalized for kw in READY_KEYWORDS)


def is_finished_command(text: str) -> bool:
    normalized = normalize_text(text)
    if is_ready_command(text):
        return False
    return any(kw in normalized for kw in FINISHED_KEYWORDS)


# ========== HTTP helpers ==========

async def fetch_session_context(session_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/session/{session_id}", timeout=5.0)
            if r.status_code != 200:
                return None
            data = r.json()
            return {
                "student_name": data.get("student_name") or "etudiant",
                "avatar_id": data.get("avatar_id") or "clea",
                "document_id": data.get("document_id"),
            }
    except Exception as e:
        logger.error(f"Error fetching session: {e}")
        return None


async def fetch_avatar_config(avatar_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/avatar/{avatar_id}", timeout=5.0)
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching avatar config: {e}")
        return None


async def fetch_phase1_sequences(avatar_id: str, student_name: str) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{BACKEND_URL}/api/avatar/{avatar_id}/phase-1-sequences",
                params={"student_name": student_name},
                timeout=5.0,
            )
            if r.status_code != 200:
                return []
            return r.json().get("sequences", [])
    except Exception as e:
        logger.error(f"Error fetching Phase 1 sequences: {e}")
        return []


async def fetch_debate_questions(document_id: str) -> list[str]:
    if not document_id:
        return []
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/documents/{document_id}/questions", timeout=5.0)
            if r.status_code != 200:
                return []
            return r.json().get("questions", [])
    except Exception as e:
        logger.warning(f"Error fetching debate questions: {e}")
        return []


async def fetch_phase_messages(avatar_id: str, phase: str) -> list[str]:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/avatar/{avatar_id}/messages/{phase}", timeout=5.0)
            if r.status_code != 200:
                return []
            return r.json().get("messages", [])
    except Exception as e:
        logger.warning(f"Error fetching phase messages {phase}: {e}")
        return []


async def send_transcription_entry(room_name: str, entry: dict):
    session_id = room_name.replace("evalora-", "")
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/api/voice-agent/transcription/append",
                json={"session_id": session_id, "room_name": room_name, "entry": entry},
                timeout=5.0,
            )
    except Exception as e:
        logger.warning(f"Error appending transcription entry: {e}")


async def call_transition_phase(session_id: str, new_phase: str, phase_duration: int | None = None):
    try:
        async with httpx.AsyncClient() as client:
            payload = {"new_phase": new_phase}
            if phase_duration is not None:
                payload["phase_duration"] = phase_duration
            await client.post(f"{BACKEND_URL}/api/session/{session_id}/transition", json=payload, timeout=5.0)
    except Exception as e:
        logger.warning(f"Error calling transition_phase: {e}")


async def call_auto_evaluate(session_id: str) -> dict | None:
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{BACKEND_URL}/api/evaluation/auto-evaluate",
                params={"session_id": session_id},
                timeout=30.0,
            )
            if r.status_code == 200:
                return r.json()
            logger.warning(f"Auto-evaluate failed: {r.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error calling auto-evaluate: {e}")
        return None


async def fetch_feedback_text(session_id: str, avatar_id: str | None = None) -> str | None:
    try:
        params = f"?avatar_id={avatar_id}" if avatar_id else ""
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/evaluation/{session_id}{params}", timeout=10.0)
            if r.status_code != 200:
                return None
            data = r.json()
            score = data.get("total_score", 0)
            grade = data.get("grade_letter", "")
            summary = data.get("summary", "")
            strengths = data.get("strengths", [])
            improvements = data.get("improvements", [])

            parts = [
                f"Votre note est de {score:.1f} sur 20, mention {grade}.",
                summary,
            ]
            if strengths:
                parts.append("Vos points forts : " + ". ".join(strengths[:2]) + ".")
            if improvements:
                parts.append("Pour progresser : " + ". ".join(improvements[:2]) + ".")
            return " ".join(parts)
    except Exception as e:
        logger.error(f"Error fetching feedback text: {e}")
        return None


async def send_event(room: rtc.Room, event_type: str, data: dict = None):
    payload = {"event": event_type}
    if data:
        payload.update(data)
    try:
        await room.local_participant.publish_data(
            json.dumps(payload).encode(), topic="exam",
        )
        logger.info(f"Event sent: {event_type}")
    except Exception as e:
        logger.warning(f"Error sending event: {e}")


# ========== Agent Classes ==========

class ConsignesAgent(Agent):
    """Phase 1: Speaks the 7 scripted sequences, then waits for 'Je suis prêt'."""

    def __init__(self, sequences: list[dict], is_tu: bool):
        super().__init__(
            instructions="Tu es un examinateur FLE. Tu viens de lire les consignes. Ne dis plus rien, attends que l'étudiant dise 'Je suis prêt'."
            if is_tu else
            "Vous êtes un examinateur FLE. Vous venez de lire les consignes. Ne dites plus rien, attendez que l'étudiant dise 'Je suis prêt'.",
        )
        self._sequences = sequences
        self._is_tu = is_tu

    async def on_enter(self) -> None:
        ctx = self.session.userdata
        room = ctx["room"]
        room_name = ctx["room_name"]

        await send_event(room, "phase_started", {"phase": "consignes"})
        logger.info("Starting Phase 1: Consignes")

        for seq in self._sequences:
            seq_text = seq.get("text", "")
            if not seq_text:
                continue
            seq_id = seq.get("id", 0)
            logger.info(f"Speaking sequence {seq_id}: {seq_text[:60]}...")

            try:
                await self.session.say(seq_text, allow_interruptions=False)
            except Exception as e:
                logger.error(f"Error speaking sequence {seq_id}: {e}")

            entry = {
                "role": "assistant", "text": seq_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "consignes", "sequence": seq_id,
            }
            ctx["transcript"].append(entry)
            asyncio.create_task(send_transcription_entry(room_name, entry))
            await asyncio.sleep(1.2)

        logger.info("Consignes complete. Listening for 'Je suis prêt'...")
        await send_event(room, "listening_for_ready", {"active": True})


class MonologueAgent(Agent):
    """Phase 2: Silent listener. Transcribes only, no LLM/TTS output."""

    def __init__(self, is_tu: bool):
        super().__init__(
            instructions="SILENCE ABSOLU. Ne génère aucune réponse.",
        )
        self._is_tu = is_tu

    async def llm_node(self, chat_ctx, tools, model_settings):
        """Override: produce no LLM output during monologue."""
        return
        yield  # make it an async generator

    async def on_enter(self) -> None:
        ctx = self.session.userdata
        room = ctx["room"]
        ctx["monologue_start"] = asyncio.get_event_loop().time()
        await send_event(room, "transition_to_monologue")
        await call_transition_phase(ctx["session_id"], "monologue", None)
        logger.info("Phase 2: Monologue - Agent silent, transcribing only")


class DebatAgent(Agent):
    """Phase 3: Interactive debate - asks questions, responds contextually."""

    def __init__(self, questions_bloc: str, is_tu: bool, avatar_config: dict):
        register = "tu" if is_tu else "vous"
        name = avatar_config.get("name", "l'examinateur")
        personality = avatar_config.get("personality", "")
        feedback_tone = avatar_config.get("feedback_tone", "")

        if is_tu:
            instructions = f"""Tu es {name}, examinateur/examinatrice FLE. {personality}
Tu tutoies l'étudiant.

Tu es maintenant en PHASE DÉBAT. Pose des questions et discute.
Questions suggérées :
{questions_bloc}

Règles :
- Pose UNE question à la fois
- Écoute la réponse, réagis brièvement (1-2 phrases)
- Puis passe à la question suivante ou approfondis
- Après 5 questions posées environ, conclus le débat naturellement
- Ton : {feedback_tone}
- Ne réponds JAMAIS en anglais, reste toujours en français"""
        else:
            instructions = f"""Vous êtes {name}, examinateur/examinatrice FLE. {personality}
Vous vouvoyez l'étudiant.

Vous êtes maintenant en PHASE DÉBAT. Posez des questions et discutez.
Questions suggérées :
{questions_bloc}

Règles :
- Posez UNE question à la fois
- Écoutez la réponse, réagissez brièvement (1-2 phrases)
- Puis passez à la question suivante ou approfondissez
- Après 5 questions posées environ, concluez le débat naturellement
- Ton : {feedback_tone}
- Ne répondez JAMAIS en anglais, restez toujours en français"""

        super().__init__(instructions=instructions)
        self._questions_bloc = questions_bloc
        self._is_tu = is_tu
        self._question_count = 0

    async def on_enter(self) -> None:
        ctx = self.session.userdata
        room = ctx["room"]
        avatar_id = ctx["avatar_id"]
        room_name = ctx["room_name"]

        # Compute monologue duration
        mono_start = ctx.get("monologue_start")
        duration = int(asyncio.get_event_loop().time() - mono_start) if mono_start else None

        await send_event(room, "transition_to_debat")
        await call_transition_phase(ctx["session_id"], "debat", duration)
        logger.info("Phase 3: Débat - Agent interactive")

        # Say transition messages
        for phase_name in ("monologue_end", "debat_start"):
            msgs = await fetch_phase_messages(avatar_id, phase_name)
            for msg in msgs:
                if msg:
                    await self.session.say(msg, allow_interruptions=True)
                    entry = {
                        "role": "assistant", "text": msg,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "phase": "debat",
                    }
                    ctx["transcript"].append(entry)
                    asyncio.create_task(send_transcription_entry(room_name, entry))
                    await asyncio.sleep(0.5)

        # Generate the first debate question
        await self.session.generate_reply(
            instructions="Pose ta première question de débat à l'étudiant."
            if self._is_tu else
            "Posez votre première question de débat à l'étudiant.",
        )


class FeedbackAgent(Agent):
    """Phase 4: Reads evaluation feedback aloud."""

    def __init__(self, is_tu: bool):
        super().__init__(
            instructions="Tu lis le feedback de l'évaluation à l'étudiant."
            if is_tu else
            "Vous lisez le feedback de l'évaluation à l'étudiant.",
        )
        self._is_tu = is_tu

    async def on_enter(self) -> None:
        ctx = self.session.userdata
        room = ctx["room"]
        session_id = ctx["session_id"]
        avatar_id = ctx["avatar_id"]
        room_name = ctx["room_name"]

        # Compute debat duration
        debat_start = ctx.get("debat_start")
        duration = int(asyncio.get_event_loop().time() - debat_start) if debat_start else None
        await call_transition_phase(session_id, "feedback", duration)
        await send_event(room, "phase_started", {"phase": "feedback"})

        logger.info("Phase 4: Feedback")

        # Trigger auto-evaluation
        eval_result = await call_auto_evaluate(session_id)
        if eval_result:
            logger.info(f"Auto-evaluate done: {eval_result.get('total_score')}/20")

        # Get feedback text
        feedback_text = await fetch_feedback_text(session_id, avatar_id)
        if feedback_text:
            await self.session.say(feedback_text, allow_interruptions=False)
            entry = {
                "role": "assistant", "text": feedback_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "phase": "feedback",
            }
            ctx["transcript"].append(entry)
            asyncio.create_task(send_transcription_entry(room_name, entry))
        else:
            fallback = "Merci pour votre participation. Votre évaluation est en cours de préparation."
            await self.session.say(fallback, allow_interruptions=False)

        # Signal exam complete
        await send_event(room, "exam_complete")
        logger.info("Exam complete, feedback delivered")


# ========== Main entrypoint ==========

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    logger.info(f"Agent joining room: {ctx.room.name}")

    session_id = ctx.room.name.replace("evalora-", "")
    if not session_id:
        logger.error("Invalid room name")
        return

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Fetch session context
    ctx_data = await fetch_session_context(session_id)
    if not ctx_data:
        ctx_data = {"student_name": "etudiant", "avatar_id": "clea", "document_id": None}
    student_name = ctx_data["student_name"]
    avatar_id = ctx_data["avatar_id"]
    document_id = ctx_data.get("document_id")
    logger.info(f"Session: student={student_name}, avatar={avatar_id}, document={document_id}")

    # Fetch avatar config
    avatar_config = await fetch_avatar_config(avatar_id) or {}
    voice_id = avatar_config.get("elevenlabs_voice_id") or DEFAULT_VOICE_ID
    is_tu = avatar_config.get("register") == "tutoiement"
    logger.info(f"Avatar: voice_id={voice_id}, register={'tu' if is_tu else 'vous'}")

    # Fetch sequences and questions
    sequences = await fetch_phase1_sequences(avatar_id, student_name)
    if not sequences:
        sequences = [{"id": 1, "text": f"Bonjour {student_name}! Bienvenue à cette simulation d'examen."}]

    debate_questions = await fetch_debate_questions(document_id) if document_id else []
    questions_bloc = "\n".join(f"- {q}" for q in debate_questions) if debate_questions else "(Pose des questions sur le document présenté.)"

    logger.info(f"Loaded {len(sequences)} sequences, {len(debate_questions)} questions")

    # Shared state via userdata
    shared_state = {
        "room": ctx.room,
        "room_name": ctx.room.name,
        "session_id": session_id,
        "student_name": student_name,
        "avatar_id": avatar_id,
        "document_id": document_id,
        "is_tu": is_tu,
        "transcript": [],
        "ready_detected": False,
        "debat_started": False,
        "current_phase": "consignes",
        "monologue_start": None,
        "debat_start": None,
        "debat_question_count": 0,
    }

    # Create TTS and STT
    tts = elevenlabs.TTS(voice_id=voice_id, model="eleven_turbo_v2_5")
    stt = openai.STT(language="fr")

    # Create agents
    consignes_agent = ConsignesAgent(sequences=sequences, is_tu=is_tu)
    monologue_agent = MonologueAgent(is_tu=is_tu)
    debat_agent = DebatAgent(questions_bloc=questions_bloc, is_tu=is_tu, avatar_config=avatar_config)
    feedback_agent = FeedbackAgent(is_tu=is_tu)

    # Create session
    session = AgentSession(
        stt=stt,
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
        allow_interruptions=False,
        userdata=shared_state,
    )

    # ========== Event handlers ==========

    @session.on("user_input_transcribed")
    def on_user_input(ev):
        text = ev.transcript if hasattr(ev, "transcript") else str(ev)
        if not text:
            return

        state = session.userdata
        phase = state["current_phase"]
        logger.info(f"User said ({phase}): {text}")

        entry = {
            "role": "user", "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": phase,
        }
        state["transcript"].append(entry)
        asyncio.create_task(send_transcription_entry(ctx.room.name, entry))

        # Consignes → detect "Je suis prêt"
        if not state["ready_detected"] and is_ready_command(text):
            state["ready_detected"] = True
            state["current_phase"] = "monologue"
            logger.info("'Je suis prêt' detected via voice!")
            asyncio.create_task(send_event(ctx.room, "ready_detected"))
            session.update_agent(monologue_agent)

        # Monologue → detect "J'ai terminé"
        elif state["current_phase"] == "monologue" and not state["debat_started"] and is_finished_command(text):
            state["debat_started"] = True
            state["current_phase"] = "debat"
            state["debat_start"] = asyncio.get_event_loop().time()
            logger.info("'J'ai terminé' detected via voice!")
            session.update_agent(debat_agent)

    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        """Track agent responses in debat to count questions."""
        state = session.userdata
        if state["current_phase"] == "debat":
            item = ev.item if hasattr(ev, "item") else None
            if item and hasattr(item, "role") and item.role == "assistant":
                state["debat_question_count"] = state.get("debat_question_count", 0) + 1
                text = ""
                if hasattr(item, "text_content"):
                    text = item.text_content() or ""
                elif hasattr(item, "content"):
                    text = str(item.content) or ""
                if text:
                    entry = {
                        "role": "assistant", "text": text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "phase": "debat",
                    }
                    state["transcript"].append(entry)
                    asyncio.create_task(send_transcription_entry(ctx.room.name, entry))

                # After ~10 exchanges (5 questions + 5 responses from agent side), end debat
                if state["debat_question_count"] >= 6:
                    logger.info("Debat complete (5+ questions asked), moving to feedback")
                    state["current_phase"] = "feedback"
                    session.update_agent(feedback_agent)

    # Listen for DataChannel events from frontend buttons
    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        state = session.userdata
        try:
            payload = json.loads(data.data.decode())
            ev = payload.get("event")

            if ev == "student_ready" and not state["ready_detected"]:
                state["ready_detected"] = True
                state["current_phase"] = "monologue"
                logger.info("'Je suis prêt' via button!")
                asyncio.create_task(send_event(ctx.room, "ready_detected"))
                session.update_agent(monologue_agent)

            elif ev in ("student_finished", "monologue_timer_ended"):
                if state["current_phase"] == "monologue" and not state["debat_started"]:
                    state["debat_started"] = True
                    state["current_phase"] = "debat"
                    state["debat_start"] = asyncio.get_event_loop().time()
                    session.update_agent(debat_agent)

            elif ev == "end_exam":
                if state["current_phase"] != "feedback":
                    state["current_phase"] = "feedback"
                    session.update_agent(feedback_agent)

        except Exception as e:
            logger.warning(f"Error parsing data received: {e}")

    # Start session with ConsignesAgent
    await session.start(agent=consignes_agent, room=ctx.room)
    logger.info("Agent session started")

    # Wait for disconnection or timeout
    shutdown_event = asyncio.Event()

    def on_participant_disconnected(participant):
        logger.info(f"Participant disconnected: {participant.identity}")
        shutdown_event.set()

    ctx.room.on("participant_disconnected", on_participant_disconnected)

    try:
        await asyncio.wait_for(shutdown_event.wait(), timeout=2400)  # 40 min max
    except asyncio.TimeoutError:
        logger.info("Session timeout after 40 minutes")

    logger.info(f"Agent finished. Total transcript entries: {len(session.userdata['transcript'])}")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
