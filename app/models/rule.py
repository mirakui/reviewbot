"""Custom review rule model."""

from dataclasses import dataclass


@dataclass
class ReviewRule:
    """A custom rule loaded from .claude/rules/*.md."""

    source_file: str
    """Filename the rule came from."""

    content: str
    """Raw markdown content."""

    priority: int
    """Load order (0-indexed, based on alphabetical order)."""

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not self.source_file.endswith(".md"):
            raise ValueError(f"Rule source file must end with .md, got: {self.source_file}")

        if not self.content or not self.content.strip():
            raise ValueError("Rule content cannot be empty")

        if self.priority < 0:
            raise ValueError(f"Rule priority must be non-negative, got: {self.priority}")

    @property
    def title(self) -> str:
        """Extract title from the first line if it's a markdown heading.

        Returns:
            Title extracted from content, or filename without extension.
        """
        lines = self.content.strip().split("\n")
        first_line = lines[0].strip() if lines else ""

        if first_line.startswith("#"):
            # Remove # prefix and whitespace
            return first_line.lstrip("#").strip()

        # Fall back to filename without extension
        return self.source_file.rsplit(".", 1)[0]
