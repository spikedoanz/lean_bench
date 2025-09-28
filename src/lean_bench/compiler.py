"""
Generic Lean compilation functions.

This module provides pure functions for compiling Lean code without any
benchmark-specific logic. All functions take explicit parameters and return
structured results.
"""

import re
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CompilerOutput:
    """Result of a Lean compilation."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    timeout: bool = False
    error: str | None = None
    args: list[str] = field(default_factory=list)
    cwd: str = ""
    cached: bool = False
    duration_ms: int = 0

    @property
    def success(self) -> bool:
        """True if compilation succeeded."""
        return self.returncode == 0 and not self.timeout and not self.error


def check_lean_installed() -> bool:
    """Check if Lean is installed and accessible via elan."""
    try:
        result = subprocess.run(
            ["elan", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and "elan" in result.stdout
    except Exception:
        return False


def get_lean_version() -> str | None:
    """Get the active Lean version."""
    try:
        result = subprocess.run(
            ["lean", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception:
        return None


def parse_lean_diagnostics(stderr: str) -> list[dict[str, Any]]:
    """
    Parse Lean compiler stderr into structured diagnostics.

    Args:
        stderr: Raw stderr output from Lean compiler

    Returns:
        List of diagnostic dictionaries with file, line, column, level, message
    """
    diagnostics = []

    # Pattern for Lean error messages: file:line:column: level: message
    pattern = r"([^:]+):(\d+):(\d+):\s*(error|warning|info):\s*(.+)"

    for line in stderr.split("\n"):
        line = line.strip()
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            file, line_num, col_num, level, message = match.groups()
            diagnostics.append({
                "file": file,
                "line": int(line_num),
                "column": int(col_num),
                "level": level,
                "message": message.strip(),
            })

    return diagnostics


def compile_lean_file(
    file_path: Path,
    project_root: Path,
    timeout: int = 60
) -> CompilerOutput:
    """
    Compile a specific Lean file.

    Args:
        file_path: Path to the .lean file to compile
        project_root: Root directory of the Lean project
        timeout: Compilation timeout in seconds

    Returns:
        CompilerOutput with compilation results
    """
    import time

    start_time = time.time()
    args = ["lean", str(file_path)]

    try:
        result = subprocess.run(
            args=args,
            cwd=str(project_root),
            text=True,
            capture_output=True,
            timeout=timeout,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        return CompilerOutput(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout=False,
            error=None,
            args=args,
            cwd=str(project_root),
            duration_ms=duration_ms,
        )

    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        return CompilerOutput(
            returncode=-1,
            timeout=True,
            error=f"Compilation timeout (exceeded {timeout} seconds)",
            args=args,
            cwd=str(project_root),
            duration_ms=duration_ms,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        return CompilerOutput(
            returncode=-1,
            error=str(e),
            args=args,
            cwd=str(project_root),
            duration_ms=duration_ms,
        )


def compile_lean_content(
    content: str,
    file_name: str,
    project_root: Path,
    dependencies: list[str] | None = None,
    timeout: int = 60
) -> CompilerOutput:
    """
    Compile Lean content by writing it to a temporary file.

    Args:
        content: Lean source code to compile
        file_name: Name for the temporary file (should end in .lean)
        project_root: Root directory of the Lean project
        dependencies: Optional list of import statements to prepend
        timeout: Compilation timeout in seconds

    Returns:
        CompilerOutput with compilation results
    """
    # Ensure file_name ends with .lean
    if not file_name.endswith(".lean"):
        file_name += ".lean"

    # Prepare full content with dependencies
    full_content = ""
    if dependencies:
        for dep in dependencies:
            if not dep.startswith("import "):
                dep = f"import {dep}"
            full_content += f"{dep}\n"
        full_content += "\n"

    full_content += content

    # Create unique filename to avoid conflicts
    unique_name = f"{uuid.uuid4().hex}_{file_name}".replace("-", "_")
    temp_file = project_root / unique_name

    try:
        # Write content to temporary file
        temp_file.write_text(full_content, encoding="utf-8")

        # Compile the temporary file
        result = compile_lean_file(temp_file, project_root, timeout)

        return result

    except Exception as e:
        return CompilerOutput(
            returncode=-1,
            error=f"Failed to write temporary file: {e}",
            args=[],
            cwd=str(project_root),
        )
    finally:
        # Clean up temporary file
        if temp_file.exists():
            try:
                temp_file.unlink()
            except Exception:
                pass  # Best effort cleanup

        # Also clean up .olean file if it exists
        olean_file = temp_file.with_suffix(".olean")
        if olean_file.exists():
            try:
                olean_file.unlink()
            except Exception:
                pass


def check_olean_cache(file_path: Path) -> bool:
    """
    Check if a .olean cache file exists and is newer than the source.

    Args:
        file_path: Path to the .lean source file

    Returns:
        True if cached .olean file exists and is up to date
    """
    olean_path = file_path.with_suffix(".olean")

    if not olean_path.exists():
        return False

    if not file_path.exists():
        return False

    # Check if .olean is newer than .lean
    try:
        olean_mtime = olean_path.stat().st_mtime
        lean_mtime = file_path.stat().st_mtime
        return olean_mtime >= lean_mtime
    except Exception:
        return False
