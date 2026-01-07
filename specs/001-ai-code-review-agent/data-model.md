# Data Model: AI Code Review Agent

**Feature Branch**: `001-ai-code-review-agent`
**Date**: 2026-01-07

This document defines the core entities, their relationships, validation rules, and state transitions for the AI code review agent.

---

## Entity Overview

```
┌─────────────────┐     1      N  ┌─────────────────┐
│  PullRequest    │──────────────>│    FileDiff     │
└─────────────────┘               └─────────────────┘
        │                                  │
        │ 1                                │ N
        │                                  │
        ▼ N                                ▼ N
┌─────────────────┐               ┌─────────────────┐
│  ReviewComment  │               │  ReviewComment  │
│   (Summary)     │               │    (Inline)     │
└─────────────────┘               └─────────────────┘

┌─────────────────┐               ┌─────────────────┐
│   ReviewRule    │               │   AgentConfig   │
└─────────────────┘               └─────────────────┘
```

---

## 1. PullRequest

Represents a GitHub pull request being reviewed.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `number` | int | Yes | PR number in the repository |
| `title` | str | Yes | PR title |
| `body` | str | No | PR description (may be empty) |
| `author` | str | Yes | GitHub username of PR author |
| `base_branch` | str | Yes | Target branch (e.g., "main") |
| `head_branch` | str | Yes | Source branch |
| `head_sha` | str | Yes | SHA of latest commit on head |
| `repository` | str | Yes | Full repo name (owner/repo) |
| `installation_id` | int | Yes | GitHub App installation ID |
| `html_url` | str | Yes | URL to PR on GitHub |
| `files_changed` | int | Yes | Number of files changed |
| `additions` | int | Yes | Lines added |
| `deletions` | int | Yes | Lines deleted |

### Validation Rules

- `number` must be positive integer
- `repository` must match pattern `^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$`
- `head_sha` must be 40-character hex string
- `installation_id` must be positive integer

### Python Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class PullRequest:
    number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    head_sha: str
    repository: str
    installation_id: int
    html_url: str
    files_changed: int
    additions: int
    deletions: int
    body: Optional[str] = None

    @classmethod
    def from_webhook_payload(cls, payload: dict) -> "PullRequest":
        pr = payload["pull_request"]
        return cls(
            number=payload["number"],
            title=pr["title"],
            body=pr.get("body"),
            author=pr["user"]["login"],
            base_branch=pr["base"]["ref"],
            head_branch=pr["head"]["ref"],
            head_sha=pr["head"]["sha"],
            repository=payload["repository"]["full_name"],
            installation_id=payload["installation"]["id"],
            html_url=pr["html_url"],
            files_changed=pr.get("changed_files", 0),
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
        )
```

---

## 2. FileDiff

Represents a single file's changes in a pull request.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `filename` | str | Yes | Path to file in repository |
| `status` | FileStatus | Yes | Type of change |
| `patch` | str | No | Unified diff patch content |
| `additions` | int | Yes | Lines added in this file |
| `deletions` | int | Yes | Lines deleted in this file |
| `sha` | str | Yes | Blob SHA of the file |
| `previous_filename` | str | No | Original name if renamed |

### FileStatus Enum

```python
from enum import Enum

