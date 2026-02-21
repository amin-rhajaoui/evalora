# Skill: LiveKit Voice Agent (v1.x)

## ⚠️ CRITICAL: Migration from v0.x to v1.x

The current `agent.py` uses the **deprecated v0.x API** (`VoicePipelineAgent`). LiveKit Agents is now at **v1.4+** with a completely new API. The agent MUST be migrated.

### Key API Changes
| v0.x (Current Code) | v1.x (Required) |
|---------------------|-----------------|
| `VoicePipelineAgent` | `AgentSession` + `Agent` class |
| `agent.say()` | `session.generate_reply()` or `session.say()` |
| `WorkerOptions` | `AgentServer` + `@server.rtc_session()` |
| `agents.cli.run_app()` | `cli.run_app()` with `AgentServer` |
| Manual STT/LLM/TTS wiring | Unified pipeline in `AgentSession` |

## Agent Architecture (v1.x)

```python
import json
from livekit.agents import (
    Agent, AgentSession, AgentServer, JobContext, RunContext,
    cli, function_tool
)
from livekit.plugins import openai, silero, elevenlabs

server = AgentServer()


# ============================================================
# PHASE 1: CONSIGNES — Delivers exam instructions
# ============================================================
class ConsignesAgent(Agent):
    """Greets student, explains exam rules, then hands off to MonologueAgent."""
    
    def __init__(self, avatar_config: dict, student_name: str, document: dict):
        self.avatar_config = avatar_config
        self.student_name = student_name
        self.document = document
        
        register = "tu" if avatar_config["register"] == "tutoiement" else "vous"
        verb_etre = "es" if register == "tu" else "êtes"
        verb_pouvoir = "tu peux" if register == "tu" else "vous pouvez"
        
        super().__init__(
            instructions=f"""Tu es {avatar_config['name']}, examinateur/examinatrice du DU FLE 
à la Sorbonne Abu Dhabi. Tu utilises le {avatar_config['register']}.

Tu accueilles l'étudiant(e) {student_name} et tu lui expliques le déroulement de l'examen:
1. D'abord, il/elle présentera le document "{document['title']}" pendant 5 à 10 minutes (monologue)
2. Ensuite, tu lui poseras des questions pour un débat d'environ 10 minutes
3. Enfin, tu donneras un feedback détaillé avec une note sur 20

Quand tu as fini les consignes, dis exactement:
"Quand {register} {verb_etre} prêt(e), {verb_pouvoir} commencer {register == 'tu' and 'ta' or 'votre'} présentation."

Puis appelle la fonction start_monologue.

Parle uniquement en français. Sois {avatar_config['style'].lower()}.
""",
        )
    
    async def on_enter(self):
        """Called when this agent becomes active."""
        self.session.generate_reply()
    
    @function_tool
    async def start_monologue(self, context: RunContext):
        """Call this when the student indicates they are ready to begin their monologue."""
        # Send phase transition event to frontend via DataChannel
        if self.session.room:
            await self.session.room.local_participant.publish_data(
                json.dumps({"type": "phase_transition", "phase": "monologue"}).encode()
            )
        monologue_agent = MonologueAgent(self.document, self.avatar_config, self.student_name)
        return monologue_agent, "C'est parti. Je vous écoute."


# ============================================================
# PHASE 2: MONOLOGUE — ABSOLUTE SILENCE
# ============================================================
class MonologueAgent(Agent):
    """SILENT agent during student monologue. Listens and records only."""
    
    def __init__(self, document: dict, avatar_config: dict, student_name: str):
        self.document = document
        self.avatar_config = avatar_config
        self.student_name = student_name
        
        super().__init__(
            instructions="""RÈGLE ABSOLUE: TU NE PARLES PAS. SILENCE TOTAL.
Tu es en phase monologue. Tu écoutes en silence. 
Tu ne fais AUCUN son. Pas de "hmm", pas de "d'accord", RIEN.
Tu attends que l'étudiant(e) finisse sa présentation.
Quand l'étudiant(e) dit "j'ai terminé", "voilà c'est tout", "c'est fini", 
ou après un silence prolongé de plus de 15 secondes,
appelle la fonction end_monologue.""",
        )
    
    async def on_enter(self):
        # ⚠️ CRITICAL: Do NOT call generate_reply() — silence is mandatory
        pass
    
    @function_tool
    async def end_monologue(self, context: RunContext):
        """Call when the student has clearly finished their monologue presentation."""
        if self.session.room:
            await self.session.room.local_participant.publish_data(
                json.dumps({"type": "phase_transition", "phase": "debat"}).encode()
            )
        debat_agent = DebatAgent(self.document, self.avatar_config, self.student_name)
        return debat_agent, "Merci pour cette présentation. Passons maintenant au débat."


# ============================================================
# PHASE 3: DÉBAT — Exactly 5 questions
# ============================================================
class DebatAgent(Agent):
    """Asks exactly 5 debate questions, then transitions to feedback."""
    
    def __init__(self, document: dict, avatar_config: dict, student_name: str):
        self.document = document
        self.avatar_config = avatar_config
        self.student_name = student_name
        self.questions_asked = 0
        
        register = "tu" if avatar_config["register"] == "tutoiement" else "vous"
        
        super().__init__(
            instructions=f"""Tu es {avatar_config['name']} en phase DÉBAT.
Tu utilises le {avatar_config['register']}.
Document: "{document['title']}" — Thème: {document['theme']}

Questions disponibles (adapte-les selon les réponses):
{chr(10).join(f"- {q}" for q in document['debate_questions'])}

RÈGLES STRICTES:
- Pose exactement 5 questions au total — pas plus, pas moins
- Après CHAQUE question posée, appelle track_question avec le numéro
- Adapte tes relances selon les réponses de l'étudiant(e)
- Si la réponse est trop courte, relance avant de passer à la question suivante
- Ne donne JAMAIS la réponse ni ne corrige les arguments
- Ne révèle JAMAIS la note ou une évaluation partielle
- Après la 5ème question et sa réponse, appelle end_debat

Sois {avatar_config['style'].lower()}.
Questions posées: {self.questions_asked}/5
""",
        )
    
    async def on_enter(self):
        self.session.generate_reply()
    
    @function_tool
    async def track_question(self, context: RunContext, question_number: int):
        """Call after asking each question. Pass the question number (1-5)."""
        self.questions_asked = question_number
        # Notify frontend
        if self.session.room:
            await self.session.room.local_participant.publish_data(
                json.dumps({"type": "question_asked", "count": question_number}).encode()
            )
        if self.questions_asked >= 5:
            return "Tu as posé les 5 questions. Attends la dernière réponse puis appelle end_debat."
        return f"Question {self.questions_asked}/5 posée. Continue avec la suivante."
    
    @function_tool
    async def end_debat(self, context: RunContext):
        """Call after the 5th question has been fully answered."""
        if self.session.room:
            await self.session.room.local_participant.publish_data(
                json.dumps({"type": "phase_transition", "phase": "feedback"}).encode()
            )
        feedback_agent = FeedbackAgent(self.document, self.avatar_config, self.student_name)
        return feedback_agent, "Merci pour cet échange très intéressant. Je vais maintenant te donner mon retour sur ta prestation."


# ============================================================
# PHASE 4: FEEDBACK — Delivers scored evaluation
# ============================================================
class FeedbackAgent(Agent):
    """Delivers detailed evaluation feedback with score on 20 points."""
    
    def __init__(self, document: dict, avatar_config: dict, student_name: str):
        self.document = document
        self.avatar_config = avatar_config
        self.student_name = student_name
        
        super().__init__(
            instructions=f"""Tu es {avatar_config['name']} en phase FEEDBACK.
Tu donnes le retour détaillé de l'examen oral DU FLE à {student_name}.

Utilise la grille officielle sur 20 points:
- Monologue (10.5 pts): Respect consigne (2), Contenu informatif (4.5), Cohérence (2), Expression (2)
- Débat (5 pts): Interaction (2.5), Argumentation (2.5)
- Langue (4.5 pts): Lexique (1.5), Morphosyntaxe (1.5), Phonétique (1.5)

Structure ton feedback:
1. Commence par un commentaire global positif
2. Détaille les points forts (2-3 exemples concrets)
3. Identifie les axes d'amélioration (2-3 avec conseils)
4. Annonce la note totale sur 20
5. Termine par un encouragement

Sois {avatar_config['style'].lower()}.
Note: la prononciation est évaluée de façon indicative uniquement.

Après avoir donné tout le feedback, appelle end_exam.
""",
        )
    
    async def on_enter(self):
        self.session.generate_reply(
            instructions="Évalue la performance globale et donne un feedback détaillé avec la note sur 20."
        )
    
    @function_tool
    async def end_exam(self, context: RunContext):
        """Call after delivering all feedback to end the exam session."""
        if self.session.room:
            await self.session.room.local_participant.publish_data(
                json.dumps({"type": "phase_transition", "phase": "completed"}).encode()
            )
        return None, "Je te souhaite bonne continuation dans ton apprentissage du français !"


# ============================================================
# ENTRYPOINT — Configures and starts the session
# ============================================================
@server.rtc_session()
async def entrypoint(ctx: JobContext):
    """Main entry point — called when a student joins a LiveKit room."""
    await ctx.connect()
    
    # Extract session config from room metadata (set by frontend when creating room)
    room_metadata = ctx.room.metadata
    config = json.loads(room_metadata) if room_metadata else {}
    
    avatar_id = config.get("avatar_id", "clea")
    document_id = config.get("document_id", "doc-1-societe")
    student_name = config.get("student_name", "l'étudiant")
    
    # Load avatar config
    avatar_config = AVATARS[avatar_id]
    
    # Load document
    document = DOCUMENTS[document_id]
    
    # Configure voice pipeline
    voice_id = avatar_config["elevenlabs_voice_id"]
    
    session = AgentSession(
        vad=silero.VAD.load(),
        stt=openai.STT(model="whisper-1", language="fr"),
        llm=openai.LLM(model="gpt-4o"),  # ⚠️ NEVER use gpt-4o-mini
        tts=elevenlabs.TTS(
            voice_id=voice_id,
            model="eleven_turbo_v2_5",
            language="fr",
        ),
    )
    
    # Start with ConsignesAgent (Phase 1)
    await session.start(
        agent=ConsignesAgent(avatar_config, student_name, document),
        room=ctx.room,
    )


# ============================================================
# DATA: Avatars and Documents (loaded from config/JSON)
# ============================================================
AVATARS = {
    "karim": {
        "name": "Karim",
        "style": "Académique et rigoureux",
        "register": "vouvoiement",
        "elevenlabs_voice_id": "onwK4e9ZLuTAKqWW03F9",  # Hugo
    },
    "clea": {
        "name": "Cléa",
        "style": "Bienveillante et chaleureuse",
        "register": "tutoiement",
        "elevenlabs_voice_id": "XrExE9yKIg1WjnnlVkGX",  # Mylene
    },
    "claire": {
        "name": "Claire",
        "style": "Stricte et exigeante",
        "register": "vouvoiement",
        "elevenlabs_voice_id": "Xb7hH8MSUJpSbSDYk0k2",  # Koraly
    },
    "alex": {
        "name": "Alex",
        "style": "Détendu et conversationnel",
        "register": "tutoiement",
        "elevenlabs_voice_id": "IKne3meq5aSn9XLyUdCD",  # Jules
    },
}

# Load documents from JSON file
import os
DOCS_PATH = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "documents.json")
if os.path.exists(DOCS_PATH):
    with open(DOCS_PATH, "r", encoding="utf-8") as f:
        _docs_data = json.load(f)
    DOCUMENTS = {doc["id"]: doc for doc in _docs_data["documents"]}
else:
    DOCUMENTS = {}


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    cli.run_app(server)
```

