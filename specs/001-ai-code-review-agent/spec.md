# Feature Specification: AI Code Review Agent

**Feature Branch**: `001-ai-code-review-agent`
**Created**: 2026-01-07
**Status**: Draft
**Input**: User description: "AI code review agent as GitHub Action using AWS Bedrock AgentCore and Strands Agents SDK"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic PR Review (Priority: P1)

A developer opens a pull request in a repository that has the reviewbot GitHub Action configured. The agent automatically triggers, reads the PR diff, analyzes the code changes, and posts review comments directly on the PR.

**Why this priority**: This is the core value proposition - automated code review on PRs. Without this, the product has no utility.

**Independent Test**: Can be fully tested by creating a PR in a test repository with the action installed. The agent should post at least one review comment within the configured timeout.

**Acceptance Scenarios**:

1. **Given** a repository with reviewbot action configured in `.github/workflows/`, **When** a developer opens a new PR, **Then** the agent triggers automatically and posts a review summary comment within 5 minutes.
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

A team wants to use a specific LLM model for their reviews based on cost, performance, or compliance requirements. They configure the model in the GitHub Action workflow.

**Why this priority**: Model flexibility is valuable but not essential for MVP. Default model works for most users.

**Independent Test**: Can be tested by configuring different models in the action workflow and verifying the agent uses the specified model.

**Acceptance Scenarios**:

1. **Given** an action workflow with `model: anthropic.claude-4-sonnet` configured, **When** the agent runs, **Then** it uses Claude 4 Sonnet via Bedrock.
2. **Given** an action workflow with `model: amazon.nova-pro-v1` configured, **When** the agent runs, **Then** it uses Amazon Nova Pro.
3. **Given** no model specified in the workflow, **When** the agent runs, **Then** it uses the default model (Claude 4 Sonnet).
4. **Given** an invalid model ID specified, **When** the agent attempts to run, **Then** it fails with a clear error message listing supported models.

---

### User Story 4 - External Repository Integration (Priority: P1)

External repositories can use the reviewbot by referencing it as a reusable GitHub Action in their workflows, without needing to copy the agent code into their repository.

**Why this priority**: This is how GitHub Actions work - the action must be callable from external repos. Critical for distribution.

**Independent Test**: Can be tested by creating a separate repository that references `uses: <owner>/reviewbot@v1` and verifying it works.

**Acceptance Scenarios**:

1. **Given** an external repository, **When** a developer adds `uses: <owner>/reviewbot@v1` to their workflow, **Then** the action is available without additional setup.
2. **Given** a workflow using the action, **When** the action runs, **Then** it has access to the PR context (number, diff, files changed).
3. **Given** AWS credentials configured as repository secrets, **When** the action runs, **Then** it can authenticate with Bedrock AgentCore.
4. **Given** the action is referenced with a specific version tag (e.g., `@v1.2.0`), **When** it runs, **Then** it uses that exact version of the agent.

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

- **FR-001**: System MUST be deployable as a GitHub Action callable via `uses:` syntax from external repositories.
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

### Non-Functional Requirements

- **NFR-001**: System MUST complete review within 10 minutes for PRs under 50 files.
- **NFR-002**: System MUST not store any code or PR content beyond the review session (stateless).
- **NFR-003**: System MUST authenticate with AWS using standard credential methods (env vars, IAM role).
- **NFR-004**: System MUST log review actions for debugging without exposing sensitive code content.
- **NFR-005**: System MUST gracefully handle transient failures with appropriate retries.

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
- **SC-005**: External repositories can integrate the action with only workflow file changes (no code copying).
- **SC-006**: Action works correctly on GitHub-hosted runners (ubuntu-latest) without additional dependencies.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Strands Agents SDK (strands-agents ^1.21), boto3, PyGithub
**AWS Services**: Bedrock AgentCore Runtime, Bedrock (model invocation)
**Testing**: pytest with moto for AWS mocking
**Target Platform**: GitHub Actions runner (ubuntu-latest)
**Deployment**: GitHub Action (Docker container or composite action)

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

### GitHub Action Structure

```
reviewbot/
├── action.yml              # GitHub Action metadata
├── Dockerfile              # Container for action execution
├── src/
│   ├── agent/              # Strands agent definition
│   ├── tools/              # Agent tools (GitHub, diff parsing)
│   ├── rules/              # Rule loading and parsing
│   └── main.py             # Entry point
└── tests/
```

## Open Questions

1. Should the agent support re-review when new commits are pushed to the PR?
2. Should there be a way to dismiss/acknowledge agent comments?
3. Should the agent support review approval/request-changes in addition to comments?
