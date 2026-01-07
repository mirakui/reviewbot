"""Unit tests for AgentCore entrypoint."""

from typing import Any
from unittest.mock import MagicMock, patch


class TestAgentCoreApp:
    """Tests for the AgentCore application setup."""

    def test_app_import(self) -> None:
        """Test that the agentcore module can be imported."""
        from app.agentcore import app  # noqa: F401, PLC0415

    def test_app_is_bedrock_agentcore_app(self) -> None:
        """Test that app is a BedrockAgentCoreApp instance."""
        from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: PLC0415

        from app.agentcore import app  # noqa: PLC0415

        assert isinstance(app, BedrockAgentCoreApp)


class TestInvokeEntrypoint:
    """Tests for the invoke entrypoint."""

    def test_invoke_function_exists(self) -> None:
        """Test that the invoke function exists."""
        from app.agentcore import invoke  # noqa: F401, PLC0415

    def test_invoke_returns_dict(self) -> None:
        """Test that invoke returns a dictionary."""
        with (
            patch("app.agentcore.ReviewAgent") as mock_agent_class,
            patch("app.agentcore.create_github_client") as mock_create_client,
            patch("app.agentcore.get_pr_metadata") as mock_get_metadata,
            patch("app.agentcore.list_pr_files") as mock_list_files,
        ):
            # Setup mocks
            mock_agent = MagicMock()
            mock_agent.review_file.return_value = MagicMock(
                file_path="test.py",
                comments=[],
                skipped=False,
            )
            mock_agent.create_summary.return_value = "Review completed"
            mock_agent_class.return_value = mock_agent

            mock_create_client.return_value = MagicMock()
            mock_get_metadata.return_value = {
                "title": "Test PR",
                "body": "Test body",
                "author": "testuser",
                "base_branch": "main",
                "head_branch": "feature",
            }
            mock_list_files.return_value = []

            from app.agentcore import invoke  # noqa: PLC0415

            payload = {
                "prompt": "Review this PR",
                "repository": "owner/repo",
                "pr_number": 42,
                "installation_id": 12345,
            }

            result = invoke(payload)

            assert isinstance(result, dict)

    def test_invoke_with_prompt_only(self) -> None:
        """Test invoke with just a prompt (no PR context)."""
        with patch("app.agentcore.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = MagicMock(message="Hello! How can I help?")
            mock_agent_class.return_value = mock_agent

            from app.agentcore import invoke  # noqa: PLC0415

            payload = {"prompt": "Hello"}
            result = invoke(payload)

            assert "result" in result
            assert isinstance(result["result"], str)

    def test_invoke_with_pr_review_request(self) -> None:
        """Test invoke with PR review request."""
        with (
            patch("app.agentcore.ReviewAgent") as mock_agent_class,
            patch("app.agentcore.create_github_client") as mock_create_client,
            patch("app.agentcore.get_pr_metadata") as mock_get_metadata,
            patch("app.agentcore.list_pr_files") as mock_list_files,
        ):
            mock_agent = MagicMock()
            mock_agent.review_file.return_value = MagicMock(
                file_path="src/main.py",
                comments=[],
                skipped=False,
                summary="Good code",
            )
            mock_agent.create_summary.return_value = "Overall: Good PR"
            mock_agent_class.return_value = mock_agent

            mock_create_client.return_value = MagicMock()
            mock_get_metadata.return_value = {
                "title": "Test PR",
                "body": "Test body",
                "author": "testuser",
                "base_branch": "main",
                "head_branch": "feature",
                "files_changed": 1,
                "additions": 10,
                "deletions": 5,
            }
            mock_list_files.return_value = [
                {
                    "filename": "src/main.py",
                    "status": "modified",
                    "additions": 10,
                    "deletions": 5,
                    "sha": "abc123def456abc123def456abc123def456abc1",
                    "patch": "+new code",
                }
            ]

            from app.agentcore import invoke  # noqa: PLC0415

            payload = {
                "prompt": "Review this PR",
                "repository": "owner/repo",
                "pr_number": 42,
                "installation_id": 12345,
            }

            result = invoke(payload)

            assert "result" in result
            # Should contain review summary
            assert "summary" in result or "result" in result

    def test_invoke_handles_missing_prompt(self) -> None:
        """Test invoke with missing prompt uses default."""
        with patch("app.agentcore.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.return_value = MagicMock(message="Default response")
            mock_agent_class.return_value = mock_agent

            from app.agentcore import invoke  # noqa: PLC0415

            payload: dict[str, Any] = {}
            result = invoke(payload)

            assert "result" in result

    def test_invoke_handles_error(self) -> None:
        """Test invoke handles errors gracefully."""
        with patch("app.agentcore.Agent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.side_effect = Exception("Agent error")
            mock_agent_class.return_value = mock_agent

            from app.agentcore import invoke  # noqa: PLC0415

            payload = {"prompt": "Hello"}
            result = invoke(payload)

            assert "error" in result


class TestPingEntrypoint:
    """Tests for the ping/health check entrypoint."""

    def test_ping_function_exists(self) -> None:
        """Test that the ping function exists."""
        from app.agentcore import ping  # noqa: F401, PLC0415

    def test_ping_returns_healthy_status(self) -> None:
        """Test that ping returns healthy status."""
        from app.agentcore import ping  # noqa: PLC0415

        result = ping()

        assert result["status"] == "healthy"

    def test_ping_includes_version(self) -> None:
        """Test that ping includes version info."""
        from app.agentcore import ping  # noqa: PLC0415

        result = ping()

        assert "version" in result


class TestReviewPR:
    """Tests for the review_pr helper function."""

    def test_review_pr_function_exists(self) -> None:
        """Test that the review_pr function exists."""
        from app.agentcore import review_pr  # noqa: F401, PLC0415

    def test_review_pr_returns_review_result(self) -> None:
        """Test that review_pr returns a proper result."""
        with (
            patch("app.agentcore.ReviewAgent") as mock_agent_class,
            patch("app.agentcore.create_github_client") as mock_create_client,
            patch("app.agentcore.get_pr_metadata") as mock_get_metadata,
            patch("app.agentcore.list_pr_files") as mock_list_files,
            patch("app.agentcore.AgentConfig") as mock_config_class,
        ):
            mock_config = MagicMock()
            mock_config_class.default.return_value = mock_config

            mock_agent = MagicMock()
            mock_agent.review_file.return_value = MagicMock(
                file_path="test.py",
                comments=[],
                skipped=False,
            )
            mock_agent.create_summary.return_value = "Review complete"
            mock_agent_class.return_value = mock_agent

            mock_create_client.return_value = MagicMock()
            mock_get_metadata.return_value = {
                "title": "Test",
                "body": "",
                "author": "testuser",
                "base_branch": "main",
                "head_branch": "feature",
            }
            mock_list_files.return_value = []

            from app.agentcore import review_pr  # noqa: PLC0415

            result = review_pr(
                repository="owner/repo",
                pr_number=42,
                installation_id=12345,
            )

            assert "summary" in result
            assert "files_reviewed" in result
