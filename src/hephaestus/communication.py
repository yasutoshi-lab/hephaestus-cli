"""Communication layer for Hephaestus.

This module implements Markdown-based message passing between
Master and Worker agents using the file system.
"""

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message between agents."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "task"  # task|status|result|error
    sender: str = "master"
    recipient: str = "worker-1"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    priority: str = "medium"  # high|medium|low
    content: str = ""
    checksum: str = ""

    def __post_init__(self):
        """Calculate checksum after initialization."""
        if not self.checksum:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        """Calculate MD5 checksum of message content."""
        # Strip content to ensure consistent checksum calculation
        content_str = f"{self.id}{self.type}{self.sender}{self.recipient}{self.content.strip()}"
        return hashlib.md5(content_str.encode()).hexdigest()

    def verify_checksum(self) -> bool:
        """Verify message integrity.

        Returns:
            True if checksum is valid, False otherwise
        """
        return self.checksum == self._calculate_checksum()

    def to_markdown(self) -> str:
        """Convert message to Markdown format.

        Returns:
            Markdown-formatted message string
        """
        metadata = {
            "id": self.id,
            "type": self.type,
            "from": self.sender,
            "to": self.recipient,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }

        markdown = "# Task Message\n"
        markdown += "---\n"
        markdown += "metadata:\n"
        for key, value in metadata.items():
            markdown += f"  {key}: \"{value}\"\n"
        markdown += "---\n\n"
        markdown += "## Content\n\n"
        markdown += self.content + "\n\n"
        markdown += "---\n"
        markdown += f"checksum: \"{self.checksum}\"\n"

        return markdown

    @classmethod
    def from_markdown(cls, markdown: str) -> "Message":
        """Parse message from Markdown format.

        Args:
            markdown: Markdown-formatted message string

        Returns:
            Message object

        Raises:
            ValueError: If markdown format is invalid
        """
        try:
            # Split by "---" delimiters
            parts = markdown.split("---")
            if len(parts) < 3:
                raise ValueError("Invalid message format: missing delimiters")

            # Extract metadata
            metadata_section = parts[1].strip()
            if metadata_section.startswith("metadata:"):
                # Parse the entire metadata section as YAML
                parsed = yaml.safe_load(metadata_section)
                metadata = parsed.get("metadata", {})
            else:
                raise ValueError("Invalid message format: metadata not found")

            # Extract content
            content_section = parts[2].strip()
            if "## Content" in content_section:
                content = content_section.split("## Content", 1)[1].strip()
            else:
                content = ""

            # Extract checksum
            checksum_section = parts[3].strip() if len(parts) > 3 else ""
            checksum = ""
            if "checksum:" in checksum_section:
                checksum = checksum_section.split("checksum:", 1)[1].strip().strip('"')

            # Create message
            message = cls(
                id=metadata.get("id", str(uuid.uuid4())),
                type=metadata.get("type", "task"),
                sender=metadata.get("from", "master"),
                recipient=metadata.get("to", "worker-1"),
                timestamp=metadata.get("timestamp", datetime.utcnow().isoformat() + "Z"),
                priority=metadata.get("priority", "medium"),
                content=content,
                checksum=checksum,
            )

            return message

        except Exception as e:
            logger.error(f"Failed to parse message from markdown: {e}")
            raise ValueError(f"Invalid message format: {e}")


