"""Health monitoring for Hephaestus-CLI.

This module provides agent health monitoring, error detection,
and automatic recovery capabilities.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from enum import Enum

from .config import Config
from .agent_controller import AgentController

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Agent health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ErrorType(Enum):
    """Error type enumeration."""

    RATE_LIMIT = "rate_limit"
    CRASH = "crash"
    TIMEOUT = "timeout"
    NETWORK = "network"
    RESOURCE = "resource"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check result."""

    agent_id: str
    status: HealthStatus
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    last_activity: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ErrorRecord:
    """Error record for an agent."""

    agent_id: str
    error_type: ErrorType
    timestamp: float = field(default_factory=time.time)
    error_details: Dict = field(default_factory=dict)
    recovery_attempts: int = 0
    recoverable: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "error_type": self.error_type.value,
            "timestamp": self.timestamp,
            "error_details": self.error_details,
            "recovery_attempts": self.recovery_attempts,
            "recoverable": self.recoverable,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorRecord":
        """Create from dictionary."""
        data["error_type"] = ErrorType(data["error_type"])
        return cls(**data)


class HealthMonitor:
    """Monitor for agent health and recovery."""

    def __init__(self, config: Config, agent_controller: AgentController, work_dir: Path):
        """Initialize HealthMonitor.

        Args:
            config: Configuration object
            agent_controller: Agent controller instance
            work_dir: Path to hephaestus-work directory
        """
        self.config = config
        self.agent_controller = agent_controller
        self.work_dir = work_dir
        self.interval = config.monitoring.health_check_interval
        self.retry_attempts = config.monitoring.retry_attempts
        self.retry_delay = config.monitoring.retry_delay

        self.error_cache_dir = work_dir / "cache" / "error_records"
        self.error_cache_dir.mkdir(parents=True, exist_ok=True)

        self._running = False
        self._health_checks: Dict[str, HealthCheck] = {}
        self._error_records: Dict[str, List[ErrorRecord]] = {}

        self._load_error_records()

    def _load_error_records(self) -> None:
        """Load error records from cache."""
        try:
            for error_file in self.error_cache_dir.glob("*.json"):
                with open(error_file, "r") as f:
                    data = json.load(f)

                agent_id = data.get("agent_id")
                if agent_id:
                    records = [ErrorRecord.from_dict(r) for r in data.get("records", [])]
                    self._error_records[agent_id] = records

            logger.info(f"Loaded error records for {len(self._error_records)} agents")
        except Exception as e:
            logger.warning(f"Failed to load error records: {e}")

    def _save_error_record(self, record: ErrorRecord) -> None:
        """Save error record to cache.

        Args:
            record: ErrorRecord to save
        """
        try:
            agent_id = record.agent_id
            if agent_id not in self._error_records:
                self._error_records[agent_id] = []

            self._error_records[agent_id].append(record)

            # Save to file
            error_file = self.error_cache_dir / f"{agent_id}.json"
            data = {
                "agent_id": agent_id,
                "records": [r.to_dict() for r in self._error_records[agent_id]],
            }

            with open(error_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved error record for {agent_id}")
        except Exception as e:
            logger.warning(f"Failed to save error record: {e}")

    async def check_agent_health(self, agent_id: str) -> HealthCheck:
        """Check health of a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            HealthCheck result
        """
        health_check = HealthCheck(agent_id=agent_id, status=HealthStatus.UNKNOWN)

        try:
            # Check if agent is running
            if not self.agent_controller.is_agent_running(agent_id):
                health_check.status = HealthStatus.UNHEALTHY
                health_check.error = "Agent is not running"
                return health_check

            # Get agent statistics
            stats = self.agent_controller.get_agent_stats(agent_id)
            if not stats:
                health_check.status = HealthStatus.UNKNOWN
                health_check.error = "Could not retrieve agent stats"
                return health_check

            health_check.cpu_percent = stats.get("cpu_percent", 0.0)
            health_check.memory_mb = stats.get("memory_mb", 0.0)

            # Determine health status based on resource usage
            if health_check.cpu_percent > 90 or health_check.memory_mb > 2048:
                health_check.status = HealthStatus.DEGRADED
                health_check.error = "High resource usage"
            else:
                health_check.status = HealthStatus.HEALTHY

            # Check last activity time
            agent = self.agent_controller.get_agent(agent_id)
            if agent:
                health_check.last_activity = agent.start_time

        except Exception as e:
            health_check.status = HealthStatus.UNHEALTHY
            health_check.error = str(e)
            logger.error(f"Health check failed for {agent_id}: {e}")

        self._health_checks[agent_id] = health_check
        return health_check

    async def monitor_agents(self) -> None:
        """Main monitoring loop - runs continuously."""
        self._running = True
        logger.info(f"Starting health monitor (interval: {self.interval}s)")

        while self._running:
            try:
                # Get all registered agents
                agents = self.agent_controller.list_agents()

                # Check health of each agent
                for agent in agents:
                    health_check = await self.check_agent_health(agent.id)

                    if health_check.status == HealthStatus.UNHEALTHY:
                        await self.handle_unhealthy_agent(agent.id, health_check)
                    elif health_check.status == HealthStatus.DEGRADED:
                        logger.warning(f"Agent {agent.id} is degraded: {health_check.error}")

                # Clean up dead agents
                self.agent_controller.cleanup_dead_agents()

                # Wait for next check
                await asyncio.sleep(self.interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(self.interval)

    async def handle_unhealthy_agent(self, agent_id: str, health_check: HealthCheck) -> None:
        """Handle an unhealthy agent.

        Args:
            agent_id: Agent identifier
            health_check: Health check result
        """
        logger.warning(f"Agent {agent_id} is unhealthy: {health_check.error}")

        # Determine error type
        error_type = self._classify_error(health_check.error or "")

        # Create error record
        error_record = ErrorRecord(
            agent_id=agent_id,
            error_type=error_type,
            error_details={
                "message": health_check.error,
                "cpu_percent": health_check.cpu_percent,
                "memory_mb": health_check.memory_mb,
            },
        )

        # Get previous error records for this agent
        previous_errors = self._error_records.get(agent_id, [])
        error_record.recovery_attempts = len([e for e in previous_errors if e.error_type == error_type])

        # Save error record
        self._save_error_record(error_record)

        # Attempt recovery if attempts haven't been exhausted
        if error_record.recovery_attempts < self.retry_attempts:
            await self.attempt_recovery(agent_id, error_record)
        else:
            logger.error(
                f"Agent {agent_id} exceeded recovery attempts ({self.retry_attempts}). Manual intervention required."
            )
            error_record.recoverable = False
            self._save_error_record(error_record)

    def _classify_error(self, error_message: str) -> ErrorType:
        """Classify error based on error message.

        Args:
            error_message: Error message string

        Returns:
            ErrorType classification
        """
        error_lower = error_message.lower()

        if "rate limit" in error_lower or "429" in error_lower:
            return ErrorType.RATE_LIMIT
        elif "timeout" in error_lower:
            return ErrorType.TIMEOUT
        elif "network" in error_lower or "connection" in error_lower:
            return ErrorType.NETWORK
        elif "memory" in error_lower or "cpu" in error_lower:
            return ErrorType.RESOURCE
        elif "crash" in error_lower or "not running" in error_lower:
            return ErrorType.CRASH
        else:
            return ErrorType.UNKNOWN

    async def attempt_recovery(self, agent_id: str, error_record: ErrorRecord) -> bool:
        """Attempt to recover an unhealthy agent.

        Args:
            agent_id: Agent identifier
            error_record: Error record

        Returns:
            True if recovery was successful, False otherwise
        """
        logger.info(
            f"Attempting recovery for {agent_id} (attempt {error_record.recovery_attempts + 1}/{self.retry_attempts})"
        )

        try:
            # Strategy depends on error type
            if error_record.error_type == ErrorType.RATE_LIMIT:
                # Wait before retrying
                logger.info(f"Rate limit detected for {agent_id}, waiting {self.retry_delay * 2}s")
                await asyncio.sleep(self.retry_delay * 2)
                return True

            elif error_record.error_type == ErrorType.CRASH:
                # Try to restart the agent
                logger.info(f"Attempting to restart crashed agent {agent_id}")
                # Note: Actual restart would need to be implemented in session_manager
                # For now, just mark as attempted
                await asyncio.sleep(self.retry_delay)
                return False

            elif error_record.error_type in [ErrorType.TIMEOUT, ErrorType.NETWORK]:
                # Wait and retry
                logger.info(f"Network/timeout issue for {agent_id}, waiting {self.retry_delay}s")
                await asyncio.sleep(self.retry_delay)
                return True

            elif error_record.error_type == ErrorType.RESOURCE:
                # Resource issue - may need manual intervention
                logger.warning(f"Resource issue for {agent_id}, limited recovery options")
                await asyncio.sleep(self.retry_delay)
                return False

            else:
                # Unknown error type
                logger.warning(f"Unknown error type for {agent_id}, default retry")
                await asyncio.sleep(self.retry_delay)
                return False

        except Exception as e:
            logger.error(f"Recovery attempt failed for {agent_id}: {e}")
            return False

    def stop(self) -> None:
        """Stop the health monitor."""
        self._running = False
        logger.info("Stopping health monitor")

    def get_health_status(self, agent_id: Optional[str] = None) -> Dict:
        """Get health status for agents.

        Args:
            agent_id: Optional agent ID to get status for specific agent

        Returns:
            Dictionary with health status information
        """
        if agent_id:
            health_check = self._health_checks.get(agent_id)
            if not health_check:
                return {"agent_id": agent_id, "status": "unknown"}

            return {
                "agent_id": health_check.agent_id,
                "status": health_check.status.value,
                "timestamp": health_check.timestamp,
                "cpu_percent": health_check.cpu_percent,
                "memory_mb": health_check.memory_mb,
                "error": health_check.error,
            }
        else:
            # Return status for all agents
            return {
                agent_id: {
                    "status": hc.status.value,
                    "timestamp": hc.timestamp,
                    "cpu_percent": hc.cpu_percent,
                    "memory_mb": hc.memory_mb,
                    "error": hc.error,
                }
                for agent_id, hc in self._health_checks.items()
            }

    def get_error_history(self, agent_id: str) -> List[Dict]:
        """Get error history for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of error records as dictionaries
        """
        records = self._error_records.get(agent_id, [])
        return [r.to_dict() for r in records]

    def clear_error_history(self, agent_id: Optional[str] = None) -> None:
        """Clear error history.

        Args:
            agent_id: Optional agent ID to clear history for specific agent
        """
        if agent_id:
            if agent_id in self._error_records:
                del self._error_records[agent_id]
                error_file = self.error_cache_dir / f"{agent_id}.json"
                if error_file.exists():
                    error_file.unlink()
                logger.info(f"Cleared error history for {agent_id}")
        else:
            self._error_records.clear()
            for error_file in self.error_cache_dir.glob("*.json"):
                error_file.unlink()
            logger.info("Cleared all error history")
