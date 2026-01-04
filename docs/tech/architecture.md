# VietVoice-TTS Architecture Documentation

## Overview

VietVoice-TTS is a Vietnamese Text-to-Speech system using a **flow-matching diffusion architecture** with ONNX Runtime for inference. The model supports voice cloning, multiple voice styles, and runs efficiently on both CPU and GPU.

---

## Model Architecture

### Core Components

The model consists of **3 ONNX models** packaged in a single `.pt` archive:

| Model | Purpose | Input | Output |
|-------|---------|-------|--------|
| `preprocess.onnx` | Process reference audio + text | audio, text_ids, max_duration | noise, positional encodings, mel features |
| `transformer.onnx` | Iterative denoising (32 NFE steps) | noise, time_step, encodings | refined noise |
| `decode.onnx` | Convert latent to waveform | refined noise, ref_signal_len | audio waveform |

### Model Source

- **HuggingFace**: `https://huggingface.co/nguyenvulebinh/VietVoice-TTS/resolve/main/model-bin.pt`
- **Cache Location**: `~/.cache/vietvoicetts/model-bin.pt`
- **Auto-download**: Yes, on first use

### Key Parameters

```python
sample_rate = 24000      # Output audio sample rate (Hz)
hop_length = 256         # Audio frame hop length
nfe_step = 32            # Number of flow estimation steps (quality vs speed)
fuse_nfe = 1             # Steps to fuse per iteration
max_chunk_duration = 15.0  # Maximum audio duration per chunk (seconds)
cross_fade_duration = 0.1  # Overlap duration between chunks (seconds)
```

---

## Directory Structure

```
VietVoice-TTS/
├── vietvoicetts/
│   ├── __init__.py          # Public API exports
│   ├── api.py                # High-level TTSApi class
│   ├── cli.py                # Command-line interface
│   └── core/
│       ├── tts_engine.py     # Main inference orchestration
│       ├── model.py          # ONNX session management
│       ├── model_config.py   # Configuration dataclass
│       ├── text_processor.py # Text cleaning & tokenization
│       └── audio_processor.py# Audio I/O & processing
├── gradio_app.py             # Web UI demo
├── basic_usage.py            # Usage examples
└── docs/
    └── architecture.md       # This file
```

---

## Inference Pipeline

### Complete Flow

```
Input Text → Clean Text → Chunk Text → For Each Chunk:
    ├── Load Reference Audio
    ├── Preprocess (ONNX)
    ├── Transformer × 32 iterations (ONNX)
    └── Decode (ONNX)
→ Concatenate with Cross-fade → Output WAV
```

### Detailed Steps

1. **Text Cleaning** (`text_processor.py`)
   - Keep: Vietnamese diacritics, English letters, digits, punctuation `.,!?'@$%&/:;()`
   - Normalize: `;:()` → `,`
   - Ensure ending punctuation

2. **Chunking** (`text_processor.py`)
   - Split by sentences (`.!?`), then by commas
   - Max ~135 characters per chunk
   - Each chunk produces ≤15 seconds of audio

3. **Preprocessing** (`tts_engine.py:_run_preprocess`)
   - Input shapes: `audio(1,1,N)`, `text_ids(1,seq_len)`, `max_duration(1,)`
   - Outputs: noise tensor, positional encodings, mel features

4. **Iterative Denoising** (`tts_engine.py:_run_transformer_steps`)
   - 32 NFE steps by default
   - Each step refines the noise tensor
   - Can reduce to 16 for 2x speed (slight quality loss)

5. **Decoding** (`tts_engine.py:_run_decode`)
   - Converts refined latent to 24kHz waveform

6. **Post-processing** (`audio_processor.py`)
   - Cross-fade chunks for smooth transitions
   - Normalize to prevent clipping

---

## Voice System

### Built-in Voices

The model includes pre-recorded reference samples with metadata:

| Attribute | Options |
|-----------|---------|
| Gender | `male`, `female` |
| Area/Accent | `northern`, `southern`, `central` |
| Group/Style | `story`, `news`, `audiobook`, `interview`, `review` |
| Emotion | `neutral`, `serious`, `monotone`, `sad`, `surprised`, `happy`, `angry` |

### Voice Selection

```python
# Use built-in voice with filters
audio, time = api.synthesize(
    text="Xin chào",
    gender="female",
    area="northern",
    emotion="happy"
)

# Voice cloning with custom reference
audio, time = api.synthesize(
    text="New text here",
    reference_audio="my_voice.wav",
    reference_text="Transcript of the reference audio"
)
```

