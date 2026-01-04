"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Loader2, Mic, Square, Trash2, Sparkles, Save, Check, Upload, FileAudio, Download } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"
import LinearProgressBar from "./linear-progress-bar"

// Default text for voice cloning - user reads this aloud
const VOICE_CLONING_TEXT = "Tiếp nữa, chúng ta sẽ điểm qua một số công cụ khác trong Facebook Business Manager rất hữu ích cho quảng cáo trên Facebook và Instagram."

// Time estimation calibration (seconds per word)
// Calibrated from 6 actual generation tests (3 samples × 2 runs each)
// Test results: 272 total words, 30.80s total time
// Samples: Vietnamese text 43-49 words, high quality mode
const TIME_PER_WORD = 0.1132

interface VoiceSample {
  id: string
  name: string | null
  reference_text: string
  created_at: number
  is_named: boolean
}

interface TextToSynthesizeTabProps {
  text: string
  setText: (value: string) => void
  onGenerate: (audioUrl: string, time: number) => void
  isGenerating: boolean
  setIsGenerating: (value: boolean) => void
}

export default function TextToSynthesizeTab({ text, setText, onGenerate, isGenerating, setIsGenerating }: TextToSynthesizeTabProps) {
  const [gender, setGender] = useState("auto")
  const [accent, setAccent] = useState("auto")
  const [emotion, setEmotion] = useState("auto")
  const [quality, setQuality] = useState("high")
  const [speed, setSpeed] = useState([1])

  // Progress bar estimation
  const [estimatedSeconds, setEstimatedSeconds] = useState(0)

  // Voice cloning section state - default OPEN, remember user preference
  // Initialize with consistent default to avoid hydration mismatch
  const [isVoiceCloningOpen, setIsVoiceCloningOpen] = useState(true)
  const [isHydrated, setIsHydrated] = useState(false)

  // Load saved preference after hydration
  useEffect(() => {
    const saved = localStorage.getItem('voiceCloningOpen')
    if (saved !== null) {
      setIsVoiceCloningOpen(saved === 'true')
    }
    setIsHydrated(true)
  }, [])

  // Persist voice cloning open/closed state (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      localStorage.setItem('voiceCloningOpen', String(isVoiceCloningOpen))
    }
  }, [isVoiceCloningOpen, isHydrated])

  // Voice cloning recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null)
  const [recordedAudioBase64, setRecordedAudioBase64] = useState<string | null>(null)
  const [useVoiceCloning, setUseVoiceCloning] = useState(true) // Default to using cloning when recorded
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  // File upload state
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null)
  const [uploadedAudioUrl, setUploadedAudioUrl] = useState<string | null>(null)
  const [uploadedAudioBase64, setUploadedAudioBase64] = useState<string | null>(null)
  const [uploadedNeedsTrim, setUploadedNeedsTrim] = useState(false)  // If uploaded file > 15s, backend will trim
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const SUPPORTED_FORMATS = ['audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/ogg', 'audio/flac']

  // Saved voice samples state
  const [savedSamples, setSavedSamples] = useState<VoiceSample[]>([])
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [selectedSampleAudio, setSelectedSampleAudio] = useState<string | null>(null)
  const [selectedSampleText, setSelectedSampleText] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveName, setSaveName] = useState("")
  const [showSaveInput, setShowSaveInput] = useState(false)
  const [voiceInitialized, setVoiceInitialized] = useState(false) // Track if we've loaded from localStorage

  // Load saved samples on mount and restore last selected voice
  useEffect(() => {
    const initVoiceSamples = async () => {
      await loadSavedSamples()
      // Restore last selected voice from localStorage
      const savedVoiceId = localStorage.getItem('selectedVoiceSampleId')
      console.log('[VoicePersistence] Checking localStorage, savedVoiceId:', savedVoiceId)
      if (savedVoiceId) {
        await restoreSelectedVoice(savedVoiceId)
      }
      // Mark as initialized AFTER loading
      setVoiceInitialized(true)
      console.log('[VoicePersistence] Initialization complete')
    }
    initVoiceSamples()
  }, [])

  // Persist selected voice to localStorage - but ONLY after initial load
  useEffect(() => {
    // Skip persistence until we've loaded from localStorage
    if (!voiceInitialized) {
      console.log('[VoicePersistence] Skipping persistence - not initialized yet')
      return
    }

    console.log('[VoicePersistence] selectedSampleId changed to:', selectedSampleId)
    if (selectedSampleId) {
      localStorage.setItem('selectedVoiceSampleId', selectedSampleId)
      console.log('[VoicePersistence] Saved to localStorage:', selectedSampleId)
    } else {
      localStorage.removeItem('selectedVoiceSampleId')
      console.log('[VoicePersistence] Removed from localStorage')
    }
  }, [selectedSampleId, voiceInitialized])

  // Restore selected voice (called after samples are loaded)
  const restoreSelectedVoice = async (sampleId: string) => {
    console.log('[VoicePersistence] Restoring voice sample:', sampleId)
    try {
      const response = await fetch(`/api/voice-samples/${sampleId}`)
      console.log('[VoicePersistence] API response status:', response.status)
      if (response.ok) {
        const data = await response.json()
        console.log('[VoicePersistence] Restored sample data, has audio:', !!data.audio)
        setSelectedSampleId(sampleId)
        setSelectedSampleAudio(data.audio)
        setSelectedSampleText(data.reference_text)
      } else {
        // Sample no longer exists, clear localStorage
        console.log('[VoicePersistence] Sample not found, clearing localStorage')
        localStorage.removeItem('selectedVoiceSampleId')
      }
    } catch (error) {
      console.error("[VoicePersistence] Error restoring voice sample:", error)
      localStorage.removeItem('selectedVoiceSampleId')
    }
  }

  const loadSavedSamples = async () => {
    try {
      const response = await fetch("/api/voice-samples")
      if (response.ok) {
        const data = await response.json()
        setSavedSamples(data.samples || [])
      }
    } catch (error) {
      console.error("Error loading voice samples:", error)
    }
  }

  const saveCurrentRecording = async (name?: string) => {
    console.log("saveCurrentRecording called, recordedAudioBase64:", recordedAudioBase64 ? "exists" : "NULL")
    if (!recordedAudioBase64) {
      console.error("No recorded audio to save")
      alert("No recording found. Please record again.")
      return
    }

    setIsSaving(true)
    try {
      const response = await fetch("/api/voice-samples", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio: recordedAudioBase64,
          referenceText: VOICE_CLONING_TEXT,
          name: name || null,
        }),
      })

      if (response.ok) {
        await loadSavedSamples()
        setShowSaveInput(false)
        setSaveName("")
      } else {
        const errorData = await response.json().catch(() => ({}))
        console.error("Failed to save voice sample:", errorData)
        alert(`Failed to save: ${errorData.error || "Unknown error"}`)
      }
    } catch (error) {
      console.error("Error saving voice sample:", error)
      alert("Failed to save voice sample. Check if backend is running.")
    } finally {
      setIsSaving(false)
    }
  }

  const selectSavedSample = async (sampleId: string) => {
    if (selectedSampleId === sampleId) {
      // Deselect
      setSelectedSampleId(null)
      setSelectedSampleAudio(null)
      setSelectedSampleText(null)
      return
    }

    try {
      const response = await fetch(`/api/voice-samples/${sampleId}`)
      if (response.ok) {
        const data = await response.json()
        setSelectedSampleId(sampleId)
        setSelectedSampleAudio(data.audio)
        setSelectedSampleText(data.reference_text)
        // Clear new recording when selecting saved sample
        clearRecording()
      }
    } catch (error) {
      console.error("Error loading voice sample:", error)
    }
  }

  const deleteSavedSample = async (sampleId: string) => {
    try {
      const response = await fetch(`/api/voice-samples/${sampleId}`, {
        method: "DELETE",
      })
      if (response.ok) {
        if (selectedSampleId === sampleId) {
          setSelectedSampleId(null)
          setSelectedSampleAudio(null)
          setSelectedSampleText(null)
        }
        await loadSavedSamples()
      }
    } catch (error) {
      console.error("Error deleting voice sample:", error)
    }
  }

  // Determine active voice cloning source (priority: recorded > uploaded > saved)
  const hasActiveCloning = (recordedAudioBase64 || uploadedAudioBase64 || selectedSampleAudio) && useVoiceCloning
  const activeAudioBase64 = recordedAudioBase64 || uploadedAudioBase64 || selectedSampleAudio
  const activeReferenceText = (recordedAudioBase64 || uploadedAudioBase64) ? VOICE_CLONING_TEXT : selectedSampleText

  // Constants for audio limits
  const MAX_AUDIO_DURATION = 15 // seconds
  const TARGET_TRIM_DURATION = 14.5 // seconds

  // Trim audio from both ends using Web Audio API
  // Converts to mono 24kHz WAV (TTS backend requirement)
  const trimAudioFile = async (file: File, targetDuration: number): Promise<Blob> => {
    const arrayBuffer = await file.arrayBuffer()
    console.log(`[Trim] File size: ${arrayBuffer.byteLength} bytes`)

    const audioContext = new AudioContext()
    let audioBuffer: AudioBuffer

    try {
      audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0))
    } catch (decodeError) {
      console.error("[Trim] Failed to decode audio:", decodeError)
      await audioContext.close()
      throw new Error(`Cannot decode audio file: ${decodeError}`)
    }

    console.log(`[Trim] Decoded: ${audioBuffer.duration}s, ${audioBuffer.sampleRate}Hz, ${audioBuffer.numberOfChannels}ch, ${audioBuffer.length} samples`)

    if (audioBuffer.length === 0 || audioBuffer.duration === 0) {
      await audioContext.close()
      throw new Error("Audio file is empty after decoding")
    }

    const originalDuration = audioBuffer.duration
    const trimAmount = (originalDuration - targetDuration) / 2
    const startTime = Math.max(0, trimAmount)
    const endTime = Math.min(originalDuration, originalDuration - trimAmount)

    const sourceSampleRate = audioBuffer.sampleRate
    const startSample = Math.floor(startTime * sourceSampleRate)
    const endSample = Math.floor(endTime * sourceSampleRate)
    const trimmedLength = endSample - startSample

    console.log(`[Trim] Trimming: start=${startTime.toFixed(2)}s, end=${endTime.toFixed(2)}s, samples=${trimmedLength}`)

    if (trimmedLength <= 0) {
      await audioContext.close()
      throw new Error("Invalid trim range - no samples remaining")
    }

    // Convert to mono by averaging all channels
    const monoData = new Float32Array(trimmedLength)
    const numChannels = audioBuffer.numberOfChannels
    for (let i = 0; i < trimmedLength; i++) {
      let sum = 0
      for (let channel = 0; channel < numChannels; channel++) {
        sum += audioBuffer.getChannelData(channel)[startSample + i]
      }
      monoData[i] = sum / numChannels
    }

    // Resample to 24000 Hz (TTS model sample rate)
    const targetSampleRate = 24000
    const resampleRatio = targetSampleRate / sourceSampleRate
    const resampledLength = Math.floor(trimmedLength * resampleRatio)

    console.log(`[Trim] Resampling: ${sourceSampleRate}Hz -> ${targetSampleRate}Hz, ratio=${resampleRatio.toFixed(4)}, output samples=${resampledLength}`)

    if (resampledLength <= 0) {
      await audioContext.close()
      throw new Error("Resampling resulted in zero samples")
    }

    const resampledData = new Float32Array(resampledLength)

    // Linear interpolation resampling
    for (let i = 0; i < resampledLength; i++) {
      const srcIndex = i / resampleRatio
      const srcIndexFloor = Math.floor(srcIndex)
      const srcIndexCeil = Math.min(srcIndexFloor + 1, trimmedLength - 1)
      const fraction = srcIndex - srcIndexFloor
      resampledData[i] = monoData[srcIndexFloor] * (1 - fraction) + monoData[srcIndexCeil] * fraction
    }

    // Validate audio has actual content (not all zeros)
    let hasContent = false
    for (let i = 0; i < Math.min(1000, resampledLength); i++) {
      if (Math.abs(resampledData[i]) > 0.001) {
        hasContent = true
        break
      }
    }
    console.log(`[Trim] Audio has content: ${hasContent}`)

    // Convert to WAV blob
    const wavBlob = floatArrayToWav(resampledData, targetSampleRate)
    console.log(`[Trim] Output WAV: ${wavBlob.size} bytes, ${(resampledLength / targetSampleRate).toFixed(2)}s`)

    await audioContext.close()
    return wavBlob
  }

  // Convert Float32Array (mono) to WAV Blob
  const floatArrayToWav = (samples: Float32Array, sampleRate: number): Blob => {
    const numChannels = 1 // Mono
    const bitDepth = 16
    const bytesPerSample = bitDepth / 8
    const blockAlign = numChannels * bytesPerSample

    const dataLength = samples.length * blockAlign
    const bufferLength = 44 + dataLength
    const arrayBuffer = new ArrayBuffer(bufferLength)
    const view = new DataView(arrayBuffer)

    // WAV header
    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + dataLength, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true) // fmt chunk size
    view.setUint16(20, 1, true)  // PCM format
    view.setUint16(22, numChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * blockAlign, true) // byte rate
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, bitDepth, true)
    writeString(36, 'data')
    view.setUint32(40, dataLength, true)

    // Write audio samples
    let offset = 44
    for (let i = 0; i < samples.length; i++) {
      const sample = Math.max(-1, Math.min(1, samples[i]))
      const intSample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
      view.setInt16(offset, intSample, true)
      offset += 2
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' })
  }

  // File upload handlers
  const handleFileUpload = async (file: File) => {
    // Validate file type (M4A not supported)
    if (file.name.match(/\.m4a$/i) || file.type.includes('m4a') || file.type === 'audio/mp4') {
      alert('M4A format not supported. Please convert to WAV or MP3 first.')
      return
    }
    if (!SUPPORTED_FORMATS.includes(file.type) && !file.name.match(/\.(webm|wav|mp3|ogg|flac)$/i)) {
      alert('Unsupported format. Please use: WAV, MP3, OGG, FLAC, or WEBM')
      return
    }

    // Clear recording when uploading
    clearRecording()
    // Clear selected sample
    setSelectedSampleId(null)
    setSelectedSampleAudio(null)
    setSelectedSampleText(null)

    // Check audio duration
    const audioUrl = URL.createObjectURL(file)
    const audio = new Audio(audioUrl)

    audio.onloadedmetadata = async () => {
      const duration = audio.duration

      if (duration > MAX_AUDIO_DURATION) {
        const confirmTrim = window.confirm(
          `Audio is ${duration.toFixed(1)} seconds long (max ${MAX_AUDIO_DURATION}s).\n\n` +
          `The server will automatically trim it to ${TARGET_TRIM_DURATION} seconds ` +
          `(from both ends equally).\n\nContinue?`
        )

        if (!confirmTrim) {
          URL.revokeObjectURL(audioUrl)
          return
        }

        // Mark that backend should trim this audio
        setUploadedNeedsTrim(true)
        setUploadedFileName(`${file.name} (will be trimmed)`)
      } else {
        setUploadedNeedsTrim(false)
        setUploadedFileName(file.name)
      }

      // Set the audio URL for preview
      setUploadedAudioUrl(audioUrl)

      // Convert uploaded file to 24kHz mono WAV (reduces memory, matches backend expectations)
      try {
        const arrayBuffer = await file.arrayBuffer()
        const audioContext = new AudioContext()
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

        // Convert to mono
        const sourceSampleRate = audioBuffer.sampleRate
        const monoData = new Float32Array(audioBuffer.length)
        const numChannels = audioBuffer.numberOfChannels
        for (let i = 0; i < audioBuffer.length; i++) {
          let sum = 0
          for (let channel = 0; channel < numChannels; channel++) {
            sum += audioBuffer.getChannelData(channel)[i]
          }
          monoData[i] = sum / numChannels
        }

        // Resample to 24kHz
        const targetSampleRate = 24000
        const resampleRatio = targetSampleRate / sourceSampleRate
        const resampledLength = Math.floor(monoData.length * resampleRatio)
        const resampledData = new Float32Array(resampledLength)

        for (let i = 0; i < resampledLength; i++) {
          const srcIndex = i / resampleRatio
          const srcIndexFloor = Math.floor(srcIndex)
          const srcIndexCeil = Math.min(srcIndexFloor + 1, monoData.length - 1)
          const fraction = srcIndex - srcIndexFloor
          resampledData[i] = monoData[srcIndexFloor] * (1 - fraction) + monoData[srcIndexCeil] * fraction
        }

        // Create WAV blob and convert to base64
        const wavBlob = floatArrayToWav(resampledData, targetSampleRate)
        const reader = new FileReader()
        reader.onloadend = () => {
          const dataUrl = reader.result as string
          const base64 = dataUrl.split(',')[1]
          setUploadedAudioBase64(base64)
        }
        reader.readAsDataURL(wavBlob)

        await audioContext.close()
        console.log(`[Upload] Converted ${file.name}: ${sourceSampleRate}Hz → 24kHz, ${numChannels}ch → mono`)
      } catch (error) {
        console.error("Error processing uploaded audio:", error)
        alert("Could not process audio file. Please try another file.")
        URL.revokeObjectURL(audioUrl)
        setUploadedAudioUrl(null)
        setUploadedFileName(null)
      }
    }

    audio.onerror = () => {
      URL.revokeObjectURL(audioUrl)
      alert("Could not read audio file. Please try another file.")
    }
  }

  const clearUpload = () => {
    if (uploadedAudioUrl) {
      URL.revokeObjectURL(uploadedAudioUrl)
    }
    setUploadedAudioUrl(null)
    setUploadedAudioBase64(null)
    setUploadedFileName(null)
    setUploadedNeedsTrim(false)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const startRecording = async () => {
    // Clear uploaded file when starting recording
    clearUpload()

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const audioUrl = URL.createObjectURL(audioBlob)
        setRecordedAudioUrl(audioUrl)

        // Convert to base64 for API using FileReader (handles large files correctly)
        const reader = new FileReader()
        reader.onloadend = () => {
          const dataUrl = reader.result as string
          // Remove the data URL prefix to get pure base64
          const base64 = dataUrl.split(',')[1]
          setRecordedAudioBase64(base64)
        }
        reader.readAsDataURL(audioBlob)

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error("Error starting recording:", error)
      alert("Could not access microphone. Please allow microphone access.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  const clearRecording = () => {
    if (recordedAudioUrl) {
      URL.revokeObjectURL(recordedAudioUrl)
    }
    setRecordedAudioUrl(null)
    setRecordedAudioBase64(null)
    // Also clear save UI state
    setShowSaveInput(false)
    setSaveName("")
  }

  // Download recording as WAV file (24kHz mono - TTS backend requirement)
  const downloadRecordingAsWav = async () => {
    if (!recordedAudioBase64) {
      alert("No recording to download")
      return
    }

    try {
      // Decode base64 to ArrayBuffer
      const binaryString = atob(recordedAudioBase64)
      const bytes = new Uint8Array(binaryString.length)
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i)
      }

      // Decode audio using Web Audio API
      const audioContext = new AudioContext()
      const audioBuffer = await audioContext.decodeAudioData(bytes.buffer)

      // Convert to mono (average all channels)
      const sourceSampleRate = audioBuffer.sampleRate
      const monoData = new Float32Array(audioBuffer.length)
      const numChannels = audioBuffer.numberOfChannels
      for (let i = 0; i < audioBuffer.length; i++) {
        let sum = 0
        for (let channel = 0; channel < numChannels; channel++) {
          sum += audioBuffer.getChannelData(channel)[i]
        }
        monoData[i] = sum / numChannels
      }

      // Resample to 24kHz (TTS backend requirement)
      const targetSampleRate = 24000
      const resampleRatio = targetSampleRate / sourceSampleRate
      const resampledLength = Math.floor(monoData.length * resampleRatio)
      const resampledData = new Float32Array(resampledLength)

      // Linear interpolation resampling
      for (let i = 0; i < resampledLength; i++) {
        const srcIndex = i / resampleRatio
        const srcIndexFloor = Math.floor(srcIndex)
        const srcIndexCeil = Math.min(srcIndexFloor + 1, monoData.length - 1)
        const fraction = srcIndex - srcIndexFloor
        resampledData[i] = monoData[srcIndexFloor] * (1 - fraction) + monoData[srcIndexCeil] * fraction
      }

      // Create WAV blob at 24kHz
      const wavBlob = floatArrayToWav(resampledData, targetSampleRate)

      // Trigger download
      const url = URL.createObjectURL(wavBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = `voice_recording_${Date.now()}.wav`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      await audioContext.close()
    } catch (error) {
      console.error("Error converting to WAV:", error)
      alert("Failed to convert recording to WAV. Please try again.")
    }
  }

  const handleGenerate = async () => {
    // Calculate estimated time based on word count
    const wordCount = text.trim().split(/\s+/).length
    const estimated = wordCount * TIME_PER_WORD
    setEstimatedSeconds(estimated)

    setIsGenerating(true)
    // Auto-collapse voice cloning section for better UX
    setIsVoiceCloningOpen(false)
    const startTime = Date.now()

    try {
      // Build request payload
      const payload: Record<string, unknown> = {
        text,
        gender,
        accent,
        emotion,
        quality,
        speed: speed[0],
      }

      // Include voice cloning data if available AND user chose to use it
      if (activeAudioBase64 && activeReferenceText && useVoiceCloning) {
        payload.referenceAudio = activeAudioBase64
        payload.referenceText = activeReferenceText

        // If using uploaded audio that needs trimming, tell backend to trim it
        if (uploadedAudioBase64 && uploadedNeedsTrim) {
          payload.trimAudioTo = TARGET_TRIM_DURATION
        }
      }

      console.log("Sending payload:", { ...payload, referenceAudio: payload.referenceAudio ? "[base64 data]" : undefined })

      const response = await fetch("/api/generate-speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      const data = await response.json()
      console.log("Response:", { success: data.success, hasAudioUrl: !!data.audioUrl, error: data.error })

      if (!response.ok || !data.success) {
        alert(`Generation failed: ${data.error || "Unknown error"}`)
        return
      }

      if (!data.audioUrl) {
        alert("No audio returned from server")
        return
      }

      const endTime = Date.now()
      const duration = (endTime - startTime) / 1000

      onGenerate(data.audioUrl, duration)
    } catch (error) {
      console.error("Error generating speech:", error)
      alert(`Error: ${error instanceof Error ? error.message : "Failed to generate speech"}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Enter text to synthesize..."
          className="min-h-[120px] resize-none"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <div className="space-y-2">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded inline-block">Quality</Label>
          <Select value={quality} onValueChange={setQuality}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="high">High Quality</SelectItem>
              <SelectItem value="fast">Fast</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded inline-block">Gender</Label>
          <Select value={gender} onValueChange={setGender}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto</SelectItem>
              <SelectItem value="male">Male</SelectItem>
              <SelectItem value="female">Female</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded inline-block">Accent</Label>
          <Select value={accent} onValueChange={setAccent}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto</SelectItem>
              <SelectItem value="northern">Northern</SelectItem>
              <SelectItem value="southern">Southern</SelectItem>
              <SelectItem value="central">Central</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded inline-block">
            Emotion
          </Label>
          <Select value={emotion} onValueChange={setEmotion}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto</SelectItem>
              <SelectItem value="neutral">Neutral</SelectItem>
              <SelectItem value="happy">Happy</SelectItem>
              <SelectItem value="sad">Sad</SelectItem>
              <SelectItem value="angry">Angry</SelectItem>
              <SelectItem value="surprised">Surprised</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-medium text-primary bg-secondary px-2 py-1 rounded">Speed</Label>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">{speed[0]}</span>
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => setSpeed([1])}>
              ⟲
            </Button>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-muted-foreground">0.5</span>
          <Slider value={speed} onValueChange={setSpeed} min={0.5} max={2} step={0.1} className="flex-1" />
          <span className="text-xs text-muted-foreground">2</span>
        </div>
      </div>

      <Collapsible open={isVoiceCloningOpen} onOpenChange={setIsVoiceCloningOpen} className="rounded-xl border-2 border-primary/20 bg-gradient-to-r from-primary/5 to-secondary/30 p-4">
        <CollapsibleTrigger className="flex items-center justify-between w-full group">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <div className="text-left">
              <h3 className="text-base font-semibold text-foreground group-hover:text-primary transition-colors">
                Voice Cloning
              </h3>
              <p className="text-xs text-muted-foreground">Clone any voice with a short recording</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {recordedAudioBase64 && <span className="text-xs text-green-500 font-medium">● New recording</span>}
            {uploadedAudioBase64 && !recordedAudioBase64 && <span className="text-xs text-purple-500 font-medium">● Uploaded file</span>}
            {selectedSampleId && !recordedAudioBase64 && !uploadedAudioBase64 && <span className="text-xs text-blue-500 font-medium">● Saved sample</span>}
            <ChevronDown className={`h-5 w-5 text-muted-foreground transition-transform ${isVoiceCloningOpen ? "rotate-180" : ""}`} />
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-4">
          <div className="space-y-4 rounded-lg border border-border p-4 bg-background/80">
            {/* Instructions */}
            <div className="space-y-2">
              <p className="text-sm font-medium">Read this text aloud:</p>
              <div className="p-3 bg-secondary rounded-md">
                <p className="text-sm italic">&ldquo;{VOICE_CLONING_TEXT}&rdquo;</p>
              </div>
            </div>

            {/* Recording controls */}
            <div className="flex items-center gap-3">
              {!isRecording ? (
                <Button
                  variant="outline"
                  onClick={startRecording}
                  disabled={isGenerating}
                  className="flex-1"
                >
                  <Mic className="h-4 w-4 mr-2" />
                  {recordedAudioUrl ? "Re-record" : "Start Recording"}
                </Button>
              ) : (
                <Button
                  variant="destructive"
                  onClick={stopRecording}
                  className="flex-1"
                >
                  <Square className="h-4 w-4 mr-2" />
                  Stop Recording
                </Button>
              )}

              {recordedAudioUrl && !isRecording && (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={downloadRecordingAsWav}
                    title="Download as WAV"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={clearRecording}
                    title="Clear recording"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </>
              )}
            </div>

            {/* Recording indicator */}
            {isRecording && (
              <div className="flex items-center gap-2 text-red-500">
                <span className="animate-pulse">●</span>
                <span className="text-sm">Recording... Read the text above clearly.</span>
              </div>
            )}

            {/* OR divider */}
            {!isRecording && !recordedAudioUrl && !uploadedAudioUrl && (
              <div className="flex items-center gap-3">
                <div className="flex-1 border-t border-border" />
                <span className="text-xs text-muted-foreground">OR</span>
                <div className="flex-1 border-t border-border" />
              </div>
            )}

            {/* File Upload Area */}
            {!isRecording && !recordedAudioUrl && (
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative border-2 border-dashed rounded-lg p-4 transition-colors cursor-pointer ${
                  isDragging
                    ? "border-primary bg-primary/5"
                    : uploadedAudioUrl
                    ? "border-green-500 bg-green-50 dark:bg-green-950/20"
                    : "border-border hover:border-primary/50"
                }`}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".webm,.wav,.mp3,.ogg,.flac,.m4a,audio/*"
                  onChange={handleFileInputChange}
                  className="hidden"
                />

                {uploadedAudioUrl ? (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <FileAudio className="h-8 w-8 text-green-500" />
                      <div>
                        <p className="text-sm font-medium">{uploadedFileName}</p>
                        <p className="text-xs text-muted-foreground">Click to change file</p>
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation()
                        clearUpload()
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2 py-2">
                    <Upload className={`h-8 w-8 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
                    <div className="text-center">
                      <p className="text-sm font-medium">
                        {isDragging ? "Drop audio file here" : "Upload audio file"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        Drag & drop or click to browse
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        webm, wav, mp3, ogg, flac, m4a
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Uploaded Audio Preview */}
            {uploadedAudioUrl && !recordedAudioUrl && (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">Preview uploaded audio:</p>
                <audio controls src={uploadedAudioUrl} className="w-full h-10" />
              </div>
            )}

            {/* Playback and Save */}
            {recordedAudioUrl && !isRecording && (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground">Preview your recording:</p>
                <audio controls src={recordedAudioUrl} className="w-full h-10" />

                {/* Save recording */}
                <div className="flex items-center gap-2">
                  {!showSaveInput ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setShowSaveInput(true)}
                      disabled={isSaving}
                    >
                      <Save className="h-4 w-4 mr-2" />
                      Save for later
                    </Button>
                  ) : (
                    <>
                      <Input
                        placeholder="Voice name (optional)"
                        value={saveName}
                        onChange={(e) => setSaveName(e.target.value)}
                        className="flex-1 h-9"
                      />
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => saveCurrentRecording(saveName)}
                        disabled={isSaving}
                      >
                        {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => { setShowSaveInput(false); setSaveName("") }}
                      >
                        Cancel
                      </Button>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* Saved Samples List */}
            {savedSamples.length > 0 && (
              <div className="space-y-2 pt-2 border-t">
                <p className="text-sm font-medium">Saved Voices</p>
                <div className="space-y-2">
                  {savedSamples.map((sample) => (
                    <div
                      key={sample.id}
                      className={`flex items-center justify-between p-2 rounded-md cursor-pointer transition-colors ${
                        selectedSampleId === sample.id
                          ? "bg-primary/10 border border-primary"
                          : "bg-secondary/50 hover:bg-secondary"
                      }`}
                      onClick={() => selectSavedSample(sample.id)}
                    >
                      <div className="flex items-center gap-2">
                        {selectedSampleId === sample.id && (
                          <Check className="h-4 w-4 text-primary" />
                        )}
                        <span className="text-sm">
                          {sample.name || `Voice ${sample.id}`}
                        </span>
                        {sample.is_named && (
                          <span className="text-xs text-muted-foreground">(saved)</span>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSavedSample(sample.id)
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Voice cloning toggle - shows when recording, uploaded file, or saved sample exists */}
      {(recordedAudioBase64 || uploadedAudioBase64 || selectedSampleAudio) && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">
              Use cloned voice
              {recordedAudioBase64 && <span className="text-xs text-muted-foreground ml-1">(new recording)</span>}
              {uploadedAudioBase64 && !recordedAudioBase64 && (
                <span className="text-xs text-muted-foreground ml-1">({uploadedFileName})</span>
              )}
              {selectedSampleId && !recordedAudioBase64 && !uploadedAudioBase64 && (
                <span className="text-xs text-muted-foreground ml-1">
                  ({savedSamples.find(s => s.id === selectedSampleId)?.name || `Voice ${selectedSampleId}`})
                </span>
              )}
            </span>
          </div>
          <Switch
            checked={useVoiceCloning}
            onCheckedChange={setUseVoiceCloning}
          />
        </div>
      )}

      <Button
        onClick={handleGenerate}
        disabled={isGenerating || !text.trim()}
        className="w-full h-12 text-base font-medium"
      >
        {isGenerating ? (
          <>
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
            Generating Speech...
          </>
        ) : hasActiveCloning ? (
          <>
            <Sparkles className="mr-2 h-5 w-5" />
            Generate with Cloned Voice
          </>
        ) : (
          "Generate Speech"
        )}
      </Button>

      {/* Progress bar - shown during generation */}
      {isGenerating && estimatedSeconds > 0 && (
        <LinearProgressBar estimatedSeconds={estimatedSeconds} />
      )}
    </div>
  )
}
