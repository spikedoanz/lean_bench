"""
MiniF2F benchmark implementation using the generic Lean Bench SDK.

This module demonstrates how to use the SDK for MiniF2F-specific tasks while
keeping all the benchmark-specific logic separate from the core SDK.
"""

import re
import subprocess

# Import from the core SDK
import sys
from pathlib import Path
from typing import Any

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from lean_bench.cache import cache_compilation_result, store_cached_result
from lean_bench.compiler import compile_lean_content
from lean_bench.project import setup_lean_project
from lean_bench.storage import store_compilation_attempt


class MiniF2FEnvironment:
    """
    MiniF2F environment manager using the generic SDK.
    """

    def __init__(self, base_path: Path | str = "~/.lean-bench/minif2f"):
        self.base_path = Path(base_path).expanduser()
        self.lean_path = self.base_path / "lean"
        self.src_path = self.lean_path / "src"

    def is_setup(self) -> bool:
        """Check if MiniF2F environment is properly set up."""
        required_files = [
            self.base_path / "leanpkg.toml",
            self.src_path / "minif2f_import.lean",
            self.src_path / "test.lean",
            self.src_path / "valid.lean",
        ]
        return all(f.exists() for f in required_files)

    def setup(self) -> bool:
        """
        Set up MiniF2F environment.
        This would typically involve cloning the MiniF2F repository.
        """
        if self.is_setup():
            return True

        # In a real implementation, you would:
        # 1. Clone the MiniF2F repository
        # 2. Set up the Lean project
        # 3. Download mathlib cache

        try:
            # Create directory structure
            self.base_path.mkdir(parents=True, exist_ok=True)

            # Use SDK to set up basic Lean project
            success = setup_lean_project(self.base_path, mathlib=True)
            if not success:
                return False

            # Get mathlib cache for faster compilation
            try:
                result = subprocess.run(
                    ["leanproject", "get-mathlib-cache"],
                    cwd=str(self.base_path),
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                return result.returncode == 0
            except Exception:
                return False

        except Exception:
            return False

    def get_split_files(self) -> dict[str, Path]:
        """Get paths to the different split files."""
        return {
            "test": self.src_path / "test.lean",
            "valid": self.src_path / "valid.lean",
            "train": self.src_path / "train.lean",  # If it exists
        }


def setup_minif2f(base_path: Path | str = "~/.lean-bench/minif2f") -> bool:
    """
    Set up MiniF2F environment using the SDK.

    Args:
        base_path: Directory where MiniF2F should be set up

    Returns:
        True if setup succeeded
    """
    env = MiniF2FEnvironment(base_path)
    return env.setup()


def get_theorem_list(
    split: str,
    minif2f_path: Path | str = "~/.lean-bench/minif2f"
) -> list[str]:
    """
    Get list of theorem names from a MiniF2F split.

    Args:
        split: Split name (test, valid, train)
        minif2f_path: Path to MiniF2F environment

    Returns:
        List of theorem names
    """
    env = MiniF2FEnvironment(minif2f_path)
    split_files = env.get_split_files()

    if split not in split_files:
        return []

    split_file = split_files[split]
    if not split_file.exists():
        return []

    try:
        content = split_file.read_text(encoding="utf-8")
        # Extract theorem names using regex
        theorem_pattern = r"theorem\s+(\w+)"
        theorems = re.findall(theorem_pattern, content)
        return theorems
    except Exception:
        return []


def extract_theorem_header(
    theorem_name: str,
    split: str,
    minif2f_path: Path | str = "~/.lean-bench/minif2f"
) -> str | None:
    """
    Extract the header of a specific theorem from MiniF2F.

    Args:
        theorem_name: Name of the theorem to extract
        split: Split name (test, valid, train)
        minif2f_path: Path to MiniF2F environment

    Returns:
        Theorem header string or None if not found
    """
    env = MiniF2FEnvironment(minif2f_path)
    split_files = env.get_split_files()

    if split not in split_files:
        return None

    split_file = split_files[split]
    if not split_file.exists():
        return None

    try:
        content = split_file.read_text(encoding="utf-8")
        # Use the SDK's project utility to extract theorem header
        from lean_bench.project import extract_theorem_header as sdk_extract
        return sdk_extract(content, theorem_name)
    except Exception:
        return None


def compile_minif2f_theorem(
    theorem_content: str,
    theorem_name: str,
    split: str,
    minif2f_path: Path | str = "~/.lean-bench/minif2f",
    timeout: int = 60,
    store_attempt: bool = True
) -> dict[str, Any]:
    """
    Compile a MiniF2F theorem using the generic SDK.

    Args:
        theorem_content: The theorem proof content (e.g., "begin simp end")
        theorem_name: Name of the theorem to compile
        split: Dataset split (test, valid, train)
        minif2f_path: Path to MiniF2F environment
        timeout: Compilation timeout in seconds
        store_attempt: Whether to store the compilation attempt

    Returns:
        Dictionary with compilation results
    """
    env = MiniF2FEnvironment(minif2f_path)

    if not env.is_setup():
        return {
            "success": False,
            "error": "MiniF2F environment not set up. Run setup_minif2f() first."
        }

    # Extract theorem header from the original file
    theorem_header = extract_theorem_header(theorem_name, split, minif2f_path)
    if not theorem_header:
        return {
            "success": False,
            "error": f"Theorem '{theorem_name}' not found in split '{split}'"
        }

    # Prepare the full Lean content
    full_content = f"""
-- Autogenerated MiniF2F theorem compilation
import minif2f_import

open_locale nat
open_locale real
open_locale rat
open_locale big_operators
open_locale topological_space

{theorem_header}
{theorem_content}
"""

    # Use SDK to compile the content
    try:
        # Check cache first
        cache_key, cached_result = cache_compilation_result(
            full_content,
            f"minif2f_{theorem_name}.lean",
            env.base_path,
            [],
            timeout
        )

        if cached_result:
            result_dict = dict(cached_result)
            result_dict["cached"] = True
        else:
            # Compile using SDK
            result = compile_lean_content(
                content=full_content,
                file_name=f"minif2f_{theorem_name}.lean",
                project_root=env.base_path,
                dependencies=None,  # Already included in content
                timeout=timeout
            )

            # Convert to dictionary
            result_dict = {
                "success": result.success,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timeout": result.timeout,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "cached": False,
            }

            # Store in cache
            store_cached_result(cache_key, result_dict)

        # Add MiniF2F-specific metadata
        result_dict.update({
            "theorem_name": theorem_name,
            "split": split,
            "benchmark": "minif2f",
        })

        # Store attempt if requested
        if store_attempt:
            attempt_id = store_compilation_attempt(
                input_data={
                    "theorem_content": theorem_content,
                    "theorem_name": theorem_name,
                    "split": split,
                    "full_content": full_content,
                },
                output_data=result_dict,
                metadata={
                    "benchmark": "minif2f",
                    "theorem": theorem_name,
                    "split": split,
                }
            )
            result_dict["attempt_id"] = attempt_id

        return result_dict

    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Compilation failed: {e!s}",
            "theorem_name": theorem_name,
            "split": split,
            "benchmark": "minif2f",
        }

        if store_attempt:
            attempt_id = store_compilation_attempt(
                input_data={
                    "theorem_content": theorem_content,
                    "theorem_name": theorem_name,
                    "split": split,
                },
                output_data=error_result,
                metadata={
                    "benchmark": "minif2f",
                    "theorem": theorem_name,
                    "split": split,
                }
            )
            error_result["attempt_id"] = attempt_id

        return error_result


