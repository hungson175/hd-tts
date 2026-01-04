"""FastAPI Gateway for VietVoice TTS API."""
import os
import uuid
import asyncio
import json
import base64
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.redis_client import RedisClient
from shared.auth import APIKeyManager, APIKeyInfo, is_localhost_request
from shared.schemas import (
    TTSRequest,
    TTSAsyncResponse,
    JobStatusResponse,
    HealthResponse,
    VoicesResponse,
    JobStatus,
    TTSJob,
    VoiceSampleCreate,
    VoiceSample,
    VoiceSampleListResponse,
)


# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
JOB_TIMEOUT = int(os.getenv("JOB_TIMEOUT", "120"))
AVG_GENERATION_TIME = 3.0  # seconds, for estimation

# Voice samples storage
VOICE_SAMPLES_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "voice_samples"
VOICE_SAMPLES_METADATA = VOICE_SAMPLES_DIR / "metadata.json"
MAX_DEFAULT_SAMPLES = 3  # Max unnamed samples to keep


# Global state
class AppState:
    redis: Optional[RedisClient] = None
    key_manager: Optional[APIKeyManager] = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    state.redis = RedisClient(REDIS_URL)
    if not state.redis.ping():
        raise RuntimeError("Cannot connect to Redis")
    print(f"Connected to Redis: {REDIS_URL}")

    # Initialize API key manager
    state.key_manager = APIKeyManager(state.redis)
    print("API key authentication enabled (localhost bypass active)")

    yield
    # Shutdown
    if state.redis:
        state.redis.close()


app = FastAPI(
    title="VietVoice TTS API",
    description="Vietnamese Text-to-Speech API with Redis queue backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from fastapi import Header, Query, Request


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key: Optional[str] = Query(None),
) -> Optional[APIKeyInfo]:
    """Verify API key - bypasses for localhost requests."""
    # Bypass for localhost
    if is_localhost_request(request):
        return None

    # Get key from header or query param
    key = x_api_key or api_key
    if not key:
        raise HTTPException(
            status_code=401,
            detail="API key required. Provide via X-API-Key header or api_key query parameter.",
        )

    # Validate key
    key_info = state.key_manager.validate_key(key)
    if not key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key.",
        )

    return key_info


@app.post("/synthesize", response_class=Response)
async def synthesize(
    req: TTSRequest,
    api_key_info: Optional[APIKeyInfo] = Depends(verify_api_key),
):
    """
    Synthesize speech from text (synchronous).

    Waits for result and returns WAV audio directly.
    Requires API key for external requests (localhost bypassed).
    """
    job_id = str(uuid.uuid4())

    # Create job
    job = TTSJob(
        job_id=job_id,
        text=req.text,
        gender=req.gender,
        area=req.area,
        emotion=req.emotion,
        speed=req.speed,
        quality=req.quality,
        reference_audio=req.reference_audio,
        reference_text=req.reference_text,
        trim_audio_to=req.trim_audio_to,
        timeout=JOB_TIMEOUT,
    )

    # Enqueue to appropriate quality queue
    state.redis.enqueue_job(job.model_dump(), quality=req.quality)
    queue_position = state.redis.get_queue_size(quality=req.quality)

    # Wait for result in thread pool (non-blocking for other requests)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: state.redis.wait_for_result(job_id, timeout=JOB_TIMEOUT)
    )

    if result is None:
        raise HTTPException(408, "Synthesis timeout - try again later")

    if result.get("status") == "error":
        raise HTTPException(500, result.get("error", "Synthesis failed"))

    # Decode audio
    import base64
    audio_bytes = base64.b64decode(result["audio"])

    # Track usage for API key users
    if api_key_info:
        audio_duration = result.get("audio_duration", 0.0)
        state.key_manager.increment_usage(api_key_info.key_id, audio_duration)

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Job-Id": job_id,
            "X-Generation-Time": str(result.get("generation_time", 0)),
            "X-Audio-Duration": str(result.get("audio_duration", 0)),
            "X-Queue-Position": str(queue_position),
        }
    )


