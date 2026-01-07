"""Webhook event handler and dispatcher."""

from typing import Any, ClassVar

from app.models.pull_request import PullRequest
from app.utils.logging import get_logger

logger = get_logger("webhook.handler")


class WebhookParseError(Exception):
    """Raised when webhook payload parsing fails."""

    pass


def parse_pr_event(payload: dict[str, Any]) -> PullRequest:
    """Parse a pull_request webhook event.

    Args:
        payload: The webhook payload.

    Returns:
        PullRequest instance.

    Raises:
        WebhookParseError: If required fields are missing.
    """
    try:
        if "pull_request" not in payload:
            raise WebhookParseError("Missing 'pull_request' in payload")

        if "installation" not in payload:
            raise WebhookParseError("Missing 'installation' in payload")

        return PullRequest.from_webhook_payload(payload)

    except KeyError as e:
        raise WebhookParseError(f"Missing required field: {e}") from e
    except ValueError as e:
        raise WebhookParseError(f"Invalid field value: {e}") from e


def parse_ping_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse a ping webhook event.

    Args:
        payload: The webhook payload.

    Returns:
        Dictionary with ping event data.

    Raises:
        WebhookParseError: If required fields are missing.
    """
    if "zen" not in payload:
        raise WebhookParseError("Missing 'zen' in ping payload")

    return {
        "zen": payload["zen"],
        "hook_id": payload.get("hook_id"),
        "hook_type": payload.get("hook", {}).get("type"),
    }


class WebhookHandler:
    """Handles and dispatches GitHub webhook events."""

    # Actions that should trigger a review
    REVIEW_ACTIONS: ClassVar[set[str]] = {"opened", "synchronize", "reopened"}

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a webhook event to the appropriate handler.

        Args:
            event_type: The X-GitHub-Event header value.
            payload: The webhook payload.

        Returns:
            Dictionary with dispatch result.
        """
        logger.info(
            "Dispatching webhook event",
            extra={"event_type": event_type, "action": payload.get("action")},
        )

        if event_type == "pull_request":
            return self._handle_pull_request(payload)
        elif event_type == "ping":
            return self._handle_ping(payload)
        elif event_type == "installation":
            return self._handle_installation(payload)
        else:
            return self._handle_unsupported(event_type, payload)

    def _handle_pull_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a pull_request event.

        Args:
            payload: The webhook payload.

        Returns:
            Dictionary with handling result.
        """
        action = payload.get("action", "")
        should_review = action in self.REVIEW_ACTIONS

        result: dict[str, Any] = {
            "event_type": "pull_request",
            "action": action,
            "should_review": should_review,
        }

        if should_review:
            try:
                pr = parse_pr_event(payload)
                result["pull_request"] = pr
                logger.info(
                    "PR event parsed for review",
                    extra={
                        "pr_number": pr.number,
                        "repository": pr.repository,
                        "action": action,
                    },
                )
            except WebhookParseError as e:
                logger.error("Failed to parse PR event", extra={"error": str(e)})
                result["should_review"] = False
                result["error"] = str(e)
        else:
            logger.info(
                "PR action does not require review",
                extra={"action": action},
            )

        return result

    def _handle_ping(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle a ping event.

        Args:
            payload: The webhook payload.

        Returns:
            Dictionary with handling result.
        """
        try:
            ping_data = parse_ping_event(payload)
            logger.info("Ping event received", extra={"zen": ping_data["zen"]})
            return {
                "event_type": "ping",
                "status": "ok",
                "zen": ping_data["zen"],
            }
        except WebhookParseError as e:
            logger.error("Failed to parse ping event", extra={"error": str(e)})
            return {
                "event_type": "ping",
                "status": "error",
                "error": str(e),
            }

    def _handle_installation(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Handle an installation event.

        Args:
            payload: The webhook payload.

        Returns:
            Dictionary with handling result.
        """
        action = payload.get("action", "")
        installation_id = payload.get("installation", {}).get("id")

        logger.info(
            "Installation event received",
            extra={"action": action, "installation_id": installation_id},
        )

        return {
            "event_type": "installation",
            "action": action,
            "status": "ok",
            "installation_id": installation_id,
        }

    def _handle_unsupported(
        self,
        event_type: str,
        payload: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, Any]:
        """Handle an unsupported event type.

        Args:
            event_type: The event type.
            payload: The webhook payload (unused but kept for consistent interface).

        Returns:
            Dictionary with handling result.
        """
        logger.info(
            "Ignoring unsupported event type",
            extra={"event_type": event_type},
        )

        return {
            "event_type": event_type,
            "status": "ignored",
        }