def extract_theorem_body(theorem_content: str) -> str | None:
    """
    Extract the proof body from theorem content (for compatibility with existing code).

    Args:
        theorem_content: Full theorem content

    Returns:
        Proof body or None if not found
    """
    # Pattern to match "begin ... end" or "by ..." proofs
    begin_end_match = re.search(r"(begin.*?end)", theorem_content, re.DOTALL)
    if begin_end_match:
        return begin_end_match.group(1)

    by_match = re.search(r"(by\s+.*?)(?:\n|$)", theorem_content, re.DOTALL)
    if by_match:
        return by_match.group(1).strip()

    return None


def get_minif2f_stats(minif2f_path: Path | str = "~/.lean-bench/minif2f") -> dict[str, Any]:
    """
    Get statistics about the MiniF2F environment.

    Args:
        minif2f_path: Path to MiniF2F environment

    Returns:
        Dictionary with environment statistics
    """
    env = MiniF2FEnvironment(minif2f_path)

    if not env.is_setup():
        return {"setup": False, "error": "Environment not set up"}

    stats = {"setup": True}

    # Count theorems in each split
    for split in ["test", "valid", "train"]:
        theorems = get_theorem_list(split, minif2f_path)
        stats[f"{split}_theorems"] = len(theorems)

    # Get file information
    split_files = env.get_split_files()
    for split, file_path in split_files.items():
        if file_path.exists():
            stats[f"{split}_file_size"] = file_path.stat().st_size
        else:
            stats[f"{split}_file_size"] = 0

    return stats
