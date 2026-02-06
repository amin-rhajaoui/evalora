import { createContext, useContext, useState, ReactNode } from "react"
import { Session, Avatar, Document, Feedback, TranscriptEntry } from "@/types"

interface ExamContextType {
  session: Session | null
  setSession: (session: Session | null) => void
  studentName: string
  setStudentName: (name: string) => void
  studentLevel: "A2+" | "B1"
  setStudentLevel: (level: "A2+" | "B1") => void
  selectedAvatar: Avatar | null
  setSelectedAvatar: (avatar: Avatar | null) => void
  selectedDocument: Document | null
  setSelectedDocument: (doc: Document | null) => void
  feedback: Feedback | null
  setFeedback: (feedback: Feedback | null) => void
  livekitToken: string | null
  setLivekitToken: (token: string | null) => void
  livekitRoomName: string | null
  setLivekitRoomName: (name: string | null) => void
  livekitWsUrl: string | null
  setLivekitWsUrl: (url: string | null) => void
  conversationTranscript: TranscriptEntry[] | null
  setConversationTranscript: (transcript: TranscriptEntry[] | null) => void
  resetExam: () => void
}

const ExamContext = createContext<ExamContextType | undefined>(undefined)

export function ExamProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [studentName, setStudentName] = useState("")
  const [studentLevel, setStudentLevel] = useState<"A2+" | "B1">("B1")
  const [selectedAvatar, setSelectedAvatar] = useState<Avatar | null>(null)
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [livekitToken, setLivekitToken] = useState<string | null>(null)
  const [livekitRoomName, setLivekitRoomName] = useState<string | null>(null)
  const [livekitWsUrl, setLivekitWsUrl] = useState<string | null>(null)
  const [conversationTranscript, setConversationTranscript] = useState<TranscriptEntry[] | null>(null)

  const resetExam = () => {
    setSession(null)
    setStudentName("")
    setStudentLevel("B1")
    setSelectedAvatar(null)
    setSelectedDocument(null)
    setFeedback(null)
    setLivekitToken(null)
    setLivekitRoomName(null)
    setLivekitWsUrl(null)
    setConversationTranscript(null)
  }

  return (
    <ExamContext.Provider
      value={{
        session,
        setSession,
        studentName,
        setStudentName,
        studentLevel,
        setStudentLevel,
        selectedAvatar,
        setSelectedAvatar,
        selectedDocument,
        setSelectedDocument,
        feedback,
        setFeedback,
        livekitToken,
        setLivekitToken,
        livekitRoomName,
        setLivekitRoomName,
        livekitWsUrl,
        setLivekitWsUrl,
        conversationTranscript,
        setConversationTranscript,
        resetExam,
      }}
    >
      {children}
    </ExamContext.Provider>
  )
}

export function useExam() {
  const context = useContext(ExamContext)
  if (context === undefined) {
    throw new Error("useExam must be used within an ExamProvider")
  }
  return context
}
