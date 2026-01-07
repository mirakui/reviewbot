"""Integration tests for webhook flow."""

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import patch

import pytest

from app.main import lambda_handler


class TestWebhookFlow:
    """Integration tests for the complete webhook flow."""

    @pytest.fixture
    def webhook_secret(self) -> str:
        """Webhook secret for testing."""
        return "test-webhook-secret"

    @pytest.fixture
    def mock_env(self, webhook_secret: str) -> dict[str, str]:
        """Mock environment variables."""
        return {
            "GITHUB_APP_ID": "123456",
            "GITHUB_PRIVATE_KEY": (
                "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
            ),
            "GITHUB_WEBHOOK_SECRET": webhook_secret,
            "AWS_REGION": "us-west-2",
        }

    def _create_lambda_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        secret: str,
    ) -> dict[str, Any]:
        """Create a Lambda event from API Gateway."""
        body = json.dumps(payload)
        signature = "sha256=" + hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

        return {
            "httpMethod": "POST",
            "path": "/webhook",
            "headers": {
                "X-GitHub-Event": event_type,
                "X-GitHub-Delivery": "test-delivery-123",
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
            "body": body,
        }

    def test_full_pr_opened_flow(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test the full flow from PR opened webhook to review trigger."""
        with patch.dict("os.environ", mock_env), patch("app.main.trigger_review") as mock_trigger:
            mock_trigger.return_value = None

            event = self._create_lambda_event("pull_request", sample_pr_payload, webhook_secret)
            response = lambda_handler(event, None)

            # Verify response
            assert response["statusCode"] == 202
            body = json.loads(response["body"])
            assert body["status"] == "queued"

            # Verify review was triggered
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            pr = call_args[0][0]  # First positional argument
            assert pr.number == 42
            assert pr.repository == "owner/repo"

    def test_pr_synchronize_triggers_rereview(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test that PR synchronize event triggers re-review."""
        sample_pr_payload["action"] = "synchronize"
        sample_pr_payload["before"] = "old_sha_123"
        sample_pr_payload["after"] = "new_sha_456"

        with patch.dict("os.environ", mock_env), patch("app.main.trigger_review") as mock_trigger:
            mock_trigger.return_value = None

            event = self._create_lambda_event("pull_request", sample_pr_payload, webhook_secret)
            response = lambda_handler(event, None)

            assert response["statusCode"] == 202
            mock_trigger.assert_called_once()

    def test_pr_closed_does_not_trigger_review(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test that PR closed event does not trigger review."""
        sample_pr_payload["action"] = "closed"

        with patch.dict("os.environ", mock_env), patch("app.main.trigger_review") as mock_trigger:
            event = self._create_lambda_event("pull_request", sample_pr_payload, webhook_secret)
            response = lambda_handler(event, None)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "ignored"
            mock_trigger.assert_not_called()

    def test_ping_flow(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_ping_payload: dict[str, Any],
    ) -> None:
        """Test ping event handling flow."""
        with patch.dict("os.environ", mock_env):
            event = self._create_lambda_event("ping", sample_ping_payload, webhook_secret)
            response = lambda_handler(event, None)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "ok"
            assert "message" in body

    def test_installation_created_flow(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
    ) -> None:
        """Test installation created event flow."""
        payload = {
            "action": "created",
            "installation": {"id": 12345},
            "repositories": [
                {"full_name": "owner/repo1"},
                {"full_name": "owner/repo2"},
            ],
            "sender": {"login": "admin", "id": 99999},
        }

        with patch.dict("os.environ", mock_env):
            event = self._create_lambda_event("installation", payload, webhook_secret)
            response = lambda_handler(event, None)

            assert response["statusCode"] == 200
            body = json.loads(response["body"])
            assert body["status"] == "ok"

    def test_signature_verification_in_flow(
        self,
        mock_env: dict[str, str],
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test that signature verification is enforced in the flow."""
        with patch.dict("os.environ", mock_env):
            # Create event with wrong signature
            event = self._create_lambda_event("pull_request", sample_pr_payload, "wrong-secret")
            response = lambda_handler(event, None)

            assert response["statusCode"] == 403
            body = json.loads(response["body"])
            assert body["error"] == "invalid_signature"

    def test_malformed_json_handling(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
    ) -> None:
        """Test handling of malformed JSON body."""
        body = "not valid json"
        signature = (
            "sha256=" + hmac.new(webhook_secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        )

        with patch.dict("os.environ", mock_env):
            event = {
                "httpMethod": "POST",
                "path": "/webhook",
                "headers": {
                    "X-GitHub-Event": "pull_request",
                    "X-GitHub-Delivery": "test-123",
                    "X-Hub-Signature-256": signature,
                    "Content-Type": "application/json",
                },
                "body": body,
            }
            response = lambda_handler(event, None)

            assert response["statusCode"] == 400
            body_parsed = json.loads(response["body"])
            assert body_parsed["error"] == "invalid_payload"

    def test_logging_in_flow(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test that proper logging occurs during webhook flow."""
        with patch.dict("os.environ", mock_env), patch("app.main.trigger_review") as mock_trigger:
            mock_trigger.return_value = None

            event = self._create_lambda_event("pull_request", sample_pr_payload, webhook_secret)
            lambda_handler(event, None)

            # Verify logging occurred (actual log verification depends on implementation)
            # This is a placeholder for log verification
