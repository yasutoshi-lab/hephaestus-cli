"""Agent communication via tmux send-keys.

This module provides direct communication between agents by sending messages
to their tmux panes, similar to the Claude-Code-Communication reference implementation.
"""

import subprocess
import time
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentCommunicator:
    """Handles agent-to-agent communication via tmux send-keys."""

    def __init__(self, session_name: str, work_dir: Path):
        """Initialize AgentCommunicator.

        Args:
            session_name: Name of the tmux session
            work_dir: Path to hephaestus-work directory
        """
        self.session_name = session_name
        self.work_dir = work_dir
        self.log_file = work_dir / "logs" / "communication.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def get_pane_target(self, agent_name: str) -> Optional[str]:
        """Get tmux pane target for an agent.

        Args:
            agent_name: Agent name (master, worker-1, worker-2, etc.)

        Returns:
            Tmux pane target string (e.g., "hephaestus:0.0") or None if not found
        """
        try:
            # List all panes with their titles
            result = subprocess.run(
                ["tmux", "list-panes", "-t", self.session_name, "-F", "#{pane_index}:#{pane_title}"],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse output to find matching agent
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    pane_index, pane_title = line.split(":", 1)
                    # Match agent name (case-insensitive)
                    if agent_name.lower() in pane_title.lower():
                        return f"{self.session_name}:0.{pane_index}"

            logger.warning(f"Agent {agent_name} not found in session {self.session_name}")
            return None

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to list panes: {e}")
            return None

    def send_message(self, target_agent: str, message: str, delay: float = 0.5) -> bool:
        """Send a message to an agent's chat pane.

        Args:
            target_agent: Target agent name (e.g., "worker-1")
            message: Message to send
            delay: Delay between commands in seconds

        Returns:
            True if message was sent successfully, False otherwise
        """
        target = self.get_pane_target(target_agent)
        if not target:
            logger.error(f"Cannot send message: target agent {target_agent} not found")
            return False

        try:
            # Step 1: Clear any existing input with Ctrl+C
            subprocess.run(
                ["tmux", "send-keys", "-t", target, "C-c"],
                check=True
            )
            time.sleep(delay)

            # Step 2: Send the message
            subprocess.run(
                ["tmux", "send-keys", "-t", target, message],
                check=True
            )
            time.sleep(delay)

            # Step 3: Press Enter to execute
            subprocess.run(
                ["tmux", "send-keys", "-t", target, "Enter"],
                check=True
            )

            # Log the communication
            self._log_communication("master", target_agent, message)

            logger.info(f"Sent message to {target_agent}: {message[:50]}...")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to send message to {target_agent}: {e}")
            return False

    def send_task_notification(self, target_agent: str, task_file: Path, comm_file: Path) -> bool:
        """Send task assignment notification to a worker.

        Args:
            target_agent: Target agent name (e.g., "worker-1")
            task_file: Path to task YAML file
            comm_file: Path to communication markdown file

        Returns:
            True if notification was sent successfully
        """
        # Create a concise notification message
        message = (
            f"New task assigned! Please read {comm_file.name} in the "
            f"communication/master_to_worker directory and execute the task."
        )

        return self.send_message(target_agent, message)

    def broadcast_to_workers(self, message: str, worker_count: int) -> int:
        """Broadcast a message to all workers.

        Args:
            message: Message to broadcast
            worker_count: Number of workers to send to

        Returns:
            Number of workers that received the message successfully
        """
        success_count = 0

        for i in range(1, worker_count + 1):
            worker_name = f"worker-{i}"
            if self.send_message(worker_name, message):
                success_count += 1

        return success_count

    def notify_master(self, worker_name: str, message: str) -> bool:
        """Send notification from worker to master.

        Args:
            worker_name: Name of the worker sending notification
            message: Notification message

        Returns:
            True if notification was sent successfully
        """
        return self.send_message("master", message)

    def _log_communication(self, from_agent: str, to_agent: str, message: str):
        """Log communication to file.

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            message: Message content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {from_agent} -> {to_agent}: {message}\n"

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            logger.warning(f"Failed to write communication log: {e}")

    def check_pane_active(self, agent_name: str) -> bool:
        """Check if an agent's pane is active and responsive.

        Args:
            agent_name: Agent name to check

        Returns:
            True if pane exists and is active
        """
        target = self.get_pane_target(agent_name)
        if not target:
            return False

        try:
            # Check if pane exists and is alive
            result = subprocess.run(
                ["tmux", "display-message", "-t", target, "-p", "#{pane_pid}"],
                capture_output=True,
                text=True,
                check=True
            )
            return bool(result.stdout.strip())
        except subprocess.CalledProcessError:
            return False

    def get_active_workers(self, worker_count: int) -> List[str]:
        """Get list of active workers.

        Args:
            worker_count: Expected number of workers

        Returns:
            List of active worker names
        """
        active_workers = []

        for i in range(1, worker_count + 1):
            worker_name = f"worker-{i}"
            if self.check_pane_active(worker_name):
                active_workers.append(worker_name)

        return active_workers
