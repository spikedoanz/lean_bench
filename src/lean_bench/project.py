"""
Generic Lean project management utilities.

This module provides pure functions for managing Lean projects without any
benchmark-specific logic.
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def setup_lean_project(
    project_path: Path,
    mathlib: bool = False
) -> bool:
    """
    Set up a Lean project directory.

    Args:
        project_path: Directory where the project should be created
        mathlib: Whether to set up mathlib dependencies

    Returns:
        True if setup succeeded, False otherwise
    """
    try:
        project_path.mkdir(parents=True, exist_ok=True)

        # Create basic leanpkg.toml if it doesn't exist
        toml_path = project_path / "leanpkg.toml"
        if not toml_path.exists():
            toml_content = f"""[package]
name = "{project_path.name}"
version = "0.1"
lean_version = "leanprover-community/lean:3.48.0"
path = "src"

[dependencies]
"""
            if mathlib:
                toml_content += 'mathlib = {git = "https://github.com/leanprover-community/mathlib", rev = "9003f28797c0664a49e4179487267c494477d853"}\n'

            toml_path.write_text(toml_content)

        # Create src directory
        src_path = project_path / "src"
        src_path.mkdir(exist_ok=True)

        return True

    except Exception:
        return False


def get_mathlib_cache(project_path: Path) -> bool:
    """
    Download mathlib cache for faster compilation.

    Args:
        project_path: Root directory of the Lean project

    Returns:
        True if cache download succeeded, False otherwise
    """
    try:
        result = subprocess.run(
            ["leanproject", "get-mathlib-cache"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout for cache download
        )
        return result.returncode == 0
    except Exception:
        return False


def find_lean_files(
    project_path: Path,
    pattern: str = "**/*.lean"
) -> list[Path]:
    """
    Find all Lean files in a project directory.

    Args:
        project_path: Root directory to search
        pattern: Glob pattern for finding files (default: all .lean files)

    Returns:
        List of Path objects for found Lean files
    """
    try:
        return list(project_path.glob(pattern))
    except Exception:
        return []


def extract_lean_definitions(file_content: str) -> list[dict[str, Any]]:
    """
    Extract definitions, theorems, and lemmas from Lean file content.

    Args:
        file_content: Content of a .lean file

    Returns:
        List of dictionaries with name, type, and line information
    """
    definitions = []

    # Pattern for top-level definitions, theorems, lemmas
    patterns = [
        (r"def\s+(\w+).*?:.*?:=", "definition"),
        (r"theorem\s+(\w+).*?:.*?:=", "theorem"),
        (r"lemma\s+(\w+).*?:.*?:=", "lemma"),
        (r"axiom\s+(\w+).*?:", "axiom"),
        (r"constant\s+(\w+).*?:", "constant"),
        (r"inductive\s+(\w+)", "inductive"),
        (r"structure\s+(\w+)", "structure"),
        (r"class\s+(\w+)", "class"),
    ]

    lines = file_content.split("\n")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("--"):
            continue

        for pattern, def_type in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1)
                definitions.append({
                    "name": name,
                    "type": def_type,
                    "line": line_num,
                    "content": line,
                })
                break

    return definitions


def create_temp_workspace(base_project: Path) -> Path:
    """
    Create a temporary workspace copying the base project structure.

    This is useful for compilation isolation when multiple compilations
    might interfere with each other.

    Args:
        base_project: Base project directory to copy

    Returns:
        Path to temporary workspace directory
    """
    import shutil

    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="lean_workspace_"))

    try:
        # Copy the entire project structure
        if base_project.exists():
            for item in base_project.iterdir():
                if item.is_dir():
                    shutil.copytree(item, temp_dir / item.name)
                else:
                    shutil.copy2(item, temp_dir / item.name)

        return temp_dir

    except Exception as e:
        # Cleanup on failure
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise RuntimeError(f"Failed to create workspace: {e}")


def validate_lean_project(project_path: Path) -> dict[str, Any]:
    """
    Validate that a directory is a proper Lean project.

    Args:
        project_path: Directory to validate

    Returns:
        Dictionary with validation results and project information
    """
    result = {
        "valid": False,
        "has_leanpkg_toml": False,
        "has_src_dir": False,
        "lean_files_count": 0,
        "errors": [],
    }

    if not project_path.exists():
        result["errors"].append("Project directory does not exist")
        return result

    if not project_path.is_dir():
        result["errors"].append("Project path is not a directory")
        return result

    # Check for leanpkg.toml or leanpkg.path
    toml_path = project_path / "leanpkg.toml"
    path_file = project_path / "leanpkg.path"

    if toml_path.exists():
        result["has_leanpkg_toml"] = True
    elif not path_file.exists():
        result["errors"].append("No leanpkg.toml or leanpkg.path found")

    # Check for src directory
    src_path = project_path / "src"
    if src_path.exists() and src_path.is_dir():
        result["has_src_dir"] = True
    else:
        result["errors"].append("No src/ directory found")

    # Count Lean files
    lean_files = find_lean_files(project_path)
    result["lean_files_count"] = len(lean_files)

    # Project is valid if it has either leanpkg.toml or src/ dir and some .lean files
    result["valid"] = (
        (result["has_leanpkg_toml"] or result["has_src_dir"]) and
        result["lean_files_count"] > 0 and
        len(result["errors"]) == 0
    )

    return result


def extract_theorem_header(file_content: str, theorem_name: str) -> str | None:
    """
    Extract the header of a specific theorem from Lean file content.

    This extracts the theorem declaration up to ":=" for completion by proof content.

    Args:
        file_content: Content of a .lean file
        theorem_name: Name of the theorem to extract

    Returns:
        Theorem header string or None if not found
    """
    # Pattern to match theorem declaration up to :=
    pattern = rf"(theorem\s+{re.escape(theorem_name)}\b.*?:=)"

    match = re.search(pattern, file_content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None
