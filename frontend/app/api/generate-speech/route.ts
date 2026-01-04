import { NextResponse } from "next/server"

// FastAPI backend URL
const BACKEND_URL = process.env.TTS_BACKEND_URL || "http://localhost:17603"

export async function POST(request: Request) {
  try {
    const { text, gender, accent, emotion, quality, speed, referenceAudio, referenceText, trimAudioTo } = await request.json()

    // Map frontend params to backend schema
    // Backend uses "area" instead of "accent"
    const backendPayload: Record<string, unknown> = {
      text,
      speed: speed || 1.0,
      quality: quality || "high",  // "high" or "fast"
    }

    // Only include non-auto values
    if (gender && gender !== "auto") {
      backendPayload.gender = gender.toLowerCase()
    }
    if (accent && accent !== "auto") {
      backendPayload.area = accent.toLowerCase() // accent → area
    }
    if (emotion && emotion !== "auto") {
      backendPayload.emotion = emotion.toLowerCase()
    }

    // Voice cloning: include reference audio and text if provided
    if (referenceAudio && referenceText) {
      backendPayload.reference_audio = referenceAudio  // base64 encoded
      backendPayload.reference_text = referenceText

      // If trim duration specified, tell backend to trim the audio
      if (trimAudioTo && typeof trimAudioTo === 'number') {
        backendPayload.trim_audio_to = trimAudioTo
      }
    }

    // Call FastAPI backend
    const response = await fetch(`${BACKEND_URL}/synthesize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(backendPayload),
    })

    if (!response.ok) {
      const errorText = await response.text()
      console.error("[TTS] Backend error:", response.status, errorText)
      return NextResponse.json(
        { success: false, error: `TTS backend error: ${response.status}` },
        { status: response.status }
      )
    }

    // Get binary WAV data
    const audioBuffer = await response.arrayBuffer()

    // Convert to base64 data URL
    const base64Audio = Buffer.from(audioBuffer).toString("base64")
    const audioUrl = `data:audio/wav;base64,${base64Audio}`

    // Extract generation time from headers if available
    const generationTime = response.headers.get("X-Generation-Time")

    return NextResponse.json({
      success: true,
      audioUrl,
      metadata: {
        text,
        gender,
        accent,
        emotion,
        quality,
        speed,
        generationTime: generationTime ? parseFloat(generationTime) : null,
      },
    })
  } catch (error) {
    console.error("[TTS] Error in generate-speech API:", error)
    return NextResponse.json(
      { success: false, error: "Failed to connect to TTS backend" },
      { status: 500 }
    )
  }
}
