"""Comment posting tools for the review agent."""

from typing import Any

from github import Github, GithubException

from app.models.comment import CommentType, ReviewComment
from app.utils.logging import get_logger

logger = get_logger("tools.comments")


class CommentPostError(Exception):
    """Error raised when comment posting fails."""

    pass


def post_review_comment(
    client: Github,
    pr_number: int,
    repository: str,
    body: str,
    file_path: str,
    line: int,
    side: str = "RIGHT",
    commit_id: str | None = None,
) -> dict[str, Any]:
    """Post an inline comment on a specific line in a pull request.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.
        body: Comment text (supports markdown).
        file_path: Path to the file to comment on.
        line: Line number to comment on.
        side: LEFT for removed lines, RIGHT for added lines.
        commit_id: Commit SHA to comment on (defaults to PR head).

    Returns:
        Dictionary with comment info (id, url).

    Raises:
        CommentPostError: If comment cannot be posted.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        # Use PR head if commit_id not specified
        if commit_id is None:
            commit_id = pr.head.sha

        # Create review comment
        comment = pr.create_review_comment(
            body=body,
            commit=repo.get_commit(commit_id),
            path=file_path,
            line=line,
            side=side,
        )

        logger.info(
            "Posted review comment",
            extra={
                "pr_number": pr_number,
                "file_path": file_path,
                "line": line,
                "comment_id": comment.id,
            },
        )

        return {
            "id": comment.id,
            "url": comment.html_url,
        }

    except GithubException as e:
        raise CommentPostError(f"Failed to post review comment: {e}") from e


def post_summary_comment(
    client: Github,
    pr_number: int,
    repository: str,
    body: str,
) -> dict[str, Any]:
    """Post a summary comment on a pull request.

    This posts a regular issue comment (appears in the conversation timeline).

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.
        body: Comment text (supports markdown).

    Returns:
        Dictionary with comment info (id, url).

    Raises:
        CommentPostError: If comment cannot be posted.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        # Post as issue comment (appears in timeline)
        comment = pr.create_issue_comment(body=body)

        logger.info(
            "Posted summary comment",
            extra={
                "pr_number": pr_number,
                "comment_id": comment.id,
            },
        )

        return {
            "id": comment.id,
            "url": comment.html_url,
        }

    except GithubException as e:
        raise CommentPostError(f"Failed to post summary comment: {e}") from e


def create_review(
    client: Github,
    pr_number: int,
    repository: str,
    body: str,
    event: str = "COMMENT",
    comments: list[dict[str, Any]] | None = None,
    commit_id: str | None = None,
) -> dict[str, Any]:
    """Create a PR review with multiple inline comments at once.

    This is more efficient than posting comments individually.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.
        body: Overall review summary.
        event: Review action - always COMMENT for this agent.
        comments: List of inline comments (path, line, side, body).
        commit_id: Commit SHA to review (defaults to PR head).

    Returns:
        Dictionary with review info (id, state, url).

    Raises:
        CommentPostError: If review cannot be created.
    """
    try:
        repo = client.get_repo(repository)
        pr = repo.get_pull(pr_number)

        # Use PR head if commit_id not specified
        if commit_id is None:
            commit_id = pr.head.sha

        # Format comments for GitHub API
        review_comments = []
        if comments:
            for c in comments:
                review_comment = {
                    "path": c["path"],
                    "line": c["line"],
                    "body": c["body"],
                }
                if "side" in c:
                    review_comment["side"] = c["side"]
                review_comments.append(review_comment)

        # Create the review
        # PyGithub accepts dicts for comments but types are declared incorrectly
        review = pr.create_review(
            commit=repo.get_commit(commit_id),
            body=body,
            event=event,
            comments=review_comments,  # type: ignore[arg-type]
        )

        logger.info(
            "Created review",
            extra={
                "pr_number": pr_number,
                "review_id": review.id,
                "comment_count": len(review_comments),
            },
        )

        return {
            "id": review.id,
            "state": review.state,
            "url": review.html_url,
        }

    except GithubException as e:
        raise CommentPostError(f"Failed to create review: {e}") from e


def post_comments(
    client: Github,
    pr_number: int,
    repository: str,
    comments: list[ReviewComment],
    commit_id: str | None = None,
) -> dict[str, Any]:
    """Post multiple review comments efficiently.

    Uses create_review for inline comments and post_summary_comment for summaries.

    Args:
        client: Authenticated GitHub client.
        pr_number: Pull request number.
        repository: Repository in owner/repo format.
        comments: List of ReviewComment objects to post.
        commit_id: Commit SHA to comment on.

    Returns:
        Dictionary with posting results.

    Raises:
        CommentPostError: If posting fails.
    """
    inline_comments = [c for c in comments if c.comment_type == CommentType.INLINE]
    summary_comments = [c for c in comments if c.comment_type == CommentType.SUMMARY]

    results: dict[str, Any] = {
        "inline_posted": 0,
        "summary_posted": 0,
        "errors": [],
    }

    # Post inline comments as a single review
    if inline_comments:
        try:
            review_comments = [c.to_github_review_comment() for c in inline_comments]

            # Build summary from inline comments if no explicit summary
            review_body = "## Code Review Results\n\nSee inline comments below."

            create_review(
                client=client,
                pr_number=pr_number,
                repository=repository,
                body=review_body,
                event="COMMENT",
                comments=review_comments,
                commit_id=commit_id,
            )
            results["inline_posted"] = len(inline_comments)

        except CommentPostError as e:
            results["errors"].append(f"Failed to post inline comments: {e}")

    # Post summary comments
    for comment in summary_comments:
        try:
            post_summary_comment(
                client=client,
                pr_number=pr_number,
                repository=repository,
                body=comment.body,
            )
            results["summary_posted"] += 1

        except CommentPostError as e:
            results["errors"].append(f"Failed to post summary: {e}")

    return results
