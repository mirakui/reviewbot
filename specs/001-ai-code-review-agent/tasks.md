# Tasks: AI Code Review Agent

**Input**: Design documents from `/specs/001-ai-code-review-agent/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included per TDD style development rules in CLAUDE.md (t_wada style - write failing tests first)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md project structure:
- **Source**: `app/` at repository root
- **Tests**: `tests/` at repository root
- **Infrastructure**: `infra/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per plan.md layout (app/, tests/, infra/ directories)
- [ ] T002 Initialize Python 3.14 project with pyproject.toml (uv sync)
- [ ] T003 [P] Add core dependencies: strands-agents ^1.21, boto3, PyGithub
- [ ] T004 [P] Add dev dependencies: pytest, moto, ruff, mypy
- [ ] T005 [P] Configure ruff (lint + format) in pyproject.toml
- [ ] T006 [P] Configure mypy (type checking) in pyproject.toml
- [ ] T007 [P] Configure mise tasks in .mise.toml (dev, test, lint, format, check)
- [ ] T008 [P] Create .env.example with required environment variables
- [ ] T009 Create pytest conftest.py with basic fixtures in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Phase

- [ ] T010 [P] Unit test for structured JSON logging in tests/unit/test_logging.py
- [ ] T011 [P] Unit test for retry with backoff utility in tests/unit/test_retry.py

### Implementation for Foundational Phase

- [ ] T012 [P] Implement structured JSON logging in app/utils/logging.py
- [ ] T013 [P] Implement retry with backoff decorator in app/utils/retry.py
- [ ] T014 [P] Create app/__init__.py with package metadata
- [ ] T015 [P] Create app/utils/__init__.py with utility exports
- [ ] T016 [P] Create app/models/__init__.py with model exports
- [ ] T017 [P] Create app/webhook/__init__.py
- [ ] T018 [P] Create app/agent/__init__.py
- [ ] T019 [P] Create app/tools/__init__.py
- [ ] T020 [P] Create app/rules/__init__.py
- [ ] T021 Create tests/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 4 - GitHub App Installation (Priority: P1) 🎯 MVP

**Goal**: Enable external repositories to install reviewbot as a GitHub App with webhook handling

**Independent Test**: Install the GitHub App on a test repository and verify it receives and validates webhook events from PR operations.

**Why P1**: GitHub App provides the security model, authentication, and event delivery mechanism that all other user stories depend on. Without this, we cannot receive PR events or authenticate to GitHub API.

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [P] [US4] Unit test for webhook signature verification in tests/unit/test_webhook.py
- [ ] T023 [P] [US4] Unit test for PR event parsing in tests/unit/test_webhook.py
- [ ] T024 [P] [US4] Unit test for ping event handling in tests/unit/test_webhook.py
- [ ] T025 [P] [US4] Contract test for webhook API per webhook-api.yaml in tests/contract/test_webhook_contract.py
- [ ] T026 [P] [US4] Integration test for webhook flow in tests/integration/test_webhook_flow.py

### Implementation for User Story 4

- [ ] T027 [P] [US4] Create PullRequest model in app/models/pull_request.py (from data-model.md)
- [ ] T028 [P] [US4] Create Installation model for GitHub App in app/models/config.py
- [ ] T029 [US4] Implement webhook signature validator in app/webhook/validators.py
- [ ] T030 [US4] Implement webhook event handler/dispatcher in app/webhook/handler.py
- [ ] T031 [US4] Create Lambda entry point in app/main.py with health check
- [ ] T032 [US4] Add webhook error handling and logging

**Checkpoint**: At this point, User Story 4 should be fully functional - webhooks are received, validated, and parsed

---

## Phase 4: User Story 1 - Basic PR Review (Priority: P1) 🎯 MVP

**Goal**: Automatically trigger code review when a PR is opened and post review comments

**Independent Test**: Create a PR in a test repository with the app installed. The agent should analyze the diff and post at least one review comment within 5 minutes.

**Why P1**: This is the core value proposition - automated code review on PRs.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T033 [P] [US1] Unit test for FileDiff model in tests/unit/test_models.py
- [ ] T034 [P] [US1] Unit test for ReviewComment model in tests/unit/test_models.py
- [ ] T035 [P] [US1] Unit test for diff parsing utilities in tests/unit/test_diff.py
- [ ] T036 [P] [US1] Unit test for GitHub API tools in tests/unit/test_github_tools.py
- [ ] T037 [P] [US1] Unit test for review agent in tests/unit/test_agent.py
- [ ] T038 [P] [US1] Contract test for GitHub API (file list, diff, comments) in tests/contract/test_github_api.py
- [ ] T039 [P] [US1] Integration test for full review flow in tests/integration/test_review_flow.py

### Implementation for User Story 1

