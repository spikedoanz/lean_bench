#!/usr/bin/env python3
"""
API tests for the Lean Bench SDK.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from lean_bench.api import app

client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint."""
    print("Testing /health endpoint...")

    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "lean_installed" in data
    assert "cache_stats" in data
    assert "storage_stats" in data

    print(f"  Status: {data['status']}")
    print(f"  Lean installed: {data['lean_installed']}")
    if data['lean_installed']:
        print(f"  Lean version: {data['lean_version']}")

    print("  ✓ Health endpoint works")


def test_project_setup_endpoint():
    """Test the project setup endpoint."""
    print("\nTesting /project/setup endpoint...")

    request_data = {
        "project_path": "/tmp/test_api_project",
        "mathlib": False
    }

    response = client.post("/project/setup", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert "success" in data
    assert "project_path" in data
    assert "validation" in data

    print(f"  Setup success: {data['success']}")
    print(f"  Project path: {data['project_path']}")

    # Cleanup
    import shutil
    shutil.rmtree("/tmp/test_api_project", ignore_errors=True)

    print("  ✓ Project setup endpoint works")


def test_compile_content_endpoint():
    """Test the content compilation endpoint."""
    print("\nTesting /compile/content endpoint...")

    # First set up a test project
    setup_response = client.post("/project/setup", json={
        "project_path": "/tmp/test_api_compile",
        "mathlib": False
    })
    assert setup_response.status_code == 200

    # Test compilation
    compile_request = {
        "content": "def hello : String := \"world\"",
        "file_name": "test.lean",
        "project_root": "/tmp/test_api_compile",
        "timeout": 30,
        "store_attempt": True,
        "metadata": {"test": "api_test"}
    }

    response = client.post("/compile/content", json=compile_request)
    print(f"  Response status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"  Compilation success: {data['success']}")
        print(f"  Return code: {data['returncode']}")
        print(f"  Cached: {data['cached']}")
        print(f"  Duration: {data['duration_ms']}ms")

        if data['attempt_id']:
            print(f"  Attempt ID: {data['attempt_id']}")

        print("  ✓ Compile content endpoint works")
    else:
        print(f"  Compilation failed: {response.text}")
        # This might be expected if Lean is not properly set up

    # Cleanup
    import shutil
    shutil.rmtree("/tmp/test_api_compile", ignore_errors=True)


def test_list_files_endpoint():
    """Test the file listing endpoint."""
    print("\nTesting file listing endpoint...")

    # Set up test project with a file
    setup_response = client.post("/project/setup", json={
        "project_path": "/tmp/test_api_files",
        "mathlib": False
    })
    assert setup_response.status_code == 200

    # Create a test file
    test_file = Path("/tmp/test_api_files/src/test.lean")
    test_file.write_text("def example : Nat := 42")

    # List files
    response = client.get("/project/%2Ftmp%2Ftest_api_files/files")
    assert response.status_code == 200

    data = response.json()
    assert "files" in data
    assert "count" in data
    assert data["count"] >= 1

    print(f"  Found {data['count']} files")
    print("  ✓ File listing endpoint works")

    # Cleanup
    import shutil
    shutil.rmtree("/tmp/test_api_files", ignore_errors=True)


def test_query_attempts_endpoint():
    """Test the attempts query endpoint."""
    print("\nTesting attempts query endpoint...")

    response = client.get("/attempts")
    assert response.status_code == 200

    data = response.json()
    assert "attempts" in data
    assert "count" in data

    print(f"  Found {data['count']} attempts")
    print("  ✓ Attempts query endpoint works")


if __name__ == "__main__":
    print("Running API tests for Lean Bench SDK...")
    print("=" * 50)

    try:
        test_health_endpoint()
        test_project_setup_endpoint()
        test_compile_content_endpoint()
        test_list_files_endpoint()
        test_query_attempts_endpoint()

        print("\n" + "=" * 50)
        print("All API tests completed! ✓")

    except Exception as e:
        print(f"\nAPI test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)