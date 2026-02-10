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
from pathlib import Path
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
    RunContext,
    function_tool,
)
from livekit.plugins import openai, silero, elevenlabs
from livekit.agents.utils.audio import audio_frames_from_file

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("evalora-agent")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEFAULT_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "WQKwBV2Uzw1gSGr69N8I")

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

# Mapping avatar_id → pre-recorded MP3 consignes file
PROJECT_ROOT = Path(__file__).parent.parent
CONSIGNES_AUDIO = {
    "clea": PROJECT_ROOT / "CLEA_Mylene \u2013 Spontaneous and Casual_pvc_sp100_s50_sb70_v3.mp3",
    "alex": PROJECT_ROOT / "ALEX_Jules - conversational_pvc_sp105_s85_sb30_v3.mp3",
    "karim": PROJECT_ROOT / "KARIM-Hugo - Warm and Grounded_pvc_sp100_s50_sb75_v3.mp3",
    "claire": PROJECT_ROOT / "Claire-02-10T20_09_02_Koraly \u2013 E-learning Instructor_pvc_sp85_s90_sb100_v3.mp3",
}


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


async def fetch_document(document_id: str) -> dict | None:
    if not document_id:
        return None
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{BACKEND_URL}/api/documents/{document_id}", timeout=5.0)
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as e:
        logger.warning(f"Error fetching document: {e}")
        return None


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


async def save_debate_qa(session_id: str, question_number: int, question_text: str, answer_text: str | None = None):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{BACKEND_URL}/api/voice-agent/debate-qa",
                json={
                    "session_id": session_id,
                    "question_number": question_number,
                    "question_text": question_text,
                    "answer_text": answer_text,
                },
                timeout=5.0,
            )
    except Exception as e:
        logger.warning(f"Error saving debate QA: {e}")


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
    """Phase 1: Plays pre-recorded MP3 consignes (or TTS fallback), then waits for 'Je suis prêt'."""

    def __init__(self, sequences: list[dict], is_tu: bool, avatar_id: str):
        super().__init__(
            instructions="Tu es un examinateur FLE. Tu viens de lire les consignes. Ne dis plus rien, attends que l'étudiant dise 'Je suis prêt'."
            if is_tu else
            "Vous êtes un examinateur FLE. Vous venez de lire les consignes. Ne dites plus rien, attendez que l'étudiant dise 'Je suis prêt'.",
        )
        self._sequences = sequences
        self._is_tu = is_tu
        self._avatar_id = avatar_id

    async def llm_node(self, chat_ctx, tools, model_settings):
        """Override: no LLM output during consignes (all speech is scripted via session.say)."""
        return
        yield  # make it an async generator

    async def on_enter(self) -> None:
        ctx = self.session.userdata
        room = ctx["room"]
        room_name = ctx["room_name"]

        await send_event(room, "phase_started", {"phase": "consignes"})
        logger.info("Starting Phase 1: Consignes (MP3)")

        # Play the pre-recorded MP3
        mp3_path = CONSIGNES_AUDIO.get(self._avatar_id)
        if mp3_path and mp3_path.exists():
            logger.info(f"Playing consignes MP3: {mp3_path.name}")
            try:
                await self.session.say(
                    "",
                    audio=audio_frames_from_file(str(mp3_path)),
                    allow_interruptions=False,
                )
            except Exception as e:
                logger.error(f"Error playing consignes MP3: {e}")
                await self._play_tts_fallback(ctx, room_name)
        else:
            logger.warning(f"No MP3 found for avatar {self._avatar_id}, using TTS fallback")
            await self._play_tts_fallback(ctx, room_name)

        # Log consignes text into transcript
        for seq in self._sequences:
            seq_text = seq.get("text", "")
            if seq_text:
                entry = {
                    "role": "assistant", "text": seq_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "phase": "consignes", "sequence": seq.get("id", 0),
                }
                ctx["transcript"].append(entry)
                asyncio.create_task(send_transcription_entry(room_name, entry))

        logger.info("Consignes complete. Listening for 'Je suis prêt'...")
        await send_event(room, "listening_for_ready", {"active": True})

    async def _play_tts_fallback(self, ctx, room_name):
        """Fallback: read sequences via TTS if MP3 is not available."""
        for seq in self._sequences:
            if ctx.get("skip_consignes"):
                break
            seq_text = seq.get("text", "")
            if not seq_text:
                continue
            try:
                await self.session.say(seq_text, allow_interruptions=False)
            except Exception as e:
                logger.error(f"Error speaking sequence: {e}")
            await asyncio.sleep(1.2)


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
        avatar_id = ctx["avatar_id"]
        room_name = ctx["room_name"]

        await send_event(room, "transition_to_monologue")
        await call_transition_phase(ctx["session_id"], "monologue", None)
        logger.info("Phase 2: Monologue")

        # Say monologue introduction messages before going silent
        msgs = await fetch_phase_messages(avatar_id, "monologue_start")
        for msg in msgs:
            if msg:
                await self.session.say(msg, allow_interruptions=False)
                entry = {
                    "role": "assistant", "text": msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "phase": "monologue",
                }
                ctx["transcript"].append(entry)
                asyncio.create_task(send_transcription_entry(room_name, entry))
                await asyncio.sleep(0.5)

        # Start monologue timer after introduction
        ctx["monologue_start"] = asyncio.get_event_loop().time()
        logger.info("Monologue timer started - Agent silent, transcribing only")


