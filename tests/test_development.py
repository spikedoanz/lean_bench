#!/usr/bin/env python3
"""
Development tests for Lean Bench SDK components.
Run during development to validate code as we build it.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from lean_bench.compiler import (
    check_lean_installed,
    get_lean_version,
    parse_lean_diagnostics,
    CompilerOutput
)
from lean_bench.project import (
    setup_lean_project,
    find_lean_files,
    extract_lean_definitions,
    validate_lean_project
)
from lean_bench.storage import (
    store_compilation_attempt,
    retrieve_attempt,
    query_attempts,
    get_storage_stats
)
from lean_bench.cache import (
    compute_content_hash,
    get_cached_result,
    store_cached_result,
    get_cache_stats
)


def test_lean_installation():
    """Test basic Lean installation detection."""
    print("Testing Lean installation...")

    has_lean = check_lean_installed()
    print(f"  Lean installed: {has_lean}")

    if has_lean:
        version = get_lean_version()
        print(f"  Lean version: {version}")

    return has_lean


def test_diagnostic_parsing():
    """Test parsing of Lean compiler diagnostics."""
    print("\nTesting diagnostic parsing...")

    sample_stderr = """
test.lean:5:10: error: unknown identifier 'foo'
test.lean:12:5: warning: unused variable 'bar'
another.lean:3:15: info: some information
"""

    diagnostics = parse_lean_diagnostics(sample_stderr)
    print(f"  Found {len(diagnostics)} diagnostics:")

    for diag in diagnostics:
        print(f"    {diag['file']}:{diag['line']}:{diag['column']} {diag['level']}: {diag['message']}")

    # Test expected results
    assert len(diagnostics) == 3
    assert diagnostics[0]['line'] == 5
    assert diagnostics[0]['level'] == 'error'
    assert 'foo' in diagnostics[0]['message']

    print("  ✓ Diagnostic parsing tests passed")


def test_project_setup():
    """Test basic project setup functionality."""
    print("\nTesting project setup...")

    test_dir = Path("/tmp/test_lean_project")

    # Clean up if exists
    if test_dir.exists():
        import shutil
        shutil.rmtree(test_dir)

    # Test project setup
    success = setup_lean_project(test_dir, mathlib=False)
    print(f"  Project setup success: {success}")

    if success:
        # Check files were created
        assert test_dir.exists()
        assert (test_dir / "leanpkg.toml").exists()
        assert (test_dir / "src").exists()
        print("  ✓ Required files created")

        # Test validation
        validation = validate_lean_project(test_dir)
        print(f"  Project validation: {validation}")

        # Create a test lean file
        test_lean = test_dir / "src" / "test.lean"
        test_lean.write_text("""
def hello : String := "world"

theorem simple_theorem : 1 + 1 = 2 := by norm_num

