"""
HTTP API for the Lean Benchmark SDK.

This module provides RESTful endpoints for compilation, project management,
and storage operations using FastAPI.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .compiler import (
    CompilerOutput,
    compile_lean_content,
    compile_lean_file,
    check_lean_installed,
    get_lean_version,
)
from .project import (
    setup_lean_project,
    find_lean_files,
    extract_lean_definitions,
    validate_lean_project,
)
from .storage import (
    store_compilation_attempt,
    retrieve_attempt,
    query_attempts,
    get_storage_stats,
)
from .cache import (
    cache_compilation_result,
    store_cached_result,
    get_cache_stats,
)


# Request/Response Models
class CompileContentRequest(BaseModel):
    content: str = Field(..., description="Lean source code content")
    file_name: str = Field(..., description="Name for the file (should end in .lean)")
    project_root: str = Field(..., description="Root directory of the Lean project")
    dependencies: list[str] | None = Field(None, description="Optional import dependencies")
    timeout: int = Field(60, description="Compilation timeout in seconds")
    store_attempt: bool = Field(True, description="Whether to store the attempt")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for storage")


class CompileFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to the .lean file to compile")
    project_root: str = Field(..., description="Root directory of the Lean project")
    timeout: int = Field(60, description="Compilation timeout in seconds")
    store_attempt: bool = Field(True, description="Whether to store the attempt")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata for storage")


class CompileResponse(BaseModel):
    success: bool
    returncode: int
    stdout: str
    stderr: str
    timeout: bool
    error: str | None
    duration_ms: int
    cached: bool
    attempt_id: str | None = None


class SetupProjectRequest(BaseModel):
    project_path: str = Field(..., description="Directory where the project should be created")
    mathlib: bool = Field(False, description="Whether to set up mathlib dependencies")


class ProjectResponse(BaseModel):
    success: bool
    project_path: str
    validation: dict[str, Any]


class BatchCompileRequest(BaseModel):
    requests: list[CompileContentRequest] = Field(..., description="List of compilation requests")
    max_concurrent: int = Field(4, description="Maximum concurrent compilations")


class BatchCompileResponse(BaseModel):
    task_id: str
    status: str
    total_requests: int


class HealthResponse(BaseModel):
    status: str
    lean_installed: bool
    lean_version: str | None
    cache_stats: dict[str, Any]
    storage_stats: dict[str, Any]


# Initialize FastAPI app
app = FastAPI(
    title="Lean Benchmark SDK API",
    description="HTTP API for compiling and interacting with Lean projects",
    version="0.1.0",
)

# Thread pool for async execution
executor = ThreadPoolExecutor(max_workers=8)


# Utility functions
def run_in_threadpool(func, *args, **kwargs):
    """Run a function in the thread pool for async execution."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(executor, func, *args, **kwargs)


