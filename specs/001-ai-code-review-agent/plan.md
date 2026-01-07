# Implementation Plan: AI Code Review Agent

**Branch**: `001-ai-code-review-agent` | **Date**: 2026-01-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-ai-code-review-agent/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Build an AI-powered code review agent deployed as a GitHub App that automatically reviews pull requests. The agent uses AWS Bedrock AgentCore Runtime with Strands Agents SDK to analyze code changes and post review comments directly on PRs. Users install the app into their repositories without requiring workflow configuration.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Strands Agents SDK (strands-agents ^1.21), boto3, PyGithub
**Package Manager**: uv
**Linting/Formatting**: ruff (lint + format), mypy (type checking)
**Task Runner**: mise (stack setup + local workflows)
**Storage**: N/A (stateless - no code/PR content stored beyond review session)
**Testing**: pytest with moto for AWS mocking
**Target Platform**: AWS Lambda (serverless webhook receiver)
**Project Type**: single (serverless backend)
**Performance Goals**: Review completion within 3 minutes for PRs <20 files; 10 minutes max for PRs <50 files
**Constraints**: Stateless execution, GitHub API rate limits, Bedrock context window limits
**Scale/Scope**: Arbitrary number of repo installations, PRs of any size (chunked if needed)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution not configured (template placeholders only in `.specify/memory/constitution.md`)

Since the constitution is not configured for this project, no explicit gates are enforced.
Default best practices apply:
- ✅ Single project structure (appropriate for serverless Lambda)
- ✅ Test coverage via pytest
- ✅ Structured logging (JSON format per NFR-006)
- ✅ Stateless design (no persistent storage needed)

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-code-review-agent/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
app/
├── __init__.py
├── main.py              # Lambda handler entry point
├── webhook/             # GitHub webhook handling
│   ├── __init__.py
│   ├── handler.py       # Webhook event dispatcher
│   └── validators.py    # Signature verification
├── agent/               # Strands agent definition
│   ├── __init__.py
│   ├── reviewer.py      # Main review agent
│   └── prompts.py       # System prompts and templates
├── tools/               # Agent tools
│   ├── __init__.py
│   ├── github.py        # GitHub API interactions
│   ├── diff.py          # Diff parsing utilities
│   └── comments.py      # Comment posting logic
├── rules/               # Custom rule handling
│   ├── __init__.py
│   └── loader.py        # .claude/rules/*.md loader
├── models/              # Data models
│   ├── __init__.py
│   ├── pull_request.py  # PR model
│   ├── file_diff.py     # File diff model
│   ├── comment.py       # Review comment model
│   └── config.py        # Agent configuration
└── utils/               # Shared utilities
    ├── __init__.py
    ├── logging.py       # Structured JSON logging
    └── retry.py         # Retry with backoff

infra/                   # AWS infrastructure (CDK or Terraform)
├── main.tf              # Terraform config (or CDK app)
└── variables.tf

tests/
├── __init__.py
├── conftest.py          # pytest fixtures
├── contract/            # Contract tests
│   └── test_github_api.py
├── integration/         # Integration tests
│   └── test_webhook_flow.py
└── unit/                # Unit tests
    ├── test_agent.py
    ├── test_diff.py
    ├── test_rules.py
    └── test_webhook.py
```

**Structure Decision**: Single serverless project structure selected. The architecture follows the spec's recommended layout with `app/` as the main package containing webhook handlers, agent definition, tools, and models. Infrastructure code is separated in `infra/`. This matches AWS Lambda best practices for Python applications.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations identified. The design follows minimal complexity:
- Single serverless function architecture
- No database or persistent storage
- Standard AWS Lambda + API Gateway pattern
- Direct GitHub API usage via PyGithub (no additional abstraction layers)

---

## Post-Design Constitution Check

*Re-evaluated after Phase 1 design completion.*

**Status**: PASS

| Principle | Status | Notes |
|-----------|--------|-------|
| Single project structure | ✅ | `app/` package with clear module boundaries |
| Test coverage | ✅ | Unit, integration, and contract tests defined |
| Structured logging | ✅ | JSON logging via `app/utils/logging.py` |
| Stateless design | ✅ | No persistent storage, session-scoped execution |
| Minimal dependencies | ✅ | Core deps: strands-agents, boto3, PyGithub |
| Clear data model | ✅ | 6 entities defined with validation rules |
| API contracts | ✅ | OpenAPI spec for webhook, agent tools spec |

**Design Decisions Validated**:
- AWS Lambda + API Gateway (vs AgentCore Runtime) - appropriate for MVP scope
- File-by-file parallel processing - balances complexity and scalability
- PyGithub for GitHub API - mature library, handles auth complexities

---

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Implementation Plan | `specs/001-ai-code-review-agent/plan.md` | ✅ Complete |
| Research | `specs/001-ai-code-review-agent/research.md` | ✅ Complete |
| Data Model | `specs/001-ai-code-review-agent/data-model.md` | ✅ Complete |
| Webhook API Contract | `specs/001-ai-code-review-agent/contracts/webhook-api.yaml` | ✅ Complete |
| Agent Tools Contract | `specs/001-ai-code-review-agent/contracts/agent-tools.yaml` | ✅ Complete |
| Quickstart Guide | `specs/001-ai-code-review-agent/quickstart.md` | ✅ Complete |
| Agent Context | `CLAUDE.md` | ✅ Updated |

---

## Next Steps

Run `/speckit.tasks` to generate the implementation task list (`tasks.md`).
