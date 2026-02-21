# Skill: Tavus CVI Integration

## Architecture Decision
Tavus provides the **visual layer only** (video avatar). LiveKit handles all audio/AI logic. The Tavus persona is configured with a minimal system prompt that focuses on emotional expression, NOT exam logic.

## Tavus API Reference

### Create Conversation (Start Exam)
```bash
POST https://tavusapi.com/v2/conversations
Headers: x-api-key: {TAVUS_API_KEY}, Content-Type: application/json

{
  "replica_id": "r...",              # Olivia-Office for Cléa, etc.
  "persona_id": "p0bd677850df",      # Cléa persona ID
  "conversation_name": "Evalora Exam - {student_name}",
  "conversational_context": "The student {student_name} is taking a DU FLE oral exam on the document: {document_title}. Current phase: {phase}.",
  "properties": {
    "max_call_duration": 1800,        # 30 min max
    "enable_recording": true,
    "language": "french"
  },
  "document_ids": ["{doc_id}"],       # RAG: exam document
  "callback_url": "https://your-server.com/api/tavus/webhook"
}

# Response:
{
  "conversation_id": "c123456",
  "conversation_url": "https://tavus.daily.co/c123456",
  "status": "active"
}
```

### End Conversation
```bash
DELETE https://tavusapi.com/v2/conversations/{conversation_id}
Headers: x-api-key: {TAVUS_API_KEY}
```

### Guardrails (Create Once, Attach to Persona)
```bash
# Step 1: Create guardrails set
POST https://tavusapi.com/v2/guardrails
{
  "name": "evalora_clea_guardrails",
  "data": [
    {
      "guardrail_name": "silence_monologue",
      "guardrail_prompt": "During the student monologue phase, remain in ABSOLUTE SILENCE. Never speak, never make any sound. Only resume when the student has clearly finished.",
      "modality": "verbal"
    },
    {
      "guardrail_name": "no_answers",
      "guardrail_prompt": "Never provide answers, correct arguments, or suggest what the student should say. Only ask questions.",
      "modality": "verbal"
    },
    {
      "guardrail_name": "no_score_early",
      "guardrail_prompt": "Never reveal scores or evaluative judgments before the final feedback phase.",
      "modality": "verbal"
    },
    {
      "guardrail_name": "french_only",
      "guardrail_prompt": "Always speak French exclusively. Never switch to another language.",
      "modality": "verbal"
    }
  ]
}
# Returns: { "guardrails_id": "g..." }

# Step 2: Attach to persona
PATCH https://tavusapi.com/v2/personas/{persona_id}
{ "guardrails_id": "g..." }
```

### Persona Configuration (Already on Tavus Platform)
| Field | Cléa Value |
|-------|-----------|
| Persona ID | `p0bd677850df` |
| Replica | Olivia - Office |
| LLM | `gpt-4o` (NOT tavus-gpt-oss) |
| TTS | ElevenLabs (Mylene voice) |
| Turn Detection | Sparrow-1 |
| Perception | Raven-1 |

### Emotion Control (Phoenix-4)
Available emotion values: `neutral`, `angry`, `excited`, `elated`, `content`, `sad`, `dejected`, `scared`, `contempt`, `disgusted`, `surprised`

In system prompt:
```
Show warm enthusiasm when the student progresses well.
Express gentle concern if the student seems lost.
Show visible satisfaction for well-structured arguments.
Remain patient and encouraging at all times.
```

In Echo Mode (manual control via text):
```
<emotion value="content"/> Très bonne analyse !
<emotion value="excited"/> Excellent argument, continue !
<emotion value="sad"/> C'est dommage, cet argument manque de profondeur.
```

## Backend Router Implementation

**File**: `backend/app/routers/tavus.py` (NEW)
```python
import httpx
from fastapi import APIRouter, Depends, HTTPException
from app.config import settings
from app.dependencies import get_current_user

router = APIRouter(prefix="/tavus", tags=["tavus"])

TAVUS_BASE_URL = "https://tavusapi.com/v2"

# Map avatar_id → Tavus persona_id
TAVUS_PERSONAS = {
    "clea": "p0bd677850df",
    "karim": None,   # TODO: create on Tavus platform
    "claire": None,  # TODO: create on Tavus platform
    "alex": None,    # TODO: create on Tavus platform
}

def tavus_headers():
    return {
        "x-api-key": settings.TAVUS_API_KEY,
        "Content-Type": "application/json"
    }

@router.post("/{session_id}/start")
async def start_tavus_conversation(
    session_id: str,
    avatar_id: str,
    student_name: str,
    document_title: str,
    user=Depends(get_current_user)
):
    persona_id = TAVUS_PERSONAS.get(avatar_id)
    if not persona_id:
        raise HTTPException(400, f"No Tavus persona configured for avatar: {avatar_id}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{TAVUS_BASE_URL}/conversations",
            headers=tavus_headers(),
            json={
                "persona_id": persona_id,
                "conversation_name": f"Evalora - {student_name}",
                "conversational_context": (
                    f"L'étudiant(e) {student_name} passe un examen oral DU FLE. "
                    f"Document: {document_title}."
                ),
                "properties": {
                    "max_call_duration": 1800,
                    "enable_recording": True,
                    "language": "french"
                }
            }
        )
        if response.status_code != 200:
            raise HTTPException(502, f"Tavus API error: {response.text}")
        
        data = response.json()
        # TODO: save conversation_id and conversation_url to session in DB
        return {
            "conversation_id": data.get("conversation_id"),
            "conversation_url": data.get("conversation_url"),
            "status": data.get("status", "active")
        }

@router.delete("/{session_id}/end")
async def end_tavus_conversation(
    session_id: str,
    conversation_id: str,
    user=Depends(get_current_user)
):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(
            f"{TAVUS_BASE_URL}/conversations/{conversation_id}",
            headers=tavus_headers()
        )
        return {"status": "ended", "conversation_id": conversation_id}
```

