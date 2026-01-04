"""Unit tests for FastAPI gateway endpoints."""
import pytest
import json
import base64
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def mock_localhost_bypass():
    """Mock localhost check to always return True for tests."""
    with patch('gateway.main.is_localhost_request', return_value=True):
        yield


@pytest.fixture(autouse=True)
def mock_redis():
    """Mock Redis client for all tests."""
    with patch('gateway.main.RedisClient') as mock_redis_class:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.redis = MagicMock()
        mock_redis_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def client(mock_redis):
    """Create test client with mocked Redis."""
    from gateway.main import app, state
    state.redis = mock_redis

    # Mock key manager
    mock_key_manager = MagicMock()
    state.key_manager = mock_key_manager

    return TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "VietVoice TTS API"
        assert "version" in data
        assert data["docs"] == "/docs"


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_healthy_status(self, client, mock_redis):
        mock_redis.ping.return_value = True
        mock_redis.get_workers_by_quality.return_value = {"high": ["worker-1"], "fast": []}
        mock_redis.get_active_workers.return_value = ["worker-1"]
        mock_redis.get_metrics.return_value = {"jobs_completed": 10}
        mock_redis.get_queue_sizes.return_value = {"high": 0, "fast": 0}
        mock_redis.get_queue_size.return_value = 0

        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "workers" in data
        assert "queue_size" in data

    def test_health_shows_worker_count(self, client, mock_redis):
        mock_redis.ping.return_value = True
        mock_redis.get_workers_by_quality.return_value = {"high": ["w1", "w2"], "fast": ["w3"]}
        mock_redis.get_active_workers.return_value = ["w1", "w2", "w3"]
        mock_redis.get_metrics.return_value = {}
        mock_redis.get_queue_sizes.return_value = {"high": 5, "fast": 2}
        mock_redis.get_queue_size.return_value = 7

        response = client.get("/health")
        data = response.json()
        assert data["workers"]["active"] == 3
        assert data["queue_size"] == 7


class TestVoicesEndpoint:
    """Tests for /voices endpoint."""

    def test_voices_returns_all_options(self, client):
        response = client.get("/voices")
        assert response.status_code == 200
        data = response.json()

        assert "male" in data["gender"]
        assert "female" in data["gender"]
        assert "northern" in data["area"]
        assert "southern" in data["area"]
        assert "neutral" in data["emotion"]


class TestSynthesizeEndpoint:
    """Tests for /synthesize endpoint."""

    def test_synthesize_returns_audio(self, client, mock_redis):
        # Mock successful job completion
        audio_data = b"RIFF....WAVEfmt fake audio data"
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.wait_for_result.return_value = {
            "status": "completed",
            "audio": base64.b64encode(audio_data).decode(),
            "generation_time": 2.5,
            "audio_duration": 3.0,
        }

        response = client.post("/synthesize", json={
            "text": "Xin chào",
            "gender": "female",
            "area": "northern",
        })

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert "X-Job-Id" in response.headers

    def test_synthesize_timeout_returns_408(self, client, mock_redis):
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.wait_for_result.return_value = None  # Timeout

        response = client.post("/synthesize", json={
            "text": "Test",
            "gender": "male",
            "area": "southern",
        })

        assert response.status_code == 408
        assert "timeout" in response.json()["detail"].lower()

    def test_synthesize_error_returns_500(self, client, mock_redis):
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.wait_for_result.return_value = {
            "status": "error",
            "error": "Model failed to generate",
        }

        response = client.post("/synthesize", json={
            "text": "Test",
            "gender": "female",
            "area": "northern",
        })

        assert response.status_code == 500

    def test_synthesize_tracks_api_key_usage(self, client, mock_redis):
        """Test that API key usage is tracked for authenticated requests."""
        from gateway.main import state
        from shared.auth import APIKeyInfo

        # Setup mock key info
        mock_key_info = APIKeyInfo(
            key_id="test1234",
            name="Test User",
            created_at=1234567890.0,
        )

        audio_data = b"fake audio"
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.wait_for_result.return_value = {
            "status": "completed",
            "audio": base64.b64encode(audio_data).decode(),
            "generation_time": 1.0,
            "audio_duration": 2.5,
        }

        # The test client runs from localhost, so auth is bypassed
        # We test the tracking logic separately
        response = client.post("/synthesize", json={
            "text": "Test",
            "gender": "female",
            "area": "northern",
        })
        assert response.status_code == 200


