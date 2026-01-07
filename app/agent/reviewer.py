"""Main review agent implementation using Strands SDK."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from strands import Agent
from strands.models import BedrockModel

from app.agent.prompts import build_review_prompt, build_summary_prompt, build_system_prompt
from app.models.comment import Category, CommentType, ReviewComment, Severity
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from app.models.config import AgentConfig
    from app.models.file_diff import FileDiff
    from app.models.pull_request import PullRequest

logger = get_logger("agent.reviewer")


@dataclass
class ReviewResult:
    """Result of reviewing a single file."""

    file_path: str
    comments: list[ReviewComment] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None
    summary: str | None = None


class ReviewAgent:
    """AI agent for reviewing pull request code changes."""

    def __init__(
        self,
        config: AgentConfig,
        custom_rules: str | None = None,
    ) -> None:
        """Initialize the review agent.

        Args:
            config: Agent configuration.
            custom_rules: Optional custom rules from repository.
        """
        self.config = config
        self.custom_rules = custom_rules

        # Build system prompt
        self.system_prompt = build_system_prompt(custom_rules)

        # Create Bedrock model
        self.model = BedrockModel(
            model_id=config.model_id,
            temperature=config.temperature,
        )

        # Create Strands agent
        self.agent = Agent(
            model=self.model,
            system_prompt=self.system_prompt,
        )

        logger.info(
            "ReviewAgent initialized",
            extra={
                "model_id": config.model_id,
                "has_custom_rules": custom_rules is not None,
            },
        )

    def _should_skip_file(self, file_diff: FileDiff) -> tuple[bool, str | None]:
        """Check if a file should be skipped.

        Args:
            file_diff: The file diff to check.

        Returns:
            Tuple of (should_skip, reason).
        """
        # Skip binary files
        if file_diff.is_binary:
            return True, "Binary file"

        # Skip files matching exclusion patterns
        for pattern in self.config.excluded_patterns:
            if fnmatch.fnmatch(file_diff.filename, pattern):
                return True, f"Matches exclusion pattern: {pattern}"

        return False, None

    def review_file(
        self,
        pr: PullRequest,
        file_diff: FileDiff,
        file_content: str | None = None,
    ) -> ReviewResult:
        """Review a single file.

        Args:
            pr: The pull request being reviewed.
            file_diff: The file diff to review.
            file_content: Optional full file content for context.

        Returns:
            ReviewResult with comments.
        """
        # Check if file should be skipped
        should_skip, skip_reason = self._should_skip_file(file_diff)
        if should_skip:
            logger.info(
                "Skipping file",
                extra={
                    "file_path": file_diff.filename,
                    "reason": skip_reason,
                },
            )
            return ReviewResult(
                file_path=file_diff.filename,
                skipped=True,
                skip_reason=skip_reason,
            )

        # Build review prompt
        prompt = build_review_prompt(
            pr_title=pr.title,
            pr_body=pr.body,
            file_path=file_diff.filename,
            file_diff=file_diff.patch or "",
            file_content=file_content,
        )

        logger.info(
            "Reviewing file",
            extra={
                "file_path": file_diff.filename,
                "additions": file_diff.additions,
                "deletions": file_diff.deletions,
            },
        )

        try:
            # Call the agent
            response = self.agent(prompt)
            response_text = str(response.message) if hasattr(response, "message") else str(response)

            # Parse response into comments
            comments = self._parse_review_response(response_text, file_diff.filename)

            return ReviewResult(
                file_path=file_diff.filename,
                comments=comments,
                summary=response_text[:200] if response_text else None,
            )

        except Exception as e:
            logger.error(
                "Failed to review file",
                extra={
                    "file_path": file_diff.filename,
                    "error": str(e),
                },
            )
            return ReviewResult(
                file_path=file_diff.filename,
                skipped=True,
                skip_reason=f"Review failed: {e}",
            )

    def _parse_review_response(
        self,
        response: str,
        file_path: str,  # noqa: ARG002
    ) -> list[ReviewComment]:
        """Parse agent response into structured comments.

        This is a simplified parser. A production implementation would use
        structured output from the LLM or more sophisticated parsing.

        Args:
            response: The agent's response text.
            file_path: The file being reviewed (reserved for future use).

        Returns:
            List of ReviewComment objects.
        """
        comments: list[ReviewComment] = []

        # For now, create a single summary comment with the full response
        # A more sophisticated implementation would parse structured output
        if response.strip():
            # Try to determine severity from response
            severity = Severity.INFO
            if "error" in response.lower() or "bug" in response.lower():
                severity = Severity.WARNING
            if "critical" in response.lower() or "security" in response.lower():
                severity = Severity.ERROR
            if "good" in response.lower() or "well done" in response.lower():
                severity = Severity.PRAISE

            # Determine category
            category = Category.BEST_PRACTICE
            if "security" in response.lower():
                category = Category.SECURITY
            elif "performance" in response.lower():
                category = Category.PERFORMANCE
            elif "bug" in response.lower():
                category = Category.BUG
            elif "style" in response.lower():
                category = Category.STYLE

            comments.append(
                ReviewComment(
                    body=response,
                    comment_type=CommentType.SUMMARY,
                    severity=severity,
                    category=category,
                )
            )

        return comments

    def create_summary(
        self,
        pr: PullRequest,
        file_results: list[ReviewResult],
    ) -> str:
        """Create an overall review summary.

        Args:
            pr: The pull request.
            file_results: Results from reviewing individual files.

        Returns:
            Summary text.
        """
        # Build file summaries
        summaries = []
        for result in file_results:
            if result.skipped:
                summaries.append(
                    {
                        "file_path": result.file_path,
                        "summary": f"Skipped: {result.skip_reason}",
                    }
                )
            else:
                comment_count = len(result.comments)
                summaries.append(
                    {
                        "file_path": result.file_path,
                        "summary": f"{comment_count} comment(s)",
                    }
                )

        prompt = build_summary_prompt(
            pr_title=pr.title,
            pr_body=pr.body,
            file_results=summaries,
        )

        try:
            response = self.agent(prompt)
            return str(response.message) if hasattr(response, "message") else str(response)
        except Exception as e:
            logger.error("Failed to create summary", extra={"error": str(e)})
            return f"Review completed for {len(file_results)} files."
