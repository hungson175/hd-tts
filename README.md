# HD-TTS

Vietnamese Text-to-Speech web application with voice cloning, built on [VietVoice-TTS](https://github.com/nguyenvulebinh/VietVoice-TTS).

## Live Demo

**🌐 [https://hd-tts.hungson175.com](https://hd-tts.hungson175.com)**

## Features

- 🎯 High-quality Vietnamese TTS with natural-sounding speech
- 🎭 Voice cloning from uploaded audio or browser recording
- 🎚️ Multiple voice options (gender, accent, emotion, style)
- ⚡ Two quality modes: High (NFE=32) and Fast (NFE=16)
- 📊 Real-time progress bar with time estimation
- 💾 Persistent voice samples and text input
- 🔊 Waveform visualization with wavesurfer.js
- ⬇️ Download as MP3 or WAV

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+
- CUDA-capable GPU (recommended)
- Redis server

### Installation

```bash
# Clone repository
git clone https://github.com/hungson175/hd-tts.git
cd hd-tts

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[gpu]"

# Install frontend dependencies
cd frontend
pnpm install
cd ..
```

### Running Services

```bash
# Start backend (gateway + 2 high-quality workers)
cd backend
./start.sh

# Start frontend (port 3341)
cd frontend
pnpm build
pnpm start
```

Access at: http://localhost:3341

### Configuration

Default ports (configured in global CLAUDE.md):
- Frontend: 3341
- Backend: 17603

## Architecture

```
Frontend (Next.js) → Backend Gateway (FastAPI) → Redis Queue → TTS Workers (GPU)
```

Workers maintain persistent GPU models for fast generation (~5s for 49 words).

## Voice Parameters

- **Gender**: male, female
- **Accent**: northern, southern, central
- **Emotion**: neutral, happy, sad, angry, surprised, serious
- **Style**: story, news, audiobook, interview, review
- **Speed**: 0.5 - 2.0
- **Quality**: high (NFE=32), fast (NFE=16)

## Voice Cloning

Upload audio or record in browser. Max 15 seconds. Requires reference text transcript.

## Credits

Built on [VietVoice-TTS](https://github.com/nguyenvulebinh/VietVoice-TTS) by Nguyen Vu Le Binh.

## License

MIT License
