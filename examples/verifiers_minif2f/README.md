# MiniF2F Verifiers Module

A complete verifiers framework integration for MiniF2F theorem proving across multiple formal languages: Lean, Isabelle, HOL Light, and Metamath.

## Overview

This module provides a verifiers-compatible environment for the MiniF2F benchmark. It integrates with the lean-bench SDK for enhanced Lean support while maintaining compatibility with the full verifiers framework.

## Features

- **Multi-language Support**: Lean, Isabelle, HOL Light, and Metamath
- **Verifiers Integration**: Complete compatibility with the verifiers framework
- **lean-bench SDK Integration**: Enhanced Lean compilation using the core SDK
- **Automatic Setup**: Handles environment setup and dependency management
- **Robust Parsing**: Extracts proofs from model outputs with multiple format support

## Installation

### Prerequisites

1. **Core Requirements**:
   ```bash
   pip install verifiers datasets
   ```

2. **Language-specific Tools** (install as needed):
   - **Lean**: Install [elan](https://github.com/leanprover/elan)
   - **Isabelle**: Install [Isabelle 2025](https://isabelle.in.tum.de/)
   - **HOL Light**: Install OCaml and the module will download HOL Light automatically
   - **Metamath**: Install [metamath-knife](http://metamath.org/)

### Setup

```bash
# Navigate to the verifiers module directory
cd examples/verifiers_minif2f

# Test the installation
python test_verifiers_module.py
```

## Usage

### Basic Usage with Verifiers Framework

```python
from examples.verifiers_minif2f import load_environment

# Load environment with all available languages
env = load_environment(languages=["all"])

# Load specific languages only
env = load_environment(languages=["lean", "isabelle"])

# Customize the environment
env = load_environment(
    languages=["lean"],
    num_eval_examples=10,
    system_prompt="Custom system prompt for theorem proving"
)
```

### Standalone Compilation

```python
from examples.verifiers_minif2f.minif2f_verifiers import (
    compile_proof,
    MiniF2FParser,
    CompilerOutput
)

# Parse a proof from model output
parser = MiniF2FParser()
proof = parser.parse_answer("```lean\nbegin sorry end\n```")

# Compile a proof
info = {
    "name": "theorem_name",
    "language": "lean",
    "split": "test"
}

result = compile_proof(
    language="lean",
    proof=proof,
    info=info,
    data_path="/path/to/minif2f"
)

print(f"Compilation successful: {result.returncode == 0}")
```

### Integration with lean-bench SDK

The module automatically integrates with the lean-bench SDK when available:

```python
# The module will use lean-bench SDK functions when available
from examples.verifiers_minif2f.minif2f_verifiers import lean_compile

# This will use lean-bench SDK's compile_lean_content if available,
# falling back to MiniF2F-specific compilation otherwise
result = lean_compile(
    theorem_content="begin sorry end",
    theorem_name="test_theorem",
    split="test",
    data_path="/path/to/minif2f"
)
```

## Environment Parameters

The `load_environment` function accepts these parameters:

- `languages` (list[str]): Languages to support. Options: `["lean", "hollight", "isabelle", "metamath", "all"]`
- `num_train_examples` (int): Number of training examples (-1 for all)
- `num_eval_examples` (int): Number of evaluation examples (-1 for all)
- `data_path` (str): Path to MiniF2F repository (auto-downloads if missing)
- `system_prompt` (str): Custom system prompt for models
- `**kwargs`: Additional arguments passed to `vf.SingleTurnEnv`

## Language-Specific Setup

### Lean

The module integrates with lean-bench SDK for enhanced Lean support:

- Uses `setup_lean_project()` for project initialization
- Uses `compile_lean_content()` for compilation when possible
- Falls back to MiniF2F-specific compilation for complex cases
- Automatic mathlib cache management

### Isabelle

- Creates proper session structure with ROOT files
- Handles theory file compilation in isolated environments
- Automatic cleanup of temporary directories

### HOL Light

- Auto-downloads and builds HOL Light if not present
- Supports both OPAM and manual installations
- Robust proof tactic extraction from model outputs

### Metamath

- Downloads required set.mm dependencies automatically
- Uses metamath-knife for verification
- Individual theorem file compilation

## File Structure

```
examples/verifiers_minif2f/
├── __init__.py                    # Module exports
├── minif2f_verifiers.py          # Main verifiers module
├── test_verifiers_module.py      # Test suite
└── README.md                     # This documentation
```

## Architecture

The module provides several layers of integration:

1. **Verifiers Layer**: `load_environment()` → `vf.SingleTurnEnv`
2. **Compilation Layer**: `compile_proof()` → Language-specific compilers
3. **SDK Integration Layer**: lean-bench SDK integration for Lean
4. **Parser Layer**: `MiniF2FParser` for extracting proofs from model outputs

## Testing

Run the test suite to verify everything is working:

```bash
cd examples/verifiers_minif2f
python test_verifiers_module.py
```

The tests verify:
- Module imports work correctly
- Language installations are detected
- Parser extracts proofs from various formats
- lean-bench SDK integration functions
- verifiers framework compatibility

## Error Handling

The module gracefully handles missing dependencies:

- **Missing verifiers**: Module works in standalone mode
- **Missing lean-bench SDK**: Falls back to direct Lean compilation
- **Missing languages**: Only available languages are used
- **Missing MiniF2F data**: Auto-downloads from GitHub

## Example: Complete Evaluation

```python
from examples.verifiers_minif2f import load_environment

# Load MiniF2F environment
env = load_environment(
    languages=["lean"],
    num_eval_examples=5
)

# Example model responses
responses = [
    "```lean\nbegin sorry end\n```",
    "```lean\nby simp\n```",
    # ... more responses
]

# Evaluate responses
total_score = 0
for i, response in enumerate(responses):
    if i < len(env.eval_dataset):
        score = env.rubric.evaluate(
            env.parser,
            response,
            info=env.eval_dataset[i]["info"]
        )
        total_score += score
        print(f"Example {i}: {score}")

print(f"Average score: {total_score / len(responses)}")
```

## Contributing

To add support for new languages:

1. Implement `{language}_check()`, `{language}_setup()`, and `{language}_compile()` functions
2. Add language to `ALL_MINIF2F_LANGUAGES` list
3. Update `compile_proof()` match statement
4. Add tests for the new language

## Troubleshooting

### Common Issues

1. **"No proof assistants properly installed"**
   - Install at least one proof assistant (Lean/elan recommended)
   - Verify installation with language-specific check functions

2. **"lean-bench SDK not available"**
   - This is normal if running standalone
   - The module will use direct compilation methods

3. **"verifiers framework not available"**
   - Install with `pip install verifiers`
   - Or use standalone compilation functions

4. **Compilation timeouts**
   - Increase timeout parameters in compiler functions
   - Check proof assistant installation and mathlib cache

### Debug Mode

Enable debug output by setting environment variables:

```bash
export EXPORT=1  # Exports compilation examples as JSON
python your_script.py
```

This creates JSON files with compilation examples for debugging.