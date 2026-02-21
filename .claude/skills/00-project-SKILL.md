# Skill: Evalora Project Architecture

## Domain Context
Evalora simulates the **DU FLE oral production exam** at Sorbonne Abu Dhabi. Students (levels A2+/B1) present a French text document for 5–10 min (monologue), then debate with the AI examiner for ~10 min, then receive scored feedback.

## Architecture: LiveKit + Tavus Hybrid

```
┌─────────────┐     WebRTC Audio      ┌──────────────────┐
│   Student    │◄────────────────────►│  LiveKit Agent    │
│   Browser    │     (bidirectional)   │  (Python)         │
│              │                       │  - STT (Whisper)  │
│  ┌────────┐  │     Tavus iframe      │  - LLM (GPT-4o)  │
│  │ Tavus  │  │◄─────(video)────────►│  - TTS (11Labs)   │
│  │ CVI    │  │                       │  - Phase logic    │
│  └────────┘  │                       └──────────────────┘
└─────────────┘              │
       │                     │
       ▼                     ▼
┌─────────────┐     ┌──────────────────┐
│  FastAPI     │     │  PostgreSQL      │
│  Backend     │────►│  (Neon)          │
│  - Auth      │     │  - Sessions      │
│  - Sessions  │     │  - Users         │
│  - Eval      │     │  - Evaluations   │
│  - Tavus API │     │  - Transcripts   │
└─────────────┘     └──────────────────┘
```

**Key design decision**: LiveKit handles all audio/AI logic (STT → LLM → TTS). Tavus provides the visual avatar (video only) synchronized with the audio. The Tavus persona acts as a "visual shell" — it does NOT control exam logic.

## Database Schema (Neon PostgreSQL)
```sql
-- Core tables
users(id, email, password_hash, name, role, created_at)
sessions(id, user_id, student_name, level, avatar_id, document_id, 
         status, current_phase, phase_started_at, created_at)
evaluations(id, session_id, monologue_transcript, debat_transcript,
            scores_json, total_score, grade_letter, passed, 
            feedback_text, avatar_id, created_at)
transcripts(id, session_id, phase, speaker, text, timestamp)
tavus_conversations(id, session_id, conversation_id, conversation_url, 
                    persona_id, status, created_at)
```

## Document Bank
8 French texts in `backend/app/data/documents.json`, themes: société, culture, environnement, numérique, travail, santé, éducation, voyage. Each has:
- `id`, `title`, `theme`, `author`, `source`, `date`
- `text` (the article content)
- `keywords` array
- `difficulty` ("B1")
- `debate_questions` (5 pre-written questions)

## API Routes
```
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/avatar
GET    /api/avatar/:id
GET    /api/avatar/:id/messages/:phase
GET    /api/documents
GET    /api/documents/:id
POST   /api/session
GET    /api/session/:id
POST   /api/session/:id/transition
POST   /api/livekit/room
POST   /api/livekit/token
DELETE /api/livekit/room/:name
POST   /api/evaluation/submit
GET    /api/evaluation/:session_id
POST   /api/tavus/conversation          # NEW - creates Tavus CVI session
GET    /api/tavus/conversation/:id       # NEW - get conversation status
DELETE /api/tavus/conversation/:id       # NEW - end conversation
```

## Phase State Machine
```
consignes → monologue → debat → feedback → completed
```
Transitions are triggered by:
- consignes → monologue: avatar finishes instructions
- monologue → debat: student says "j'ai terminé" or timer (10 min)
- debat → feedback: 5 questions asked OR timer (10 min)
- feedback → completed: avatar finishes feedback delivery

## Non-Negotiable Rules
1. **Silence during monologue**: Zero audio output from agent during monologue phase
2. **5 questions in débat**: Exactly 5 questions, auto-transition after 5th answer
3. **French only**: All avatar speech in French, all student-facing UI in French
4. **Grading on 20**: Total score always on 20 points, using official DU FLE grid
5. **No help during exam**: Avatar never gives answers or corrects arguments
6. **No early scores**: Scores revealed only during feedback phase
