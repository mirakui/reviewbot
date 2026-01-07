"""Unit tests for data models."""

from typing import Any

import pytest

from app.models.comment import (
    Category,
    CommentType,
    LineSide,
    ReviewComment,
    Severity,
)
from app.models.config import AgentConfig
from app.models.file_diff import FileDiff, FileStatus
from app.models.pull_request import PullRequest
from app.models.session import ReviewSession, ReviewState


class TestFileDiff:
    """Tests for FileDiff model."""

    def test_create_modified_file(self) -> None:
        """Test creating a modified file diff."""
        diff = FileDiff(
            filename="src/main.py",
            status=FileStatus.MODIFIED,
            additions=10,
            deletions=5,
            sha="abc123def456abc123def456abc123def456abc1",
            patch="@@ -1,5 +1,10 @@\n-old\n+new",
        )

        assert diff.filename == "src/main.py"
        assert diff.status == FileStatus.MODIFIED
        assert diff.additions == 10
        assert diff.deletions == 5
        assert diff.total_changes == 15
        assert diff.is_binary is False

    def test_create_added_file(self) -> None:
        """Test creating an added file diff."""
        diff = FileDiff(
            filename="new_file.py",
            status=FileStatus.ADDED,
            additions=50,
            deletions=0,
            sha="abc123def456abc123def456abc123def456abc1",
            patch="@@ -0,0 +1,50 @@\n+...",
        )

        assert diff.status == FileStatus.ADDED
        assert diff.is_binary is False

    def test_create_removed_file(self) -> None:
        """Test creating a removed file diff."""
        diff = FileDiff(
            filename="deleted.py",
            status=FileStatus.REMOVED,
            additions=0,
            deletions=30,
            sha="abc123def456abc123def456abc123def456abc1",
            patch=None,
        )

        assert diff.status == FileStatus.REMOVED
        assert diff.is_binary is False  # Removed files have no patch, but aren't binary

    def test_binary_file_detection(self) -> None:
        """Test that binary files are detected (no patch, not removed)."""
        diff = FileDiff(
            filename="image.png",
            status=FileStatus.MODIFIED,
            additions=0,
            deletions=0,
            sha="abc123def456abc123def456abc123def456abc1",
            patch=None,
        )

        assert diff.is_binary is True

    def test_renamed_file(self) -> None:
        """Test creating a renamed file diff."""
        diff = FileDiff(
            filename="new_name.py",
            status=FileStatus.RENAMED,
            additions=0,
            deletions=0,
            sha="abc123def456abc123def456abc123def456abc1",
            patch=None,
            previous_filename="old_name.py",
        )

        assert diff.status == FileStatus.RENAMED
        assert diff.previous_filename == "old_name.py"

    def test_from_github_file(self, sample_file_diff: dict[str, Any]) -> None:
        """Test creating FileDiff from GitHub API response."""
        diff = FileDiff.from_github_file(sample_file_diff)

        assert diff.filename == "src/main.py"
        assert diff.status == FileStatus.MODIFIED
        assert diff.additions == 10
        assert diff.deletions == 5


