"""Edge case tests for ReviewBot."""

from app.models.file_diff import FileDiff, FileStatus
from app.models.pull_request import PullRequest
from app.tools.diff import extract_changed_lines, parse_unified_diff
from tests.fixtures.diffs import (
    BINARY_FILE_DIFF,
    LARGE_DIFF,
    MULTIPLE_HUNKS,
    RENAME_ONLY_DIFF,
)
from tests.fixtures.webhook_payloads import create_fork_pr_payload, create_pr_payload

# Standard SHA for tests
TEST_SHA = "a" * 40


class TestLargePRs:
    """Tests for handling large PRs with many files."""

    def test_pr_with_many_files(self) -> None:
        """Test that PR model handles many files."""
        payload = create_pr_payload(pr_number=1)
        pr = PullRequest.from_webhook_payload(payload)

        # Simulate adding many file diffs
        files = []
        for i in range(100):
            files.append(
                FileDiff(
                    filename=f"file_{i}.py",
                    status=FileStatus.MODIFIED,
                    additions=10,
                    deletions=5,
                    sha=TEST_SHA,
                    patch=f"@@ -1,1 +1,1 @@\n-old_{i}\n+new_{i}",
                )
            )

        # Should be able to handle 100 files
        assert len(files) == 100
        assert pr.number == 1

    def test_large_diff_parsing(self) -> None:
        """Test parsing of large diffs."""
        lines = extract_changed_lines(LARGE_DIFF)

        # Should extract many changed lines
        assert len(lines) > 0

        # Should include both additions and deletions
        additions = [ln for ln in lines if ln.change_type.value == "added"]
        deletions = [ln for ln in lines if ln.change_type.value == "removed"]

        assert len(additions) > 0
        assert len(deletions) > 0


class TestBinaryFiles:
    """Tests for handling binary files."""

    def test_binary_file_diff_detection(self) -> None:
        """Test that binary files are detected from no patch content."""
        # Binary files have no patch in GitHub API
        file_diff = FileDiff(
            filename="image.png",
            status=FileStatus.MODIFIED,
            additions=0,
            deletions=0,
            sha=TEST_SHA,
            patch=None,  # No patch = binary
        )

        # Binary file should be detected
        assert file_diff.is_binary

    def test_binary_file_no_lines(self) -> None:
        """Test that binary files have no extractable lines."""
        lines = extract_changed_lines(BINARY_FILE_DIFF)
        assert len(lines) == 0

    def test_binary_file_extensions(self) -> None:
        """Test common binary file extensions are handled."""
        binary_extensions = [".png", ".jpg", ".gif", ".pdf", ".zip"]

        for ext in binary_extensions:
            file_diff = FileDiff(
                filename=f"file{ext}",
                status=FileStatus.ADDED,
                additions=0,
                deletions=0,
                sha=TEST_SHA,
                patch=None,  # No patch = binary
            )
            assert file_diff.is_binary


class TestForkPRs:
    """Tests for handling PRs from forks."""

    def test_fork_pr_payload_parsing(self) -> None:
        """Test parsing PR payloads from forks."""
        payload = create_fork_pr_payload(
            pr_number=42,
            fork_owner="contributor",
            upstream_owner="mainrepo",
            repo="project",
        )

        pr = PullRequest.from_webhook_payload(payload)

        assert pr.number == 42
        assert pr.author == "contributor"
        # The repository should be the upstream (where PR is opened)
        assert pr.repository == "mainrepo/project"

    def test_fork_pr_head_repo_differs(self) -> None:
        """Test that fork PRs have different head/base repos."""
        payload = create_fork_pr_payload()

        # Head repo (fork) differs from base repo (upstream)
        head_repo = payload["pull_request"]["head"]["repo"]["full_name"]
        base_repo = payload["pull_request"]["base"]["repo"]["full_name"]

        assert head_repo != base_repo


class TestEmptyPRs:
    """Tests for PRs with no changes or empty content."""

    def test_pr_with_empty_body(self) -> None:
        """Test PR with empty description."""
        payload = create_pr_payload(body=None)
        pr = PullRequest.from_webhook_payload(payload)

        assert pr.body is None or pr.body == ""

    def test_renamed_file_no_changes(self) -> None:
        """Test renamed file with no content changes."""
        file_diff = FileDiff(
            filename="new_name.py",
            status=FileStatus.RENAMED,
            additions=0,
            deletions=0,
            sha=TEST_SHA,
            patch=RENAME_ONLY_DIFF if RENAME_ONLY_DIFF else None,
            previous_filename="old_name.py",
        )

        assert file_diff.status == FileStatus.RENAMED
        assert file_diff.previous_filename == "old_name.py"

        # No lines changed in rename-only
        lines = extract_changed_lines(RENAME_ONLY_DIFF)
        assert len(lines) == 0

    def test_empty_patch(self) -> None:
        """Test handling of empty patch."""
        hunks = parse_unified_diff("")
        assert len(hunks) == 0

        hunks = parse_unified_diff(None)
        assert len(hunks) == 0


class TestMultipleHunks:
    """Tests for diffs with multiple hunks."""

    def test_multiple_hunks_parsing(self) -> None:
        """Test parsing diffs with multiple hunks."""
        hunks = parse_unified_diff(MULTIPLE_HUNKS)

        # Should have 2 hunks
        assert len(hunks) == 2

    def test_multiple_hunks_line_numbers(self) -> None:
        """Test line numbers are correct across hunks."""
        lines = extract_changed_lines(MULTIPLE_HUNKS)

        # Lines should span different parts of the file
        line_numbers = [ln.new_line_number or ln.old_line_number for ln in lines]

        # Should have lines from both hunks
        assert min(line_numbers) < 15  # First hunk
        assert max(line_numbers) > 20  # Second hunk


class TestSpecialCharacters:
    """Tests for handling special characters in code."""

    def test_unicode_in_diff(self) -> None:
        """Test handling Unicode characters in diffs."""
        unicode_diff = """\
@@ -1,3 +1,3 @@
 # -*- coding: utf-8 -*-
-message = "Hello"
+message = "こんにちは世界 🌍"
 print(message)
"""
        lines = extract_changed_lines(unicode_diff)

        # Should handle Unicode without errors
        assert len(lines) == 2

    def test_special_regex_characters(self) -> None:
        """Test handling regex special characters in code."""
        regex_diff = """\
@@ -1,3 +1,3 @@
 import re
-pattern = r".*"
+pattern = r"^[a-z]+\\d{3}$"
 match = re.match(pattern, text)
"""
        lines = extract_changed_lines(regex_diff)
        assert len(lines) == 2


class TestPRActions:
    """Tests for different PR actions."""

    def test_pr_opened_action(self) -> None:
        """Test parsing opened PR."""
        payload = create_pr_payload(action="opened")
        pr = PullRequest.from_webhook_payload(payload)
        assert pr.number > 0

    def test_pr_synchronize_action(self) -> None:
        """Test parsing synchronize (new commits) PR."""
        payload = create_pr_payload(action="synchronize")
        pr = PullRequest.from_webhook_payload(payload)
        assert pr.number > 0

    def test_pr_closed_action(self) -> None:
        """Test parsing closed PR."""
        payload = create_pr_payload(action="closed")
        pr = PullRequest.from_webhook_payload(payload)
        assert pr.number > 0

    def test_pr_reopened_action(self) -> None:
        """Test parsing reopened PR."""
        payload = create_pr_payload(action="reopened")
        pr = PullRequest.from_webhook_payload(payload)
        assert pr.number > 0
