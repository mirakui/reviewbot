"""Custom rules loader from .claude/rules/*.md files."""

from pathlib import Path  # noqa: TC003

from app.models.rule import ReviewRule
from app.utils.logging import get_logger

logger = get_logger("rules.loader")


class RuleLoaderError(Exception):
    """Error raised when rule loading fails."""

    pass


class RuleLoader:
    """Loads custom review rules from a directory."""

    def load_from_directory(self, rules_dir: Path) -> list[ReviewRule]:
        """Load all rules from a directory, sorted alphabetically.

        Args:
            rules_dir: Path to the rules directory.

        Returns:
            List of ReviewRule objects sorted by filename.
        """
        if not rules_dir.exists():
            logger.debug("Rules directory does not exist", extra={"path": str(rules_dir)})
            return []

        if not rules_dir.is_dir():
            logger.warning(
                "Rules path is not a directory",
                extra={"path": str(rules_dir)},
            )
            return []

        rules: list[ReviewRule] = []
        files = sorted(rules_dir.glob("*.md"))

        for idx, filepath in enumerate(files):
            try:
                if not filepath.is_file():
                    logger.warning(
                        "Skipping non-file entry",
                        extra={"path": str(filepath)},
                    )
                    continue

                content = filepath.read_text(encoding="utf-8")

                if not content.strip():
                    logger.warning(
                        "Skipping empty rule file",
                        extra={"path": str(filepath)},
                    )
                    continue

                rule = ReviewRule(
                    source_file=filepath.name,
                    content=content,
                    priority=idx,
                )
                rules.append(rule)

                logger.debug(
                    "Loaded rule",
                    extra={
                        "file": filepath.name,
                        "priority": idx,
                        "content_length": len(content),
                    },
                )

            except OSError as e:
                logger.warning(
                    "Failed to read rule file",
                    extra={"path": str(filepath), "error": str(e)},
                )
            except ValueError as e:
                logger.warning(
                    "Invalid rule file",
                    extra={"path": str(filepath), "error": str(e)},
                )

        logger.info(
            "Loaded rules",
            extra={
                "directory": str(rules_dir),
                "rule_count": len(rules),
            },
        )

        return rules

    def merge_rules(self, rules: list[ReviewRule]) -> str:
        """Merge multiple rules into a single string.

        Args:
            rules: List of ReviewRule objects.

        Returns:
            Merged content with separators between rules.
        """
        if not rules:
            return ""

        sections = []
        for rule in sorted(rules, key=lambda r: r.priority):
            sections.append(f"### {rule.title}\n\n{rule.content}")

        return "\n\n---\n\n".join(sections)

    def load_and_merge(self, rules_dir: Path) -> str:
        """Load rules from a directory and merge them.

        Convenience method combining load_from_directory and merge_rules.

        Args:
            rules_dir: Path to the rules directory.

        Returns:
            Merged rules content, or empty string if no rules found.
        """
        rules = self.load_from_directory(rules_dir)
        return self.merge_rules(rules)


def load_rules_from_repo(
    repository_root: Path,
    rules_path: str = ".claude/rules",
) -> str:
    """Load custom rules from a repository.

    Args:
        repository_root: Root path of the repository.
        rules_path: Relative path to rules directory.

    Returns:
        Merged rules content, or empty string if no rules found.
    """
    rules_dir = repository_root / rules_path
    loader = RuleLoader()
    return loader.load_and_merge(rules_dir)