## Dependencies (agent/requirements.txt)
```
livekit-agents>=1.4.0
livekit-plugins-openai>=1.0.0
livekit-plugins-silero>=1.0.0
livekit-plugins-elevenlabs>=1.0.0
python-dotenv
httpx
```

## Key Patterns

### Agent Handoff (Phase Transitions)
In v1.x, `function_tool` that returns `(new_agent, message)` triggers handoff:
```python
@function_tool
async def transition(self, context: RunContext):
    next_agent = NextPhaseAgent(...)
    return next_agent, "Transition message spoken aloud"
```

### Silence During Monologue
`MonologueAgent` achieves silence by:
1. NOT calling `self.session.generate_reply()` in `on_enter()`
2. Instructions explicitly say "do not speak"
3. Only uses `function_tool` to transition when student finishes

### DataChannel Events (Agent → Frontend)
```python
await self.session.room.local_participant.publish_data(
    json.dumps({
        "type": "phase_transition",  # or "question_asked", "evaluation_complete"
        "phase": "debat",
    }).encode()
)
```

## Environment Variables (agent/.env)
```
OPENAI_API_KEY=sk-...
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=API...
LIVEKIT_API_SECRET=...
ELEVENLABS_API_KEY=...
```

## Running the Agent
```bash
cd agent
source venv/bin/activate

# Development (auto-reload, connects to playground)
python agent.py dev

# Production
python agent.py start
```

## Testing
```bash
# Verify agent starts
python agent.py dev
# → Should print "Agent server started" without errors

# Test with LiveKit Agents Playground
# https://agents-playground.livekit.io
# Connect to your LiveKit project, agent should respond in French
```
