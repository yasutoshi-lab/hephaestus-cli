"""Task distribution and monitoring for multi-agent system.

This module handles automatic task distribution to workers and monitors
their completion status.
"""

import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from .agent_communicator import AgentCommunicator
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class TaskAssignment:
    """Represents a task assignment to a worker."""

    task_id: str
    worker_name: str
    task_file: Path
    comm_file: Path
    assigned_at: datetime
    notified: bool = False
    completed: bool = False


class TaskDistributor:
    """Handles task distribution and monitoring."""

    def __init__(self, config: Config, work_dir: Path, communicator: AgentCommunicator):
        """Initialize TaskDistributor.

        Args:
            config: Configuration object
            work_dir: Path to hephaestus-work directory
            communicator: AgentCommunicator instance
        """
        self.config = config
        self.work_dir = work_dir
        self.communicator = communicator
        self.assignments: Dict[str, TaskAssignment] = {}

        # Task directories
        self.pending_dir = work_dir / "tasks" / "pending"
        self.in_progress_dir = work_dir / "tasks" / "in_progress"
        self.completed_dir = work_dir / "tasks" / "completed"

        # Communication directories
        self.master_to_worker_dir = work_dir / "communication" / "master_to_worker"
        self.worker_to_master_dir = work_dir / "communication" / "worker_to_master"

    def monitor_and_distribute_tasks(self, interval: int = 5, max_iterations: int = 60) -> bool:
        """Monitor pending tasks and distribute to available workers.

        This function runs in a loop, checking for new tasks and distributing them.

        Args:
            interval: Check interval in seconds
            max_iterations: Maximum number of iterations before stopping

        Returns:
            True if all tasks were distributed successfully
        """
        logger.info("Starting task distribution monitor...")

        for iteration in range(max_iterations):
            # Check for new communication files from master
            new_tasks = self._scan_new_tasks()

            if new_tasks:
                logger.info(f"Found {len(new_tasks)} new tasks to distribute")
                self._distribute_tasks(new_tasks)

            # Check for completed tasks
            self._check_completions()

            # Log status
            if iteration % 5 == 0:
                self._log_status()

            time.sleep(interval)

        return True

    def distribute_task_immediately(self, task_id: str, worker_name: str,
                                   task_file: Path, comm_file: Path) -> bool:
        """Distribute a single task immediately to a worker.

        Args:
            task_id: Task identifier
            worker_name: Target worker name
            task_file: Path to task YAML file
            comm_file: Path to communication file

        Returns:
            True if task was distributed successfully
        """
        logger.info(f"Distributing task {task_id} to {worker_name}")

        # Send notification to worker
        success = self.communicator.send_task_notification(worker_name, task_file, comm_file)

        if success:
            # Record assignment
            assignment = TaskAssignment(
                task_id=task_id,
                worker_name=worker_name,
                task_file=task_file,
                comm_file=comm_file,
                assigned_at=datetime.now(),
                notified=True
            )
            self.assignments[task_id] = assignment
            logger.info(f"Task {task_id} distributed successfully to {worker_name}")
        else:
            logger.error(f"Failed to distribute task {task_id} to {worker_name}")

        return success

    def _scan_new_tasks(self) -> List[Dict[str, Path]]:
        """Scan for new tasks in master_to_worker directory.

        Returns:
            List of new task dictionaries with task_id, worker, and file paths
        """
        new_tasks = []

        if not self.master_to_worker_dir.exists():
            return new_tasks

        # Find communication files that haven't been notified yet
        for comm_file in self.master_to_worker_dir.glob("*_master_worker*_task_*.md"):
            # Parse filename to extract task info
            task_info = self._parse_comm_filename(comm_file)
            if not task_info:
                continue

            task_id = task_info["task_id"]

            # Skip if already notified
            if task_id in self.assignments and self.assignments[task_id].notified:
                continue

            # Find corresponding task file
            task_file = self.pending_dir / f"{task_id}.yaml"
            if not task_file.exists():
                # Try in_progress
                task_file = self.in_progress_dir / f"{task_id}.yaml"

            if task_file.exists():
                new_tasks.append({
                    "task_id": task_id,
                    "worker": task_info["worker"],
                    "task_file": task_file,
                    "comm_file": comm_file
                })

        return new_tasks

    def _parse_comm_filename(self, comm_file: Path) -> Optional[Dict[str, str]]:
        """Parse communication filename to extract task information.

        Expected format: YYYYMMDD_HHMMSS_master_worker[N]_task_[ID].md

        Args:
            comm_file: Path to communication file

        Returns:
            Dictionary with task_id and worker, or None if parsing fails
        """
        filename = comm_file.stem  # Remove .md extension

        try:
            parts = filename.split("_")

            # Find task_XXX part
            task_id = None
            for i, part in enumerate(parts):
                if part == "task" and i + 1 < len(parts):
                    task_id = f"task_{parts[i + 1]}"
                    break

            # Find worker name (workerN or worker-N)
            worker = None
            for part in parts:
                if part.startswith("worker"):
                    # Extract worker number
                    worker_num = part.replace("worker", "")
                    worker = f"worker-{worker_num}" if worker_num else None
                    break

            if task_id and worker:
                return {"task_id": task_id, "worker": worker}

        except Exception as e:
            logger.warning(f"Failed to parse comm filename {comm_file.name}: {e}")

        return None

    def _distribute_tasks(self, tasks: List[Dict[str, Path]]):
        """Distribute multiple tasks to workers.

        Args:
            tasks: List of task dictionaries
        """
        for task_info in tasks:
            self.distribute_task_immediately(
                task_info["task_id"],
                task_info["worker"],
                task_info["task_file"],
                task_info["comm_file"]
            )

    def _check_completions(self):
        """Check for completed tasks based on worker responses."""
        if not self.worker_to_master_dir.exists():
            return

        # Scan for completion reports
        for report_file in self.worker_to_master_dir.glob("*_worker*_master_task_*.md"):
            # Parse to find task_id
            task_id = self._extract_task_id_from_report(report_file)

            if task_id and task_id in self.assignments:
                assignment = self.assignments[task_id]

                # Check if task file has moved to completed
                completed_task_file = self.completed_dir / f"{task_id}.yaml"

                if completed_task_file.exists() and not assignment.completed:
                    assignment.completed = True
                    logger.info(f"Task {task_id} marked as completed by {assignment.worker_name}")

    def _extract_task_id_from_report(self, report_file: Path) -> Optional[str]:
        """Extract task ID from worker report filename.

        Args:
            report_file: Path to worker report file

        Returns:
            Task ID or None
        """
        filename = report_file.stem

        try:
            parts = filename.split("_")
            for i, part in enumerate(parts):
                if part == "task" and i + 1 < len(parts):
                    return f"task_{parts[i + 1]}"
        except Exception as e:
            logger.warning(f"Failed to extract task ID from {report_file.name}: {e}")

        return None

    def _log_status(self):
        """Log current distribution status."""
        total = len(self.assignments)
        notified = sum(1 for a in self.assignments.values() if a.notified)
        completed = sum(1 for a in self.assignments.values() if a.completed)

        logger.info(f"Task status: {total} total, {notified} notified, {completed} completed")

    def get_status_summary(self) -> Dict[str, int]:
        """Get summary of task distribution status.

        Returns:
            Dictionary with counts of total, notified, and completed tasks
        """
        return {
            "total": len(self.assignments),
            "notified": sum(1 for a in self.assignments.values() if a.notified),
            "completed": sum(1 for a in self.assignments.values() if a.completed),
            "pending": sum(1 for a in self.assignments.values()
                         if a.notified and not a.completed)
        }
