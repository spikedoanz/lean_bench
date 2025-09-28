"""
Simple content-based caching for compilation results.

This module provides pure functions for caching compilation results based on
content hashes to avoid redundant compilations.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any


def compute_content_hash(*args: Any) -> str:
    """
    Compute SHA256 hash of the given arguments.

    Args:
        *args: Arguments to hash (strings, dicts, lists, etc.)

    Returns:
        Hexadecimal hash string
    """
    # Convert all arguments to a stable string representation
    content_str = ""
    for arg in args:
        if isinstance(arg, (dict, list)):
            content_str += json.dumps(arg, sort_keys=True, ensure_ascii=False)
        else:
            content_str += str(arg)

    return hashlib.sha256(content_str.encode("utf-8")).hexdigest()


def get_cached_result(
    cache_key: str,
    cache_dir: str | Path = "~/.lean-bench/cache"
) -> dict[str, Any] | None:
    """
    Retrieve a cached compilation result.

    Args:
        cache_key: Cache key (typically a content hash)
        cache_dir: Directory where cache files are stored

    Returns:
        Cached result dictionary or None if not found/expired
    """
    cache_path = Path(cache_dir).expanduser()
    cache_file = cache_path / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cached_data = json.load(f)

        # Check TTL if specified
        if "expires_at" in cached_data:
            if time.time() > cached_data["expires_at"]:
                # Cache expired, remove file
                cache_file.unlink(missing_ok=True)
                return None

        # Return the actual result (without cache metadata)
        result = cached_data.get("result", cached_data)

        # Mark as cache hit
        if isinstance(result, dict):
            result["cached"] = True

        return result

    except Exception:
        # If there's any error reading the cache, treat as cache miss
        cache_file.unlink(missing_ok=True)
        return None


def store_cached_result(
    cache_key: str,
    result: dict[str, Any],
    ttl_seconds: int | None = None,
    cache_dir: str | Path = "~/.lean-bench/cache"
) -> None:
    """
    Store a compilation result in the cache.

    Args:
        cache_key: Cache key (typically a content hash)
        result: Result dictionary to cache
        ttl_seconds: Optional time-to-live in seconds
        cache_dir: Directory where cache files are stored
    """
    cache_path = Path(cache_dir).expanduser()
    cache_path.mkdir(parents=True, exist_ok=True)

    cache_file = cache_path / f"{cache_key}.json"

    # Prepare cache data
    cache_data = {
        "result": result,
        "cached_at": time.time(),
    }

    if ttl_seconds is not None:
        cache_data["expires_at"] = time.time() + ttl_seconds

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
    except Exception:
        # If we can't write to cache, that's okay - just continue
        pass


def clear_cache(cache_dir: str | Path = "~/.lean-bench/cache") -> int:
    """
    Clear all cached results.

    Args:
        cache_dir: Directory where cache files are stored

    Returns:
        Number of cache files removed
    """
    cache_path = Path(cache_dir).expanduser()

    if not cache_path.exists():
        return 0

    count = 0
    for cache_file in cache_path.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception:
            continue

    return count


def cleanup_expired_cache(cache_dir: str | Path = "~/.lean-bench/cache") -> int:
    """
    Remove expired cache entries.

    Args:
        cache_dir: Directory where cache files are stored

    Returns:
        Number of expired cache files removed
    """
    cache_path = Path(cache_dir).expanduser()

    if not cache_path.exists():
        return 0

    current_time = time.time()
    count = 0

    for cache_file in cache_path.glob("*.json"):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            if "expires_at" in cache_data and current_time > cache_data["expires_at"]:
                cache_file.unlink()
                count += 1

        except Exception:
            # If we can't read the cache file, remove it
            cache_file.unlink(missing_ok=True)
            count += 1

    return count


def get_cache_stats(cache_dir: str | Path = "~/.lean-bench/cache") -> dict[str, Any]:
    """
    Get statistics about the cache.

    Args:
        cache_dir: Directory where cache files are stored

    Returns:
        Dictionary with cache statistics
    """
    cache_path = Path(cache_dir).expanduser()

    if not cache_path.exists():
        return {
            "total_entries": 0,
            "total_size_bytes": 0,
            "expired_entries": 0,
        }

    total_entries = 0
    total_size = 0
    expired_entries = 0
    current_time = time.time()

    for cache_file in cache_path.glob("*.json"):
        total_entries += 1
        total_size += cache_file.stat().st_size

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            if "expires_at" in cache_data and current_time > cache_data["expires_at"]:
                expired_entries += 1

        except Exception:
            expired_entries += 1

    return {
        "total_entries": total_entries,
        "total_size_bytes": total_size,
        "expired_entries": expired_entries,
    }


def cache_compilation_result(
    content: str,
    file_name: str,
    project_root: str | Path,
    dependencies: list[str] | None = None,
    timeout: int = 60
) -> tuple[str, dict[str, Any] | None]:
    """
    Generate cache key and check for cached compilation result.

    This is a convenience function that combines cache key generation
    and cache lookup for compilation operations.

    Args:
        content: Lean source content
        file_name: Name of the file
        project_root: Project root directory
        dependencies: Optional dependencies
        timeout: Compilation timeout

    Returns:
        Tuple of (cache_key, cached_result_or_None)
    """
    # Generate cache key from all input parameters
    cache_key = compute_content_hash(
        content,
        file_name,
        str(project_root),
        dependencies or [],
        timeout
    )

    # Check for cached result
    cached_result = get_cached_result(cache_key)

    return cache_key, cached_result