import { useState, useEffect, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import {
  Mic,
  MicOff,
  Check,
  AlertCircle,
  Play,
  ArrowRight,
  Loader2,
  Volume2,
} from "lucide-react"

type MicStatus = "idle" | "requesting" | "granted" | "denied" | "error"
type RecordingStatus = "idle" | "recording" | "recorded"

export default function MicTest() {
  const navigate = useNavigate()

  const [micStatus, setMicStatus] = useState<MicStatus>("idle")
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("")
  const [vuLevels, setVuLevels] = useState<number[]>([0, 0, 0, 0, 0])
  const [micConfirmed, setMicConfirmed] = useState(false)
  const [recordingStatus, setRecordingStatus] = useState<RecordingStatus>("idle")
  const [recordingCountdown, setRecordingCountdown] = useState(5)
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  const streamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioPlaybackRef = useRef<HTMLAudioElement | null>(null)

  // Request microphone permission and list devices
  const requestMicPermission = useCallback(async (deviceId?: string) => {
    setMicStatus("requesting")

    try {
      // Stop any existing stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }

      const constraints: MediaStreamConstraints = {
        audio: deviceId ? { deviceId: { exact: deviceId } } : true,
      }

      const stream = await navigator.mediaDevices.getUserMedia(constraints)
      streamRef.current = stream

      // List available audio input devices
      const allDevices = await navigator.mediaDevices.enumerateDevices()
      const audioInputs = allDevices.filter((d) => d.kind === "audioinput")
      setDevices(audioInputs)

      // Set selected device if not already set
      if (!deviceId && audioInputs.length > 0) {
        const activeTrack = stream.getAudioTracks()[0]
        const settings = activeTrack.getSettings()
        setSelectedDeviceId(settings.deviceId || audioInputs[0].deviceId)
      }

      // Set up AudioContext and AnalyserNode for VU meter
      const audioContext = new AudioContext()
      audioContextRef.current = audioContext
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      analyserRef.current = analyser

      const source = audioContext.createMediaStreamSource(stream)
      source.connect(analyser)

      setMicStatus("granted")
      startVuMeter()
    } catch (err) {
      const error = err as DOMException
      if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
        setMicStatus("denied")
      } else {
        setMicStatus("error")
      }
    }
  }, [])

  // Start VU meter animation loop
  const startVuMeter = useCallback(() => {
    const update = () => {
      if (!analyserRef.current) return

      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
      analyserRef.current.getByteFrequencyData(dataArray)

      // Compute average volume
      const average = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length
      const normalizedLevel = Math.min(average / 128, 1)

      // Check if mic is picking up sound (confirm working)
      if (normalizedLevel > 0.05) {
        setMicConfirmed(true)
      }

      // Split into 5 bars with slight variation
      const barCount = 5
      const levels: number[] = []
      const segmentSize = Math.floor(dataArray.length / barCount)
      for (let i = 0; i < barCount; i++) {
        let segmentSum = 0
        for (let j = 0; j < segmentSize; j++) {
          segmentSum += dataArray[i * segmentSize + j]
        }
        const segmentAvg = segmentSum / segmentSize / 255
        levels.push(Math.min(segmentAvg * 2, 1))
      }

      setVuLevels(levels)
      animationFrameRef.current = requestAnimationFrame(update)
    }

    animationFrameRef.current = requestAnimationFrame(update)
  }, [])

  // Record 5 seconds of audio
  const startRecording = useCallback(() => {
    if (!streamRef.current || recordingStatus === "recording") return

    // Clear previous recording
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl)
      setAudioUrl(null)
    }

    chunksRef.current = []
    setRecordingStatus("recording")
    setRecordingCountdown(5)

    const mediaRecorder = new MediaRecorder(streamRef.current)
    mediaRecorderRef.current = mediaRecorder

    mediaRecorder.ondataavailable = (event: BlobEvent) => {
      if (event.data.size > 0) {
        chunksRef.current.push(event.data)
      }
    }

    mediaRecorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "audio/webm" })
      const url = URL.createObjectURL(blob)
      setAudioUrl(url)
      setRecordingStatus("recorded")
    }

    mediaRecorder.start()

    // Countdown timer
    let remaining = 5
    const interval = setInterval(() => {
      remaining -= 1
      setRecordingCountdown(remaining)
      if (remaining <= 0) {
        clearInterval(interval)
        if (mediaRecorder.state === "recording") {
          mediaRecorder.stop()
        }
      }
    }, 1000)
  }, [recordingStatus, audioUrl])

  // Play recorded audio
  const playRecording = useCallback(() => {
    if (!audioUrl) return

    if (audioPlaybackRef.current) {
      audioPlaybackRef.current.pause()
      audioPlaybackRef.current = null
    }

    const audio = new Audio(audioUrl)
    audioPlaybackRef.current = audio
    setIsPlaying(true)

    audio.onended = () => {
      setIsPlaying(false)
    }

    audio.play()
  }, [audioUrl])

  // Handle device change
  const handleDeviceChange = useCallback(
    (deviceId: string) => {
      setSelectedDeviceId(deviceId)
      setMicConfirmed(false)
      requestMicPermission(deviceId)
    },
    [requestMicPermission]
  )

  // Request permission on mount
  useEffect(() => {
    requestMicPermission()

    return () => {
      // Cleanup on unmount
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
      if (audioPlaybackRef.current) {
        audioPlaybackRef.current.pause()
      }
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleContinue = () => {
    navigate("/exam")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl mb-4 shadow-md">
            <Mic className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">Test du microphone</h1>
          <p className="text-slate-600 mt-2 text-lg">
            Verifions que votre microphone fonctionne correctement
          </p>
        </div>

        {/* Mic Status Card */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-slate-200">
            <CardTitle className="text-slate-800 flex items-center gap-2 text-lg">
              {micStatus === "granted" ? (
                <Mic className="w-5 h-5 text-sky-600" />
              ) : (
                <MicOff className="w-5 h-5 text-slate-400" />
              )}
              Statut du microphone
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6 space-y-6">
            {/* Permission status */}
            <div className="flex items-center gap-3">
              {micStatus === "idle" && (
                <>
                  <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
                  <span className="text-slate-600">Initialisation...</span>
                </>
              )}
              {micStatus === "requesting" && (
                <>
                  <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
                  <span className="text-slate-600">
                    Demande d'autorisation du microphone...
                  </span>
                </>
              )}
              {micStatus === "granted" && (
                <>
                  <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                    <Check className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-green-700 font-medium">
                    Microphone autorise
                  </span>
                </>
              )}
              {micStatus === "denied" && (
                <>
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <div>
                    <span className="text-red-700 font-medium block">
                      Acces au microphone refuse
                    </span>
                    <span className="text-sm text-slate-500">
                      Veuillez autoriser l'acces au microphone dans les parametres de votre navigateur.
                    </span>
                  </div>
                </>
              )}
              {micStatus === "error" && (
                <>
                  <AlertCircle className="w-5 h-5 text-red-500" />
                  <div>
                    <span className="text-red-700 font-medium block">
                      Erreur lors de l'acces au microphone
                    </span>
                    <span className="text-sm text-slate-500">
                      Verifiez qu'un microphone est bien connecte a votre appareil.
                    </span>
                  </div>
                </>
              )}
            </div>

            {/* Device selector */}
            {micStatus === "granted" && devices.length > 0 && (
              <div className="space-y-2">
                <label
                  htmlFor="mic-select"
                  className="text-sm font-medium text-slate-700"
                >
                  Peripherique audio
                </label>
                <select
                  id="mic-select"
                  value={selectedDeviceId}
                  onChange={(e) => handleDeviceChange(e.target.value)}
                  className="w-full rounded-lg border-2 border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                >
                  {devices.map((device) => (
                    <option key={device.deviceId} value={device.deviceId}>
                      {device.label || `Microphone ${device.deviceId.slice(0, 8)}`}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Retry button for denied/error */}
            {(micStatus === "denied" || micStatus === "error") && (
              <Button
                onClick={() => requestMicPermission()}
                className="bg-gradient-to-r from-sky-500 to-blue-500 text-white hover:from-sky-600 hover:to-blue-600"
              >
                <Mic className="w-4 h-4 mr-2" />
                Reessayer
              </Button>
            )}
          </CardContent>
        </Card>

        {/* VU Meter Card */}
        {micStatus === "granted" && (
          <Card className="border-2 border-slate-200 shadow-sm">
            <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-slate-200">
              <CardTitle className="text-slate-800 flex items-center gap-2 text-lg">
                <Volume2 className="w-5 h-5 text-sky-600" />
                Niveau sonore
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <p className="text-sm text-slate-600 mb-4">
                Parlez dans votre microphone pour verifier le niveau sonore.
              </p>

              {/* VU Meter - 5 animated bars */}
              <div className="flex items-end justify-center gap-2 h-24 bg-slate-50 rounded-xl p-4 border border-slate-200">
                {vuLevels.map((level, index) => (
                  <div
                    key={index}
                    className="w-8 rounded-t-md transition-all duration-75"
                    style={{
                      height: `${Math.max(level * 100, 4)}%`,
                      backgroundColor:
                        level > 0.6
                          ? "#ef4444"
                          : level > 0.3
                          ? "#f59e0b"
                          : "#22c55e",
                      minHeight: "4px",
                    }}
                  />
                ))}
              </div>

              {/* Mic confirmed indicator */}
              <div className="mt-4 flex items-center gap-2">
                {micConfirmed ? (
                  <>
                    <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                      <Check className="w-4 h-4 text-white" />
                    </div>
                    <span className="text-green-700 font-medium text-sm">
                      Microphone detecte et fonctionnel
                    </span>
                  </>
                ) : (
                  <>
                    <div className="w-6 h-6 bg-slate-200 rounded-full flex items-center justify-center">
                      <Mic className="w-3 h-3 text-slate-400" />
                    </div>
                    <span className="text-slate-500 text-sm">
                      En attente de detection du son...
                    </span>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recording Test Card */}
        {micStatus === "granted" && (
          <Card className="border-2 border-slate-200 shadow-sm">
            <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-slate-200">
              <CardTitle className="text-slate-800 flex items-center gap-2 text-lg">
                <Mic className="w-5 h-5 text-sky-600" />
                Test d'enregistrement
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <p className="text-sm text-slate-600">
                Enregistrez un court extrait de 5 secondes puis ecoutez-le pour verifier la qualite.
              </p>

              <div className="flex flex-col sm:flex-row items-center gap-3">
                {/* Record button */}
                <Button
                  onClick={startRecording}
                  disabled={recordingStatus === "recording"}
                  className={cn(
                    "min-w-[180px]",
                    recordingStatus === "recording"
                      ? "bg-red-500 hover:bg-red-500 text-white"
                      : "bg-gradient-to-r from-sky-500 to-blue-500 text-white hover:from-sky-600 hover:to-blue-600"
                  )}
                >
                  {recordingStatus === "recording" ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Enregistrement... {recordingCountdown}s
                    </>
                  ) : (
                    <>
                      <Mic className="w-4 h-4 mr-2" />
                      Enregistrer 5s
                    </>
                  )}
                </Button>

                {/* Play button */}
                {recordingStatus === "recorded" && audioUrl && (
                  <Button
                    onClick={playRecording}
                    disabled={isPlaying}
                    variant="outline"
                    className="min-w-[140px] border-2 border-slate-300"
                  >
                    {isPlaying ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Lecture...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 mr-2" />
                        Ecouter
                      </>
                    )}
                  </Button>
                )}
              </div>

              {/* Recording indicator */}
              {recordingStatus === "recording" && (
                <div className="flex items-center gap-2 text-red-600 text-sm">
                  <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                  Enregistrement en cours... Parlez dans votre microphone.
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Continue button */}
        <div className="flex justify-center pt-6">
          <Button
            size="lg"
            onClick={handleContinue}
            disabled={micStatus !== "granted"}
            className="min-w-[250px] bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl transition-all text-base px-8 py-6 rounded-xl"
          >
            Continuer
            <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        </div>

        {/* Encouragement message when mic confirmed */}
        {micConfirmed && (
          <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200">
            <div className="p-4 text-center">
              <p className="text-sm text-slate-700">
                <strong className="text-green-700">Votre microphone fonctionne correctement.</strong>
                <span className="block mt-1 text-xs text-slate-600">
                  Vous pouvez continuer vers l'examen.
                </span>
              </p>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
