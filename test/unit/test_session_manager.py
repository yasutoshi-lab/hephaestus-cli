from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import libtmux
import pytest

from hephaestus.config import ConfigManager, create_default_config
from hephaestus.session_manager import SessionManager
from hephaestus.utils.file_utils import create_agent_config_files, create_directory_structure


def _prepare_workspace(tmp_path: Path, agent_type: str = "claude") -> Path:
    work_dir = create_directory_structure(tmp_path)
    create_agent_config_files(work_dir, agent_type=agent_type)
    config_path = work_dir / "config.yaml"
    create_default_config(config_path, agent_type=agent_type)
    return work_dir


@pytest.fixture
def config(tmp_path: Path) -> tuple[ConfigManager, Path]:
    work_dir = _prepare_workspace(tmp_path)
    config_path = work_dir / "config.yaml"
    config_manager = ConfigManager(config_path)
    return config_manager, work_dir


def test_create_session_enters_headless_when_tmux_missing(monkeypatch: pytest.MonkeyPatch, config: tuple[ConfigManager, Path]) -> None:
    config_manager, work_dir = config

    monkeypatch.setattr("hephaestus.session_manager.shutil.which", lambda _name: None)

    started: list[str] = []

    def fake_spawn(self: SessionManager, **kwargs):
        started.append(kwargs["agent_name"])
        return SimpleNamespace(pid=len(started))

    captured_state: dict = {}

    def fake_save(self: SessionManager, agents):
        captured_state["agents"] = agents

    monkeypatch.setattr(SessionManager, "_spawn_headless_agent", fake_spawn)
    monkeypatch.setattr(SessionManager, "_save_headless_state", fake_save)

    manager = SessionManager(config_manager.load(), work_dir)
    manager.create_session()

    assert manager.mode == "headless"
    assert started[0] == "master"
    assert len(started) == 1 + manager.config.workers.count
    assert len(captured_state["agents"]) == len(started)


def test_headless_fallback_on_tmux_permission_error(monkeypatch: pytest.MonkeyPatch, config: tuple[ConfigManager, Path]) -> None:
    config_manager, work_dir = config

    class FailingServer:
        def __init__(self, *_args, **_kwargs):
            pass

        def find_where(self, *_args, **_kwargs):
            return None

        def new_session(self, *_args, **_kwargs):
            raise libtmux.exc.LibTmuxException("error connecting to socket (Operation not permitted)")

    monkeypatch.setattr("hephaestus.session_manager.shutil.which", lambda _name: "/usr/bin/tmux")
    monkeypatch.setattr("hephaestus.session_manager.libtmux.Server", FailingServer)

    started: list[str] = []

    def fake_spawn(self: SessionManager, **kwargs):
        started.append(kwargs["agent_name"])
        return SimpleNamespace(pid=len(started) + 100)

    monkeypatch.setattr(SessionManager, "_spawn_headless_agent", fake_spawn)
    monkeypatch.setattr(SessionManager, "_save_headless_state", lambda *_args, **_kwargs: None)

    manager = SessionManager(config_manager.load(), work_dir)

    manager.create_session()

    assert manager.mode == "headless"
    assert started[0] == "master"
    assert manager._tmux_failure_reason is not None
