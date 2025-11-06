"""Hephaestus-CLI: A tmux-based multi-agent CLI tool.

Hephaestus-CLI manages multiple LLM agents (Master + Workers) to execute
complex tasks collaboratively using tmux for process management.
"""

__version__ = "0.1.0"
__author__ = "Hephaestus-CLI Development Team"
__license__ = "MIT"

from .config import Config, ConfigManager
from .agent_controller import AgentController, AgentInfo
from .communication import CommunicationManager, Message
from .task_manager import TaskManager, Task, TaskStatus, TaskPriority
from .health_monitor import HealthMonitor, HealthStatus, ErrorType
from .session_manager import SessionManager

__all__ = [
    "__version__",
    "__author__",
    "__license__",
    "Config",
    "ConfigManager",
    "AgentController",
    "AgentInfo",
    "CommunicationManager",
    "Message",
    "TaskManager",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "HealthMonitor",
    "HealthStatus",
    "ErrorType",
    "SessionManager",
]
