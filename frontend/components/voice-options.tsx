import { Card } from "@/components/ui/card"

export default function VoiceOptions() {
  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold mb-4">Voice Options</h2>
      <ul className="space-y-2 text-sm">
        <li className="flex gap-2">
          <span className="font-semibold min-w-[80px]">Gender:</span>
          <span className="text-muted-foreground">Male or Female voice</span>
        </li>
        <li className="flex gap-2">
          <span className="font-semibold min-w-[80px]">Accent:</span>
          <span className="text-muted-foreground">Northern, Southern, or Central accent</span>
        </li>
        <li className="flex gap-2">
          <span className="font-semibold min-w-[80px]">Emotion:</span>
          <span className="text-muted-foreground">Neutral, Happy, Sad, Angry, Surprised, Serious</span>
        </li>
      </ul>
    </Card>
  )
}
