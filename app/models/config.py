"""Configuration models for reviewbot."""

from dataclasses import dataclass, field
from typing import Any

# Supported Bedrock model IDs
SUPPORTED_MODELS = {
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-haiku-4-20251015-v1:0",
    "amazon.nova-pro-v1:0",
    "amazon.nova-lite-v1:0",
}

# Default patterns to exclude from review
DEFAULT_EXCLUDED = [
    "*.lock",
    "*.min.js",
    "*.min.css",
    "vendor/**",
    "node_modules/**",
    "dist/**",
    "build/**",
]


@dataclass
class Installation:
    """Represents a GitHub App installation."""

    id: int
    account_login: str | None = None
    account_type: str | None = None  # "User" or "Organization"
    repositories: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if self.id <= 0:
            raise ValueError(f"Installation ID must be positive, got {self.id}")

    @classmethod
    def from_webhook_payload(cls, payload: dict[str, Any]) -> Installation:
        """Create an Installation from a webhook payload.

        Args:
            payload: The webhook payload containing installation data.

        Returns:
            Installation instance.
        """
        installation = payload.get("installation", {})
        account = installation.get("account", {})
        repositories = payload.get("repositories", [])

        return cls(
            id=installation["id"],
            account_login=account.get("login"),
            account_type=account.get("type"),
            repositories=[r.get("full_name", "") for r in repositories if r],
        )


@dataclass
class AgentConfig:
    """Configuration for the review agent."""

    model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0"
    timeout_seconds: int = 600
    temperature: float = 0.3
    max_files: int | None = None
    enable_rereview: bool = True
    rules_path: str = ".claude/rules"
    excluded_patterns: list[str] = field(default_factory=lambda: DEFAULT_EXCLUDED.copy())

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.model_id not in SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {self.model_id}. "
                f"Supported models: {', '.join(sorted(SUPPORTED_MODELS))}"
            )

        if not 60 <= self.timeout_seconds <= 900:
            raise ValueError(
                f"timeout_seconds must be between 60 and 900, got {self.timeout_seconds}"
            )

        if not 0.0 <= self.temperature <= 1.0:
            raise ValueError(f"temperature must be between 0.0 and 1.0, got {self.temperature}")

    @classmethod
    def from_repo_config(cls, config: dict[str, Any]) -> AgentConfig:
        """Load configuration from repository config file.

        Args:
            config: Configuration dictionary (e.g., from .reviewbot.yml).

        Returns:
            AgentConfig instance.
        """
        return cls(
            model_id=config.get("model", cls.model_id),
            timeout_seconds=config.get("timeout", cls.timeout_seconds),
            temperature=config.get("temperature", cls.temperature),
            max_files=config.get("max_files"),
            enable_rereview=config.get("enable_rereview", cls.enable_rereview),
            rules_path=config.get("rules_path", cls.rules_path),
            excluded_patterns=config.get("excluded_patterns", DEFAULT_EXCLUDED.copy()),
        )

    @classmethod
    def default(cls) -> AgentConfig:
        """Create a default configuration."""
        return cls()
