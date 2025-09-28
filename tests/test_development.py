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


if __name__ == "__main__":
    print("Running development tests for Lean Bench SDK...")
    print("=" * 50)

    try:
        test_lean_installation()
        test_diagnostic_parsing()
        test_project_setup()
        test_compiler_output()

        print("\n" + "=" * 50)
        print("All development tests passed! ✓")

    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)