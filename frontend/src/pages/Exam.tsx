import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { deleteLivekitRoom, getTranscription, submitEvaluation, getFeedback } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn, formatTime } from "@/lib/utils"
import { Mic, MicOff, Phone, Loader2, CheckCircle, Flag, Headphones, Volume2 } from "lucide-react"
import { ExamPhase } from "@/types"
import {
  Room,
  RoomEvent,
  RemoteParticipant,
  RemoteTrackPublication,
  RemoteTrack,
  Track,
  LocalAudioTrack,
  createLocalAudioTrack,
  DataPacket_Kind,
} from "livekit-client"

const AVATAR_EMOJIS: Record<string, string> = {
  clea: "C",
  alex: "A",
  karim: "K",
  claire: "Cl",
}

const PHASE_LABELS: Record<string, string> = {
  consignes: "CONSIGNES",
  monologue: "MONOLOGUE",
  debat: "DEBAT",
  feedback: "FEEDBACK",
  results: "RESULTATS",
}

const PHASE_COLORS: Record<string, string> = {
  consignes: "bg-blue-100 text-blue-700 border-blue-300",
  monologue: "bg-green-100 text-green-700 border-green-300",
  debat: "bg-purple-100 text-purple-700 border-purple-300",
  feedback: "bg-amber-100 text-amber-700 border-amber-300",
}

const MONOLOGUE_MAX = 600 // 10 min
const DEBAT_MAX = 600 // 10 min

type AgentState = "connecting" | "listening" | "speaking" | "thinking"

