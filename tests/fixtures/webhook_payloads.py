"""Sample webhook payloads for testing."""

from typing import Any


def create_pr_payload(
    action: str = "opened",
    pr_number: int = 1,
    title: str = "Test PR",
    body: str | None = "Test description",
    author: str = "testuser",
    repository: str = "owner/repo",
    base_branch: str = "main",
    head_branch: str = "feature",
    head_sha: str = "a" * 40,  # Valid 40-character hex SHA
    installation_id: int = 12345,
    draft: bool = False,
    merged: bool = False,
    changed_files: int = 1,
    additions: int = 10,
    deletions: int = 5,
) -> dict[str, Any]:
    """Create a pull_request webhook payload.

    Args:
        action: The PR action (opened, synchronize, closed, etc.).
        pr_number: The PR number.
        title: The PR title.
        body: The PR description.
        author: The PR author username.
        repository: The repository in owner/repo format.
        base_branch: The base branch name.
        head_branch: The head branch name.
        head_sha: The head commit SHA (must be 40-character hex string).
        installation_id: The GitHub App installation ID.
        draft: Whether the PR is a draft.
        merged: Whether the PR has been merged.
        changed_files: Number of files changed.
        additions: Number of lines added.
        deletions: Number of lines deleted.

    Returns:
        A valid pull_request webhook payload.
    """
    owner, repo = repository.split("/")

    return {
        "action": action,
        "number": pr_number,
        "pull_request": {
            "number": pr_number,
            "title": title,
            "body": body,
            "user": {"login": author},
            "head": {
                "sha": head_sha,
                "ref": head_branch,
                "repo": {
                    "full_name": repository,
                },
            },
            "base": {
                "ref": base_branch,
                "repo": {
                    "full_name": repository,
                },
            },
            "html_url": f"https://github.com/{repository}/pull/{pr_number}",
            "draft": draft,
            "merged": merged,
            "changed_files": changed_files,
            "additions": additions,
            "deletions": deletions,
        },
        "repository": {
            "full_name": repository,
            "name": repo,
            "owner": {"login": owner},
        },
        "installation": {"id": installation_id},
    }


def create_fork_pr_payload(
    pr_number: int = 1,
    fork_owner: str = "forker",
    upstream_owner: str = "upstream",
    repo: str = "repo",
    head_sha: str = "b" * 40,  # Valid 40-character hex SHA
) -> dict[str, Any]:
    """Create a pull_request payload from a fork.

    Args:
        pr_number: The PR number.
        fork_owner: The owner of the fork.
        upstream_owner: The owner of the upstream repo.
        repo: The repository name.
        head_sha: The head commit SHA.

    Returns:
        A pull_request payload from a fork.
    """
    return {
        "action": "opened",
        "number": pr_number,
        "pull_request": {
            "number": pr_number,
            "title": "Fork PR",
            "body": "PR from a fork",
            "user": {"login": fork_owner},
            "head": {
                "sha": head_sha,
                "ref": "feature",
                "repo": {
                    "full_name": f"{fork_owner}/{repo}",
                },
            },
            "base": {
                "ref": "main",
                "repo": {
                    "full_name": f"{upstream_owner}/{repo}",
                },
            },
            "html_url": f"https://github.com/{upstream_owner}/{repo}/pull/{pr_number}",
            "draft": False,
            "merged": False,
            "changed_files": 1,
            "additions": 10,
            "deletions": 5,
        },
        "repository": {
            "full_name": f"{upstream_owner}/{repo}",
            "name": repo,
            "owner": {"login": upstream_owner},
        },
        "installation": {"id": 12345},
    }


def create_ping_payload(
    zen: str = "Design for failure.",
    hook_id: int = 123456,
) -> dict[str, Any]:
    """Create a ping webhook payload.

    Args:
        zen: The GitHub zen message.
        hook_id: The webhook ID.

    Returns:
        A valid ping webhook payload.
    """
    return {
        "zen": zen,
        "hook_id": hook_id,
        "hook": {"type": "App"},
    }


def create_installation_payload(
    action: str = "created",
    installation_id: int = 12345,
    account: str = "org-name",
) -> dict[str, Any]:
    """Create an installation webhook payload.

    Args:
        action: The installation action (created, deleted, etc.).
        installation_id: The installation ID.
        account: The account name.

    Returns:
        A valid installation webhook payload.
    """
    return {
        "action": action,
        "installation": {
            "id": installation_id,
            "account": {"login": account},
        },
    }
