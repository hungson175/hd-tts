"use client"

import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card } from "@/components/ui/card"
import { AudioLines } from "lucide-react"
import TextToSynthesizeTab from "./text-to-synthesize-tab"
import GeneratedAudioTab from "./generated-audio-tab"
import VoiceOptions from "./voice-options"

export default function TTSInterface() {
  const [activeTab, setActiveTab] = useState("text")
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationTime, setGenerationTime] = useState<number | null>(null)

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-foreground mb-2">HD-Voice-Clone</h1>
        <p className="text-muted-foreground">High-quality Text-to-Speech with voice cloning support.</p>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_400px]">
        <div className="space-y-6">
          <Card className="p-6">
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="mb-6">
                <TabsTrigger value="text" className="gap-2">
                  Text to synthesize
                </TabsTrigger>
                <TabsTrigger value="audio" className="gap-2">
                  <AudioLines className="h-4 w-4" />
                  Generated Audio
                </TabsTrigger>
              </TabsList>

              <TabsContent value="text" className="mt-0">
                <TextToSynthesizeTab
                  onGenerate={(url, time) => {
                    setAudioUrl(url)
                    setGenerationTime(time)
                    setActiveTab("audio")
                  }}
                  isGenerating={isGenerating}
                  setIsGenerating={setIsGenerating}
                />
              </TabsContent>

              <TabsContent value="audio" className="mt-0">
                <GeneratedAudioTab audioUrl={audioUrl} generationTime={generationTime} />
              </TabsContent>
            </Tabs>
          </Card>

          <VoiceOptions />
        </div>

        <div className="lg:sticky lg:top-6 lg:h-fit">
          {audioUrl && (
            <Card className="p-6">
              <h3 className="text-sm font-medium mb-4 flex items-center gap-2">
                <AudioLines className="h-4 w-4 text-primary" />
                Generated Audio
              </h3>
              <GeneratedAudioTab audioUrl={audioUrl} generationTime={generationTime} compact />
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
