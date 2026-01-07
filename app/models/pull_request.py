"""Pull request model."""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class PullRequest:
    """Represents a GitHub pull request being reviewed."""

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
    body: str | None = None

    # Validation patterns
    REPO_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+$")
    SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.number <= 0:
            raise ValueError(f"PR number must be positive, got {self.number}")

        if not self.REPO_PATTERN.match(self.repository):
            raise ValueError(
                f"Invalid repository format: {self.repository}. Expected format: owner/repo"
            )

        if not self.SHA_PATTERN.match(self.head_sha):
            raise ValueError(
                f"Invalid SHA format: {self.head_sha}. Expected 40-character hex string"
            )

        if self.installation_id <= 0:
            raise ValueError(f"Installation ID must be positive, got {self.installation_id}")

    @classmethod
    def from_webhook_payload(cls, payload: dict[str, Any]) -> PullRequest:
        """Create a PullRequest from a GitHub webhook payload.

        Args:
            payload: The webhook payload containing pull_request data.

        Returns:
            PullRequest instance.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If field values are invalid.
        """
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

    @property
    def owner(self) -> str:
        """Get the repository owner."""
        return self.repository.split("/")[0]

    @property
    def repo_name(self) -> str:
        """Get the repository name without owner."""
        return self.repository.split("/")[1]

    @property
    def total_changes(self) -> int:
        """Get total lines changed (additions + deletions)."""
        return self.additions + self.deletions
