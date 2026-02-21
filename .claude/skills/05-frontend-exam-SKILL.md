# Skill: Frontend Exam Page & State

## ExamContext (Global State)
**File**: `frontend/src/contexts/ExamContext.tsx`

Current state shape (add missing fields marked NEW):
```typescript
interface ExamContextType {
  // Session
  session: Session | null;
  setSession: (session: Session | null) => void;
  studentName: string;
  setStudentName: (name: string) => void;
  studentLevel: "A2+" | "B1";
  setStudentLevel: (level: "A2+" | "B1") => void;
  
  // Selection
  selectedAvatar: Avatar | null;
  setSelectedAvatar: (avatar: Avatar | null) => void;
  selectedDocument: Document | null;
  setSelectedDocument: (doc: Document | null) => void;
  
  // LiveKit (audio agent)
  livekitToken: string | null;
  setLivekitToken: (token: string | null) => void;
  livekitRoomName: string | null;
  setLivekitRoomName: (name: string | null) => void;
  livekitWsUrl: string | null;
  setLivekitWsUrl: (url: string | null) => void;
  
  // Tavus (video avatar) — NEW
  tavusConversationUrl: string | null;
  setTavusConversationUrl: (url: string | null) => void;
  tavusConversationId: string | null;
  setTavusConversationId: (id: string | null) => void;
  
  // Exam state — NEW (currently managed locally in Exam.tsx, should be here)
  currentPhase: "consignes" | "monologue" | "debat" | "feedback" | "completed";
  setCurrentPhase: (phase: string) => void;
  questionsAsked: number;  // 0-5 for débat
  setQuestionsAsked: (n: number) => void;
  
  // Results
  feedback: Feedback | null;
  setFeedback: (feedback: Feedback | null) => void;
  conversationTranscript: TranscriptEntry[] | null;
  setConversationTranscript: (transcript: TranscriptEntry[] | null) => void;
  
  // Actions
  resetExam: () => void;
}
```

## Exam Page Layout
**File**: `frontend/src/pages/Exam.tsx`

```
┌────────────────────────────────────────────────────┐
│  Phase: MONOLOGUE          ⏱ 07:23 / 10:00        │
├────────────────────────────┬───────────────────────┤
│                            │                       │
│    Tavus Avatar Video      │  Live Transcript      │
│    (TavusPlayer component) │  - Student: "..."     │
│                            │  - Examiner: "..."    │
│                            │                       │
│                            ├───────────────────────┤
│                            │  Controls             │
│                            │  [🎤 Micro ON/OFF]    │
│                            │  [⏭️ J'ai terminé]   │
│                            │  [🚪 Quitter]         │
├────────────────────────────┴───────────────────────┤
│  Question 3/5 posée                                │
└────────────────────────────────────────────────────┘
```

## Phase-Specific UI Behavior

### Consignes Phase
- Avatar video active, speaking
- No student controls visible (except mute/quit)
- Progress indicator: "Instructions en cours..."
- Transition: automatic via DataChannel event from agent

### Monologue Phase  
- Timer starts (10 min countdown)
- "J'ai terminé" button appears after 5 min minimum
- Microphone indicator active (student is speaking)
- Transcript panel shows student speech in real-time
- Avatar is SILENT (neutral expression, no lip movement)

### Débat Phase
- Timer resets (10 min countdown)
- Question counter visible: "Question 2/5"
- Transcript shows both examiner (blue) and student (white)
- No "J'ai terminé" button (agent controls transition after 5 questions)

### Feedback Phase
- Timer hidden (no time pressure)
- Avatar delivers scores
- Transcript shows feedback text
- "Voir mes résultats" button appears when agent sends "completed" event

## LiveKit Connection
```tsx
import { LiveKitRoom, useDataChannel } from "@livekit/components-react";

function ExamRoom() {
  const { livekitToken, livekitWsUrl } = useExam();
  
  if (!livekitToken || !livekitWsUrl) {
    return <div>Connexion en cours...</div>;
  }
  
  return (
    <LiveKitRoom
      token={livekitToken}
      serverUrl={livekitWsUrl}
      connect={true}
      audio={true}
      video={false}  // Video comes from Tavus, NOT LiveKit
    >
      <ExamContent />
    </LiveKitRoom>
  );
}
```

