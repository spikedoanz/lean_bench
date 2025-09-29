#!/usr/bin/env python3
"""
Comprehensive tests for the Lean Bench SDK core functionality.
Focuses on edge cases, error handling, and integration scenarios.
"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lean_bench.cache import (
    cleanup_expired_cache,
    clear_cache,
    compute_content_hash,
    get_cache_stats,
    get_cached_result,
    store_cached_result,
)
from lean_bench.compiler import (
    CompilerOutput,
    check_olean_cache,
    compile_lean_content,
    compile_lean_file,
    parse_lean_diagnostics,
)
from lean_bench.project import (
    create_temp_workspace,
    extract_lean_definitions,
    extract_theorem_header,
    find_lean_files,
    setup_lean_project,
    validate_lean_project,
)
from lean_bench.storage import (
    cleanup_old_attempts,
    get_storage_stats,
    query_attempts,
    retrieve_attempt,
    store_compilation_attempt,
)


# ==================== Edge Case Tests ====================

def test_compiler_edge_cases():
    """Test compiler module with edge cases and invalid inputs."""
    print("\n=== Testing Compiler Edge Cases ===")
    
    # Test with empty content
    with tempfile.TemporaryDirectory() as tmpdir:
        result = compile_lean_content(
            content="",
            file_name="empty.lean",
            project_root=Path(tmpdir),
            timeout=5
        )
        print(f"  Empty content compilation: returncode={result.returncode}")
        
    # Test with invalid file name characters
    with tempfile.TemporaryDirectory() as tmpdir:
        result = compile_lean_content(
            content="def test : Nat := 42",
            file_name="test/with/slashes.lean",
            project_root=Path(tmpdir),
            timeout=5
        )
        print(f"  Invalid filename handling: error={result.error is not None}")
    
    # Test with very long content
    with tempfile.TemporaryDirectory() as tmpdir:
        long_content = "-- " + "x" * 1000000  # 1MB comment
        result = compile_lean_content(
            content=long_content,
            file_name="large.lean",
            project_root=Path(tmpdir),
            timeout=5
        )
        print(f"  Large file compilation: completed={result.returncode is not None}")
    
    # Test with timeout = 0
    with tempfile.TemporaryDirectory() as tmpdir:
        result = compile_lean_content(
            content="def test : Nat := 42",
            file_name="timeout_test.lean",
            project_root=Path(tmpdir),
            timeout=0
        )
        print(f"  Zero timeout handling: timeout={result.timeout}")
    
    # Test with non-existent project root
    result = compile_lean_content(
        content="def test : Nat := 42",
        file_name="test.lean",
        project_root=Path("/nonexistent/path/to/project"),
        timeout=5
    )
    print(f"  Non-existent project root: error={result.error is not None}")
    
    # Test diagnostic parsing with malformed stderr
    malformed_stderr = """
    This is not a proper error format
    Random text here
    ::: Some weird formatting
    test.lean:not_a_number:abc: invalid format
    """
    diagnostics = parse_lean_diagnostics(malformed_stderr)
    print(f"  Malformed stderr parsing: diagnostics_count={len(diagnostics)}")
    
    # Test check_olean_cache with non-existent files
    assert not check_olean_cache(Path("/nonexistent/file.lean"))
    print("  ✓ Compiler edge cases tested")


def test_cache_edge_cases():
    """Test cache module with edge cases and error conditions."""
    print("\n=== Testing Cache Edge Cases ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"
        
        # Test with very large cache key
        huge_key = "x" * 10000
        store_cached_result(huge_key, {"test": "data"}, cache_dir=cache_dir)
        # File system might truncate the filename
        print(f"  Huge cache key handling: stored")
        
        # Test with special characters in cache key
        special_key = "test:key/with\\special*chars?"
        store_cached_result(special_key, {"test": "data"}, cache_dir=cache_dir)
        print(f"  Special chars in key: handled")
        
        # Test with corrupted cache file
        corrupt_file = cache_dir / "corrupt.json"
        cache_dir.mkdir(exist_ok=True)
        corrupt_file.write_text("{ this is not valid json }")
        result = get_cached_result("corrupt", cache_dir=cache_dir)
        assert result is None
        print(f"  Corrupted cache file: handled gracefully")
        
        # Test with directory instead of file
        fake_cache = cache_dir / "fake_cache.json"
        fake_cache.mkdir(parents=True, exist_ok=True)
        result = get_cached_result("fake_cache", cache_dir=cache_dir)
        assert result is None
        print(f"  Directory as cache file: handled gracefully")
        # Clean up the directory (may fail on some systems due to permissions)
        try:
            import shutil
            shutil.rmtree(fake_cache)
        except Exception:
            pass  # Best effort cleanup
        
        # Test with read-only cache directory
        if os.name != 'nt':  # Skip on Windows
            readonly_dir = Path(tmpdir) / "readonly"
            readonly_dir.mkdir()
            os.chmod(readonly_dir, 0o444)
            store_cached_result("test", {"data": "test"}, cache_dir=readonly_dir)
            # Should not raise exception
            print(f"  Read-only cache dir: handled gracefully")
            os.chmod(readonly_dir, 0o755)  # Restore permissions for cleanup
        
        # Test TTL with negative value
        store_cached_result("negative_ttl", {"test": "data"}, ttl_seconds=-1, cache_dir=cache_dir)
        result = get_cached_result("negative_ttl", cache_dir=cache_dir)
        assert result is None  # Should be immediately expired
        print(f"  Negative TTL: handled correctly")
        
        # Test cleanup with no cache directory
        count = cleanup_expired_cache(cache_dir=Path(tmpdir) / "nonexistent")
        assert count == 0
        print(f"  Cleanup non-existent dir: handled gracefully")
        
    print("  ✓ Cache edge cases tested")


def test_storage_edge_cases():
    """Test storage module with edge cases and error conditions."""
    print("\n=== Testing Storage Edge Cases ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "storage"
        
        # Test with None values in data
        attempt_id = store_compilation_attempt(
            input_data={"content": None, "empty": ""},
            output_data={"returncode": None, "stdout": None},
            metadata=None,
            storage_dir=storage_dir
        )
        retrieved = retrieve_attempt(attempt_id, storage_dir=storage_dir)
        assert retrieved is not None
        print(f"  None values handling: stored and retrieved")
        
        # Test with circular reference in metadata (should fail gracefully)
        circular_dict = {"key": "value"}
        circular_dict["self"] = circular_dict
        try:
            store_compilation_attempt(
                input_data={"test": "data"},
                output_data={"result": "success"},
                metadata=circular_dict,
                storage_dir=storage_dir
            )
            print(f"  Circular reference: handled")
        except (ValueError, TypeError):
            print(f"  Circular reference: raised expected error")
        
        # Test query with invalid filter syntax
        results = query_attempts(
            filters={"..invalid..key": "value"},
            storage_dir=storage_dir
        )
        print(f"  Invalid filter syntax: returned {len(results)} results")
        
        # Test with corrupted storage file
        date_dir = storage_dir / "2024-01-01"
        date_dir.mkdir(parents=True)
        corrupt_file = date_dir / "2024-01-01T12:00:00_test.json"
        corrupt_file.write_text("not valid json")
        
        results = query_attempts(storage_dir=storage_dir)
        # Should skip corrupted file
        print(f"  Corrupted storage file: skipped gracefully")
        
        # Test cleanup with invalid days_to_keep
        count = cleanup_old_attempts(days_to_keep=-1, storage_dir=storage_dir)
        print(f"  Negative days_to_keep: cleaned {count} files")
        
        # Test with extremely large limit
        results = query_attempts(limit=999999999, storage_dir=storage_dir)
        print(f"  Huge limit: returned {len(results)} results")
        
        # Test retrieve with malformed attempt_id
        result = retrieve_attempt("../../etc/passwd", storage_dir=storage_dir)
        assert result is None
        print(f"  Path traversal attempt: blocked")
        
    print("  ✓ Storage edge cases tested")


def test_project_edge_cases():
    """Test project module with edge cases and error conditions."""
    print("\n=== Testing Project Edge Cases ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test validation on file instead of directory
        file_path = Path(tmpdir) / "file.txt"
        file_path.write_text("not a directory")
        validation = validate_lean_project(file_path)
        assert not validation["valid"]
        assert "not a directory" in str(validation["errors"]).lower()
        print(f"  File as project: validation failed correctly")
        
        # Test with empty directory
        empty_dir = Path(tmpdir) / "empty"
        empty_dir.mkdir()
        validation = validate_lean_project(empty_dir)
        assert not validation["valid"]
        print(f"  Empty directory: validation failed correctly")
        
        # Test find_lean_files with invalid pattern
        try:
            files = find_lean_files(Path(tmpdir), pattern="[invalid")
            print(f"  Invalid glob pattern: returned {len(files)} files")
        except Exception:
            print(f"  Invalid glob pattern: raised exception")
        
        # Test extract_lean_definitions with malformed content
        malformed = """
        def incomplete_def
        theorem without_type
        lemma : := proof
        """
        definitions = extract_lean_definitions(malformed)
        print(f"  Malformed definitions: found {len(definitions)}")
        
        # Test extract_theorem_header with non-existent theorem
        header = extract_theorem_header("file content", "non_existent_theorem")
        assert header is None
        print(f"  Non-existent theorem: returned None")
        
        # Test create_temp_workspace with non-existent base
        try:
            workspace = create_temp_workspace(Path("/nonexistent/base/project"))
            # Should create empty workspace
            assert workspace.exists()
            shutil.rmtree(workspace)
            print(f"  Non-existent base project: created empty workspace")
        except RuntimeError:
            print(f"  Non-existent base project: raised RuntimeError")
        
    print("  ✓ Project edge cases tested")


# ==================== Integration Tests ====================

def test_cache_storage_integration():
    """Test integration between cache and storage modules."""
    print("\n=== Testing Cache-Storage Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"
        storage_dir = Path(tmpdir) / "storage"
        
        # Simulate compilation with caching and storage
        content = "def test : Nat := 42"
        cache_key = compute_content_hash(content, "test.lean")
        
        # First compilation - should store in both cache and storage
        result_data = {
            "returncode": 0,
            "stdout": "Success",
            "stderr": "",
            "success": True
        }
        
        store_cached_result(cache_key, result_data, cache_dir=cache_dir)
        attempt_id = store_compilation_attempt(
            input_data={"content": content, "cache_key": cache_key},
            output_data=result_data,
            metadata={"cached": False},
            storage_dir=storage_dir
        )
        
        # Second compilation - should hit cache
        cached = get_cached_result(cache_key, cache_dir=cache_dir)
        assert cached is not None
        assert cached["cached"] == True
        
        # Store cache hit in storage
        attempt_id_2 = store_compilation_attempt(
            input_data={"content": content, "cache_key": cache_key},
            output_data=cached,
            metadata={"cached": True},
            storage_dir=storage_dir
        )
        
        # Query to verify both attempts
        attempts = query_attempts(storage_dir=storage_dir)
        assert len(attempts) == 2
        
        # Verify cache stats match storage
        cache_stats = get_cache_stats(cache_dir=cache_dir)
        storage_stats = get_storage_stats(storage_dir=storage_dir)
        
        print(f"  Cache entries: {cache_stats['total_entries']}")
        print(f"  Storage attempts: {storage_stats['total_attempts']}")
        print(f"  Integration successful: cache hit recorded in storage")
        
    print("  ✓ Cache-Storage integration tested")


def test_project_compiler_integration():
    """Test integration between project setup and compilation."""
    print("\n=== Testing Project-Compiler Integration ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "test_project"
        
        # Setup project
        success = setup_lean_project(project_path, mathlib=False)
        assert success
        
        # Validate project
        validation = validate_lean_project(project_path)
        assert validation["valid"]
        
        # Create test file
        test_file = project_path / "src" / "integration_test.lean"
        test_content = """