lemma example_lemma (x : Nat) : x + 0 = x := by simp
""")

        # Test finding lean files
        lean_files = find_lean_files(test_dir)
        print(f"  Found {len(lean_files)} Lean files")

        # Test extracting definitions
        definitions = extract_lean_definitions(test_lean.read_text())
        print(f"  Found {len(definitions)} definitions:")
        for defn in definitions:
            print(f"    {defn['type']}: {defn['name']} (line {defn['line']})")

        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        print("  ✓ Project setup tests passed")


def test_compiler_output():
    """Test CompilerOutput dataclass."""
    print("\nTesting CompilerOutput...")

    # Test successful compilation
    success_output = CompilerOutput(returncode=0, stdout="compiled successfully")
    assert success_output.success
    print("  ✓ Success case works")

    # Test failed compilation
    fail_output = CompilerOutput(returncode=1, stderr="compilation error")
    assert not fail_output.success
    print("  ✓ Failure case works")

    # Test timeout case
    timeout_output = CompilerOutput(returncode=-1, timeout=True)
    assert not timeout_output.success
    print("  ✓ Timeout case works")


def test_storage_system():
    """Test storage and retrieval of compilation attempts."""
    print("\nTesting storage system...")

    # Test storing an attempt
    input_data = {
        "content": "def test : String := \"hello\"",
        "file_name": "test.lean"
    }
    output_data = {
        "returncode": 0,
        "stdout": "compiled successfully",
        "stderr": ""
    }
    metadata = {
        "benchmark": "test",
        "session_id": "test_session"
    }

    attempt_id = store_compilation_attempt(
        input_data,
        output_data,
        metadata,
        storage_dir="/tmp/test_storage"
    )
    print(f"  Stored attempt with ID: {attempt_id}")

    # Test retrieving the attempt
    retrieved = retrieve_attempt(attempt_id, storage_dir="/tmp/test_storage")
    assert retrieved is not None
    assert retrieved["attempt_id"] == attempt_id
    assert retrieved["input"] == input_data
    assert retrieved["output"] == output_data
    print("  ✓ Successfully stored and retrieved attempt")

    # Test querying attempts
    attempts = query_attempts(
        filters={"metadata.benchmark": "test"},
        storage_dir="/tmp/test_storage"
    )
    assert len(attempts) >= 1
    print(f"  Found {len(attempts)} attempts with filter")

    # Test storage stats
    stats = get_storage_stats(storage_dir="/tmp/test_storage")
    assert stats["total_attempts"] >= 1
    print(f"  Storage stats: {stats}")

    # Cleanup
    import shutil
    shutil.rmtree("/tmp/test_storage", ignore_errors=True)
    print("  ✓ Storage system tests passed")


def test_cache_system():
    """Test caching functionality."""
    print("\nTesting cache system...")

    # Test hash computation
    hash1 = compute_content_hash("test content", "test.lean")
    hash2 = compute_content_hash("test content", "test.lean")
    hash3 = compute_content_hash("different content", "test.lean")

    assert hash1 == hash2  # Same inputs should give same hash
    assert hash1 != hash3  # Different inputs should give different hash
    print("  ✓ Hash computation works correctly")

    # Test caching
    cache_key = "test_cache_key"
    result_data = {
        "returncode": 0,
        "stdout": "cached result",
        "duration_ms": 100
    }

    # Store in cache
    store_cached_result(
        cache_key,
        result_data,
        cache_dir="/tmp/test_cache"
    )

    # Retrieve from cache
    cached = get_cached_result(cache_key, cache_dir="/tmp/test_cache")
    assert cached is not None
    assert cached["stdout"] == "cached result"
    assert cached["cached"] == True  # Should be marked as cache hit
    print("  ✓ Successfully stored and retrieved from cache")

    # Test cache stats
    stats = get_cache_stats(cache_dir="/tmp/test_cache")
    assert stats["total_entries"] >= 1
    print(f"  Cache stats: {stats}")

    # Test TTL caching
    store_cached_result(
        "ttl_test",
        {"test": "data"},
        ttl_seconds=1,  # Very short TTL
        cache_dir="/tmp/test_cache"
    )

    # Should be available immediately
    cached_ttl = get_cached_result("ttl_test", cache_dir="/tmp/test_cache")
    assert cached_ttl is not None

    # Wait and check expiration (quick test - sleep for 1.1 seconds)
    import time
    time.sleep(1.1)
    expired = get_cached_result("ttl_test", cache_dir="/tmp/test_cache")
    assert expired is None  # Should be expired and removed
    print("  ✓ TTL expiration works correctly")

    # Cleanup
    import shutil
    shutil.rmtree("/tmp/test_cache", ignore_errors=True)
    print("  ✓ Cache system tests passed")


if __name__ == "__main__":
    print("Running development tests for Lean Bench SDK...")
    print("=" * 50)

    try:
        test_lean_installation()
        test_diagnostic_parsing()
        test_project_setup()
        test_compiler_output()
        test_storage_system()
        test_cache_system()

        print("\n" + "=" * 50)
        print("All development tests passed! ✓")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)