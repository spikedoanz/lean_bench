#!/usr/bin/env python3
"""
Test MiniF2F with LLM sampling using the verifiers framework.
This script uses GPT-4o to generate proof attempts and verifies them.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import verifiers and related modules
try:
    import verifiers as vf
    from openai import OpenAI
    VERIFIERS_AVAILABLE = True
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please install: pip install verifiers openai python-dotenv")
    sys.exit(1)

# Import the verifiers MiniF2F module
try:
    # Add parent directory to path to find verifiers_minif2f
    sys.path.insert(0, str(Path(__file__).parent.parent / "verifiers_minif2f"))
    from minif2f_verifiers import (
        load_environment,
        MiniF2FParser,
        compile_proof,
        VERIFIERS_AVAILABLE as VF_MODULE_AVAILABLE
    )
except ImportError as e:
    print(f"Could not import verifiers_minif2f module: {e}")
    print("Make sure the verifiers_minif2f module is in the parent directory")
    sys.exit(1)


def load_api_key():
    """Load OpenAI API key from ~/.env file."""
    env_path = Path.home() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print("✓ Loaded OpenAI API key from ~/.env")
            return api_key
    
    print("✗ No OpenAI API key found in ~/.env")
    print("  Please add OPENAI_API_KEY=your-key to ~/.env")
    return None


def test_llm_proof_generation():
    """Test LLM proof generation using GPT-4o with the verifiers framework."""
    print("\n" + "=" * 60)
    print("Testing LLM Proof Generation with GPT-4o")
    print("=" * 60)
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("Skipping LLM tests - no API key available")
        return False
    
    # Set up OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Create a temporary directory for MiniF2F data
    with tempfile.TemporaryDirectory() as temp_dir:
        minif2f_path = Path(temp_dir) / "minif2f"
        
        print(f"\n1. Loading MiniF2F environment...")
        print(f"   Path: {minif2f_path}")
        
        try:
            # Load the MiniF2F environment using verifiers
            env = load_environment(
                languages=["lean"],  # Focus on Lean for this test
                num_eval_examples=3,  # Small number for testing
                data_path=str(minif2f_path),
                system_prompt="You are an expert Lean theorem prover. Generate correct Lean proofs for the given theorems."
            )
            
            print(f"   ✓ Environment loaded with {len(env.eval_dataset)} eval examples")
            
        except Exception as e:
            print(f"   ✗ Failed to load environment: {e}")
            return False
        
        print("\n2. Sampling proofs from GPT-4o...")
        
        # Test with a few examples
        results = []
        for i, example in enumerate(env.eval_dataset.select(range(min(3, len(env.eval_dataset))))):
            print(f"\n   Example {i+1}:")
            print(f"   Theorem: {example['info']['name']}")
            
            # Get the prompt
            prompt = example['question']
            
            # Sample from GPT-4o
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": env.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                completion = response.choices[0].message.content
                print(f"   Generated proof attempt (truncated): {completion[:100]}...")
                
                # Parse the proof using the MiniF2F parser
                parser = env.parser
                parsed_proof = parser.parse_answer(completion)
                
                if parsed_proof:
                    print(f"   ✓ Successfully parsed proof from response")
                    
                    # Verify the proof using compilation
                    print(f"   Compiling proof...")
                    compiler_output = compile_proof(
                        language="lean",
                        proof=parsed_proof,
                        info=example['info'],
                        data_path=str(minif2f_path)
                    )
                    
                    if compiler_output.returncode == 0:
                        print(f"   ✓ Proof compiled successfully!")
                        results.append({
                            "theorem": example['info']['name'],
                            "success": True,
                            "proof": parsed_proof
                        })
                    else:
                        print(f"   ✗ Compilation failed")
                        print(f"     Error: {compiler_output.stderr[:200] if compiler_output.stderr else 'Unknown error'}")
                        results.append({
                            "theorem": example['info']['name'],
                            "success": False,
                            "error": "Compilation failed"
                        })
                else:
                    print(f"   ✗ Could not parse proof from LLM response")
                    results.append({
                        "theorem": example['info']['name'],
                        "success": False,
                        "error": "Parse failed"
                    })
                    
            except Exception as e:
                print(f"   ✗ Error during sampling: {e}")
                results.append({
                    "theorem": example['info']['name'] if 'info' in example else f"example_{i}",
                    "success": False,
                    "error": str(e)
                })
        
        # Summary
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"Total theorems tested: {len(results)}")
        print(f"Successful proofs: {sum(1 for r in results if r['success'])}")
        print(f"Failed proofs: {sum(1 for r in results if not r['success'])}")
        
        for result in results:
            status = "✓" if result['success'] else "✗"
            print(f"  {status} {result['theorem']}")
        
        return len(results) > 0


def test_verifiers_evaluation():
    """Test the full verifiers evaluation pipeline."""
    print("\n" + "=" * 60)
    print("Testing Verifiers Evaluation Pipeline")
    print("=" * 60)
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        print("Skipping evaluation tests - no API key available")
        return False
    
    # Set up OpenAI client
    client = OpenAI(api_key=api_key)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        minif2f_path = Path(temp_dir) / "minif2f"
        
        print("\n1. Loading environment for evaluation...")
        
        try:
            # Load environment with very small dataset for testing
            env = load_environment(
                languages=["lean"],
                num_eval_examples=2,  # Very small for quick test
                data_path=str(minif2f_path)
            )
            
            print(f"   ✓ Environment loaded")
            
            # Run evaluation using verifiers framework
            print("\n2. Running evaluation with GPT-4o...")
            
            results = env.evaluate(
                client=client,
                model="gpt-4o",
                num_examples=2,
                rollouts_per_example=1,
                max_concurrent=1
            )
            
            print(f"   ✓ Evaluation completed")
            
            # Display results
            print("\n3. Results:")
            if hasattr(results, 'rewards'):
                avg_reward = sum(results.rewards) / len(results.rewards) if results.rewards else 0
                print(f"   Average reward: {avg_reward:.2f}")
            
            # Create dataset from results
            dataset = env.make_dataset(results)
            print(f"   Generated dataset with {len(dataset)} examples")
            
            return True
            
        except Exception as e:
            print(f"   ✗ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all LLM tests."""
    print("MiniF2F LLM Testing Suite")
    print("=" * 60)
    
    # Check if verifiers is available
    if not VERIFIERS_AVAILABLE:
        print("✗ Verifiers framework not available")
        print("  Install with: pip install verifiers")
        return 1
    
    if not VF_MODULE_AVAILABLE:
        print("✗ Verifiers MiniF2F module not properly configured")
        return 1
    
    print("✓ Verifiers framework is available")
    print("✓ MiniF2F module is available")
    
    # Run tests
    tests = [
        ("LLM Proof Generation", test_llm_proof_generation),
        ("Verifiers Evaluation", test_verifiers_evaluation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 60)
    print("Final Test Summary:")
    print("=" * 60)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, s in results if s)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")
    
    return 0 if total_passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())