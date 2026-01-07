"""Review comment model."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommentType(str, Enum):
    """Type of review comment."""

    SUMMARY = "summary"  # Posted as PR comment
    INLINE = "inline"  # Posted on specific line


class Severity(str, Enum):
    """Severity level of a review comment."""

    ERROR = "error"  # Must fix
    WARNING = "warning"  # Should fix
    INFO = "info"  # Suggestion
    PRAISE = "praise"  # Positive feedback


class Category(str, Enum):
    """Category of issue found."""

    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    BEST_PRACTICE = "best_practice"
    DOCUMENTATION = "documentation"
    CUSTOM_RULE = "custom_rule"


class LineSide(str, Enum):
    """Side of the diff for inline comments."""

    LEFT = "LEFT"  # Removed line (base)
    RIGHT = "RIGHT"  # Added line (head)


@dataclass
class ReviewComment:
    """A comment to be posted on the pull request."""

    body: str
    comment_type: CommentType
    severity: Severity
    category: Category
    file_path: str | None = None
    line: int | None = None
    side: LineSide | str | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.body:
            raise ValueError("Comment body cannot be empty")

        if self.comment_type == CommentType.INLINE:
            if not self.file_path:
                raise ValueError("Inline comments require file_path")
            if not self.line:
                raise ValueError("Inline comments require line number")
            if not self.side:
                raise ValueError("Inline comments require side")

        # Normalize side to LineSide enum if string
        if isinstance(self.side, str) and self.side:
            self.side = LineSide(self.side)

    @property
    def is_inline(self) -> bool:
        """Check if this is an inline comment."""
        return self.comment_type == CommentType.INLINE

    def to_github_review_comment(self) -> dict[str, Any]:
        """Convert to GitHub API format for review comments.

        Returns:
            Dictionary in GitHub's review comment format.

        Raises:
            ValueError: If not an inline comment.
        """
        if not self.is_inline:
            raise ValueError("Only inline comments can be converted to GitHub format")

        side_value = self.side.value if isinstance(self.side, LineSide) else self.side

        return {
            "path": self.file_path,
            "line": self.line,
            "side": side_value,
            "body": self.body,
        }

    def format_with_metadata(self) -> str:
        """Format comment body with severity and category metadata.

        Returns:
            Formatted comment body with metadata prefix.
        """
        severity_emoji = {
            Severity.ERROR: ":x:",
            Severity.WARNING: ":warning:",
            Severity.INFO: ":information_source:",
            Severity.PRAISE: ":star:",
        }

        emoji = severity_emoji.get(self.severity, "")
        return f"{emoji} **{self.severity.value.upper()}** ({self.category.value}): {self.body}"
