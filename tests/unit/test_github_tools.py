"""Unit tests for GitHub API tools."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from github import GithubException

from app.tools.github import (
    GitHubToolError,
    create_github_client,
    get_file_content,
    get_file_diff,
    get_pr_metadata,
    list_pr_files,
)


class TestCreateGitHubClient:
    """Tests for GitHub client creation."""

    def test_create_client_with_valid_credentials(self, set_mock_env: None) -> None:  # noqa: ARG002
        """Test creating client with valid credentials."""
        with patch("app.tools.github.GithubIntegration") as mock_integration:
            mock_github = MagicMock()
            mock_integration.return_value.get_github_for_installation.return_value = mock_github

            client = create_github_client(installation_id=12345)

            assert client is not None
            mock_integration.return_value.get_github_for_installation.assert_called_once_with(12345)

    def test_create_client_missing_app_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing APP_ID raises error."""
        monkeypatch.setenv("GITHUB_PRIVATE_KEY", "test-key")
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)

        with pytest.raises(GitHubToolError, match="GITHUB_APP_ID"):
            create_github_client(installation_id=12345)

    def test_create_client_missing_private_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing private key raises error."""
        monkeypatch.setenv("GITHUB_APP_ID", "123456")
        monkeypatch.delenv("GITHUB_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("GITHUB_PRIVATE_KEY_PATH", raising=False)

        with pytest.raises(GitHubToolError, match="private key"):
            create_github_client(installation_id=12345)


class TestGetPrMetadata:
    """Tests for get_pr_metadata tool."""

    def test_get_metadata_success(self) -> None:
        """Test getting PR metadata successfully."""
        mock_client = MagicMock()
        mock_pr = MagicMock()
        mock_pr.title = "Test PR"
        mock_pr.body = "PR description"
        mock_pr.user.login = "author"
        mock_pr.base.ref = "main"
        mock_pr.head.ref = "feature"
        mock_pr.changed_files = 5
        mock_pr.additions = 100
        mock_pr.deletions = 50

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        result = get_pr_metadata(
            client=mock_client,
            pr_number=42,
            repository="owner/repo",
        )

        assert result["title"] == "Test PR"
        assert result["body"] == "PR description"
        assert result["author"] == "author"
        assert result["files_changed"] == 5

    def test_get_metadata_pr_not_found(self) -> None:
        """Test handling PR not found error."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pull.side_effect = GithubException(404, {"message": "Not Found"}, {})
        mock_client.get_repo.return_value = mock_repo

        with pytest.raises(GitHubToolError, match="not found"):
            get_pr_metadata(
                client=mock_client,
                pr_number=999,
                repository="owner/repo",
            )


class TestListPrFiles:
    """Tests for list_pr_files tool."""

    def test_list_files_success(self) -> None:
        """Test listing PR files successfully."""
        mock_client = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.filename = "file1.py"
        mock_file1.status = "modified"
        mock_file1.additions = 10
        mock_file1.deletions = 5

        mock_file2 = MagicMock()
        mock_file2.filename = "file2.py"
        mock_file2.status = "added"
        mock_file2.additions = 20
        mock_file2.deletions = 0

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file1, mock_file2]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        result = list_pr_files(
            client=mock_client,
            pr_number=42,
            repository="owner/repo",
        )

        assert len(result) == 2
        assert result[0]["filename"] == "file1.py"
        assert result[1]["filename"] == "file2.py"

    def test_list_files_empty_pr(self) -> None:
        """Test listing files for PR with no changes."""
        mock_client = MagicMock()
        mock_pr = MagicMock()
        mock_pr.get_files.return_value = []

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        result = list_pr_files(
            client=mock_client,
            pr_number=42,
            repository="owner/repo",
        )

        assert result == []


class TestGetFileDiff:
    """Tests for get_file_diff tool."""

    def test_get_diff_success(self) -> None:
        """Test getting file diff successfully."""
        mock_client = MagicMock()
        mock_file = MagicMock()
        mock_file.filename = "test.py"
        mock_file.status = "modified"
        mock_file.patch = "@@ -1,3 +1,4 @@\n context\n-old\n+new"
        mock_file.additions = 1
        mock_file.deletions = 1

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        result = get_file_diff(
            client=mock_client,
            pr_number=42,
            repository="owner/repo",
            file_path="test.py",
        )

        assert result["filename"] == "test.py"
        assert result["status"] == "modified"
        assert "@@ -1,3 +1,4 @@" in result["patch"]

    def test_get_diff_file_not_in_pr(self) -> None:
        """Test getting diff for file not in PR."""
        mock_client = MagicMock()
        mock_file = MagicMock()
        mock_file.filename = "other.py"

        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [mock_file]

        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        with pytest.raises(GitHubToolError, match="not found"):
            get_file_diff(
                client=mock_client,
                pr_number=42,
                repository="owner/repo",
                file_path="missing.py",
            )


class TestGetFileContent:
    """Tests for get_file_content tool."""

    def test_get_content_success(self) -> None:
        """Test getting file content successfully."""
        mock_client = MagicMock()
        content = "print('hello')"
        mock_content = MagicMock()
        mock_content.content = base64.b64encode(content.encode()).decode()
        mock_content.encoding = "base64"
        mock_content.sha = "abc123"

        mock_repo = MagicMock()
        mock_repo.get_contents.return_value = mock_content
        mock_client.get_repo.return_value = mock_repo

        result = get_file_content(
            client=mock_client,
            repository="owner/repo",
            file_path="test.py",
            ref="main",
        )

        assert result["content"] == content
        assert result["sha"] == "abc123"

    def test_get_content_file_not_found(self) -> None:
        """Test handling file not found."""
        mock_client = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"}, {})
        mock_client.get_repo.return_value = mock_repo

        with pytest.raises(GitHubToolError, match="not found"):
            get_file_content(
                client=mock_client,
                repository="owner/repo",
                file_path="missing.py",
                ref="main",
            )
