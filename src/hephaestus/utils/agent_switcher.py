"""Utilities for switching agent configurations at runtime."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from ..config import Config, ConfigManager, AGENT_COMMANDS
from .file_utils import (
    AGENT_DIR_NAMES,
    create_agent_config_files,
    get_agent_directory_name,
)

logger = logging.getLogger(__name__)


def switch_agent_environment(
    work_dir: Path,
    config: Config,
    config_manager: ConfigManager,
    new_agent_type: str,
) -> Path:
    """Replace agent-specific configuration files with a different agent type.

    Args:
        work_dir: Path to .hephaestus-work directory.
        config: Currently loaded Config object (will be mutated).
        config_manager: Manager responsible for persisting config.yaml.
        new_agent_type: Target agent identifier (claude, gemini, codex).

    Returns:
        Path to the newly created agent directory (e.g., .Claude).

    Raises:
        ValueError: If an unsupported agent type is requested.
    """
    normalized_type = new_agent_type.lower()
    if normalized_type not in AGENT_COMMANDS:
        raise ValueError(f"Unsupported agent type: {new_agent_type}")

    logger.info(
        "Switching agent environment from %s to %s",
        config.agent_type,
        normalized_type,
    )

    # Remove any existing agent directories so new personas can be generated cleanly.
    for dir_name in set(AGENT_DIR_NAMES.values()):
        dir_path = work_dir / dir_name
        if dir_path.exists():
            shutil.rmtree(dir_path)
            logger.debug("Removed agent directory: %s", dir_path)

    # Update configuration with new agent commands.
    new_command = AGENT_COMMANDS[normalized_type]
    config.agent_type = normalized_type
    config.master.command = new_command
    config.master.args = []
    config.workers.command = new_command
    config.workers.args = []
    config_manager.save(config)

    # Recreate agent persona files for the requested type.
    create_agent_config_files(work_dir, agent_type=normalized_type)
    agent_dir = work_dir / get_agent_directory_name(normalized_type)
    logger.info("Created new agent directory at %s", agent_dir)
    return agent_dir
