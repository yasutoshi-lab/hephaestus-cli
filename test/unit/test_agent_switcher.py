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
    claude_dir = work_dir / get_agent_directory_name("claude")
    assert claude_dir.exists()

    target_type = "gemini"
    new_dir = switch_agent_environment(work_dir, config, manager, target_type)

    assert new_dir == work_dir / get_agent_directory_name(target_type)
    assert new_dir.exists()
    assert not (work_dir / get_agent_directory_name("claude")).exists()

    refreshed = manager.load()
    assert refreshed.agent_type == target_type
    assert refreshed.master.command == AGENT_COMMANDS[target_type]
    assert refreshed.workers.command == AGENT_COMMANDS[target_type]
    # Ensure persona files were recreated
    assert (new_dir / "master" / "GEMINI.md").exists()


def test_switch_agent_environment_validates_agent(tmp_path: Path) -> None:
    work_dir, manager = _setup_workspace(tmp_path)
    config = manager.load()

    with pytest.raises(ValueError):
        switch_agent_environment(work_dir, config, manager, "unknown")


def test_switch_agent_environment_preserves_non_agent_dirs(tmp_path: Path) -> None:
    work_dir, manager = _setup_workspace(tmp_path)
    config = manager.load()

    # Drop a sentinel file in tasks directory to ensure it survives the switch
    tasks_dir = work_dir / "tasks" / "pending"
    sentinel = tasks_dir / "keep.me"
    sentinel.write_text("important", encoding="utf-8")

    switch_agent_environment(work_dir, config, manager, "codex")

    assert sentinel.exists(), "Non-agent directories should remain untouched"
