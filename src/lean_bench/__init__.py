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

from .compiler import CompilerOutput, compile_lean_content, compile_lean_file
from .project import setup_lean_project, find_lean_files
from .storage import store_compilation_attempt, retrieve_attempt, query_attempts
from .cache import get_cached_result, store_cached_result, compute_content_hash

__version__ = "0.1.0"
__all__ = [
    "CompilerOutput",
    "compile_lean_content",
    "compile_lean_file",
    "setup_lean_project",
    "find_lean_files",
    "store_compilation_attempt",
    "retrieve_attempt",
    "query_attempts",
    "get_cached_result",
    "store_cached_result",
    "compute_content_hash",
]