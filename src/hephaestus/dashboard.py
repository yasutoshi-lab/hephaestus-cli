"""Real-time TUI dashboard for monitoring Hephaestus agents.

This module provides a Textual-based terminal UI for visualizing
agent status, tasks, and communications in real-time.
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Log
from textual.reactive import reactive
from textual import work
from textual.worker import Worker

from .config import Config, ConfigManager
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class AgentStatusWidget(Static):
    """Widget displaying individual agent status."""

    agent_name = reactive("")
    status = reactive("Unknown")
    current_task = reactive("Idle")

    def __init__(self, agent_name: str, **kwargs):
        super().__init__(**kwargs)
        self.agent_name = agent_name

    def render(self) -> str:
        """Render the agent status."""
        status_emoji = {
            "Active": "🟢",
            "Idle": "🟡",
            "Error": "🔴",
            "Unknown": "⚪"
        }

        emoji = status_emoji.get(self.status, "⚪")

        return f"""[bold]{emoji} {self.agent_name}[/bold]
Status: {self.status}
Task: {self.current_task}"""


class TasksTableWidget(Static):
    """Widget displaying tasks table."""

    def __init__(self, work_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.work_dir = work_dir
        self.table = DataTable()

    def compose(self) -> ComposeResult:
        """Compose the tasks table."""
        self.table.add_columns("ID", "Status", "Priority", "Assigned To")
        yield self.table

    def update_tasks(self, tasks: List[Dict]):
        """Update the tasks table with new data."""
        self.table.clear()
        for task in tasks:
            self.table.add_row(
                task.get("id", "N/A"),
                task.get("status", "Unknown"),
                task.get("priority", "N/A"),
                task.get("assigned_to", "N/A")
            )


class CommunicationLogWidget(Static):
    """Widget displaying agent communication log."""

    def __init__(self, work_dir: Path, **kwargs):
        super().__init__(**kwargs)
        self.work_dir = work_dir
        self.log = Log(highlight=True, max_lines=100)

    def compose(self) -> ComposeResult:
        """Compose the communication log."""
        yield self.log

    def add_message(self, message: str):
        """Add a message to the communication log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.write_line(f"[dim]{timestamp}[/dim] {message}")


