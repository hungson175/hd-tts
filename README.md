# VietVoice-TTS

A Vietnamese Text-to-Speech library that provides high-quality speech synthesis with voice cloning capabilities.

## Features

- 🎯 **High-quality Vietnamese TTS** - Natural-sounding speech synthesis
- 🔊 **Multiple voice options** - Gender, accent, emotion, and style variations
- 🎭 **Voice cloning** - Clone voices using reference audio
- 📱 **Dual interfaces** - Both CLI and Python API
- 🔄 **Chunk processing** - Handle long texts efficiently

## Live Demo

Try VietVoice TTS online with our interactive Gradio interface before installing the library:

**🌐 [VietVoice TTS/](https://demo.nguyenbinh.dev/tts)**

The demo allows you to:
- Test different voice options (gender, accent, emotion, style)
- Try voice cloning with your own reference audio
- Experience the quality and capabilities without any setup
- Generate sample audio files to evaluate the results

NOTE: The demo link is temporary and may change or be disabled at any time. You can also try our [colab](https://colab.research.google.com/drive/1iBxTDeyyeuNoaMBoVR3iTXDSrapbR_oc?usp=sharing), which is more stable.

## Installation

### Install from Source

Since this package is not yet published on PyPI, you need to install it from source:

```bash
# Clone the repository
git clone https://github.com/nguyenvulebinh/VietVoice-TTS.git
cd VietVoice-TTS

# Install with GPU support (recommended if you have CUDA)
pip install -e ".[gpu]"

# OR install with CPU support (for systems without GPU)
pip install -e ".[cpu]"
```

**Important**: You must choose either `[gpu]` or `[cpu]` - the base installation without extras will not include ONNX Runtime and will not work.

## Quick Start

### Command Line Interface

```bash
# Basic usage
python -m vietvoicetts "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt." output.wav

# With voice options
python -m vietvoicetts "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt." output.wav --gender female --area northern

# Voice cloning with reference audio
python -m vietvoicetts "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt." output.wav --reference-audio examples/sample.m4a --reference-text "Xin chào các anh chị và các bạn. Chào mừng các anh chị đến với podcast Hiếu TV. Trước khi bắt đầu, dành cho anh chị nào mới lần đầu đến podcast này."
```

### Python API

### Basic Text-to-Speech
```python
from vietvoicetts import synthesize

# Simple synthesis
duration = synthesize("Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt.", "greeting.wav")
print(f"Generated audio: {duration:.2f} seconds")
```

### Voice Customization
```python
from vietvoicetts import synthesize

# Female voice with northern accent and happy emotion
duration = synthesize(
    "Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt.",
    "welcome.wav",
    gender="female",
    area="northern",
)
```

### Voice Cloning
```python
from vietvoicetts import synthesize

# Clone voice from reference audio
duration = synthesize(
    "Đây là giọng nói được nhân bản từ tệp âm thanh tham chiếu",
    "cloned_voice.wav",
    reference_audio="examples/sample.m4a",
    reference_text="Xin chào các anh chị và các bạn. Chào mừng các anh chị đến với podcast Hiếu TV. Trước khi bắt đầu, dành cho anh chị nào mới lần đầu đến podcast này."
)
```

### Custom Configuration
```python
from vietvoicetts import TTSApi, ModelConfig

# Custom model configuration
config = ModelConfig(
    speed=1.2,
    random_seed=12345
)

api = TTSApi(config)
duration = api.synthesize_to_file("Xin chào các bạn! Đây là ví dụ cơ bản về tổng hợp giọng nói tiếng Việt.", "custom.wav")
```

## Voice Configuration

### Gender Options
- `male` - Male voice
- `female` - Female voice

### Area/Accent Options
- `northern` - Northern Vietnamese accent
- `southern` - Southern Vietnamese accent  
- `central` - Central Vietnamese accent

### Group/Style Options
- `story` - Storytelling style
- `news` - News reading style
- `audiobook` - Audiobook narration style
- `interview` - Interview/conversation style
- `review` - Review/commentary style

### Emotion Options
- `neutral` - Neutral emotion (default)
- `serious` - Serious tone
- `monotone` - Monotone delivery
- `sad` - Sad emotion
- `surprised` - Surprised tone
- `happy` - Happy emotion
- `angry` - Angry emotion

## CLI Parameters

### Required Arguments
- `text` - Text to synthesize
- `output` - Output audio file path

### Voice Selection
- `--gender` - Voice gender (male/female)
- `--group` - Voice group/style (story/news/audiobook/interview/review)
- `--area` - Voice area/accent (northern/southern/central)
- `--emotion` - Voice emotion (neutral/serious/monotone/sad/surprised/happy/angry)

### Reference Audio (Voice Cloning)
- `--reference-audio` - Path to reference audio file
- `--reference-text` - Text corresponding to reference audio

### Audio Processing
- `--speed` - Speech speed multiplier (default: 1.0)
- `--cross-fade-duration` - Cross-fade duration in seconds (default: 0.1)

### Advanced Options
- `--random-seed` - Random seed for consistent voice generation (default: 9527)


## Disclaimer

By using VietVoice TTS, you agree to the following terms:

**Content Responsibility:**
- Users are solely responsible for all generated content and its usage
- Do not use this library to create content that infringes on third-party intellectual property rights
- Do not generate content that violates applicable laws or regulations

**Voice Cloning Ethics:**
- Only use reference audio that you own or have explicit permission to use
- Respect the rights and consent of individuals whose voices may be cloned
- Clearly indicate when content has been generated using AI voice synthesis

**Liability:**
- The authors and contributors are not liable for any damages or legal issues arising from the use of this software
- Users assume full responsibility for their use of the generated content

**Attribution:**
- When sharing AI-generated content, clearly indicate that it was created using VietVoice TTS
- Provide appropriate attribution to this project when redistributing or building upon this work

## Requirements

- Python 3.7+
- ONNX Runtime
- pydub
- soundfile
- numpy

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please visit the [GitHub repository](https://github.com/nguyenvulebinh/VietVoice-TTS).
