.PHONY: install check contract contract-verify run

# Install runtime + dev dependencies.
install:
	uv sync --group dev

# Full local gate: lint (ruff), type-check (mypy strict), tests (pytest).
# Generated contract artifacts are excluded from ruff + mypy via pyproject.
check:
	uv run ruff check . && uv run mypy src/ && uv run pytest

# Regenerate the API contract package from the committed OpenAPI snapshot.
# Emits _generated_paths.py, _generated_enums.py, and _generated_models.py.
contract:
	uv run python scripts/gen_contract.py

# CI-only: fail if the committed contract artifacts are stale. Separate from
# `check` so local runs do not depend on git state.
contract-verify:
	$(MAKE) contract && git diff --exit-code contract/ src/kidney_genetics_mcp/contract/

# Run the MCP server (streamable-HTTP on KGDB_MCP_PORT, default 8789).
run:
	uv run kidney-genetics-mcp
