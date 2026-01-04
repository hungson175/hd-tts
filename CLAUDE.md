# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VietVoice-TTS is a Vietnamese Text-to-Speech system with three main components:
- **Core Library** (`vietvoicetts/`): Python library using ONNX Runtime with flow-matching diffusion models
- **Backend** (`backend/`): FastAPI gateway + Redis queue + GPU workers for scalable inference
- **Frontend** (`frontend/`): Next.js 16 web interface

## Architecture

```
Frontend (Next.js, port 3341)
    ↓ POST /api/generate-speech (with quality: "high" | "fast")
Next.js API Route (proxies to backend)
    ↓
FastAPI Gateway (port 17603)
    ↓ Redis queues (tts:jobs:high, tts:jobs:fast)
TTS Workers (persistent GPU model)
    ├── High-quality workers (NFE=32) → tts:jobs:high
    └── Fast workers (NFE=16) → tts:jobs:fast
    ↓ ONNX Runtime
3 ONNX Models (preprocess → transformer × NFE → decode)
    ↓
WAV audio (24kHz mono)
```

## Commands

### Core Library
```bash
# Install with GPU support (required)
pip install -e ".[gpu]"

# CLI usage
python -m vietvoicetts "Xin chào" output.wav --gender female --area northern

# Python API
from vietvoicetts import synthesize
synthesize("Xin chào", "output.wav", gender="female", area="northern")
```

### Backend Server
```bash
cd backend
./start.sh           # Start gateway + 2 high-quality workers (default)
./start.sh 3         # Start with 3 high-quality workers
./start.sh "2h,1f"   # Start with 2 high-quality + 1 fast worker
./start.sh "1h,2f"   # Start with 1 high-quality + 2 fast workers
./start.sh stop      # Stop all
./start.sh status    # Show status

# Manual start
API_PORT=17603 python backend/gateway/main.py
WORKER_ID=worker-1 QUALITY=high python backend/worker/main.py
WORKER_ID=worker-2 QUALITY=fast python backend/worker/main.py
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev             # Runs on port 3341
pnpm build
pnpm lint
```

## Key Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Frontend Port | 3341 | Configured in global CLAUDE.md |
| Backend Port | 17603 | Configured in global CLAUDE.md |
| Model Cache | `~/.cache/vietvoicetts/` | Auto-downloads ~1GB on first use |
| GPU Memory | ~2.75GB per worker | 3 workers ≈ 8.25GB VRAM |

## Persistent Services (systemd)

**Backend and Frontend are now running as persistent systemd services.** They auto-start on boot.

| Service | Status | Port |
|---------|--------|------|
| Frontend (Next.js) | systemd enabled | 3341 |
| Backend Gateway | systemd enabled | 17603 |
| TTS Workers | systemd enabled | - |
| Redis | systemd enabled | 6379 |

No need to manually start services - they run automatically after server restart.

### Quality Tiers

| Quality | NFE Steps | Gen Time | Use Case |
|---------|-----------|----------|----------|
| `high` | 32 | ~3-5s | Production, high-quality output |
| `fast` | 16 | ~1.5-2.5s | Preview, drafts, real-time apps |

Workers listen to separate Redis queues based on quality (`tts:jobs:high`, `tts:jobs:fast`).

## Voice Parameters

```python
gender: "male" | "female"
area: "northern" | "southern" | "central"  # Note: frontend uses "accent"
emotion: "neutral" | "happy" | "sad" | "angry" | "surprised" | "serious"
group: "story" | "news" | "audiobook" | "interview" | "review"
speed: 0.5 - 2.0
quality: "high" | "fast"  # High=NFE32, Fast=NFE16
```

## Critical Integration Notes

1. **Frontend→Backend mapping**: Frontend sends `accent`, backend expects `area` (converted in `frontend/app/api/generate-speech/route.ts`)

2. **Worker model persistence**: Workers load the TTS model ONCE at startup and keep it in GPU memory. This avoids ~4s model load per request.

3. **Redis required**: Backend gateway and workers require Redis at `redis://localhost:6379/0`

4. **Text chunking**: Long texts are automatically chunked (max 15s audio per chunk) and cross-faded

5. **Voice cloning**: Requires both `reference_audio` (file path) and `reference_text` (transcript)

## API Endpoints (Backend)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/synthesize` | Sync TTS, returns WAV binary |
| POST | `/synthesize/async` | Async TTS, returns job_id |
| GET | `/job/{job_id}` | Poll job status |
| GET | `/job/{job_id}/audio` | Download completed audio |
| GET | `/health` | Health check with worker status |
| GET | `/voices` | List available voice options |

## File Structure (Key Files)

```
vietvoicetts/
├── api.py              # TTSApi class, synthesize()
├── cli.py              # Command-line interface
└── core/
    ├── tts_engine.py   # Main inference orchestration
    ├── model.py        # ONNX session management
    └── model_config.py # ModelConfig dataclass

backend/
├── gateway/main.py     # FastAPI app
├── worker/main.py      # TTS worker with persistent model
├── shared/
│   ├── schemas.py      # Pydantic models
│   └── redis_client.py # Redis operations
└── start.sh            # Startup script

frontend/
├── app/
│   ├── page.tsx                    # Home page
│   └── api/generate-speech/route.ts # Backend proxy
└── components/
    └── text-to-synthesize-tab.tsx  # Main TTS form
```