@app.post("/synthesize/async", response_model=TTSAsyncResponse)
async def synthesize_async(
    req: TTSRequest,
    api_key_info: Optional[APIKeyInfo] = Depends(verify_api_key),
):
    """
    Submit synthesis job (asynchronous).

    Returns job_id immediately. Poll /job/{job_id} for result.
    Requires API key for external requests (localhost bypassed).
    """
    job_id = str(uuid.uuid4())

    # Create job
    job = TTSJob(
        job_id=job_id,
        text=req.text,
        gender=req.gender,
        area=req.area,
        emotion=req.emotion,
        speed=req.speed,
        quality=req.quality,
        reference_audio=req.reference_audio,
        reference_text=req.reference_text,
        trim_audio_to=req.trim_audio_to,
        timeout=JOB_TIMEOUT,
    )

    # Enqueue to appropriate quality queue
    state.redis.enqueue_job(job.model_dump(), quality=req.quality)
    queue_position = state.redis.get_queue_size(quality=req.quality)

    # Estimate wait time
    workers = len(state.redis.get_active_workers())
    if workers > 0:
        estimated_wait = (queue_position / workers) * AVG_GENERATION_TIME
    else:
        estimated_wait = None

    # Track usage for API key users (request count only, audio tracked on download)
    if api_key_info:
        state.key_manager.increment_usage(api_key_info.key_id, audio_seconds=0.0)

    return TTSAsyncResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        queue_position=queue_position,
        estimated_wait=estimated_wait,
    )


@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    api_key_info: Optional[APIKeyInfo] = Depends(verify_api_key),
):
    """Get job status and result. Requires API key for external requests."""
    status = state.redis.get_job_status(job_id)
    if status is None:
        raise HTTPException(404, "Job not found")

    result = state.redis.get_result(job_id)

    response = JobStatusResponse(
        job_id=job_id,
        status=JobStatus(status),
    )

    if status == "pending":
        response.queue_position = state.redis.get_queue_position(job_id)
    elif status == "completed" and result:
        response.audio_url = f"/job/{job_id}/audio"
        response.generation_time = result.get("generation_time")
    elif status == "error" and result:
        response.error = result.get("error")

    return response