**Register in main.py:**
```python
from app.routers import tavus
app.include_router(tavus.router, prefix="/api")
```

## Frontend: Embed Tavus CVI

### Option A: iframe (Simplest — use this first)
```tsx
// frontend/src/components/TavusPlayer.tsx
interface TavusPlayerProps {
  conversationUrl: string | null;
}

export function TavusPlayer({ conversationUrl }: TavusPlayerProps) {
  if (!conversationUrl) {
    return (
      <div className="w-full aspect-video rounded-xl bg-gray-900 flex items-center justify-center">
        <div className="text-gray-400 animate-pulse">Connexion avatar...</div>
      </div>
    );
  }

  return (
    <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-black">
      <iframe
        src={conversationUrl}
        allow="camera; microphone; autoplay; display-capture"
        className="w-full h-full border-0"
      />
    </div>
  );
}
```

### Option B: React SDK (@tavus/cvi-ui) — For later
```bash
npx @tavus/cvi-ui init
npx @tavus/cvi-ui add conversation
```
```tsx
import { CVIProvider, Conversation } from "@tavus/cvi-ui";

export function TavusPlayer({ conversationUrl }: { conversationUrl: string }) {
  return (
    <CVIProvider>
      <Conversation
        conversationUrl={conversationUrl}
        className="w-full aspect-video rounded-xl"
      />
    </CVIProvider>
  );
}
```

## Integration in Exam.tsx
```tsx
// Add state
const [tavusUrl, setTavusUrl] = useState<string | null>(null);

// When LiveKit connects, start Tavus conversation
const startExam = async () => {
  // 1. Create LiveKit room (audio agent)
  const room = await createLivekitRoom(session.id);
  const token = await getLivekitToken(room.room_name, studentName);
  
  // 2. Create Tavus conversation (video avatar)
  const tavusResponse = await api.post(`/tavus/${session.id}/start`, {
    avatar_id: selectedAvatar.id,
    student_name: studentName,
    document_title: selectedDocument.title
  });
  setTavusUrl(tavusResponse.data.conversation_url);
  setLivekitToken(token.token);
};

// In cleanup / end exam
const endExam = async () => {
  if (tavusUrl) {
    await api.delete(`/tavus/${session.id}/end`);
  }
};

// In render — replace avatar placeholder with TavusPlayer
<TavusPlayer conversationUrl={tavusUrl} />
```

## Frontend API additions
**File**: `frontend/src/services/api.ts` — add:
```typescript
export async function startTavusConversation(
  sessionId: string,
  avatarId: string,
  studentName: string,
  documentTitle: string
): Promise<{ conversation_id: string; conversation_url: string; status: string }> {
  const response = await api.post(`/tavus/${sessionId}/start`, {
    avatar_id: avatarId,
    student_name: studentName,
    document_title: documentTitle,
  });
  return response.data;
}

export async function endTavusConversation(
  sessionId: string,
  conversationId: string
): Promise<void> {
  await api.delete(`/tavus/${sessionId}/end`, {
    params: { conversation_id: conversationId },
  });
}
```

## DB Migration
```python
# alembic revision --autogenerate -m "add_tavus_fields_to_sessions"
# Add to sessions table:
#   tavus_conversation_id: String(128), nullable=True
#   tavus_conversation_url: String(512), nullable=True
```

## Avatar-to-Persona Mapping
Only Cléa's persona exists so far. Create others on Tavus platform:
| Avatar | Persona ID | Replica | Status |
|--------|-----------|---------|--------|
| Cléa | `p0bd677850df` | Olivia-Office | ✅ Created |
| Karim | TBD | TBD | ❌ To create |
| Claire | TBD | TBD | ❌ To create |
| Alex | TBD | TBD | ❌ To create |
