import axios from "axios"
import { Session, Avatar, Document, Feedback } from "@/types"

const api = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json",
  },
})

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

export async function initAvatar(data: {
  session_id: string
  avatar_id: string
  student_name: string
}): Promise<{
  avatar_id: string
  avatar_name: string
  conversation_id: string
  conversation_url?: string
  status: string
  mode: string
}> {
  const response = await api.post("/avatar/init", data)
  return response.data
}

export async function makeAvatarSpeak(data: {
  conversation_id: string
  text: string
  message_type?: string
}): Promise<{
  text: string
  audio_url?: string
  video_url?: string
  status: string
}> {
  const response = await api.post("/avatar/speak", data)
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

export default api
