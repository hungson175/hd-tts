"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { AudioLines } from "lucide-react"
import TextToSynthesizeTab from "./text-to-synthesize-tab"
import GeneratedAudioTab from "./generated-audio-tab"

const DEFAULT_TEXT = "Tiếp theo, bạn sẽ được làm quen với Facebook Ads Manager, để hiểu rõ cấu trúc và cách thiết lập campaign, ad set và ad. Sau đó, chúng ta sẽ phân tích các định dạng quảng cáo khác nhau và những best practices khi chạy ads cho nghệ sĩ."

export default function TTSInterface() {
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationTime, setGenerationTime] = useState<number | null>(null)
  const [text, setText] = useState(DEFAULT_TEXT)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">HD-Voice-Clone</h1>
        <p className="text-muted-foreground">High-quality Text-to-Speech with voice cloning support.</p>
      </div>

      <div className="space-y-6">
        <Card className="p-6">
          <TextToSynthesizeTab
            text={text}
            setText={setText}
            onGenerate={(url, time) => {
              setAudioUrl(url)
              setGenerationTime(time)
            }}
            isGenerating={isGenerating}
            setIsGenerating={setIsGenerating}
          />
        </Card>

        {audioUrl && (
          <Card className="p-6">
            <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
              <AudioLines className="h-4 w-4 text-primary" />
              Generated Audio
            </h3>
            <GeneratedAudioTab audioUrl={audioUrl} generationTime={generationTime} />
          </Card>
        )}
      </div>
    </div>
  )
}