class CommunicationManager:
    """Manager for inter-agent communication."""

    def __init__(self, work_dir: Path):
        """Initialize CommunicationManager.

        Args:
            work_dir: Path to .hephaestus-work directory
        """
        self.work_dir = work_dir
        self.comm_dir = work_dir / "communication"
        self.master_to_worker_dir = self.comm_dir / "master_to_worker"
        self.worker_to_master_dir = self.comm_dir / "worker_to_master"

        # Ensure directories exist
        self.master_to_worker_dir.mkdir(parents=True, exist_ok=True)
        self.worker_to_master_dir.mkdir(parents=True, exist_ok=True)

    def send_message(self, message: Message) -> bool:
        """Send a message from one agent to another.

        Args:
            message: Message to send

        Returns:
            True if message was sent successfully, False otherwise
        """
        try:
            # Determine target directory
            if message.sender == "master":
                target_dir = self.master_to_worker_dir / message.recipient
            else:
                target_dir = self.worker_to_master_dir / message.sender

            target_dir.mkdir(parents=True, exist_ok=True)

            # Write message to file
            filename = f"{message.id}_{message.type}.md"
            filepath = target_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(message.to_markdown())

            logger.debug(f"Sent message {message.id} from {message.sender} to {message.recipient}")
            return True

        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            return False

    def receive_messages(self, agent_id: str, message_type: Optional[str] = None) -> List[Message]:
        """Receive messages for a specific agent.

        Args:
            agent_id: Agent identifier (e.g., 'master', 'worker-1')
            message_type: Optional filter by message type

        Returns:
            List of Message objects
        """
        messages = []

        try:
            # Determine message file locations
            pattern = f"*_{message_type}.md" if message_type else "*.md"

            if agent_id == "master":
                if not self.worker_to_master_dir.exists():
                    return messages
                filepaths = sorted(self.worker_to_master_dir.rglob(pattern))
            else:
                source_dir = self.master_to_worker_dir / agent_id
                if not source_dir.exists():
                    return messages
                filepaths = sorted(source_dir.glob(pattern))

            for filepath in filepaths:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        markdown = f.read()

                    message = Message.from_markdown(markdown)

                    # Verify checksum
                    if not message.verify_checksum():
                        logger.warning(f"Invalid checksum for message {message.id}")
                        continue

                    messages.append(message)

                except Exception as e:
                    logger.error(f"Failed to parse message from {filepath}: {e}")

            logger.debug(f"Received {len(messages)} messages for {agent_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to receive messages: {e}", exc_info=True)
            return messages

    def delete_message(self, agent_id: str, message_id: str) -> bool:
        """Delete a processed message.

        Args:
            agent_id: Agent identifier
            message_id: Message ID to delete

        Returns:
            True if message was deleted, False otherwise
        """
        try:
            # Determine directory
            if agent_id == "master":
                search_dirs = [self.worker_to_master_dir]
            else:
                search_dirs = [self.master_to_worker_dir / agent_id]

            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue

                # Find and delete message file
                for filepath in search_dir.rglob(f"{message_id}_*.md"):
                    filepath.unlink()
                    logger.debug(f"Deleted message {message_id} for {agent_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete message: {e}", exc_info=True)
            return False

    def get_message_count(self, agent_id: str) -> int:
        """Get number of pending messages for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Number of pending messages
        """
        try:
            if agent_id == "master":
                if not self.worker_to_master_dir.exists():
                    return 0
                return len(list(self.worker_to_master_dir.rglob("*.md")))

            source_dir = self.master_to_worker_dir / agent_id
            if not source_dir.exists():
                return 0

            return len(list(source_dir.glob("*.md")))

        except Exception as e:
            logger.error(f"Failed to count messages: {e}", exc_info=True)
            return 0

    def clear_all_messages(self, agent_id: Optional[str] = None) -> int:
        """Clear all messages, optionally for a specific agent.

        Args:
            agent_id: Optional agent identifier to clear messages for

        Returns:
            Number of messages cleared
        """
        cleared = 0

        try:
            if agent_id:
                # Clear for specific agent
                if agent_id == "master":
                    dirs = [self.worker_to_master_dir]
                else:
                    dirs = [self.master_to_worker_dir / agent_id]
            else:
                # Clear all
                dirs = [self.master_to_worker_dir, self.worker_to_master_dir]

            for directory in dirs:
                if directory.exists():
                    for filepath in directory.rglob("*.md"):
                        filepath.unlink()
                        cleared += 1

            logger.info(f"Cleared {cleared} messages")
            return cleared

        except Exception as e:
            logger.error(f"Failed to clear messages: {e}", exc_info=True)
            return cleared


def create_task_message(
    task_id: str,
    sender: str,
    recipient: str,
    objective: str,
    requirements: List[str],
    expected_output: str,
    deadline: Optional[str] = None,
    priority: str = "medium",
) -> Message:
    """Create a formatted task message.

    Args:
        task_id: Unique task identifier
        sender: Sender agent ID
        recipient: Recipient agent ID
        objective: Task objective description
        requirements: List of task requirements
        expected_output: Description of expected output
        deadline: Optional deadline
        priority: Task priority (high|medium|low)

    Returns:
        Message object
    """
    content = f"### Objective\n{objective}\n\n"
    content += "### Requirements\n"
    for req in requirements:
        content += f"- {req}\n"
    content += f"\n### Expected Output\n{expected_output}\n"

    if deadline:
        content += f"\n### Deadline\n{deadline}\n"

    return Message(
        id=task_id,
        type="task",
        sender=sender,
        recipient=recipient,
        priority=priority,
        content=content,
    )