def hello : String := "world"
def add (x y : Nat) : Nat := x + y
theorem add_comm (x y : Nat) : add x y = add y x := by simp [add]
"""
        test_file.write_text(test_content)
        
        # Find and compile the file
        files = find_lean_files(project_path)
        assert len(files) > 0
        
        # Extract definitions before compilation
        definitions = extract_lean_definitions(test_content)
        assert len(definitions) == 3
        
        # Compile the file
        result = compile_lean_file(test_file, project_path, timeout=30)
        print(f"  Project setup and compilation: returncode={result.returncode}")
        
        # Test compilation with dependencies
        dependent_content = """
import integration_test

def use_hello : String := hello ++ "!"
"""
        
        result2 = compile_lean_content(
            content=dependent_content,
            file_name="dependent.lean",
            project_root=project_path,
            dependencies=["integration_test"],
            timeout=30
        )
        print(f"  Compilation with dependencies: returncode={result2.returncode}")
        
    print("  ✓ Project-Compiler integration tested")


# ==================== Concurrent Operations Tests ====================

def test_concurrent_caching():
    """Test cache system under concurrent access."""
    print("\n=== Testing Concurrent Caching ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"
        results = []
        errors = []
        
        def cache_operation(thread_id):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_item_{i}"
                    data = {"thread": thread_id, "item": i, "timestamp": time.time()}
                    
                    # Store
                    store_cached_result(key, data, cache_dir=cache_dir)
                    
                    # Retrieve
                    cached = get_cached_result(key, cache_dir=cache_dir)
                    if cached is None or cached.get("thread") != thread_id:
                        errors.append(f"Thread {thread_id} item {i} mismatch")
                    
                    results.append((thread_id, i))
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")
        
        # Run concurrent operations
        threads = []
        for t_id in range(5):
            thread = threading.Thread(target=cache_operation, args=(t_id,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        print(f"  Concurrent cache operations: {len(results)} successful")
        print(f"  Errors encountered: {len(errors)}")
        
        # Verify cache integrity
        stats = get_cache_stats(cache_dir=cache_dir)
        print(f"  Final cache entries: {stats['total_entries']}")
        
        assert len(errors) == 0, f"Concurrent errors: {errors}"
        
    print("  ✓ Concurrent caching tested")


def test_concurrent_storage():
    """Test storage system under concurrent access."""
    print("\n=== Testing Concurrent Storage ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "storage"
        attempt_ids = []
        lock = threading.Lock()
        
        def storage_operation(thread_id):
            for i in range(10):
                input_data = {"thread": thread_id, "iteration": i}
                output_data = {"success": True, "thread": thread_id}
                
                attempt_id = store_compilation_attempt(
                    input_data=input_data,
                    output_data=output_data,
                    metadata={"concurrent_test": True},
                    storage_dir=storage_dir
                )
                
                with lock:
                    attempt_ids.append(attempt_id)
                
                # Try to retrieve immediately
                retrieved = retrieve_attempt(attempt_id, storage_dir=storage_dir)
                assert retrieved is not None
                assert retrieved["input"]["thread"] == thread_id
        
        # Run concurrent operations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(storage_operation, i) for i in range(5)]
            for future in futures:
                future.result()
        
        print(f"  Concurrent storage operations: {len(attempt_ids)} attempts")
        
        # Verify all attempts are retrievable
        for attempt_id in attempt_ids:
            assert retrieve_attempt(attempt_id, storage_dir=storage_dir) is not None
        
        # Query all attempts
        all_attempts = query_attempts(
            filters={"metadata.concurrent_test": True},
            storage_dir=storage_dir
        )
        assert len(all_attempts) == len(attempt_ids)
        
        print(f"  All attempts retrievable: {len(all_attempts)}")
        
    print("  ✓ Concurrent storage tested")


# ==================== Performance Tests ====================

def test_large_scale_operations():
    """Test system performance with large-scale operations."""
    print("\n=== Testing Large-Scale Operations ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "cache"
        storage_dir = Path(tmpdir) / "storage"
        
        # Test with many cache entries
        print("  Creating 1000 cache entries...")
        start_time = time.time()
        for i in range(1000):
            store_cached_result(
                f"key_{i}",
                {"data": f"value_{i}", "index": i},
                cache_dir=cache_dir
            )
        cache_time = time.time() - start_time
        print(f"    Time: {cache_time:.2f}s")
        
        # Test cache stats performance
        start_time = time.time()
        stats = get_cache_stats(cache_dir=cache_dir)
        stats_time = time.time() - start_time
        print(f"    Cache stats time: {stats_time:.3f}s")
        assert stats["total_entries"] == 1000
        
        # Test with many storage attempts
        print("  Creating 100 storage attempts...")
        start_time = time.time()
        for i in range(100):
            store_compilation_attempt(
                input_data={"test": i},
                output_data={"result": i},
                metadata={"batch": "performance_test"},
                storage_dir=storage_dir
            )
        storage_time = time.time() - start_time
        print(f"    Time: {storage_time:.2f}s")
        
        # Test query performance
        start_time = time.time()
        results = query_attempts(
            filters={"metadata.batch": "performance_test"},
            limit=1000,
            storage_dir=storage_dir
        )
        query_time = time.time() - start_time
        print(f"    Query time: {query_time:.3f}s")
        assert len(results) == 100
        
        # Test cleanup performance
        start_time = time.time()
        cleared = clear_cache(cache_dir=cache_dir)
        clear_time = time.time() - start_time
        print(f"    Clear cache time: {clear_time:.3f}s, cleared {cleared} entries")
        
    print("  ✓ Large-scale operations tested")


# ==================== Error Recovery Tests ====================

def test_error_recovery():
    """Test system recovery from various error conditions."""
    print("\n=== Testing Error Recovery ===")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test compilation with syntax errors
        result = compile_lean_content(
            content="def broken : : : syntax error",
            file_name="error.lean",
            project_root=Path(tmpdir),
            timeout=5
        )
        assert not result.success
        assert result.returncode != 0
        print(f"  Syntax error handling: returncode={result.returncode}")
        
        # Test with missing imports
        result = compile_lean_content(
            content="import NonExistentModule\ndef test : Nat := 42",
            file_name="missing_import.lean",
            project_root=Path(tmpdir),
            timeout=5
        )
        assert not result.success
        print(f"  Missing import handling: handled gracefully")
        
        # Test cache recovery after corruption
        cache_dir = Path(tmpdir) / "cache"
        cache_dir.mkdir()
        
        # Create corrupted cache entry
        corrupt_file = cache_dir / "corrupt_key.json"
        corrupt_file.write_text("corrupted")
        
        # Try to use cache (should handle corruption)
        result = get_cached_result("corrupt_key", cache_dir=cache_dir)
        assert result is None
        
        # Verify we can still write new entries
        store_cached_result("new_key", {"data": "valid"}, cache_dir=cache_dir)
        result = get_cached_result("new_key", cache_dir=cache_dir)
        assert result is not None
        print(f"  Cache recovery after corruption: successful")
        
    print("  ✓ Error recovery tested")


# ==================== Main Test Runner ====================

def run_all_tests():
    """Run all comprehensive tests."""
    print("=" * 60)
    print("Running Comprehensive Tests for Lean Bench SDK")
    print("=" * 60)
    
    test_functions = [
        # Edge cases
        test_compiler_edge_cases,
        test_cache_edge_cases,
        test_storage_edge_cases,
        test_project_edge_cases,
        
        # Integration
        test_cache_storage_integration,
        test_project_compiler_integration,
        
        # Concurrency
        test_concurrent_caching,
        test_concurrent_storage,
        
        # Performance
        test_large_scale_operations,
        
        # Error recovery
        test_error_recovery,
    ]
    
    failed_tests = []
    
    for test_func in test_functions:
        try:
            test_func()
        except AssertionError as e:
            failed_tests.append((test_func.__name__, str(e)))
            print(f"  ✗ {test_func.__name__} failed: {e}")
        except Exception as e:
            failed_tests.append((test_func.__name__, str(e)))
            print(f"  ✗ {test_func.__name__} error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    if failed_tests:
        print(f"FAILED: {len(failed_tests)} tests failed")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
        return 1
    else:
        print(f"SUCCESS: All {len(test_functions)} comprehensive tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(run_all_tests())