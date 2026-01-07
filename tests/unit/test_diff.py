"""Unit tests for diff parsing utilities."""

from app.tools.diff import (
    ChangedLine,
    DiffHunk,
    LineChangeType,
    extract_changed_lines,
    parse_unified_diff,
)


class TestParseUnifiedDiff:
    """Tests for unified diff parsing."""

    def test_parse_simple_modification(self) -> None:
        """Test parsing a simple file modification."""
        patch = """\
@@ -1,3 +1,3 @@
 line1
-old line
+new line
 line3"""

        hunks = parse_unified_diff(patch)

        assert len(hunks) == 1
        assert hunks[0].old_start == 1
        assert hunks[0].old_count == 3
        assert hunks[0].new_start == 1
        assert hunks[0].new_count == 3

    def test_parse_addition(self) -> None:
        """Test parsing a pure addition."""
        patch = """\
@@ -0,0 +1,3 @@
+new line 1
+new line 2
+new line 3"""

        hunks = parse_unified_diff(patch)

        assert len(hunks) == 1
        assert hunks[0].old_start == 0
        assert hunks[0].old_count == 0
        assert hunks[0].new_start == 1
        assert hunks[0].new_count == 3

    def test_parse_deletion(self) -> None:
        """Test parsing a pure deletion."""
        patch = """\
@@ -1,3 +0,0 @@
-deleted line 1
-deleted line 2
-deleted line 3"""

        hunks = parse_unified_diff(patch)

        assert len(hunks) == 1
        assert hunks[0].old_start == 1
        assert hunks[0].old_count == 3
        assert hunks[0].new_start == 0
        assert hunks[0].new_count == 0

    def test_parse_multiple_hunks(self) -> None:
        """Test parsing multiple hunks in one patch."""
        patch = """\
@@ -1,3 +1,4 @@
 line1
+inserted
 line2
 line3
@@ -10,3 +11,3 @@
 line10
-old
+new
 line12"""

        hunks = parse_unified_diff(patch)

        assert len(hunks) == 2
        assert hunks[0].new_start == 1
        assert hunks[1].new_start == 11

    def test_parse_empty_patch(self) -> None:
        """Test parsing an empty patch."""
        hunks = parse_unified_diff("")

        assert len(hunks) == 0

    def test_parse_none_patch(self) -> None:
        """Test parsing None patch (binary file)."""
        hunks = parse_unified_diff(None)

        assert len(hunks) == 0


class TestExtractChangedLines:
    """Tests for extracting changed line information."""

    def test_extract_added_lines(self) -> None:
        """Test extracting added lines from a patch."""
        patch = """\
@@ -1,2 +1,4 @@
 existing
+new line 1
+new line 2
 also existing"""

        lines = extract_changed_lines(patch)
        added = [line for line in lines if line.change_type == LineChangeType.ADDED]

        assert len(added) == 2
        assert added[0].new_line_number == 2
        assert added[0].content == "new line 1"
        assert added[1].new_line_number == 3

    def test_extract_removed_lines(self) -> None:
        """Test extracting removed lines from a patch."""
        patch = """\
@@ -1,4 +1,2 @@
 existing
-removed 1
-removed 2
 also existing"""

        lines = extract_changed_lines(patch)
        removed = [line for line in lines if line.change_type == LineChangeType.REMOVED]

        assert len(removed) == 2
        assert removed[0].old_line_number == 2
        assert removed[0].content == "removed 1"

    def test_extract_mixed_changes(self) -> None:
        """Test extracting mixed additions and removals."""
        patch = """\
@@ -1,3 +1,3 @@
 context
-old value
+new value
 more context"""

        lines = extract_changed_lines(patch)

        assert len(lines) == 2
        removed = [line for line in lines if line.change_type == LineChangeType.REMOVED]
        added = [line for line in lines if line.change_type == LineChangeType.ADDED]

        assert len(removed) == 1
        assert len(added) == 1
        assert removed[0].content == "old value"
        assert added[0].content == "new value"

    def test_line_numbers_are_correct(self) -> None:
        """Test that line numbers are correctly tracked."""
        patch = """\
@@ -10,5 +10,6 @@
 line 10
 line 11
+inserted at 12
 line 12
 line 13
 line 14"""

        lines = extract_changed_lines(patch)
        added = [line for line in lines if line.change_type == LineChangeType.ADDED]

        assert len(added) == 1
        assert added[0].new_line_number == 12

    def test_empty_patch_returns_empty_list(self) -> None:
        """Test that empty patch returns empty list."""
        lines = extract_changed_lines("")
        assert lines == []

    def test_context_only_returns_empty_list(self) -> None:
        """Test that patch with only context returns empty list."""
        patch = """\
@@ -1,3 +1,3 @@
 line1
 line2
 line3"""

        lines = extract_changed_lines(patch)
        assert lines == []


class TestDiffHunk:
    """Tests for DiffHunk data class."""

    def test_hunk_creation(self) -> None:
        """Test creating a diff hunk."""
        hunk = DiffHunk(
            old_start=1,
            old_count=3,
            new_start=1,
            new_count=4,
            header="@@ -1,3 +1,4 @@",
            lines=["context", "+added", "-removed"],
        )

        assert hunk.old_start == 1
        assert hunk.old_count == 3
        assert hunk.new_start == 1
        assert hunk.new_count == 4

    def test_hunk_is_addition(self) -> None:
        """Test detecting a pure addition hunk."""
        hunk = DiffHunk(
            old_start=0,
            old_count=0,
            new_start=1,
            new_count=5,
            header="@@ -0,0 +1,5 @@",
            lines=["+line"] * 5,
        )

        assert hunk.is_pure_addition is True

    def test_hunk_is_deletion(self) -> None:
        """Test detecting a pure deletion hunk."""
        hunk = DiffHunk(
            old_start=1,
            old_count=5,
            new_start=0,
            new_count=0,
            header="@@ -1,5 +0,0 @@",
            lines=["-line"] * 5,
        )

        assert hunk.is_pure_deletion is True


class TestChangedLine:
    """Tests for ChangedLine data class."""

    def test_added_line(self) -> None:
        """Test creating an added line."""
        line = ChangedLine(
            change_type=LineChangeType.ADDED,
            content="new code",
            old_line_number=None,
            new_line_number=42,
        )

        assert line.change_type == LineChangeType.ADDED
        assert line.new_line_number == 42
        assert line.old_line_number is None

    def test_removed_line(self) -> None:
        """Test creating a removed line."""
        line = ChangedLine(
            change_type=LineChangeType.REMOVED,
            content="deleted code",
            old_line_number=10,
            new_line_number=None,
        )

        assert line.change_type == LineChangeType.REMOVED
        assert line.old_line_number == 10
        assert line.new_line_number is None
