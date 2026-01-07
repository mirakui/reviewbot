"""Webhook signature validation."""

import hashlib
import hmac


class WebhookSignatureError(Exception):
    """Raised when webhook signature verification fails."""

    pass


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> None:
    """Verify the HMAC-SHA256 signature of a webhook payload.

    Args:
        payload: The raw request body bytes.
        signature: The X-Hub-Signature-256 header value.
        secret: The webhook secret configured in the GitHub App.

    Raises:
        WebhookSignatureError: If signature is invalid or missing.
    """
    if not signature:
        raise WebhookSignatureError("Missing signature header")

    if not signature.startswith("sha256="):
        raise WebhookSignatureError("Invalid signature format: must start with 'sha256='")

    expected_signature = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_signature):
        raise WebhookSignatureError("Signature verification failed")
