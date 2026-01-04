"""Unit tests for API key authentication."""
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import (
    generate_api_key,
    get_key_id_from_full_key,
    APIKeyManager,
    APIKeyInfo,
    is_localhost_request,
    KEY_PREFIX,
)


class TestGenerateAPIKey:
    """Tests for API key generation."""

    def test_generates_key_with_correct_prefix(self):
        full_key, key_id = generate_api_key()
        assert full_key.startswith(KEY_PREFIX)

    def test_generates_key_with_correct_length(self):
        full_key, key_id = generate_api_key()
        # vvtts_ (6) + 32 hex chars = 38
        assert len(full_key) == 38

    def test_key_id_is_last_8_chars(self):
        full_key, key_id = generate_api_key()
        token = full_key[len(KEY_PREFIX):]
        assert key_id == token[-8:]

    def test_generates_unique_keys(self):
        keys = [generate_api_key()[0] for _ in range(10)]
        assert len(set(keys)) == 10


class TestGetKeyIdFromFullKey:
    """Tests for extracting key ID from full key."""

    def test_extracts_key_id_correctly(self):
        full_key = "vvtts_1234567890abcdef1234567890abcdef"
        key_id = get_key_id_from_full_key(full_key)
        assert key_id == "90abcdef"

    def test_returns_none_for_invalid_prefix(self):
        invalid_key = "invalid_1234567890abcdef1234567890abcdef"
        assert get_key_id_from_full_key(invalid_key) is None

    def test_returns_none_for_wrong_length(self):
        short_key = "vvtts_tooshort"
        assert get_key_id_from_full_key(short_key) is None

    def test_returns_none_for_empty_string(self):
        assert get_key_id_from_full_key("") is None

    def test_returns_none_for_none(self):
        assert get_key_id_from_full_key(None) is None


class TestAPIKeyManager:
    """Tests for API key manager."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client."""
        mock_client = MagicMock()
        mock_client.redis = MagicMock()
        return mock_client

    @pytest.fixture
    def manager(self, mock_redis_client):
        """Create an APIKeyManager with mocked Redis."""
        return APIKeyManager(mock_redis_client)

    def test_create_key_stores_in_redis(self, manager, mock_redis_client):
        full_key, key_info = manager.create_key("Test User")

        # Verify Redis set was called
        mock_redis_client.redis.set.assert_called_once()
        call_args = mock_redis_client.redis.set.call_args
        assert call_args[0][0].startswith("apikey:")
        assert key_info.name == "Test User"

    def test_create_key_returns_valid_key(self, manager):
        full_key, key_info = manager.create_key("Test User")

        assert full_key.startswith(KEY_PREFIX)
        assert len(full_key) == 38
        assert key_info.key_id == full_key[-8:]

    def test_validate_key_returns_info_for_valid_key(self, manager, mock_redis_client):
        # Setup: create a key first
        full_key, created_info = manager.create_key("Test User")

        # Mock Redis to return stored data
        import json
        import hashlib
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        stored_data = json.dumps({
            "key_id": created_info.key_id,
            "full_key_hash": key_hash,
            "name": "Test User",
            "created_at": 1234567890.0,
            "requests_count": 5,
            "audio_seconds": 10.5,
        })
        mock_redis_client.redis.get.return_value = stored_data

        # Validate
        result = manager.validate_key(full_key)

        assert result is not None
        assert result.name == "Test User"
        assert result.requests_count == 5
        assert result.audio_seconds == 10.5

    def test_validate_key_returns_none_for_invalid_key(self, manager, mock_redis_client):
        mock_redis_client.redis.get.return_value = None

        result = manager.validate_key("vvtts_invalidkey12345678901234567")
        assert result is None

    def test_validate_key_returns_none_for_wrong_hash(self, manager, mock_redis_client):
        import json
        stored_data = json.dumps({
            "key_id": "12345678",
            "full_key_hash": "wrong_hash",
            "name": "Test User",
            "created_at": 1234567890.0,
        })
        mock_redis_client.redis.get.return_value = stored_data

        result = manager.validate_key("vvtts_00000000000000000012345678")
        assert result is None

    def test_delete_key_removes_from_redis(self, manager, mock_redis_client):
        mock_redis_client.redis.delete.return_value = 1

        result = manager.delete_key("12345678")

        mock_redis_client.redis.delete.assert_called_once_with("apikey:12345678")
        assert result is True

    def test_delete_key_returns_false_if_not_found(self, manager, mock_redis_client):
        mock_redis_client.redis.delete.return_value = 0

        result = manager.delete_key("nonexistent")
        assert result is False

    def test_increment_usage_updates_counters(self, manager, mock_redis_client):
        import json
        stored_data = json.dumps({
            "key_id": "12345678",
            "full_key_hash": "somehash",
            "name": "Test User",
            "created_at": 1234567890.0,
            "requests_count": 5,
            "audio_seconds": 10.0,
        })
        mock_redis_client.redis.get.return_value = stored_data

        manager.increment_usage("12345678", audio_seconds=5.5)

        # Verify set was called with updated data
        mock_redis_client.redis.set.assert_called()
        call_args = mock_redis_client.redis.set.call_args
        updated_data = json.loads(call_args[0][1])
        assert updated_data["requests_count"] == 6
        assert updated_data["audio_seconds"] == 15.5

    def test_list_keys_returns_all_keys(self, manager, mock_redis_client):
        import json
        mock_redis_client.redis.scan_iter.return_value = ["apikey:key1", "apikey:key2"]
        mock_redis_client.redis.get.side_effect = [
            json.dumps({"key_id": "key1", "name": "User 1", "created_at": 100.0}),
            json.dumps({"key_id": "key2", "name": "User 2", "created_at": 200.0}),
        ]

        keys = manager.list_keys()

        assert len(keys) == 2
        # Should be sorted by created_at desc
        assert keys[0].name == "User 2"
        assert keys[1].name == "User 1"


