from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT.parent / "src"

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from hephaestus.utils.file_utils import create_agent_config_files, create_directory_structure


@pytest.fixture
def work_dir(tmp_path: Path) -> Path:
    """Create a fresh .hephaestus-work directory for tests."""
    create_directory_structure(tmp_path)
    work_directory = tmp_path / ".hephaestus-work"
    create_agent_config_files(work_directory)
    return work_directory