## DataChannel Events (Agent → Frontend)
The LiveKit agent sends JSON messages via DataChannel:
```typescript
import { useDataChannel } from "@livekit/components-react";

function ExamContent() {
  const { currentPhase, setCurrentPhase, setQuestionsAsked, setFeedback } = useExam();
  
  // Listen for agent events
  const onDataReceived = useCallback((msg: any) => {
    try {
      const data = JSON.parse(new TextDecoder().decode(msg.payload));
      
      switch (data.type) {
        case "phase_transition":
          setCurrentPhase(data.phase);
          break;
          
        case "question_asked":
          setQuestionsAsked(data.count);  // 1-5
          break;
          
        case "transcript":
          // Add to transcript list
          addTranscriptEntry({
            speaker: data.speaker,  // "student" | "examiner"
            text: data.text,
            timestamp: Date.now(),
            phase: currentPhase,
          });
          break;
          
        case "evaluation_complete":
          setFeedback(data.feedback);
          break;
      }
    } catch (e) {
      console.error("Failed to parse agent event:", e);
    }
  }, [currentPhase]);

  useDataChannel("exam", { onMessage: onDataReceived });
  
  return (/* ... exam UI ... */);
}
```

## Circular Timer Component
```typescript
interface CircularTimerProps {
  duration: number;       // Total seconds
  phase: string;
  isRunning: boolean;
}

function CircularTimer({ duration, phase, isRunning }: CircularTimerProps) {
  const [elapsed, setElapsed] = useState(0);
  
  // Reset timer when phase changes
  useEffect(() => {
    setElapsed(0);
  }, [phase]);
  
  // Tick every second when running
  useEffect(() => {
    if (!isRunning) return;
    const interval = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isRunning]);
  
  const remaining = Math.max(0, duration - elapsed);
  const progress = (elapsed / duration) * 100;
  const isWarning = remaining < 60;  // Last minute = red
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  
  return (
    <div className={`text-2xl font-mono ${isWarning ? "text-red-500 animate-pulse" : "text-white"}`}>
      {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
    </div>
  );
}
```

## Phase Durations
```typescript
const PHASE_DURATIONS: Record<string, number> = {
  consignes: 180,    // 3 min
  monologue: 600,    // 10 min
  debat: 600,        // 10 min
  feedback: 0,       // No timer
};
```

## Conditional Controls
```tsx
{/* "J'ai terminé" — only in monologue, after 5 min */}
{currentPhase === "monologue" && elapsed >= 300 && (
  <button 
    onClick={handleStudentFinished}
    className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
  >
    J'ai terminé ma présentation
  </button>
)}

{/* Question counter — only in débat */}
{currentPhase === "debat" && (
  <div className="text-sm text-gray-400">
    Question {questionsAsked}/5
  </div>
)}

{/* "Voir résultats" — only when exam is completed */}
{currentPhase === "completed" && (
  <button 
    onClick={() => navigate("/results")}
    className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium"
  >
    Voir mes résultats
  </button>
)}
```

## Exam Start Flow (in Exam.tsx)
```typescript
const startExam = async () => {
  try {
    // 1. Create session on backend
    const session = await createSession({
      student_name: studentName,
      level: studentLevel,
      avatar_id: selectedAvatar.id,
      document_id: selectedDocument.id,
    });
    setSession(session);
    
    // 2. Create LiveKit room + get token
    const room = await createLivekitRoom(session.id);
    const tokenData = await getLivekitToken(room.room_name, studentName);
    setLivekitToken(tokenData.token);
    setLivekitWsUrl(tokenData.ws_url);
    setLivekitRoomName(room.room_name);
    
    // 3. Create Tavus video conversation
    const tavus = await startTavusConversation(
      session.id,
      selectedAvatar.id,
      studentName,
      selectedDocument.title
    );
    setTavusConversationUrl(tavus.conversation_url);
    setTavusConversationId(tavus.conversation_id);
    
    // 4. Set initial phase
    setCurrentPhase("consignes");
  } catch (error) {
    console.error("Failed to start exam:", error);
    // Show error toast to user
  }
};
```

## Exam End / Cleanup
```typescript
const endExam = async () => {
  try {
    // 1. End Tavus conversation
    if (tavusConversationId) {
      await endTavusConversation(session.id, tavusConversationId);
    }
    
    // 2. Submit evaluation
    const evalResult = await submitEvaluation({
      session_id: session.id,
      monologue_transcript: getTranscriptForPhase("monologue"),
      debat_transcript: getTranscriptForPhase("debat"),
      monologue_duration: getPhaseElapsed("monologue"),
      debat_duration: getPhaseElapsed("debat"),
    });
    
    setFeedback(evalResult);
    
    // 3. Navigate to results
    navigate("/results");
  } catch (error) {
    console.error("Failed to end exam:", error);
  }
};
```

## Frontend Dependencies
```json
{
  "@livekit/components-react": "^2.0.0",
  "livekit-client": "^2.0.0",
  "axios": "^1.6.0",
  "react-router-dom": "^6.0.0",
  "recharts": "^2.0.0"
}
```

## Page Flow (Routes)
```
/login → /welcome → /setup → /document-select → /system-check → /mic-test → /exam → /results
```

Each page validates required state before rendering:
- `/setup` requires authenticated user
- `/document-select` requires avatar selected
- `/exam` requires session + avatar + document + LiveKit token
- `/results` requires completed session with feedback data