class TestIsLocalhostRequest:
    """Tests for localhost detection."""

    def test_detects_127_0_0_1(self):
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers.get.return_value = ""

        assert is_localhost_request(request) is True

    def test_detects_ipv6_localhost(self):
        request = MagicMock()
        request.client.host = "::1"
        request.headers.get.return_value = ""

        assert is_localhost_request(request) is True

    def test_rejects_external_ip(self):
        request = MagicMock()
        request.client.host = "203.0.113.50"
        request.headers.get.return_value = ""

        assert is_localhost_request(request) is False

    def test_checks_x_forwarded_for_header(self):
        request = MagicMock()
        request.client.host = "10.0.0.1"  # Proxy IP
        request.headers.get.return_value = "127.0.0.1, 10.0.0.1"  # Original is localhost

        assert is_localhost_request(request) is True

    def test_rejects_external_in_x_forwarded_for(self):
        request = MagicMock()
        request.client.host = "10.0.0.1"
        request.headers.get.return_value = "203.0.113.50, 10.0.0.1"

        assert is_localhost_request(request) is False

    def test_handles_no_client(self):
        request = MagicMock()
        request.client = None
        request.headers.get.return_value = ""

        assert is_localhost_request(request) is False


class TestAuthIntegration:
    """Integration tests for auth flow."""

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client with in-memory storage."""
        storage = {}

        mock_client = MagicMock()
        mock_redis = MagicMock()

        def mock_set(key, value):
            storage[key] = value

        def mock_get(key):
            return storage.get(key)

        def mock_delete(key):
            if key in storage:
                del storage[key]
                return 1
            return 0

        def mock_scan_iter(pattern):
            prefix = pattern.replace("*", "")
            return [k for k in storage.keys() if k.startswith(prefix)]

        mock_redis.set = mock_set
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete
        mock_redis.scan_iter = mock_scan_iter

        mock_client.redis = mock_redis
        return mock_client

    def test_full_key_lifecycle(self, mock_redis_client):
        """Test create -> validate -> use -> delete flow."""
        manager = APIKeyManager(mock_redis_client)

        # Create
        full_key, key_info = manager.create_key("Integration Test")
        assert key_info.name == "Integration Test"

        # Validate
        validated = manager.validate_key(full_key)
        assert validated is not None
        assert validated.name == "Integration Test"
        assert validated.requests_count == 0

        # Use (increment)
        manager.increment_usage(key_info.key_id, audio_seconds=3.5)

        # Validate again - should show usage
        validated = manager.validate_key(full_key)
        assert validated.requests_count == 1
        assert validated.audio_seconds == 3.5

        # Delete
        deleted = manager.delete_key(key_info.key_id)
        assert deleted is True

        # Validate after delete - should fail
        validated = manager.validate_key(full_key)
        assert validated is None

    def test_invalid_key_rejected(self, mock_redis_client):
        """Test that invalid keys are properly rejected."""
        manager = APIKeyManager(mock_redis_client)

        # Create a valid key
        full_key, _ = manager.create_key("Valid User")

        # Try to validate wrong key
        wrong_key = "vvtts_wrongwrongwrongwrongwrongwr"
        result = manager.validate_key(wrong_key)
        assert result is None

        # Try with malformed key
        result = manager.validate_key("not_a_valid_key")
        assert result is None
