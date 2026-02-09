import { useMemo } from "react"
import { cn } from "@/lib/utils"
import { Clock, MessageSquare, Award } from "lucide-react"

type TimerPhase = "consignes" | "monologue" | "debat" | "feedback"

interface ExamTimerProps {
  phase: TimerPhase
  elapsedSeconds: number
  maxSeconds?: number
}

const RADIUS = 45
const STROKE_WIDTH = 6
const CIRCUMFERENCE = 2 * Math.PI * RADIUS
const VIEW_SIZE = (RADIUS + STROKE_WIDTH) * 2

/** Threshold in seconds for yellow warning during monologue (8 min). */
const WARNING_THRESHOLD = 480
/** Threshold in seconds for red danger during monologue (10 min). */
const DANGER_THRESHOLD = 600

function formatDigitalTime(totalSeconds: number): string {
  const negative = totalSeconds < 0
  const abs = Math.abs(totalSeconds)
  const mins = Math.floor(abs / 60)
  const secs = abs % 60
  const prefix = negative ? "-" : ""
  return `${prefix}${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
}

export default function ExamTimer({
  phase,
  elapsedSeconds,
  maxSeconds = 600,
}: ExamTimerProps) {
  const remaining = maxSeconds - elapsedSeconds

  // Compute progress ratio (0 to 1) for ring fill
  const progress = useMemo(() => {
    if (phase === "consignes" || phase === "feedback") return 0
    return Math.min(Math.max(elapsedSeconds / maxSeconds, 0), 1)
  }, [phase, elapsedSeconds, maxSeconds])

  // Stroke dash offset: full circumference = empty ring, 0 = full ring
  const strokeDashoffset = CIRCUMFERENCE * (1 - progress)

  // Determine colors based on phase and elapsed time
  const { strokeColor, textColor, bgClass, labelText } = useMemo(() => {
    switch (phase) {
      case "consignes":
        return {
          strokeColor: "#ADD8E6",
          textColor: "text-blue-700",
          bgClass: "bg-blue-50/80",
          labelText: "Consignes...",
        }
      case "monologue": {
        if (elapsedSeconds >= DANGER_THRESHOLD) {
          return {
            strokeColor: "#ef4444",
            textColor: "text-red-600",
            bgClass: "bg-red-50/80",
            labelText: formatDigitalTime(remaining),
          }
        }
        if (elapsedSeconds >= WARNING_THRESHOLD) {
          return {
            strokeColor: "#eab308",
            textColor: "text-yellow-700",
            bgClass: "bg-yellow-50/80",
            labelText: formatDigitalTime(remaining),
          }
        }
        return {
          strokeColor: "#22c55e",
          textColor: "text-green-700",
          bgClass: "bg-green-50/80",
          labelText: formatDigitalTime(remaining),
        }
      }
      case "debat":
        return {
          strokeColor: "#9C27B0",
          textColor: "text-purple-700",
          bgClass: "bg-purple-50/80",
          labelText: formatDigitalTime(remaining),
        }
      case "feedback":
        return {
          strokeColor: "#e2e8f0",
          textColor: "text-slate-600",
          bgClass: "bg-white/80",
          labelText: "Feedback",
        }
      default:
        return {
          strokeColor: "#94a3b8",
          textColor: "text-slate-600",
          bgClass: "bg-slate-50/80",
          labelText: "--:--",
        }
    }
  }, [phase, elapsedSeconds, remaining])

  // Icon for center area
  const PhaseIcon = useMemo(() => {
    switch (phase) {
      case "consignes":
        return Clock
      case "debat":
        return MessageSquare
      case "feedback":
        return Award
      default:
        return null
    }
  }, [phase])

  return (
    <div
      className={cn(
        "relative inline-flex flex-col items-center justify-center rounded-full p-1",
        bgClass,
        phase === "consignes" && "animate-pulse-ring"
      )}
    >
      <svg
        width={VIEW_SIZE}
        height={VIEW_SIZE}
        viewBox={`0 0 ${VIEW_SIZE} ${VIEW_SIZE}`}
        className="transform -rotate-90"
      >
        {/* Background track */}
        <circle
          cx={VIEW_SIZE / 2}
          cy={VIEW_SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={STROKE_WIDTH}
        />
        {/* Progress arc */}
        {phase !== "feedback" && (
          <circle
            cx={VIEW_SIZE / 2}
            cy={VIEW_SIZE / 2}
            r={RADIUS}
            fill="none"
            stroke={strokeColor}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-linear"
          />
        )}
      </svg>

      {/* Center content overlay */}
      <div
        className={cn(
          "absolute inset-0 flex flex-col items-center justify-center",
          textColor
        )}
      >
        {PhaseIcon && <PhaseIcon className="w-4 h-4 mb-0.5 opacity-60" />}
        <span
          className={cn(
            "font-mono font-bold leading-none",
            phase === "consignes" || phase === "feedback"
              ? "text-[10px]"
              : "text-sm"
          )}
        >
          {labelText}
        </span>
      </div>

      {/* Debat: horizontal progress bar beneath the circle */}
      {phase === "debat" && (
        <div className="w-full mt-1 h-1.5 rounded-full bg-purple-200 overflow-hidden">
          <div
            className="h-full rounded-full bg-purple-600 transition-all duration-1000 ease-linear"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      )}
    </div>
  )
}
