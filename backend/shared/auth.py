"""API key authentication for VietVoice TTS."""
import secrets
import time
import json
from typing import Optional
from dataclasses import dataclass

from fastapi import Request


# Key format: vvtts_{32_char_random_token}
KEY_PREFIX = "vvtts_"
KEY_LENGTH = 32

# Redis key prefixes
APIKEY_PREFIX = "apikey:"


@dataclass
class APIKeyInfo:
    """API key information."""
    key_id: str
    name: str
    created_at: float
    requests_count: int = 0
    audio_seconds: float = 0.0


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (full_key, key_id) where key_id is last 8 chars for identification
    """
    token = secrets.token_hex(KEY_LENGTH // 2)  # 32 hex chars
    full_key = f"{KEY_PREFIX}{token}"
    key_id = token[-8:]  # Last 8 chars as ID
    return full_key, key_id


def get_key_id_from_full_key(full_key: str) -> Optional[str]:
    """Extract key_id from full API key.

    Args:
        full_key: Full API key (vvtts_...)

    Returns:
        key_id (last 8 chars) or None if invalid format
    """
    if not full_key or not full_key.startswith(KEY_PREFIX):
        return None
    token = full_key[len(KEY_PREFIX):]
    if len(token) != KEY_LENGTH:
        return None
    return token[-8:]


class APIKeyManager:
    """Manages API keys in Redis."""

    def __init__(self, redis_client):
        """Initialize with Redis client.

        Args:
            redis_client: RedisClient instance
        """
        self.redis = redis_client.redis

    def create_key(self, name: str) -> tuple[str, APIKeyInfo]:
        """Create a new API key.

        Args:
            name: Human-readable name for the key

        Returns:
            Tuple of (full_key, APIKeyInfo)
        """
        full_key, key_id = generate_api_key()

        key_data = {
            "key_id": key_id,
            "full_key_hash": self._hash_key(full_key),
            "name": name,
            "created_at": time.time(),
            "requests_count": 0,
            "audio_seconds": 0.0,
        }

        # Store in Redis (no expiry - permanent until deleted)
        self.redis.set(
            f"{APIKEY_PREFIX}{key_id}",
            json.dumps(key_data)
        )

        return full_key, APIKeyInfo(
            key_id=key_id,
            name=name,
            created_at=key_data["created_at"],
        )

    def validate_key(self, full_key: str) -> Optional[APIKeyInfo]:
        """Validate an API key.

        Args:
            full_key: Full API key to validate

        Returns:
            APIKeyInfo if valid, None otherwise
        """
        key_id = get_key_id_from_full_key(full_key)
        if not key_id:
            return None

        key_data_json = self.redis.get(f"{APIKEY_PREFIX}{key_id}")
        if not key_data_json:
            return None

        key_data = json.loads(key_data_json)

        # Verify hash matches
        if key_data.get("full_key_hash") != self._hash_key(full_key):
            return None

        return APIKeyInfo(
            key_id=key_data["key_id"],
            name=key_data["name"],
            created_at=key_data["created_at"],
            requests_count=key_data.get("requests_count", 0),
            audio_seconds=key_data.get("audio_seconds", 0.0),
        )

    def list_keys(self) -> list[APIKeyInfo]:
        """List all API keys.

        Returns:
            List of APIKeyInfo objects
        """
        keys = []
        for redis_key in self.redis.scan_iter(f"{APIKEY_PREFIX}*"):
            key_data_json = self.redis.get(redis_key)
            if key_data_json:
                key_data = json.loads(key_data_json)
                keys.append(APIKeyInfo(
                    key_id=key_data["key_id"],
                    name=key_data["name"],
                    created_at=key_data["created_at"],
                    requests_count=key_data.get("requests_count", 0),
                    audio_seconds=key_data.get("audio_seconds", 0.0),
                ))
        return sorted(keys, key=lambda k: k.created_at, reverse=True)

    def delete_key(self, key_id: str) -> bool:
        """Delete an API key by its ID.

        Args:
            key_id: Key ID (last 8 chars of the key)

        Returns:
            True if deleted, False if not found
        """
        result = self.redis.delete(f"{APIKEY_PREFIX}{key_id}")
        return result > 0

    def increment_usage(self, key_id: str, audio_seconds: float = 0.0) -> None:
        """Increment usage counters for a key.

        Args:
            key_id: Key ID
            audio_seconds: Audio duration generated (seconds)
        """
        redis_key = f"{APIKEY_PREFIX}{key_id}"
        key_data_json = self.redis.get(redis_key)
        if key_data_json:
            key_data = json.loads(key_data_json)
            key_data["requests_count"] = key_data.get("requests_count", 0) + 1
            key_data["audio_seconds"] = key_data.get("audio_seconds", 0.0) + audio_seconds
            self.redis.set(redis_key, json.dumps(key_data))

    def _hash_key(self, full_key: str) -> str:
        """Hash a full key for storage (simple hash for comparison)."""
        import hashlib
        return hashlib.sha256(full_key.encode()).hexdigest()


def is_localhost_request(request: Request) -> bool:
    """Check if request is from localhost.

    Args:
        request: FastAPI request object

    Returns:
        True if request is from localhost
    """
    client_host = request.client.host if request.client else None

    # Check for localhost IPs
    localhost_ips = {"127.0.0.1", "::1", "localhost"}
    if client_host in localhost_ips:
        return True

    # Check X-Forwarded-For header (for proxied requests)
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # First IP in chain is the original client
        original_ip = forwarded_for.split(",")[0].strip()
        if original_ip in localhost_ips:
            return True

    return False
