from __future__ import annotations

import time
from pathlib import Path

import pytest

from hephaestus.task_manager import TaskManager, TaskPriority, TaskStatus


def test_create_task_persists_to_disk(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    task = manager.create_task(
        title="Analyse logs",
        description="Inspect log files",
        requirements=["Gather files", "Summarise findings"],
        expected_output="Report",
        priority=TaskPriority.HIGH,
    )

    assert manager.get_task(task.id) is not None
    task_file = manager._get_task_file(task.id, TaskStatus.PENDING)
    assert task_file.exists()


def test_assign_task_updates_status_and_timestamp(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    task = manager.create_task("Build feature", "Implement module")
    assert manager.assign_task(task.id, "worker-1")
    updated = manager.get_task(task.id)
    assert updated.status == TaskStatus.IN_PROGRESS
    assert updated.assigned_to == "worker-1"
    assert updated.started_at is not None


def test_update_task_status_moves_file(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    task = manager.create_task("Write docs", "Document API")
    manager.assign_task(task.id, "worker-1")
    assert manager.update_task_status(task.id, TaskStatus.COMPLETED, result="Done")
    updated = manager.get_task(task.id)
    assert updated.status == TaskStatus.COMPLETED
    assert updated.result == "Done"
    completed_file = manager._get_task_file(task.id, TaskStatus.COMPLETED)
    assert completed_file.exists()


def test_list_tasks_filters_by_status_priority_and_assignment(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    high = manager.create_task("High prio", "Important", priority=TaskPriority.HIGH)
    medium = manager.create_task("Medium prio", "Normal", priority=TaskPriority.MEDIUM)
    manager.assign_task(high.id, "worker-1")
    manager.update_task_status(high.id, TaskStatus.IN_PROGRESS)

    pending_tasks = manager.list_tasks(status=TaskStatus.PENDING)
    assert all(task.status == TaskStatus.PENDING for task in pending_tasks)
    priority_tasks = manager.list_tasks(priority=TaskPriority.HIGH)
    assert priority_tasks[0].priority == TaskPriority.HIGH
    assigned_tasks = manager.list_tasks(assigned_to="worker-1")
    assert assigned_tasks and assigned_tasks[0].assigned_to == "worker-1"


def test_get_next_pending_task_prefers_high_priority(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    low = manager.create_task("Low", "Task", priority=TaskPriority.LOW)
    high = manager.create_task("High", "Task", priority=TaskPriority.HIGH)
    next_task = manager.get_next_pending_task()
    assert next_task.id == high.id
    manager.assign_task(high.id, "worker")
    assert manager.get_next_pending_task().id == low.id


def test_cancel_and_delete_task(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    task = manager.create_task("Cancel me", "Testing")
    assert manager.cancel_task(task.id)
    assert manager.get_task(task.id).status == TaskStatus.CANCELLED
    assert manager.delete_task(task.id)
    assert manager.get_task(task.id) is None


def test_get_statistics_counts_statuses(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    pending = manager.create_task("Pending", "Task")
    in_progress = manager.create_task("In progress", "Task")
    completed = manager.create_task("Completed", "Task")

    manager.assign_task(in_progress.id, "worker")
    manager.update_task_status(in_progress.id, TaskStatus.IN_PROGRESS)
    manager.assign_task(completed.id, "worker")
    manager.update_task_status(completed.id, TaskStatus.COMPLETED)

    stats = manager.get_statistics()
    assert stats["total"] == 3
    assert stats["pending"] == 1
    assert stats["in_progress"] == 1
    assert stats["completed"] == 1


def test_cleanup_old_tasks_removes_expired_completed_tasks(work_dir: Path) -> None:
    manager = TaskManager(work_dir)
    task = manager.create_task("Cleanup", "Task")
    manager.assign_task(task.id, "worker")
    manager.update_task_status(task.id, TaskStatus.COMPLETED)
    stored = manager.get_task(task.id)
    stored.completed_at = time.time() - (60 * 60 * 24 * 31)
    manager._save_task(stored)

    removed = manager.cleanup_old_tasks(days=30)
    assert removed == 1
    assert manager.get_task(task.id) is None

