import { cn } from "@/lib/utils"
import { Headphones, Volume2, Loader2 } from "lucide-react"

type AgentState = "listening" | "speaking" | "thinking" | "connecting"

interface AgentStateIndicatorProps {
  state: AgentState
  agentName: string
}

function WaveformBars() {
  return (
    <div className="flex items-end gap-[2px] h-4">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="w-[3px] rounded-full bg-green-500 animate-wave"
          style={{
            height: "100%",
            animationDelay: `${i * 0.12}s`,
            animationDuration: `${0.6 + i * 0.08}s`,
          }}
        />
      ))}
    </div>
  )
}

const STATE_CONFIG: Record<
  AgentState,
  {
    label: string
    dotClass: string
    borderClass: string
    bgClass: string
    textClass: string
  }
> = {
  listening: {
    label: "L'examinateur vous écoute",
    dotClass: "bg-blue-500 animate-pulse",
    borderClass: "border-blue-200",
    bgClass: "bg-blue-50/90",
    textClass: "text-blue-700",
  },
  speaking: {
    label: "L'examinateur parle",
    dotClass: "bg-green-500",
    borderClass: "border-green-200",
    bgClass: "bg-green-50/90",
    textClass: "text-green-700",
  },
  thinking: {
    label: "L'examinateur réfléchit…",
    dotClass: "bg-yellow-500 animate-pulse",
    borderClass: "border-yellow-200",
    bgClass: "bg-yellow-50/90",
    textClass: "text-yellow-700",
  },
  connecting: {
    label: "Connexion en cours...",
    dotClass: "",
    borderClass: "border-slate-200",
    bgClass: "bg-slate-50/90",
    textClass: "text-slate-600",
  },
}

export default function AgentStateIndicator({
  state,
  agentName,
}: AgentStateIndicatorProps) {
  const config = STATE_CONFIG[state]

  return (
    <div
      className={cn(
        "inline-flex items-center gap-3 px-4 py-2.5 rounded-xl border backdrop-blur-sm shadow-sm transition-all duration-300",
        config.borderClass,
        config.bgClass
      )}
    >
      {/* Status dot or spinner */}
      {state === "connecting" ? (
        <Loader2 className={cn("w-4 h-4 animate-spin", config.textClass)} />
      ) : (
        <span className={cn("w-2.5 h-2.5 rounded-full shrink-0", config.dotClass)} />
      )}

      {/* Icon */}
      {state === "listening" && (
        <Headphones className={cn("w-4 h-4", config.textClass)} />
      )}
      {state === "speaking" && (
        <div className="flex items-center gap-1.5">
          <Volume2 className={cn("w-4 h-4", config.textClass)} />
          <WaveformBars />
        </div>
      )}

      {/* Label */}
      <div className="flex flex-col">
        <span className={cn("text-sm font-medium leading-tight", config.textClass)}>
          {config.label}
        </span>
        <span className="text-[10px] text-slate-400 leading-tight">{agentName}</span>
      </div>
    </div>
  )
}
