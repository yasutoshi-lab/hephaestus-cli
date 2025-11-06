"""File system utilities for Hephaestus-CLI.

This module provides functions for directory structure creation,
file operations, and template management.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Work directory name
WORK_DIR_NAME = "hephaestus-work"


def get_work_directory(base_path: Optional[Path] = None) -> Path:
    """Get the hephaestus-work directory path.

    Args:
        base_path: Base directory path. Defaults to current working directory.

    Returns:
        Path to hephaestus-work directory
    """
    if base_path is None:
        base_path = Path.cwd()
    return base_path / WORK_DIR_NAME


def ensure_directory(path: Path, mode: int = 0o700) -> None:
    """Ensure a directory exists with proper permissions.

    Args:
        path: Directory path to create
        mode: Unix file permissions (default: 0o700 for security)
    """
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    # Explicitly set permissions in case umask interfered
    os.chmod(path, mode)
    logger.debug(f"Created directory: {path} with mode {oct(mode)}")


def create_directory_structure(base_path: Optional[Path] = None) -> Path:
    """Create the complete hephaestus-work directory structure.

    Args:
        base_path: Base directory path. Defaults to current working directory.

    Returns:
        Path to the created hephaestus-work directory

    Raises:
        OSError: If directory creation fails
    """
    work_dir = get_work_directory(base_path)

    # Define directory structure
    directories = [
        work_dir,
        work_dir / "cache" / "agent_states",
        work_dir / "cache" / "rate_limits",
        work_dir / "tasks" / "pending",
        work_dir / "tasks" / "in_progress",
        work_dir / "tasks" / "completed",
        work_dir / "checkpoints",
        work_dir / "progress",
        work_dir / "logs",
        work_dir / "communication" / "master_to_worker",
        work_dir / "communication" / "worker_to_master",
    ]

    # Create all directories
    for directory in directories:
        ensure_directory(directory)

    logger.info(f"Created hephaestus-work directory structure at {work_dir}")
    return work_dir


def copy_template(template_name: str, destination: Path) -> None:
    """Copy a template file to the destination.

    Args:
        template_name: Name of the template file (e.g., 'config.yaml.template')
        destination: Destination file path

    Raises:
        FileNotFoundError: If template file is not found
    """
    # Get the package directory
    package_dir = Path(__file__).parent.parent.parent.parent
    template_path = package_dir / "templates" / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Copy template to destination
    shutil.copy2(template_path, destination)
    logger.debug(f"Copied template {template_name} to {destination}")


def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """List files in a directory matching a pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern (default: "*" for all files)

    Returns:
        List of matching file paths
    """
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern))


def cleanup_old_files(directory: Path, max_age_days: int = 30) -> int:
    """Remove files older than specified age.

    Args:
        directory: Directory to clean
        max_age_days: Maximum age in days

    Returns:
        Number of files removed
    """
    import time

    if not directory.exists():
        return 0

    max_age_seconds = max_age_days * 24 * 3600
    current_time = time.time()
    removed_count = 0

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

    return removed_count


def get_directory_size(directory: Path) -> int:
    """Calculate total size of directory in bytes.

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total_size = 0
    if directory.exists():
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    return total_size
