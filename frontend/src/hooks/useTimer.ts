import { useState, useEffect, useCallback, useRef } from 'react';
import { ExamPhase, TIMER_PHASES } from '../types';

interface UseTimerOptions {
  onWarning?: () => void;
  onEnd?: () => void;
  warningSound?: boolean;
}

interface UseTimerReturn {
  elapsedTime: number;
  isRunning: boolean;
  phase: ExamPhase;
  isWarning: boolean;
  isEnded: boolean;
  start: () => void;
  pause: () => void;
  reset: () => void;
  setPhase: (phase: ExamPhase) => void;
}

export function useTimer(
  initialPhase: ExamPhase = 'consignes',
  options: UseTimerOptions = {}
): UseTimerReturn {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [phase, setPhase] = useState<ExamPhase>(initialPhase);
  const [isWarning, setIsWarning] = useState(false);
  const [isEnded, setIsEnded] = useState(false);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const warningTriggeredRef = useRef(false);
  const endTriggeredRef = useRef(false);

  const phaseConfig = TIMER_PHASES[phase];

  // Timer tick
  useEffect(() => {
    if (isRunning) {
      intervalRef.current = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isRunning]);

  // Check warnings and end
  useEffect(() => {
    if (!phaseConfig.duration) return;

    // Warning check
    if (
      phaseConfig.warning_at &&
      elapsedTime >= phaseConfig.warning_at &&
      !warningTriggeredRef.current
    ) {
      setIsWarning(true);
      warningTriggeredRef.current = true;
      options.onWarning?.();

      // Play warning sound
      if (options.warningSound) {
        playSound('warning');
      }
    }

    // End check
    if (
      elapsedTime >= phaseConfig.duration &&
      !endTriggeredRef.current
    ) {
      setIsEnded(true);
      endTriggeredRef.current = true;
      options.onEnd?.();

      // Play end sound
      if (options.warningSound) {
        playSound('end');
      }
    }
  }, [elapsedTime, phaseConfig, options]);

  const start = useCallback(() => {
    setIsRunning(true);
  }, []);

  const pause = useCallback(() => {
    setIsRunning(false);
  }, []);

  const reset = useCallback(() => {
    setElapsedTime(0);
    setIsRunning(false);
    setIsWarning(false);
    setIsEnded(false);
    warningTriggeredRef.current = false;
    endTriggeredRef.current = false;
  }, []);

  const changePhase = useCallback((newPhase: ExamPhase) => {
    reset();
    setPhase(newPhase);
  }, [reset]);

  return {
    elapsedTime,
    isRunning,
    phase,
    isWarning,
    isEnded,
    start,
    pause,
    reset,
    setPhase: changePhase,
  };
}

// Simple beep sound using Web Audio API
function playSound(type: 'warning' | 'end') {
  try {
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = type === 'warning' ? 440 : 880;
    oscillator.type = 'sine';
    gainNode.gain.value = 0.1;

    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.2);
  } catch {
    // Sound playback failed - silently ignore
  }
}

export default useTimer;
