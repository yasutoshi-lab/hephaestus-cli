"""Log streaming and viewing utilities for Hephaestus-CLI.

This module provides functionality to stream and view agent logs in real-time.
"""

import time
import logging
from pathlib import Path
from typing import Optional, List, Set
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


class LogStreamer:
    """Stream logs from one or more agents in real-time."""

    def __init__(self, work_dir: Path):
        """Initialize LogStreamer.

        Args:
            work_dir: Path to hephaestus-work directory
        """
        self.work_dir = work_dir
        self.log_dir = work_dir / "logs"
        self.file_positions: dict = {}

    def get_agent_log_file(self, agent_name: str) -> Optional[Path]:
        """Get log file path for an agent.

        Args:
            agent_name: Agent name (master, worker-1, worker-2, etc.)

        Returns:
            Path to log file or None if not found
        """
        # Normalize agent name
        agent_name = agent_name.lower()

        if agent_name == "master":
            log_file = self.log_dir / "master.log"
        elif agent_name.startswith("worker"):
            # Extract worker number
            worker_num = agent_name.replace("worker-", "").replace("worker", "")
            log_file = self.log_dir / f"worker_{worker_num}.log"
        elif agent_name == "system":
            log_file = self.log_dir / "system.log"
        elif agent_name == "communication":
            log_file = self.log_dir / "communication.log"
        else:
            console.print(f"[yellow]Unknown agent: {agent_name}[/yellow]")
            return None

        return log_file if log_file.exists() else None

    def get_all_log_files(self) -> List[Path]:
        """Get all available log files.

        Returns:
            List of log file paths
        """
        if not self.log_dir.exists():
            return []

        log_files = []
        for log_file in self.log_dir.glob("*.log"):
            log_files.append(log_file)

        return sorted(log_files)

    def read_new_lines(self, log_file: Path) -> List[str]:
        """Read new lines from a log file since last read.

        Args:
            log_file: Path to log file

        Returns:
            List of new lines
        """
        if not log_file.exists():
            return []

        try:
            # Get current file position
            current_pos = self.file_positions.get(str(log_file), 0)

            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Seek to last read position
                f.seek(current_pos)

                # Read new lines
                new_lines = f.readlines()

                # Update position
                self.file_positions[str(log_file)] = f.tell()

                return new_lines

        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
            return []

    def stream_logs(self, agent_names: Optional[List[str]] = None, follow: bool = True):
        """Stream logs from specified agents.

        Args:
            agent_names: List of agent names to stream. If None, stream all.
            follow: If True, continuously follow the logs (like tail -f)
        """
        # Determine which log files to stream
        if agent_names:
            log_files = []
            for agent_name in agent_names:
                log_file = self.get_agent_log_file(agent_name)
                if log_file:
                    log_files.append(log_file)
        else:
            log_files = self.get_all_log_files()

        if not log_files:
            console.print("[yellow]No log files found.[/yellow]")
            return

        # Display header
        if len(log_files) == 1:
            console.print(Panel(
                f"[cyan]Streaming logs from:[/cyan] {log_files[0].name}",
                title="Log Stream",
                border_style="cyan"
            ))
        else:
            file_list = "\n".join([f"- {f.name}" for f in log_files])
            console.print(Panel(
                f"[cyan]Streaming logs from:[/cyan]\n{file_list}",
                title="Log Stream",
                border_style="cyan"
            ))

        console.print("[yellow]Press Ctrl+C to stop streaming[/yellow]\n")

        try:
            # Initial read to get to the end of files
            for log_file in log_files:
                if log_file.exists():
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, 2)  # Seek to end
                        self.file_positions[str(log_file)] = f.tell()

            # Continuously stream new lines
            while follow:
                has_output = False

                for log_file in log_files:
                    new_lines = self.read_new_lines(log_file)
                    if new_lines:
                        has_output = True
                        # Determine agent name for display
                        agent_name = self._get_agent_name_from_log_file(log_file)
                        color = self._get_agent_color(agent_name)

                        for line in new_lines:
                            line = line.rstrip()
                            if line:
                                console.print(f"[{color}][{agent_name}][/{color}] {line}")

                if not has_output:
                    # Sleep briefly if no new output
                    time.sleep(0.5)

        except KeyboardInterrupt:
            console.print("\n[yellow]Log streaming stopped[/yellow]")

    def tail_logs(self, agent_name: str, lines: int = 50):
        """Display last N lines from an agent's log.

        Args:
            agent_name: Agent name
            lines: Number of lines to display
        """
        log_file = self.get_agent_log_file(agent_name)
        if not log_file:
            console.print(f"[red]Log file not found for agent: {agent_name}[/red]")
            return

        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                last_lines = all_lines[-lines:]

            # Display header
            console.print(Panel(
                f"[cyan]Last {len(last_lines)} lines from:[/cyan] {log_file.name}",
                title=f"{agent_name} Log",
                border_style="cyan"
            ))

            # Display lines
            color = self._get_agent_color(agent_name)
            for line in last_lines:
                line = line.rstrip()
                if line:
                    console.print(f"[{color}]{line}[/{color}]")

        except Exception as e:
            console.print(f"[red]Error reading log file: {e}[/red]")

    def _get_agent_name_from_log_file(self, log_file: Path) -> str:
        """Extract agent name from log file path.

        Args:
            log_file: Path to log file

        Returns:
            Agent name
        """
        name = log_file.stem  # filename without extension

        if name == "master":
            return "Master"
        elif name.startswith("worker_"):
            worker_num = name.replace("worker_", "")
            return f"Worker-{worker_num}"
        elif name == "system":
            return "System"
        elif name == "communication":
            return "Comm"
        else:
            return name.capitalize()

    def _get_agent_color(self, agent_name: str) -> str:
        """Get color for agent based on name.

        Args:
            agent_name: Agent name

        Returns:
            Rich color name
        """
        agent_name = agent_name.lower()

        if "master" in agent_name:
            return "bright_cyan"
        elif "worker" in agent_name:
            return "bright_green"
        elif "system" in agent_name:
            return "bright_yellow"
        elif "comm" in agent_name:
            return "bright_magenta"
        else:
            return "white"

    def show_log_summary(self):
        """Display a summary of all available logs."""
        log_files = self.get_all_log_files()

        if not log_files:
            console.print("[yellow]No log files found.[/yellow]")
            return

        table = Table(title="Available Logs")
        table.add_column("Agent", style="cyan")
        table.add_column("Log File", style="green")
        table.add_column("Size", style="yellow")
        table.add_column("Last Modified", style="magenta")

        for log_file in log_files:
            agent_name = self._get_agent_name_from_log_file(log_file)
            size = log_file.stat().st_size
            size_str = self._format_size(size)
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(log_file.stat().st_mtime))

            table.add_row(agent_name, log_file.name, size_str, mtime)

        console.print(table)

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
