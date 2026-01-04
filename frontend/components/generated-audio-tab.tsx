"use client"

import type React from "react"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { SkipBack, Play, Pause, SkipForward, Volume2, Download, Share2 } from "lucide-react"

interface GeneratedAudioTabProps {
  audioUrl: string | null
  generationTime: number | null
  compact?: boolean
}

export default function GeneratedAudioTab({ audioUrl, generationTime, compact = false }: GeneratedAudioTabProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState([1])
  const [playbackRate, setPlaybackRate] = useState(1)
  const audioRef = useRef<HTMLAudioElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const updateTime = () => setCurrentTime(audio.currentTime)
    const updateDuration = () => setDuration(audio.duration)
    const handleEnded = () => setIsPlaying(false)

    audio.addEventListener("timeupdate", updateTime)
    audio.addEventListener("loadedmetadata", updateDuration)
    audio.addEventListener("ended", handleEnded)

    return () => {
      audio.removeEventListener("timeupdate", updateTime)
      audio.removeEventListener("loadedmetadata", updateDuration)
      audio.removeEventListener("ended", handleEnded)
    }
  }, [audioUrl])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume[0]
    }
  }, [volume])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate
    }
  }, [playbackRate])

  useEffect(() => {
    drawWaveform()
  }, [audioUrl, isPlaying, currentTime])

  const drawWaveform = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const barCount = 100
    const barWidth = width / barCount
    const progress = duration > 0 ? currentTime / duration : 0

    ctx.clearRect(0, 0, width, height)

    for (let i = 0; i < barCount; i++) {
      const barHeight = Math.random() * height * 0.8 + height * 0.1
      const x = i * barWidth
      const y = (height - barHeight) / 2

      if (i / barCount < progress) {
        ctx.fillStyle = "hsl(270, 60%, 55%)"
      } else {
        ctx.fillStyle = "hsl(0, 0%, 85%)"
      }

      ctx.fillRect(x, y, barWidth * 0.6, barHeight)
    }

    if (isPlaying) {
      animationRef.current = requestAnimationFrame(drawWaveform)
    }
  }

  const togglePlay = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
    setIsPlaying(!isPlaying)
  }

  const skipBackward = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(0, currentTime - 5)
    }
  }

  const skipForward = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.min(duration, currentTime + 5)
    }
  }

  const cyclePlaybackRate = () => {
    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2]
    const currentIndex = rates.indexOf(playbackRate)
    const nextIndex = (currentIndex + 1) % rates.length
    setPlaybackRate(rates[nextIndex])
  }

  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  if (!audioUrl) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        <p>No audio generated yet. Enter text and click "Generate Speech".</p>
      </div>
    )
  }

  if (compact) {
    return (
      <div className="space-y-4">
        <canvas ref={canvasRef} width={800} height={100} className="w-full h-20 rounded" />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{formatTime(currentTime)}</span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay}>
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
          </div>
          <span className="text-xs text-muted-foreground">{formatTime(duration)}</span>
        </div>
        <audio ref={audioRef} src={audioUrl} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <canvas ref={canvasRef} width={1200} height={120} className="w-full h-32 rounded-lg" />

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        <div className="flex items-center justify-center gap-2">
          <Button variant="ghost" size="icon" className="h-10 w-10" onClick={() => setVolume([volume[0] > 0 ? 0 : 1])}>
            <Volume2 className="h-5 w-5" />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={cyclePlaybackRate}
            className="h-8 px-3 text-xs font-medium bg-transparent"
          >
            {playbackRate}x
          </Button>

          <div className="flex items-center gap-1 mx-4">
            <Button variant="ghost" size="icon" className="h-10 w-10" onClick={skipBackward}>
              <SkipBack className="h-5 w-5" />
            </Button>

            <Button size="icon" className="h-12 w-12" onClick={togglePlay}>
              {isPlaying ? <Pause className="h-6 w-6" /> : <Play className="h-6 w-6" />}
            </Button>

            <Button variant="ghost" size="icon" className="h-10 w-10" onClick={skipForward}>
              <SkipForward className="h-5 w-5" />
            </Button>
          </div>

          <Button variant="ghost" size="icon" className="h-10 w-10">
            <Download className="h-5 w-5" />
          </Button>

          <Button variant="ghost" size="icon" className="h-10 w-10">
            <Share2 className="h-5 w-5" />
          </Button>
        </div>
      </div>

      {generationTime && (
        <div className="space-y-2">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded inline-block">Status</Label>
          <p className="text-sm text-muted-foreground">Generated in {generationTime.toFixed(2)} seconds</p>
        </div>
      )}

      <audio ref={audioRef} src={audioUrl} />
    </div>
  )
}

function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return <label className={className}>{children}</label>
}