@app.get("/job/{job_id}/audio", response_class=Response)
async def get_job_audio(
    job_id: str,
    api_key_info: Optional[APIKeyInfo] = Depends(verify_api_key),
):
    """Download audio for completed job. Requires API key for external requests."""
    result = state.redis.get_result(job_id)
    if result is None:
        raise HTTPException(404, "Job not found or expired")

    if result.get("status") != "completed":
        raise HTTPException(400, f"Job status is {result.get('status')}, not completed")

    import base64
    audio_bytes = base64.b64decode(result["audio"])

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f"attachment; filename={job_id}.wav",
            "X-Generation-Time": str(result.get("generation_time", 0)),
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check with system status."""
    workers_by_quality = state.redis.get_workers_by_quality()
    all_workers = state.redis.get_active_workers()
    metrics = state.redis.get_metrics()
    queue_sizes = state.redis.get_queue_sizes()

    return HealthResponse(
        status="healthy" if state.redis.ping() else "unhealthy",
        queue_size=state.redis.get_queue_size(),
        workers={
            "active": len(all_workers),
            "ids": all_workers,
            "by_quality": workers_by_quality,
        },
        metrics=metrics if metrics else None,
        queue_sizes=queue_sizes,
    )


@app.get("/voices", response_model=VoicesResponse)
async def list_voices():
    """List available voice options."""
    return VoicesResponse(
        gender=["male", "female"],
        area=["northern", "southern", "central"],
        emotion=["neutral", "serious", "monotone", "sad", "surprised", "happy", "angry"],
        group=["story", "news", "audiobook", "interview", "review"],
    )


# ============ Voice Samples API ============

def _ensure_samples_dir():
    """Ensure voice samples directory exists."""
    VOICE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    if not VOICE_SAMPLES_METADATA.exists():
        VOICE_SAMPLES_METADATA.write_text("[]")


def _load_samples_metadata() -> list[dict]:
    """Load voice samples metadata."""
    _ensure_samples_dir()
    try:
        return json.loads(VOICE_SAMPLES_METADATA.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_samples_metadata(samples: list[dict]):
    """Save voice samples metadata."""
    _ensure_samples_dir()
    VOICE_SAMPLES_METADATA.write_text(json.dumps(samples, indent=2))


def _cleanup_old_default_samples(samples: list[dict]) -> list[dict]:
    """Remove oldest default samples if over limit."""
    default_samples = [s for s in samples if not s.get("is_named")]
    named_samples = [s for s in samples if s.get("is_named")]

    # Sort by created_at (oldest first)
    default_samples.sort(key=lambda x: x.get("created_at", 0))

    # Remove oldest if over limit
    while len(default_samples) > MAX_DEFAULT_SAMPLES:
        old = default_samples.pop(0)
        # Delete audio file
        audio_path = VOICE_SAMPLES_DIR / f"{old['id']}.wav"
        audio_path.unlink(missing_ok=True)

    return named_samples + default_samples


@app.post("/voice-samples", response_model=VoiceSample)
async def save_voice_sample(req: VoiceSampleCreate):
    """Save a voice sample for reuse."""
    from pydub import AudioSegment
    from pydub.silence import detect_leading_silence
    import io

    sample_id = str(uuid.uuid4())[:8]
    is_named = bool(req.name and req.name.strip())

    # Decode and process audio (trim silence, convert to WAV)
    try:
        audio_bytes = base64.b64decode(req.audio)
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))

        # Trim silence
        def trim_silence(seg, thresh=-40):
            start = detect_leading_silence(seg, silence_threshold=thresh)
            end = detect_leading_silence(seg.reverse(), silence_threshold=thresh)
            return seg[start:len(seg) - end]

        audio = trim_silence(audio)

        # Save as WAV
        _ensure_samples_dir()
        audio_path = VOICE_SAMPLES_DIR / f"{sample_id}.wav"
        audio.export(str(audio_path), format="wav")
    except Exception as e:
        raise HTTPException(400, f"Invalid audio data: {e}")

    # Create sample metadata
    sample = {
        "id": sample_id,
        "name": req.name.strip() if req.name else None,
        "reference_text": req.reference_text,
        "created_at": time.time(),
        "is_named": is_named,
    }

    # Load existing, add new, cleanup old defaults
    samples = _load_samples_metadata()
    samples.append(sample)
    samples = _cleanup_old_default_samples(samples)
    _save_samples_metadata(samples)

    return VoiceSample(**sample)


@app.get("/voice-samples", response_model=VoiceSampleListResponse)
async def list_voice_samples():
    """List all saved voice samples."""
    samples = _load_samples_metadata()
    # Sort: named first, then by created_at desc
    samples.sort(key=lambda x: (not x.get("is_named"), -x.get("created_at", 0)))
    return VoiceSampleListResponse(samples=[VoiceSample(**s) for s in samples])


@app.get("/voice-samples/{sample_id}/audio", response_class=Response)
async def get_voice_sample_audio(sample_id: str):
    """Get audio file for a voice sample (base64 encoded)."""
    samples = _load_samples_metadata()
    sample = next((s for s in samples if s["id"] == sample_id), None)
    if not sample:
        raise HTTPException(404, "Voice sample not found")

    audio_path = VOICE_SAMPLES_DIR / f"{sample_id}.wav"
    if not audio_path.exists():
        raise HTTPException(404, "Audio file not found")

    audio_bytes = audio_path.read_bytes()
    audio_b64 = base64.b64encode(audio_bytes).decode()

    return Response(
        content=json.dumps({"audio": audio_b64, "reference_text": sample["reference_text"]}),
        media_type="application/json"
    )


@app.delete("/voice-samples/{sample_id}")
async def delete_voice_sample(sample_id: str):
    """Delete a voice sample."""
    samples = _load_samples_metadata()
    sample = next((s for s in samples if s["id"] == sample_id), None)
    if not sample:
        raise HTTPException(404, "Voice sample not found")

    # Remove from list
    samples = [s for s in samples if s["id"] != sample_id]
    _save_samples_metadata(samples)

    # Delete audio file
    audio_path = VOICE_SAMPLES_DIR / f"{sample_id}.wav"
    audio_path.unlink(missing_ok=True)

    return {"status": "deleted", "id": sample_id}


@app.get("/")
async def root():
    """API info."""
    return {
        "name": "VietVoice TTS API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
