from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.config import ConfigManager, create_default_config, AGENT_COMMANDS
from hephaestus.utils.file_utils import (
    create_agent_config_files,
    create_directory_structure,
    get_agent_directory_name,
)
from hephaestus.utils.agent_switcher import switch_agent_environment


def _setup_workspace(tmp_path: Path, agent_type: str = "claude") -> tuple[Path, ConfigManager]:
    base = create_directory_structure(tmp_path)
    create_agent_config_files(base, agent_type=agent_type)
    config_path = base / "config.yaml"
    create_default_config(config_path, agent_type=agent_type)
    return base, ConfigManager(config_path)


def test_switch_agent_environment_replaces_directories(tmp_path: Path) -> None:
    work_dir, manager = _setup_workspace(tmp_path, agent_type="claude")
    config = manager.load()
    assert (work_dir / get_agent_directory_name("claude")).exists()

    target_type = "gemini"
    new_dir = switch_agent_environment(work_dir, config, manager, target_type)

    assert new_dir == work_dir / get_agent_directory_name(target_type)
    assert new_dir.exists()
    assert not (work_dir / get_agent_directory_name("claude")).exists()

    refreshed = manager.load()
    assert refreshed.agent_type == target_type
    assert refreshed.master.command == AGENT_COMMANDS[target_type]
    assert refreshed.workers.command == AGENT_COMMANDS[target_type]


def test_switch_agent_environment_validates_agent(tmp_path: Path) -> None:
    work_dir, manager = _setup_workspace(tmp_path)
    config = manager.load()

    with pytest.raises(ValueError):
        switch_agent_environment(work_dir, config, manager, "unknown")
