from __future__ import annotations

from pathlib import Path

from hephaestus.communication import CommunicationManager, create_task_message, Message
from hephaestus.config import ConfigManager, create_default_config
from hephaestus.task_manager import TaskManager, TaskStatus
from hephaestus.utils.file_utils import create_agent_config_files, create_directory_structure


def test_end_to_end_task_assignment_and_completion(tmp_path: Path) -> None:
    base_path = tmp_path / "workspace"
    work_dir = create_directory_structure(base_path)
    create_agent_config_files(work_dir)

    config_path = work_dir / "config.yaml"
    create_default_config(config_path)
    config_manager = ConfigManager(config_path)
    config = config_manager.load()

    task_manager = TaskManager(work_dir)
    communication_manager = CommunicationManager(work_dir)

    task = task_manager.create_task(
        title="Integrate feature",
        description="Implement new feature and tests",
        requirements=["Write code", "Add tests", "Update docs"],
        expected_output="Merged pull request",
    )

    message = create_task_message(
        task_id=task.id,
        sender="master",
        recipient="worker-1",
        objective=task.description,
        requirements=task.requirements,
        expected_output=task.expected_output,
        priority="high",
    )
    assert communication_manager.send_message(message)

    worker_messages = communication_manager.receive_messages("worker-1")
    assert worker_messages and worker_messages[0].id == task.id

    # Worker acknowledges and sends status update back to master
    status_message = Message(
        id=f"{task.id}-status",
        type="status",
        sender="worker-1",
        recipient="master",
        content="Task started",
    )
    assert communication_manager.send_message(status_message)
    master_messages = communication_manager.receive_messages("master")
    assert master_messages and master_messages[0].type == "status"

    # Task progresses to completion
    assert task_manager.assign_task(task.id, "worker-1")
    assert task_manager.update_task_status(task.id, TaskStatus.COMPLETED, result="Feature delivered")
    stats = task_manager.get_statistics()
    assert stats["completed"] == 1
    assert stats["pending"] == 0

