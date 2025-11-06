"""Configuration management for Hephaestus-CLI.

This module handles loading, validating, and accessing configuration
from the config.yaml file in the hephaestus-work directory.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for an agent (Master or Worker)."""

    enabled: bool = True
    command: str = "claude --dangerously-skip-permissions"
    args: list = field(default_factory=list)


@dataclass
class WorkersConfig:
    """Configuration for Worker agents."""

    count: int = 3
    command: str = "claude --dangerously-skip-permissions"
    args: list = field(default_factory=list)


@dataclass
class MonitoringConfig:
    """Configuration for agent monitoring."""

    health_check_interval: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5


@dataclass
class CommunicationConfig:
    """Configuration for inter-agent communication."""

    format: str = "markdown"
    encoding: str = "utf-8"


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class TmuxConfig:
    """Configuration for tmux session."""

    session_name: str = "hephaestus"
    layout: str = "tiled"


@dataclass
class Config:
    """Main configuration class for Hephaestus-CLI."""

    version: str = "1.0"
    master: AgentConfig = field(default_factory=AgentConfig)
    workers: WorkersConfig = field(default_factory=WorkersConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    communication: CommunicationConfig = field(default_factory=CommunicationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    tmux: TmuxConfig = field(default_factory=TmuxConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config instance from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        agents = data.get("agents", {})
        master_data = agents.get("master", {})
        workers_data = agents.get("workers", {})

        return cls(
            version=data.get("version", "1.0"),
            master=AgentConfig(**master_data),
            workers=WorkersConfig(**workers_data),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
            communication=CommunicationConfig(**data.get("communication", {})),
            logging=LoggingConfig(**data.get("logging", {})),
            tmux=TmuxConfig(**data.get("tmux", {})),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config instance to dictionary.

        Returns:
            Configuration dictionary
        """
        return {
            "version": self.version,
            "agents": {
                "master": {
                    "enabled": self.master.enabled,
                    "command": self.master.command,
                    "args": self.master.args,
                },
                "workers": {
                    "count": self.workers.count,
                    "command": self.workers.command,
                    "args": self.workers.args,
                },
            },
            "monitoring": {
                "health_check_interval": self.monitoring.health_check_interval,
                "retry_attempts": self.monitoring.retry_attempts,
                "retry_delay": self.monitoring.retry_delay,
            },
            "communication": {
                "format": self.communication.format,
                "encoding": self.communication.encoding,
            },
            "logging": {
                "level": self.logging.level,
                "format": self.logging.format,
            },
            "tmux": {
                "session_name": self.tmux.session_name,
                "layout": self.tmux.layout,
            },
        }


class ConfigManager:
    """Manager for loading and saving configuration."""

    def __init__(self, config_path: Path):
        """Initialize ConfigManager.

        Args:
            config_path: Path to config.yaml file
        """
        self.config_path = config_path
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self._config = Config.from_dict(data)
        logger.info(f"Loaded configuration from {self.config_path}")
        return self._config

    def save(self, config: Config) -> None:
        """Save configuration to file.

        Args:
            config: Config instance to save
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)

        self._config = config
        logger.info(f"Saved configuration to {self.config_path}")

    def get(self) -> Config:
        """Get current configuration.

        Returns:
            Config instance

        Raises:
            RuntimeError: If configuration hasn't been loaded
        """
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config

    def reload(self) -> Config:
        """Reload configuration from file.

        Returns:
            Updated Config instance
        """
        return self.load()


def create_default_config(config_path: Path) -> Config:
    """Create a default configuration file.

    Args:
        config_path: Path where config.yaml should be created

    Returns:
        Default Config instance
    """
    config = Config()
    manager = ConfigManager(config_path)
    manager.save(config)
    logger.info(f"Created default configuration at {config_path}")
    return config
