"use client"

import { useEffect, useState } from "react"

interface LinearProgressBarProps {
  estimatedSeconds: number
  onComplete?: () => void
}

export default function LinearProgressBar({ estimatedSeconds, onComplete }: LinearProgressBarProps) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    const startTime = Date.now()
    const interval = setInterval(() => {
      const elapsed = (Date.now() - startTime) / 1000
      setElapsedSeconds(elapsed)
    }, 100) // Update every 100ms for smooth animation

    return () => clearInterval(interval)
  }, [])

  // Calculate progress percentage, cap at 95% until actually complete
  const progress = Math.min((elapsedSeconds / estimatedSeconds) * 100, 95)

  return (
    <div className="w-full space-y-1">
      {/* Progress bar container */}
      <div className="w-full h-2 bg-secondary rounded-full overflow-hidden">
        {/* Progress fill - green from bottom to top */}
        <div
          className="h-full bg-green-500 transition-all duration-300 ease-out rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Time display */}
      <div className="text-xs text-muted-foreground text-center">
        {elapsedSeconds.toFixed(1)}s / ~{estimatedSeconds.toFixed(1)}s
      </div>
    </div>
  )
}
