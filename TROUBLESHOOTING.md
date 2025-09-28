# Troubleshooting Guide

## Environment Setup Issues

### Problem: `python` command not found after venv activation

This is the current blocking issue. The virtual environment appears to be created but the `python` command is not available.

#### Diagnosis Steps:
1. Check if venv was created properly:
   ```bash
   ls -la .venv/bin/
   ```
   Should show `python`, `python3`, `pip`, etc.

2. Check Python location in venv:
   ```bash
   ls -la .venv/bin/python*
   ```

3. Try direct path:
   ```bash
   .venv/bin/python --version
   ```

#### Solutions to Try:

**Option 1: Recreate venv**
```bash
rm -rf .venv
uv venv .venv -p 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
```

**Option 2: Use uv run instead of activation**
```bash
# Instead of activating, use uv run for everything
uv run python tests/test_development.py
uv run python tests/test_api.py
uv run python -m lean_bench.api
```

**Option 3: Check shell compatibility**
```bash
# Try with different shell activation
bash
source .venv/bin/activate
python --version
```

**Option 4: Manual PATH setup**
```bash
export PATH=".venv/bin:$PATH"
python --version
```

## Testing Issues

### If tests fail after environment fix:

1. **Import errors**: Make sure you're in project root and SDK is installed
2. **Lean not found**: Install Lean 4 via elan
3. **Permission errors**: Check file permissions for temp directories

## API Issues

### If HTTP API won't start:

1. **Port conflicts**: Try different port
   ```bash
   uv run uvicorn lean_bench.api:app --port 8001
   ```

2. **Dependency issues**: Reinstall with dev dependencies
   ```bash
   uv pip install -e ".[dev]"
   ```

## Development Commands

Once environment is working:

```bash
# Verify everything is installed
uv run python -c "import lean_bench; print('✓ SDK ready')"

# Run tests
uv run python tests/test_development.py
uv run python tests/test_api.py

# Start API server
uv run uvicorn lean_bench.api:app --reload

# Run linting
uv run ruff check src/ examples/ tests/

# MiniF2F example
cd examples/minif2f
uv run python test_minif2f.py
```

## Quick Environment Reset

If all else fails:
```bash
# Nuclear option - start fresh
rm -rf .venv
uv venv .venv -p 3.12
source .venv/bin/activate

# If activation still doesn't work, use uv run for everything
uv pip install -e ".[dev]"
uv run python tests/test_development.py
```