class DebatAgent(Agent):
    """Phase 3: Interactive debate - asks questions, responds contextually."""

    def __init__(self, questions_bloc: str, is_tu: bool, avatar_config: dict, doc_context: str = ""):
        register = "tu" if is_tu else "vous"
        name = avatar_config.get("name", "l'examinateur")
        personality = avatar_config.get("personality", "")
        feedback_tone = avatar_config.get("feedback_tone", "")

        doc_section = f"\n\n{doc_context}\n" if doc_context else ""

        if is_tu:
            instructions = f"""Tu es {name}, examinateur/examinatrice FLE. {personality}
Tu tutoies l'étudiant.

Tu es en PHASE DÉBAT. Tu dois poser 5 questions à l'étudiant sur le document.
{doc_section}
Questions suggérées :
{questions_bloc}

RÈGLES STRICTES :
- Pose UNE SEULE question courte et directe (1-2 phrases maximum)
- NE FAIS AUCUNE introduction, préambule, ou explication avant ta question
- Après chaque réponse de l'étudiant, réagis BRIÈVEMENT (1 phrase) puis enchaîne avec la question suivante
- ATTENDS TOUJOURS que l'étudiant ait fini de répondre avant de parler
- Ne répète JAMAIS une question ou une idée déjà évoquée
- Tu dois poser exactement 5 questions au total
- Ton : {feedback_tone}
- Ne réponds JAMAIS en anglais, reste toujours en français
- Tes questions doivent être en rapport avec le document et son contenu
- Quand tu as posé tes 5 questions, appelle la fonction end_debate"""
        else:
            instructions = f"""Vous êtes {name}, examinateur/examinatrice FLE. {personality}
Vous vouvoyez l'étudiant.

Vous êtes en PHASE DÉBAT. Vous devez poser 5 questions à l'étudiant sur le document.
{doc_section}
Questions suggérées :
{questions_bloc}

RÈGLES STRICTES :
- Posez UNE SEULE question courte et directe (1-2 phrases maximum)
- NE FAITES AUCUNE introduction, préambule, ou explication avant votre question
- Après chaque réponse de l'étudiant, réagissez BRIÈVEMENT (1 phrase) puis enchaînez avec la question suivante
- ATTENDEZ TOUJOURS que l'étudiant ait fini de répondre avant de parler
- Ne répétez JAMAIS une question ou une idée déjà évoquée
- Vous devez poser exactement 5 questions au total
- Ton : {feedback_tone}
- Ne répondez JAMAIS en anglais, restez toujours en français
- Vos questions doivent être en rapport avec le document et son contenu
- Quand vous avez posé vos 5 questions, appelez la fonction end_debate"""

        super().__init__(instructions=instructions, allow_interruptions=True)
        self._questions_bloc = questions_bloc
        self._is_tu = is_tu
        self._question_count = 0
        self._finished = False

    @function_tool()
    async def end_debate(self, context: RunContext) -> Agent:
        """Termine le débat et passe à l'évaluation. Appelle cette fonction quand :
        - Tu as posé toutes tes questions
        - L'étudiant indique qu'il a terminé
        - La conversation a naturellement atteint sa conclusion
        """
        state = context.userdata
        if state["current_phase"] != "debat":
            return self
        state["current_phase"] = "feedback"
        closing = (
            "Merci beaucoup, c'est la fin du débat. Je vais maintenant te donner ton évaluation."
            if state["is_tu"] else
            "Merci beaucoup, c'est la fin du débat. Je vais maintenant vous donner votre évaluation."
        )
        await context.session.say(closing, allow_interruptions=False)
        return FeedbackAgent(is_tu=state["is_tu"])

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

        # Enable question counting now that transition messages are done
        ctx["debat_counting_active"] = True
        ctx["debat_question_count"] = 0
        ctx["debat_awaiting_response"] = False

        # Generate the first debate question
        await self.session.generate_reply(
            instructions="Pose directement ta première question sans aucune introduction ni préambule. Juste la question."
            if self._is_tu else
            "Posez directement votre première question sans aucune introduction ni préambule. Juste la question.",
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

        # Cleanup: delete room after a short delay
        async def _cleanup_room():
            await asyncio.sleep(10)
            try:
                async with httpx.AsyncClient() as client:
                    await client.delete(f"{BACKEND_URL}/api/livekit/room/{room_name}", timeout=5.0)
                logger.info(f"Room {room_name} deleted after feedback")
            except Exception:
                pass
        asyncio.create_task(_cleanup_room())


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

    document_data = await fetch_document(document_id) if document_id else None
    if document_data:
        doc_context = f"""Document de l'épreuve :
- Titre : {document_data.get('title', '')}
- Thème : {document_data.get('theme', '')}
- Source : {document_data.get('source', '')} ({document_data.get('date', '')})
- Texte : {document_data.get('text', '')}
- Mots-clés : {', '.join(document_data.get('keywords', []))}"""
    else:
        doc_context = ""

    logger.info(f"Loaded {len(sequences)} sequences, {len(debate_questions)} questions, document={'yes' if document_data else 'no'}")

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
        "debat_counting_active": False,
        "debat_awaiting_response": False,
        "debat_current_question": None,
        "debat_qa_pairs": [],
        "skip_consignes": False,
    }

    # Create TTS and STT
    tts = elevenlabs.TTS(voice_id=voice_id, model="eleven_turbo_v2_5")
    stt = openai.STT(language="fr")

    # Create agents
    consignes_agent = ConsignesAgent(sequences=sequences, is_tu=is_tu, avatar_id=avatar_id)
    monologue_agent = MonologueAgent(is_tu=is_tu)
    debat_agent = DebatAgent(questions_bloc=questions_bloc, is_tu=is_tu, avatar_config=avatar_config, doc_context=doc_context)
    feedback_agent = FeedbackAgent(is_tu=is_tu)

    # Create session
    session = AgentSession(
        stt=stt,
        llm=openai.LLM(model="gpt-4o-mini"),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=1.5,
        allow_interruptions=False,
        userdata=shared_state,
    )

    # ========== Shared helpers ==========

    async def _end_debat():
        """Shared transition: debat → feedback. Called from auto-5-questions, voice, button."""
        state = session.userdata
        if state["current_phase"] != "debat":
            return
        state["current_phase"] = "feedback"
        closing = (
            "Merci beaucoup, c'est la fin du débat. Je vais maintenant te donner ton évaluation."
            if state["is_tu"] else
            "Merci beaucoup, c'est la fin du débat. Je vais maintenant vous donner votre évaluation."
        )
        await session.say(closing, allow_interruptions=False)
        session.update_agent(feedback_agent)

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
            logger.info("'J'ai terminé' detected via voice during monologue!")
            session.update_agent(debat_agent)

        # Debat → detect "J'ai terminé"
        elif state["current_phase"] == "debat" and is_finished_command(text):
            logger.info("'J'ai terminé' detected via voice during debat!")
            asyncio.create_task(_end_debat())

    @session.on("conversation_item_added")
    def on_conversation_item(ev):
        """Track agent responses in debat to count questions, track Q&A, and auto-transition to feedback."""
        state = session.userdata
        if state["current_phase"] != "debat":
            return

        item = ev.item if hasattr(ev, "item") else None
        if not item:
            return

        role = getattr(item, "role", None)
        if not role:
            return

        # Extract text content
        text = ""
        if hasattr(item, "text_content"):
            tc = item.text_content
            text = tc() if callable(tc) else (tc or "")
        elif hasattr(item, "content"):
            text = str(item.content) or ""

        if not text:
            return

        # Save transcription entry for both user and assistant
        entry = {
            "role": role, "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "debat",
        }
        state["transcript"].append(entry)
        asyncio.create_task(send_transcription_entry(ctx.room.name, entry))

        # Track Q&A pairs (only count after transition messages are done)
        if role == "assistant":
            if not state.get("debat_counting_active"):
                logger.info(f"Debat transition message (not counted): {text[:80]}...")
                return

            # Store current question text
            state["debat_current_question"] = text

            # Only count as a new question if we're NOT awaiting a response
            # (consecutive assistant messages don't increment the counter)
            if not state.get("debat_awaiting_response"):
                state["debat_question_count"] = state.get("debat_question_count", 0) + 1
                state["debat_awaiting_response"] = True

            count = state["debat_question_count"]
            logger.info(f"Debat question #{count}: {text[:80]}...")

            # After 5 actual questions, transition to feedback
            if count >= 5 and state["current_phase"] == "debat":
                logger.info("Debat complete (5 questions), auto-transitioning to feedback")
                asyncio.create_task(_end_debat())

        elif role == "user":
            # Student responded — next assistant message will be a new question
            state["debat_awaiting_response"] = False

            # Pair user answer with the last agent question
            current_q = state.get("debat_current_question")
            if current_q:
                q_num = len(state["debat_qa_pairs"]) + 1
                pair = {"question_number": q_num, "question_text": current_q, "answer_text": text}
                state["debat_qa_pairs"].append(pair)
                state["debat_current_question"] = None
                asyncio.create_task(save_debate_qa(session_id, q_num, current_q, text))

    # Listen for DataChannel events from frontend buttons
    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        state = session.userdata
        try:
            payload = json.loads(data.data.decode())
            ev = payload.get("event")

            if ev == "skip_consignes" and state["current_phase"] == "consignes":
                state["skip_consignes"] = True
                logger.info("Skip consignes requested by user")

            elif ev == "student_ready" and not state["ready_detected"]:
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
                elif ev == "student_finished" and state["current_phase"] == "debat":
                    logger.info("'J'ai terminé' via button during debat!")
                    asyncio.create_task(_end_debat())

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
