import { useEffect, useRef } from "react"
import { cn } from "@/lib/utils"
import { BookOpen, Mic, MessageSquare, Award } from "lucide-react"

interface PhaseTransitionProps {
  phase: string
  isVisible: boolean
  onComplete: () => void
}

interface PhaseConfig {
  label: string
  instruction: string
  bgClass: string
  textClass: string
  icon: React.ElementType
}

const PHASE_CONFIGS: Record<string, PhaseConfig> = {
  consignes: {
    label: "CONSIGNES",
    instruction: "Ecoutez attentivement les instructions de l'examinateur.",
    bgClass: "bg-blue-600/95",
    textClass: "text-white",
    icon: BookOpen,
  },
  monologue: {
    label: "MONOLOGUE",
    instruction: "Presentez votre point de vue sur le document.",
    bgClass: "bg-green-600/95",
    textClass: "text-white",
    icon: Mic,
  },
  debat: {
    label: "DEBAT",
    instruction: "Echangez avec l'examinateur et defendez votre position.",
    bgClass: "bg-purple-700/95",
    textClass: "text-white",
    icon: MessageSquare,
  },
  feedback: {
    label: "FEEDBACK",
    instruction: "L'examinateur va vous donner un retour sur votre prestation.",
    bgClass: "bg-gradient-to-br from-slate-50 to-amber-50/95",
    textClass: "text-slate-800",
    icon: Award,
  },
}

const FALLBACK_CONFIG: PhaseConfig = {
  label: "TRANSITION",
  instruction: "Veuillez patienter...",
  bgClass: "bg-slate-700/95",
  textClass: "text-white",
  icon: BookOpen,
}

/** Auto-hide duration in milliseconds. */
const AUTO_HIDE_MS = 2000

export default function PhaseTransition({
  phase,
  isVisible,
  onComplete,
}: PhaseTransitionProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  useEffect(() => {
    if (isVisible) {
      timerRef.current = setTimeout(() => {
        onCompleteRef.current()
      }, AUTO_HIDE_MS)
    }

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }
  }, [isVisible])

  const config = PHASE_CONFIGS[phase] ?? FALLBACK_CONFIG
  const Icon = config.icon

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex flex-col items-center justify-center transition-opacity duration-500",
        config.bgClass,
        isVisible
          ? "opacity-100 pointer-events-auto"
          : "opacity-0 pointer-events-none"
      )}
      aria-hidden={!isVisible}
    >
      {/* Icon */}
      <div
        className={cn(
          "mb-6 p-5 rounded-full",
          phase === "feedback"
            ? "bg-amber-100/80"
            : "bg-white/15"
        )}
      >
        <Icon
          className={cn(
            "w-12 h-12",
            phase === "feedback" ? "text-amber-600" : "text-white"
          )}
        />
      </div>

      {/* Phase name */}
      <h1
        className={cn(
          "text-4xl sm:text-5xl font-extrabold tracking-widest mb-4",
          config.textClass
        )}
      >
        {config.label}
      </h1>

      {/* Divider line */}
      <div
        className={cn(
          "w-24 h-1 rounded-full mb-6",
          phase === "feedback" ? "bg-amber-400" : "bg-white/40"
        )}
      />

      {/* Instruction text */}
      <p
        className={cn(
          "text-lg sm:text-xl text-center max-w-md px-6 font-medium",
          phase === "feedback" ? "text-slate-600" : "text-white/80"
        )}
      >
        {config.instruction}
      </p>
    </div>
  )
}
