"""Shared schemas for TTS server."""
import base64
import time
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class TTSJob(BaseModel):
    """Job submitted to the TTS queue."""
    job_id: str
    text: str
    gender: Optional[str] = None
    area: Optional[str] = None
    emotion: Optional[str] = None
    speed: float = 1.0
    quality: str = "high"  # "high" or "fast"
    reference_audio: Optional[str] = None  # base64 encoded
    reference_text: Optional[str] = None
    trim_audio_to: Optional[float] = None  # trim reference audio to this duration (seconds)
    created_at: float = Field(default_factory=time.time)
    timeout: int = 120


class TTSResult(BaseModel):
    """Result of TTS synthesis."""
    status: JobStatus
    audio: Optional[str] = None  # base64 encoded WAV bytes
    generation_time: Optional[float] = None
    audio_duration: Optional[float] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    completed_at: float = Field(default_factory=time.time)

    def get_audio_bytes(self) -> Optional[bytes]:
        """Decode base64 audio to bytes."""
        if self.audio:
            return base64.b64decode(self.audio)
        return None


class TTSRequest(BaseModel):
    """API request for TTS synthesis."""
    text: str = Field(..., min_length=1, max_length=5000)
    gender: Optional[str] = Field(None, pattern="^(male|female)$")
    area: Optional[str] = Field(None, pattern="^(northern|southern|central)$")
    emotion: Optional[str] = Field(
        None,
        pattern="^(neutral|serious|monotone|sad|surprised|happy|angry)$"
    )
    speed: float = Field(1.0, ge=0.5, le=2.0)
    quality: str = Field("high", pattern="^(high|fast)$")  # "high" (NFE=32) or "fast" (NFE=16)
    reference_audio: Optional[str] = None  # base64 encoded audio for voice cloning
    reference_text: Optional[str] = None  # transcript of reference audio
    trim_audio_to: Optional[float] = Field(None, ge=1.0, le=60.0)  # trim reference audio to this duration (seconds)


class TTSAsyncResponse(BaseModel):
    """Response for async synthesis request."""
    job_id: str
    status: JobStatus
    queue_position: int
    estimated_wait: Optional[float] = None


class JobStatusResponse(BaseModel):
    """Response for job status query."""
    job_id: str
    status: JobStatus
    queue_position: Optional[int] = None
    audio_url: Optional[str] = None
    generation_time: Optional[float] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    queue_size: int
    queue_sizes: Optional[dict] = None  # {"high": N, "fast": M}
    workers: dict
    metrics: Optional[dict] = None


class VoicesResponse(BaseModel):
    """Available voice options."""
    gender: list[str]
    area: list[str]
    emotion: list[str]
    group: list[str]


# Voice Sample schemas
class VoiceSampleCreate(BaseModel):
    """Request to save a voice sample."""
    audio: str  # base64 encoded audio
    reference_text: str  # transcript of the audio
    name: Optional[str] = None  # optional name (if None, it's a "default" sample)


class VoiceSample(BaseModel):
    """A saved voice sample."""
    id: str
    name: Optional[str] = None
    reference_text: str
    created_at: float
    is_named: bool = False  # True if user gave it a name (permanent)


class VoiceSampleListResponse(BaseModel):
    """List of saved voice samples."""
    samples: list[VoiceSample]