class TestSynthesizeAsyncEndpoint:
    """Tests for /synthesize/async endpoint."""

    def test_async_returns_job_id(self, client, mock_redis):
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 3
        mock_redis.get_active_workers.return_value = ["w1", "w2"]

        response = client.post("/synthesize/async", json={
            "text": "Hello world",
            "gender": "male",
            "area": "central",
        })

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["queue_position"] == 3

    def test_async_estimates_wait_time(self, client, mock_redis):
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 6
        mock_redis.get_active_workers.return_value = ["w1", "w2"]  # 2 workers

        response = client.post("/synthesize/async", json={
            "text": "Test",
            "gender": "female",
            "area": "northern",
        })

        data = response.json()
        # With 6 jobs and 2 workers, estimated wait should be calculated
        assert data["estimated_wait"] is not None

    def test_async_no_workers_no_estimate(self, client, mock_redis):
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 5
        mock_redis.get_active_workers.return_value = []  # No workers

        response = client.post("/synthesize/async", json={
            "text": "Test",
            "gender": "female",
            "area": "northern",
        })

        data = response.json()
        assert data["estimated_wait"] is None


class TestJobStatusEndpoint:
    """Tests for /job/{job_id} endpoint."""

    def test_get_pending_job_status(self, client, mock_redis):
        mock_redis.get_job_status.return_value = "pending"
        mock_redis.get_result.return_value = None
        mock_redis.get_queue_position.return_value = 2

        response = client.get("/job/test-job-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["queue_position"] == 2

    def test_get_completed_job_status(self, client, mock_redis):
        mock_redis.get_job_status.return_value = "completed"
        mock_redis.get_result.return_value = {
            "status": "completed",
            "generation_time": 3.5,
        }

        response = client.get("/job/test-job-456")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["audio_url"] == "/job/test-job-456/audio"
        assert data["generation_time"] == 3.5

    def test_get_error_job_status(self, client, mock_redis):
        mock_redis.get_job_status.return_value = "error"
        mock_redis.get_result.return_value = {
            "status": "error",
            "error": "GPU out of memory",
        }

        response = client.get("/job/test-job-789")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error"] == "GPU out of memory"

    def test_get_nonexistent_job_returns_404(self, client, mock_redis):
        mock_redis.get_job_status.return_value = None

        response = client.get("/job/nonexistent-job")
        assert response.status_code == 404


class TestJobAudioEndpoint:
    """Tests for /job/{job_id}/audio endpoint."""

    def test_download_completed_audio(self, client, mock_redis):
        audio_data = b"RIFF....WAVEfmt real audio content here"
        mock_redis.get_result.return_value = {
            "status": "completed",
            "audio": base64.b64encode(audio_data).decode(),
            "generation_time": 2.0,
        }

        response = client.get("/job/test-job-audio/audio")
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert response.content == audio_data

    def test_download_nonexistent_job_returns_404(self, client, mock_redis):
        mock_redis.get_result.return_value = None

        response = client.get("/job/nonexistent/audio")
        assert response.status_code == 404

    def test_download_incomplete_job_returns_400(self, client, mock_redis):
        mock_redis.get_result.return_value = {
            "status": "processing",
        }

        response = client.get("/job/processing-job/audio")
        assert response.status_code == 400
        assert "not completed" in response.json()["detail"]


class TestVoiceSamplesEndpoints:
    """Tests for voice samples CRUD endpoints."""

    @pytest.fixture
    def mock_audio_processing(self):
        """Mock pydub audio processing."""
        with patch.dict('sys.modules', {'pydub': MagicMock(), 'pydub.silence': MagicMock()}):
            with patch('pydub.AudioSegment') as mock_audio:
                mock_segment = MagicMock()
                mock_segment.reverse.return_value = mock_segment
                mock_segment.__getitem__ = lambda self, key: mock_segment
                mock_segment.__len__ = lambda self: 10000
                mock_segment.export = MagicMock()
                mock_audio.from_file.return_value = mock_segment
                yield mock_audio

    @pytest.fixture
    def mock_samples_storage(self, tmp_path):
        """Mock voice samples directory."""
        with patch('gateway.main.VOICE_SAMPLES_DIR', tmp_path):
            with patch('gateway.main.VOICE_SAMPLES_METADATA', tmp_path / "metadata.json"):
                (tmp_path / "metadata.json").write_text("[]")
                yield tmp_path

    def test_list_empty_samples(self, client, mock_samples_storage):
        response = client.get("/voice-samples")
        assert response.status_code == 200
        assert response.json()["samples"] == []

    def test_save_voice_sample_invalid_audio(self, client, mock_samples_storage):
        """Test that invalid audio returns 400."""
        audio_b64 = base64.b64encode(b"not valid audio").decode()
        response = client.post("/voice-samples", json={
            "audio": audio_b64,
            "reference_text": "Hello world",
            "name": "Test Sample",
        })
        # Should fail with invalid audio
        assert response.status_code == 400

    def test_delete_voice_sample(self, client, mock_samples_storage):
        # First create metadata with a sample
        sample_data = [{
            "id": "test1234",
            "name": "Test",
            "reference_text": "Hello",
            "created_at": 1234567890.0,
            "is_named": True,
        }]
        (mock_samples_storage / "metadata.json").write_text(json.dumps(sample_data))
        (mock_samples_storage / "test1234.wav").write_bytes(b"audio")

        response = client.delete("/voice-samples/test1234")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_nonexistent_sample_returns_404(self, client, mock_samples_storage):
        response = client.delete("/voice-samples/nonexistent")
        assert response.status_code == 404

    def test_get_sample_audio(self, client, mock_samples_storage):
        # Setup sample
        sample_data = [{
            "id": "audio123",
            "name": "Test",
            "reference_text": "Test text",
            "created_at": 1234567890.0,
            "is_named": True,
        }]
        (mock_samples_storage / "metadata.json").write_text(json.dumps(sample_data))
        (mock_samples_storage / "audio123.wav").write_bytes(b"audio content")

        response = client.get("/voice-samples/audio123/audio")
        assert response.status_code == 200
        data = response.json()
        assert "audio" in data
        assert data["reference_text"] == "Test text"


class TestAuthBypass:
    """Tests for localhost auth bypass."""

    def test_localhost_bypasses_auth(self, client, mock_redis):
        """Localhost requests should bypass API key requirement."""
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.get_active_workers.return_value = ["w1"]

        # TestClient simulates localhost - should not require API key
        response = client.post("/synthesize/async", json={
            "text": "Test without API key",
            "gender": "female",
            "area": "northern",
        })

        # Should succeed without API key (localhost bypass)
        assert response.status_code == 200


class TestExternalAuth:
    """Tests for external (non-localhost) auth."""

    @pytest.fixture(autouse=True)
    def disable_localhost_bypass(self):
        """Disable localhost bypass for these tests."""
        with patch('gateway.main.is_localhost_request', return_value=False):
            yield

    def test_external_request_requires_api_key(self, client, mock_redis):
        """External requests should require API key."""
        response = client.post("/synthesize/async", json={
            "text": "Test",
            "gender": "female",
            "area": "northern",
        })
        assert response.status_code == 401
        assert "API key required" in response.json()["detail"]

    def test_external_request_invalid_key_rejected(self, client, mock_redis):
        """Invalid API key should be rejected."""
        from gateway.main import state
        state.key_manager.validate_key.return_value = None

        response = client.post(
            "/synthesize/async",
            json={"text": "Test", "gender": "female", "area": "northern"},
            headers={"X-API-Key": "vvtts_invalid_key_12345678901234"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_external_request_valid_key_accepted(self, client, mock_redis):
        """Valid API key should be accepted."""
        from gateway.main import state
        from shared.auth import APIKeyInfo

        mock_key_info = APIKeyInfo(
            key_id="test1234",
            name="Test User",
            created_at=1234567890.0,
        )
        state.key_manager.validate_key.return_value = mock_key_info

        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.get_active_workers.return_value = ["w1"]

        response = client.post(
            "/synthesize/async",
            json={"text": "Test", "gender": "female", "area": "northern"},
            headers={"X-API-Key": "vvtts_valid_key_1234567890123456"}
        )
        assert response.status_code == 200

    def test_api_key_via_query_param(self, client, mock_redis):
        """API key can be provided via query parameter."""
        from gateway.main import state
        from shared.auth import APIKeyInfo

        mock_key_info = APIKeyInfo(
            key_id="test1234",
            name="Test User",
            created_at=1234567890.0,
        )
        state.key_manager.validate_key.return_value = mock_key_info

        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.get_active_workers.return_value = ["w1"]

        response = client.post(
            "/synthesize/async?api_key=vvtts_valid_key_1234567890123456",
            json={"text": "Test", "gender": "female", "area": "northern"},
        )
        assert response.status_code == 200


class TestUsageTracking:
    """Tests for API key usage tracking."""

    @pytest.fixture(autouse=True)
    def disable_localhost_bypass(self):
        """Disable localhost bypass for these tests."""
        with patch('gateway.main.is_localhost_request', return_value=False):
            yield

    def test_sync_synthesize_tracks_usage(self, client, mock_redis):
        """Sync synthesize should track audio duration for API key users."""
        from gateway.main import state
        from shared.auth import APIKeyInfo

        mock_key_info = APIKeyInfo(
            key_id="track123",
            name="Usage Test",
            created_at=1234567890.0,
        )
        state.key_manager.validate_key.return_value = mock_key_info

        audio_data = b"fake audio"
        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.wait_for_result.return_value = {
            "status": "completed",
            "audio": base64.b64encode(audio_data).decode(),
            "generation_time": 1.0,
            "audio_duration": 5.5,
        }

        response = client.post(
            "/synthesize",
            json={"text": "Test", "gender": "female", "area": "northern"},
            headers={"X-API-Key": "vvtts_valid_key_1234567890123456"}
        )

        assert response.status_code == 200
        # Verify usage was tracked
        state.key_manager.increment_usage.assert_called_once_with("track123", 5.5)

    def test_async_synthesize_tracks_request(self, client, mock_redis):
        """Async synthesize should track request count for API key users."""
        from gateway.main import state
        from shared.auth import APIKeyInfo

        mock_key_info = APIKeyInfo(
            key_id="async123",
            name="Async Test",
            created_at=1234567890.0,
        )
        state.key_manager.validate_key.return_value = mock_key_info

        mock_redis.enqueue_job.return_value = None
        mock_redis.get_queue_size.return_value = 1
        mock_redis.get_active_workers.return_value = ["w1"]

        response = client.post(
            "/synthesize/async",
            json={"text": "Test", "gender": "female", "area": "northern"},
            headers={"X-API-Key": "vvtts_valid_key_1234567890123456"}
        )

        assert response.status_code == 200
        # Verify request was tracked (audio_seconds=0 for async)
        state.key_manager.increment_usage.assert_called_once_with("async123", audio_seconds=0.0)


class TestRequestValidation:
    """Tests for request validation."""

    def test_missing_required_field(self, client):
        response = client.post("/synthesize", json={
            "gender": "female",
            # Missing 'text' field
        })
        assert response.status_code == 422  # Validation error

    def test_invalid_gender_value(self, client):
        response = client.post("/synthesize", json={
            "text": "Hello",
            "gender": "invalid_gender",
            "area": "northern",
        })
        assert response.status_code == 422

    def test_invalid_area_value(self, client):
        response = client.post("/synthesize", json={
            "text": "Hello",
            "gender": "female",
            "area": "invalid_area",
        })
        assert response.status_code == 422