---

## Python API

### Basic Usage

```python
from vietvoicetts import synthesize

# Simplest form
duration = synthesize("Xin chào các bạn!", "output.wav")

# With voice options
duration = synthesize(
    "Xin chào các bạn!",
    "output.wav",
    gender="female",
    area="northern",
    emotion="neutral",
    speed=1.0
)
```

### Advanced Usage with TTSApi

```python
from vietvoicetts import TTSApi, ModelConfig

# Custom configuration
config = ModelConfig(
    nfe_step=32,           # Quality (32=high, 16=fast)
    speed=1.0,             # Speaking rate multiplier
    max_chunk_duration=15.0,
    cross_fade_duration=0.1
)

# Context manager ensures cleanup
with TTSApi(config) as api:
    # Get numpy array + generation time
    audio_array, gen_time = api.synthesize(
        text="Text to synthesize",
        gender="female",
        output_path="output.wav"  # Optional: also save to file
    )

    # Get raw bytes (good for streaming/API responses)
    audio_bytes, gen_time = api.synthesize_to_bytes(
        text="Another text",
        emotion="happy"
    )

    # Just save to file
    gen_time = api.synthesize_to_file(
        text="Save directly",
        output_path="direct.wav"
    )
```

### Voice Cloning

```python
from vietvoicetts import synthesize

# Clone voice from reference audio
duration = synthesize(
    text="New content in cloned voice",
    output_path="cloned.wav",
    reference_audio="reference.wav",      # 3-10 seconds recommended
    reference_text="Exact transcript of reference audio"
)
```

---

## Command Line Interface

```bash
# Basic
vietvoice-tts "Xin chào các bạn!" output.wav

# With options
vietvoice-tts "Text here" output.wav \
    --gender female \
    --area northern \
    --emotion happy \
    --speed 1.2

# Voice cloning
vietvoice-tts "New text" output.wav \
    --reference-audio voice.wav \
    --reference-text "Transcript of voice.wav"

# Performance tuning
vietvoice-tts "Text" output.wav \
    --nfe-step 16 \
    --inter-op-threads 4 \
    --intra-op-threads 4
```

---

## ONNX Runtime Configuration

### GPU (CUDA) Setup

```python
# Automatically uses CUDA if available
# Priority: CUDAExecutionProvider → CPUExecutionProvider

# Check available providers
import onnxruntime as ort
print(ort.get_available_providers())
# ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

### Session Options

```python
config = ModelConfig(
    log_severity_level=4,      # 0=verbose, 4=error only
    inter_op_num_threads=0,    # 0=auto, or set specific count
    intra_op_num_threads=0,    # 0=auto, or set specific count
    enable_cpu_mem_arena=True  # Memory optimization
)
```

---

## Performance Characteristics

### Benchmarks (RTX 3090 Ti)

| Text Length | NFE Steps | Approx. Time | Audio Duration |
|-------------|-----------|--------------|----------------|
| 20 chars | 32 | ~0.5-1s | ~2s |
| 50 chars | 32 | ~1-2s | ~5s |
| 100 chars | 32 | ~2-3s | ~10s |
| 200+ chars | 32 | Chunked | Multiple chunks |

### Speed Optimization

```python
# Faster synthesis (slight quality reduction)
config = ModelConfig(nfe_step=16)  # Half the steps = ~2x faster

# Adjust speed
config = ModelConfig(speed=1.2)    # 20% faster speech
```

### Memory Usage

- Model size: ~500MB (3 ONNX models)
- VRAM usage: ~2-4GB during inference
- Scales with text length (chunked for long texts)

---

## Concurrency & Thread Safety

### Critical Warning

**ONNX Runtime inference is NOT thread-safe.** Sending multiple texts to the same session simultaneously will cause errors or corrupted output.

### Solutions

1. **Queue-based** (Single model, sequential processing)
2. **Worker pool** (Multiple model instances)
3. **Process-based** (Separate processes for isolation)

---

## FastAPI Server Implementation

### Simple Queue-Based Server

This approach uses a single model instance with an async queue for thread safety:

```python
# server.py
import asyncio
import io
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from vietvoicetts import TTSApi, ModelConfig


# Request/Response models
class TTSRequest(BaseModel):
    text: str
    gender: Optional[str] = None      # male, female
    area: Optional[str] = None        # northern, southern, central
    emotion: Optional[str] = None     # neutral, happy, sad, angry, etc.
    speed: float = 1.0

