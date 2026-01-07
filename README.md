# ReviewBot

AI-powered code review agent for GitHub pull requests.

## Overview

ReviewBot is a GitHub App that automatically reviews pull requests using AI. It analyzes code changes and posts review comments directly on PRs.

## Quick Start

See [quickstart.md](specs/001-ai-code-review-agent/quickstart.md) for setup instructions.

## Development

```bash
# Install tools via mise
mise install

# Install dependencies
uv sync --dev

# Run tests
uv run pytest

# Run linter
uv run ruff check app/ tests/

# Format code
uv run ruff format app/ tests/
```

## License

MIT
