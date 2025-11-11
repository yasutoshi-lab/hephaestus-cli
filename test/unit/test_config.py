from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.config import (
    AgentConfig,
    CommunicationConfig,
    Config,
    ConfigManager,
    LoggingConfig,
    MonitoringConfig,
    TmuxConfig,
    WorkersConfig,
    create_default_config,
)


def test_config_from_and_to_dict_roundtrip() -> None:
    data = {
        "version": "2.0",
        "agent_type": "gemini",
        "agents": {
            "master": {"enabled": False, "command": "master-cmd", "args": ["--debug"]},
            "workers": {"count": 5, "command": "worker-cmd", "args": ["--fast"]},
        },
        "monitoring": {"health_check_interval": 10, "retry_attempts": 5, "retry_delay": 2},
        "communication": {"format": "json", "encoding": "latin-1"},
        "logging": {"level": "DEBUG", "format": "%(message)s"},
        "tmux": {"session_name": "test-session", "layout": "even-horizontal"},
    }

    config = Config.from_dict(data)
    assert config.version == "2.0"
    assert config.agent_type == "gemini"
    assert config.master == AgentConfig(enabled=False, command="master-cmd", args=["--debug"])
    assert config.workers == WorkersConfig(count=5, command="worker-cmd", args=["--fast"])
    assert config.monitoring == MonitoringConfig(10, 5, 2)
    assert config.communication == CommunicationConfig("json", "latin-1")
    assert config.logging == LoggingConfig("DEBUG", "%(message)s")
    assert config.tmux == TmuxConfig("test-session", "even-horizontal")

    assert config.to_dict() == data


def test_config_manager_save_and_load(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager(config_path)
    config = Config(version="1.1")

    manager.save(config)
    loaded = manager.load()
    assert loaded.version == "1.1"
    assert manager.get() is loaded


def test_config_manager_get_without_load_raises(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path / "config.yaml")
    with pytest.raises(RuntimeError):
        _ = manager.get()


def test_config_manager_reload_reads_new_content(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    manager = ConfigManager(config_path)
    first = Config(version="1.0")
    manager.save(first)

    second = Config(version="2.0")
    manager.save(second)
    reloaded = manager.reload()
    assert reloaded.version == "2.0"


def test_create_default_config_writes_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config = create_default_config(config_path)
    assert config_path.exists()
    assert config.version == "1.0"
    assert config.agent_type == "claude"
    assert config.master.command == "claude --dangerously-skip-permissions"
    assert config.workers.command == "claude --dangerously-skip-permissions"


def test_create_default_config_with_claude_agent() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.yaml"
        config = create_default_config(config_path, agent_type="claude")
        assert config.agent_type == "claude"
        assert config.master.command == "claude --dangerously-skip-permissions"
        assert config.workers.command == "claude --dangerously-skip-permissions"


def test_create_default_config_with_gemini_agent() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.yaml"
        config = create_default_config(config_path, agent_type="gemini")
        assert config.agent_type == "gemini"
        assert config.master.command == "gemini --yolo"
        assert config.workers.command == "gemini --yolo"


def test_create_default_config_with_codex_agent() -> None:
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "config.yaml"
        config = create_default_config(config_path, agent_type="codex")
        assert config.agent_type == "codex"
        assert config.master.command == "codex --full-auto"
        assert config.workers.command == "codex --full-auto"

