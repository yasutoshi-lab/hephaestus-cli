from __future__ import annotations

import os
import stat
import time
from pathlib import Path

import pytest

from hephaestus.utils import file_utils


def test_get_agent_directory_name_defaults() -> None:
    assert file_utils.get_agent_directory_name("claude") == ".Claude"
    assert file_utils.get_agent_directory_name("gemini") == ".Gemini"
    assert file_utils.get_agent_directory_name("codex") == ".Codex"
    # Unknown types should fall back to Claude directory
    assert file_utils.get_agent_directory_name("unknown") == ".Claude"


def test_get_work_directory_defaults_to_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    expected = tmp_path / file_utils.WORK_DIR_NAME
    assert file_utils.get_work_directory() == expected


def test_ensure_directory_creates_with_permissions(tmp_path: Path) -> None:
    target = tmp_path / "secure_dir"
    file_utils.ensure_directory(target, mode=0o750)
    assert target.exists()
    assert stat.S_IMODE(target.stat().st_mode) == 0o750


def test_create_directory_structure(tmp_path: Path) -> None:
    work_dir = file_utils.create_directory_structure(tmp_path)
    expected_subdirs = [
        "cache/agent_states",
        "cache/rate_limits",
        "tasks/pending",
        "tasks/in_progress",
        "tasks/completed",
        "checkpoints",
        "progress",
        "logs",
        "communication/master_to_worker",
        "communication/worker_to_master",
    ]
    for subdir in expected_subdirs:
        assert (work_dir / subdir).exists()


def test_copy_template(tmp_path: Path) -> None:
    destination = tmp_path / "config.yaml"
    file_utils.copy_template("config.yaml.template", destination)
    assert destination.exists()
    template_path = Path(__file__).resolve().parents[2] / "templates" / "config.yaml.template"
    assert destination.read_text(encoding="utf-8") == template_path.read_text(encoding="utf-8")


def test_list_files_returns_sorted_paths(tmp_path: Path) -> None:
    files = [tmp_path / name for name in ("b.txt", "a.txt", "c.txt")]
    for file_path in files:
        file_path.write_text("data", encoding="utf-8")
    listed = file_utils.list_files(tmp_path)
    assert listed == sorted(files)


def test_cleanup_old_files_removes_only_stale_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    old_file = tmp_path / "old.log"
    old_file.write_text("old", encoding="utf-8")
    new_file = tmp_path / "new.log"
    new_file.write_text("new", encoding="utf-8")

    stale_time = time.time() - (2 * 24 * 3600)
    os.utime(old_file, (stale_time, stale_time))

    removed = file_utils.cleanup_old_files(tmp_path, max_age_days=1)

    assert removed == 1
    assert not old_file.exists()
    assert new_file.exists()


def test_get_directory_size_counts_bytes(tmp_path: Path) -> None:
    file_one = tmp_path / "one.bin"
    file_one.write_bytes(b"\x00" * 10)
    file_two = tmp_path / "two.bin"
    file_two.write_bytes(b"\x01" * 5)
    assert file_utils.get_directory_size(tmp_path) == 15


def test_create_agent_config_files_generates_claude_md(tmp_path: Path) -> None:
    work_dir = tmp_path / ".hephaestus-work"
    work_dir.mkdir()
    file_utils.create_agent_config_files(work_dir, agent_type="claude")

    agent_dir = work_dir / file_utils.get_agent_directory_name("claude")
    assert (agent_dir / "CLAUDE.md").exists()
    assert (agent_dir / "master" / "CLAUDE.md").exists()
    assert (agent_dir / "worker" / "CLAUDE.md").exists()
    master_content = (agent_dir / "master" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Master Agent Configuration" in master_content


def test_create_agent_config_files_generates_gemini_md(tmp_path: Path) -> None:
    work_dir = tmp_path / ".hephaestus-work"
    work_dir.mkdir()
    file_utils.create_agent_config_files(work_dir, agent_type="gemini")

    agent_dir = work_dir / file_utils.get_agent_directory_name("gemini")
    assert (agent_dir / "GEMINI.md").exists()
    assert (agent_dir / "master" / "GEMINI.md").exists()
    assert (agent_dir / "worker" / "GEMINI.md").exists()
    master_content = (agent_dir / "master" / "GEMINI.md").read_text(encoding="utf-8")
    assert "Master Agent Configuration" in master_content


def test_create_agent_config_files_generates_codex_agent_md(tmp_path: Path) -> None:
    work_dir = tmp_path / ".hephaestus-work"
    work_dir.mkdir()
    file_utils.create_agent_config_files(work_dir, agent_type="codex")

    agent_dir = work_dir / file_utils.get_agent_directory_name("codex")
    assert (agent_dir / "AGENT.md").exists()
    assert (agent_dir / "master" / "AGENT.md").exists()
    assert (agent_dir / "worker" / "AGENT.md").exists()
    master_content = (agent_dir / "master" / "AGENT.md").read_text(encoding="utf-8")
    assert "Master Agent Configuration" in master_content


def test_create_agent_config_files_default_to_claude(tmp_path: Path) -> None:
    work_dir = tmp_path / ".hephaestus-work"
    work_dir.mkdir()
    file_utils.create_agent_config_files(work_dir)

    agent_dir = work_dir / file_utils.get_agent_directory_name("claude")
    assert (agent_dir / "CLAUDE.md").exists()
    assert (agent_dir / "master" / "CLAUDE.md").exists()
    assert (agent_dir / "worker" / "CLAUDE.md").exists()