- [ ] T040 [P] [US1] Create FileDiff model with FileStatus enum in app/models/file_diff.py
- [ ] T041 [P] [US1] Create ReviewComment model with CommentType, Severity, Category enums in app/models/comment.py
- [ ] T042 [P] [US1] Create ReviewSession model with ReviewState in app/models/session.py
- [ ] T043 [US1] Implement diff parsing utilities in app/tools/diff.py
- [ ] T044 [US1] Implement GitHub client factory (App auth, installation tokens) in app/tools/github.py
- [ ] T045 [US1] Implement get_pr_metadata tool in app/tools/github.py
- [ ] T046 [US1] Implement list_pr_files tool in app/tools/github.py
- [ ] T047 [US1] Implement get_file_diff tool in app/tools/github.py
- [ ] T048 [US1] Implement get_file_content tool in app/tools/github.py
- [ ] T049 [US1] Implement comment posting logic (inline + summary) in app/tools/comments.py
- [ ] T050 [US1] Implement post_review_comment tool in app/tools/comments.py
- [ ] T051 [US1] Implement post_summary_comment tool in app/tools/comments.py
- [ ] T052 [US1] Implement create_review tool in app/tools/comments.py
- [ ] T053 [US1] Create system prompts and templates in app/agent/prompts.py
- [ ] T054 [US1] Implement main review agent with Strands SDK in app/agent/reviewer.py
- [ ] T055 [US1] Integrate agent with webhook handler in app/main.py
- [ ] T056 [US1] Add review session logging and metrics

**Checkpoint**: At this point, User Story 1 should be fully functional - PRs trigger automated reviews with inline and summary comments

---

## Phase 5: User Story 2 - Custom Review Rules (Priority: P2)

**Goal**: Enable teams to configure custom coding standards via `.claude/rules/*.md` files

**Independent Test**: Add a `.claude/rules/docstrings.md` file with rule "All functions must have docstrings" and verify the agent enforces this in reviews.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T057 [P] [US2] Unit test for ReviewRule model in tests/unit/test_rules.py
- [ ] T058 [P] [US2] Unit test for rule loader (alphabetical merge, missing dir) in tests/unit/test_rules.py
- [ ] T059 [P] [US2] Integration test for custom rules in review in tests/integration/test_custom_rules.py

### Implementation for User Story 2

