# Lean Benchmark SDK

A generic SDK for compiling and interacting with Lean projects, designed for benchmark implementations but suitable for any Lean development workflow.

## Features

- **Generic Lean compilation** - Works with any Lean project
- **Content-based caching** - Automatic caching to avoid redundant compilations
- **Structured storage** - Track compilation attempts with rich metadata
- **HTTP API** - RESTful interface for remote compilation
- **Pure functions** - Minimal state, easy to test and reason about
- **Benchmark-agnostic** - Core SDK has no benchmark-specific code

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd lean-bench-sdk

# Set up environment with uv
uv venv .venv -p 3.12
source .venv/bin/activate
uv pip install -e .
```

### Basic Usage

```python
from lean_bench import compile_lean_content, setup_lean_project

# Set up a Lean project
success = setup_lean_project("/path/to/project", mathlib=True)

# Compile some Lean code
result = compile_lean_content(
    content="def hello : String := \"world\"",
    file_name="test.lean",
    project_root="/path/to/project"
)

print(f"Success: {result.success}")
print(f"Duration: {result.duration_ms}ms")
```

### HTTP API

Start the API server:

```bash
python -m lean_bench.api
# or
uvicorn lean_bench.api:app --reload
```

Example API usage:

```bash
# Health check
curl http://localhost:8000/health

# Compile content
curl -X POST http://localhost:8000/compile/content \
  -H "Content-Type: application/json" \
  -d '{
    "content": "def test : Nat := 42",
    "file_name": "test.lean",
    "project_root": "/path/to/project"
  }'
```

## Architecture

### Core Components

- **`compiler.py`** - Generic Lean compilation functions
- **`project.py`** - Project setup and file management
- **`cache.py`** - Content-based caching system
- **`storage.py`** - Compilation attempt storage
- **`api.py`** - HTTP API endpoints

### Design Principles

1. **Pure functions** - All core functions take explicit parameters
2. **No hidden state** - Configuration passed explicitly
3. **Benchmark-agnostic** - No benchmark-specific logic in core SDK
4. **Composable** - Small functions that work together

## Examples

### MiniF2F Integration

The `examples/minif2f/` directory shows how to use the SDK for MiniF2F:

```python
from examples.minif2f import compile_minif2f_theorem

result = compile_minif2f_theorem(
    theorem_content="begin simp end",
    theorem_name="simple_theorem",
    split="test"
)
```

### MiniF2F Verifiers Module

The `examples/verifiers_minif2f/` directory provides a complete verifiers framework integration:

```python
from examples.verifiers_minif2f import load_environment

# Load MiniF2F environment with multiple languages
env = load_environment(languages=["lean", "isabelle", "hollight"])

# Evaluate model responses
score = env.rubric.evaluate(
    env.parser,
    "```lean\nby simp\n```",
    info=env.eval_dataset[0]["info"]
)
```

Features:
- **Multi-language support**: Lean, Isabelle, HOL Light, Metamath
- **Verifiers framework compatibility**: Drop-in replacement for verifiers environments
- **lean-bench SDK integration**: Enhanced Lean compilation using the core SDK
- **Automatic setup**: Downloads MiniF2F data and manages dependencies

### Custom Benchmarks

Create your own benchmark by:

1. Using the core SDK functions
2. Adding benchmark-specific parsing/setup logic
3. Keeping it in `examples/your_benchmark/`

## API Reference

### Core Functions

#### `compile_lean_content(content, file_name, project_root, dependencies=None, timeout=60)`
Compile Lean code provided as a string.

#### `compile_lean_file(file_path, project_root, timeout=60)`
Compile a specific Lean file.

#### `setup_lean_project(project_path, mathlib=False)`
Set up a new Lean project directory.

### Caching

#### `get_cached_result(cache_key)` / `store_cached_result(cache_key, result)`
Manual cache operations.

#### `cache_compilation_result(...)`
Generate cache key and check for cached results.

### Storage

#### `store_compilation_attempt(input_data, output_data, metadata=None)`
Store a compilation attempt with metadata.

#### `query_attempts(filters=None, limit=100)`
Query stored attempts with optional filters.

## HTTP API Endpoints

- `GET /health` - System health and status
- `POST /compile/content` - Compile Lean content
- `POST /compile/file` - Compile a Lean file
- `POST /project/setup` - Set up a new project
- `GET /project/{path}/files` - List project files
- `POST /compile/batch` - Batch compilation
- `GET /attempts` - Query compilation attempts

## Testing

Run all tests:

```bash
# Core SDK tests
python tests/test_development.py

# API tests
python tests/test_api.py

# Example tests
cd examples/minif2f && python test_minif2f.py

# Linting
ruff check src/ examples/ tests/
```

## Configuration

The SDK uses these default paths:
- Cache: `~/.lean-bench/cache`
- Storage: `~/.lean-bench/attempts`
- MiniF2F: `~/.lean-bench/minif2f`

Override by passing explicit paths to functions.

## Development

### Project Structure

```
lean-bench-sdk/
├── src/lean_bench/          # Core SDK
├── examples/                 # Benchmark implementations
├── tests/                    # Test suites
└── README.md                # This file
```

### Adding New Features

1. Add pure functions to appropriate core module
2. Add tests to `tests/test_development.py`
3. Update API endpoints if needed
4. Run linting and tests

### Benchmark Integration

To integrate a new benchmark:

1. Create `examples/your_benchmark/`
2. Use core SDK functions for compilation/storage
3. Add benchmark-specific parsing logic
4. Provide compatibility layer if needed

## Requirements

- Python 3.12+
- Lean 4 (via elan)
- Dependencies: FastAPI, pydantic, uvicorn
