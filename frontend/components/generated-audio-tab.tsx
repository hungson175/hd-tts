"use client"

import type React from "react"
import { useEffect, useRef, useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { SkipBack, Play, Pause, SkipForward, Volume2, Download, Share2 } from "lucide-react"
import { useWavesurfer } from "@wavesurfer/react"

// lamejs will be loaded via script tag on first use
declare global {
  interface Window {
    lamejs: {
      Mp3Encoder: new (channels: number, sampleRate: number, kbps: number) => {
        encodeBuffer: (left: Int16Array) => Int8Array
        flush: () => Int8Array
      }
    }
  }
}

const loadLamejs = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.lamejs) {
      resolve()
      return
    }

    const script = document.createElement('script')
    script.src = 'https://cdn.jsdelivr.net/npm/lamejs@1.2.1/lame.min.js'
    script.onload = () => {
      console.log('[MP3] lamejs loaded from CDN')
      resolve()
    }
    script.onerror = () => reject(new Error('Failed to load lamejs from CDN'))
    document.head.appendChild(script)
  })
}

interface GeneratedAudioTabProps {
  audioUrl: string | null
  generationTime: number | null
  compact?: boolean
}

export default function GeneratedAudioTab({ audioUrl, generationTime, compact = false }: GeneratedAudioTabProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [playbackRate, setPlaybackRate] = useState(1)

  const { wavesurfer, isPlaying, currentTime } = useWavesurfer({
    container: containerRef,
    url: audioUrl || undefined,
    waveColor: 'hsl(0, 0%, 75%)',
    progressColor: 'hsl(270, 60%, 55%)',
    cursorColor: 'hsl(270, 60%, 45%)',
    barWidth: 3,
    barGap: 2,
    barRadius: 2,
    height: compact ? 80 : 120,
  })

  const duration = wavesurfer?.getDuration() || 0

  // Update playback rate when changed
  useEffect(() => {
    if (wavesurfer) {
      wavesurfer.setPlaybackRate(playbackRate)
    }
  }, [wavesurfer, playbackRate])

  const togglePlay = useCallback(() => {
    if (wavesurfer) {
      wavesurfer.playPause()
    }
  }, [wavesurfer])

  const skipBackward = useCallback(() => {
    if (wavesurfer) {
      const newTime = Math.max(0, wavesurfer.getCurrentTime() - 5)
      wavesurfer.seekTo(newTime / wavesurfer.getDuration())
    }
  }, [wavesurfer])

  const skipForward = useCallback(() => {
    if (wavesurfer) {
      const newTime = Math.min(wavesurfer.getDuration(), wavesurfer.getCurrentTime() + 5)
      wavesurfer.seekTo(newTime / wavesurfer.getDuration())
    }
  }, [wavesurfer])

  const toggleMute = useCallback(() => {
    if (wavesurfer) {
      wavesurfer.setMuted(!wavesurfer.getMuted())
    }
  }, [wavesurfer])

  const cyclePlaybackRate = () => {
    const rates = [0.5, 0.75, 1, 1.25, 1.5, 2]
    const currentIndex = rates.indexOf(playbackRate)
    const nextIndex = (currentIndex + 1) % rates.length
    setPlaybackRate(rates[nextIndex])
  }

  const formatTime = (time: number) => {
    if (!isFinite(time)) return "0:00"
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes}:${seconds.toString().padStart(2, "0")}`
  }

  const handleDownload = async () => {
    if (!audioUrl) return

    try {
      // Decode WAV data URL to audio buffer
      const response = await fetch(audioUrl)
      const arrayBuffer = await response.arrayBuffer()

      // Parse WAV header to get audio data
      const dataView = new DataView(arrayBuffer)
      const numChannels = dataView.getUint16(22, true)
      const sampleRate = dataView.getUint32(24, true)

      // Find data chunk
      let dataOffset = 44 // Standard WAV header size
      const dataLength = (arrayBuffer.byteLength - dataOffset)
      const samples = new Int16Array(arrayBuffer, dataOffset, dataLength / 2)

      // Convert to mono if stereo
      let monoSamples: Int16Array
      if (numChannels === 2) {
        monoSamples = new Int16Array(samples.length / 2)
        for (let i = 0; i < monoSamples.length; i++) {
          monoSamples[i] = Math.round((samples[i * 2] + samples[i * 2 + 1]) / 2)
        }
      } else {
        monoSamples = samples
      }

      // Load lamejs from CDN if not already loaded
      console.log('[MP3] Starting conversion, sampleRate:', sampleRate, 'samples:', monoSamples.length)
      await loadLamejs()

      if (!window.lamejs?.Mp3Encoder) {
        throw new Error('Mp3Encoder not available after loading lamejs')
      }

      const mp3Encoder = new window.lamejs.Mp3Encoder(1, sampleRate, 128) // mono, sampleRate, 128kbps
      const mp3Data: Uint8Array[] = []

      // Process in chunks
      const sampleBlockSize = 1152
      for (let i = 0; i < monoSamples.length; i += sampleBlockSize) {
        const chunk = monoSamples.subarray(i, i + sampleBlockSize)
        const mp3buf = mp3Encoder.encodeBuffer(chunk)
        if (mp3buf.length > 0) {
          mp3Data.push(new Uint8Array(mp3buf))
        }
      }

      // Flush remaining data
      const mp3buf = mp3Encoder.flush()
      if (mp3buf.length > 0) {
        mp3Data.push(new Uint8Array(mp3buf))
      }

      // Create MP3 blob
      const mp3Blob = new Blob(mp3Data, { type: 'audio/mp3' })
      console.log('[MP3] Created MP3 blob, size:', mp3Blob.size, 'bytes')

      if (mp3Blob.size === 0) {
        throw new Error('MP3 conversion resulted in empty file')
      }

      // Download
      const url = URL.createObjectURL(mp3Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `generated_speech_${Date.now()}.mp3`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      console.log('[MP3] Download triggered successfully')
    } catch (error) {
      console.error('[MP3] Error converting to MP3:', error)
      // Fallback to WAV download
      const a = document.createElement('a')
      a.href = audioUrl
      a.download = `generated_speech_${Date.now()}.wav`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    }
  }

  const handleShare = async () => {
    const url = window.location.href

    // Try native share API first (mobile)
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'HD-Voice-Clone Audio',
          text: 'Check out this generated speech!',
          url: url,
        })
        return
      } catch (err) {
        // User cancelled or error, fall back to clipboard
      }
    }

    // Fall back to copying link
    try {
      await navigator.clipboard.writeText(url)
      alert('Link copied to clipboard!')
    } catch (err) {
      alert('Could not copy link')
    }
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
        <div ref={containerRef} className="w-full rounded" />
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">{formatTime(currentTime)}</span>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={togglePlay}>
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleDownload} title="Download MP3">
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleShare} title="Share link">
              <Share2 className="h-4 w-4" />
            </Button>
          </div>
          <span className="text-xs text-muted-foreground">{formatTime(duration)}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div ref={containerRef} className="w-full rounded-lg" />

        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>

        <div className="flex items-center justify-center gap-2">
          <Button variant="ghost" size="icon" className="h-10 w-10" onClick={toggleMute}>
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

          <Button variant="ghost" size="icon" className="h-10 w-10" onClick={handleDownload} title="Download MP3">
            <Download className="h-5 w-5" />
          </Button>

          <Button variant="ghost" size="icon" className="h-10 w-10" onClick={handleShare} title="Share link">
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
    </div>
  )
}

function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return <label className={className}>{children}</label>
}
