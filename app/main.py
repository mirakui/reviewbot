"""Lambda entry point for ReviewBot webhook handler."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any

from app import __version__
from app.utils.logging import configure_logging, get_logger
from app.webhook.handler import WebhookHandler, WebhookParseError
from app.webhook.validators import WebhookSignatureError, verify_webhook_signature

if TYPE_CHECKING:
    from app.models.pull_request import PullRequest

# Configure logging on module load
configure_logging()
logger = get_logger("main")


def trigger_review(pr: PullRequest) -> None:
    """Trigger a review for the given pull request.

    This is a placeholder that will be implemented in Phase 4 (US1).
    For now, it just logs that a review would be triggered.

    Args:
        pr: The pull request to review.
    """
    logger.info(
        "Review triggered",
        extra={
            "pr_number": pr.number,
            "repository": pr.repository,
            "head_sha": pr.head_sha,
        },
    )
    # TODO: Implement actual review logic in Phase 4


def _create_response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Create a Lambda response.

    Args:
        status_code: HTTP status code.
        body: Response body dictionary.

    Returns:
        Lambda response dictionary.
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def _handle_webhook(event: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0911
    """Handle a webhook request.

    Args:
        event: Lambda event from API Gateway.

    Returns:
        Lambda response dictionary.
    """
    # Get headers (case-insensitive)
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}

    event_type = headers.get("x-github-event", "")
    delivery_id = headers.get("x-github-delivery", "")
    signature = headers.get("x-hub-signature-256", "")

    logger.info(
        "Received webhook",
        extra={
            "event_type": event_type,
            "delivery_id": delivery_id,
        },
    )

    # Get webhook secret from environment
    webhook_secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.error("GITHUB_WEBHOOK_SECRET not configured")
        return _create_response(
            500,
            {
                "error": "configuration_error",
                "message": "Webhook secret not configured",
            },
        )

    # Verify signature
    body = event.get("body", "")
    body_bytes = body.encode() if isinstance(body, str) else body

    try:
        verify_webhook_signature(body_bytes, signature, webhook_secret)
    except WebhookSignatureError as e:
        logger.warning("Signature verification failed", extra={"error": str(e)})
        return _create_response(
            403,
            {
                "error": "invalid_signature",
                "message": str(e),
            },
        )

    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON payload", extra={"error": str(e)})
        return _create_response(
            400,
            {
                "error": "invalid_payload",
                "message": f"Invalid JSON: {e}",
            },
        )

    # Dispatch event
    handler = WebhookHandler()

    try:
        result = handler.dispatch(event_type, payload)
    except WebhookParseError as e:
        logger.warning("Failed to parse webhook", extra={"error": str(e)})
        return _create_response(
            400,
            {
                "error": "invalid_payload",
                "message": str(e),
            },
        )

    # Handle based on result
    # Check for parse errors first (applies to PR events with missing fields)
    if result.get("event_type") == "pull_request" and "error" in result:
        return _create_response(
            400,
            {
                "error": "invalid_payload",
                "message": result["error"],
            },
        )

    if result.get("should_review") and "pull_request" in result:
        pr = result["pull_request"]

        try:
            trigger_review(pr)
            return _create_response(
                202,
                {
                    "status": "queued",
                    "message": f"Review queued for PR #{pr.number}",
                },
            )
        except Exception as e:
            logger.error("Failed to trigger review", extra={"error": str(e)})
            return _create_response(
                500,
                {
                    "error": "internal_error",
                    "message": "Failed to queue review",
                },
            )

    elif result.get("event_type") == "ping":
        return _create_response(
            200,
            {
                "status": "ok",
                "message": f"Pong! {result.get('zen', '')}",
            },
        )

    elif result.get("event_type") == "installation":
        return _create_response(
            200,
            {
                "status": "ok",
                "message": f"Installation event processed: {result.get('action', '')}",
            },
        )

    elif result.get("status") == "ignored":
        return _create_response(
            200,
            {
                "status": "ignored",
                "message": f"Event type '{event_type}' not handled",
            },
        )

    else:
        # PR event that doesn't need review (closed, etc.)
        return _create_response(
            200,
            {
                "status": "ignored",
                "message": f"Action '{result.get('action', '')}' does not trigger review",
            },
        )


def _handle_health() -> dict[str, Any]:
    """Handle health check request.

    Returns:
        Lambda response dictionary.
    """
    # Basic health check - could be extended to check Bedrock, GitHub connectivity
    return _create_response(
        200,
        {
            "status": "healthy",
            "version": __version__,
        },
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:  # noqa: ARG001
    """AWS Lambda handler for webhook requests.

    Args:
        event: Lambda event from API Gateway.
        context: Lambda context (unused but required by AWS Lambda).

    Returns:
        Lambda response dictionary.
    """
    path = event.get("path", "")
    method = event.get("httpMethod", "")

    logger.info(
        "Request received",
        extra={"path": path, "method": method},
    )

    # Route request
    if path == "/health" and method == "GET":
        return _handle_health()
    elif path == "/webhook" and method == "POST":
        return _handle_webhook(event)
    else:
        return _create_response(
            404,
            {
                "error": "not_found",
                "message": f"Path not found: {method} {path}",
            },
        )


# For local development
if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.requests import Request  # noqa: TC002
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    async def webhook_route(request: Request) -> JSONResponse:
        """Handle webhook requests for local development."""
        body = await request.body()
        event = {
            "httpMethod": "POST",
            "path": "/webhook",
            "headers": dict(request.headers),
            "body": body.decode(),
        }
        response = lambda_handler(event, None)
        return JSONResponse(
            content=json.loads(response["body"]),
            status_code=response["statusCode"],
        )

    async def health_route(request: Request) -> JSONResponse:
        """Handle health check requests for local development."""
        del request  # unused but required by Starlette routing
        event = {
            "httpMethod": "GET",
            "path": "/health",
        }
        response = lambda_handler(event, None)
        return JSONResponse(
            content=json.loads(response["body"]),
            status_code=response["statusCode"],
        )

    app = Starlette(
        routes=[
            Route("/webhook", webhook_route, methods=["POST"]),
            Route("/health", health_route, methods=["GET"]),
        ]
    )

    print(f"Starting ReviewBot v{__version__} on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