# API Endpoints

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Get system health and status information."""
    lean_installed = await run_in_threadpool(check_lean_installed)
    lean_version = await run_in_threadpool(get_lean_version) if lean_installed else None

    cache_stats = await run_in_threadpool(get_cache_stats)
    storage_stats = await run_in_threadpool(get_storage_stats)

    return HealthResponse(
        status="healthy" if lean_installed else "degraded",
        lean_installed=lean_installed,
        lean_version=lean_version,
        cache_stats=cache_stats,
        storage_stats=storage_stats,
    )


@app.post("/compile/content", response_model=CompileResponse)
async def compile_content(request: CompileContentRequest):
    """Compile Lean content provided as a string."""

    # Check cache first
    cache_key, cached_result = await run_in_threadpool(
        cache_compilation_result,
        request.content,
        request.file_name,
        request.project_root,
        request.dependencies,
        request.timeout
    )

    if cached_result:
        return CompileResponse(
            success=cached_result.get("success", cached_result["returncode"] == 0),
            returncode=cached_result["returncode"],
            stdout=cached_result.get("stdout", ""),
            stderr=cached_result.get("stderr", ""),
            timeout=cached_result.get("timeout", False),
            error=cached_result.get("error"),
            duration_ms=cached_result.get("duration_ms", 0),
            cached=True,
            attempt_id=cached_result.get("attempt_id")
        )

    # Run compilation
    try:
        result = await run_in_threadpool(
            compile_lean_content,
            request.content,
            request.file_name,
            Path(request.project_root),
            request.dependencies,
            request.timeout
        )

        # Convert to dict for caching/storage
        result_dict = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": result.timeout,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "success": result.success,
        }

        # Store in cache
        await run_in_threadpool(store_cached_result, cache_key, result_dict)

        # Store attempt if requested
        attempt_id = None
        if request.store_attempt:
            attempt_id = await run_in_threadpool(
                store_compilation_attempt,
                {
                    "content": request.content,
                    "file_name": request.file_name,
                    "project_root": request.project_root,
                    "dependencies": request.dependencies,
                    "timeout": request.timeout,
                },
                result_dict,
                request.metadata
            )
            result_dict["attempt_id"] = attempt_id

        return CompileResponse(
            success=result.success,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout=result.timeout,
            error=result.error,
            duration_ms=result.duration_ms,
            cached=False,
            attempt_id=attempt_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")


@app.post("/compile/file", response_model=CompileResponse)
async def compile_file(request: CompileFileRequest):
    """Compile a specific Lean file."""

    try:
        result = await run_in_threadpool(
            compile_lean_file,
            Path(request.file_path),
            Path(request.project_root),
            request.timeout
        )

        # Convert to dict for storage
        result_dict = {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": result.timeout,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "success": result.success,
        }

        # Store attempt if requested
        attempt_id = None
        if request.store_attempt:
            attempt_id = await run_in_threadpool(
                store_compilation_attempt,
                {
                    "file_path": request.file_path,
                    "project_root": request.project_root,
                    "timeout": request.timeout,
                },
                result_dict,
                request.metadata
            )

        return CompileResponse(
            success=result.success,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            timeout=result.timeout,
            error=result.error,
            duration_ms=result.duration_ms,
            cached=False,
            attempt_id=attempt_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compilation failed: {str(e)}")


@app.post("/project/setup", response_model=ProjectResponse)
async def setup_project(request: SetupProjectRequest):
    """Set up a new Lean project."""

    try:
        success = await run_in_threadpool(
            setup_lean_project,
            Path(request.project_path),
            request.mathlib
        )

        if success:
            validation = await run_in_threadpool(
                validate_lean_project,
                Path(request.project_path)
            )
        else:
            validation = {"valid": False, "errors": ["Project setup failed"]}

        return ProjectResponse(
            success=success,
            project_path=request.project_path,
            validation=validation
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Project setup failed: {str(e)}")


@app.get("/project/{project_path:path}/files")
async def list_project_files(project_path: str, pattern: str = "**/*.lean"):
    """List Lean files in a project directory."""

    try:
        files = await run_in_threadpool(
            find_lean_files,
            Path(project_path),
            pattern
        )

        return {
            "files": [str(f) for f in files],
            "count": len(files)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@app.get("/project/{project_path:path}/definitions")
async def extract_project_definitions(project_path: str, file_pattern: str = "**/*.lean"):
    """Extract definitions from Lean files in a project."""

    try:
        files = await run_in_threadpool(
            find_lean_files,
            Path(project_path),
            file_pattern
        )

        all_definitions = []
        for file_path in files:
            content = file_path.read_text(encoding="utf-8")
            definitions = await run_in_threadpool(extract_lean_definitions, content)

            for defn in definitions:
                defn["file"] = str(file_path)

            all_definitions.extend(definitions)

        return {
            "definitions": all_definitions,
            "count": len(all_definitions),
            "files_scanned": len(files)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract definitions: {str(e)}")


@app.post("/compile/batch", response_model=BatchCompileResponse)
async def batch_compile(request: BatchCompileRequest, background_tasks: BackgroundTasks):
    """Compile multiple requests in parallel."""

    import uuid
    task_id = str(uuid.uuid4())

    # Add batch compilation task to background
    background_tasks.add_task(
        _run_batch_compilation,
        task_id,
        request.requests,
        request.max_concurrent
    )

    return BatchCompileResponse(
        task_id=task_id,
        status="queued",
        total_requests=len(request.requests)
    )


async def _run_batch_compilation(
    task_id: str,
    requests: list[CompileContentRequest],
    max_concurrent: int
):
    """Run batch compilation in background."""
    # This is a simplified implementation
    # In a production system, you'd want proper job tracking

    semaphore = asyncio.Semaphore(max_concurrent)

    async def compile_single(req: CompileContentRequest):
        async with semaphore:
            # Reuse the compile_content logic
            try:
                cache_key, cached_result = await run_in_threadpool(
                    cache_compilation_result,
                    req.content,
                    req.file_name,
                    req.project_root,
                    req.dependencies,
                    req.timeout
                )

                if cached_result:
                    return cached_result

                result = await run_in_threadpool(
                    compile_lean_content,
                    req.content,
                    req.file_name,
                    Path(req.project_root),
                    req.dependencies,
                    req.timeout
                )

                result_dict = {
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "timeout": result.timeout,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                    "success": result.success,
                }

                # Store in cache
                await run_in_threadpool(store_cached_result, cache_key, result_dict)

                # Store attempt if requested
                if req.store_attempt:
                    await run_in_threadpool(
                        store_compilation_attempt,
                        {
                            "content": req.content,
                            "file_name": req.file_name,
                            "project_root": req.project_root,
                            "dependencies": req.dependencies,
                            "timeout": req.timeout,
                        },
                        result_dict,
                        req.metadata
                    )

                return result_dict

            except Exception as e:
                return {"error": str(e), "success": False}

    # Run all compilations
    await asyncio.gather(*[compile_single(req) for req in requests])


@app.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: str):
    """Retrieve a specific compilation attempt."""

    attempt = await run_in_threadpool(retrieve_attempt, attempt_id)

    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")

    return attempt


@app.get("/attempts")
async def query_compilation_attempts(
    benchmark: str | None = None,
    success: bool | None = None,
    limit: int = 100
):
    """Query compilation attempts with filters."""

    filters = {}
    if benchmark:
        filters["metadata.benchmark"] = benchmark
    if success is not None:
        filters["output.success"] = success

    attempts = await run_in_threadpool(query_attempts, filters, limit)

    return {
        "attempts": attempts,
        "count": len(attempts)
    }


# Add CORS middleware for development
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)