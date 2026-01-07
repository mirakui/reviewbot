# Research: AI Code Review Agent

**Feature Branch**: `001-ai-code-review-agent`
**Date**: 2026-01-07

This document consolidates research findings for all technical unknowns identified during planning.

---

## Decision Summary

| Area | Decision | Rationale |
|------|----------|-----------|
| Agent Framework | Strands Agents SDK (strands-agents ^1.21) | AWS-native, Bedrock integration, simple tool definition |
| Deployment | AWS Lambda + API Gateway (not AgentCore Runtime) | Simpler MVP, lower complexity, familiar pattern |
| Model Provider | Amazon Bedrock with Claude Sonnet 4 default | Native Strands support, multi-model support |
| GitHub Auth | PyGithub + GitHub App installation tokens | Industry-standard, avoids PAT dependency |
| Large PRs | File-by-file parallel processing + map-reduce | Best balance of performance and complexity |
| Token Counting | Bedrock Count Tokens API + heuristic fallback | Accurate pre-request validation |

---

## 1. Strands Agents SDK

### Decision
Use Strands Agents SDK (`strands-agents ^1.21`) as the primary agent framework.

### Rationale
- **AWS Native**: Developed by AWS, powers Amazon Q Developer internally
- **Simple API**: Agent creation requires minimal boilerplate
- **Bedrock Integration**: Default model provider is Amazon Bedrock
- **Tool Definition**: Clean `@tool` decorator pattern with automatic schema generation
- **Streaming Support**: Built-in callback handlers and async streaming

### Alternatives Considered
- **LangChain**: More complex, heavier dependencies, less AWS-native
- **Custom Implementation**: Higher maintenance burden, reinventing wheel

### Key Implementation Patterns

```python
from strands import Agent, tool
from strands.models import BedrockModel

@tool
def get_pr_files(pr_number: int, repo: str) -> list[dict]:
    """Fetch files changed in a pull request.

    Args:
        pr_number: The pull request number
        repo: Repository in owner/name format
    """
    # Implementation
    pass

model = BedrockModel(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-west-2",
    temperature=0.3,
    streaming=True
)

agent = Agent(
    model=model,
    system_prompt="You are a code review specialist...",
    tools=[get_pr_files, post_comment, analyze_diff]
)
```

### Required IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "bedrock:InvokeModelWithResponseStream"
  ],
  "Resource": "arn:aws:bedrock:*:*:model/*"
}
```

---

## 2. AWS Bedrock AgentCore vs Lambda

### Decision
Use **AWS Lambda + API Gateway** for MVP, not AgentCore Runtime.

### Rationale
- **Simplicity**: Lambda is a well-understood pattern, fewer moving parts
- **Cost Predictability**: Lambda pricing is simpler to estimate
- **Quick Iteration**: No container build/deploy cycle for code changes
- **Migration Path**: Strands agents are portable; can migrate to AgentCore later if needed

### Alternatives Considered
- **AgentCore Runtime**: Better for long-running agents (up to 8 hours), but overkill for PR review (typically <10 min)
- **ECS/Fargate**: More infrastructure to manage

### AgentCore Future Consideration
AgentCore offers:
- Pay-per-actual-CPU (I/O wait is free)
- 8-hour session support
- MicroVM isolation

Consider migration when:
- Review sessions exceed Lambda timeout (15 min)
- Need more complex multi-agent orchestration
- Cost optimization becomes priority

---

## 3. GitHub App Authentication

### Decision
Use GitHub App with installation tokens via PyGithub.

### Rationale
- **Security**: No long-lived tokens; installation tokens auto-expire after 1 hour
- **Granular Permissions**: Request only needed permissions per installation
- **Better UX**: Users install app without configuring secrets

### Required Permissions
| Operation | Permission | Access Level |
|-----------|------------|--------------|
| Read PRs | `Pull requests` | Read |
| Get PR files/diff | `Pull requests` | Read |
| Post review comments | `Pull requests` | Write |
| Post timeline comments | `Issues` | Write |
| Read file contents | `Contents` | Read |

### Webhook Events
- `pull_request.opened`: Trigger review on new PR
- `pull_request.synchronize`: Trigger re-review on push (if enabled)

### Authentication Pattern
```python
from github import Auth, GithubIntegration

