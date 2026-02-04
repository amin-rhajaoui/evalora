import { useState, useEffect, useCallback, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useExam } from "@/contexts/ExamContext"
import { transitionPhase, submitEvaluation, getFeedback, getAvatarMessages, deleteLivekitRoom, getTranscription } from "@/services/api"
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
  Heart,
  Sparkles,
  ThumbsUp,
} from "lucide-react"
import { Room, RoomEvent, RemoteParticipant, RemoteTrackPublication, RemoteTrack, Track, LocalVideoTrack, LocalAudioTrack, createLocalVideoTrack, createLocalAudioTrack } from "livekit-client"

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
    livekitToken,
    livekitRoomName,
    livekitWsUrl,
    setConversationTranscript,
  } = useExam()

  const [elapsedTime, setElapsedTime] = useState(0)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [messages, setMessages] = useState<{ role: "avatar" | "student"; text: string }[]>([])
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [debateQuestions, setDebateQuestions] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [livekitConnected, setLivekitConnected] = useState(false)
  const [livekitVideoTrack, setLivekitVideoTrack] = useState<RemoteTrack | null>(null)
  const [livekitAudioTrack, setLivekitAudioTrack] = useState<RemoteTrack | null>(null)
  const [localVideoTrack, setLocalVideoTrack] = useState<LocalVideoTrack | null>(null)
  const [localAudioTrack, setLocalAudioTrack] = useState<LocalAudioTrack | null>(null)
  const [cameraEnabled, setCameraEnabled] = useState(true)
  const [microphoneEnabled, setMicrophoneEnabled] = useState(true)
  const avatarVideoRef = useRef<HTMLVideoElement>(null)
  const avatarAudioRef = useRef<HTMLAudioElement>(null)
  const userVideoRef = useRef<HTMLVideoElement>(null)
  const roomRef = useRef<Room | null>(null)

  useEffect(() => {
    if (!session || !selectedDocument) {
      navigate("/")
    }
  }, [session, selectedDocument, navigate])

  // Gestionnaire pour supprimer la room quand l'utilisateur quitte la page
  useEffect(() => {
    const handleBeforeUnload = async () => {
      if (livekitRoomName && roomRef.current) {
        // Déconnecter de LiveKit
        roomRef.current.disconnect()
        // Supprimer la room (envoi synchrone via sendBeacon si possible)
        try {
          await fetch(`/api/livekit/room/${livekitRoomName}`, {
            method: "DELETE",
            keepalive: true,
          })
        } catch (error) {
          console.error("Erreur lors de la suppression de la room:", error)
        }
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload)
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload)
    }
  }, [livekitRoomName])

  // Connexion LiveKit avec caméra et micro
  // On se connecte toujours à LiveKit pour que l'utilisateur puisse se voir
  // Même si Tavus est utilisé pour Clea
  useEffect(() => {
    // Vérifier que LiveKit est configuré
    if (!livekitToken || !livekitRoomName || !livekitWsUrl) {
      return
    }

    const connectToLiveKit = async () => {
      try {
        const room = new Room()
        roomRef.current = room

        // Gérer les tracks reçus (avatar - vidéo et audio)
        room.on(RoomEvent.TrackSubscribed, (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          // Ne prendre que les tracks des autres participants (pas soi-même)
          if (participant.identity === room.localParticipant?.identity) {
            return
          }

          console.log(`Track reçu de ${participant.identity}:`, track.kind, track.source)

          if (track.kind === Track.Kind.Video) {
            setLivekitVideoTrack(track)
            if (avatarVideoRef.current) {
              track.attach(avatarVideoRef.current)
              console.log("Track vidéo avatar attaché")
            }
          } else if (track.kind === Track.Kind.Audio) {
            setLivekitAudioTrack(track)
            if (avatarAudioRef.current) {
              track.attach(avatarAudioRef.current)
              console.log("Track audio avatar attaché")
            }
          }
        })

        room.on(RoomEvent.TrackUnsubscribed, (track: RemoteTrack) => {
          if (track.kind === Track.Kind.Video) {
            track.detach()
            setLivekitVideoTrack(null)
            console.log("Track vidéo avatar détaché")
          } else if (track.kind === Track.Kind.Audio) {
            track.detach()
            setLivekitAudioTrack(null)
            console.log("Track audio avatar détaché")
          }
        })

        // Écouter quand un participant rejoint
        room.on(RoomEvent.ParticipantConnected, (participant: RemoteParticipant) => {
          console.log(`Participant connecté: ${participant.identity}`, participant.name)
          // Vérifier les tracks déjà publiés
          participant.trackPublications.forEach((publication) => {
            if (publication.track) {
              console.log(`Track déjà publié: ${publication.track.kind}`, publication.track.source)
            }
          })
        })

        // Écouter quand des tracks sont publiés
        room.on(RoomEvent.TrackPublished, (publication: RemoteTrackPublication, participant: RemoteParticipant) => {
          if (participant.identity !== room.localParticipant?.identity) {
            console.log(`Track publié par ${participant.identity}:`, publication.kind, publication.trackSource)
          }
        })

        room.on(RoomEvent.Connected, async () => {
          setLivekitConnected(true)
          console.log("Connecté à LiveKit room:", livekitRoomName)
          console.log("Participants dans la room:", room.remoteParticipants.size)
          
          // Vérifier les participants déjà présents
          room.remoteParticipants.forEach((participant) => {
            console.log(`Participant déjà présent: ${participant.identity}`, participant.name)
            participant.trackPublications.forEach((publication) => {
              if (publication.track) {
                console.log(`Track existant: ${publication.track.kind}`, publication.track.source)
              }
            })
          })
          
          // Activer la caméra et le micro de l'utilisateur
          try {
            if (cameraEnabled) {
              const videoTrack = await createLocalVideoTrack({
                facingMode: "user",
                resolution: { width: 1280, height: 720 }
              })
              setLocalVideoTrack(videoTrack)
              await room.localParticipant?.publishTrack(videoTrack)
              
              // Attacher la vidéo locale à l'élément vidéo utilisateur
              if (userVideoRef.current) {
                videoTrack.attach(userVideoRef.current)
              }
            }
            
            if (microphoneEnabled) {
              const audioTrack = await createLocalAudioTrack()
              setLocalAudioTrack(audioTrack)
              await room.localParticipant?.publishTrack(audioTrack)
            }
          } catch (error) {
            console.error("Erreur lors de l'activation de la caméra/micro:", error)
          }
        })

        room.on(RoomEvent.Disconnected, () => {
          setLivekitConnected(false)
          setLivekitVideoTrack(null)
          // Arrêter les tracks locaux
          if (localVideoTrack) {
            localVideoTrack.stop()
            setLocalVideoTrack(null)
          }
          if (localAudioTrack) {
            localAudioTrack.stop()
            setLocalAudioTrack(null)
          }
        })

        // Se connecter à la room
        await room.connect(livekitWsUrl, livekitToken)
      } catch (error) {
        console.error("Erreur de connexion LiveKit:", error)
        setLivekitConnected(false)
      }
    }

    connectToLiveKit()

    // Nettoyage à la déconnexion - NE PAS supprimer la room ici
    // La room sera supprimée dans handleEndDebate ou beforeunload
    return () => {
      if (localVideoTrack) {
        localVideoTrack.stop()
        setLocalVideoTrack(null)
      }
      if (localAudioTrack) {
        localAudioTrack.stop()
        setLocalAudioTrack(null)
      }
      if (roomRef.current) {
        roomRef.current.disconnect()
        roomRef.current = null
      }
    }
  }, [livekitToken, livekitRoomName, livekitWsUrl])

  // Attacher/détacher la vidéo de l'avatar quand le track change
  useEffect(() => {
    if (livekitVideoTrack && avatarVideoRef.current) {
      livekitVideoTrack.attach(avatarVideoRef.current)
      return () => {
        livekitVideoTrack.detach()
      }
    }
  }, [livekitVideoTrack])

  // Attacher/détacher l'audio de l'avatar quand le track change
  useEffect(() => {
    if (livekitAudioTrack && avatarAudioRef.current) {
      livekitAudioTrack.attach(avatarAudioRef.current)
      return () => {
        livekitAudioTrack.detach()
      }
    }
  }, [livekitAudioTrack])

  // Attacher/détacher la vidéo locale de l'utilisateur
  useEffect(() => {
    if (localVideoTrack && userVideoRef.current) {
      localVideoTrack.attach(userVideoRef.current)
      return () => {
        localVideoTrack.detach()
      }
    }
  }, [localVideoTrack])

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
    
    // Déconnecter de LiveKit et supprimer la room avant de naviguer
    if (roomRef.current) {
      roomRef.current.disconnect()
      roomRef.current = null
    }
    if (livekitRoomName) {
      try {
        await deleteLivekitRoom(livekitRoomName)
        console.log("Room LiveKit supprimée avec succès")
      } catch (error) {
        console.error("Erreur lors de la suppression de la room LiveKit:", error)
      }
    }
    
    try {
      await submitEvaluation({
        session_id: session!.id,
        monologue_duration: monologueDuration,
        debat_duration: elapsedTime,
      })
      const feedback = await getFeedback(session!.id, selectedAvatar?.id)
      setFeedback(feedback)

      // Récupérer la transcription de la conversation vocale
      try {
        const transcriptionData = await getTranscription(session!.id)
        if (transcriptionData?.transcript) {
          setConversationTranscript(transcriptionData.transcript)
        }
      } catch (transcriptError) {
        console.log("Pas de transcription disponible:", transcriptError)
      }

      setTimeout(() => navigate("/results"), 2000)
    } catch {
      // Error submitting evaluation - navigate to results anyway
      navigate("/results")
    }
  }, [session, elapsedTime, monologueDuration, selectedAvatar, setCurrentPhase, setDebatDuration, setFeedback, setConversationTranscript, navigate, livekitRoomName])

  // Toggle caméra
  const toggleCamera = useCallback(async () => {
    if (!roomRef.current) return
    
    if (cameraEnabled && localVideoTrack) {
      // Désactiver la caméra
      localVideoTrack.stop()
      await roomRef.current.localParticipant?.unpublishTrack(localVideoTrack)
      setLocalVideoTrack(null)
      setCameraEnabled(false)
    } else {
      // Activer la caméra
      try {
        const videoTrack = await createLocalVideoTrack({
          facingMode: "user",
          resolution: { width: 1280, height: 720 }
        })
        setLocalVideoTrack(videoTrack)
        await roomRef.current.localParticipant?.publishTrack(videoTrack)
        if (userVideoRef.current) {
          videoTrack.attach(userVideoRef.current)
        }
        setCameraEnabled(true)
      } catch (error) {
        console.error("Erreur activation caméra:", error)
      }
    }
  }, [cameraEnabled, localVideoTrack])

  // Toggle micro
  const toggleMicrophone = useCallback(async () => {
    if (!roomRef.current) return
    
    if (microphoneEnabled && localAudioTrack) {
      // Désactiver le micro
      localAudioTrack.stop()
      await roomRef.current.localParticipant?.unpublishTrack(localAudioTrack)
      setLocalAudioTrack(null)
      setMicrophoneEnabled(false)
    } else {
      // Activer le micro
      try {
        const audioTrack = await createLocalAudioTrack()
        setLocalAudioTrack(audioTrack)
        await roomRef.current.localParticipant?.publishTrack(audioTrack)
        setMicrophoneEnabled(true)
      } catch (error) {
        console.error("Erreur activation micro:", error)
      }
    }
  }, [microphoneEnabled, localAudioTrack])

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
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50">
      {/* Top Bar */}
      <div className="bg-white/90 backdrop-blur-sm border-b-2 border-sky-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Badge variant="outline" className={cn("text-white border-0 shadow-sm", phaseConfig.color)}>
              {phaseConfig.label}
            </Badge>
            <span className="text-sm text-slate-600 font-medium">
              {selectedDocument.title}
            </span>
          </div>

          {/* Timer avec encouragements */}
          <div className="flex items-center gap-4">
            {/* Message d'encouragement */}
            {currentPhase === "monologue" && elapsedTime > 0 && !isEnded && (
              <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-full">
                <Sparkles className="w-4 h-4 text-green-600" />
                <span className="text-xs text-green-700 font-medium">Vous y arrivez !</span>
              </div>
            )}
            
            <div className={cn(
              "flex items-center gap-3 px-5 py-2.5 rounded-full border-2 transition-all shadow-sm",
              isEnded ? "border-red-400 bg-red-50" :
              isWarning ? "border-amber-400 bg-amber-50" :
              "border-sky-300 bg-white"
            )}>
              <div className={cn(
                "w-3 h-3 rounded-full",
                isTimerRunning ? "bg-green-500 animate-pulse" : "bg-slate-300"
              )} />
              <span className={cn(
                "font-mono text-xl font-bold tabular-nums",
                isEnded ? "text-red-600" : isWarning ? "text-amber-600" : "text-slate-800"
              )}>
                {formatTime(elapsedTime)}
              </span>
              {phaseConfig.maxTime && (
                <span className="text-sm text-slate-500">
                  / {formatTime(phaseConfig.maxTime)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Progress */}
        <Progress value={progress} className="h-1.5 rounded-none bg-slate-100" />
      </div>

      <div className="max-w-7xl mx-auto p-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-4">
          {/* Video Zone - Avatar et Utilisateur */}
          <Card className="overflow-hidden">
            {tavusConversationUrl ? (
              <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
                <iframe
                  src={tavusConversationUrl}
                  className="w-full h-full border-0"
                  allow="camera; microphone; autoplay; fullscreen"
                  title="Conversation Tavus avec Clea"
                />
                <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                  {selectedAvatar?.name || "Clea"}
                </div>
              </div>
            ) : livekitConnected ? (
              <div className="grid grid-cols-2 gap-2 p-2 bg-slate-900 aspect-video">
                {/* Vidéo Avatar Cléa */}
                <div className="relative bg-slate-800 rounded-lg overflow-hidden">
                  {/* Élément audio caché pour l'avatar */}
                  <audio
                    ref={avatarAudioRef}
                    autoPlay
                    playsInline
                    className="hidden"
                  />
                  {livekitVideoTrack ? (
                    <video
                      ref={avatarVideoRef}
                      className="w-full h-full object-cover"
                      autoPlay
                      playsInline
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white">
                      <div className="text-center">
                        <div className="text-4xl mb-2">
                          {selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] : "👤"}
                        </div>
                        <p className="text-sm">{selectedAvatar?.name || "Avatar"}</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {livekitConnected 
                            ? "En attente de connexion de l'avatar à LiveKit..." 
                            : "En attente..."}
                        </p>
                        {livekitConnected && (
                          <p className="text-xs text-slate-500 mt-2">
                            Vérifiez la console pour les logs de débogage
                          </p>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                    {selectedAvatar?.name || "Avatar"}
                  </div>
                </div>

                {/* Vidéo Utilisateur */}
                <div className="relative bg-slate-800 rounded-lg overflow-hidden">
                  {localVideoTrack ? (
                    <video
                      ref={userVideoRef}
                      className="w-full h-full object-cover"
                      autoPlay
                      playsInline
                      muted
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white">
                      <div className="text-center">
                        <User className="w-12 h-12 mx-auto mb-2 text-slate-400" />
                        <p className="text-sm">Vous</p>
                        <p className="text-xs text-slate-400 mt-1">
                          {cameraEnabled ? "Activation caméra..." : "Caméra désactivée"}
                        </p>
                      </div>
                    </div>
                  )}
                  <div className="absolute bottom-2 left-2 bg-black/50 text-white text-xs px-2 py-1 rounded">
                    Vous
                  </div>
                  {/* Indicateurs caméra/micro */}
                  <div className="absolute top-2 right-2 flex gap-1">
                    {!cameraEnabled && (
                      <div className="bg-red-500 text-white text-xs px-2 py-1 rounded">
                        📷 Off
                      </div>
                    )}
                    {!microphoneEnabled && (
                      <div className="bg-red-500 text-white text-xs px-2 py-1 rounded">
                        🎤 Off
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="aspect-video bg-slate-900 flex items-center justify-center relative">
                <div className="text-center text-white">
                  <div className="text-6xl mb-4 animate-float">
                    {selectedAvatar ? AVATAR_EMOJIS[selectedAvatar.id] : "👤"}
                  </div>
                  <p className="text-lg font-medium">
                    {selectedAvatar?.name || "Examinateur"}
                  </p>
                  <p className="text-sm text-slate-400 mt-1">
                    {livekitToken && !livekitConnected
                      ? "Connexion en cours..."
                      : currentPhase === "monologue"
                      ? "En ecoute..."
                      : "Mode texte"}
                  </p>
                  {currentPhase !== "monologue" && !livekitToken && (
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
              </div>
            )}
          </Card>

          {/* Document */}
          <Card className="border-2 border-slate-200 shadow-sm">
            <CardHeader className="pb-3 bg-gradient-to-r from-slate-50 to-blue-50/30 border-b border-slate-200">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg text-slate-800">{selectedDocument.title}</CardTitle>
                <Badge variant="secondary" className="bg-sky-100 text-sky-700 border-sky-200">
                  {selectedDocument.theme}
                </Badge>
              </div>
              <p className="text-sm text-slate-600 mt-1">
                {selectedDocument.source} | {selectedDocument.date}
              </p>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="bg-white/60 rounded-lg p-4 border border-slate-200">
                <p className="text-foreground leading-relaxed text-base">
                  {selectedDocument.text}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Actions avec encouragements */}
          <div className="flex flex-col items-center gap-4">
            {currentPhase === "consignes" && (
              <>
                <Button 
                  size="lg" 
                  onClick={handleStartMonologue} 
                  className="gap-2 bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl"
                >
                  <Play className="w-5 h-5" />
                  Je suis prêt(e) !
                </Button>
                <Card className="bg-blue-50/80 border-2 border-blue-200 max-w-md">
                  <div className="p-3 text-center">
                    <p className="text-sm text-slate-700">
                      <Heart className="w-4 h-4 inline mr-1 text-pink-400" />
                      Prenez votre temps, respirez, et faites de votre mieux !
                    </p>
                  </div>
                </Card>
              </>
            )}
            {currentPhase === "monologue" && (
              <>
                <Button 
                  size="lg" 
                  variant="success" 
                  onClick={handleEndMonologue} 
                  className="gap-2 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white shadow-lg"
                >
                  <Square className="w-5 h-5" />
                  J'ai terminé
                </Button>
                {elapsedTime > 30 && (
                  <Card className="bg-green-50/80 border-2 border-green-200 max-w-md">
                    <div className="p-3 text-center">
                      <p className="text-sm text-slate-700">
                        <ThumbsUp className="w-4 h-4 inline mr-1 text-green-600" />
                        Vous vous débrouillez très bien ! Continuez ainsi.
                      </p>
                    </div>
                  </Card>
                )}
              </>
            )}
            {currentPhase === "debat" && (
              <>
                <Button 
                  size="lg" 
                  variant="success" 
                  onClick={handleNextQuestion} 
                  className="gap-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg"
                >
                  <ChevronRight className="w-5 h-5" />
                  Question suivante
                </Button>
                <Card className="bg-purple-50/80 border-2 border-purple-200 max-w-md">
                  <div className="p-3 text-center">
                    <p className="text-sm text-slate-700">
                      <Sparkles className="w-4 h-4 inline mr-1 text-purple-600" />
                      N'hésitez pas à exprimer votre opinion, il n'y a pas de mauvaise réponse !
                    </p>
                  </div>
                </Card>
              </>
            )}
            {isLoading && (
              <Card className="bg-gradient-to-r from-sky-50 to-blue-50 border-2 border-sky-200">
                <div className="p-4 flex flex-col items-center gap-3">
                  <Loader2 className="w-6 h-6 animate-spin text-sky-600" />
                  <p className="text-sm font-medium text-slate-700">
                    Calcul de votre évaluation...
                  </p>
                  <p className="text-xs text-slate-500">
                    Nous analysons votre performance avec bienveillance
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>

        {/* Sidebar - Chat */}
        <div className="space-y-4">
          <Card className="h-[500px] flex flex-col border-2 border-slate-200 shadow-sm">
            <CardHeader className="pb-3 border-b-2 border-slate-200 bg-gradient-to-r from-slate-50 to-blue-50/30">
              <CardTitle className="text-base flex items-center gap-2 text-slate-800">
                <MessageCircle className="w-4 h-4 text-sky-600" />
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
                      "max-w-[80%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed",
                      msg.role === "student"
                        ? "bg-gradient-to-br from-sky-500 to-blue-500 text-white rounded-br-md shadow-sm"
                        : "bg-white border-2 border-slate-200 rounded-bl-md text-slate-700"
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

          {/* Controls - Caméra et Micro */}
          {livekitConnected && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-4">
                  {/* Contrôle Caméra */}
                  <Button
                    variant={cameraEnabled ? "default" : "outline"}
                    size="sm"
                    onClick={toggleCamera}
                    className="flex items-center gap-2"
                  >
                    {cameraEnabled ? (
                      <>
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        Caméra activée
                      </>
                    ) : (
                      <>
                        <div className="w-2 h-2 bg-red-500 rounded-full" />
                        Caméra désactivée
                      </>
                    )}
                  </Button>

                  {/* Contrôle Micro */}
                  <Button
                    variant={microphoneEnabled ? "default" : "outline"}
                    size="sm"
                    onClick={toggleMicrophone}
                    className="flex items-center gap-2"
                  >
                    {microphoneEnabled ? (
                      <>
                        <Mic className="w-4 h-4" />
                        Micro activé
                      </>
                    ) : (
                      <>
                        <MicOff className="w-4 h-4" />
                        Micro désactivé
                      </>
                    )}
                  </Button>

                  {/* Statut connexion */}
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className={cn(
                      "w-2 h-2 rounded-full",
                      livekitConnected ? "bg-green-500" : "bg-red-500"
                    )} />
                    {livekitConnected ? "Connecté" : "Déconnecté"}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Mic Status (si pas LiveKit) */}
          {!livekitConnected && (
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
          )}
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