class HephaestusDashboard(App):
    """Hephaestus real-time monitoring dashboard."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #agents-container {
        height: auto;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    #tasks-container {
        height: 15;
        border: solid $secondary;
        margin: 1;
        padding: 1;
    }

    #communication-container {
        height: 1fr;
        border: solid $accent;
        margin: 1;
        padding: 1;
    }

    AgentStatusWidget {
        width: 1fr;
        height: auto;
        border: solid $primary-lighten-2;
        padding: 1;
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, config: Config, work_dir: Path):
        super().__init__()
        self.config = config
        self.work_dir = work_dir
        self.session_manager = SessionManager(config, work_dir)
        self.agent_widgets: Dict[str, AgentStatusWidget] = {}
        self.update_worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        """Compose the dashboard UI."""
        yield Header(show_clock=True)

        # Agents status section
        with Container(id="agents-container"):
            yield Static("[bold]Agent Status[/bold]", classes="section-title")
            with Horizontal():
                # Master agent
                master_widget = AgentStatusWidget("Master Agent")
                self.agent_widgets["master"] = master_widget
                yield master_widget

                # Worker agents
                for i in range(1, self.config.workers.count + 1):
                    worker_name = f"Worker-{i}"
                    worker_widget = AgentStatusWidget(worker_name)
                    self.agent_widgets[f"worker-{i}"] = worker_widget
                    yield worker_widget

        # Tasks table section
        with Container(id="tasks-container"):
            yield Static("[bold]Tasks Overview[/bold]", classes="section-title")
            self.tasks_widget = TasksTableWidget(self.work_dir)
            yield self.tasks_widget

        # Communication log section
        with Container(id="communication-container"):
            yield Static("[bold]Communication Log[/bold]", classes="section-title")
            self.comm_widget = CommunicationLogWidget(self.work_dir)
            yield self.comm_widget

        yield Footer()

    def on_mount(self) -> None:
        """Start monitoring when the dashboard is mounted."""
        self.update_worker = self.update_dashboard()

    @work(exclusive=True, thread=True)
    def update_dashboard(self):
        """Background worker to update dashboard periodically."""
        while True:
            try:
                # Update agent status
                self.call_from_thread(self._update_agents)

                # Update tasks
                self.call_from_thread(self._update_tasks)

                # Update communication log
                self.call_from_thread(self._update_communication)

            except Exception as e:
                logger.error(f"Dashboard update error: {e}")

            # Update every 2 seconds
            import time
            time.sleep(2)

    def _update_agents(self):
        """Update agent status widgets."""
        # Check if session is active
        if not self.session_manager.session_exists():
            for widget in self.agent_widgets.values():
                widget.status = "Unknown"
                widget.current_task = "Session not running"
            return

        # Check master agent
        master_widget = self.agent_widgets.get("master")
        if master_widget:
            # Check master log for activity
            master_log = self.work_dir / "logs" / "master.log"
            if master_log.exists():
                master_widget.status = "Active"
                # Try to read current task from progress tracking
                progress_file = self.work_dir / "progress" / "master.json"
                if progress_file.exists():
                    try:
                        with open(progress_file) as f:
                            progress = json.load(f)
                            master_widget.current_task = progress.get("current_task", "Idle")
                    except:
                        master_widget.current_task = "Active"
            else:
                master_widget.status = "Unknown"

        # Check worker agents
        for i in range(1, self.config.workers.count + 1):
            worker_key = f"worker-{i}"
            worker_widget = self.agent_widgets.get(worker_key)
            if worker_widget:
                # Check worker log for activity
                worker_log = self.work_dir / "logs" / f"worker_{i}.log"
                if worker_log.exists():
                    worker_widget.status = "Active"
                    # Check for assigned tasks
                    comm_dir = self.work_dir / "communication" / "master_to_worker" / worker_key
                    if comm_dir.exists():
                        task_files = list(comm_dir.glob("*_task.md"))
                        if task_files:
                            # Get the most recent task
                            latest_task = sorted(task_files)[-1]
                            worker_widget.current_task = f"Executing: {latest_task.stem}"
                        else:
                            worker_widget.current_task = "Idle"
                    else:
                        worker_widget.current_task = "Idle"
                else:
                    worker_widget.status = "Unknown"

    def _update_tasks(self):
        """Update tasks table."""
        tasks = []

        # Read tasks from all status directories
        for status in ["pending", "in_progress", "completed"]:
            task_dir = self.work_dir / "tasks" / status
            if task_dir.exists():
                for task_file in task_dir.glob("*.yaml"):
                    try:
                        import yaml
                        with open(task_file) as f:
                            task_data = yaml.safe_load(f)
                            tasks.append({
                                "id": task_data.get("id", task_file.stem),
                                "status": status,
                                "priority": task_data.get("priority", "N/A"),
                                "assigned_to": task_data.get("assigned_to", "N/A")
                            })
                    except Exception as e:
                        logger.debug(f"Error reading task {task_file}: {e}")

        # Update the table
        if tasks:
            self.tasks_widget.update_tasks(tasks)

    def _update_communication(self):
        """Update communication log with recent messages."""
        comm_log = self.work_dir / "logs" / "communication.log"
        if comm_log.exists():
            try:
                # Read last 10 lines
                with open(comm_log, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-10:]

                    # Add new lines to the log widget
                    for line in recent_lines:
                        if line.strip():
                            self.comm_widget.add_message(line.strip())
            except Exception as e:
                logger.debug(f"Error reading communication log: {e}")

    def action_refresh(self):
        """Manually refresh the dashboard."""
        self._update_agents()
        self._update_tasks()
        self._update_communication()


def run_dashboard(config: Config, work_dir: Path):
    """Run the Hephaestus dashboard.

    Args:
        config: Configuration object
        work_dir: Path to hephaestus-work directory
    """
    app = HephaestusDashboard(config, work_dir)
    app.run()
