# Quickstart: AI Code Review Agent

This guide helps you get the ReviewBot running locally for development and testing.

## Prerequisites

- [mise](https://mise.jdx.dev/) (manages Python 3.14, uv, and task workflows)
- AWS account with Bedrock access (Claude models enabled)
- GitHub account for creating test GitHub App
- ngrok or similar for webhook tunneling (local development)

## Quick Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <repo-url>
cd reviewbot

# Install toolchain via mise (Python 3.14, uv, etc.)
mise install

# Install dependencies via uv
uv sync

# Or install with dev dependencies
uv sync --dev
```

### 2. Configure AWS Credentials

```bash
# Option A: Environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_REGION="us-west-2"

# Option B: AWS CLI profile
aws configure --profile reviewbot
export AWS_PROFILE=reviewbot
```

**Required IAM permissions:**
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "arn:aws:bedrock:*:*:model/anthropic.*"
}
```

### 3. Create GitHub App (Development)

1. Go to GitHub Settings > Developer settings > GitHub Apps > New GitHub App
2. Configure:
   - **App name**: `reviewbot-dev-<your-username>`
   - **Homepage URL**: `https://github.com/your-org/reviewbot`
   - **Webhook URL**: Leave empty for now (update after ngrok setup)
   - **Webhook secret**: Generate a random string (save it!)

3. Set permissions:
   - **Repository permissions**:
     - Contents: Read
     - Issues: Write
     - Metadata: Read
     - Pull requests: Read & Write
   - **Subscribe to events**:
     - Pull request

4. After creation:
   - Note the **App ID**
   - Generate and download a **Private Key** (.pem file)

### 4. Configure Environment

Create `.env` file in project root:

```bash
# GitHub App
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# AWS Bedrock
AWS_REGION=us-west-2

# Optional: Override default model
# BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-20250514-v1:0

# Development
LOG_LEVEL=DEBUG
```

Or export directly:

```bash
export GITHUB_APP_ID=123456
export GITHUB_PRIVATE_KEY="$(cat /path/to/private-key.pem)"
export GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

### 5. Start Local Server

```bash
# Using mise task
mise run dev

# Or directly with uv
uv run python -m app.main

# Server runs on http://localhost:8000
```

### 6. Expose Webhook (Development)

```bash
# In another terminal, start ngrok
ngrok http 8000

# Note the HTTPS URL, e.g., https://abc123.ngrok.io
```

Update your GitHub App webhook URL to: `https://abc123.ngrok.io/webhook`

### 7. Install App on Test Repository

1. Go to your GitHub App settings
2. Click "Install App"
3. Select a test repository
4. Approve the installation

### 8. Test the Bot

1. Create a new branch in your test repository
2. Make some code changes
3. Open a pull request
4. Watch the ReviewBot post comments!

## Local Development Workflow

### Running Tests

```bash
# Using mise tasks
mise run test              # Run all tests
mise run test:unit         # Run unit tests only
mise run test:integration  # Run integration tests
mise run test:cov          # Run with coverage

# Or directly with uv
uv run pytest
uv run pytest --cov=app --cov-report=html
uv run pytest tests/unit/test_agent.py -v
```

### Linting and Formatting

```bash
# Using mise tasks
mise run lint              # Run linter
mise run lint:fix          # Auto-fix lint issues
mise run format            # Format code
mise run check             # Run all checks (lint + format + type)

# Or directly with uv + ruff
uv run ruff check app/ tests/
uv run ruff check --fix app/ tests/
uv run ruff format app/ tests/
uv run mypy app/
```

### Available mise Tasks

```bash
mise tasks                 # List all available tasks

# Common tasks
mise run dev               # Start development server
mise run test              # Run tests
mise run lint              # Run linter
mise run format            # Format code
mise run check             # Run all checks
mise run build             # Build for deployment
```

### Testing Webhook Locally

Use the GitHub webhook tester or curl:

```bash
# Simulate a PR opened event
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: sha256=$(echo -n '{}' | openssl dgst -sha256 -hmac 'your-secret' | cut -d' ' -f2)" \
  -d @tests/fixtures/pr_opened_event.json
```

### Debugging the Agent

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
export STRANDS_DEBUG=1
```

View agent reasoning:

```python
# In your code
from strands import Agent

def debug_callback(**kwargs):
    if "data" in kwargs:
        print(f"[Agent] {kwargs['data']}", end="", flush=True)
    if "current_tool_use" in kwargs:
        print(f"\n[Tool] {kwargs['current_tool_use']['name']}")

agent = Agent(..., callback_handler=debug_callback)
```

## Directory Structure

```
reviewbot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── webhook/             # Webhook handling
│   ├── agent/               # Strands agent
│   ├── tools/               # Agent tools
│   ├── rules/               # Rule loading
│   ├── models/              # Data models
│   └── utils/               # Utilities
├── tests/
│   ├── conftest.py
│   ├── fixtures/            # Test data
│   ├── unit/
│   ├── integration/
│   └── contract/
├── infra/                   # AWS infrastructure
├── .mise.toml               # mise configuration
├── pyproject.toml           # Python project config (uv)
├── .env.example
└── README.md
```

## Common Issues

### "Model access denied" error

Ensure you have enabled the Claude model in AWS Bedrock:
1. Go to AWS Console > Bedrock > Model access
2. Request access to Anthropic Claude models
3. Wait for approval (usually instant)

### Webhook signature verification failed

Check that `GITHUB_WEBHOOK_SECRET` matches exactly what you configured in the GitHub App.

### "Installation not found" error

The GitHub App may not be installed on the repository. Check the app's installation settings.

### Rate limiting

The agent implements exponential backoff. If you hit rate limits during development:
- Reduce test frequency
- Use a smaller test repository
- Check AWS Bedrock quotas

### mise not finding Python

Run `mise install` to ensure Python 3.14 is installed, then `mise trust` if prompted.

## Next Steps

- Review [Architecture Notes](./spec.md#architecture-notes) for system design
- See [Data Model](./data-model.md) for entity definitions
- Check [API Contracts](./contracts/) for endpoint specifications
- Read [Research](./research.md) for technical decisions

## Getting Help

- Check existing issues in the repository
- Review the spec.md for requirements clarification
- Contact the maintainers for access issues
