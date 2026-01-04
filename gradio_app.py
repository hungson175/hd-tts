#!/usr/bin/env python3
"""
VietVoice TTS Gradio Interface
"""
import gradio as gr
import vietvoicetts
from vietvoicetts import ModelConfig, TTSApi
import tempfile
import os

# Global TTS API instance
tts_api = None

def initialize_tts():
    """Initialize TTS API on startup"""
    global tts_api
    if tts_api is None:
        config = ModelConfig(
            max_chunk_duration=20.0,
            cross_fade_duration=0.15
        )
        tts_api = TTSApi(config)
    return tts_api

def synthesize(
    text: str,
    gender: str,
    area: str,
    emotion: str,
    speed: float,
    reference_audio,
    reference_text: str
):
    """Synthesize speech from text"""
    if not text or text.strip() == "":
        return None, "Please enter some text to synthesize"

    try:
        api = initialize_tts()

        # Prepare parameters
        kwargs = {
            "text": text.strip(),
            "gender": gender.lower() if gender != "Auto" else None,
            "area": area.lower() if area != "Auto" else None,
            "emotion": emotion.lower() if emotion != "Auto" else None,
        }

        # Handle speed
        if speed != 1.0:
            api.config.speed = speed

        # Handle reference audio for voice cloning
        if reference_audio is not None and reference_text and reference_text.strip():
            kwargs["reference_audio"] = reference_audio
            kwargs["reference_text"] = reference_text.strip()

        # Generate audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            output_path = tmp.name

        generation_time = api.synthesize_to_file(output_path=output_path, **kwargs)

        return output_path, f"Generated in {generation_time:.2f} seconds"

    except Exception as e:
        return None, f"Error: {str(e)}"

# Create Gradio interface
with gr.Blocks(title="VietVoice TTS", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # VietVoice TTS
    High-quality Vietnamese Text-to-Speech with voice cloning support.
    """)

    with gr.Row():
        with gr.Column(scale=2):
            text_input = gr.Textbox(
                label="Text to synthesize",
                placeholder="Enter Vietnamese text here...",
                lines=5,
                value="Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt."
            )

            with gr.Row():
                gender = gr.Dropdown(
                    choices=["Auto", "Male", "Female"],
                    value="Auto",
                    label="Gender"
                )
                area = gr.Dropdown(
                    choices=["Auto", "Northern", "Southern", "Central"],
                    value="Auto",
                    label="Accent"
                )
                emotion = gr.Dropdown(
                    choices=["Auto", "Neutral", "Happy", "Sad", "Angry", "Surprised", "Serious"],
                    value="Auto",
                    label="Emotion"
                )

            speed = gr.Slider(
                minimum=0.5,
                maximum=2.0,
                value=1.0,
                step=0.1,
                label="Speed"
            )

            with gr.Accordion("Voice Cloning (Optional)", open=False):
                reference_audio = gr.Audio(
                    label="Reference Audio (10-15 seconds)",
                    type="filepath",
                    sources=["upload"]
                )
                reference_text = gr.Textbox(
                    label="Reference Audio Transcript",
                    placeholder="Enter the exact text spoken in the reference audio...",
                    lines=2
                )

            generate_btn = gr.Button("Generate Speech", variant="primary", size="lg")

        with gr.Column(scale=1):
            audio_output = gr.Audio(
                label="Generated Audio",
                type="filepath",
                autoplay=True
            )
            status_output = gr.Textbox(label="Status", interactive=False)

    generate_btn.click(
        fn=synthesize,
        inputs=[text_input, gender, area, emotion, speed, reference_audio, reference_text],
        outputs=[audio_output, status_output]
    )

    gr.Markdown("""
    ## Voice Options
    - **Gender**: Male or Female voice
    - **Accent**: Northern, Southern, or Central Vietnamese
    - **Emotion**: Neutral, Happy, Sad, Angry, Surprised, Serious

    ## Voice Cloning
    Upload a 10-15 second audio sample and provide the exact transcript to clone a voice.
    """)

if __name__ == "__main__":
    # Pre-initialize TTS to load models
    print("Initializing VietVoice TTS...")
    initialize_tts()
    print("Ready!")

    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
