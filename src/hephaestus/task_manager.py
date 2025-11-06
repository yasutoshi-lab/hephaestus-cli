"""Task management for Hephaestus-CLI.

This module handles task queue management, task assignment,
and progress tracking for Master and Worker agents.
"""

import json
import logging
import shutil
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority enumeration."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    """Represents a task to be executed by an agent."""

    id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    title: str = ""
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    expected_output: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert task to dictionary."""
        data = asdict(self)
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        """Create task from dictionary."""
        # Convert enum values
        if "priority" in data:
            data["priority"] = TaskPriority(data["priority"])
        if "status" in data:
            data["status"] = TaskStatus(data["status"])
        return cls(**data)


class TaskManager:
    """Manager for task queue and assignment."""

    def __init__(self, work_dir: Path):
        """Initialize TaskManager.

        Args:
            work_dir: Path to hephaestus-work directory
        """
        self.work_dir = work_dir
        self.tasks_dir = work_dir / "tasks"
        self.pending_dir = self.tasks_dir / "pending"
        self.in_progress_dir = self.tasks_dir / "in_progress"
        self.completed_dir = self.tasks_dir / "completed"

        # Ensure directories exist
        for directory in [self.pending_dir, self.in_progress_dir, self.completed_dir]:
            directory.mkdir(parents=True, exist_ok=True)

        self._tasks: Dict[str, Task] = {}
        self._load_all_tasks()

    def _get_task_file(self, task_id: str, status: TaskStatus) -> Path:
        """Get file path for a task based on its status.

        Args:
            task_id: Task identifier
            status: Task status

        Returns:
            Path to task file
        """
        if status == TaskStatus.PENDING:
            directory = self.pending_dir
        elif status == TaskStatus.IN_PROGRESS:
            directory = self.in_progress_dir
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            directory = self.completed_dir
        else:
            directory = self.pending_dir

        return directory / f"{task_id}.json"

    def _load_all_tasks(self) -> None:
        """Load all tasks from disk."""
        for directory in [self.pending_dir, self.in_progress_dir, self.completed_dir]:
            for task_file in directory.glob("*.json"):
                try:
                    with open(task_file, "r") as f:
                        data = json.load(f)
                    task = Task.from_dict(data)
                    self._tasks[task.id] = task
                except Exception as e:
                    logger.error(f"Failed to load task from {task_file}: {e}")

        logger.info(f"Loaded {len(self._tasks)} tasks from disk")

    def _save_task(self, task: Task) -> None:
        """Save task to disk.

        Args:
            task: Task to save
        """
        task_file = self._get_task_file(task.id, task.status)

        # Remove task from old location if status changed
        for status in TaskStatus:
            if status != task.status:
                old_file = self._get_task_file(task.id, status)
                if old_file.exists():
                    old_file.unlink()

        # Save to new location
        with open(task_file, "w") as f:
            json.dump(task.to_dict(), f, indent=2)

        logger.debug(f"Saved task {task.id} with status {task.status.value}")

    def create_task(
        self,
        title: str,
        description: str,
        requirements: Optional[List[str]] = None,
        expected_output: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: Optional[Dict] = None,
    ) -> Task:
        """Create a new task.

        Args:
            title: Task title
            description: Task description
            requirements: List of task requirements
            expected_output: Expected output description
            priority: Task priority
            metadata: Additional metadata

        Returns:
            Created Task object
        """
        task = Task(
            title=title,
            description=description,
            requirements=requirements or [],
            expected_output=expected_output,
            priority=priority,
            metadata=metadata or {},
        )

        self._tasks[task.id] = task
        self._save_task(task)

        logger.info(f"Created task {task.id}: {title}")
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task object or None if not found
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[TaskPriority] = None,
    ) -> List[Task]:
        """List tasks with optional filters.

        Args:
            status: Filter by status
            assigned_to: Filter by assigned agent
            priority: Filter by priority

        Returns:
            List of Task objects
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if assigned_to:
            tasks = [t for t in tasks if t.assigned_to == assigned_to]
        if priority:
            tasks = [t for t in tasks if t.priority == priority]

        # Sort by priority (high first) and creation time
        priority_order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        tasks.sort(key=lambda t: (priority_order[t.priority], t.created_at))

        return tasks

    def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier

        Returns:
            True if assignment was successful, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False

        if task.status != TaskStatus.PENDING:
            logger.error(f"Task {task_id} is not pending (status: {task.status.value})")
            return False

        task.assigned_to = agent_id
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = time.time()

        self._save_task(task)
        logger.info(f"Assigned task {task_id} to {agent_id}")
        return True

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update task status.

        Args:
            task_id: Task identifier
            status: New task status
            result: Optional result message
            error: Optional error message

        Returns:
            True if update was successful, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False

        task.status = status

        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = time.time()

        if result:
            task.result = result

        if error:
            task.error = error

        self._save_task(task)
        logger.info(f"Updated task {task_id} status to {status.value}")
        return True

    def get_next_pending_task(self, priority: Optional[TaskPriority] = None) -> Optional[Task]:
        """Get the next pending task.

        Args:
            priority: Optional minimum priority filter

        Returns:
            Next pending Task or None
        """
        pending_tasks = self.list_tasks(status=TaskStatus.PENDING, priority=priority)

        if not pending_tasks:
            return None

        # Return highest priority task
        return pending_tasks[0]

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancellation was successful, False otherwise
        """
        return self.update_task_status(task_id, TaskStatus.CANCELLED)

    def delete_task(self, task_id: str) -> bool:
        """Delete a task completely.

        Args:
            task_id: Task identifier

        Returns:
            True if deletion was successful, False otherwise
        """
        task = self.get_task(task_id)
        if not task:
            return False

        # Remove from memory
        del self._tasks[task_id]

        # Remove from disk
        task_file = self._get_task_file(task_id, task.status)
        if task_file.exists():
            task_file.unlink()

        logger.info(f"Deleted task {task_id}")
        return True

    def get_statistics(self) -> Dict:
        """Get task statistics.

        Returns:
            Dictionary with task statistics
        """
        stats = {
            "total": len(self._tasks),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "by_priority": {
                "high": 0,
                "medium": 0,
                "low": 0,
            },
        }

        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING:
                stats["pending"] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                stats["in_progress"] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats["completed"] += 1
            elif task.status == TaskStatus.FAILED:
                stats["failed"] += 1
            elif task.status == TaskStatus.CANCELLED:
                stats["cancelled"] += 1

            stats["by_priority"][task.priority.value] += 1

        return stats

    def cleanup_old_tasks(self, days: int = 30) -> int:
        """Remove completed tasks older than specified days.

        Args:
            days: Number of days

        Returns:
            Number of tasks removed
        """
        cutoff_time = time.time() - (days * 24 * 3600)
        removed = 0

        for task_id, task in list(self._tasks.items()):
            if (
                task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                and task.completed_at
                and task.completed_at < cutoff_time
            ):
                if self.delete_task(task_id):
                    removed += 1

        logger.info(f"Cleaned up {removed} old tasks")
        return removed
