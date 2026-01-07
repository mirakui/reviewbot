"""Unit tests for review agent."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.agent.prompts import build_review_prompt, build_system_prompt
from app.agent.reviewer import ReviewAgent, ReviewResult
from app.models.config import AgentConfig
from app.models.file_diff import FileDiff, FileStatus
from app.models.pull_request import PullRequest


class TestBuildSystemPrompt:
    """Tests for system prompt building."""

    def test_basic_system_prompt(self) -> None:
        """Test building a basic system prompt."""
        prompt = build_system_prompt()

        assert "code review" in prompt.lower()
        assert "pull request" in prompt.lower()

    def test_system_prompt_with_custom_rules(self) -> None:
        """Test building system prompt with custom rules."""
        rules = "Always check for SQL injection.\nRequire docstrings."

        prompt = build_system_prompt(custom_rules=rules)

        assert "SQL injection" in prompt
        assert "docstrings" in prompt

    def test_system_prompt_mentions_severity_levels(self) -> None:
        """Test that system prompt explains severity levels."""
        prompt = build_system_prompt()

        # Should mention severity concepts
        assert any(term in prompt.lower() for term in ["error", "warning", "info", "severity"])


class TestBuildReviewPrompt:
    """Tests for review prompt building."""

    def test_build_prompt_with_pr_info(self) -> None:
        """Test building review prompt with PR information."""
        prompt = build_review_prompt(
            pr_title="Add new feature",
            pr_body="This PR adds a new feature.",
            file_path="src/feature.py",
            file_diff="@@ -1,3 +1,5 @@\n-old\n+new",
        )

        assert "Add new feature" in prompt
        assert "This PR adds a new feature" in prompt
        assert "src/feature.py" in prompt
        assert "-old" in prompt
        assert "+new" in prompt

    def test_build_prompt_with_empty_body(self) -> None:
        """Test building prompt when PR body is empty."""
        prompt = build_review_prompt(
            pr_title="Quick fix",
            pr_body=None,
            file_path="fix.py",
            file_diff="+fix",
        )

        assert "Quick fix" in prompt
        assert "fix.py" in prompt

    def test_build_prompt_with_file_content(self) -> None:
        """Test building prompt with additional file content."""
        prompt = build_review_prompt(
            pr_title="Update",
            pr_body="",
            file_path="test.py",
            file_diff="+new_line",
            file_content="def old_function():\n    pass\nnew_line",
        )

        assert "old_function" in prompt


class TestReviewAgent:
    """Tests for the review agent."""

    @pytest.fixture
    def sample_pr(self, sample_pr_payload: dict[str, Any]) -> PullRequest:
        """Create a sample PR."""
        return PullRequest.from_webhook_payload(sample_pr_payload)

    @pytest.fixture
    def sample_config(self) -> AgentConfig:
        """Create a sample agent config."""
        return AgentConfig.default()

    @pytest.fixture
    def sample_files(self) -> list[FileDiff]:
        """Create sample file diffs."""
        return [
            FileDiff(
                filename="src/main.py",
                status=FileStatus.MODIFIED,
                additions=10,
                deletions=5,
                sha="abc123def456abc123def456abc123def456abc1",
                patch="@@ -1,5 +1,10 @@\n-old\n+new",
            ),
            FileDiff(
                filename="src/utils.py",
                status=FileStatus.ADDED,
                additions=20,
                deletions=0,
                sha="def456abc123def456abc123def456abc123def4",
                patch="@@ -0,0 +1,20 @@\n+new code",
            ),
        ]

    def test_agent_creation(self, sample_config: AgentConfig) -> None:
        """Test creating a review agent."""
        with patch("app.agent.reviewer.Agent"):
            agent = ReviewAgent(config=sample_config)

            assert agent.config == sample_config

    def test_agent_reviews_files(
        self,
        sample_pr: PullRequest,
        sample_config: AgentConfig,
        sample_files: list[FileDiff],
    ) -> None:
        """Test that agent reviews files and produces results."""
        with patch("app.agent.reviewer.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = MagicMock(message="Found a potential bug on line 5")
            mock_agent_class.return_value = mock_agent

            agent = ReviewAgent(config=sample_config)
            result = agent.review_file(
                pr=sample_pr,
                file_diff=sample_files[0],
            )

            assert isinstance(result, ReviewResult)

    def test_agent_handles_binary_files(
        self,
        sample_pr: PullRequest,
        sample_config: AgentConfig,
    ) -> None:
        """Test that agent skips binary files."""
        binary_file = FileDiff(
            filename="image.png",
            status=FileStatus.MODIFIED,
            additions=0,
            deletions=0,
            sha="abc123def456abc123def456abc123def456abc1",
            patch=None,  # Binary files have no patch
        )

        with patch("app.agent.reviewer.Agent"):
            agent = ReviewAgent(config=sample_config)
            result = agent.review_file(
                pr=sample_pr,
                file_diff=binary_file,
            )

            # Should return empty result for binary files
            assert result.comments == []
            assert result.skipped is True

    def test_agent_respects_excluded_patterns(
        self,
        sample_pr: PullRequest,
        sample_config: AgentConfig,
    ) -> None:
        """Test that agent skips excluded files."""
        excluded_file = FileDiff(
            filename="package-lock.json",
            status=FileStatus.MODIFIED,
            additions=100,
            deletions=50,
            sha="abc123def456abc123def456abc123def456abc1",
            patch="+changes",
        )

        # Add lock files to exclusion
        sample_config.excluded_patterns.append("*.lock")
        sample_config.excluded_patterns.append("*-lock.json")

        with patch("app.agent.reviewer.Agent"):
            agent = ReviewAgent(config=sample_config)
            result = agent.review_file(
                pr=sample_pr,
                file_diff=excluded_file,
            )

            assert result.skipped is True

    def test_agent_creates_summary(
        self,
        sample_pr: PullRequest,
        sample_config: AgentConfig,
        sample_files: list[FileDiff],
    ) -> None:
        """Test that agent creates a summary comment."""
        with patch("app.agent.reviewer.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = MagicMock(message="Overall, good code quality")
            mock_agent_class.return_value = mock_agent

            agent = ReviewAgent(config=sample_config)
            summary = agent.create_summary(
                pr=sample_pr,
                file_results=[],
            )

            assert summary is not None
            assert isinstance(summary, str)


class TestReviewResult:
    """Tests for ReviewResult data class."""

    def test_review_result_with_comments(self) -> None:
        """Test creating a review result with comments."""
        from app.models.comment import Category, CommentType, ReviewComment, Severity

        comments = [
            ReviewComment(
                body="Found issue",
                comment_type=CommentType.INLINE,
                severity=Severity.ERROR,
                category=Category.BUG,
                file_path="test.py",
                line=10,
                side="RIGHT",
            )
        ]

        result = ReviewResult(
            file_path="test.py",
            comments=comments,
            skipped=False,
        )

        assert result.file_path == "test.py"
        assert len(result.comments) == 1
        assert result.skipped is False

    def test_review_result_skipped(self) -> None:
        """Test creating a skipped review result."""
        result = ReviewResult(
            file_path="binary.png",
            comments=[],
            skipped=True,
            skip_reason="Binary file",
        )

        assert result.skipped is True
        assert result.skip_reason == "Binary file"
