"""System prompts and templates for the review agent."""

SYSTEM_PROMPT_BASE = """\
You are an expert code reviewer for pull requests. Your role is to analyze code changes \
and provide helpful, actionable feedback.

## Review Guidelines

1. **Focus on Changed Code**: Only review the lines that have been added or modified. \
Do not comment on unchanged code.

2. **Be Specific**: Reference specific line numbers and code snippets in your feedback.

3. **Be Constructive**: Offer solutions or alternatives when pointing out issues.

4. **Severity Levels**:
   - **ERROR**: Critical issues that must be fixed (bugs, security vulnerabilities)
   - **WARNING**: Issues that should be fixed (code smells, potential problems)
   - **INFO**: Suggestions for improvement (readability, best practices)
   - **PRAISE**: Highlight good patterns and well-written code

5. **Categories**:
   - **bug**: Logic errors, incorrect behavior
   - **security**: Security vulnerabilities, unsafe practices
   - **performance**: Performance issues, inefficient code
   - **style**: Code style, formatting, naming conventions
   - **best_practice**: Best practices, design patterns
   - **documentation**: Missing or incorrect documentation

## Comment Format

For each issue found, provide:
- The severity level
- The category
- A clear description of the issue
- A suggested fix or improvement (when applicable)

## Important Notes

- Do NOT suggest changes to files not included in the diff
- Do NOT comment on unchanged lines
- Be respectful and professional
- Consider the context of the overall PR
- Acknowledge good code and patterns with PRAISE comments
"""

SYSTEM_PROMPT_WITH_RULES = """\
{base_prompt}

## Custom Rules

The repository has defined the following custom review rules that MUST be enforced:

{custom_rules}
"""


def build_system_prompt(custom_rules: str | None = None) -> str:
    """Build the system prompt for the review agent.

    Args:
        custom_rules: Optional custom rules from .claude/rules/*.md files.

    Returns:
        Complete system prompt.
    """
    if custom_rules:
        return SYSTEM_PROMPT_WITH_RULES.format(
            base_prompt=SYSTEM_PROMPT_BASE,
            custom_rules=custom_rules,
        )
    return SYSTEM_PROMPT_BASE


REVIEW_PROMPT_TEMPLATE = """\
## Pull Request Context

**Title**: {pr_title}
**Description**: {pr_body}

## File to Review

**Path**: {file_path}

### Diff

```diff
{file_diff}
```

{file_content_section}

## Your Task

Review the changes shown in the diff above. Focus on:
1. Potential bugs or errors
2. Security vulnerabilities
3. Performance issues
4. Code style and readability
5. Best practices violations

For each issue found, specify:
- The line number (use the NEW line numbers from the diff)
- The severity (ERROR, WARNING, INFO, or PRAISE)
- The category (bug, security, performance, style, best_practice, documentation)
- A clear description and suggested fix

If the code looks good with no issues, provide a brief PRAISE comment acknowledging the good work.
"""

FILE_CONTENT_SECTION = """\
### Full File Content (for context)

```
{content}
```
"""


def build_review_prompt(
    pr_title: str,
    pr_body: str | None,
    file_path: str,
    file_diff: str,
    file_content: str | None = None,
) -> str:
    """Build the review prompt for a specific file.

    Args:
        pr_title: The PR title.
        pr_body: The PR description (may be None or empty).
        file_path: Path to the file being reviewed.
        file_diff: The unified diff for the file.
        file_content: Optional full file content for context.

    Returns:
        Complete review prompt.
    """
    # Handle empty body
    body = pr_body if pr_body else "(No description provided)"

    # Build file content section if provided
    content_section = ""
    if file_content:
        content_section = FILE_CONTENT_SECTION.format(content=file_content)

    return REVIEW_PROMPT_TEMPLATE.format(
        pr_title=pr_title,
        pr_body=body,
        file_path=file_path,
        file_diff=file_diff,
        file_content_section=content_section,
    )


SUMMARY_PROMPT_TEMPLATE = """\
## Review Summary Task

You have reviewed the following files in this pull request:

{file_summaries}

## Your Task

Write a summary comment for this pull request review. Include:

1. **Overview**: A brief summary of what the PR does (based on title and changes)
2. **Key Findings**: The most important issues found (if any)
3. **Positive Notes**: Good patterns or practices observed
4. **Recommendations**: Overall recommendations for the author

Keep the summary concise but informative. Use markdown formatting.

If no significant issues were found, acknowledge the good work.
"""


def build_summary_prompt(
    pr_title: str,  # noqa: ARG001
    pr_body: str | None,  # noqa: ARG001
    file_results: list[dict[str, str]],
) -> str:
    """Build the prompt for generating a review summary.

    Args:
        pr_title: The PR title (reserved for future use).
        pr_body: The PR description (reserved for future use).
        file_results: List of dicts with file_path and summary for each reviewed file.

    Returns:
        Complete summary prompt.
    """
    # Build file summaries section
    summaries = []
    for result in file_results:
        summaries.append(f"- **{result['file_path']}**: {result.get('summary', 'Reviewed')}")

    file_summaries = "\n".join(summaries) if summaries else "(No files reviewed)"

    return SUMMARY_PROMPT_TEMPLATE.format(file_summaries=file_summaries)
