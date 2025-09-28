#!/usr/bin/env python3
"""
Example usage of the MiniF2F verifiers module.

This script demonstrates how to use the module both with and without
the verifiers framework.
"""

import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def example_standalone_compilation():
    """Example of standalone compilation without verifiers framework."""
    print("=== Standalone Compilation Example ===")

    from minif2f_verifiers import (
        MiniF2FParser,
        compile_proof,
        lean_check,
        CompilerOutput
    )

    # Check if Lean is available
    if not lean_check():
        print("Lean not available, skipping Lean examples")
        return

    # Create parser
    parser = MiniF2FParser()

    # Example model outputs to parse
    model_outputs = [
        "```lean\nbegin sorry end\n```",
        "```lean\nby simp\n```",
        "Here's my proof: ```lean\nbegin\n  sorry\nend\n```",
        "No code block here, just text"
    ]

    print("Testing parser on various model outputs:")
    for i, output in enumerate(model_outputs):
        parsed = parser.parse_answer(output)
        print(f"  Output {i+1}: {parsed}")

    # Example compilation (requires MiniF2F data)
    print("\nTesting compilation (requires MiniF2F setup):")

    # This would normally require actual MiniF2F data
    # For demo purposes, we'll show the structure
    example_info = {
        "name": "example_theorem",
        "language": "lean",
        "split": "test"
    }

    # Note: This will fail without proper MiniF2F setup, but shows the interface
    try:
        result = compile_proof(
            language="lean",
            proof="begin sorry end",
            info=example_info,
            data_path="/tmp/fake_minif2f_path"  # This path doesn't exist
        )
        print(f"  Compilation result: {result.returncode}")
    except Exception as e:
        print(f"  Compilation failed as expected (no MiniF2F data): {type(e).__name__}")

def example_verifiers_integration():
    """Example of integration with verifiers framework."""
    print("\n=== Verifiers Framework Integration Example ===")

    try:
        from minif2f_verifiers import load_environment, VERIFIERS_AVAILABLE

        if not VERIFIERS_AVAILABLE:
            print("Verifiers framework not available.")
            print("Install with: pip install verifiers")
            return

        print("Loading MiniF2F environment...")

        # This would download MiniF2F data if not present
        # For demo, we'll catch the error gracefully
        try:
            env = load_environment(
                languages=["lean"],  # Start with just Lean
                num_eval_examples=2,  # Small number for demo
                data_path="/tmp/demo_minif2f"  # Temporary path for demo
            )

            print(f"Environment loaded with {len(env.eval_dataset)} eval examples")
            print(f"System prompt: {env.system_prompt[:100]}...")

            # Example evaluation
            if env.eval_dataset:
                example_response = "```lean\nbegin sorry end\n```"
                score = env.rubric.evaluate(
                    env.parser,
                    example_response,
                    info=env.eval_dataset[0]["info"]
                )
                print(f"Example evaluation score: {score}")

        except Exception as e:
            print(f"Environment loading failed (expected without MiniF2F data): {type(e).__name__}")
            print("This is normal - the module would download MiniF2F data in a real scenario")

    except ImportError as e:
        print(f"Could not import verifiers components: {e}")

def example_lean_bench_integration():
    """Example of lean-bench SDK integration."""
    print("\n=== lean-bench SDK Integration Example ===")

    from minif2f_verifiers import LEAN_BENCH_AVAILABLE

    if LEAN_BENCH_AVAILABLE:
        print("lean-bench SDK is available - enhanced Lean support enabled")

        # Show that lean-bench functions are available
        from lean_bench import setup_lean_project, compile_lean_content
        print("✓ Can import lean-bench functions")

        # Example of setting up a Lean project
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir) / "test_project"

            print(f"Setting up Lean project at {project_path}")
            success = setup_lean_project(str(project_path), mathlib=False)
            print(f"Project setup success: {success}")

            if success:
                # Try a simple compilation
                try:
                    result = compile_lean_content(
                        content='def hello : String := "world"',
                        file_name="test.lean",
                        project_root=str(project_path)
                    )
                    print(f"Simple compilation success: {result.success}")
                except Exception as e:
                    print(f"Compilation error: {e}")
    else:
        print("lean-bench SDK not available - using standalone Lean support")

def main():
    """Run all examples."""
    print("MiniF2F Verifiers Module - Usage Examples")
    print("=" * 60)

    examples = [
        example_standalone_compilation,
        example_verifiers_integration,
        example_lean_bench_integration,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")
        print()

    print("=" * 60)
    print("Examples completed!")
    print("\nFor full functionality:")
    print("1. Install verifiers: pip install verifiers")
    print("2. Install proof assistants (Lean/elan recommended)")
    print("3. The module will auto-download MiniF2F data when needed")

if __name__ == "__main__":
    main()