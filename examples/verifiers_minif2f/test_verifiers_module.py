#!/usr/bin/env python3
"""
Test the verifiers MiniF2F module.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def test_verifiers_module_import():
    """Test that we can import the verifiers module."""
    print("Testing verifiers module import...")

    try:
        from minif2f_verifiers import (
            CompilerOutput,
            lean_check,
            MiniF2FParser,
            DEFAULT_MINIF2F_PATH,
            DEFAULT_MINIF2F_SYSTEM_PROMPT
        )
        print("✓ Successfully imported core verifiers module components")
    except ImportError as e:
        print(f"✗ Failed to import verifiers module: {e}")
        return False

    return True

def test_lean_check():
    """Test Lean installation check."""
    print("Testing Lean installation check...")

    try:
        from minif2f_verifiers import lean_check

        lean_available = lean_check()
        print(f"  Lean available: {lean_available}")

        if lean_available:
            print("✓ Lean is properly installed")
        else:
            print("⚠ Lean not available (this is expected if Lean isn't installed)")

        return True
    except Exception as e:
        print(f"✗ Error checking Lean: {e}")
        return False

def test_parser():
    """Test the MiniF2F parser."""
    print("Testing MiniF2F parser...")

    try:
        from minif2f_verifiers import MiniF2FParser

        parser = MiniF2FParser()

        # Test parsing code blocks
        test_cases = [
            "```lean\nbegin sorry end\n```",
            "```\nproof content here\n```",
            "No code block here",
            "```isabelle\nby auto\n```"
        ]

        for i, test_case in enumerate(test_cases):
            result = parser.parse_answer(test_case)
            print(f"  Test case {i+1}: {'✓' if result else '✗'} -> {result}")

        print("✓ Parser tests completed")
        return True
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return False

def test_compiler_output():
    """Test CompilerOutput dataclass."""
    print("Testing CompilerOutput...")

    try:
        from minif2f_verifiers import CompilerOutput

        # Test successful compilation
        success_output = CompilerOutput(returncode=0, stdout="Success!")
        print(f"  Success case: returncode={success_output.returncode}")

        # Test failed compilation
        fail_output = CompilerOutput(
            returncode=1,
            stderr="Error message",
            error="Compilation failed"
        )
        print(f"  Failure case: returncode={fail_output.returncode}, error={fail_output.error}")

        print("✓ CompilerOutput tests passed")
        return True
    except Exception as e:
        print(f"✗ CompilerOutput test failed: {e}")
        return False

def test_lean_bench_integration():
    """Test integration with lean-bench SDK."""
    print("Testing lean-bench SDK integration...")

    try:
        from minif2f_verifiers import LEAN_BENCH_AVAILABLE

        if LEAN_BENCH_AVAILABLE:
            print("✓ lean-bench SDK is available and integrated")

            # Test importing lean-bench functions
            from lean_bench import setup_lean_project, compile_lean_content
            print("✓ Successfully imported lean-bench functions")
        else:
            print("⚠ lean-bench SDK not available (running in standalone mode)")

        return True
    except Exception as e:
        print(f"✗ lean-bench integration test failed: {e}")
        return False

def test_verifiers_integration():
    """Test integration with verifiers framework."""
    print("Testing verifiers framework integration...")

    try:
        from minif2f_verifiers import VERIFIERS_AVAILABLE

        if VERIFIERS_AVAILABLE:
            print("✓ verifiers framework is available")

            # Test load_environment function
            from minif2f_verifiers import load_environment
            print("✓ load_environment function available")
        else:
            print("⚠ verifiers framework not available")
            print("  Install with: pip install verifiers")

        return True
    except Exception as e:
        print(f"✗ verifiers integration test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Running verifiers MiniF2F module tests...")
    print("=" * 50)

    tests = [
        test_verifiers_module_import,
        test_lean_check,
        test_parser,
        test_compiler_output,
        test_lean_bench_integration,
        test_verifiers_integration,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            print()

    print("=" * 50)
    print(f"Tests completed: {passed}/{total} passed")

    if passed == total:
        print("✓ All tests passed!")
        return True
    else:
        print("⚠ Some tests failed or had warnings")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)