class TestReviewComment:
    """Tests for ReviewComment model."""

    def test_create_summary_comment(self) -> None:
        """Test creating a summary comment."""
        comment = ReviewComment(
            body="Overall the code looks good.",
            comment_type=CommentType.SUMMARY,
            severity=Severity.INFO,
            category=Category.BEST_PRACTICE,
        )

        assert comment.body == "Overall the code looks good."
        assert comment.comment_type == CommentType.SUMMARY
        assert comment.is_inline is False

    def test_create_inline_comment(self) -> None:
        """Test creating an inline comment."""
        comment = ReviewComment(
            body="This variable should be renamed.",
            comment_type=CommentType.INLINE,
            severity=Severity.WARNING,
            category=Category.STYLE,
            file_path="src/main.py",
            line=42,
            side=LineSide.RIGHT,
        )

        assert comment.is_inline is True
        assert comment.file_path == "src/main.py"
        assert comment.line == 42
        assert comment.side == LineSide.RIGHT

    def test_inline_comment_requires_file_path(self) -> None:
        """Test that inline comments require file_path."""
        with pytest.raises(ValueError, match="file_path"):
            ReviewComment(
                body="Comment",
                comment_type=CommentType.INLINE,
                severity=Severity.INFO,
                category=Category.STYLE,
                line=10,
                side=LineSide.RIGHT,
            )

    def test_inline_comment_requires_line(self) -> None:
        """Test that inline comments require line number."""
        with pytest.raises(ValueError, match="line"):
            ReviewComment(
                body="Comment",
                comment_type=CommentType.INLINE,
                severity=Severity.INFO,
                category=Category.STYLE,
                file_path="test.py",
                side=LineSide.RIGHT,
            )

    def test_inline_comment_requires_side(self) -> None:
        """Test that inline comments require side."""
        with pytest.raises(ValueError, match="side"):
            ReviewComment(
                body="Comment",
                comment_type=CommentType.INLINE,
                severity=Severity.INFO,
                category=Category.STYLE,
                file_path="test.py",
                line=10,
            )

    def test_to_github_review_comment(self) -> None:
        """Test converting inline comment to GitHub API format."""
        comment = ReviewComment(
            body="Fix this issue.",
            comment_type=CommentType.INLINE,
            severity=Severity.ERROR,
            category=Category.BUG,
            file_path="src/bug.py",
            line=100,
            side=LineSide.RIGHT,
        )

        github_comment = comment.to_github_review_comment()

        assert github_comment["path"] == "src/bug.py"
        assert github_comment["line"] == 100
        assert github_comment["side"] == "RIGHT"
        assert github_comment["body"] == "Fix this issue."

    def test_to_github_review_comment_fails_for_summary(self) -> None:
        """Test that summary comments cannot be converted."""
        comment = ReviewComment(
            body="Summary",
            comment_type=CommentType.SUMMARY,
            severity=Severity.INFO,
            category=Category.BEST_PRACTICE,
        )

        with pytest.raises(ValueError, match="inline"):
            comment.to_github_review_comment()

    def test_severity_levels(self) -> None:
        """Test all severity levels."""
        for severity in Severity:
            comment = ReviewComment(
                body="Test",
                comment_type=CommentType.SUMMARY,
                severity=severity,
                category=Category.STYLE,
            )
            assert comment.severity == severity

    def test_category_values(self) -> None:
        """Test all category values."""
        for category in Category:
            comment = ReviewComment(
                body="Test",
                comment_type=CommentType.SUMMARY,
                severity=Severity.INFO,
                category=category,
            )
            assert comment.category == category


class TestReviewSession:
    """Tests for ReviewSession model."""

    @pytest.fixture
    def sample_pr(self, sample_pr_payload: dict[str, Any]) -> PullRequest:
        """Create a sample PR for testing."""
        return PullRequest.from_webhook_payload(sample_pr_payload)

    @pytest.fixture
    def sample_config(self) -> AgentConfig:
        """Create a sample config for testing."""
        return AgentConfig.default()

    def test_create_session(self, sample_pr: PullRequest, sample_config: AgentConfig) -> None:
        """Test creating a review session."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)

        assert session.state == ReviewState.PENDING
        assert session.pull_request == sample_pr
        assert session.config == sample_config
        assert session.files == []
        assert session.comments == []
        assert session.error is None

    def test_transition_to_loading(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test transitioning from PENDING to LOADING."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)

        session.transition_to(ReviewState.LOADING)

        assert session.state == ReviewState.LOADING

    def test_transition_to_reviewing(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test transitioning from LOADING to REVIEWING."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)
        session.state = ReviewState.LOADING

        session.transition_to(ReviewState.REVIEWING)

        assert session.state == ReviewState.REVIEWING

    def test_transition_to_posting(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test transitioning from REVIEWING to POSTING."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)
        session.state = ReviewState.REVIEWING

        session.transition_to(ReviewState.POSTING)

        assert session.state == ReviewState.POSTING

    def test_transition_to_completed(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test transitioning from POSTING to COMPLETED."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)
        session.state = ReviewState.POSTING

        session.transition_to(ReviewState.COMPLETED)

        assert session.state == ReviewState.COMPLETED
        assert session.completed_at is not None

    def test_transition_to_failed(self, sample_pr: PullRequest, sample_config: AgentConfig) -> None:
        """Test transitioning to FAILED from any state."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)

        session.transition_to(ReviewState.FAILED)

        assert session.state == ReviewState.FAILED
        assert session.completed_at is not None

    def test_invalid_transition_raises_error(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test that invalid state transitions raise errors."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)

        with pytest.raises(ValueError, match="Invalid transition"):
            session.transition_to(ReviewState.COMPLETED)

    def test_completed_state_is_terminal(
        self, sample_pr: PullRequest, sample_config: AgentConfig
    ) -> None:
        """Test that COMPLETED is a terminal state."""
        session = ReviewSession(pull_request=sample_pr, config=sample_config)
        session.state = ReviewState.POSTING
        session.transition_to(ReviewState.COMPLETED)

        with pytest.raises(ValueError, match="Invalid transition"):
            session.transition_to(ReviewState.FAILED)
