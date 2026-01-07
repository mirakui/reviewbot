"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(autouse=True)
def reset_env() -> Generator[None]:
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_env() -> dict[str, str]:
    """Standard environment variables for testing."""
    return {
        "GITHUB_APP_ID": "123456",
        "GITHUB_PRIVATE_KEY": (
            "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
        ),
        "GITHUB_WEBHOOK_SECRET": "test-webhook-secret",
        "AWS_REGION": "us-west-2",
        "LOG_LEVEL": "DEBUG",
    }


@pytest.fixture
def set_mock_env(mock_env: dict[str, str]) -> Generator[None]:
    """Set mock environment variables for a test."""
    for key, value in mock_env.items():
        os.environ[key] = value
    yield


@pytest.fixture
def sample_pr_payload() -> dict[str, Any]:
    """Sample GitHub PR webhook payload."""
    return {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 1234567890,
            "number": 42,
            "state": "open",
            "title": "Add new feature",
            "body": "This PR adds a new feature.",
            "user": {"login": "testuser", "id": 12345},
            "head": {
                "ref": "feature-branch",
                "sha": "abc123def456abc123def456abc123def456abc1",
            },
            "base": {"ref": "main", "sha": "def456abc123def456abc123def456abc123def4"},
            "html_url": "https://github.com/owner/repo/pull/42",
            "changed_files": 3,
            "additions": 100,
            "deletions": 20,
        },
        "repository": {
            "id": 987654321,
            "full_name": "owner/repo",
            "clone_url": "https://github.com/owner/repo.git",
            "default_branch": "main",
        },
        "sender": {"login": "testuser", "id": 12345},
        "installation": {"id": 11111111},
    }


@pytest.fixture
def sample_ping_payload() -> dict[str, Any]:
    """Sample GitHub ping webhook payload."""
    return {
        "zen": "Responsive is better than fast.",
        "hook_id": 123456,
        "hook": {"type": "App", "id": 789012},
    }


@pytest.fixture
def sample_file_diff() -> dict[str, Any]:
    """Sample file diff from GitHub API."""
    return {
        "filename": "src/main.py",
        "status": "modified",
        "additions": 10,
        "deletions": 5,
        "sha": "abc123def456abc123def456abc123def456abc1",
        "patch": (
            "@@ -1,5 +1,10 @@\n def hello():\n-    return 'Hello'\n+    return 'Hello, World!'"
        ),
    }


@pytest.fixture
def mock_github_client() -> MagicMock:
    """Mock GitHub client."""
    client = MagicMock()
    client.get_repo.return_value = MagicMock()
    return client


@pytest.fixture
def mock_bedrock_client() -> MagicMock:
    """Mock Bedrock client."""
    client = MagicMock()
    client.invoke_model.return_value = {"body": MagicMock(read=lambda: b'{"completion": "test"}')}
    return client


@pytest.fixture
def webhook_signature(mock_env: dict[str, str]) -> str:
    """Generate a valid webhook signature for testing."""
    secret = mock_env["GITHUB_WEBHOOK_SECRET"]
    body = b'{"test": "payload"}'
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"
