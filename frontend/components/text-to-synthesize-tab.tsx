"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Loader2, Mic, Square, Trash2, Sparkles, Save, Check } from "lucide-react"
import { Switch } from "@/components/ui/switch"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown } from "lucide-react"
import { Input } from "@/components/ui/input"

// Default text for voice cloning - user reads this aloud
const VOICE_CLONING_TEXT = "Tiếp nữa, chúng ta sẽ điểm qua một số công cụ khác trong Facebook Business Manager rất hữu ích cho quảng cáo trên Facebook và Instagram."

interface VoiceSample {
  id: string
  name: string | null
  reference_text: string
  created_at: number
  is_named: boolean
}

interface TextToSynthesizeTabProps {
  onGenerate: (audioUrl: string, time: number) => void
  isGenerating: boolean
  setIsGenerating: (value: boolean) => void
}

export default function TextToSynthesizeTab({ onGenerate, isGenerating, setIsGenerating }: TextToSynthesizeTabProps) {
  const [text, setText] = useState("Tiếp theo, bạn sẽ được làm quen với Facebook Ads Manager, để hiểu rõ cấu trúc và cách thiết lập campaign, ad set và ad. Sau đó, chúng ta sẽ phân tích các định dạng quảng cáo khác nhau và những best practices khi chạy ads cho nghệ sĩ.")
  const [gender, setGender] = useState("auto")
  const [accent, setAccent] = useState("auto")
  const [emotion, setEmotion] = useState("auto")
  const [quality, setQuality] = useState("high")
  const [speed, setSpeed] = useState([1])

  // Voice cloning section state - default OPEN, remember user preference
  const [isVoiceCloningOpen, setIsVoiceCloningOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('voiceCloningOpen')
      return saved !== null ? saved === 'true' : true // Default to OPEN
    }
    return true
  })

  // Persist voice cloning open/closed state
  useEffect(() => {
    localStorage.setItem('voiceCloningOpen', String(isVoiceCloningOpen))
  }, [isVoiceCloningOpen])

  // Voice cloning recording state
  const [isRecording, setIsRecording] = useState(false)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null)
  const [recordedAudioBase64, setRecordedAudioBase64] = useState<string | null>(null)
  const [useVoiceCloning, setUseVoiceCloning] = useState(true) // Default to using cloning when recorded
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])

  // Saved voice samples state
  const [savedSamples, setSavedSamples] = useState<VoiceSample[]>([])
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null)
  const [selectedSampleAudio, setSelectedSampleAudio] = useState<string | null>(null)
  const [selectedSampleText, setSelectedSampleText] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [saveName, setSaveName] = useState("")
  const [showSaveInput, setShowSaveInput] = useState(false)

  // Load saved samples on mount
  useEffect(() => {
    loadSavedSamples()
  }, [])

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

  // Determine active voice cloning source
  const hasActiveCloning = (recordedAudioBase64 || selectedSampleAudio) && useVoiceCloning
  const activeAudioBase64 = recordedAudioBase64 || selectedSampleAudio
  const activeReferenceText = recordedAudioBase64 ? VOICE_CLONING_TEXT : selectedSampleText

  const startRecording = async () => {
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

  const handleGenerate = async () => {
    setIsGenerating(true)
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
      }

      const response = await fetch("/api/generate-speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })

      const data = await response.json()
      const endTime = Date.now()
      const duration = (endTime - startTime) / 1000

      onGenerate(data.audioUrl, duration)
    } catch (error) {
      console.error("Error generating speech:", error)
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
            {selectedSampleId && !recordedAudioBase64 && <span className="text-xs text-blue-500 font-medium">● Saved sample</span>}
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
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearRecording}
                  title="Clear recording"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              )}
            </div>

            {/* Recording indicator */}
            {isRecording && (
              <div className="flex items-center gap-2 text-red-500">
                <span className="animate-pulse">●</span>
                <span className="text-sm">Recording... Read the text above clearly.</span>
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

      {/* Voice cloning toggle - shows when recording or saved sample exists */}
      {(recordedAudioBase64 || selectedSampleAudio) && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/50 border">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium">
              Use cloned voice
              {recordedAudioBase64 && <span className="text-xs text-muted-foreground ml-1">(new recording)</span>}
              {selectedSampleId && !recordedAudioBase64 && (
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
    </div>
  )
}
