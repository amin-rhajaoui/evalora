import { useState, useEffect, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Wifi,
  Mic,
  Globe,
  ArrowRight,
} from "lucide-react"

type CheckStatus = "pending" | "running" | "success" | "failure"

interface SystemCheckItem {
  id: string
  name: string
  description: string
  status: CheckStatus
  icon: React.ReactNode
  critical: boolean
  errorMessage?: string
}

const INITIAL_CHECKS: SystemCheckItem[] = [
  {
    id: "webrtc",
    name: "Support WebRTC",
    description: "Verification de la compatibilite du navigateur avec les communications en temps reel.",
    status: "pending",
    icon: <Globe className="w-5 h-5" />,
    critical: true,
  },
  {
    id: "mic",
    name: "Acces au microphone",
    description: "Verification de l'autorisation d'acces au microphone.",
    status: "pending",
    icon: <Mic className="w-5 h-5" />,
    critical: true,
  },
  {
    id: "backend",
    name: "Connectivite serveur",
    description: "Verification de la connexion au serveur backend.",
    status: "pending",
    icon: <Wifi className="w-5 h-5" />,
    critical: false,
  },
  {
    id: "livekit",
    name: "Service LiveKit",
    description: "Verification de la disponibilite du service de communication vocale.",
    status: "pending",
    icon: <Wifi className="w-5 h-5" />,
    critical: false,
  },
]

