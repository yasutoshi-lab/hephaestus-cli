"""Agent lifecycle management for Hephaestus-CLI.

This module handles the lifecycle of Master and Worker agents,
including spawning, monitoring, and terminating processes.
"""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List
import psutil

from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about a running agent."""

    id: str
    type: str  # 'master' or 'worker'
    pid: Optional[int]
    command: str
    start_time: float
    status: str  # 'running', 'stopped', 'error'
    log_file: Path


class AgentController:
    """Controller for managing agent lifecycle."""

    def __init__(self, config: Config, work_dir: Path):
        """Initialize AgentController.

        Args:
            config: Configuration object
            work_dir: Path to hephaestus-work directory
        """
        self.config = config
        self.work_dir = work_dir
        self.agents: Dict[str, AgentInfo] = {}
        self._load_agent_states()

    def _get_state_file(self) -> Path:
        """Get path to agent states file."""
        return self.work_dir / "cache" / "agent_states" / "agents.json"

    def _load_agent_states(self) -> None:
        """Load agent states from cache."""
        state_file = self._get_state_file()
        if not state_file.exists():
            return

        try:
            with open(state_file, "r") as f:
                data = json.load(f)

            for agent_id, agent_data in data.items():
                self.agents[agent_id] = AgentInfo(
                    id=agent_id,
                    type=agent_data["type"],
                    pid=agent_data.get("pid"),
                    command=agent_data["command"],
                    start_time=agent_data["start_time"],
                    status=agent_data["status"],
                    log_file=Path(agent_data["log_file"]),
                )

            logger.info(f"Loaded {len(self.agents)} agent states from cache")
        except Exception as e:
            logger.warning(f"Failed to load agent states: {e}")

    def _save_agent_states(self) -> None:
        """Save agent states to cache."""
        state_file = self._get_state_file()
        state_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            data = {}
            for agent_id, agent_info in self.agents.items():
                data[agent_id] = {
                    "type": agent_info.type,
                    "pid": agent_info.pid,
                    "command": agent_info.command,
                    "start_time": agent_info.start_time,
                    "status": agent_info.status,
                    "log_file": str(agent_info.log_file),
                }

            with open(state_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved agent states to cache")
        except Exception as e:
            logger.warning(f"Failed to save agent states: {e}")

    def register_agent(
        self, agent_id: str, agent_type: str, pid: Optional[int] = None
    ) -> AgentInfo:
        """Register a new agent.

        Args:
            agent_id: Unique agent identifier
            agent_type: Type of agent ('master' or 'worker')
            pid: Process ID (if available)

        Returns:
            AgentInfo object for the registered agent
        """
        if agent_type == "master":
            command = self.config.master.command
            log_file = self.work_dir / "logs" / "master.log"
        else:
            command = self.config.workers.command
            worker_num = agent_id.split("-")[-1]
            log_file = self.work_dir / "logs" / f"worker_{worker_num}.log"

        agent_info = AgentInfo(
            id=agent_id,
            type=agent_type,
            pid=pid,
            command=command,
            start_time=time.time(),
            status="running" if pid else "stopped",
            log_file=log_file,
        )

        self.agents[agent_id] = agent_info
        self._save_agent_states()

        logger.info(f"Registered agent: {agent_id} (type={agent_type}, pid={pid})")
        return agent_info

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent identifier to unregister
        """
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_agent_states()
            logger.info(f"Unregistered agent: {agent_id}")

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentInfo object or None if not found
        """
        return self.agents.get(agent_id)

    def list_agents(self) -> List[AgentInfo]:
        """List all registered agents.

        Returns:
            List of AgentInfo objects
        """
        return list(self.agents.values())

    def is_agent_running(self, agent_id: str) -> bool:
        """Check if an agent is currently running.

        Args:
            agent_id: Agent identifier

        Returns:
            True if agent is running, False otherwise
        """
        agent = self.get_agent(agent_id)
        if not agent or not agent.pid:
            return False

        try:
            process = psutil.Process(agent.pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def get_agent_stats(self, agent_id: str) -> Optional[Dict]:
        """Get resource usage statistics for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Dictionary with CPU, memory, and runtime stats, or None
        """
        agent = self.get_agent(agent_id)
        if not agent or not agent.pid:
            return None

        try:
            process = psutil.Process(agent.pid)

            return {
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "memory_percent": process.memory_percent(),
                "runtime_seconds": time.time() - agent.start_time,
                "status": process.status(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Failed to get stats for {agent_id}: {e}")
            return None

    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status ('running', 'stopped', 'error')
        """
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self._save_agent_states()
            logger.debug(f"Updated {agent_id} status to {status}")

    def stop_agent(self, agent_id: str, timeout: int = 10) -> bool:
        """Stop a running agent gracefully.

        Args:
            agent_id: Agent identifier
            timeout: Timeout in seconds for graceful shutdown

        Returns:
            True if agent was stopped, False otherwise
        """
        agent = self.get_agent(agent_id)
        if not agent or not agent.pid:
            logger.warning(f"Agent {agent_id} not found or has no PID")
            return False

        try:
            process = psutil.Process(agent.pid)

            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=timeout)
            except psutil.TimeoutExpired:
                # Force kill if graceful termination fails
                logger.warning(f"Agent {agent_id} did not terminate gracefully, forcing kill")
                process.kill()
                process.wait(timeout=5)

            self.update_agent_status(agent_id, "stopped")
            logger.info(f"Stopped agent: {agent_id}")
            return True

        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            return False

    def stop_all_agents(self, timeout: int = 10) -> int:
        """Stop all running agents.

        Args:
            timeout: Timeout in seconds for each agent

        Returns:
            Number of agents successfully stopped
        """
        stopped_count = 0
        for agent_id in list(self.agents.keys()):
            if self.stop_agent(agent_id, timeout):
                stopped_count += 1

        return stopped_count

    def cleanup_dead_agents(self) -> int:
        """Remove dead agents from the registry.

        Returns:
            Number of dead agents removed
        """
        dead_agents = []

        for agent_id, agent in self.agents.items():
            if agent.pid and not self.is_agent_running(agent_id):
                dead_agents.append(agent_id)

        for agent_id in dead_agents:
            self.unregister_agent(agent_id)

        if dead_agents:
            logger.info(f"Cleaned up {len(dead_agents)} dead agents")

        return len(dead_agents)