class TTSResponse(BaseModel):
    success: bool
    generation_time: float
    audio_duration: float
    message: str = ""


# Global state
class AppState:
    tts_api: TTSApi = None
    request_queue: asyncio.Queue = None
    worker_task: asyncio.Task = None

state = AppState()


async def process_queue():
    """Worker that processes TTS requests sequentially."""
    while True:
        try:
            request_data, future = await state.request_queue.get()

            # Run blocking synthesis in thread pool
            loop = asyncio.get_event_loop()
            audio_bytes, gen_time = await loop.run_in_executor(
                None,
                lambda: state.tts_api.synthesize_to_bytes(
                    text=request_data.text,
                    gender=request_data.gender,
                    area=request_data.area,
                    emotion=request_data.emotion,
                )
            )

            future.set_result((audio_bytes, gen_time))

        except asyncio.CancelledError:
            break
        except Exception as e:
            if not future.done():
                future.set_exception(e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    # Startup
    config = ModelConfig(
        nfe_step=32,          # Use 16 for faster synthesis
        speed=1.0,
        max_chunk_duration=15.0,
    )
    state.tts_api = TTSApi(config)
    state.request_queue = asyncio.Queue()
    state.worker_task = asyncio.create_task(process_queue())

    print("TTS Server ready!")
    yield

    # Shutdown
    state.worker_task.cancel()
    try:
        await state.worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="VietVoice-TTS API",
    description="Vietnamese Text-to-Speech API",
    version="1.0.0",
    lifespan=lifespan
)


@app.post("/synthesize", response_class=Response)
async def synthesize(req: TTSRequest):
    """
    Synthesize speech from text.
    Returns WAV audio file.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")

    if len(req.text) > 5000:
        raise HTTPException(400, "Text too long (max 5000 characters)")

    # Create future for this request
    loop = asyncio.get_event_loop()
    future = loop.create_future()

    # Add to queue
    await state.request_queue.put((req, future))

    try:
        # Wait for result with timeout
        audio_bytes, gen_time = await asyncio.wait_for(future, timeout=120.0)

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={
                "X-Generation-Time": f"{gen_time:.3f}",
                "X-Queue-Size": str(state.request_queue.qsize()),
            }
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "Synthesis timeout - text may be too long")
    except Exception as e:
        raise HTTPException(500, f"Synthesis failed: {str(e)}")


@app.post("/synthesize/stream")
async def synthesize_stream(req: TTSRequest):
    """
    Synthesize speech and stream the audio.
    Useful for large texts.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")

    loop = asyncio.get_event_loop()
    future = loop.create_future()
    await state.request_queue.put((req, future))

    try:
        audio_bytes, gen_time = await asyncio.wait_for(future, timeout=120.0)

        def audio_stream():
            chunk_size = 8192
            audio_io = io.BytesIO(audio_bytes)
            while chunk := audio_io.read(chunk_size):
                yield chunk

        return StreamingResponse(
            audio_stream(),
            media_type="audio/wav",
            headers={"X-Generation-Time": f"{gen_time:.3f}"}
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "Synthesis timeout")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "queue_size": state.request_queue.qsize(),
        "model_loaded": state.tts_api is not None
    }


