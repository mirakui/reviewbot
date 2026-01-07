"""Amazon Bedrock AgentCore Runtime entrypoint for ReviewBot.

This module provides the AgentCore-compatible entrypoint for deploying
ReviewBot as a Bedrock AgentCore agent. It handles:
- AI agent invocations via /invocations endpoint
- GitHub webhook events for PR review automation
- Health checks via /ping endpoint
"""

from __future__ import annotations

import json
import os
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus
from strands import Agent
from strands.models import BedrockModel

from app.agent.prompts import build_system_prompt
from app.agent.reviewer import ReviewAgent, ReviewResult
from app.models.config import AgentConfig
from app.models.file_diff import FileDiff
from app.models.pull_request import PullRequest
from app.tools.github import (
    GitHubToolError,
    create_github_client,
    get_pr_metadata,
    list_pr_files,
)
from app.utils.logging import configure_logging, get_logger
from app.webhook.handler import WebhookHandler, WebhookParseError
from app.webhook.validators import WebhookSignatureError, verify_webhook_signature

# Configure logging
configure_logging()
logger = get_logger("agentcore")

# Create AgentCore application
app = BedrockAgentCoreApp()


def _create_general_agent() -> Agent:
    """Create a general-purpose conversational agent.

    Returns:
        Strands Agent for general queries.
    """
    model = BedrockModel(
        model_id="anthropic.claude-sonnet-4-20250514-v1:0",
        temperature=0.3,
    )
    return Agent(
        model=model,
        system_prompt=build_system_prompt(),
    )


def review_pr(
    repository: str,
    pr_number: int,
    installation_id: int | None = None,
) -> dict[str, Any]:
    """Review a pull request.

    Args:
        repository: Repository in owner/repo format.
        pr_number: Pull request number.
        installation_id: Optional GitHub App installation ID.

    Returns:
        Dictionary containing review results.
    """
    logger.info(
        "Starting PR review",
        extra={
            "repository": repository,
            "pr_number": pr_number,
        },
    )

    try:
        # Create agent config
        config = AgentConfig.default()

        # If we have installation_id, use GitHub API to get PR details
        if installation_id:
            github_client = create_github_client(installation_id)
            pr_metadata = get_pr_metadata(github_client, pr_number, repository)
            pr_files = list_pr_files(github_client, pr_number, repository)

            # Create PullRequest object
            pr = PullRequest(
                number=pr_number,
                title=pr_metadata["title"],
                body=pr_metadata.get("body"),
                author=pr_metadata["author"],
                base_branch=pr_metadata["base_branch"],
                head_branch=pr_metadata["head_branch"],
                head_sha="0" * 40,  # Placeholder - we don't have this from metadata
                repository=repository,
                installation_id=installation_id,
                html_url=f"https://github.com/{repository}/pull/{pr_number}",
                files_changed=pr_metadata.get("files_changed", len(pr_files)),
                additions=pr_metadata.get("additions", 0),
                deletions=pr_metadata.get("deletions", 0),
            )

            # Convert to FileDiff objects
            file_diffs = [FileDiff.from_github_file(f) for f in pr_files]
        else:
            # Create minimal PR object for review without GitHub API
            pr = PullRequest(
                number=pr_number,
                title=f"PR #{pr_number}",
                body=None,
                author="unknown",
                base_branch="main",
                head_branch="feature",
                head_sha="0" * 40,
                repository=repository,
                installation_id=1,  # Placeholder
                html_url=f"https://github.com/{repository}/pull/{pr_number}",
                files_changed=0,
                additions=0,
                deletions=0,
            )
            file_diffs = []

        # Create review agent
        agent = ReviewAgent(config=config)

        # Review each file
        results: list[ReviewResult] = []
        for file_diff in file_diffs:
            result = agent.review_file(pr=pr, file_diff=file_diff)
            results.append(result)

        # Create summary
        summary = agent.create_summary(pr=pr, file_results=results)

        # Compile response
        files_reviewed = [
            {
                "file_path": r.file_path,
                "skipped": r.skipped,
                "skip_reason": r.skip_reason,
                "comment_count": len(r.comments),
            }
            for r in results
        ]

        return {
            "summary": summary,
            "files_reviewed": files_reviewed,
            "total_files": len(file_diffs),
            "files_skipped": sum(1 for r in results if r.skipped),
            "total_comments": sum(len(r.comments) for r in results),
        }

    except GitHubToolError as e:
        logger.error("GitHub API error", extra={"error": str(e)})
        return {
            "error": str(e),
            "summary": f"Failed to review PR: {e}",
            "files_reviewed": [],
            "total_files": 0,
            "files_skipped": 0,
            "total_comments": 0,
        }
    except Exception as e:
        logger.error("Review failed", extra={"error": str(e)})
        return {
            "error": str(e),
            "summary": f"Review failed: {e}",
            "files_reviewed": [],
            "total_files": 0,
            "files_skipped": 0,
            "total_comments": 0,
        }


def review_pr_from_model(pr: PullRequest) -> dict[str, Any]:
    """Review a pull request using a PullRequest model object.

    This is used by the webhook handler when a PR event is received.

    Args:
        pr: The PullRequest model object.

    Returns:
        Dictionary containing review results.
    """
    return review_pr(
        repository=pr.repository,
        pr_number=pr.number,
        installation_id=pr.installation_id,
    )