- [ ] T060 [P] [US2] Create ReviewRule model in app/models/rule.py
- [ ] T061 [US2] Implement rule loader from .claude/rules/*.md in app/rules/loader.py
- [ ] T062 [US2] Implement get_custom_rules tool in app/tools/github.py
- [ ] T063 [US2] Update agent prompts to incorporate custom rules in app/agent/prompts.py
- [ ] T064 [US2] Update reviewer agent to load and apply custom rules in app/agent/reviewer.py
- [ ] T065 [US2] Add logging for rule loading (warnings for invalid markdown)

**Checkpoint**: At this point, User Story 2 should be fully functional - custom rules are loaded and applied in reviews

---

## Phase 6: User Story 3 - Configurable Model Selection (Priority: P3)

**Goal**: Allow teams to select different LLM models based on cost, performance, or compliance requirements

**Independent Test**: Configure `model: amazon.nova-pro-v1:0` in repository config and verify the agent uses Amazon Nova Pro instead of default Claude.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T066 [P] [US3] Unit test for AgentConfig model (validation, defaults) in tests/unit/test_config.py
- [ ] T067 [P] [US3] Unit test for model ID validation in tests/unit/test_config.py
- [ ] T068 [P] [US3] Integration test for model switching in tests/integration/test_model_selection.py

### Implementation for User Story 3

- [ ] T069 [P] [US3] Create AgentConfig model with SUPPORTED_MODELS in app/models/config.py
- [ ] T070 [US3] Implement repository config loader (.reviewbot.yml) in app/utils/config_loader.py
- [ ] T071 [US3] Update reviewer agent to use configurable model in app/agent/reviewer.py
- [ ] T072 [US3] Add model validation with clear error messages for invalid IDs
- [ ] T073 [US3] Add logging for model selection

**Checkpoint**: At this point, User Story 3 should be fully functional - teams can configure different models

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T074 [P] Create test fixtures (sample webhook payloads, diffs) in tests/fixtures/
- [ ] T075 [P] Add edge case tests (large PRs, binary files, fork PRs) in tests/unit/
- [ ] T076 [P] Add rate limiting and exponential backoff for GitHub API in app/tools/github.py
- [ ] T077 [P] Add chunking strategy for large PRs (>50 files) in app/agent/reviewer.py
- [ ] T078 [P] Add Bedrock token counting integration in app/utils/tokens.py
- [ ] T079 Code cleanup and unused import removal
- [ ] T080 Run ruff format and ruff check --fix on entire codebase
- [ ] T081 Run mypy and fix all type errors
- [ ] T082 Run full test suite and ensure all tests pass
- [ ] T083 Run quickstart.md validation (manual setup verification)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 4 (Phase 3)**: Depends on Foundational - webhook infrastructure
- **User Story 1 (Phase 4)**: Depends on US4 (needs webhook events and GitHub auth)
- **User Story 2 (Phase 5)**: Depends on US1 (extends review with custom rules)
- **User Story 3 (Phase 6)**: Depends on US1 (extends agent with model selection)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

```
                    ┌──────────────┐
                    │   Setup      │
                    │  (Phase 1)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ Foundational │
                    │  (Phase 2)   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   US4 (P1)   │  GitHub App Installation
                    │  (Phase 3)   │  (webhook infrastructure)
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   US1 (P1)   │  Basic PR Review
                    │  (Phase 4)   │  (core review agent)
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼───────┐          ┌──────▼───────┐
       │   US2 (P2)   │          │   US3 (P3)   │
       │  (Phase 5)   │          │  (Phase 6)   │
       │ Custom Rules │          │ Model Select │
       └──────┬───────┘          └──────┬───────┘
              │                         │
              └────────────┬────────────┘
                           │
                    ┌──────▼───────┐
                    │    Polish    │
                    │  (Phase 7)   │
                    └──────────────┘
```

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (TDD - t_wada style)
2. Models before services/tools
3. Tools before agent integration
4. Core implementation before integration
5. Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**:
```bash
# All [P] tasks can run in parallel after T001-T002 complete:
T003, T004, T005, T006, T007, T008
```

**Phase 2 (Foundational)**:
```bash
# Tests in parallel:
T010, T011

# All __init__.py files in parallel:
T014, T015, T016, T017, T018, T019, T020

# Implementation after tests fail:
T012, T013
```

**Phase 3 (US4 - GitHub App)**:
```bash
# All tests in parallel:
T022, T023, T024, T025, T026

# Models in parallel:
T027, T028

# Then sequential: T029 → T030 → T031 → T032
```

**Phase 4 (US1 - Basic Review)**:
```bash
# All tests in parallel:
T033, T034, T035, T036, T037, T038, T039

# All models in parallel:
T040, T041, T042

# GitHub tools (sequential within, parallel across files):
T044 → T045 → T046 → T047 → T048 (github.py)
T049 → T050 → T051 → T052 (comments.py, can parallel with github.py)

# Agent (sequential):
T053 → T054 → T055 → T056
```

**Phase 5 (US2 - Custom Rules)**:
```bash
# Tests in parallel:
T057, T058, T059

# Then: T060 → T061 → T062 → T063 → T064 → T065
```

**Phase 6 (US3 - Model Selection)**:
```bash
# Tests in parallel:
T066, T067, T068

# Then: T069 → T070 → T071 → T072 → T073
```

**Phase 7 (Polish)**:
```bash
# Most tasks can run in parallel:
T074, T075, T076, T077, T078

# Sequential at end:
T079 → T080 → T081 → T082 → T083
```

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for FileDiff model in tests/unit/test_models.py"
Task: "Unit test for ReviewComment model in tests/unit/test_models.py"
Task: "Unit test for diff parsing utilities in tests/unit/test_diff.py"
Task: "Unit test for GitHub API tools in tests/unit/test_github_tools.py"
Task: "Unit test for review agent in tests/unit/test_agent.py"
Task: "Contract test for GitHub API in tests/contract/test_github_api.py"
Task: "Integration test for full review flow in tests/integration/test_review_flow.py"

# Launch all models for User Story 1 together:
Task: "Create FileDiff model with FileStatus enum in app/models/file_diff.py"
Task: "Create ReviewComment model with enums in app/models/comment.py"
Task: "Create ReviewSession model with ReviewState in app/models/session.py"
```

---

## Implementation Strategy

### MVP First (User Stories 4 + 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 4 (GitHub App Installation)
4. Complete Phase 4: User Story 1 (Basic PR Review)
5. **STOP and VALIDATE**: Test end-to-end by opening a PR
6. Deploy/demo if ready - MVP complete!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 4 → Webhook infrastructure ready
3. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
4. Add User Story 2 → Custom rules working → Deploy/Demo
5. Add User Story 3 → Model selection working → Deploy/Demo
6. Each story adds value without breaking previous stories

### Test-Driven Development (t_wada style)

For each user story:
1. Write ALL test tasks first (marked with [US#])
2. Run tests - ensure they FAIL (red)
3. Implement model/service/tool tasks
4. Run tests - ensure they PASS (green)
5. Refactor if needed
6. Move to next story

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD - t_wada style)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
