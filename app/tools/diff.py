"""Diff parsing utilities."""

import re
from dataclasses import dataclass
from enum import Enum


class LineChangeType(str, Enum):
    """Type of line change."""

    ADDED = "added"
    REMOVED = "removed"
    CONTEXT = "context"


@dataclass
class ChangedLine:
    """Represents a changed line in a diff."""

    change_type: LineChangeType
    content: str
    old_line_number: int | None
    new_line_number: int | None


@dataclass
class DiffHunk:
    """Represents a hunk in a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    lines: list[str]

    @property
    def is_pure_addition(self) -> bool:
        """Check if this hunk is a pure addition (new file or insertion)."""
        return self.old_count == 0 and self.new_count > 0

    @property
    def is_pure_deletion(self) -> bool:
        """Check if this hunk is a pure deletion."""
        return self.old_count > 0 and self.new_count == 0


# Pattern to match hunk headers: @@ -old_start,old_count +new_start,new_count @@
HUNK_HEADER_PATTERN = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_unified_diff(patch: str | None) -> list[DiffHunk]:
    """Parse a unified diff patch into hunks.

    Args:
        patch: The unified diff patch content, or None for binary files.

    Returns:
        List of DiffHunk objects.
    """
    if not patch:
        return []

    hunks: list[DiffHunk] = []
    current_hunk: DiffHunk | None = None
    current_lines: list[str] = []

    for line in patch.split("\n"):
        match = HUNK_HEADER_PATTERN.match(line)

        if match:
            # Save previous hunk if exists
            if current_hunk is not None:
                current_hunk.lines = current_lines
                hunks.append(current_hunk)

            # Parse hunk header
            old_start = int(match.group(1))
            old_count = int(match.group(2)) if match.group(2) else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) else 1

            current_hunk = DiffHunk(
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                header=line,
                lines=[],
            )
            current_lines = []

        elif current_hunk is not None:
            current_lines.append(line)

    # Save final hunk
    if current_hunk is not None:
        current_hunk.lines = current_lines
        hunks.append(current_hunk)

    return hunks


def extract_changed_lines(patch: str | None) -> list[ChangedLine]:
    """Extract changed lines from a unified diff patch.

    Args:
        patch: The unified diff patch content.

    Returns:
        List of ChangedLine objects for additions and removals.
    """
    if not patch:
        return []

    hunks = parse_unified_diff(patch)
    changed_lines: list[ChangedLine] = []

    for hunk in hunks:
        old_line = hunk.old_start
        new_line = hunk.new_start

        for line in hunk.lines:
            if not line:
                continue

            prefix = line[0] if line else " "
            content = line[1:] if len(line) > 1 else ""

            if prefix == "+":
                changed_lines.append(
                    ChangedLine(
                        change_type=LineChangeType.ADDED,
                        content=content,
                        old_line_number=None,
                        new_line_number=new_line,
                    )
                )
                new_line += 1

            elif prefix == "-":
                changed_lines.append(
                    ChangedLine(
                        change_type=LineChangeType.REMOVED,
                        content=content,
                        old_line_number=old_line,
                        new_line_number=None,
                    )
                )
                old_line += 1

            elif prefix in {" ", "\\"}:
                # Context line or "\ No newline at end of file"
                if prefix == " ":
                    old_line += 1
                    new_line += 1

    return changed_lines


def get_line_at_position(patch: str | None, position: int) -> int | None:
    """Get the new file line number at a given diff position.

    GitHub's API uses 'position' (1-indexed line in the diff) for comments.
    This converts that to actual line numbers.

    Args:
        patch: The unified diff patch content.
        position: The 1-indexed position in the diff.

    Returns:
        The new file line number, or None if position is invalid.
    """
    if not patch:
        return None

    lines = patch.split("\n")

    if position < 1 or position > len(lines):
        return None

    # Find the hunk containing this position
    current_position = 0
    new_line = 0

    for line in lines:
        current_position += 1

        match = HUNK_HEADER_PATTERN.match(line)
        if match:
            new_line = int(match.group(3))
            if match.group(4):
                pass  # new_count not needed here
            continue

        if current_position == position:
            return new_line if line.startswith("+") or line.startswith(" ") else None

        # Update line counter
        if line.startswith("+") or line.startswith(" ") or not line.startswith("-"):
            new_line += 1

    return None
