"""TTS Worker - Processes jobs from Redis queue with persistent model."""
import os
import sys
import signal
import base64
import time
import uuid
import logging
from typing import Optional

# Add parent paths for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.redis_client import RedisClient
from shared.schemas import JobStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tts-worker")


class TTSWorker:
    """TTS Worker with persistent model loading.

    The model is loaded ONCE at startup and reused for all jobs.
    This avoids the ~4s model loading time per request.

    Workers can be configured for different quality levels:
    - "high": NFE=32, higher quality, slower (~3-5s per request)
    - "fast": NFE=16, faster generation (~1.5-2.5s per request)
    """

    # Quality presets
    QUALITY_PRESETS = {
        "high": 32,  # High quality
        "fast": 16,  # Fast generation
    }

    def __init__(
        self,
        worker_id: Optional[str] = None,
        redis_url: str = "redis://localhost:6379/0",
        quality: str = "high",
        nfe_steps: Optional[int] = None,
        heartbeat_interval: int = 30,
    ):
        """Initialize worker.

        Args:
            worker_id: Unique worker identifier (auto-generated if None)
            redis_url: Redis connection URL
            quality: Quality level ("high" or "fast")
            nfe_steps: Override NFE steps (uses quality preset if None)
            heartbeat_interval: Heartbeat interval in seconds
        """
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.redis_url = redis_url
        self.quality = quality if quality in self.QUALITY_PRESETS else "high"
        self.nfe_steps = nfe_steps or self.QUALITY_PRESETS[self.quality]
        self.heartbeat_interval = heartbeat_interval

        self.redis: Optional[RedisClient] = None
        self.tts_api = None  # Loaded once, reused forever
        self.running = False
        self.last_heartbeat = 0

        # Signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def _load_model(self):
        """Load TTS model (singleton - called once)."""
        logger.info("Loading TTS model (this may take a few seconds)...")

        from vietvoicetts import TTSApi, ModelConfig

        config = ModelConfig(
            nfe_step=self.nfe_steps,
            speed=1.0,
        )

        self.tts_api = TTSApi(config)
        logger.info("TTS model loaded successfully!")

    def _update_heartbeat(self):
        """Update worker heartbeat if interval elapsed."""
        now = time.time()
        if now - self.last_heartbeat >= self.heartbeat_interval:
            self.redis.register_worker(self.worker_id, self.quality)
            self.last_heartbeat = now

    def _process_job(self, job: dict) -> dict:
        """Process a single TTS job.

        Args:
            job: Job data dictionary

        Returns:
            Result dictionary
        """
        import tempfile
        from pathlib import Path

        job_id = job["job_id"]
        text = job["text"]
        reference_audio_b64 = job.get("reference_audio")
        reference_text = job.get("reference_text")

        logger.info(f"Processing job {job_id}: {len(text)} chars")
        if reference_audio_b64:
            logger.info(f"Voice cloning enabled for job {job_id}")
        start_time = time.time()

        # Handle reference audio (decode base64 to temp file if provided)
        ref_audio_path = None
        try:
            if reference_audio_b64 and reference_text:
                # Decode base64 audio and convert to WAV with silence trimming
                from pydub import AudioSegment
                from pydub.silence import detect_leading_silence
                import io

                ref_audio_bytes = base64.b64decode(reference_audio_b64)

                # Load audio (pydub auto-detects format: webm, wav, etc.)
                audio = AudioSegment.from_file(io.BytesIO(ref_audio_bytes))

                # Trim silence from start and end
                def trim_silence(audio_segment, silence_thresh=-40):
                    start_trim = detect_leading_silence(audio_segment, silence_threshold=silence_thresh)
                    end_trim = detect_leading_silence(audio_segment.reverse(), silence_threshold=silence_thresh)
                    duration = len(audio_segment)
                    return audio_segment[start_trim:duration - end_trim]

                audio = trim_silence(audio)
                logger.info(f"Trimmed audio duration: {len(audio)}ms")

                # Export as WAV to temp file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                    audio.export(tmp.name, format='wav')
                    ref_audio_path = tmp.name
                logger.info(f"Reference audio converted and saved to {ref_audio_path}")

            # Update status to processing
            self.redis.set_job_status(job_id, JobStatus.PROCESSING.value)

            # Synthesize
            audio_bytes, audio_duration = self.tts_api.synthesize_to_bytes(
                text=text,
                gender=job.get("gender"),
                area=job.get("area"),
                emotion=job.get("emotion"),
                reference_audio=ref_audio_path,
                reference_text=reference_text,
            )

            generation_time = time.time() - start_time

            # Encode audio to base64
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

            result = {
                "status": JobStatus.COMPLETED.value,
                "audio": audio_b64,
                "generation_time": round(generation_time, 3),
                "audio_duration": round(audio_duration, 3) if audio_duration else None,
                "completed_at": time.time(),
            }

            logger.info(
                f"Completed job {job_id}: "
                f"gen_time={generation_time:.2f}s, "
                f"audio_duration={audio_duration:.2f}s"
            )

            # Update metrics
            self.redis.increment_metric("jobs_completed")

            return result

        except Exception as e:
            logger.error(f"Failed job {job_id}: {e}")

            result = {
                "status": JobStatus.ERROR.value,
                "error": str(e),
                "error_code": type(e).__name__,
                "completed_at": time.time(),
            }

            # Update metrics
            self.redis.increment_metric("jobs_failed")

            return result

        finally:
            # Clean up temp reference audio file
            if ref_audio_path:
                Path(ref_audio_path).unlink(missing_ok=True)

    def run(self):
        """Main worker loop."""
        logger.info(f"Starting worker {self.worker_id}")

        # Connect to Redis
        self.redis = RedisClient(self.redis_url)
        if not self.redis.ping():
            raise RuntimeError("Cannot connect to Redis")
        logger.info(f"Connected to Redis: {self.redis_url}")

        # Load model ONCE
        self._load_model()

        # Register worker
        self.redis.register_worker(self.worker_id, self.quality)
        self.last_heartbeat = time.time()

        self.running = True
        logger.info(f"Worker {self.worker_id} ready (quality={self.quality}, nfe={self.nfe_steps}), waiting for jobs...")

        try:
            while self.running:
                # Update heartbeat
                self._update_heartbeat()

                # Get job from queue (blocking with timeout)
                job = self.redis.dequeue_job(quality=self.quality, timeout=5)

                if job is None:
                    # No job, continue loop (allows heartbeat updates)
                    continue

                # Process job
                result = self._process_job(job)

                # Store result
                self.redis.store_result(job["job_id"], result)

        except Exception as e:
            logger.error(f"Worker error: {e}")
            raise

        finally:
            # Cleanup
            logger.info(f"Shutting down worker {self.worker_id}")
            if self.redis:
                self.redis.unregister_worker(self.worker_id)
                self.redis.close()
            logger.info("Worker stopped")


def main():
    """Entry point."""
    worker_id = os.getenv("WORKER_ID")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    quality = os.getenv("QUALITY", "high")  # "high" or "fast"
    nfe_steps_env = os.getenv("NFE_STEPS")
    nfe_steps = int(nfe_steps_env) if nfe_steps_env else None  # Use quality preset if not specified
    heartbeat_interval = int(os.getenv("HEARTBEAT_INTERVAL", "30"))

    worker = TTSWorker(
        worker_id=worker_id,
        redis_url=redis_url,
        quality=quality,
        nfe_steps=nfe_steps,
        heartbeat_interval=heartbeat_interval,
    )

    worker.run()


if __name__ == "__main__":
    main()
