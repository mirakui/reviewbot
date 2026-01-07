# Feature Specification: AI Code Review Agent

**Feature Branch**: `001-ai-code-review-agent`
**Created**: 2026-01-07
**Status**: Draft
**Input**: User description: "AI code review agent as GitHub App using AWS Bedrock AgentCore and Strands Agents SDK"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic PR Review (Priority: P1)

A developer opens a pull request in a repository that has the reviewbot GitHub App installed. The agent automatically triggers, reads the PR diff, analyzes the code changes, and posts review comments directly on the PR.

**Why this priority**: This is the core value proposition - automated code review on PRs. Without this, the product has no utility.

**Independent Test**: Can be fully tested by creating a PR in a test repository with the app installed. The agent should post at least one review comment within the configured timeout.

**Acceptance Scenarios**:

1. **Given** a repository with reviewbot GitHub App installed, **When** a developer opens a new PR, **Then** the agent triggers automatically and posts a review summary comment within 5 minutes.
2. **Given** a PR with code changes, **When** the agent analyzes the diff, **Then** it identifies potential issues (bugs, style, security) and posts inline comments on specific lines.
3. **Given** a PR with no issues, **When** the agent completes analysis, **Then** it posts a summary comment indicating the code looks good.
4. **Given** a PR with only documentation changes (.md files), **When** the agent analyzes the diff, **Then** it provides relevant feedback for documentation (clarity, accuracy) rather than code-specific feedback.

---

### User Story 2 - Custom Review Rules (Priority: P2)

A team wants to enforce specific coding standards and review criteria beyond general best practices. They configure custom rules that the agent uses to evaluate code changes.

**Why this priority**: Customization is essential for teams with specific coding standards, but the core review functionality must work first.

**Independent Test**: Can be tested by adding a `.claude/rules/*.md` file with custom rules (e.g., "All functions must have docstrings") and verifying the agent enforces these rules in reviews.

**Acceptance Scenarios**:

1. **Given** a repository with `.claude/rules/` directory containing rule files, **When** the agent performs a review, **Then** it incorporates those rules into its analysis.
2. **Given** multiple rule files in `.claude/rules/`, **When** the agent loads rules, **Then** it merges all `.md` files in alphabetical order.
3. **Given** a PR that violates a custom rule, **When** the agent analyzes the code, **Then** it specifically cites the violated rule in its comment.
4. **Given** no `.claude/rules/` directory exists, **When** the agent performs a review, **Then** it uses default best-practice guidelines without error.

---

### User Story 3 - Configurable Model Selection (Priority: P3)

A team wants to use a specific LLM model for their reviews based on cost, performance, or compliance requirements. They configure the model in the GitHub App settings or repository configuration.

**Why this priority**: Model flexibility is valuable but not essential for MVP. Default model works for most users.

**Independent Test**: Can be tested by configuring different models in the repository config and verifying the agent uses the specified model.

**Acceptance Scenarios**:

1. **Given** a repository with `model: anthropic.claude-4-sonnet` in config, **When** the agent runs, **Then** it uses Claude 4 Sonnet via Bedrock.
2. **Given** a repository with `model: amazon.nova-pro-v1` in config, **When** the agent runs, **Then** it uses Amazon Nova Pro.
3. **Given** no model specified in config, **When** the agent runs, **Then** it uses the default model (Claude 4 Sonnet).
4. **Given** an invalid model ID specified, **When** the agent attempts to run, **Then** it fails with a clear error message listing supported models.

---

### User Story 4 - GitHub App Installation (Priority: P1)

External repositories can use the reviewbot by installing it as a GitHub App, without needing to configure workflows or copy agent code into their repository.

**Why this priority**: GitHub App provides better security isolation, fine-grained permissions, and smoother installation UX. Critical for distribution.

**Independent Test**: Can be tested by installing the GitHub App on a test repository and verifying it triggers on PR events.

**Acceptance Scenarios**:

1. **Given** a repository owner, **When** they install the reviewbot GitHub App, **Then** the bot is activated without additional workflow configuration.
2. **Given** an installed GitHub App, **When** a PR is opened/updated, **Then** the app receives webhook events and has access to PR context.
3. **Given** the GitHub App installation, **When** the agent runs, **Then** it authenticates using the App's installation token (not user PAT or workflow token).
4. **Given** an installed app with re-review enabled, **When** new commits are pushed, **Then** the agent posts new review comments (previous comments remain).

---

### Edge Cases

- What happens when a PR has more than 100 changed files?
  - Agent processes all files but may take longer; status updates are posted to indicate progress.
- What happens when the PR diff is larger than the model's context window?
  - Agent splits the review into chunks, reviewing files in batches and aggregating results.
- How does system handle GitHub API rate limiting?
  - Implements exponential backoff with jitter; fails gracefully with informative error if limits exceeded.
- What happens when AWS Bedrock is unavailable?
  - Action fails with clear error message; does not block PR merge.
- What happens when `.claude/rules/` contains invalid markdown?
  - Agent logs a warning and continues with parseable rules; does not fail the entire review.
- What happens when the PR is from a fork?
  - Agent handles fork PRs but may have limited permissions for inline comments; falls back to summary comment.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST be deployable as a GitHub App that users can install into their repositories.
