# MiniF2F Example Implementation

This example demonstrates how to use the Lean Bench SDK for MiniF2F-specific operations.

## Overview

The MiniF2F implementation shows how to:

1. **Use the generic SDK** for benchmark-specific tasks
2. **Keep benchmark logic separate** from the core SDK
3. **Leverage SDK features** like caching, storage, and compilation
4. **Provide a clean interface** for MiniF2F operations

## Key Components

### `MiniF2FEnvironment`
Manages the MiniF2F project setup and file structure.

### `setup_minif2f()`
Sets up the MiniF2F environment with mathlib dependencies.

### `compile_minif2f_theorem()`
Compiles a MiniF2F theorem using the generic SDK compilation functions.

### `get_theorem_list()` / `extract_theorem_header()`
Utilities for working with MiniF2F theorem files.

## Usage Example

```python
# Set up MiniF2F environment
from examples.minif2f import setup_minif2f, compile_minif2f_theorem

# Initialize environment
success = setup_minif2f()
if not success:
    print("Failed to set up MiniF2F environment")
    exit(1)

# Compile a theorem
result = compile_minif2f_theorem(
    theorem_content="begin simp end",
    theorem_name="test_theorem",
    split="test"
)

print(f"Compilation success: {result['success']}")
if result['success']:
    print(f"Duration: {result['duration_ms']}ms")
    print(f"Cached: {result['cached']}")
else:
    print(f"Error: {result['error']}")
```

## Integration with Original Code

This implementation provides compatibility with the original `lean_compile()` function:

```python
# Original interface
def lean_compile(theorem_content, theorem_name, split, data_path):
    return compile_minif2f_theorem(
        theorem_content=theorem_content,
        theorem_name=theorem_name,
        split=split,
        minif2f_path=data_path
    )
```

## Benefits of Using the SDK

1. **Automatic caching** - Avoid recompiling identical content
2. **Structured storage** - Track all compilation attempts with metadata
3. **Error handling** - Robust error reporting and timeout management
4. **Async support** - Can be used with the HTTP API for remote compilation
5. **Monitoring** - Built-in statistics and health checks

## File Structure

```
examples/minif2f/
├── __init__.py          # Package exports
├── minif2f.py           # Main implementation
├── README.md            # This file
└── test_minif2f.py      # Example tests
```

## Notes

- This example assumes you have a MiniF2F repository set up
- The SDK handles all the low-level compilation details
- Benchmark-specific logic (imports, file parsing) stays in the example
- The core SDK remains generic and reusable