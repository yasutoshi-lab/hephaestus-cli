from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import pytest

from hephaestus import cli
from hephaestus.config import ConfigManager, create_default_config
from hephaestus.utils.file_utils import create_agent_config_files, create_directory_structure, get_agent_directory_name


class DummySessionManager:
    """SessionManager test double with configurable behaviors."""

    session_exists_responses: list[bool] = []
    created = 0
    attached = 0

    def __init__(self, config, work_dir):
        self.config = config
        self.work_dir = work_dir

    def session_exists(self) -> bool:
        return self.session_exists_responses.pop(0)

    def create_session(self) -> None:
        type(self).created += 1

    def attach(self) -> None:
        type(self).attached += 1


def _prepare_workspace(tmp_path: Path, agent_type: str = "claude") -> Path:
    work_dir = create_directory_structure(tmp_path)
    create_agent_config_files(work_dir, agent_type=agent_type)
    config_path = work_dir / "config.yaml"
    create_default_config(config_path, agent_type=agent_type)
    return work_dir


def test_attach_rejects_agent_change_when_session_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work_dir = _prepare_workspace(tmp_path)

    monkeypatch.setattr(cli, "init_logger", lambda: None)
    monkeypatch.setattr(cli, "get_work_directory", lambda base_path=None: work_dir)

    class ActiveSessionManager:
        def __init__(self, *_args, **_kwargs):
            pass

        def session_exists(self) -> bool:
            return True

    monkeypatch.setattr(cli, "SessionManager", ActiveSessionManager)

    switch_called = False

    def fake_switch(*_args, **_kwargs):
        nonlocal switch_called
        switch_called = True

    monkeypatch.setattr(cli, "switch_agent_environment", fake_switch)

    runner = CliRunner()
    result = runner.invoke(cli.attach_command, ["--change-agent", "codex"])

    assert result.exit_code == 1
    assert "Cannot change agent" in result.output
    assert switch_called is False


def test_attach_changes_agent_and_creates_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    work_dir = _prepare_workspace(tmp_path, agent_type="claude")

    monkeypatch.setattr(cli, "init_logger", lambda: None)
    monkeypatch.setattr(cli, "get_work_directory", lambda base_path=None: work_dir)

    DummySessionManager.session_exists_responses = [False, False]
    DummySessionManager.created = 0
    DummySessionManager.attached = 0
    monkeypatch.setattr(cli, "SessionManager", DummySessionManager)

    runner = CliRunner()
    result = runner.invoke(
        cli.attach_command,
        ["--change-agent", "codex", "--create"],
    )

    assert result.exit_code == 0
    assert DummySessionManager.created == 1
    assert DummySessionManager.attached == 1

    config = ConfigManager(work_dir / "config.yaml").load()
    assert config.agent_type == "codex"
    assert config.master.command == "codex --full-auto"
    codex_dir = work_dir / get_agent_directory_name("codex")
    assert codex_dir.exists()
    assert (codex_dir / "master" / "AGENT.md").exists()
