import { NextResponse } from "next/server"

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:17603"

// GET /api/voice-samples/[id] - Get voice sample audio
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params

    const response = await fetch(`${BACKEND_URL}/voice-samples/${id}/audio`)

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { error: error.detail || "Voice sample not found" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error getting voice sample:", error)
    return NextResponse.json(
      { error: "Failed to get voice sample" },
      { status: 500 }
    )
  }
}

// DELETE /api/voice-samples/[id] - Delete a voice sample
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params

    const response = await fetch(`${BACKEND_URL}/voice-samples/${id}`, {
      method: "DELETE",
    })

    if (!response.ok) {
      const error = await response.json()
      return NextResponse.json(
        { error: error.detail || "Failed to delete voice sample" },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Error deleting voice sample:", error)
    return NextResponse.json(
      { error: "Failed to delete voice sample" },
      { status: 500 }
    )
  }
}
