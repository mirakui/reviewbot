"""Unit tests for webhook handling."""

import hashlib
import hmac
from typing import Any

import pytest

from app.models.pull_request import PullRequest
from app.webhook.handler import (
    WebhookHandler,
    WebhookParseError,
    parse_ping_event,
    parse_pr_event,
)
from app.webhook.validators import WebhookSignatureError, verify_webhook_signature


class TestVerifyWebhookSignature:
    """Tests for webhook signature verification."""

    def test_valid_signature(self) -> None:
        """Test that a valid signature passes verification."""
        secret = "test-secret"
        payload = b'{"action": "opened"}'
        signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        # Should not raise
        verify_webhook_signature(payload, signature, secret)

    def test_invalid_signature(self) -> None:
        """Test that an invalid signature raises error."""
        secret = "test-secret"
        payload = b'{"action": "opened"}'
        signature = "sha256=invalid"

        with pytest.raises(WebhookSignatureError):
            verify_webhook_signature(payload, signature, secret)

    def test_missing_prefix(self) -> None:
        """Test that signature without sha256= prefix raises error."""
        secret = "test-secret"
        payload = b'{"action": "opened"}'
        signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

        with pytest.raises(WebhookSignatureError):
            verify_webhook_signature(payload, signature, secret)

    def test_empty_signature(self) -> None:
        """Test that empty signature raises error."""
        secret = "test-secret"
        payload = b'{"action": "opened"}'

        with pytest.raises(WebhookSignatureError):
            verify_webhook_signature(payload, "", secret)

    def test_wrong_secret(self) -> None:
        """Test that wrong secret fails verification."""
        correct_secret = "correct-secret"
        wrong_secret = "wrong-secret"
        payload = b'{"action": "opened"}'
        signature = (
            "sha256=" + hmac.new(correct_secret.encode(), payload, hashlib.sha256).hexdigest()
        )

        with pytest.raises(WebhookSignatureError):
            verify_webhook_signature(payload, signature, wrong_secret)


class TestParsePrEvent:
    """Tests for PR event parsing."""

    def test_parse_opened_event(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test parsing a PR opened event."""
        pr = parse_pr_event(sample_pr_payload)

        assert isinstance(pr, PullRequest)
        assert pr.number == 42
        assert pr.title == "Add new feature"
        assert pr.author == "testuser"
        assert pr.repository == "owner/repo"
        assert pr.head_sha == "abc123def456abc123def456abc123def456abc1"
        assert pr.installation_id == 11111111

    def test_parse_synchronize_event(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test parsing a PR synchronize event."""
        sample_pr_payload["action"] = "synchronize"
        sample_pr_payload["before"] = "old_sha"
        sample_pr_payload["after"] = "new_sha"

        pr = parse_pr_event(sample_pr_payload)

        assert pr.number == 42

    def test_parse_missing_pr_data(self) -> None:
        """Test parsing event with missing pull_request data."""
        payload = {"action": "opened", "number": 1}

        with pytest.raises(WebhookParseError) as exc_info:
            parse_pr_event(payload)

        assert "pull_request" in str(exc_info.value)

    def test_parse_missing_installation(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test parsing event with missing installation data."""
        del sample_pr_payload["installation"]

        with pytest.raises(WebhookParseError) as exc_info:
            parse_pr_event(sample_pr_payload)

        assert "installation" in str(exc_info.value)

    def test_parse_with_empty_body(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test parsing PR with no body."""
        sample_pr_payload["pull_request"]["body"] = None

        pr = parse_pr_event(sample_pr_payload)

        assert pr.body is None


class TestParsePingEvent:
    """Tests for ping event parsing."""

    def test_parse_valid_ping(self, sample_ping_payload: dict[str, Any]) -> None:
        """Test parsing a valid ping event."""
        result = parse_ping_event(sample_ping_payload)

        assert result["zen"] == "Responsive is better than fast."
        assert result["hook_id"] == 123456

    def test_parse_ping_missing_zen(self) -> None:
        """Test parsing ping event missing zen."""
        payload = {"hook_id": 123456}

        with pytest.raises(WebhookParseError) as exc_info:
            parse_ping_event(payload)

        assert "zen" in str(exc_info.value)


class TestWebhookHandler:
    """Tests for webhook handler/dispatcher."""

    def test_dispatch_pr_opened(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test dispatching a PR opened event."""
        handler = WebhookHandler()
        result = handler.dispatch("pull_request", sample_pr_payload)

        assert result["event_type"] == "pull_request"
        assert result["action"] == "opened"
        assert result["should_review"] is True

    def test_dispatch_pr_synchronize(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test dispatching a PR synchronize event."""
        sample_pr_payload["action"] = "synchronize"
        handler = WebhookHandler()
        result = handler.dispatch("pull_request", sample_pr_payload)

        assert result["action"] == "synchronize"
        assert result["should_review"] is True

    def test_dispatch_pr_closed(self, sample_pr_payload: dict[str, Any]) -> None:
        """Test dispatching a PR closed event (should not trigger review)."""
        sample_pr_payload["action"] = "closed"
        handler = WebhookHandler()
        result = handler.dispatch("pull_request", sample_pr_payload)

        assert result["action"] == "closed"
        assert result["should_review"] is False

    def test_dispatch_ping(self, sample_ping_payload: dict[str, Any]) -> None:
        """Test dispatching a ping event."""
        handler = WebhookHandler()
        result = handler.dispatch("ping", sample_ping_payload)

        assert result["event_type"] == "ping"
        assert result["status"] == "ok"

    def test_dispatch_unsupported_event(self) -> None:
        """Test dispatching an unsupported event type."""
        handler = WebhookHandler()
        result = handler.dispatch("issues", {"action": "opened"})

        assert result["event_type"] == "issues"
        assert result["status"] == "ignored"

    def test_dispatch_installation_event(self) -> None:
        """Test dispatching an installation event."""
        handler = WebhookHandler()
        payload = {
            "action": "created",
            "installation": {"id": 12345},
            "repositories": [{"full_name": "owner/repo"}],
        }
        result = handler.dispatch("installation", payload)

        assert result["event_type"] == "installation"
        assert result["status"] == "ok"
