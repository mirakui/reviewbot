"""GitHub API tools for the review agent."""

import base64
import os
from typing import Any

from github import Auth, Github, GithubException, GithubIntegration

from app.utils.logging import get_logger

logger = get_logger("tools.github")


class GitHubToolError(Exception):
    """Error raised by GitHub tools."""

    pass


def _get_private_key() -> str:
    """Get the GitHub App private key from environment.

    Returns:
        The private key content.

    Raises:
        GitHubToolError: If private key is not configured.
    """
    # Try inline key first
    key = os.environ.get("GITHUB_PRIVATE_KEY")
    if key:
        return key

    # Try key file path
    key_path = os.environ.get("GITHUB_PRIVATE_KEY_PATH")
    if key_path:
        from pathlib import Path  # noqa: PLC0415

        try:
            return Path(key_path).read_text()
        except OSError as e:
            raise GitHubToolError(f"Failed to read private key from {key_path}: {e}") from e

    raise GitHubToolError(
        "GitHub private key not configured. "
        "Set GITHUB_PRIVATE_KEY or GITHUB_PRIVATE_KEY_PATH environment variable."
    )


def create_github_client(installation_id: int) -> Github:
    """Create an authenticated GitHub client for an installation.

    Args:
        installation_id: The GitHub App installation ID.

    Returns:
        Authenticated Github client.

    Raises:
        GitHubToolError: If authentication fails.
    """
    app_id = os.environ.get("GITHUB_APP_ID")
    if not app_id:
        raise GitHubToolError("GITHUB_APP_ID environment variable not set")

    try:
        private_key = _get_private_key()
        auth = Auth.AppAuth(int(app_id), private_key)
        gi = GithubIntegration(auth=auth)
        return gi.get_github_for_installation(installation_id)
    except Exception as e:
        raise GitHubToolError(f"Failed to create GitHub client: {e}") from e


def get_pr_metadata(
    client: Github,
    pr_number: int,
    repository: str,
) -> dict[str, Any]:
    """Fetch metadata about a pull request.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.

    Returns:
        Dictionary with PR metadata.

    Raises:
        GitHubToolError: If PR cannot be fetched.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        return {
            "title": pr.title,
            "body": pr.body,
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "files_changed": pr.changed_files,
            "additions": pr.additions,
            "deletions": pr.deletions,
        }

    except GithubException as e:
        if e.status == 404:
            raise GitHubToolError(f"PR #{pr_number} not found in {repository}") from e
        raise GitHubToolError(f"GitHub API error: {e}") from e


def list_pr_files(
    client: Github,
    pr_number: int,
    repository: str,
) -> list[dict[str, Any]]:
    """List all files changed in a pull request.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.

    Returns:
        List of file information dictionaries.

    Raises:
        GitHubToolError: If files cannot be fetched.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        files = []
        for f in pr.get_files():
            files.append(
                {
                    "filename": f.filename,
                    "status": f.status,
                    "additions": f.additions,
                    "deletions": f.deletions,
                    "sha": f.sha,
                    "patch": getattr(f, "patch", None),
                    "previous_filename": getattr(f, "previous_filename", None),
                }
            )

        logger.info(
            "Listed PR files",
            extra={
                "pr_number": pr_number,
                "repository": repository,
                "file_count": len(files),
            },
        )

        return files

    except GithubException as e:
        raise GitHubToolError(f"Failed to list PR files: {e}") from e


def get_file_diff(
    client: Github,
    pr_number: int,
    repository: str,
    file_path: str,
) -> dict[str, Any]:
    """Get the diff for a specific file in a pull request.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.
        file_path: Path to the file in the repository.

    Returns:
        Dictionary with file diff information.

    Raises:
        GitHubToolError: If file is not found in PR.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        for f in pr.get_files():
            if f.filename == file_path:
                return {
                    "filename": f.filename,
                    "status": f.status,
                    "patch": getattr(f, "patch", None),
                    "additions": f.additions,
                    "deletions": f.deletions,
                }

        raise GitHubToolError(f"File '{file_path}' not found in PR #{pr_number}")

    except GithubException as e:
        raise GitHubToolError(f"Failed to get file diff: {e}") from e


def get_file_content(
    client: Github,
    repository: str,
    file_path: str,
    ref: str,
) -> dict[str, Any]:
    """Get the full content of a file at a specific ref.

    Args:
        client: Authenticated GitHub client.
        repository: Repository in owner/repo format.
        file_path: Path to the file in the repository.
        ref: Git ref (branch, tag, or SHA).

    Returns:
        Dictionary with file content.

    Raises:
        GitHubToolError: If file cannot be fetched.
    """
    try:
        repo = client.get_repo(repository)
        content = repo.get_contents(file_path, ref=ref)

        # Handle directory case
        if isinstance(content, list):
            raise GitHubToolError(f"'{file_path}' is a directory, not a file")

        # Decode content
        if content.encoding == "base64":
            decoded = base64.b64decode(content.content).decode("utf-8")
        else:
            decoded = content.content

        return {
            "content": decoded,
            "encoding": content.encoding,
            "sha": content.sha,
        }

    except GithubException as e:
        if e.status == 404:
            raise GitHubToolError(f"File '{file_path}' not found at ref '{ref}'") from e
        raise GitHubToolError(f"Failed to get file content: {e}") from e
