#!/usr/bin/env python3
"""
Test the MiniF2F example implementation.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from minif2f import (
    MiniF2FEnvironment,
    compile_minif2f_theorem,
    get_minif2f_stats,
)


def test_minif2f_environment():
    """Test MiniF2F environment management."""
    print("Testing MiniF2F environment...")

    test_path = Path("/tmp/test_minif2f_env")
    env = MiniF2FEnvironment(test_path)

    # Test initial state
    assert not env.is_setup()
    print("  ✓ Initial state detection works")

    # Test paths
    assert env.base_path == test_path
    assert env.lean_path == test_path / "lean"
    assert env.src_path == test_path / "lean" / "src"
    print("  ✓ Path structure correct")

    # Cleanup
    import shutil
    shutil.rmtree(test_path, ignore_errors=True)
    print("  ✓ MiniF2F environment tests passed")


def test_theorem_extraction():
    """Test theorem extraction functionality."""
    print("\nTesting theorem extraction...")

    # Create a mock theorem file
    mock_content = """
import data.real.basic

theorem test_theorem (x : ℝ) : x + 0 = x :=
by simp

theorem another_theorem : 1 + 1 = 2 :=
by norm_num

lemma helper_lemma : true :=
trivial
"""

    # Test theorem list extraction (would need actual file)
    # This is a simplified test
    import re
    theorem_pattern = r"theorem\s+(\w+)"
    theorems = re.findall(theorem_pattern, mock_content)

    assert "test_theorem" in theorems
    assert "another_theorem" in theorems
    print(f"  Found theorems: {theorems}")

    # Test header extraction
    from lean_bench.project import extract_theorem_header
    header = extract_theorem_header(mock_content, "test_theorem")
    assert header is not None
    assert "test_theorem" in header
    assert ":=" in header
    print(f"  Extracted header: {header}")

    print("  ✓ Theorem extraction tests passed")


def test_compilation_interface():
    """Test the compilation interface (mock)."""
    print("\nTesting compilation interface...")

    # This would require actual MiniF2F setup, so we'll do a mock test
    # In practice, you'd set up a test MiniF2F environment

    # Test error handling for missing environment
    result = compile_minif2f_theorem(
        theorem_content="begin simp end",
        theorem_name="nonexistent",
        split="test",
        minif2f_path="/nonexistent/path"
    )

    assert not result["success"]
    assert "not set up" in result["error"]
    print("  ✓ Error handling for missing environment works")

    # Test stats for missing environment
    stats = get_minif2f_stats("/nonexistent/path")
    assert not stats["setup"]
    print("  ✓ Stats for missing environment works")

    print("  ✓ Compilation interface tests passed")


def test_compatibility_interface():
    """Test compatibility with original lean_compile function."""
    print("\nTesting compatibility interface...")

    # Create a compatibility wrapper
    def lean_compile(theorem_content, theorem_name, split, data_path):
        """Compatibility wrapper for original interface."""
        return compile_minif2f_theorem(
            theorem_content=theorem_content,
            theorem_name=theorem_name,
            split=split,
            minif2f_path=data_path
        )

    # Test the wrapper
    result = lean_compile(
        theorem_content="begin simp end",
        theorem_name="test",
        split="test",
        data_path="/nonexistent"
    )

    # Should return the same format as the new function
    assert "success" in result
    assert not result["success"]  # Should fail for nonexistent path
    print("  ✓ Compatibility wrapper works")

    print("  ✓ Compatibility interface tests passed")


if __name__ == "__main__":
    print("Running MiniF2F example tests...")
    print("=" * 50)

    try:
        test_minif2f_environment()
        test_theorem_extraction()
        test_compilation_interface()
        test_compatibility_interface()

        print("\n" + "=" * 50)
        print("All MiniF2F example tests passed! ✓")

    except Exception as e:
        print(f"\nMiniF2F test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