class FileStatus(str, Enum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    COPIED = "copied"
    CHANGED = "changed"
    UNCHANGED = "unchanged"
```

### Validation Rules

- `filename` must not be empty
- `patch` may be None for binary files or very large files
- `additions` and `deletions` must be non-negative
- If `status` is `RENAMED`, `previous_filename` should be set

### Python Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileDiff:
    filename: str
    status: FileStatus
    additions: int
    deletions: int
    sha: str
    patch: Optional[str] = None
    previous_filename: Optional[str] = None

    @property
    def is_binary(self) -> bool:
        """Check if file appears to be binary (no patch available)."""
        return self.patch is None and self.status != FileStatus.REMOVED

    @property
    def total_changes(self) -> int:
        """Total lines changed (added + deleted)."""
        return self.additions + self.deletions

    @classmethod
    def from_github_file(cls, file: dict) -> "FileDiff":
        return cls(
            filename=file["filename"],
            status=FileStatus(file["status"]),
            additions=file["additions"],
            deletions=file["deletions"],
            sha=file["sha"],
            patch=file.get("patch"),
            previous_filename=file.get("previous_filename"),
        )
```

---

## 3. ReviewComment

A comment to be posted on the pull request.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `body` | str | Yes | Comment text (markdown) |
| `comment_type` | CommentType | Yes | Summary or inline |
| `file_path` | str | Conditional | File path for inline comments |
| `line` | int | Conditional | Line number for inline comments |
| `side` | LineSide | Conditional | LEFT (old) or RIGHT (new) |
| `severity` | Severity | Yes | Importance of the comment |
| `category` | Category | Yes | Type of issue found |

### CommentType Enum

```python
class CommentType(str, Enum):
    SUMMARY = "summary"      # Posted as PR comment
    INLINE = "inline"        # Posted on specific line
```

### Severity Enum

```python
class Severity(str, Enum):
    ERROR = "error"          # Must fix
    WARNING = "warning"      # Should fix
    INFO = "info"            # Suggestion
    PRAISE = "praise"        # Positive feedback
```

### Category Enum

```python
class Category(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    DOCUMENTATION = "documentation"
    CUSTOM_RULE = "custom_rule"
```

### LineSide Enum

```python
class LineSide(str, Enum):
    LEFT = "LEFT"    # Removed line (base)
    RIGHT = "RIGHT"  # Added line (head)
```

### Validation Rules

- `body` must not be empty
- If `comment_type` is `INLINE`, then `file_path`, `line`, and `side` are required
- `line` must be positive integer
- Inline comments can only be posted on lines present in the diff

### Python Model

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ReviewComment:
    body: str
    comment_type: CommentType
    severity: Severity
    category: Category
    file_path: Optional[str] = None
    line: Optional[int] = None
    side: Optional[LineSide] = None

    def __post_init__(self):
        if self.comment_type == CommentType.INLINE:
            if not self.file_path or not self.line or not self.side:
                raise ValueError(
                    "Inline comments require file_path, line, and side"
                )

    @property
    def is_inline(self) -> bool:
        return self.comment_type == CommentType.INLINE

    def to_github_review_comment(self) -> dict:
        """Convert to GitHub API format for review comments."""
        if not self.is_inline:
            raise ValueError("Only inline comments can be converted")
        return {
            "path": self.file_path,
            "line": self.line,
            "side": self.side.value,
            "body": self.body,
        }
```

---

## 4. ReviewRule

A custom rule loaded from `.claude/rules/*.md`.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_file` | str | Yes | Filename the rule came from |
| `content` | str | Yes | Raw markdown content |
| `priority` | int | Yes | Load order (alphabetical) |

### Validation Rules

- `source_file` must end with `.md`
- `content` must not be empty
- `priority` is 0-indexed based on alphabetical order

### Python Model

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ReviewRule:
    source_file: str
    content: str
    priority: int

    @classmethod
    def load_from_directory(cls, rules_dir: Path) -> list["ReviewRule"]:
        """Load all rules from a directory, sorted alphabetically."""
        if not rules_dir.exists():
            return []

        rules = []
        files = sorted(rules_dir.glob("*.md"))
        for idx, filepath in enumerate(files):
            rules.append(cls(
                source_file=filepath.name,
                content=filepath.read_text(),
                priority=idx,
            ))
        return rules
```

---

## 5. AgentConfig

Configuration for the review agent.

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `model_id` | str | No | `anthropic.claude-sonnet-4-20250514-v1:0` | Bedrock model ID |
| `timeout_seconds` | int | No | 600 | Max execution time |
| `temperature` | float | No | 0.3 | Model temperature |
| `max_files` | int | No | None | Max files to review (None = unlimited) |
| `enable_rereview` | bool | No | True | Re-review on push |
| `rules_path` | str | No | `.claude/rules` | Custom rules directory |
| `excluded_patterns` | list[str] | No | [] | Glob patterns to exclude |

### Validation Rules

- `model_id` must be one of supported models
- `timeout_seconds` must be between 60 and 900
- `temperature` must be between 0.0 and 1.0
- `excluded_patterns` must be valid glob patterns

### Python Model

```python
from dataclasses import dataclass, field
from typing import Optional

SUPPORTED_MODELS = {
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-haiku-4-20251015-v1:0",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
}

DEFAULT_EXCLUDED = [
    "*.lock",
    "*.min.js",
    "*.min.css",
    "vendor/**",
    "node_modules/**",
    "dist/**",
    "build/**",
]

@dataclass
class AgentConfig:
    model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    timeout_seconds: int = 600
    temperature: float = 0.3
    max_files: Optional[int] = None
    enable_rereview: bool = True
    rules_path: str = ".claude/rules"
    excluded_patterns: list[str] = field(default_factory=lambda: DEFAULT_EXCLUDED.copy())

    def __post_init__(self):
        if self.model_id not in SUPPORTED_MODELS:
            raise ValueError(f"Unsupported model: {self.model_id}")
        if not 60 <= self.timeout_seconds <= 900:
            raise ValueError("timeout_seconds must be between 60 and 900")
        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError("temperature must be between 0.0 and 1.0")

    @classmethod
    def from_repo_config(cls, config: dict) -> "AgentConfig":
        """Load from repository configuration (e.g., .reviewbot.yml)."""
        return cls(
            model_id=config.get("model", cls.model_id),
            timeout_seconds=config.get("timeout", cls.timeout_seconds),
            temperature=config.get("temperature", cls.temperature),
            max_files=config.get("max_files"),
            enable_rereview=config.get("enable_rereview", True),
            rules_path=config.get("rules_path", ".claude/rules"),
            excluded_patterns=config.get("excluded_patterns", DEFAULT_EXCLUDED),
        )
```

---

## 6. ReviewSession (Internal State)

Tracks the state of a review session (not persisted).

### State Diagram

```
┌─────────┐   webhook    ┌────────────┐   files loaded   ┌────────────┐
│ PENDING │─────────────>│  LOADING   │─────────────────>│ REVIEWING  │
└─────────┘              └────────────┘                  └────────────┘
                                │                              │
                                │ error                        │ complete
                                ▼                              ▼
                         ┌────────────┐                 ┌────────────┐
                         │   FAILED   │                 │  POSTING   │
                         └────────────┘                 └────────────┘
                                                               │
                                                               │ posted
                                                               ▼
                                                        ┌────────────┐
                                                        │ COMPLETED  │
                                                        └────────────┘
```

### States

| State | Description |
|-------|-------------|
| PENDING | Webhook received, not yet processed |
| LOADING | Fetching PR files and diff |
| REVIEWING | Agent analyzing code |
| POSTING | Posting comments to GitHub |
| COMPLETED | Review finished successfully |
| FAILED | Review failed with error |

### Python Model

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

class ReviewState(str, Enum):
    PENDING = "pending"
    LOADING = "loading"
    REVIEWING = "reviewing"
    POSTING = "posting"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ReviewSession:
    pull_request: PullRequest
    config: AgentConfig
    state: ReviewState = ReviewState.PENDING
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    files: list[FileDiff] = field(default_factory=list)
    comments: list[ReviewComment] = field(default_factory=list)
    error: Optional[str] = None

    def transition_to(self, new_state: ReviewState) -> None:
        """Transition to a new state with validation."""
        valid_transitions = {
            ReviewState.PENDING: {ReviewState.LOADING, ReviewState.FAILED},
            ReviewState.LOADING: {ReviewState.REVIEWING, ReviewState.FAILED},
            ReviewState.REVIEWING: {ReviewState.POSTING, ReviewState.FAILED},
            ReviewState.POSTING: {ReviewState.COMPLETED, ReviewState.FAILED},
        }

        if new_state not in valid_transitions.get(self.state, set()):
            raise ValueError(
                f"Invalid transition: {self.state} -> {new_state}"
            )

        self.state = new_state
        if new_state in {ReviewState.COMPLETED, ReviewState.FAILED}:
            self.completed_at = datetime.utcnow()
```

---

## Relationships Summary

| Entity | Relationship | Target | Cardinality |
|--------|--------------|--------|-------------|
| PullRequest | has many | FileDiff | 1:N |
| PullRequest | has many | ReviewComment | 1:N |
| FileDiff | has many | ReviewComment (inline) | 1:N |
| ReviewSession | has one | PullRequest | 1:1 |
| ReviewSession | has one | AgentConfig | 1:1 |
| ReviewSession | has many | FileDiff | 1:N |
| ReviewSession | has many | ReviewComment | 1:N |
