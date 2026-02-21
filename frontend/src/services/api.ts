import axios from "axios"
import { Session, Avatar, Document, Feedback, TranscriptEntry, TavusSession } from "@/types"

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
})

// Clés de stockage des tokens
const TOKEN_KEY = 'evalora_access_token';
const REFRESH_KEY = 'evalora_refresh_token';

// Intercepteur pour ajouter le token JWT aux requêtes
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercepteur pour gérer les erreurs 401 et rafraîchir le token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Si erreur 401 et pas déjà en retry
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem(REFRESH_KEY);
        if (!refreshToken) {
          throw new Error('No refresh token');
        }

        // Appel refresh sans intercepteur pour éviter boucle infinie
        const response = await axios.post('/api/auth/refresh', {
          refresh_token: refreshToken
        });

        const { access_token, refresh_token } = response.data;
        localStorage.setItem(TOKEN_KEY, access_token);
        localStorage.setItem(REFRESH_KEY, refresh_token);

        // Réessayer la requête originale avec le nouveau token
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Échec du refresh: déconnecter l'utilisateur
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
)

export async function createSession(data: {
  student_name: string
  level: string
  avatar_id?: string
  document_id?: string
}): Promise<Session> {
  const response = await api.post("/session", data)
  return response.data
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await api.get(`/session/${sessionId}`)
  return response.data
}

export async function transitionPhase(
  sessionId: string,
  newPhase: string,
  phaseDuration?: number
): Promise<void> {
  await api.post(`/session/${sessionId}/transition`, {
    session_id: sessionId,
    new_phase: newPhase,
    phase_duration: phaseDuration,
  })
}

export async function getDocuments(): Promise<{ documents: Document[]; total: number }> {
  const response = await api.get("/documents")
  return response.data
}

export async function getDocument(documentId: string): Promise<Document> {
  const response = await api.get(`/documents/${documentId}`)
  return response.data
}

export async function getDebateQuestions(
  documentId: string
): Promise<{ questions: string[] }> {
  const response = await api.get(`/documents/${documentId}/questions`)
  return response.data
}

export async function getAvatars(): Promise<{ avatars: Avatar[] }> {
  const response = await api.get("/avatar")
  return response.data
}

export async function getAvatar(avatarId: string): Promise<Avatar> {
  const response = await api.get(`/avatar/${avatarId}`)
  return response.data
}

export async function getAvatarMessages(
  avatarId: string,
  phase: string
): Promise<{ messages: string[] }> {
  const response = await api.get(`/avatar/${avatarId}/messages/${phase}`)
  return response.data
}

export async function getLivekitStatus(): Promise<{
  configured: boolean
  url?: string
}> {
  const response = await api.get("/livekit/status")
  return response.data
}

export async function createLivekitRoom(sessionId: string): Promise<{
  room_name: string
  status: string
}> {
  const response = await api.post("/livekit/room", {
    session_id: sessionId,
    participant_name: "student",
  })
  return response.data
}

export async function getLivekitToken(
  roomName: string,
  participantName: string
): Promise<{
  token: string
  ws_url?: string
  configured: boolean
}> {
  const response = await api.post("/livekit/token", {
    room_name: roomName,
    participant_name: participantName,
  })
  return response.data
}

export async function deleteLivekitRoom(roomName: string): Promise<{
  status: string
  room_name: string
}> {
  const response = await api.delete(`/livekit/room/${roomName}`)
  return response.data
}

export async function submitEvaluation(data: {
  session_id: string
  monologue_transcript?: string
  debat_transcript?: string
  monologue_duration: number
  debat_duration: number
}): Promise<{
  total_score: number
  grade_letter: string
  passed: boolean
}> {
  const response = await api.post("/evaluation/submit", data)
  return response.data
}

export async function getFeedback(
  sessionId: string,
  avatarId?: string
): Promise<Feedback> {
  const params = avatarId ? `?avatar_id=${avatarId}` : ""
  const response = await api.get(`/evaluation/${sessionId}${params}`)
  return response.data
}

// Voice Agent / Transcription API
export async function getVoiceAgentStatus(): Promise<{
  configured: boolean
  openai_configured: boolean
  livekit_configured: boolean
  message: string
}> {
  const response = await api.get("/voice-agent/status")
  return response.data
}

export async function getTranscription(sessionId: string): Promise<{
  session_id: string
  transcript: TranscriptEntry[]
  created_at: string
}> {
  const response = await api.get(`/voice-agent/transcription/${sessionId}`)
  return response.data
}

// Tavus API
export async function startTavusConversation(
  sessionId: string,
  avatarId: string,
  studentName: string,
  documentTitle: string,
): Promise<TavusSession> {
  const response = await api.post(`/tavus/${sessionId}/start`, {
    avatar_id: avatarId,
    student_name: studentName,
    document_title: documentTitle,
  })
  return response.data
}

export async function endTavusConversation(sessionId: string): Promise<void> {
  await api.delete(`/tavus/${sessionId}/end`)
}

export default api
