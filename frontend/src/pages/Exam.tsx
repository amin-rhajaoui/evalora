import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { deleteLivekitRoom, getTranscription, getFeedback } from "@/services/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { cn, formatTime } from "@/lib/utils"
import { Mic, MicOff, Phone, Loader2, User, Video, VideoOff } from "lucide-react"
import { ExamPhase } from "@/types"
import {
  Room,
  RoomEvent,
  RemoteParticipant,
  RemoteTrackPublication,
  RemoteTrack,
  Track,
  LocalVideoTrack,
  LocalAudioTrack,
  createLocalVideoTrack,
  createLocalAudioTrack,
  DataPacket_Kind,
} from "livekit-client"

const AVATAR_EMOJIS: Record<string, string> = {
  clea: "👩‍🏫",
  alex: "🧑‍🎓",
  karim: "👨‍💼",
  claire: "👩‍💼",
}

const PHASE_LABELS: Record<ExamPhase, string> = {
  consignes: "CONSIGNES",
  monologue: "MONOLOGUE",
  debat: "DÉBAT",
  results: "RÉSULTATS",
}

const MAX_TIME = 900 // 15 minutes

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

  // Timer and connection state
  const [elapsedTime, setElapsedTime] = useState(0)
  const [isEnding, setIsEnding] = useState(false)
  const [livekitConnected, setLivekitConnected] = useState(false)
  const [livekitAudioTrack, setLivekitAudioTrack] = useState<RemoteTrack | null>(null)
  const [localVideoTrack, setLocalVideoTrack] = useState<LocalVideoTrack | null>(null)
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(true)
  const [microphoneEnabled, setMicrophoneEnabled] = useState(true)

  const avatarAudioRef = useRef<HTMLAudioElement>(null)
  const userVideoRef = useRef<HTMLVideoElement>(null)
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
          await fetch(`/api/livekit/room/${livekitRoomName}`, {
            method: "DELETE",
            keepalive: true,
          })
        } catch {
          // ignore
        }
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

        // Handle incoming audio from avatar
        room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, _pub: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (participant.identity === room.localParticipant?.identity) return

          if (track.kind === Track.Kind.Audio) {
            setLivekitAudioTrack(track)
            if (avatarAudioRef.current) {
              track.attach(avatarAudioRef.current)
            }
          }
        })

        room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Audio) {
            track.detach()
            setLivekitAudioTrack(null)
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
                if (data.phase) {
                  setPhase(data.phase as ExamPhase)
                }
                break
              case "listening_for_ready":
                setIsListeningForReady(data.active === true)
                break
              case "ready_detected":
                setIsListeningForReady(false)
                break
              case "transition_to_monologue":
                setPhase("monologue")
                setIsListeningForReady(false)
                break
              case "transition_to_debat":
                setPhase("debat")
                break
            }
          } catch (e) {
            console.error("Error parsing agent event:", e)
          }
        })

        room.on(RoomEvent.Connected, async () => {
          setLivekitConnected(true)

          // Publish user camera and mic
          try {
            const videoTrack = await createLocalVideoTrack({
              facingMode: "user",
              resolution: { width: 1280, height: 720 },
            })
            setLocalVideoTrack(videoTrack)
            await room.localParticipant?.publishTrack(videoTrack)
            if (userVideoRef.current) {
              videoTrack.attach(userVideoRef.current)
            }

            const audioTrack = await createLocalAudioTrack()
            setLocalAudioTrack(audioTrack)
            await room.localParticipant?.publishTrack(audioTrack)
          } catch (error) {
            console.error("Error publishing tracks:", error)
          }
        })

        room.on(RoomEvent.Disconnected, () => {
          setLivekitConnected(false)
          setLivekitAudioTrack(null)
        })

        await room.connect(livekitWsUrl, livekitToken)
      } catch (error) {
        console.error("LiveKit connection error:", error)
        setLivekitConnected(false)
      }
    }

    connectToLiveKit()

    return () => {
      localVideoTrack?.stop()
      localAudioTrack?.stop()
      roomRef.current?.disconnect()
      roomRef.current = null
    }
  }, [livekitToken, livekitRoomName, livekitWsUrl])

  // Attach local video
  useEffect(() => {
    if (localVideoTrack && userVideoRef.current) {
      localVideoTrack.attach(userVideoRef.current)
      return () => {
        localVideoTrack.detach()
      }
    }
  }, [localVideoTrack])

  // Attach avatar audio
  useEffect(() => {
    if (livekitAudioTrack && avatarAudioRef.current) {
      livekitAudioTrack.attach(avatarAudioRef.current)
      return () => {
        livekitAudioTrack.detach()
      }
    }
  }, [livekitAudioTrack])

  // Timer - only starts when connected and during monologue/debat phases
  useEffect(() => {
    if (livekitConnected && !isEnding && phase !== "consignes") {
      const interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1)
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [livekitConnected, isEnding, phase])

  // Toggle camera
  const toggleCamera = useCallback(async () => {
    if (!roomRef.current) return

    if (cameraEnabled && localVideoTrack) {
      localVideoTrack.stop()
      await roomRef.current.localParticipant?.unpublishTrack(localVideoTrack)
      setLocalVideoTrack(null)
      setCameraEnabled(false)
    } else {
      try {
        const videoTrack = await createLocalVideoTrack({
          facingMode: "user",
          resolution: { width: 1280, height: 720 },
        })
        setLocalVideoTrack(videoTrack)
        await roomRef.current.localParticipant?.publishTrack(videoTrack)
        if (userVideoRef.current) {
          videoTrack.attach(userVideoRef.current)
        }
        setCameraEnabled(true)
      } catch (error) {
        console.error("Camera error:", error)
      }
    }
  }, [cameraEnabled, localVideoTrack])

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
    setIsEnding(true)

    // Disconnect LiveKit
    if (roomRef.current) {
      roomRef.current.disconnect()
      roomRef.current = null
    }

    // Delete room
    if (livekitRoomName) {
      try {
        await deleteLivekitRoom(livekitRoomName)
      } catch {
        // ignore
      }
    }

    // Get transcription and feedback
    try {
      const transcriptionData = await getTranscription(session!.id)
      if (transcriptionData?.transcript) {
        setConversationTranscript(transcriptionData.transcript)
      }
    } catch {
      // No transcription available
    }

    try {
      const feedback = await getFeedback(session!.id, selectedAvatar?.id)
      setFeedback(feedback)
    } catch {
      // No feedback available
    }

    navigate("/results")
  }, [session, selectedAvatar, livekitRoomName, setFeedback, setConversationTranscript, navigate])

  if (!session || !selectedDocument) return null

  const timeRemaining = MAX_TIME - elapsedTime
  const isWarning = timeRemaining <= 120 && timeRemaining > 0
  const isOvertime = timeRemaining <= 0

  // Timer class based on phase
  const getTimerClass = () => {
    if (isOvertime) return "timer-overtime"
    if (isWarning) return "timer-warning"
    if (phase === "consignes") return "timer-consignes"
    return "timer-monologue"
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 flex flex-col">
      {/* Hidden audio element for avatar */}
      <audio ref={avatarAudioRef} autoPlay playsInline className="hidden" />

      {/* Header */}
      <header className="bg-white/90 backdrop-blur-sm border-b border-sky-200 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-2xl">{selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] : "👤"}</div>
            <div>
              <p className="font-medium text-slate-800">{selectedAvatar?.name || "Avatar"}</p>
              <p className="text-xs text-slate-500">
                {livekitConnected ? (
                  <span className="text-green-600 flex items-center gap-1">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
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
            className={cn(
              "text-sm font-semibold px-3 py-1",
              phase === "consignes" && "bg-blue-100 text-blue-700 border-blue-300",
              phase === "monologue" && "bg-green-100 text-green-700 border-green-300",
              phase === "debat" && "bg-purple-100 text-purple-700 border-purple-300"
            )}
          >
            {PHASE_LABELS[phase]}
          </Badge>

          {/* Timer */}
          <div
            className={cn(
              "px-4 py-2 rounded-full font-mono text-lg font-bold",
              getTimerClass()
            )}
          >
            {phase === "consignes" ? (
              <span className="text-sm">Consignes...</span>
            ) : (
              <>
                {isOvertime ? "-" : ""}
                {formatTime(Math.abs(timeRemaining))}
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex flex-col items-center justify-center p-4 gap-6">
        {/* Phase Consignes: Just show listening indicator when ready */}
        {phase === "consignes" && isListeningForReady && (
          <Card className="w-full max-w-2xl bg-white/90 border-2 border-green-200">
            <CardContent className="p-4 text-center">
              <div className="flex items-center justify-center gap-2 text-green-700">
                <span className="w-3 h-3 bg-green-500 rounded-full mic-active" />
                <span className="font-medium">Dites "Je suis prêt" pour commencer</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Video area */}
        <Card className="w-full max-w-2xl overflow-hidden">
          <div className="aspect-video bg-slate-900 relative">
            {localVideoTrack ? (
              <video
                ref={userVideoRef}
                className="w-full h-full object-cover"
                autoPlay
                playsInline
                muted
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <User className="w-16 h-16 text-slate-600" />
              </div>
            )}

            {/* Status overlay */}
            <div className="absolute top-3 left-3 flex gap-2">
              {!cameraEnabled && (
                <span className="bg-red-500/80 text-white text-xs px-2 py-1 rounded">
                  Camera off
                </span>
              )}
              {!microphoneEnabled && (
                <span className="bg-red-500/80 text-white text-xs px-2 py-1 rounded">
                  Micro off
                </span>
              )}
            </div>

            {/* Microphone indicator */}
            <div className="absolute bottom-3 right-3">
              {microphoneEnabled && localAudioTrack && (
                <div className="flex items-center gap-2 bg-black/60 text-white px-3 py-1.5 rounded-full">
                  <span className="w-2 h-2 bg-green-500 rounded-full mic-active" />
                  <Mic className="w-4 h-4" />
                </div>
              )}
            </div>

            {/* Connection status */}
            {!livekitConnected && (
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                <div className="text-center text-white">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                  <p>Connexion en cours...</p>
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Controls */}
        <div className="flex items-center gap-4">
          <Button
            variant={cameraEnabled ? "outline" : "destructive"}
            size="lg"
            onClick={toggleCamera}
            className="rounded-full w-14 h-14"
          >
            {cameraEnabled ? <Video className="w-5 h-5" /> : <VideoOff className="w-5 h-5" />}
          </Button>

          <Button
            variant={microphoneEnabled ? "outline" : "destructive"}
            size="lg"
            onClick={toggleMicrophone}
            className="rounded-full w-14 h-14"
          >
            {microphoneEnabled ? <Mic className="w-5 h-5" /> : <MicOff className="w-5 h-5" />}
          </Button>

          {/* Only show end button after consignes */}
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

        {/* Document preview - only show during monologue/debat */}
        {phase !== "consignes" && (
          <Card className="w-full max-w-2xl">
            <CardContent className="p-4">
              <p className="text-sm font-medium text-slate-800 mb-1">{selectedDocument.title}</p>
              <p className="text-xs text-slate-500 line-clamp-2">{selectedDocument.text}</p>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
