# reviewbot Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-07

## Active Technologies

- Python 3.14 + Strands Agents SDK (strands-agents ^1.21), boto3, PyGithub (001-ai-code-review-agent)

## Project Structure

```text
app/
├── webhook/
├── agent/
├── tools/
├── rules/
├── models/
└── utils/
tests/
├── unit/
├── integration/
└── contract/
infra/
```

## Commands

```bash
# Setup (via mise)
mise install                    # Install Python 3.14, uv
uv sync --dev                   # Install dependencies

# Development
mise run dev                    # Start development server
uv run python -m app.main       # Alternative: run directly

# Testing
uv run pytest                   # Run all tests
uv run pytest tests/unit/       # Run unit tests only
uv run pytest --cov=app         # Run with coverage

# Linting & Formatting (ruff)
uv run ruff check app/ tests/   # Lint
uv run ruff check --fix app/    # Auto-fix lint issues
uv run ruff format app/ tests/  # Format code

# Type checking
uv run mypy app/
```

## Code Style

Python 3.14: Follow standard conventions, enforced by ruff

## Recent Changes

- 001-ai-code-review-agent: Added Python 3.14 + Strands Agents SDK (strands-agents ^1.21), boto3, PyGithub

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
