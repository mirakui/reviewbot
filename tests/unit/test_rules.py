"""Unit tests for custom review rules."""

import tempfile
from pathlib import Path

import pytest

from app.models.rule import ReviewRule
from app.rules.loader import RuleLoader


class TestReviewRule:
    """Tests for ReviewRule model."""

    def test_create_rule(self) -> None:
        """Test creating a review rule."""
        rule = ReviewRule(
            source_file="docstrings.md",
            content="All functions must have docstrings.",
            priority=0,
        )

        assert rule.source_file == "docstrings.md"
        assert rule.content == "All functions must have docstrings."
        assert rule.priority == 0

    def test_rule_requires_md_extension(self) -> None:
        """Test that source_file must end with .md."""
        with pytest.raises(ValueError, match=r"\.md"):
            ReviewRule(
                source_file="rules.txt",
                content="Some content",
                priority=0,
            )

    def test_rule_requires_non_empty_content(self) -> None:
        """Test that content cannot be empty."""
        with pytest.raises(ValueError, match="empty"):
            ReviewRule(
                source_file="rules.md",
                content="",
                priority=0,
            )

    def test_rule_requires_non_negative_priority(self) -> None:
        """Test that priority must be non-negative."""
        with pytest.raises(ValueError, match="priority"):
            ReviewRule(
                source_file="rules.md",
                content="Content",
                priority=-1,
            )


class TestRuleLoader:
    """Tests for RuleLoader."""

    def test_load_from_directory(self) -> None:
        """Test loading rules from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / ".claude" / "rules"
            rules_dir.mkdir(parents=True)

            # Create rule files
            (rules_dir / "01-docstrings.md").write_text(
                "# Docstring Rules\nAll functions must have docstrings."
            )
            (rules_dir / "02-typing.md").write_text(
                "# Type Hints\nAll functions must have type hints."
            )

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)

            assert len(rules) == 2
            # Rules should be sorted alphabetically
            assert rules[0].source_file == "01-docstrings.md"
            assert rules[1].source_file == "02-typing.md"
            assert rules[0].priority == 0
            assert rules[1].priority == 1

    def test_load_from_missing_directory(self) -> None:
        """Test loading from non-existent directory returns empty list."""
        loader = RuleLoader()
        rules = loader.load_from_directory(Path("/nonexistent/path"))

        assert rules == []

    def test_load_from_empty_directory(self) -> None:
        """Test loading from empty directory returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir) / "rules"
            rules_dir.mkdir()

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)

            assert rules == []

    def test_ignores_non_md_files(self) -> None:
        """Test that non-markdown files are ignored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir)

            (rules_dir / "valid.md").write_text("Valid rule")
            (rules_dir / "invalid.txt").write_text("Not a rule")
            (rules_dir / "also-invalid.json").write_text("{}")

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)

            assert len(rules) == 1
            assert rules[0].source_file == "valid.md"

    def test_alphabetical_merge(self) -> None:
        """Test that rules are merged in alphabetical order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir)

            # Create files in non-alphabetical order
            (rules_dir / "c-third.md").write_text("Third")
            (rules_dir / "a-first.md").write_text("First")
            (rules_dir / "b-second.md").write_text("Second")

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)

            assert len(rules) == 3
            assert rules[0].source_file == "a-first.md"
            assert rules[1].source_file == "b-second.md"
            assert rules[2].source_file == "c-third.md"

    def test_merge_rules_content(self) -> None:
        """Test merging all rules into a single string."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir)

            (rules_dir / "01-first.md").write_text("First rule")
            (rules_dir / "02-second.md").write_text("Second rule")

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)
            merged = loader.merge_rules(rules)

            assert "First rule" in merged
            assert "Second rule" in merged
            # Should have separators between rules
            assert "---" in merged or "\n\n" in merged

    def test_load_and_merge(self) -> None:
        """Test loading and merging in one step."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir)

            (rules_dir / "rules.md").write_text("My custom rules")

            loader = RuleLoader()
            merged = loader.load_and_merge(rules_dir)

            assert "My custom rules" in merged

    def test_load_and_merge_returns_empty_for_missing_dir(self) -> None:
        """Test load_and_merge returns empty string for missing directory."""
        loader = RuleLoader()
        merged = loader.load_and_merge(Path("/nonexistent"))

        assert merged == ""

    def test_handles_unreadable_files(self) -> None:
        """Test that unreadable files log warning and are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rules_dir = Path(tmpdir)

            valid_file = rules_dir / "valid.md"
            valid_file.write_text("Valid content")

            # Create a directory with .md extension (will fail to read)
            invalid_dir = rules_dir / "invalid.md"
            invalid_dir.mkdir()

            loader = RuleLoader()
            rules = loader.load_from_directory(rules_dir)

            # Should only load the valid file
            assert len(rules) == 1
            assert rules[0].source_file == "valid.md"
