"""Redis client for TTS job queue management."""
import json
import time
from typing import Optional
import redis


class RedisClient:
    """Redis client for TTS job queue operations."""

    # Quality-based queue keys
    JOBS_QUEUE_HIGH = "tts:jobs:high"      # High quality (NFE=32)
    JOBS_QUEUE_FAST = "tts:jobs:fast"      # Fast generation (NFE=16)
    JOBS_QUEUE = "tts:jobs:high"           # Default (backward compat)

    # Key prefixes
    RESULT_PREFIX = "tts:result:"
    STATUS_PREFIX = "tts:status:"
    WORKER_PREFIX = "tts:worker:"
    METRICS_KEY = "tts:metrics"

    # Valid quality levels
    QUALITY_HIGH = "high"
    QUALITY_FAST = "fast"

    # TTLs
    RESULT_TTL = 300  # 5 minutes
    WORKER_HEARTBEAT_TTL = 60  # 1 minute

    def __init__(self, url: str = "redis://localhost:6379/0"):
        """Initialize Redis client.

        Args:
            url: Redis connection URL
        """
        self.redis = redis.from_url(url, decode_responses=True)
        self._bytes_redis = redis.from_url(url, decode_responses=False)

    def _get_queue_key(self, quality: str) -> str:
        """Get queue key for quality level."""
        if quality == self.QUALITY_FAST:
            return self.JOBS_QUEUE_FAST
        return self.JOBS_QUEUE_HIGH  # Default to high quality

    def enqueue_job(self, job_data: dict, quality: str = "high") -> None:
        """Add a job to the appropriate quality queue.

        Args:
            job_data: Job data dictionary
            quality: Quality level ("high" or "fast")
        """
        job_json = json.dumps(job_data)
        queue_key = self._get_queue_key(quality)
        self.redis.lpush(queue_key, job_json)
        self.redis.set(
            f"{self.STATUS_PREFIX}{job_data['job_id']}",
            "pending",
            ex=self.RESULT_TTL
        )

    def dequeue_job(self, quality: str = "high", timeout: int = 5) -> Optional[dict]:
        """Get next job from quality-specific queue (blocking).

        Args:
            quality: Quality level to listen to ("high" or "fast")
            timeout: Blocking timeout in seconds

        Returns:
            Job data dict or None if timeout
        """
        queue_key = self._get_queue_key(quality)
        result = self.redis.brpop(queue_key, timeout=timeout)
        if result:
            _, job_json = result
            return json.loads(job_json)
        return None

    def set_job_status(self, job_id: str, status: str) -> None:
        """Update job status.

        Args:
            job_id: Job identifier
            status: Status string (pending, processing, completed, error)
        """
        self.redis.set(
            f"{self.STATUS_PREFIX}{job_id}",
            status,
            ex=self.RESULT_TTL
        )

    def get_job_status(self, job_id: str) -> Optional[str]:
        """Get job status.

        Args:
            job_id: Job identifier

        Returns:
            Status string or None if not found
        """
        return self.redis.get(f"{self.STATUS_PREFIX}{job_id}")

    def store_result(self, job_id: str, result_data: dict) -> None:
        """Store job result.

        Args:
            job_id: Job identifier
            result_data: Result data dictionary
        """
        result_json = json.dumps(result_data)
        self.redis.set(
            f"{self.RESULT_PREFIX}{job_id}",
            result_json,
            ex=self.RESULT_TTL
        )
        self.redis.set(
            f"{self.STATUS_PREFIX}{job_id}",
            result_data.get("status", "completed"),
            ex=self.RESULT_TTL
        )

    def get_result(self, job_id: str) -> Optional[dict]:
        """Get job result.

        Args:
            job_id: Job identifier

        Returns:
            Result dict or None if not found
        """
        result_json = self.redis.get(f"{self.RESULT_PREFIX}{job_id}")
        if result_json:
            return json.loads(result_json)
        return None

    def wait_for_result(self, job_id: str, timeout: float = 120.0, poll_interval: float = 0.1) -> Optional[dict]:
        """Wait for job result (polling).

        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Result dict or None if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            result = self.get_result(job_id)
            if result:
                return result
            time.sleep(poll_interval)
        return None

    def get_queue_size(self, quality: str = None) -> int:
        """Get number of jobs in queue.

        Args:
            quality: If specified, get size for that quality queue.
                     If None, return total across all queues.
        """
        if quality:
            return self.redis.llen(self._get_queue_key(quality))
        # Return total
        return (
            self.redis.llen(self.JOBS_QUEUE_HIGH) +
            self.redis.llen(self.JOBS_QUEUE_FAST)
        )

    def get_queue_sizes(self) -> dict:
        """Get sizes for all quality queues."""
        return {
            "high": self.redis.llen(self.JOBS_QUEUE_HIGH),
            "fast": self.redis.llen(self.JOBS_QUEUE_FAST),
        }

    def get_queue_position(self, job_id: str, quality: str = "high") -> int:
        """Get position of job in queue (approximate).

        Args:
            job_id: Job identifier
            quality: Quality queue to check

        Returns:
            Position (0 = next to be processed) or -1 if not in queue
        """
        queue_key = self._get_queue_key(quality)
        jobs = self.redis.lrange(queue_key, 0, -1)
        for i, job_json in enumerate(reversed(jobs)):  # Queue is LIFO with BRPOP
            job = json.loads(job_json)
            if job.get("job_id") == job_id:
                return i
        return -1

    def register_worker(self, worker_id: str, quality: str = "high") -> None:
        """Register worker heartbeat with quality info.

        Args:
            worker_id: Worker identifier
            quality: Quality level this worker handles
        """
        worker_data = json.dumps({
            "timestamp": time.time(),
            "quality": quality,
        })
        self.redis.set(
            f"{self.WORKER_PREFIX}{worker_id}",
            worker_data,
            ex=self.WORKER_HEARTBEAT_TTL
        )

    def unregister_worker(self, worker_id: str) -> None:
        """Remove worker registration.

        Args:
            worker_id: Worker identifier
        """
        self.redis.delete(f"{self.WORKER_PREFIX}{worker_id}")

    def get_active_workers(self) -> list[str]:
        """Get list of active worker IDs."""
        workers = []
        for key in self.redis.scan_iter(f"{self.WORKER_PREFIX}*"):
            worker_id = key.replace(self.WORKER_PREFIX, "")
            workers.append(worker_id)
        return workers

    def get_workers_by_quality(self) -> dict:
        """Get workers grouped by quality level."""
        workers = {"high": [], "fast": []}
        for key in self.redis.scan_iter(f"{self.WORKER_PREFIX}*"):
            worker_id = key.replace(self.WORKER_PREFIX, "")
            worker_data = self.redis.get(key)
            try:
                data = json.loads(worker_data)
                # Handle both old format (just timestamp) and new format (dict with quality)
                if isinstance(data, dict):
                    quality = data.get("quality", "high")
                else:
                    # Old format - just a timestamp number
                    quality = "high"
                workers[quality].append(worker_id)
            except (json.JSONDecodeError, TypeError):
                # Fallback for unparseable data
                workers["high"].append(worker_id)
        return workers

    def increment_metric(self, metric: str, amount: int = 1) -> None:
        """Increment a metric counter.

        Args:
            metric: Metric name (e.g., "jobs_completed")
            amount: Amount to increment
        """
        self.redis.hincrby(self.METRICS_KEY, metric, amount)

    def get_metrics(self) -> dict:
        """Get all metrics."""
        metrics = self.redis.hgetall(self.METRICS_KEY)
        return {k: int(v) for k, v in metrics.items()}

    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self.redis.ping()
        except Exception:
            return False

    def close(self) -> None:
        """Close Redis connections."""
        self.redis.close()
        self._bytes_redis.close()
