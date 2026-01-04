import { Card } from "@/components/ui/card"

export default function VoiceCloningInfo() {
  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold mb-4">Voice Cloning</h2>
      <p className="text-sm text-muted-foreground">
        Upload a 10-15 second audio sample and provide the exact transcript to clone a voice. The more accurate the
        transcript, the better the cloning quality will be.
      </p>
    </Card>
  )
}