def get_github_client(installation_id: int) -> Github:
    auth = Auth.AppAuth(APP_ID, PRIVATE_KEY)
    gi = GithubIntegration(auth=auth)
    return gi.get_github_for_installation(installation_id)
```

### Signature Verification
```python
import hmac
import hashlib

def verify_webhook(body: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

## 4. Large PR Handling Strategy

### Decision
Use file-by-file parallel processing with map-reduce aggregation.

### Rationale
- **Scalability**: Handles PRs of any size by processing files independently
- **Performance**: Parallel execution reduces total review time
- **Quality**: Focused context per file improves review quality
- **Simplicity**: Easier to implement than Chain-of-Agents pattern

### Strategy Selection
| PR Size | Strategy |
|---------|----------|
| < 300 LOC | Single request (all files in one prompt) |
| 300-1,500 LOC | File-by-file parallel |
| > 1,500 LOC | File-by-file parallel + chunking for large files |

### Token Management
```python
# Use Bedrock Count Tokens API
response = bedrock_runtime.count_tokens(
    modelId='anthropic.claude-sonnet-4-20250514-v1:0',
    body={"messages": [...], "system": system_prompt}
)

# Fallback heuristic: ~4 chars per token for code
estimated_tokens = len(content) // 4
```

### Aggregation Pipeline
1. **Map Phase**: Review each file independently (parallel)
2. **Filter Phase**: Deduplicate findings, remove low-confidence items
3. **Reduce Phase**: Synthesize into summary + inline comments

---

## 5. Supported Models

### Decision
Support multiple models with Claude Sonnet 4 as default.

### Rationale
- **Flexibility**: Teams can choose based on cost/performance/compliance
- **Bedrock Native**: All models available through unified Bedrock API

### Supported Models
| Model ID | Provider | Use Case |
|----------|----------|----------|
| `anthropic.claude-sonnet-4-20250514-v1:0` | Anthropic | Default - best quality/cost balance |
| `anthropic.claude-haiku-4-20251015-v1:0` | Anthropic | Fast, cost-effective for simple reviews |
| `amazon.nova-pro-v1:0` | Amazon | Alternative, good for multi-language |
| `amazon.nova-lite-v1:0` | Amazon | Budget option |

### Configuration Pattern
```python
model_configs = {
    "claude-sonnet": "anthropic.claude-sonnet-4-20250514-v1:0",
    "claude-haiku": "anthropic.claude-haiku-4-20251015-v1:0",
    "nova-pro": "amazon.nova-pro-v1:0",
    "nova-lite": "amazon.nova-lite-v1:0",
}
```

---

## 6. Custom Rules Loading

### Decision
Load rules from `.claude/rules/*.md` files, merged alphabetically.

### Rationale
- **Simplicity**: Plain markdown files, no special syntax
- **Version Control**: Rules stored in repo, reviewed with code
- **Flexibility**: Multiple files allow organizing rules by category

### Implementation
```python
from pathlib import Path

def load_custom_rules(repo_root: Path) -> str:
    rules_dir = repo_root / ".claude" / "rules"
    if not rules_dir.exists():
        return ""

    rules_files = sorted(rules_dir.glob("*.md"))
    rules_content = []
    for f in rules_files:
        rules_content.append(f.read_text())

    return "\n\n---\n\n".join(rules_content)
```

---

## Open Technical Decisions

All critical technical decisions have been resolved. No remaining NEEDS CLARIFICATION items.

---

## Sources

- [Strands Agents Documentation](https://strandsagents.com/latest/documentation/docs/)
- [AWS Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps/creating-github-apps)
- [PyGithub Documentation](https://pygithub.readthedocs.io/)
- [AWS Bedrock Count Tokens API](https://docs.aws.amazon.com/bedrock/latest/userguide/count-tokens.html)
