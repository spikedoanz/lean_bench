"""
Simple file-based storage for compilation attempts.

This module provides pure functions for storing and retrieving compilation
attempts without requiring a database.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def store_compilation_attempt(
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    metadata: dict[str, Any] | None = None,
    storage_dir: str | Path = "~/.lean-bench/attempts"
) -> str:
    """
    Store a compilation attempt to the filesystem.

    Args:
        input_data: Input data for the compilation (content, params, etc.)
        output_data: Output from the compilation (CompilerOutput data)
        metadata: Optional metadata (session_id, benchmark, etc.)
        storage_dir: Directory to store attempts

    Returns:
        Unique attempt ID
    """
    attempt_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Prepare storage directory
    storage_path = Path(storage_dir).expanduser()
    storage_path.mkdir(parents=True, exist_ok=True)

    # Organize by date for easier browsing
    date_dir = storage_path / datetime.now().strftime("%Y-%m-%d")
    date_dir.mkdir(exist_ok=True)

    # Prepare attempt data
    attempt_data = {
        "attempt_id": attempt_id,
        "timestamp": timestamp,
        "input": input_data,
        "output": output_data,
        "metadata": metadata or {},
    }

    # Write to file
    attempt_file = date_dir / f"{timestamp}_{attempt_id}.json"
    with open(attempt_file, "w", encoding="utf-8") as f:
        json.dump(attempt_data, f, indent=2, ensure_ascii=False)

    return attempt_id


def retrieve_attempt(
    attempt_id: str,
    storage_dir: str | Path = "~/.lean-bench/attempts"
) -> dict[str, Any] | None:
    """
    Retrieve a compilation attempt by ID.

    Args:
        attempt_id: Unique attempt ID to retrieve
        storage_dir: Directory where attempts are stored

    Returns:
        Attempt data dictionary or None if not found
    """
    storage_path = Path(storage_dir).expanduser()

    if not storage_path.exists():
        return None

    # Search through date directories
    for date_dir in storage_path.iterdir():
        if not date_dir.is_dir():
            continue

        # Look for files containing the attempt_id
        for attempt_file in date_dir.glob(f"*_{attempt_id}.json"):
            try:
                with open(attempt_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue

    return None


def query_attempts(
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    storage_dir: str | Path = "~/.lean-bench/attempts"
) -> list[dict[str, Any]]:
    """
    Query compilation attempts with optional filters.

    Args:
        filters: Optional filters to apply (e.g., {"metadata.benchmark": "minif2f"})
        limit: Maximum number of results to return
        storage_dir: Directory where attempts are stored

    Returns:
        List of matching attempt data dictionaries
    """
    storage_path = Path(storage_dir).expanduser()

    if not storage_path.exists():
        return []

    attempts = []
    filters = filters or {}

    # Collect all attempt files, sorted by date (newest first)
    attempt_files = []
    for date_dir in sorted(storage_path.iterdir(), reverse=True):
        if not date_dir.is_dir():
            continue

        for attempt_file in sorted(date_dir.glob("*.json"), reverse=True):
            attempt_files.append(attempt_file)

    # Load and filter attempts
    for attempt_file in attempt_files:
        if len(attempts) >= limit:
            break

        try:
            with open(attempt_file, encoding="utf-8") as f:
                attempt_data = json.load(f)

            # Apply filters
            if _matches_filters(attempt_data, filters):
                attempts.append(attempt_data)

        except Exception:
            continue

    return attempts


def _matches_filters(attempt_data: dict[str, Any], filters: dict[str, Any]) -> bool:
    """
    Check if attempt data matches the given filters.

    Args:
        attempt_data: Attempt data to check
        filters: Filters to apply

    Returns:
        True if attempt matches all filters
    """
    for filter_key, filter_value in filters.items():
        # Support nested keys like "metadata.benchmark"
        value = attempt_data
        for key_part in filter_key.split("."):
            if isinstance(value, dict) and key_part in value:
                value = value[key_part]
            else:
                return False

        # Check if value matches filter
        if value != filter_value:
            return False

    return True


def cleanup_old_attempts(
    days_to_keep: int = 30,
    storage_dir: str | Path = "~/.lean-bench/attempts"
) -> int:
    """
    Clean up old attempt files to save disk space.

    Args:
        days_to_keep: Number of days of attempts to keep
        storage_dir: Directory where attempts are stored

    Returns:
        Number of files deleted
    """
    storage_path = Path(storage_dir).expanduser()

    if not storage_path.exists():
        return 0

    from datetime import timedelta

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0

    for date_dir in storage_path.iterdir():
        if not date_dir.is_dir():
            continue

        try:
            # Parse directory name as date
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if dir_date < cutoff_date:
                import shutil
                shutil.rmtree(date_dir)
                deleted_count += len(list(date_dir.glob("*.json")))
        except Exception:
            continue

    return deleted_count


def get_storage_stats(
    storage_dir: str | Path = "~/.lean-bench/attempts"
) -> dict[str, Any]:
    """
    Get statistics about stored attempts.

    Args:
        storage_dir: Directory where attempts are stored

    Returns:
        Dictionary with storage statistics
    """
    storage_path = Path(storage_dir).expanduser()

    if not storage_path.exists():
        return {
            "total_attempts": 0,
            "total_size_bytes": 0,
            "date_range": None,
            "success_rate": 0.0,
        }

    total_attempts = 0
    total_size = 0
    successful_attempts = 0
    dates = []

    for date_dir in storage_path.iterdir():
        if not date_dir.is_dir():
            continue

        dates.append(date_dir.name)

        for attempt_file in date_dir.glob("*.json"):
            total_attempts += 1
            total_size += attempt_file.stat().st_size

            # Check if attempt was successful
            try:
                with open(attempt_file, encoding="utf-8") as f:
                    attempt_data = json.load(f)
                    if attempt_data.get("output", {}).get("returncode") == 0:
                        successful_attempts += 1
            except Exception:
                continue

    success_rate = successful_attempts / total_attempts if total_attempts > 0 else 0.0
    date_range = f"{min(dates)} to {max(dates)}" if dates else None

    return {
        "total_attempts": total_attempts,
        "total_size_bytes": total_size,
        "date_range": date_range,
        "success_rate": success_rate,
        "successful_attempts": successful_attempts,
    }