@app.get("/voices")
async def list_voices():
    """List available voice options."""
    return {
        "gender": ["male", "female"],
        "area": ["northern", "southern", "central"],
        "emotion": ["neutral", "serious", "monotone", "sad", "surprised", "happy", "angry"],
        "group": ["story", "news", "audiobook", "interview", "review"]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Multi-Worker Server (Higher Throughput)

For more concurrent users, use multiple model instances:

```python
# server_multiworker.py
import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from contextlib import asynccontextmanager

from vietvoicetts import TTSApi, ModelConfig


class TTSRequest(BaseModel):
    text: str
    gender: Optional[str] = None
    area: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0


class WorkerPool:
    """Pool of TTS workers for concurrent processing."""

    def __init__(self, num_workers: int = 2):
        self.num_workers = num_workers
        self.workers: list[TTSApi] = []
        self.semaphores: list[asyncio.Semaphore] = []
        self.next_worker = 0

    def initialize(self, config: ModelConfig):
        """Initialize worker pool with model instances."""
        for i in range(self.num_workers):
            print(f"Loading TTS model for worker {i+1}/{self.num_workers}...")
            worker = TTSApi(config)
            self.workers.append(worker)
            self.semaphores.append(asyncio.Semaphore(1))
        print(f"Worker pool ready with {self.num_workers} workers")

    async def synthesize(self, req: TTSRequest) -> tuple[bytes, float]:
        """Get available worker and synthesize."""
        # Round-robin worker selection
        worker_idx = self.next_worker
        self.next_worker = (self.next_worker + 1) % self.num_workers

        # Wait for this worker to be available
        async with self.semaphores[worker_idx]:
            worker = self.workers[worker_idx]

            loop = asyncio.get_event_loop()
            audio_bytes, gen_time = await loop.run_in_executor(
                None,
                lambda: worker.synthesize_to_bytes(
                    text=req.text,
                    gender=req.gender,
                    area=req.area,
                    emotion=req.emotion,
                )
            )
            return audio_bytes, gen_time

    def get_status(self) -> dict:
        """Get worker pool status."""
        busy = sum(1 for s in self.semaphores if s.locked())
        return {
            "total_workers": self.num_workers,
            "busy_workers": busy,
            "available_workers": self.num_workers - busy
        }


# Configuration
NUM_WORKERS = 2  # Adjust based on GPU memory (each instance ~2-4GB)

pool = WorkerPool(num_workers=NUM_WORKERS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = ModelConfig(nfe_step=32)
    pool.initialize(config)
    yield


app = FastAPI(
    title="VietVoice-TTS API (Multi-Worker)",
    lifespan=lifespan
)


@app.post("/synthesize")
async def synthesize(req: TTSRequest):
    if not req.text.strip():
        raise HTTPException(400, "Text cannot be empty")

    try:
        audio_bytes, gen_time = await asyncio.wait_for(
            pool.synthesize(req),
            timeout=120.0
        )

        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            headers={"X-Generation-Time": f"{gen_time:.3f}"}
        )
    except asyncio.TimeoutError:
        raise HTTPException(408, "Synthesis timeout")
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/health")
async def health():
    return {"status": "healthy", **pool.get_status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Running the Server

```bash
# Install dependencies
pip install fastapi uvicorn

# Run single-worker server
python server.py

# Or with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1

# For production
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
```

### Client Examples

#### Python Client

```python
import requests

# Basic synthesis
response = requests.post(
    "http://localhost:8000/synthesize",
    json={
        "text": "Xin chào các bạn!",
        "gender": "female",
        "area": "northern"
    }
)

if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)
    print(f"Generated in {response.headers['X-Generation-Time']}s")
```

#### cURL

```bash
# Basic request
curl -X POST "http://localhost:8000/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Xin chào các bạn!", "gender": "female"}' \
  --output output.wav

# Check health
curl http://localhost:8000/health

# List voices
curl http://localhost:8000/voices
```

#### JavaScript/Fetch

```javascript
async function synthesize(text, options = {}) {
    const response = await fetch('http://localhost:8000/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, ...options })
    });

    if (!response.ok) {
        throw new Error(`Synthesis failed: ${response.status}`);
    }

    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    // Play audio
    const audio = new Audio(audioUrl);
    audio.play();

    return audioUrl;
}

// Usage
synthesize("Xin chào!", { gender: "female", emotion: "happy" });
```

---

## Capacity Planning

### For ~10 Users

| Concurrent Requests | Recommended Setup | Avg Wait Time |
|---------------------|-------------------|---------------|
| 1-3 | Single worker | 0-3s |
| 3-5 | Single worker | 3-10s |
| 5-10 | 2 workers | 2-5s |

### GPU Memory Requirements

| Workers | VRAM Usage | Recommended GPU |
|---------|------------|-----------------|
| 1 | ~3-4 GB | Any modern GPU |
| 2 | ~6-8 GB | RTX 3070+ |
| 3 | ~9-12 GB | RTX 3090/4080 |
| 4 | ~12-16 GB | RTX 3090 Ti/4090 |

---

## Troubleshooting

### Common Issues

1. **CUDA out of memory**
   - Reduce `num_workers`
   - Use `nfe_step=16` for smaller memory footprint

2. **Slow first request**
   - Model loading happens on first synthesis
   - Pre-warm with a test request on startup

3. **Garbled audio**
   - Check text encoding (UTF-8 required)
   - Ensure single request per session (thread safety)

4. **Long texts timeout**
   - Increase timeout in `wait_for()`
   - Consider chunking on client side

### Debug Logging

```python
config = ModelConfig(
    log_severity_level=0  # Verbose ONNX logging
)
```

---

## References

- [VietVoice-TTS on HuggingFace](https://huggingface.co/nguyenvulebinh/VietVoice-TTS)
- [ONNX Runtime Documentation](https://onnxruntime.ai/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
