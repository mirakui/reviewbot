"""Unit tests for configuration."""

import tempfile
from pathlib import Path

import pytest

from app.models.config import SUPPORTED_MODELS, AgentConfig
from app.utils.config_loader import ConfigLoaderError, load_repo_config


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_default_config(self) -> None:
        """Test creating default configuration."""
        config = AgentConfig.default()

        assert config.model_id == "anthropic.claude-sonnet-4-20250514-v1:0"
        assert config.timeout_seconds == 600
        assert config.temperature == 0.3
        assert config.enable_rereview is True

    def test_custom_config(self) -> None:
        """Test creating custom configuration."""
        config = AgentConfig(
            model_id="anthropic.claude-haiku-4-20251015-v1:0",
            timeout_seconds=300,
            temperature=0.5,
            max_files=10,
            enable_rereview=False,
        )

        assert config.model_id == "anthropic.claude-haiku-4-20251015-v1:0"
        assert config.timeout_seconds == 300
        assert config.temperature == 0.5
        assert config.max_files == 10
        assert config.enable_rereview is False

    def test_all_supported_models_valid(self) -> None:
        """Test that all supported models can be used."""
        for model_id in SUPPORTED_MODELS:
            config = AgentConfig(model_id=model_id)
            assert config.model_id == model_id

    def test_invalid_model_raises_error(self) -> None:
        """Test that invalid model ID raises error."""
        with pytest.raises(ValueError, match="Unsupported model"):
            AgentConfig(model_id="invalid-model-id")

    def test_timeout_validation(self) -> None:
        """Test timeout validation."""
        # Too low
        with pytest.raises(ValueError, match="timeout"):
            AgentConfig(timeout_seconds=30)

        # Too high
        with pytest.raises(ValueError, match="timeout"):
            AgentConfig(timeout_seconds=1000)

        # Valid boundaries
        config_low = AgentConfig(timeout_seconds=60)
        assert config_low.timeout_seconds == 60

        config_high = AgentConfig(timeout_seconds=900)
        assert config_high.timeout_seconds == 900

    def test_temperature_validation(self) -> None:
        """Test temperature validation."""
        # Too low
        with pytest.raises(ValueError, match="temperature"):
            AgentConfig(temperature=-0.1)

        # Too high
        with pytest.raises(ValueError, match="temperature"):
            AgentConfig(temperature=1.5)

        # Valid boundaries
        config_low = AgentConfig(temperature=0.0)
        assert config_low.temperature == 0.0

        config_high = AgentConfig(temperature=1.0)
        assert config_high.temperature == 1.0

    def test_from_repo_config(self) -> None:
        """Test creating config from repository config dict."""
        repo_config = {
            "model": "amazon.nova-pro-v1:0",
            "timeout": 300,
            "temperature": 0.7,
            "max_files": 20,
            "enable_rereview": False,
        }

        config = AgentConfig.from_repo_config(repo_config)

        assert config.model_id == "amazon.nova-pro-v1:0"
        assert config.timeout_seconds == 300
        assert config.temperature == 0.7
        assert config.max_files == 20
        assert config.enable_rereview is False

    def test_from_repo_config_with_defaults(self) -> None:
        """Test that missing values use defaults."""
        repo_config = {"model": "amazon.nova-lite-v1:0"}

        config = AgentConfig.from_repo_config(repo_config)

        assert config.model_id == "amazon.nova-lite-v1:0"
        assert config.timeout_seconds == 600  # default
        assert config.temperature == 0.3  # default

    def test_excluded_patterns_default(self) -> None:
        """Test default excluded patterns."""
        config = AgentConfig.default()

        assert "*.lock" in config.excluded_patterns
        assert "node_modules/**" in config.excluded_patterns

    def test_custom_excluded_patterns(self) -> None:
        """Test custom excluded patterns."""
        custom_patterns = ["*.test.js", "coverage/**"]
        config = AgentConfig(excluded_patterns=custom_patterns)

        assert config.excluded_patterns == custom_patterns


class TestLoadRepoConfig:
    """Tests for repository configuration loading."""

    def test_load_yaml_config(self) -> None:
        """Test loading .reviewbot.yml config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".reviewbot.yml"
            config_file.write_text(
                """\
model: amazon.nova-pro-v1:0
timeout: 300
temperature: 0.5
enable_rereview: false
"""
            )

            config = load_repo_config(Path(tmpdir))

            assert config.model_id == "amazon.nova-pro-v1:0"
            assert config.timeout_seconds == 300
            assert config.temperature == 0.5
            assert config.enable_rereview is False

    def test_load_yaml_config_alternative_name(self) -> None:
        """Test loading .reviewbot.yaml config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".reviewbot.yaml"
            config_file.write_text("model: amazon.nova-lite-v1:0\n")

            config = load_repo_config(Path(tmpdir))

            assert config.model_id == "amazon.nova-lite-v1:0"

    def test_missing_config_returns_default(self) -> None:
        """Test that missing config returns default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_repo_config(Path(tmpdir))

            assert config.model_id == "anthropic.claude-sonnet-4-20250514-v1:0"

    def test_empty_config_returns_default(self) -> None:
        """Test that empty config returns default configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".reviewbot.yml"
            config_file.write_text("")

            config = load_repo_config(Path(tmpdir))

            assert config.model_id == "anthropic.claude-sonnet-4-20250514-v1:0"

    def test_invalid_yaml_raises_error(self) -> None:
        """Test that invalid YAML raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".reviewbot.yml"
            config_file.write_text("invalid: yaml: content: :")

            with pytest.raises(ConfigLoaderError, match="parse"):
                load_repo_config(Path(tmpdir))

    def test_invalid_model_in_config_raises_error(self) -> None:
        """Test that invalid model ID in config raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / ".reviewbot.yml"
            config_file.write_text("model: invalid-model\n")

            with pytest.raises(ConfigLoaderError, match="model"):
                load_repo_config(Path(tmpdir))

    def test_yml_takes_precedence_over_yaml(self) -> None:
        """Test that .yml is preferred over .yaml when both exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yml_file = Path(tmpdir) / ".reviewbot.yml"
            yml_file.write_text("model: amazon.nova-pro-v1:0\n")

            yaml_file = Path(tmpdir) / ".reviewbot.yaml"
            yaml_file.write_text("model: amazon.nova-lite-v1:0\n")

            config = load_repo_config(Path(tmpdir))

            # .yml should take precedence
            assert config.model_id == "amazon.nova-pro-v1:0"
