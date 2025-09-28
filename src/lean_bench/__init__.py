"""
Lean Benchmark SDK - Generic toolkit for compiling and interacting with Lean projects.

This SDK provides benchmark-agnostic tools for:
- Compiling Lean files and content
- Managing Lean projects
- Caching compilation results
- Storing compilation attempts
- HTTP API for remote compilation

Benchmark-specific implementations should use these tools and live in examples/.
"""

from .cache import compute_content_hash, get_cached_result, store_cached_result
from .compiler import CompilerOutput, compile_lean_content, compile_lean_file
from .project import find_lean_files, setup_lean_project
from .storage import query_attempts, retrieve_attempt, store_compilation_attempt

__version__ = "0.1.0"
__all__ = [
    "CompilerOutput",
    "compile_lean_content",
    "compile_lean_file",
    "compute_content_hash",
    "find_lean_files",
    "get_cached_result",
    "query_attempts",
    "retrieve_attempt",
    "setup_lean_project",
    "store_cached_result",
    "store_compilation_attempt",
]