- **FR-002**: System MUST read PR metadata (number, title, description, author) from GitHub context.
- **FR-003**: System MUST fetch the full diff of changed files via GitHub API.
- **FR-004**: System MUST analyze code changes using an LLM via AWS Bedrock.
- **FR-005**: System MUST post review comments to the PR via GitHub API.
- **FR-006**: System MUST support inline comments on specific lines of code.
- **FR-007**: System MUST post a summary comment with overall review findings.
- **FR-008**: System MUST load custom review rules from `.claude/rules/*.md` in the repository root if present.
- **FR-009**: System MUST merge multiple rule files in alphabetical order.
- **FR-010**: System MUST allow model selection via action input parameter.
- **FR-011**: System MUST support at least: Claude 4 Sonnet, Claude 4 Haiku, Amazon Nova Pro, Amazon Nova Lite.
- **FR-012**: System MUST use Strands Agents SDK for agent orchestration.
- **FR-013**: System MUST use AWS Bedrock AgentCore Runtime for agent execution.
- **FR-014**: System MUST handle PRs of any size (no artificial file limits).
- **FR-015**: System MUST provide meaningful review feedback covering: bugs, security issues, code style, performance, and best practices.
- **FR-016**: System MUST support configurable re-review on push (enabled/disabled per installation).
- **FR-017**: System MUST authenticate using GitHub App installation tokens (not PAT or workflow tokens).
- **FR-018**: System MUST post comments only; it SHALL NOT approve PRs or request changes.
- **FR-019**: When re-reviewing, system MUST post new comments (previous comments remain visible).

### Non-Functional Requirements

- **NFR-001**: System MUST complete review within 10 minutes for PRs under 50 files.
- **NFR-002**: System MUST not store any code or PR content beyond the review session (stateless).
- **NFR-003**: System MUST authenticate with AWS using standard credential methods (env vars, IAM role).
- **NFR-004**: System MUST emit verbose structured logs including prompts sent to LLM (excluding code content from logs).
- **NFR-005**: System MUST gracefully handle transient failures with appropriate retries.
- **NFR-006**: System MUST log review metadata (timing, file counts, model used) in structured format (JSON) for debugging.

### Key Entities

- **PullRequest**: Represents a GitHub PR with metadata (number, title, description, base/head branches, author, files changed).
- **FileDiff**: Represents a single file's changes with path, patch content, additions/deletions.
- **ReviewComment**: A comment to be posted, either inline (with file path and line number) or summary.
- **ReviewRule**: A custom rule loaded from `.claude/rules/`, containing natural language instructions.
- **AgentConfig**: Configuration for the agent including model ID, timeout, and other settings.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Agent successfully posts review comments on 95% of triggered PRs (5% allowance for transient failures).
- **SC-002**: Average review completion time is under 3 minutes for PRs with fewer than 20 changed files.
- **SC-003**: Agent identifies at least one actionable issue in PRs that contain known anti-patterns (tested with synthetic PRs).
- **SC-004**: Custom rules are correctly applied in 100% of reviews where `.claude/rules/` is present.
- **SC-005**: External repositories can integrate via GitHub App installation (no workflow configuration required).
- **SC-006**: Agent runs correctly on serverless infrastructure without additional dependencies.

## Technical Context

**Language/Version**: Python 3.14
**Primary Dependencies**: Strands Agents SDK (strands-agents ^1.21), boto3, PyGithub
**Package Manager**: uv
**Linting/Formatting**: ruff (lint + format), mypy (type checking)
**Task Runner**: mise (stack setup + local workflows)
**AWS Services**: Bedrock AgentCore Runtime, Bedrock (model invocation)
**Testing**: pytest with moto for AWS mocking
**Target Platform**: AWS Lambda / serverless (webhook receiver)
**Deployment**: GitHub App with webhook endpoint hosted on AWS

## Architecture Notes

### AWS Bedrock AgentCore Integration

The agent leverages AgentCore Runtime for:
- Secure, isolated execution environment
- Pay-per-use pricing model
- Native integration with Strands Agents SDK

### Strands Agents SDK Usage

- Agent loop handles iterative reasoning over code changes
- Tools defined for: GitHub API interactions, diff parsing, comment posting
- Model provider configured for Bedrock with configurable model ID

### GitHub App Architecture

```
reviewbot/
├── app/
│   ├── webhook/            # GitHub webhook handler (Lambda)
│   ├── agent/              # Strands agent definition
│   ├── tools/              # Agent tools (GitHub, diff parsing)
│   ├── rules/              # Rule loading and parsing
│   └── main.py             # Entry point
├── infra/                  # AWS infrastructure (CDK/Terraform)
└── tests/
```

### GitHub App Configuration

- **Permissions**: Contents (read), Pull requests (read/write), Metadata (read)
- **Webhook Events**: `pull_request` (opened, synchronize), `issue_comment` (for `/review` commands)
- **Authentication**: JWT for App-level auth, Installation tokens for repo-level API calls

## Clarifications

### Session 2026-01-07

- Q: What security model for accessing repository content and posting comments? → A: GitHub App installation token (users install app into repositories)
- Q: Should the agent support re-review when new commits are pushed? → A: Configurable (on/off) via action input
- Q: Should the agent approve PRs or request changes? → A: Comments only, no approval or request-changes
- Q: How should re-review handle previous comments? → A: Post new comments each time (previous comments remain)
- Q: What level of logging/observability for debugging? → A: Verbose logs including prompts sent to LLM (excludes code content)

## Open Questions

~~1. Should the agent support re-review when new commits are pushed to the PR?~~ → Resolved: Configurable
~~2. Should there be a way to dismiss/acknowledge agent comments?~~ → Deferred: UX enhancement for post-MVP
~~3. Should the agent support review approval/request-changes in addition to comments?~~ → Resolved: Comments only
