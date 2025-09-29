#!/usr/bin/env python3
"""Run a single test from the comprehensive test suite with detailed output."""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import the test function
from tests.test_comprehensive import test_project_compiler_integration

if __name__ == "__main__":
    print("Running test_project_compiler_integration in isolation...")
    print("=" * 60)
    try:
        test_project_compiler_integration()
        print("\nTest passed!")
    except AssertionError as e:
        print(f"\nAssertion failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Print the line where it failed
        tb = traceback.extract_tb(e.__traceback__)
        for frame in tb:
            if "test_comprehensive.py" in frame.filename:
                print(f"\nFailed at line {frame.lineno} in test_comprehensive.py")
                print(f"Statement: {frame.line}")
    except Exception as e:
        print(f"\nTest error: {e}")
        import traceback
        traceback.print_exc()