export default function SystemCheck() {
  const navigate = useNavigate()
  const [checks, setChecks] = useState<SystemCheckItem[]>(INITIAL_CHECKS)
  const [allDone, setAllDone] = useState(false)

  const updateCheck = useCallback(
    (id: string, update: Partial<SystemCheckItem>) => {
      setChecks((prev) =>
        prev.map((check) =>
          check.id === id ? { ...check, ...update } : check
        )
      )
    },
    []
  )

  // Check WebRTC support
  const checkWebRTC = useCallback(async (): Promise<boolean> => {
    updateCheck("webrtc", { status: "running" })

    try {
      if (
        typeof RTCPeerConnection !== "undefined" &&
        typeof navigator.mediaDevices !== "undefined" &&
        typeof navigator.mediaDevices.getUserMedia === "function"
      ) {
        updateCheck("webrtc", { status: "success" })
        return true
      } else {
        updateCheck("webrtc", {
          status: "failure",
          errorMessage: "Votre navigateur ne supporte pas WebRTC. Utilisez Chrome, Firefox ou Edge.",
        })
        return false
      }
    } catch {
      updateCheck("webrtc", {
        status: "failure",
        errorMessage: "Impossible de verifier le support WebRTC.",
      })
      return false
    }
  }, [updateCheck])

  // Check microphone permissions
  const checkMic = useCallback(async (): Promise<boolean> => {
    updateCheck("mic", { status: "running" })

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      // Stop the stream immediately, we just need to check permission
      stream.getTracks().forEach((track) => track.stop())
      updateCheck("mic", { status: "success" })
      return true
    } catch (err) {
      const error = err as DOMException
      const message =
        error.name === "NotAllowedError" || error.name === "PermissionDeniedError"
          ? "L'acces au microphone a ete refuse. Veuillez l'autoriser dans les parametres du navigateur."
          : "Aucun microphone detecte ou erreur d'acces."
      updateCheck("mic", {
        status: "failure",
        errorMessage: message,
      })
      return false
    }
  }, [updateCheck])

  // Check backend connectivity
  const checkBackend = useCallback(async (): Promise<boolean> => {
    updateCheck("backend", { status: "running" })

    try {
      const response = await fetch("/health", { method: "GET" })
      if (response.ok) {
        updateCheck("backend", { status: "success" })
        return true
      } else {
        updateCheck("backend", {
          status: "failure",
          errorMessage: `Le serveur a repondu avec le code ${response.status}.`,
        })
        return false
      }
    } catch {
      updateCheck("backend", {
        status: "failure",
        errorMessage: "Impossible de contacter le serveur. Verifiez votre connexion.",
      })
      return false
    }
  }, [updateCheck])

  // Check LiveKit status
  const checkLiveKit = useCallback(async (): Promise<boolean> => {
    updateCheck("livekit", { status: "running" })

    try {
      const response = await fetch("/api/livekit/status", { method: "GET" })
      if (response.ok) {
        const data = await response.json()
        if (data.configured) {
          updateCheck("livekit", { status: "success" })
          return true
        } else {
          updateCheck("livekit", {
            status: "failure",
            errorMessage: "Le service LiveKit n'est pas configure sur le serveur.",
          })
          return false
        }
      } else {
        updateCheck("livekit", {
          status: "failure",
          errorMessage: `Le service LiveKit a repondu avec le code ${response.status}.`,
        })
        return false
      }
    } catch {
      updateCheck("livekit", {
        status: "failure",
        errorMessage: "Impossible de contacter le service LiveKit.",
      })
      return false
    }
  }, [updateCheck])

  // Run all checks sequentially
  useEffect(() => {
    let cancelled = false

    const runChecks = async () => {
      if (cancelled) return
      await checkWebRTC()

      if (cancelled) return
      await checkMic()

      if (cancelled) return
      await checkBackend()

      if (cancelled) return
      await checkLiveKit()

      if (!cancelled) {
        setAllDone(true)
      }
    }

    runChecks()

    return () => {
      cancelled = true
    }
  }, [checkWebRTC, checkMic, checkBackend, checkLiveKit])

  // Determine if critical checks have failed
  const hasCriticalFailure = checks.some(
    (check) => check.critical && check.status === "failure"
  )

  const successCount = checks.filter((c) => c.status === "success").length
  const totalCount = checks.length

  const handleContinue = () => {
    navigate("/mic-test")
  }

  const getStatusIcon = (status: CheckStatus) => {
    switch (status) {
      case "pending":
        return (
          <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-slate-300" />
          </div>
        )
      case "running":
        return (
          <div className="w-8 h-8 rounded-full bg-sky-100 flex items-center justify-center">
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin" />
          </div>
        )
      case "success":
        return (
          <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5 text-green-600" />
          </div>
        )
      case "failure":
        return (
          <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
            <XCircle className="w-5 h-5 text-red-500" />
          </div>
        )
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-sky-50 via-blue-50 to-indigo-50 py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl mb-4 shadow-md">
            <Globe className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            Verification du systeme
          </h1>
          <p className="text-slate-600 mt-2 text-lg">
            Nous verifions que tout est pret pour votre session
          </p>
        </div>

        {/* Progress indicator */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700">
                Progression des verifications
              </span>
              <span className="text-sm text-slate-500">
                {successCount}/{totalCount}
              </span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  hasCriticalFailure
                    ? "bg-red-400"
                    : "bg-gradient-to-r from-sky-400 to-blue-500"
                )}
                style={{
                  width: `${allDone ? 100 : (checks.filter((c) => c.status === "success" || c.status === "failure").length / totalCount) * 100}%`,
                }}
              />
            </div>
          </CardContent>
        </Card>

        {/* Checks list */}
        <Card className="border-2 border-slate-200 shadow-sm">
          <CardHeader className="bg-gradient-to-r from-sky-50 to-blue-50 border-b border-slate-200">
            <CardTitle className="text-slate-800 flex items-center gap-2 text-lg">
              <Wifi className="w-5 h-5 text-sky-600" />
              Verifications systeme
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {checks.map((check) => (
                <div
                  key={check.id}
                  className={cn(
                    "flex items-start gap-4 p-4 rounded-xl border-2 transition-all",
                    check.status === "success" && "border-green-200 bg-green-50/50",
                    check.status === "failure" && "border-red-200 bg-red-50/50",
                    check.status === "running" && "border-sky-200 bg-sky-50/50",
                    check.status === "pending" && "border-slate-200 bg-slate-50/50"
                  )}
                >
                  {/* Status icon */}
                  <div className="shrink-0 mt-0.5">{getStatusIcon(check.status)}</div>

                  {/* Check details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">{check.icon}</span>
                      <h3 className="font-semibold text-slate-800">{check.name}</h3>
                      {check.critical && (
                        <span className="text-xs font-medium text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                          Requis
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mt-1">
                      {check.description}
                    </p>
                    {check.status === "failure" && check.errorMessage && (
                      <p className="text-sm text-red-600 mt-2 font-medium">
                        {check.errorMessage}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Result summary */}
        {allDone && (
          <Card
            className={cn(
              "border-2",
              hasCriticalFailure
                ? "bg-gradient-to-r from-red-50 to-orange-50 border-red-200"
                : "bg-gradient-to-r from-green-50 to-emerald-50 border-green-200"
            )}
          >
            <div className="p-4 text-center">
              {hasCriticalFailure ? (
                <p className="text-sm text-slate-700">
                  <strong className="text-red-700">
                    Certaines verifications requises ont echoue.
                  </strong>
                  <span className="block mt-1 text-xs text-slate-600">
                    Veuillez corriger les problemes ci-dessus avant de continuer.
                  </span>
                </p>
              ) : (
                <p className="text-sm text-slate-700">
                  <strong className="text-green-700">
                    Toutes les verifications sont terminees.
                  </strong>
                  <span className="block mt-1 text-xs text-slate-600">
                    Votre systeme est pret. Vous pouvez continuer.
                  </span>
                </p>
              )}
            </div>
          </Card>
        )}

        {/* Continue button */}
        <div className="flex justify-center pt-6">
          <Button
            size="lg"
            onClick={handleContinue}
            disabled={!allDone || hasCriticalFailure}
            className="min-w-[250px] bg-gradient-to-r from-sky-500 to-blue-500 hover:from-sky-600 hover:to-blue-600 text-white shadow-lg hover:shadow-xl transition-all text-base px-8 py-6 rounded-xl"
          >
            {!allDone ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Verification en cours...
              </>
            ) : (
              <>
                Continuer
                <ArrowRight className="w-5 h-5 ml-2" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
