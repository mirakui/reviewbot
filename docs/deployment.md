# ReviewBot Deployment Guide

This guide covers deploying ReviewBot to Amazon Bedrock AgentCore Runtime using the CLI starter toolkit. It includes both local development setup and production deployment.

## Table of Contents

- [Prerequisites](#prerequisites)
- [GitHub App Setup](#github-app-setup)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Webhook Configuration](#webhook-configuration)
- [Testing the Deployment](#testing-the-deployment)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)

## Prerequisites

### AWS Requirements

- AWS account with configured credentials (`aws configure`)
- Access to Amazon Bedrock with Claude models enabled
- Permissions for AgentCore Runtime operations:
  - `bedrock-agentcore:*`
  - `iam:CreateRole`, `iam:AttachRolePolicy` (for first deployment)
  - `ecr:*` (for container deployment)
  - `codebuild:*` (for default deployment mode)
  - `logs:*` (for CloudWatch logging)

Enable Claude model access in the [Amazon Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess):

- `anthropic.claude-sonnet-4-20250514-v1:0` (default)
- `anthropic.claude-haiku-4-20251015-v1:0` (optional, for faster reviews)

### Local Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- [mise](https://mise.jdx.dev/) (optional, for task running)
- Git

### AgentCore Runtime Availability

AgentCore Runtime is available in the following AWS regions:

- US East (N. Virginia) - `us-east-1`
- US East (Ohio) - `us-east-2`
- US West (Oregon) - `us-west-2`
- Asia Pacific (Mumbai) - `ap-south-1`
- Asia Pacific (Singapore) - `ap-southeast-1`
- Asia Pacific (Sydney) - `ap-southeast-2`
- Asia Pacific (Tokyo) - `ap-northeast-1`
- Europe (Frankfurt) - `eu-central-1`
- Europe (Ireland) - `eu-west-1`

## GitHub App Setup

ReviewBot uses a GitHub App for authentication. This provides fine-grained permissions and automatic token management.

### Step 1: Create the GitHub App

1. Go to **GitHub Settings** > **Developer settings** > **GitHub Apps** > **New GitHub App**

2. Configure the app:

   | Field | Value |
   |-------|-------|
   | GitHub App name | `reviewbot-<your-org>` (must be unique) |
   | Homepage URL | Your organization URL or repository URL |
   | Webhook URL | Leave blank (configure after deployment) |
   | Webhook secret | Generate a secure secret (save for later) |

3. Set permissions:

   **Repository permissions:**
   | Permission | Access |
   |------------|--------|
   | Contents | Read |
   | Pull requests | Read and write |
   | Metadata | Read |

   **Subscribe to events:**
   - Pull request
   - Pull request review
   - Pull request review comment

4. Click **Create GitHub App**

### Step 2: Generate Private Key

1. After creation, scroll to **Private keys** section
2. Click **Generate a private key**
3. Save the downloaded `.pem` file securely

### Step 3: Install the App

1. Go to your GitHub App settings
2. Click **Install App** in the sidebar
3. Select your organization/account
4. Choose repositories (all or select specific ones)
5. Note the **Installation ID** from the URL after installation:
   ```
   https://github.com/settings/installations/<INSTALLATION_ID>
   ```

### Step 4: Note App Credentials

Collect the following values:

| Credential | Location |
|------------|----------|
| App ID | GitHub App settings page (under app name) |
| Private Key | Downloaded `.pem` file |
| Webhook Secret | Generated during app creation |
| Installation ID | URL after installing the app |

## Local Development

### Step 1: Clone and Setup

```bash
git clone <repository-url>
cd reviewbot

# Install dependencies using mise (recommended)
mise install
mise run dev:setup

# Or manually with uv
uv sync --all-extras
```

### Step 2: Configure Environment

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# AWS Configuration
AWS_REGION=us-west-2

# Logging (optional)
LOG_LEVEL=INFO
```

For local development, you can also use inline private key:

```bash
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
...key contents...
-----END RSA PRIVATE KEY-----"
```

### Step 3: Run Locally

```bash
# Using mise
mise run dev

# Or directly
uv run python -m app.agentcore
```

The agent starts on `http://localhost:8080`.

### Step 4: Test Local Agent

```bash
# Health check
curl http://localhost:8080/ping

# Test invocation
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, what can you help me with?"}'

# Test PR review (requires valid installation_id)
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "owner/repo",
    "pr_number": 123,
    "installation_id": 12345678
  }'
```

## Production Deployment

### Step 1: Install AgentCore CLI

```bash
uv pip install bedrock-agentcore-starter-toolkit

# Verify installation
agentcore --help
```

### Step 2: Configure AgentCore

```bash
agentcore configure -e app/agentcore.py -r us-west-2
```

This creates a `.bedrock_agentcore.yaml` configuration file. You can customize it:

```yaml
# .bedrock_agentcore.yaml
agent_name: reviewbot
entrypoint: app/agentcore.py
region: us-west-2
deployment_type: direct_code_deploy  # or 'container'
```

### Step 3: Set Environment Variables for Deployment

AgentCore agents access secrets via environment variables. Configure them before deployment:

```bash
# Export for the deployment process
export GITHUB_APP_ID=123456
export GITHUB_WEBHOOK_SECRET=your-webhook-secret

# For private key, use AWS Secrets Manager (recommended for production)
# Or inline as environment variable
export GITHUB_PRIVATE_KEY="$(cat /path/to/private-key.pem)"
```

### Step 4: Deploy to AgentCore Runtime

```bash
# Default deployment (recommended - uses CodeBuild, no Docker required)
agentcore launch

# Alternative: Local build (requires Docker)
agentcore launch --local-build
```

Deployment takes 2-5 minutes. Note the **Agent ARN** from the output:

```
Agent ARN: arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/reviewbot-abc123
```

### Step 5: Verify Deployment

```bash
# Check deployment status
agentcore status

# Test the deployed agent
agentcore invoke '{"prompt": "Hello!"}'
```

### Custom Execution Role (Optional)

If you need specific IAM permissions:

```bash
agentcore configure -e app/agentcore.py --execution-role arn:aws:iam::123456789012:role/ReviewBotRole
```

## Webhook Configuration

After deploying to AgentCore, configure GitHub to send webhooks to your agent.

### Step 1: Get Agent Endpoint

The AgentCore agent endpoint follows this pattern:

```
https://bedrock-agentcore.{region}.amazonaws.com/agents/{agent-id}/invocations
```

To invoke via webhook, you need to create an API Gateway or use AgentCore Gateway.

### Option A: Using AgentCore Gateway (Recommended)

AgentCore Gateway provides a managed webhook endpoint:

```bash
# Configure gateway for your agent
agentcore gateway configure --webhook-path /github/webhook
```

This provides a public endpoint like:

```
https://{gateway-id}.execute-api.{region}.amazonaws.com/github/webhook
```

### Option B: Using API Gateway

Create an API Gateway to proxy requests to AgentCore:

1. Create a new REST API in API Gateway
2. Create a POST method at `/webhook`
3. Configure Lambda proxy or direct integration to AgentCore
4. Deploy the API and note the endpoint URL

### Step 2: Update GitHub App Webhook URL

1. Go to your GitHub App settings
2. Update **Webhook URL** with your endpoint
3. Ensure **Webhook secret** matches `GITHUB_WEBHOOK_SECRET`
4. Save changes

### Step 3: Test Webhook

Create or update a pull request in a repository where the app is installed. Check CloudWatch logs to verify the webhook was received:

```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow
```

## Testing the Deployment

### Programmatic Invocation

Create a test script to invoke the deployed agent:

```python
#!/usr/bin/env python3
"""Test script for invoking ReviewBot on AgentCore."""

import json
import uuid
import boto3

# Replace with your agent ARN
AGENT_ARN = "arn:aws:bedrock-agentcore:us-west-2:123456789012:agent-runtime/reviewbot-abc123"

def invoke_agent(payload: dict) -> dict:
    """Invoke the ReviewBot agent."""
    client = boto3.client("bedrock-agentcore")

    response = client.invoke_agent_runtime(
        agentRuntimeArn=AGENT_ARN,
        runtimeSessionId=str(uuid.uuid4()),
        payload=json.dumps(payload).encode(),
        qualifier="DEFAULT",
    )

    content = []
    for chunk in response.get("response", []):
        content.append(chunk.decode("utf-8"))

    return json.loads("".join(content))


if __name__ == "__main__":
    # Test general query
    result = invoke_agent({"prompt": "What can you help me with?"})
    print("General query:", result)

    # Test PR review (requires valid credentials)
    result = invoke_agent({
        "repository": "owner/repo",
        "pr_number": 123,
        "installation_id": 12345678,
    })
    print("PR review:", result)
```

### Manual Webhook Test

Simulate a webhook event:

```bash
# Generate signature
PAYLOAD='{"action":"opened","number":1,"pull_request":{"number":1}}'
SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$GITHUB_WEBHOOK_SECRET" | cut -d' ' -f2)"

# Send test webhook
curl -X POST https://your-webhook-endpoint/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -H "X-GitHub-Delivery: test-$(uuidgen)" \
  -d "$PAYLOAD"
```

## Troubleshooting

### Common Issues

#### "Model access not enabled"

Enable Claude models in the [Bedrock console](https://console.aws.amazon.com/bedrock/home#/modelaccess).

#### "Signature verification failed"

- Verify `GITHUB_WEBHOOK_SECRET` matches the secret in GitHub App settings
- Ensure the webhook payload is not modified by proxies

#### "GitHub API rate limit exceeded"

- Check that installation tokens are being used (not PAT)
- Review the number of concurrent reviews

#### "Agent invocation timeout"

- Large PRs may exceed default timeout
- Consider increasing timeout or implementing chunked processing

### Viewing Logs

```bash
# CloudWatch logs
aws logs tail /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT \
  --filter-pattern "ERROR"
```

### Debug Mode

Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
export STRANDS_DEBUG=1
```

## Cleanup

Remove the deployed agent and associated resources:

```bash
agentcore destroy
```

This removes:

- AgentCore Runtime agent
- ECR repository (if container deployment)
- S3 bucket (if direct code deployment)
- IAM execution role (created by toolkit)

CloudWatch logs are retained. Delete manually if needed:

```bash
aws logs delete-log-group --log-group-name /aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT
```

## Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [AgentCore Starter Toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit)
- [Strands Agents SDK](https://strandsagents.com/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
