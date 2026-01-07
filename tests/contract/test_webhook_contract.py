"""Contract tests for webhook API per webhook-api.yaml."""

import hashlib
import hmac
import json
from typing import Any
from unittest.mock import patch

import pytest

from app.main import lambda_handler


class TestWebhookContract:
    """Contract tests verifying webhook API matches OpenAPI spec."""

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

    def _create_signature(self, payload: bytes, secret: str) -> str:
        """Create HMAC-SHA256 signature for payload."""
        return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    def _create_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        secret: str,
        delivery_id: str = "test-delivery-123",
    ) -> dict[str, Any]:
        """Create a Lambda event simulating API Gateway."""
        body = json.dumps(payload)
        signature = self._create_signature(body.encode(), secret)

        return {
            "httpMethod": "POST",
            "path": "/webhook",
            "headers": {
                "X-GitHub-Event": event_type,
                "X-GitHub-Delivery": delivery_id,
                "X-Hub-Signature-256": signature,
                "Content-Type": "application/json",
            },
            "body": body,
        }

    def test_webhook_returns_200_for_ping(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_ping_payload: dict[str, Any],
    ) -> None:
        """Test webhook returns 200 OK for ping event per contract."""
        with patch.dict("os.environ", mock_env):
            event = self._create_event("ping", sample_ping_payload, webhook_secret)
            response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ok"

    def test_webhook_returns_202_for_pr_opened(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test webhook returns 202 Accepted for PR opened event per contract."""
        with patch.dict("os.environ", mock_env), patch("app.main.trigger_review") as mock_trigger:
            mock_trigger.return_value = None
            event = self._create_event("pull_request", sample_pr_payload, webhook_secret)
            response = lambda_handler(event, None)

        assert response["statusCode"] == 202
        body = json.loads(response["body"])
        assert body["status"] == "queued"

    def test_webhook_returns_403_for_invalid_signature(
        self,
        mock_env: dict[str, str],
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test webhook returns 403 Forbidden for invalid signature per contract."""
        with patch.dict("os.environ", mock_env):
            event = self._create_event(
                "pull_request",
                sample_pr_payload,
                "wrong-secret",  # Wrong secret
            )
            response = lambda_handler(event, None)

        assert response["statusCode"] == 403
        body = json.loads(response["body"])
        assert body["error"] == "invalid_signature"

    def test_webhook_returns_400_for_invalid_payload(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
    ) -> None:
        """Test webhook returns 400 Bad Request for invalid payload per contract."""
        with patch.dict("os.environ", mock_env):
            # Missing required fields
            event = self._create_event(
                "pull_request",
                {"action": "opened"},
                webhook_secret,  # Missing pull_request
            )
            response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        body = json.loads(response["body"])
        assert body["error"] == "invalid_payload"

    def test_webhook_returns_200_ignored_for_unsupported_event(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
    ) -> None:
        """Test webhook returns 200 with status ignored for unsupported events."""
        with patch.dict("os.environ", mock_env):
            event = self._create_event("issues", {"action": "opened", "issue": {}}, webhook_secret)
            response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "ignored"

    def test_health_endpoint_returns_200(
        self,
        mock_env: dict[str, str],
    ) -> None:
        """Test health check endpoint returns 200 OK per contract."""
        with patch.dict("os.environ", mock_env):
            event = {
                "httpMethod": "GET",
                "path": "/health",
            }
            response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in body

    def test_webhook_response_format(
        self,
        mock_env: dict[str, str],
        webhook_secret: str,
        sample_ping_payload: dict[str, Any],
    ) -> None:
        """Test webhook response matches WebhookResponse schema."""
        with patch.dict("os.environ", mock_env):
            event = self._create_event("ping", sample_ping_payload, webhook_secret)
            response = lambda_handler(event, None)

        body = json.loads(response["body"])
        # WebhookResponse requires 'status' field
        assert "status" in body
        assert body["status"] in ["ok", "queued", "ignored"]

    def test_error_response_format(
        self,
        mock_env: dict[str, str],
        sample_pr_payload: dict[str, Any],
    ) -> None:
        """Test error response matches ErrorResponse schema."""
        with patch.dict("os.environ", mock_env):
            event = self._create_event("pull_request", sample_pr_payload, "wrong-secret")
            response = lambda_handler(event, None)

        body = json.loads(response["body"])
        # ErrorResponse requires 'error' and 'message' fields
        assert "error" in body
        assert "message" in body
        assert isinstance(body["error"], str)
        assert isinstance(body["message"], str)
