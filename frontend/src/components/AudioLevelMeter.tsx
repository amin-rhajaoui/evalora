import { useEffect, useRef, useState, useCallback } from "react"
import { cn } from "@/lib/utils"
import { Mic, AlertTriangle } from "lucide-react"

interface AudioLevelMeterProps {
  stream: MediaStream | null
  className?: string
}

const BAR_COUNT = 7
/** Consecutive seconds of low audio before showing a warning. */
const LOW_LEVEL_WARNING_DELAY = 5
/** RMS threshold below which audio is considered "too quiet". */
const LOW_THRESHOLD = 0.02
/** RMS threshold above which audio is considered "too loud". */
const HIGH_THRESHOLD = 0.85

export default function AudioLevelMeter({ stream, className }: AudioLevelMeterProps) {
  const [levels, setLevels] = useState<number[]>(new Array(BAR_COUNT).fill(0))
  const [showLowWarning, setShowLowWarning] = useState(false)
  const [isLoud, setIsLoud] = useState(false)

  const audioCtxRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const animFrameRef = useRef<number>(0)
  const lowLevelStartRef = useRef<number | null>(null)

  const cleanup = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current)
      animFrameRef.current = 0
    }
    if (sourceRef.current) {
      sourceRef.current.disconnect()
      sourceRef.current = null
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close()
      audioCtxRef.current = null
    }
    analyserRef.current = null
    lowLevelStartRef.current = null
    setLevels(new Array(BAR_COUNT).fill(0))
    setShowLowWarning(false)
    setIsLoud(false)
  }, [])

  useEffect(() => {
    if (!stream) {
      cleanup()
      return
    }

    const audioCtx = new AudioContext()
    audioCtxRef.current = audioCtx

    const analyser = audioCtx.createAnalyser()
    analyser.fftSize = 256
    analyser.smoothingTimeConstant = 0.6
    analyserRef.current = analyser

    const source = audioCtx.createMediaStreamSource(stream)
    source.connect(analyser)
    sourceRef.current = source

    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const tick = () => {
      if (!analyserRef.current) return

      analyserRef.current.getByteFrequencyData(dataArray)

      // Compute RMS-like level from frequency data
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        const normalized = dataArray[i] / 255
        sum += normalized * normalized
      }
      const rms = Math.sqrt(sum / dataArray.length)

      // Distribute across bars with slight frequency weighting
      const newLevels: number[] = []
      const binSize = Math.floor(dataArray.length / BAR_COUNT)
      for (let b = 0; b < BAR_COUNT; b++) {
        let barSum = 0
        const start = b * binSize
        for (let i = start; i < start + binSize && i < dataArray.length; i++) {
          barSum += dataArray[i] / 255
        }
        newLevels.push(Math.min(barSum / binSize, 1))
      }
      setLevels(newLevels)

      // Loud detection
      setIsLoud(rms > HIGH_THRESHOLD)

      // Low-level duration tracking
      if (rms < LOW_THRESHOLD) {
        if (lowLevelStartRef.current === null) {
          lowLevelStartRef.current = Date.now()
        } else {
          const elapsed = (Date.now() - lowLevelStartRef.current) / 1000
          setShowLowWarning(elapsed >= LOW_LEVEL_WARNING_DELAY)
        }
      } else {
        lowLevelStartRef.current = null
        setShowLowWarning(false)
      }

      animFrameRef.current = requestAnimationFrame(tick)
    }

    animFrameRef.current = requestAnimationFrame(tick)

    return cleanup
  }, [stream, cleanup])

  return (
    <div className={cn("flex flex-col items-center gap-1.5", className)}>
      {/* Bars */}
      <div className="flex items-end gap-[3px] h-8">
        {levels.map((level, i) => {
          // Determine bar color
          let barColor = "bg-green-500"
          if (isLoud) {
            barColor = "bg-orange-500"
          } else if (level < 0.05) {
            barColor = "bg-slate-300"
          }

          return (
            <div
              key={i}
              className={cn(
                "w-[5px] rounded-full transition-all duration-75",
                barColor
              )}
              style={{
                height: `${Math.max(level * 100, 8)}%`,
              }}
            />
          )
        })}
        <Mic
          className={cn(
            "w-3.5 h-3.5 ml-1",
            isLoud ? "text-orange-500" : "text-slate-400"
          )}
        />
      </div>

      {/* Low-level warning */}
      {showLowWarning && (
        <div className="flex items-center gap-1 text-[10px] text-amber-600 font-medium animate-pulse">
          <AlertTriangle className="w-3 h-3" />
          <span>Volume trop faible</span>
        </div>
      )}
    </div>
  )
}
