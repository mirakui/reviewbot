"""File diff model."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FileStatus(str, Enum):
    """Status of a file in a pull request."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    RENAMED = "renamed"
    COPIED = "copied"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


@dataclass
class FileDiff:
    """Represents a single file's changes in a pull request."""

    filename: str
    status: FileStatus
    additions: int
    deletions: int
    sha: str
    patch: str | None = None
    previous_filename: str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.filename:
            raise ValueError("filename cannot be empty")

        if self.additions < 0:
            raise ValueError(f"additions must be non-negative, got {self.additions}")

        if self.deletions < 0:
            raise ValueError(f"deletions must be non-negative, got {self.deletions}")

    @property
    def is_binary(self) -> bool:
        """Check if file appears to be binary (no patch available).

        Binary files don't have patch content in GitHub's API.
        Removed files also have no patch, but aren't binary.
        """
        return self.patch is None and self.status != FileStatus.REMOVED

    @property
    def total_changes(self) -> int:
        """Total lines changed (added + deleted)."""
        return self.additions + self.deletions

    @property
    def file_extension(self) -> str:
        """Get the file extension."""
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[-1].lower()
        return ""

    @classmethod
    def from_github_file(cls, file: dict[str, Any]) -> FileDiff:
        """Create a FileDiff from a GitHub API file response.

        Args:
            file: File data from GitHub's pull request files API.

        Returns:
            FileDiff instance.
        """
        return cls(
            filename=file["filename"],
            status=FileStatus(file["status"]),
            additions=file["additions"],
            deletions=file["deletions"],
            sha=file["sha"],
            patch=file.get("patch"),
            previous_filename=file.get("previous_filename"),
        )
