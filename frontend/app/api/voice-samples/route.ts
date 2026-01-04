import { NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:17603"

// POST /api/voice-samples - Save a voice sample
export async function POST(request: Request) {
  try {
    const body = await request.json()

    const response = await fetch(`${BACKEND_URL}/voice-samples`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        audio: body.audio,
        reference_text: body.referenceText,
        name: body.name || null,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { error: error.detail || "Failed to save voice sample" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error saving voice sample:", error)
    return NextResponse.json(
      { error: "Failed to save voice sample" },
      { status: 500 }
    )
  }
}

// GET /api/voice-samples - List all voice samples
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/voice-samples`)

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { error: error.detail || "Failed to list voice samples" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error listing voice samples:", error)
    return NextResponse.json(
      { error: "Failed to list voice samples" },
      { status: 500 }
    )
  }
}
