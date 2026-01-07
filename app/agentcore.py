"""Amazon Bedrock AgentCore Runtime entrypoint for ReviewBot.

This module provides the AgentCore-compatible entrypoint for deploying
ReviewBot as a Bedrock AgentCore agent.
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands import Agent
from strands.models import BedrockModel

from app import __version__
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


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """Main entrypoint for AgentCore invocations.

    This function handles incoming requests to the agent. It supports:
    - General conversational queries (prompt only)
    - PR review requests (with repository and pr_number)

    Args:
        payload: Request payload containing:
            - prompt: The user's message or request
            - repository: (optional) Repository in owner/repo format
            - pr_number: (optional) Pull request number to review
            - installation_id: (optional) GitHub App installation ID

    Returns:
        Dictionary containing:
            - result: The agent's response or review summary
            - Additional fields depending on request type
    """
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
def ping() -> dict[str, Any]:
    """Health check endpoint for AgentCore Runtime.

    Returns:
        Dictionary with health status and version.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "agent": "reviewbot",
    }


# For local development and testing
if __name__ == "__main__":
    app.run()
