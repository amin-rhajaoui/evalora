import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { transitionPhase, submitEvaluation, getFeedback, getAvatarMessages } from "@/services/api"
import { ExamPhase } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { cn, formatTime } from "@/lib/utils"
import {
  Mic,
  MicOff,
  Play,
  Square,
  ChevronRight,
  Loader2,
  MessageCircle,
  User,
} from "lucide-react"

const AVATAR_EMOJIS: Record<string, string> = {
  clea: "👩‍🏫",
  alex: "🧑‍🎓",
  karim: "👨‍💼",
  claire: "👩‍💼",
}

const PHASE_CONFIG: Record<ExamPhase, { label: string; color: string; maxTime?: number }> = {
  consignes: { label: "Consignes", color: "bg-sky-500" },
  monologue: { label: "Monologue", color: "bg-green-500", maxTime: 600 },
  debat: { label: "Debat", color: "bg-purple-500", maxTime: 600 },
  feedback: { label: "Feedback", color: "bg-slate-200" },
  completed: { label: "Termine", color: "bg-green-500" },
}

export default function Exam() {
  const navigate = useNavigate()
  const {
    session,
    studentName,
    selectedAvatar,
    selectedDocument,
    currentPhase,
    setCurrentPhase,
    monologueDuration,
    setMonologueDuration,
    setDebatDuration,
    setFeedback,
    tavusConversationUrl,
  } = useExam()

  const [elapsedTime, setElapsedTime] = useState(0)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [messages, setMessages] = useState<{ role: "avatar" | "student"; text: string }[]>([])
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [debateQuestions, setDebateQuestions] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!session || !selectedDocument) {
      navigate("/")
    }
  }, [session, selectedDocument, navigate])

  useEffect(() => {
    async function loadMessages() {
      if (!selectedAvatar) return
      try {
        const data = await getAvatarMessages(selectedAvatar.id, currentPhase)
        if (data.messages?.length > 0) {
          for (const msg of data.messages) {
            await new Promise((resolve) => setTimeout(resolve, 1000))
            setMessages((prev) => [...prev, { role: "avatar", text: msg }])
          }
        }
      } catch {
        // Error loading messages - continue silently
      }
    }

    if (currentPhase === "consignes") {
      const greeting = selectedAvatar
        ? `Bonjour ${studentName} ! Je m'appelle ${selectedAvatar.name}. Je serai ${selectedAvatar.register === "tutoiement" ? "ton" : "votre"} examinateur pour cette simulation.`
        : `Bonjour ${studentName} ! Bienvenue a cette simulation d'examen.`
      setMessages([{ role: "avatar", text: greeting }])
      loadMessages()
    }
  }, [currentPhase, selectedAvatar, studentName])

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isTimerRunning) {
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1)
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [isTimerRunning])

  const handleStartMonologue = useCallback(async () => {
    setCurrentPhase("monologue")
    setElapsedTime(0)
    setIsTimerRunning(true)
    if (session) await transitionPhase(session.id, "monologue")
    setMessages((prev) => [
      ...prev,
      {
        role: "avatar",
        text: selectedAvatar?.register === "tutoiement"
          ? "Parfait ! Le timer demarre. Tu peux commencer."
          : "Parfait ! Le timer demarre. Vous pouvez commencer.",
      },
    ])
  }, [session, selectedAvatar, setCurrentPhase])

  const handleEndMonologue = useCallback(async () => {
    setIsTimerRunning(false)
    setMonologueDuration(elapsedTime)
    setCurrentPhase("debat")
    setElapsedTime(0)
    if (session) await transitionPhase(session.id, "debat", elapsedTime)
    if (selectedDocument?.debate_questions) {
      setDebateQuestions(selectedDocument.debate_questions)
    }
    setMessages((prev) => [
      ...prev,
      {
        role: "avatar",
        text: selectedAvatar?.register === "tutoiement"
          ? "Merci ! Tu as bien presente ton document. Maintenant, nous allons passer au debat."
          : "Merci ! Vous avez bien presente votre document. Maintenant, nous allons passer au debat.",
      },
    ])
    setIsTimerRunning(true)
  }, [session, elapsedTime, selectedDocument, selectedAvatar, setCurrentPhase, setMonologueDuration])

  const handleNextQuestion = useCallback(() => {
    if (currentQuestion < debateQuestions.length - 1) {
      setCurrentQuestion((prev) => prev + 1)
      setMessages((prev) => [
        ...prev,
        { role: "avatar", text: debateQuestions[currentQuestion + 1] },
      ])
    } else {
      handleEndDebate()
    }
  }, [currentQuestion, debateQuestions])

  const handleEndDebate = useCallback(async () => {
    setIsTimerRunning(false)
    setDebatDuration(elapsedTime)
    setCurrentPhase("feedback")
    if (session) await transitionPhase(session.id, "feedback", elapsedTime)
    setMessages((prev) => [
      ...prev,
      { role: "avatar", text: "L'examen est termine. Voici votre feedback detaille." },
    ])
    setIsLoading(true)
    try {
      await submitEvaluation({
        session_id: session!.id,
        monologue_duration: monologueDuration,
        debat_duration: elapsedTime,
      })
      const feedback = await getFeedback(session!.id, selectedAvatar?.id)
      setFeedback(feedback)
      setTimeout(() => navigate("/results"), 2000)
    } catch {
      // Error submitting evaluation - navigate to results anyway
      navigate("/results")
    }
  }, [session, elapsedTime, monologueDuration, selectedAvatar, setCurrentPhase, setDebatDuration, setFeedback, navigate])

  useEffect(() => {
    if (currentPhase === "debat" && debateQuestions.length > 0 && currentQuestion === 0) {
      setTimeout(() => {
        setMessages((prev) => [...prev, { role: "avatar", text: debateQuestions[0] }])
      }, 2000)
    }
  }, [currentPhase, debateQuestions, currentQuestion])

  if (!session || !selectedDocument) return null

  const phaseConfig = PHASE_CONFIG[currentPhase]
  const maxTime = phaseConfig.maxTime || 600
  const progress = Math.min((elapsedTime / maxTime) * 100, 100)
  const isWarning = currentPhase === "monologue" && elapsedTime >= 480
  const isEnded = currentPhase === "monologue" && elapsedTime >= 600

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Top Bar */}
      <div className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Badge variant="outline" className={cn("text-white border-0", phaseConfig.color)}>
              {phaseConfig.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              {selectedDocument.title}
            </span>
          </div>

          {/* Timer */}
          <div className={cn(
            "flex items-center gap-3 px-4 py-2 rounded-full border-2 transition-all",
            isEnded ? "border-red-500 bg-red-50 animate-pulse" :
            isWarning ? "border-amber-500 bg-amber-50" :
            "border-slate-200 bg-white"
          )}>
            <div className={cn(
              "w-3 h-3 rounded-full",
              isTimerRunning ? "bg-green-500 animate-pulse" : "bg-slate-300"
            )} />
            <span className={cn(
              "font-mono text-xl font-bold tabular-nums",
              isEnded ? "text-red-600" : isWarning ? "text-amber-600" : "text-slate-900"
            )}>
              {formatTime(elapsedTime)}
            </span>
            {phaseConfig.maxTime && (
              <span className="text-sm text-muted-foreground">
                / {formatTime(phaseConfig.maxTime)}
              </span>
            )}
          </div>
        </div>

        {/* Progress */}
        <Progress value={progress} className="h-1 rounded-none" />
      </div>

      <div className="max-w-7xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-4">
          {/* Avatar Zone */}
          <Card className="overflow-hidden">
            <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
              {tavusConversationUrl ? (
                <iframe
                  src={tavusConversationUrl}
                  className="w-full h-full"
                  allow="camera; microphone; autoplay"
                />
              ) : (
                <div className="text-center text-white">
                  <div className="text-6xl mb-4 animate-float">
                    {selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] : "👤"}
                  </div>
                  <p className="text-lg font-medium">
                    {selectedAvatar?.name || "Examinateur"}
                  </p>
                  <p className="text-sm text-slate-400 mt-1">
                    {currentPhase === "monologue" ? "En ecoute..." : "Mode texte"}
                  </p>
                  {currentPhase !== "monologue" && (
                    <div className="flex justify-center gap-1 mt-4">
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="w-2 h-4 bg-green-500 rounded-full animate-wave"
                          style={{ animationDelay: `${i * 0.1}s` }}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Document */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{selectedDocument.title}</CardTitle>
                <Badge variant="secondary">{selectedDocument.theme}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">
                {selectedDocument.source} | {selectedDocument.date}
              </p>
            </CardHeader>
            <CardContent>
              <p className="text-foreground leading-relaxed">
                {selectedDocument.text}
              </p>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-center gap-4">
            {currentPhase === "consignes" && (
              <Button size="lg" onClick={handleStartMonologue} className="gap-2">
                <Play className="w-5 h-5" />
                Je suis pret(e)
              </Button>
            )}
            {currentPhase === "monologue" && (
              <Button size="lg" variant="success" onClick={handleEndMonologue} className="gap-2">
                <Square className="w-5 h-5" />
                J'ai termine
              </Button>
            )}
            {currentPhase === "debat" && (
              <Button size="lg" variant="success" onClick={handleNextQuestion} className="gap-2">
                <ChevronRight className="w-5 h-5" />
                Question suivante
              </Button>
            )}
            {isLoading && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Loader2 className="w-5 h-5 animate-spin" />
                Calcul de votre evaluation...
              </div>
            )}
          </div>
        </div>

        {/* Sidebar - Chat */}
        <div className="space-y-4">
          <Card className="h-[500px] flex flex-col">
            <CardHeader className="pb-3 border-b">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageCircle className="w-4 h-4" />
                Conversation
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    "flex gap-2",
                    msg.role === "student" ? "justify-end" : "justify-start"
                  )}
                >
                  {msg.role === "avatar" && (
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      {selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] : "👤"}
                    </div>
                  )}
                  <div
                    className={cn(
                      "max-w-[80%] px-4 py-2 rounded-2xl text-sm",
                      msg.role === "student"
                        ? "bg-primary text-primary-foreground rounded-br-md"
                        : "bg-slate-100 rounded-bl-md"
                    )}
                  >
                    {msg.text}
                  </div>
                  {msg.role === "student" && (
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Mic Status */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-10 h-10 rounded-full flex items-center justify-center",
                    isTimerRunning ? "bg-green-100" : "bg-slate-100"
                  )}>
                    {isTimerRunning ? (
                      <Mic className="w-5 h-5 text-green-600" />
                    ) : (
                      <MicOff className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                  <div>
                    <p className="font-medium text-sm">
                      {isTimerRunning ? "Micro actif" : "Micro inactif"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {isTimerRunning ? "Vous pouvez parler" : "En attente"}
                    </p>
                  </div>
                </div>
                {isTimerRunning && (
                  <div className="flex gap-1">
                    {[0, 1, 2, 3].map((i) => (
                      <div
                        key={i}
                        className="w-1 bg-green-500 rounded-full animate-wave"
                        style={{
                          height: `${12 + Math.random() * 12}px`,
                          animationDelay: `${i * 0.1}s`,
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Bottom Progress Steps */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t py-3">
        <div className="max-w-7xl mx-auto px-4 flex justify-center gap-8">
          {(["consignes", "monologue", "debat", "feedback"] as ExamPhase[]).map((phase, i) => {
            const phases: ExamPhase[] = ["consignes", "monologue", "debat", "feedback"]
            const currentIndex = phases.indexOf(currentPhase)
            const isActive = phase === currentPhase
            const isCompleted = phases.indexOf(phase) < currentIndex

            return (
              <div key={phase} className="flex items-center gap-2">
                <div
                  className={cn(
                    "w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium",
                    isActive ? "bg-primary text-white" :
                    isCompleted ? "bg-green-500 text-white" :
                    "bg-slate-200 text-slate-500"
                  )}
                >
                  {isCompleted ? "✓" : i + 1}
                </div>
                <span className={cn(
                  "text-sm",
                  isActive ? "font-medium text-primary" :
                  isCompleted ? "text-green-600" :
                  "text-muted-foreground"
                )}>
                  {PHASE_CONFIG[phase].label}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
