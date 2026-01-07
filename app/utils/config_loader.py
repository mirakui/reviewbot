"""Repository configuration loader."""

from pathlib import Path  # noqa: TC003
from typing import Any

import yaml

from app.models.config import AgentConfig
from app.utils.logging import get_logger

logger = get_logger("utils.config_loader")


class ConfigLoaderError(Exception):
    """Error raised when configuration loading fails."""

    pass


# Config file names in order of precedence
CONFIG_FILE_NAMES = [
    ".reviewbot.yml",
    ".reviewbot.yaml",
]


def load_repo_config(repo_root: Path) -> AgentConfig:
    """Load configuration from a repository.

    Looks for configuration in the following order:
    1. .reviewbot.yml
    2. .reviewbot.yaml

    If no config file is found, returns default configuration.

    Args:
        repo_root: Root path of the repository.

    Returns:
        AgentConfig instance.

    Raises:
        ConfigLoaderError: If config file exists but is invalid.
    """
    config_file = _find_config_file(repo_root)

    if config_file is None:
        logger.debug("No config file found, using defaults", extra={"path": str(repo_root)})
        return AgentConfig.default()

    try:
        raw_config = _load_yaml_file(config_file)
    except yaml.YAMLError as e:
        raise ConfigLoaderError(f"Failed to parse config file {config_file}: {e}") from e

    if not raw_config:
        logger.debug("Config file is empty, using defaults", extra={"file": str(config_file)})
        return AgentConfig.default()

    try:
        config = AgentConfig.from_repo_config(raw_config)
        logger.info(
            "Loaded configuration",
            extra={
                "file": str(config_file),
                "model_id": config.model_id,
            },
        )
        return config
    except ValueError as e:
        raise ConfigLoaderError(f"Invalid configuration in {config_file}: {e}") from e


def _find_config_file(repo_root: Path) -> Path | None:
    """Find the configuration file in a repository.

    Args:
        repo_root: Root path of the repository.

    Returns:
        Path to config file, or None if not found.
    """
    for filename in CONFIG_FILE_NAMES:
        config_path = repo_root / filename
        if config_path.exists() and config_path.is_file():
            return config_path

    return None


def _load_yaml_file(filepath: Path) -> dict[str, Any] | None:
    """Load a YAML file.

    Args:
        filepath: Path to the YAML file.

    Returns:
        Parsed YAML content, or None if empty.

    Raises:
        yaml.YAMLError: If YAML is invalid.
        OSError: If file cannot be read.
    """
    content = filepath.read_text(encoding="utf-8")

    if not content.strip():
        return None

    result: dict[str, Any] | None = yaml.safe_load(content)
    return result
