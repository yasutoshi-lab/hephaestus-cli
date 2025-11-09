from __future__ import annotations

from pathlib import Path

import pytest

from hephaestus.communication import CommunicationManager, Message, create_task_message


def test_message_checksum_and_verification() -> None:
    message = Message(content="Hello world", sender="master", recipient="worker-1")
    assert message.verify_checksum()
    original_checksum = message.checksum
    message.content = "Tampered"
    assert not message.verify_checksum()
    message.content = "Hello world"
    assert message.checksum == original_checksum


def test_message_markdown_roundtrip() -> None:
    message = Message(
        id="task-123",
        type="task",
        sender="master",
        recipient="worker-2",
        content="### Objective\nDo something\n",
        priority="high",
    )
    markdown = message.to_markdown()
    parsed = Message.from_markdown(markdown)
    assert parsed.id == "task-123"
    assert parsed.sender == "master"
    assert parsed.recipient == "worker-2"
    assert parsed.content.strip().startswith("### Objective")
    assert parsed.verify_checksum()


def test_create_task_message_formats_content() -> None:
    message = create_task_message(
        task_id="task-1",
        sender="master",
        recipient="worker-1",
        objective="Build feature",
        requirements=["Write code", "Add tests"],
        expected_output="Pull request",
        deadline="Tomorrow",
        priority="high",
    )
    assert message.id == "task-1"
    assert "### Objective" in message.content
    assert "- Write code" in message.content
    assert "### Deadline" in message.content


def test_communication_manager_send_receive_and_delete(work_dir: Path) -> None:
    manager = CommunicationManager(work_dir)
    message = Message(content="Task details", sender="master", recipient="worker-1")
    assert manager.send_message(message)

    # Worker receives message
    received = manager.receive_messages("worker-1")
    assert len(received) == 1
    assert received[0].content.startswith("Task details")

    # Deleting message removes it
    assert manager.delete_message("worker-1", message.id)
    assert manager.get_message_count("worker-1") == 0


def test_communication_manager_handles_worker_to_master(work_dir: Path) -> None:
    manager = CommunicationManager(work_dir)
    message = Message(content="Status update", sender="worker-1", recipient="master", type="status")
    assert manager.send_message(message)

    received = manager.receive_messages("master")
    assert len(received) == 1
    assert received[0].type == "status"
    assert received[0].verify_checksum()


def test_clear_all_messages_returns_count(work_dir: Path) -> None:
    manager = CommunicationManager(work_dir)
    for idx in range(2):
        manager.send_message(Message(content=f"Task {idx}", sender="master", recipient=f"worker-{idx+1}"))
    cleared = manager.clear_all_messages()
    assert cleared == 2
    assert manager.get_message_count("worker-1") == 0

