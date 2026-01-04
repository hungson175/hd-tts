#!/usr/bin/env python3
"""CLI tool for managing VietVoice TTS API keys."""
import argparse
import sys
import os
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.redis_client import RedisClient
from shared.auth import APIKeyManager


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def format_timestamp(ts: float) -> str:
    """Format timestamp to readable string."""
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def cmd_create(args):
    """Create a new API key."""
    redis = RedisClient(REDIS_URL)
    manager = APIKeyManager(redis)

    full_key, key_info = manager.create_key(args.name)

    print("\n=== API Key Created ===")
    print(f"Name:       {key_info.name}")
    print(f"Key ID:     {key_info.key_id}")
    print(f"Created:    {format_timestamp(key_info.created_at)}")
    print()
    print(f"API Key:    {full_key}")
    print()
    print("IMPORTANT: Save this key now. It cannot be retrieved later.")
    print()

    redis.close()


def cmd_list(args):
    """List all API keys."""
    redis = RedisClient(REDIS_URL)
    manager = APIKeyManager(redis)

    keys = manager.list_keys()

    if not keys:
        print("No API keys found.")
        redis.close()
        return

    print(f"\n{'Key ID':<12} {'Name':<20} {'Created':<20} {'Requests':<10} {'Audio (s)':<10}")
    print("-" * 72)

    for key in keys:
        print(
            f"{key.key_id:<12} "
            f"{key.name[:18]:<20} "
            f"{format_timestamp(key.created_at):<20} "
            f"{key.requests_count:<10} "
            f"{key.audio_seconds:<10.1f}"
        )

    print(f"\nTotal: {len(keys)} key(s)")

    redis.close()


def cmd_delete(args):
    """Delete an API key."""
    redis = RedisClient(REDIS_URL)
    manager = APIKeyManager(redis)

    if manager.delete_key(args.key_id):
        print(f"API key {args.key_id} deleted.")
    else:
        print(f"API key {args.key_id} not found.")
        sys.exit(1)

    redis.close()


def cmd_info(args):
    """Show info about an API key."""
    redis = RedisClient(REDIS_URL)
    manager = APIKeyManager(redis)

    keys = manager.list_keys()
    key = next((k for k in keys if k.key_id == args.key_id), None)

    if not key:
        print(f"API key {args.key_id} not found.")
        sys.exit(1)

    print(f"\n=== API Key: {key.key_id} ===")
    print(f"Name:           {key.name}")
    print(f"Created:        {format_timestamp(key.created_at)}")
    print(f"Total Requests: {key.requests_count}")
    print(f"Audio Seconds:  {key.audio_seconds:.1f}")
    print()

    redis.close()


def main():
    parser = argparse.ArgumentParser(
        description="Manage VietVoice TTS API keys",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create "Friend Name"   Create a new API key
  %(prog)s list                   List all API keys
  %(prog)s info abc12345          Show info about a key
  %(prog)s delete abc12345        Delete an API key
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new API key")
    create_parser.add_argument("name", help="Name for the API key (e.g., friend's name)")
    create_parser.set_defaults(func=cmd_create)

    # list
    list_parser = subparsers.add_parser("list", help="List all API keys")
    list_parser.set_defaults(func=cmd_list)

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete an API key")
    delete_parser.add_argument("key_id", help="Key ID (last 8 chars of the key)")
    delete_parser.set_defaults(func=cmd_delete)

    # info
    info_parser = subparsers.add_parser("info", help="Show info about an API key")
    info_parser.add_argument("key_id", help="Key ID (last 8 chars of the key)")
    info_parser.set_defaults(func=cmd_info)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
