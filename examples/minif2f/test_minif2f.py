#!/usr/bin/env python3
"""
Test the MiniF2F example implementation.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from minif2f import (
    MiniF2FEnvironment,
    compile_minif2f_theorem,
    get_minif2f_stats,
    get_theorem_list,
    extract_theorem_header,
    extract_theorem_proof_body,
    setup_minif2f,
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
    theorem_pattern = r"theorem\s+([a-zA-Z_][a-zA-Z0-9_]*)"
    theorems = re.findall(theorem_pattern, mock_content)

    assert "test_theorem" in theorems
    assert "another_theorem" in theorems
    print(f"  Found theorems: {theorems}")

    # Test proof body extraction
    test_proofs = [
        "begin simp end",
        "by simp",
        "by norm_num",
        "exact rfl",
        "simp",
    ]
    
    for proof in test_proofs:
        extracted = extract_theorem_proof_body(proof)
        assert extracted is not None
        print(f"  Extracted proof '{proof}' -> '{extracted}'")

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

    # Import the compatibility function
    from minif2f import lean_compile

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


def test_real_minif2f_setup():
    """Test real MiniF2F setup (optional - requires internet)."""
    print("\nTesting real MiniF2F setup...")
    
    # Use a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        test_path = Path(temp_dir) / "test_minif2f"
        
        try:
            print(f"  Setting up MiniF2F in {test_path}")
            success = setup_minif2f(test_path)
            
            if success:
                print("  ✓ MiniF2F setup succeeded")
                
                # Test getting theorem lists
                valid_theorems = get_theorem_list("valid", test_path)
                test_theorems = get_theorem_list("test", test_path)
                
                print(f"  Found {len(valid_theorems)} valid theorems")
                print(f"  Found {len(test_theorems)} test theorems")
                
                if valid_theorems:
                    # Test extracting a theorem header
                    first_theorem = valid_theorems[0]
                    header = extract_theorem_header(first_theorem, "valid", test_path)
                    if header:
                        print(f"  ✓ Successfully extracted header for {first_theorem}")
                    else:
                        print(f"  ⚠ Could not extract header for {first_theorem}")
                
                # Test stats
                stats = get_minif2f_stats(test_path)
                print(f"  Stats: {stats}")
                
                print("  ✓ Real MiniF2F tests passed")
            else:
                print("  ⚠ MiniF2F setup failed (this is okay if no internet/git)")
                
        except Exception as e:
            print(f"  ⚠ Real MiniF2F test failed: {e} (this is okay if no internet/git)")


def test_simple_compilation():
    """Test a simple theorem compilation (mock)."""
    print("\nTesting simple compilation...")
    
    # Test with a very simple theorem that should parse correctly
    simple_proof_tests = [
        ("by simp", "by tactic"),
        ("begin simp end", "begin...end block"),
        ("exact rfl", "exact proof"),
        ("simp", "direct tactic"),
    ]
    
    for proof, description in simple_proof_tests:
        extracted = extract_theorem_proof_body(proof)
        assert extracted is not None, f"Failed to extract {description}"
        print(f"  ✓ {description}: '{proof}' -> '{extracted}'")
    
    print("  ✓ Simple compilation tests passed")


if __name__ == "__main__":
    print("Running MiniF2F example tests...")
    print("=" * 50)

    try:
        test_minif2f_environment()
        test_theorem_extraction()
        test_compilation_interface()
        test_compatibility_interface()
        test_simple_compilation()
        
        # Optional test that requires internet
        try:
            test_real_minif2f_setup()
        except Exception as e:
            print(f"  ⚠ Real MiniF2F test skipped: {e}")

        print("\n" + "=" * 50)
        print("All MiniF2F example tests passed! ✓")

    except Exception as e:
        print(f"\nMiniF2F test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