def handle_webhook(  # noqa: PLR0911
    body: bytes,
    signature: str,
    event_type: str,
    delivery_id: str,
) -> dict[str, Any]:
    """Handle a GitHub webhook request.

    Args:
        body: Raw request body bytes.
        signature: X-Hub-Signature-256 header value.
        event_type: X-GitHub-Event header value.
        delivery_id: X-GitHub-Delivery header value.

    Returns:
        Dictionary containing response data.
    """
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
        return {
            "status_code": 500,
            "error": "configuration_error",
            "message": "Webhook secret not configured",
        }

    # Verify signature
    try:
        verify_webhook_signature(body, signature, webhook_secret)
    except WebhookSignatureError as e:
        logger.warning("Signature verification failed", extra={"error": str(e)})
        return {
            "status_code": 403,
            "error": "invalid_signature",
            "message": str(e),
        }

    # Parse JSON payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning("Invalid JSON payload", extra={"error": str(e)})
        return {
            "status_code": 400,
            "error": "invalid_payload",
            "message": f"Invalid JSON: {e}",
        }

    # Dispatch event
    handler = WebhookHandler()

    try:
        result = handler.dispatch(event_type, payload)
    except WebhookParseError as e:
        logger.warning("Failed to parse webhook", extra={"error": str(e)})
        return {
            "status_code": 400,
            "error": "invalid_payload",
            "message": str(e),
        }

    # Handle based on result
    # Check for parse errors first (applies to PR events with missing fields)
    if result.get("event_type") == "pull_request" and "error" in result:
        return {
            "status_code": 400,
            "error": "invalid_payload",
            "message": result["error"],
        }

    if result.get("should_review") and "pull_request" in result:
        pr = result["pull_request"]

        try:
            review_result = review_pr_from_model(pr)
            return {
                "status_code": 202,
                "status": "queued",
                "message": f"Review queued for PR #{pr.number}",
                "review": review_result,
            }
        except Exception as e:
            logger.error("Failed to trigger review", extra={"error": str(e)})
            return {
                "status_code": 500,
                "error": "internal_error",
                "message": "Failed to queue review",
            }

    elif result.get("event_type") == "ping":
        return {
            "status_code": 200,
            "status": "ok",
            "message": f"Pong! {result.get('zen', '')}",
        }

    elif result.get("event_type") == "installation":
        return {
            "status_code": 200,
            "status": "ok",
            "message": f"Installation event processed: {result.get('action', '')}",
        }

    elif result.get("status") == "ignored":
        return {
            "status_code": 200,
            "status": "ignored",
            "message": f"Event type '{event_type}' not handled",
        }

    else:
        # PR event that doesn't need review (closed, etc.)
        return {
            "status_code": 200,
            "status": "ignored",
            "message": f"Action '{result.get('action', '')}' does not trigger review",
        }


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Main entrypoint for AgentCore invocations.

    This function handles incoming requests to the agent. It supports:
    - General conversational queries (prompt only)
    - PR review requests (with repository and pr_number)
    - GitHub webhook events (with webhook_body, webhook_signature, etc.)

    Args:
        payload: Request payload containing:
            - prompt: The user's message or request
            - repository: (optional) Repository in owner/repo format
            - pr_number: (optional) Pull request number to review
            - installation_id: (optional) GitHub App installation ID
            - webhook_body: (optional) Raw webhook body for webhook handling
            - webhook_signature: (optional) X-Hub-Signature-256 header
            - webhook_event_type: (optional) X-GitHub-Event header
            - webhook_delivery_id: (optional) X-GitHub-Delivery header

    Returns:
        Dictionary containing:
            - result: The agent's response or review summary
            - Additional fields depending on request type
    """
    # Check if this is a webhook request
    webhook_body = payload.get("webhook_body")
    if webhook_body:
        body_bytes = webhook_body.encode() if isinstance(webhook_body, str) else webhook_body
        return handle_webhook(
            body=body_bytes,
            signature=payload.get("webhook_signature", ""),
            event_type=payload.get("webhook_event_type", ""),
            delivery_id=payload.get("webhook_delivery_id", ""),
        )

    prompt = payload.get("prompt", "Hello! How can I help you with code review?")
    repository = payload.get("repository")
    pr_number = payload.get("pr_number")
    installation_id = payload.get("installation_id")

    logger.info(
        "Received invocation",
        extra={
            "has_prompt": bool(prompt),
            "has_repository": bool(repository),
            "has_pr_number": bool(pr_number),
        },
    )

    try:
        # If repository and pr_number provided, do a PR review
        if repository and pr_number:
            review_result = review_pr(
                repository=repository,
                pr_number=pr_number,
                installation_id=installation_id,
            )
            return {
                "result": review_result.get("summary", "Review completed"),
                **review_result,
            }

        # Otherwise, handle as a general query
        agent = _create_general_agent()
        response = agent(prompt)
        response_text = str(response.message) if hasattr(response, "message") else str(response)

        return {"result": response_text}

    except Exception as e:
        logger.error("Invocation failed", extra={"error": str(e)})
        return {
            "error": str(e),
            "result": f"An error occurred: {e}",
        }


@app.ping
def ping() -> PingStatus:
    """Health check endpoint for AgentCore Runtime.

    Returns:
        PingStatus indicating the agent's health.
    """
    return PingStatus.HEALTHY


# For local development and testing
if __name__ == "__main__":
    app.run()