export default function Exam() {
  const navigate = useNavigate()
  const {
    session,
    selectedAvatar,
    selectedDocument,
    setFeedback,
    livekitToken,
    livekitRoomName,
    livekitWsUrl,
    setConversationTranscript,
  } = useExam()

  // Phase state
  const [phase, setPhase] = useState<ExamPhase>("consignes")
  const [isListeningForReady, setIsListeningForReady] = useState(false)
  const [agentState, setAgentState] = useState<AgentState>("connecting")

  // Separate timers for monologue and debat
  const [monologueTime, setMonologueTime] = useState(0)
  const [debatTime, setDebatTime] = useState(0)

  // Connection state
  const [isEnding, setIsEnding] = useState(false)
  const [livekitConnected, setLivekitConnected] = useState(false)
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null)
  const [microphoneEnabled, setMicrophoneEnabled] = useState(true)

  // Transcript
  const [liveTranscript, setLiveTranscript] = useState<Array<{ role: string; text: string; phase: string }>>([])
  const transcriptEndRef = useRef<HTMLDivElement>(null)

  const avatarAudioRef = useRef<HTMLAudioElement>(null)
  const roomRef = useRef<Room | null>(null)

  // Redirect if no session
  useEffect(() => {
    if (!session || !selectedDocument) {
      navigate("/")
    }
  }, [session, selectedDocument, navigate])

  // Cleanup on page unload
  useEffect(() => {
    const handleBeforeUnload = async () => {
      if (livekitRoomName && roomRef.current) {
        roomRef.current.disconnect()
        try {
          await fetch(`/api/livekit/room/${livekitRoomName}`, { method: "DELETE", keepalive: true })
        } catch { /* ignore */ }
      }
    }
    window.addEventListener("beforeunload", handleBeforeUnload)
    return () => window.removeEventListener("beforeunload", handleBeforeUnload)
  }, [livekitRoomName])

  // LiveKit connection
  useEffect(() => {
    if (!livekitToken || !livekitRoomName || !livekitWsUrl) return

    const connectToLiveKit = async () => {
      try {
        const room = new Room()
        roomRef.current = room

        // Handle incoming audio from agent
        room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (participant.identity === room.localParticipant?.identity) return
          if (track.kind === Track.Kind.Audio && avatarAudioRef.current) {
            track.attach(avatarAudioRef.current)
          }
        })

        room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Audio) {
            track.detach()
          }
        })

        // Handle DataChannel events from agent
        room.on(RoomEvent.DataReceived, (payload: Uint8Array, _participant?: RemoteParticipant, _kind?: DataPacket_Kind, topic?: string) => {
          if (topic !== "exam") return
          try {
            const data = JSON.parse(new TextDecoder().decode(payload))
            console.log("Agent event:", data)

            switch (data.event) {
              case "phase_started":
                if (data.phase) setPhase(data.phase as ExamPhase)
                break
              case "listening_for_ready":
                setIsListeningForReady(data.active === true)
                setAgentState("listening")
                break
              case "ready_detected":
                setIsListeningForReady(false)
                break
              case "transition_to_monologue":
                setPhase("monologue")
                setIsListeningForReady(false)
                setAgentState("listening")
                break
              case "transition_to_debat":
                setPhase("debat")
                setAgentState("listening")
                break
              case "exam_complete":
                handleEndConversation()
                break
              case "transcript":
                if (data.role && data.text) {
                  setLiveTranscript(prev => [...prev, { role: data.role, text: data.text, phase: data.phase || phase }])
                }
                break
            }
          } catch (e) {
            console.error("Error parsing agent event:", e)
          }
        })

        // Track agent state from participant metadata/speaking
        room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
          const agentSpeaking = speakers.some(s => s.identity !== room.localParticipant?.identity)
          if (agentSpeaking) {
            setAgentState("speaking")
          } else {
            setAgentState("listening")
          }
        })

        room.on(RoomEvent.Connected, async () => {
          setLivekitConnected(true)
          setAgentState("listening")

          // Publish audio only (no video)
          try {
            const audioTrack = await createLocalAudioTrack()
            setLocalAudioTrack(audioTrack)
            await room.localParticipant?.publishTrack(audioTrack)
          } catch (error) {
            console.error("Error publishing audio:", error)
          }
        })

        room.on(RoomEvent.Disconnected, () => {
          setLivekitConnected(false)
          setAgentState("connecting")
        })

        await room.connect(livekitWsUrl, livekitToken)
      } catch (error) {
        console.error("LiveKit connection error:", error)
        setLivekitConnected(false)
      }
    }

    connectToLiveKit()

    return () => {
      localAudioTrack?.stop()
      roomRef.current?.disconnect()
      roomRef.current = null
    }
  }, [livekitToken, livekitRoomName, livekitWsUrl])

  // Monologue timer
  useEffect(() => {
    if (livekitConnected && phase === "monologue" && !isEnding) {
      const interval = setInterval(() => setMonologueTime(prev => prev + 1), 1000)
      return () => clearInterval(interval)
    }
  }, [livekitConnected, phase, isEnding])

  // Debat timer
  useEffect(() => {
    if (livekitConnected && phase === "debat" && !isEnding) {
      const interval = setInterval(() => setDebatTime(prev => prev + 1), 1000)
      return () => clearInterval(interval)
    }
  }, [livekitConnected, phase, isEnding])

  // Auto-scroll transcript
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [liveTranscript])

  // Toggle microphone
  const toggleMicrophone = useCallback(async () => {
    if (!roomRef.current) return
    if (microphoneEnabled && localAudioTrack) {
      localAudioTrack.stop()
      await roomRef.current.localParticipant?.unpublishTrack(localAudioTrack)
      setLocalAudioTrack(null)
      setMicrophoneEnabled(false)
    } else {
      try {
        const audioTrack = await createLocalAudioTrack()
        setLocalAudioTrack(audioTrack)
        await roomRef.current.localParticipant?.publishTrack(audioTrack)
        setMicrophoneEnabled(true)
      } catch (error) {
        console.error("Microphone error:", error)
      }
    }
  }, [microphoneEnabled, localAudioTrack])

  // End conversation
  const handleEndConversation = useCallback(async () => {
    if (isEnding) return
    setIsEnding(true)

    // Disconnect LiveKit
    if (roomRef.current) {
      roomRef.current.disconnect()
      roomRef.current = null
    }

    // Delete room
    if (livekitRoomName) {
      try { await deleteLivekitRoom(livekitRoomName) } catch { /* ignore */ }
    }

    // Submit evaluation first
    try {
      await submitEvaluation({
        session_id: session!.id,
        monologue_duration: monologueTime,
        debat_duration: debatTime,
      })
    } catch { /* evaluation may already be done by agent */ }

    // Get transcription
    try {
      const transcriptionData = await getTranscription(session!.id)
      if (transcriptionData?.transcript) {
        setConversationTranscript(transcriptionData.transcript)
      }
    } catch { /* no transcription available */ }

    // Get feedback
    try {
      const feedback = await getFeedback(session!.id, selectedAvatar?.id)
      setFeedback(feedback)
    } catch { /* no feedback available */ }

    navigate("/results")
  }, [session, selectedAvatar, livekitRoomName, setFeedback, setConversationTranscript, navigate, isEnding, monologueTime, debatTime])

  // Send "Je suis prêt" via DataChannel
  const handleReady = useCallback(async () => {
    if (!roomRef.current) return
    try {
      const payload = JSON.stringify({ event: "student_ready" })
      await roomRef.current.localParticipant?.publishData(
        new TextEncoder().encode(payload),
        { topic: "exam" }
      )
      setIsListeningForReady(false)
    } catch (error) {
      console.error("Error sending ready event:", error)
    }
  }, [])

  // Send "J'ai terminé"
  const handleFinished = useCallback(async () => {
    if (!roomRef.current) return
    try {
      const payload = JSON.stringify({ event: "student_finished" })
      await roomRef.current.localParticipant?.publishData(
        new TextEncoder().encode(payload),
        { topic: "exam" }
      )
    } catch (error) {
      console.error("Error sending finished event:", error)
    }
  }, [])

  // Monologue timer ended
  const monologueTimerEndedRef = useRef(false)
  useEffect(() => {
    if (phase !== "monologue" || !roomRef.current) return
    if (monologueTime >= MONOLOGUE_MAX && !monologueTimerEndedRef.current) {
      monologueTimerEndedRef.current = true
      try {
        const payload = JSON.stringify({ event: "monologue_timer_ended" })
        roomRef.current.localParticipant?.publishData(
          new TextEncoder().encode(payload),
          { topic: "exam" }
        )
      } catch (e) {
        console.error("Error sending monologue_timer_ended:", e)
      }
    }
  }, [phase, monologueTime])

  if (!session || !selectedDocument) return null

  // Timer display logic
  const getCurrentTime = () => {
    if (phase === "monologue") return monologueTime
    if (phase === "debat") return debatTime
    return 0
  }
  const getMaxTime = () => {
    if (phase === "monologue") return MONOLOGUE_MAX
    if (phase === "debat") return DEBAT_MAX
    return 0
  }
  const currentTime = getCurrentTime()
  const maxTime = getMaxTime()
  const timeRemaining = maxTime - currentTime
  const isWarning = phase === "monologue" && monologueTime >= 480 && monologueTime < 600
  const isOvertime = phase === "monologue" && monologueTime >= 600

  // SVG circular timer
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const progress = maxTime > 0 ? Math.min(currentTime / maxTime, 1) : 0
  const dashoffset = circumference * (1 - progress)

  const timerStrokeColor = () => {
    if (phase === "consignes") return "#93C5FD" // blue-300
    if (phase === "feedback") return "#D4D4D8" // zinc-300
    if (isOvertime) return "#EF4444" // red-500
    if (isWarning) return "#F59E0B" // amber-500
    if (phase === "monologue") return "#22C55E" // green-500
    if (phase === "debat") return "#A855F7" // purple-500
    return "#93C5FD"
  }

  // Agent state indicator
  const agentStateInfo = () => {
    switch (agentState) {
      case "speaking":
        return { color: "bg-green-500", pulse: false, text: "L'examinateur parle", icon: <Volume2 className="w-4 h-4" /> }
      case "thinking":
        return { color: "bg-yellow-500", pulse: true, text: "L'examinateur reflechit...", icon: <Loader2 className="w-4 h-4 animate-spin" /> }
      case "connecting":
        return { color: "bg-gray-400", pulse: true, text: "Connexion en cours...", icon: <Loader2 className="w-4 h-4 animate-spin" /> }
      case "listening":
      default:
        return { color: "bg-blue-500", pulse: true, text: "L'examinateur vous ecoute", icon: <Headphones className="w-4 h-4" /> }
    }
  }

  const stateInfo = agentStateInfo()

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 flex flex-col">
      {/* Hidden audio element for agent */}
      <audio ref={avatarAudioRef} autoPlay playsInline className="hidden" />

      {/* Header */}
      <header className="bg-white/90 backdrop-blur-sm border-b border-sky-200 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          {/* Avatar info */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-sky-400 to-blue-500 flex items-center justify-center text-white font-bold text-sm">
              {selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] || "E" : "E"}
            </div>
            <div>
              <p className="font-medium text-slate-800 text-sm">{selectedAvatar?.name || "Examinateur"}</p>
              <p className="text-xs text-slate-500">
                {livekitConnected ? (
                  <span className="text-green-600 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                    Connecte
                  </span>
                ) : (
                  "Connexion..."
                )}
              </p>
            </div>
          </div>

          {/* Phase Badge */}
          <Badge
            variant="outline"
            className={cn("text-sm font-semibold px-3 py-1", PHASE_COLORS[phase] || PHASE_COLORS.consignes)}
          >
            {PHASE_LABELS[phase] || phase.toUpperCase()}
          </Badge>

          {/* Circular Timer */}
          <div className="flex items-center gap-2">
            <svg width="90" height="90" viewBox="0 0 100 100" className="-rotate-90">
              <circle cx="50" cy="50" r={radius} fill="none" stroke="#E5E7EB" strokeWidth="6" />
              {(phase === "monologue" || phase === "debat") && (
                <circle
                  cx="50" cy="50" r={radius}
                  fill="none"
                  stroke={timerStrokeColor()}
                  strokeWidth="6"
                  strokeDasharray={circumference}
                  strokeDashoffset={dashoffset}
                  strokeLinecap="round"
                  className="transition-all duration-1000"
                />
              )}
              {phase === "consignes" && (
                <circle
                  cx="50" cy="50" r={radius}
                  fill="none"
                  stroke="#93C5FD"
                  strokeWidth="6"
                  strokeDasharray="8 4"
                  className="animate-pulse"
                />
              )}
            </svg>
            <div className="absolute w-[90px] flex items-center justify-center">
              <span className={cn(
                "font-mono text-sm font-bold",
                isOvertime && "text-red-600",
                isWarning && "text-amber-600",
                phase === "consignes" && "text-blue-500 text-xs",
              )}>
                {phase === "consignes" ? "Consignes" :
                  phase === "feedback" ? "Feedback" :
                  `${formatTime(Math.max(0, timeRemaining))}`}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center p-4 gap-4 max-w-3xl mx-auto w-full">
        {/* Agent State Indicator */}
        <Card className="w-full bg-white/90 border border-slate-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-3 h-3 rounded-full",
                stateInfo.color,
                stateInfo.pulse && "animate-pulse"
              )} />
              {stateInfo.icon}
              <span className="text-sm font-medium text-slate-700">{stateInfo.text}</span>

              {/* Mic level indicator */}
              {microphoneEnabled && localAudioTrack && (
                <div className="ml-auto flex items-center gap-1.5">
                  <Mic className="w-4 h-4 text-green-600" />
                  <div className="flex items-end gap-0.5 h-4">
                    {[1, 2, 3, 4, 5].map(i => (
                      <div
                        key={i}
                        className="w-1 bg-green-400 rounded-full animate-wave"
                        style={{
                          height: `${Math.random() * 60 + 40}%`,
                          animationDelay: `${i * 0.1}s`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* "Je suis pret" prompt */}
        {phase === "consignes" && isListeningForReady && (
          <Card className="w-full bg-white/90 border-2 border-green-200 shadow-lg">
            <CardContent className="p-5">
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <div className="flex items-center gap-2 text-green-700">
                  <span className="w-3 h-3 bg-green-500 rounded-full mic-active" />
                  <span className="font-medium text-sm">Dites "Je suis pret" ou cliquez sur le bouton</span>
                </div>
                <Button onClick={handleReady} className="bg-green-600 hover:bg-green-700 text-white shadow-md px-6">
                  <CheckCircle className="w-5 h-5 mr-2" />
                  Je suis pret(e)
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Document preview - during monologue */}
        {(phase === "monologue" || phase === "debat") && selectedDocument && (
          <Card className="w-full bg-white/90 border border-slate-200">
            <CardContent className="p-4">
              <p className="text-sm font-semibold text-slate-800 mb-1">{selectedDocument.title}</p>
              <p className="text-xs text-slate-600 leading-relaxed">{selectedDocument.text}</p>
              {selectedDocument.keywords && selectedDocument.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {selectedDocument.keywords.map((kw, i) => (
                    <Badge key={i} variant="secondary" className="text-xs bg-sky-50 text-sky-700 border-sky-200">
                      {kw}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Live transcript */}
        {liveTranscript.length > 0 && (
          <Card className="w-full bg-white/90 border border-slate-200 max-h-48 overflow-hidden">
            <CardContent className="p-3">
              <p className="text-xs font-medium text-slate-500 mb-2">Transcription en direct</p>
              <div className="space-y-1.5 max-h-32 overflow-y-auto text-sm">
                {liveTranscript.slice(-6).map((entry, i) => (
                  <div key={i} className={cn(
                    "text-xs px-2 py-1 rounded",
                    entry.role === "user" ? "bg-sky-50 text-sky-800 ml-4" : "bg-slate-50 text-slate-700 mr-4"
                  )}>
                    <span className="font-medium">{entry.role === "user" ? "Vous" : "Examinateur"}: </span>
                    {entry.text}
                  </div>
                ))}
                <div ref={transcriptEndRef} />
              </div>
            </CardContent>
          </Card>
        )}

        {/* Connection status overlay */}
        {!livekitConnected && (
          <Card className="w-full bg-white/90 border border-slate-200 shadow-lg">
            <CardContent className="p-8 text-center">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-sky-500" />
              <p className="text-slate-700 font-medium">Connexion en cours...</p>
              <p className="text-xs text-slate-500 mt-1">Preparation de la salle d'examen</p>
            </CardContent>
          </Card>
        )}
      </main>

      {/* Bottom controls */}
      <footer className="bg-white/90 backdrop-blur-sm border-t border-sky-200 px-4 py-4">
        <div className="max-w-3xl mx-auto flex items-center justify-center gap-3">
          {/* Mic toggle */}
          <Button
            size="lg"
            onClick={toggleMicrophone}
            className={cn(
              "rounded-full w-14 h-14 shadow-md",
              microphoneEnabled
                ? "bg-slate-100 border-2 border-slate-300 hover:bg-slate-200 text-slate-700"
                : "bg-red-500 hover:bg-red-600 text-white border-0"
            )}
          >
            {microphoneEnabled ? <Mic className="w-5 h-5 text-slate-700" /> : <MicOff className="w-5 h-5 text-white" />}
          </Button>

          {/* Je suis pret button (consignes phase) */}
          {phase === "consignes" && isListeningForReady && (
            <Button
              size="lg"
              onClick={handleReady}
              className="rounded-full px-6 bg-green-600 hover:bg-green-700 text-white shadow-md"
            >
              <CheckCircle className="w-5 h-5 mr-2" />
              Je suis pret(e)
            </Button>
          )}

          {/* J'ai termine button (monologue phase) */}
          {phase === "monologue" && (
            <Button
              size="lg"
              onClick={handleFinished}
              className="rounded-full px-6 bg-amber-500 hover:bg-amber-600 text-white shadow-md"
            >
              <Flag className="w-5 h-5 mr-2" />
              J'ai termine
            </Button>
          )}

          {/* End exam button */}
          {phase !== "consignes" && (
            <Button
              variant="destructive"
              size="lg"
              onClick={handleEndConversation}
              disabled={isEnding}
              className="rounded-full px-6"
            >
              {isEnding ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <>
                  <Phone className="w-5 h-5 mr-2" />
                  Terminer
                </>
              )}
            </Button>
          )}
        </div>
      </footer>
    </div>
  )
}
