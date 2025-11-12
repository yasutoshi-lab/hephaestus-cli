"""Tmux session management for Hephaestus.

This module handles creation, management, and destruction of tmux sessions
for running Master and Worker agents. When tmux isn't usable (common inside
restricted sandboxes), it falls back to a headless mode that keeps agents
alive as background processes and exposes their logs via the existing log
viewer.
"""

import json
import logging
import os
import shutil
import signal
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Optional, List, Dict

import libtmux
from libtmux.pane import PaneDirection
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .config import Config, AGENT_README_FILES
from .utils.file_utils import get_agent_directory_name
from .agent_controller import AgentController

logger = logging.getLogger(__name__)

HEADLESS_AGENT_SCRIPT = r"""
import json
import os
import pathlib
import signal
import subprocess
import time

stop = False


def _stop_handler(*_args):
    global stop
    stop = True


signal.signal(signal.SIGTERM, _stop_handler)
signal.signal(signal.SIGINT, _stop_handler)

spec = json.loads(os.environ["HEPHAESTUS_AGENT_SPEC"])
log_path = pathlib.Path(spec["log_file"])
log_path.parent.mkdir(parents=True, exist_ok=True)
log_file = log_path.open("a", encoding="utf-8")

timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
log_file.write(f"[bootstrap] {spec['agent_name']} started at {timestamp}\n")

persona = spec.get("persona")
if persona:
    log_file.write("[persona]\n")
    log_file.write(persona)
    log_file.write("\n[persona-end]\n")
    log_file.flush()

command = spec.get("command")
work_dir = spec["work_dir"]


def _run_command() -> bool:
    if not command:
        return False

    try:
        proc = subprocess.Popen(
            ["bash", "-lc", command],
            cwd=work_dir,
            stdout=log_file,
            stderr=log_file,
        )
    except FileNotFoundError:
        log_file.write(f"[error] Command not found: {command}\n")
        log_file.flush()
        return False

    returncode = proc.wait()
    log_file.write(f"[exit] {spec['agent_name']} exited with code {returncode}\n")
    log_file.flush()
    return True


ran_command = _run_command()

if not ran_command:
    log_file.write(f"[fallback] {spec['agent_name']} running heartbeat mode.\n")
    log_file.flush()
    while not stop:
        log_file.write(
            f"[heartbeat] {spec['agent_name']} alive at {time.strftime('%H:%M:%S')}\n"
        )
        log_file.flush()
        time.sleep(5)

shutdown_time = time.strftime("%Y-%m-%d %H:%M:%S")
log_file.write(f"[shutdown] {spec['agent_name']} stopped at {shutdown_time}\n")
log_file.flush()
log_file.close()
"""


class SessionManager:
    """Manager for tmux sessions and agent panes."""

    def __init__(self, config: Config, work_dir: Path):
        """Initialize SessionManager.

        Args:
            config: Configuration object
            work_dir: Path to .hephaestus-work directory
        """
        self.config = config
        self.work_dir = work_dir
        self.session_name = config.tmux.session_name
        self.console = Console()
        self.headless_state_file = self.work_dir / "cache" / "headless_session.json"
        self.tmux_available = shutil.which("tmux") is not None
        self._tmux_failure_reason: Optional[str] = None
        self.mode = "tmux" if self.tmux_available else "headless"
        self.server = libtmux.Server() if self.tmux_available else None
        self.agent_controller = AgentController(config, work_dir)
        self.agent_dir_name = get_agent_directory_name(config.agent_type)
        self.agent_dir = self.work_dir / self.agent_dir_name

        if not self.tmux_available:
            self._tmux_failure_reason = "tmux executable not found"

    def session_exists(self) -> bool:
        """Check if the tmux session exists.

        Returns:
            True if session exists, False otherwise
        """
        if self.tmux_available and self.server is not None:
            try:
                session = self.server.find_where({"session_name": self.session_name})
                if session is not None:
                    return True
            except Exception as e:
                logger.warning(f"Error checking session existence: {e}")

        return self._headless_session_exists()

    def create_session(self) -> None:
        """Create a new tmux session with Master and Worker panes.

        Creates a tmux session with panes for:
        - 1 Master agent
        - N Worker agents (based on config)

        Each pane runs a claude instance.
        """
        if self.session_exists():
            logger.warning(f"Session {self.session_name} already exists")
            return

        if self.mode == "headless":
            logger.info("tmux unavailable; starting headless session")
            self._start_headless_session()
            return

        try:
            # Create new session
            session = self.server.new_session(
                session_name=self.session_name,
                window_name="hephaestus",
                attach=False,
            )
            logger.info(f"Created tmux session: {self.session_name}")

            # Enable mouse mode for easier pane navigation
            session.set_option("mouse", "on", global_=True)

            # Get the default window
            window = session.windows[0]

            # Enable pane border titles (window options)
            window.set_window_option("pane-border-status", "top")
            window.set_window_option("pane-border-format", "#{pane_index}: #{pane_title}")
            logger.info("Enabled mouse mode and pane border titles")

            # Number of total panes needed (1 Master + N Workers)
            total_panes = 1 + self.config.workers.count

            # Create panes for agents
            panes: List[libtmux.Pane] = []

            # First pane is already created (Master)
            master_pane = window.panes[0]
            panes.append(master_pane)

            # Create additional panes for workers
            # Use calculated percentages to ensure equal distribution of space
            for i in range(self.config.workers.count):
                # Calculate percentage for each split to ensure equal pane sizes
                # Each time we split, we want the new pane to be 1/(remaining_panes) of current space
                remaining_panes = self.config.workers.count - i
                percentage = int(100 / (remaining_panes + 1))

                # Split the master pane with calculated percentage
                # Using split() with PaneDirection.Right (vertical split, side-by-side)
                pane = panes[0].split(
                    direction=PaneDirection.Right,
                    attach=False,
                    size=f"{percentage}%"
                )
                panes.append(pane)

            # Apply layout (this will rearrange panes according to the configured layout)
            window.select_layout(self.config.tmux.layout)

            # Start agents in each pane
            # Master pane
            self._start_agent_in_pane(panes[0], "master", 0)

            # Worker panes
            for i in range(self.config.workers.count):
                self._start_agent_in_pane(panes[i + 1], "worker", i + 1)

            logger.info(f"Started {total_panes} agents in session {self.session_name}")

        except Exception as e:
            if self._should_fallback_to_headless(e):
                self._switch_to_headless(e)
                self._start_headless_session()
                return

            logger.error(f"Failed to create session: {e}", exc_info=True)
            raise

    def _start_agent_in_pane(self, pane: libtmux.Pane, agent_type: str, agent_id: int) -> None:
        """Start an agent in a tmux pane with agent-type specific persona injection.

        For Codex agents, persona is injected via command-line argument at startup.
        For Claude/Gemini agents, persona is injected post-startup via echo commands.

        Args:
            pane: Tmux pane object
            agent_type: Type of agent ('master' or 'worker')
            agent_id: Agent identifier (0 for master, 1+ for workers)
        """
        # Determine agent name
        if agent_type == "master":
            agent_name = "Master Agent"
            log_file = self.work_dir / "logs" / "master.log"
        else:
            agent_name = f"Worker-{agent_id}"
            log_file = self.work_dir / "logs" / f"worker_{agent_id}.log"

        # Create log directory if it doesn't exist
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Set pane title using tmux's select-pane command
        pane.select_pane()
        pane.cmd("select-pane", "-T", agent_name)

        # Determine agent working directory
        if agent_type == "master":
            agent_work_dir = self.agent_dir / "master"
        else:
            agent_work_dir = self.agent_dir / "worker"

        # Change to agent-specific directory
        pane.send_keys(f"cd {agent_work_dir}")

        # Display agent information
        pane.send_keys("clear")
        pane.send_keys(f"echo '═══════════════════════════════════════'")
        pane.send_keys(f"echo ' Hephaestus Agent: {agent_name}'")
        pane.send_keys(f"echo '═══════════════════════════════════════'")
        pane.send_keys(f"echo 'Log file: {log_file}'")
        pane.send_keys(f"echo 'Work directory: {self.work_dir}'")
        pane.send_keys(f"echo '═══════════════════════════════════════'")
        pane.send_keys("")

        # Start agent with agent-type specific handling
        command = self.config.master.command if agent_type == "master" else self.config.workers.command
        args = self.config.master.args if agent_type == "master" else self.config.workers.args

        # Agent-type specific persona injection
        import time

        if self.config.agent_type == "codex":
            # For Codex: inject persona at startup via command argument
            persona_content = self._load_persona(agent_type)
            if persona_content:
                # Create initialization prompt (same as _inject_persona)
                init_prompt = f"""You are now initializing as {agent_name} in the Hephaestus multi-agent system.

【CRITICAL ROLE ASSIGNMENT】
Your role is strictly defined. You MUST adhere to this role at all times.
Deviating from this role is NOT permitted.

{persona_content}

【CONFIRMATION】
Please confirm your role by responding: "✓ {agent_name} initialized and ready. Role acknowledged."

After confirmation, you will begin receiving tasks according to your role."""

                # Create a temporary script to launch codex with persona
                # This avoids complex shell escaping issues
                import tempfile
                import os

                # Create a temporary script file
                script_fd, script_path = tempfile.mkstemp(
                    suffix=".sh",
                    dir=agent_work_dir,
                    prefix=".codex_init_",
                    text=True
                )

                try:
                    # Write the script that launches codex with persona
                    with os.fdopen(script_fd, 'w') as script_file:
                        script_file.write("#!/bin/bash\n")
                        script_file.write(f"PERSONA=$(cat << 'PERSONA_EOF'\n")
                        script_file.write(init_prompt)
                        script_file.write("\nPERSONA_EOF\n")
                        script_file.write(")\n")
                        script_file.write(f'{command} "$PERSONA" {" ".join(args)}\n')

                    # Make the script executable
                    os.chmod(script_path, 0o755)

                    # Start the agent by running the script
                    full_command = script_path

                    logger.info(f"Starting {agent_name} with persona injection via command argument")
                except Exception as e:
                    logger.error(f"Failed to create initialization script: {e}")
                    # Fallback to basic command
                    cmd_parts = [command] + args
                    full_command = " ".join(cmd_parts)
            else:
                logger.warning(f"Persona file not found for {agent_type}, starting without persona")
                cmd_parts = [command] + args
                full_command = " ".join(cmd_parts)

            # Start the agent
            pane.send_keys(full_command)
            logger.info(f"Started {agent_name} in pane {pane.id}")

        else:
            # For Claude/Gemini: use traditional post-startup persona injection
            # Build command with arguments
            cmd_parts = [command] + args
            full_command = " ".join(cmd_parts)

            # Start the agent
            pane.send_keys(full_command)

            logger.info(f"Started {agent_name} in pane {pane.id}")

            # Inject persona after a brief delay to allow agent to start
            time.sleep(3)  # Wait for agent to initialize
            self._inject_persona(pane, agent_type, agent_name)

    def _inject_persona(self, pane: libtmux.Pane, agent_type: str, agent_name: str) -> None:
        """Inject persona configuration into agent on startup.

        Args:
            pane: Tmux pane object
            agent_type: Type of agent ('master' or 'worker')
            agent_name: Display name of the agent
        """
        try:
            persona_content = self._load_persona(agent_type)
            if not persona_content:
                logger.warning(f"Persona file not found for {agent_type}")
                return

            # Create initialization prompt
            init_prompt = f"""You are now initializing as {agent_name} in the Hephaestus multi-agent system.

【CRITICAL ROLE ASSIGNMENT】
Your role is strictly defined. You MUST adhere to this role at all times.
Deviating from this role is NOT permitted.

{persona_content}

【CONFIRMATION】
Please confirm your role by responding: "✓ {agent_name} initialized and ready. Role acknowledged."

After confirmation, you will begin receiving tasks according to your role."""

            # Send the initialization prompt
            # First, clear any existing input
            pane.send_keys("C-c")
            import time
            time.sleep(0.5)

            # Split the prompt into smaller chunks to avoid tmux limitations
            lines = init_prompt.split('\n')
            chunk_size = 5  # Send 5 lines at a time

            for i in range(0, len(lines), chunk_size):
                chunk = '\n'.join(lines[i:i+chunk_size])
                # Escape special characters for tmux
                escaped_chunk = chunk.replace('"', '\\"').replace('$', '\\$')
                pane.send_keys(f'echo "{escaped_chunk}"')
                time.sleep(0.2)

            # Send the actual prompt to agent by typing it
            # Use a simpler version that's easier to send
            readme_filename = AGENT_README_FILES.get(self.config.agent_type, "CLAUDE.md")
            simple_prompt = (
                f"Initialize as {agent_name}. Acknowledge your role as defined in {readme_filename} "
                "and confirm you are ready to operate according to your role description."
            )
            pane.send_keys(simple_prompt)
            time.sleep(0.5)
            pane.send_keys("Enter")

            logger.info(f"Injected persona for {agent_name}")

        except Exception as e:
            logger.error(f"Failed to inject persona for {agent_name}: {e}", exc_info=True)

    def attach(self) -> None:
        """Attach to the existing tmux session.

        This will switch the terminal to the tmux session.
        """
        if self.mode == "headless":
            if not self._headless_session_exists():
                raise RuntimeError(f"Session {self.session_name} does not exist")
            self._attach_headless_dashboard()
            return

        if not self.session_exists():
            raise RuntimeError(f"Session {self.session_name} does not exist")

        try:
            # Use subprocess to attach (this will take over the terminal)
            subprocess.run(["tmux", "attach-session", "-t", self.session_name], check=True)
        except Exception as e:
            if self._should_fallback_to_headless(e):
                self._switch_to_headless(e)
                if self._headless_session_exists():
                    self._attach_headless_dashboard()
                    return

            logger.error(f"Failed to attach to session: {e}", exc_info=True)
            raise

    def kill_session(self) -> None:
        """Kill the tmux session and all agents.

        This will gracefully stop all agents and destroy the session.
        """
        headless_running = self._headless_session_exists()

        if self.mode == "headless" or (not self.tmux_available and headless_running):
            if headless_running:
                self._stop_headless_agents()
            else:
                logger.warning(f"Session {self.session_name} does not exist")
            return

        if not self.tmux_available or self.server is None:
            logger.warning("tmux is not available; nothing to kill")
            return

        if not self.session_exists():
            logger.warning(f"Session {self.session_name} does not exist")
            return

        try:
            session = self.server.find_where({"session_name": self.session_name})
            if session:
                # Save session state before killing
                self._save_session_state()

                # Kill the session
                session.kill_session()
                logger.info(f"Killed session: {self.session_name}")
                self._remove_headless_state()
        except Exception as e:
            logger.error(f"Failed to kill session: {e}", exc_info=True)
            raise

    def _save_session_state(self) -> None:
        """Save the current state of the session before termination."""
        try:
            state_file = self.work_dir / "cache" / "last_session_state.json"
            state_file.parent.mkdir(parents=True, exist_ok=True)

            import json
            import time

            state = {
                "session_name": self.session_name,
                "terminated_at": time.time(),
                "worker_count": self.config.workers.count,
            }

            with open(state_file, "w") as f:
                json.dump(state, f, indent=2)

            logger.info(f"Saved session state to {state_file}")
        except Exception as e:
            logger.warning(f"Failed to save session state: {e}")

    def list_panes(self) -> List[dict]:
        """List all panes in the session.

        Returns:
            List of pane information dictionaries
        """
        if self._headless_session_exists() and (self.mode == "headless" or not self.tmux_available):
            state = self._load_headless_state()
            if not state:
                return []
            panes = []
            for idx, agent in enumerate(state.get("agents", [])):
                panes.append(
                    {
                        "id": agent["name"],
                        "window": "headless",
                        "active": idx == 0,
                        "width": None,
                        "height": None,
                    }
                )
            return panes

        if not self.tmux_available or self.server is None:
            return []

        if not self.session_exists():
            return []

        try:
            session = self.server.find_where({"session_name": self.session_name})
            panes = []

            for window in session.windows:
                for pane in window.panes:
                    panes.append(
                        {
                            "id": pane.id,
                            "window": window.name,
                            "active": pane.get("pane_active") == "1",
                            "width": pane.get("pane_width"),
                            "height": pane.get("pane_height"),
                        }
                    )

            return panes
        except Exception as e:
            logger.error(f"Failed to list panes: {e}", exc_info=True)
            return []

    def get_session_info(self) -> Optional[dict]:
        """Get information about the current session.

        Returns:
            Dictionary with session information, or None if session doesn't exist
        """
        if self._headless_session_exists() and (self.mode == "headless" or not self.tmux_available):
            state = self._load_headless_state()
            if not state:
                return None
            return {
                "name": f"{self.session_name}-headless",
                "id": "headless",
                "windows": 1,
                "attached": True,
            }

        if not self.tmux_available or self.server is None:
            return None

        if not self.session_exists():
            return None

        try:
            session = self.server.find_where({"session_name": self.session_name})
            return {
                "name": session.name,
                "id": session.id,
                "windows": len(session.windows),
                "attached": session.get("session_attached") != "0",
            }
        except Exception as e:
            logger.error(f"Failed to get session info: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Headless fallback helpers
    # ------------------------------------------------------------------

    def _should_fallback_to_headless(self, error: Exception) -> bool:
        if isinstance(error, FileNotFoundError):
            return True

        message = str(error)
        keywords = [
            "Operation not permitted",
            "can't connect",
            "No such file or directory",
            "socket not found",
            "tmux executable not found",
        ]
        return any(keyword in message for keyword in keywords)

    def _switch_to_headless(self, error: Exception) -> None:
        self.tmux_available = False
        self.mode = "headless"
        self._tmux_failure_reason = str(error)
        logger.warning("tmux is unavailable (%s). Falling back to headless mode.", error)

    def _build_agent_command(self, agent_type: str) -> str:
        if agent_type == "master":
            command = self.config.master.command
            args = self.config.master.args
        else:
            command = self.config.workers.command
            args = self.config.workers.args

        cmd_parts = [command] + list(args)
        return " ".join(cmd_parts).strip()

    def _load_persona(self, agent_type: str) -> Optional[str]:
        readme_filename = AGENT_README_FILES.get(self.config.agent_type, "CLAUDE.md")
        if agent_type == "master":
            persona_file = self.agent_dir / "master" / readme_filename
        else:
            persona_file = self.agent_dir / "worker" / readme_filename

        if not persona_file.exists():
            return None

        with open(persona_file, "r", encoding="utf-8") as file:
            return file.read()

    def _start_headless_session(self) -> None:
        agents: List[Dict[str, object]] = []

        agent_specs = [("master", 0)]
        agent_specs.extend(("worker", i + 1) for i in range(self.config.workers.count))

        for agent_type, slot in agent_specs:
            if agent_type == "master":
                agent_name = "master"
                log_file = self.work_dir / "logs" / "master.log"
                agent_work_dir = self.agent_dir / "master"
            else:
                agent_name = f"worker-{slot}"
                log_file = self.work_dir / "logs" / f"worker_{slot}.log"
                agent_work_dir = self.agent_dir / "worker"

            log_file.parent.mkdir(parents=True, exist_ok=True)
            agent_work_dir.mkdir(parents=True, exist_ok=True)

            persona = self._load_persona(agent_type)
            command = self._build_agent_command(agent_type)

            process = self._spawn_headless_agent(
                agent_name=agent_name,
                command=command,
                agent_work_dir=agent_work_dir,
                log_file=log_file,
                persona=persona,
            )

            agents.append(
                {
                    "pid": process.pid,
                    "name": agent_name,
                    "type": agent_type,
                    "log_file": str(log_file),
                    "work_dir": str(agent_work_dir),
                }
            )

        self._save_headless_state(agents)

    def _spawn_headless_agent(
        self,
        agent_name: str,
        command: str,
        agent_work_dir: Path,
        log_file: Path,
        persona: Optional[str],
    ) -> subprocess.Popen:
        spec = {
            "agent_name": agent_name,
            "command": command,
            "work_dir": str(agent_work_dir),
            "log_file": str(log_file),
            "persona": persona,
        }

        env = os.environ.copy()
        env["HEPHAESTUS_AGENT_SPEC"] = json.dumps(spec)

        return subprocess.Popen(
            ["python3", "-u", "-c", HEADLESS_AGENT_SCRIPT],
            cwd=str(agent_work_dir),
            env=env,
        )

    def _save_headless_state(self, agents: List[Dict[str, object]]) -> None:
        state = {
            "session_name": self.session_name,
            "created_at": time.time(),
            "agents": agents,
            "mode": "headless",
            "tmux_error": self._tmux_failure_reason,
        }

        self.headless_state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.headless_state_file, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

    def _load_headless_state(self) -> Optional[Dict[str, object]]:
        if not self.headless_state_file.exists():
            return None

        try:
            with open(self.headless_state_file, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as exc:
            logger.warning(f"Failed to load headless session state: {exc}")
            return None

    def _headless_session_exists(self) -> bool:
        state = self._load_headless_state()
        if not state:
            return False

        agents = state.get("agents", [])
        alive = any(self._is_pid_running(agent.get("pid")) for agent in agents)
        if not alive:
            self._remove_headless_state()
        return alive

    def _is_pid_running(self, pid: Optional[int]) -> bool:
        if not pid:
            return False

        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _stop_headless_agents(self) -> None:
        state = self._load_headless_state()
        if not state:
            return

        for agent in state.get("agents", []):
            pid = agent.get("pid")
            if not pid:
                continue
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                continue
            except Exception as exc:
                logger.warning(f"Failed to stop agent {agent.get('name')}: {exc}")

        self._remove_headless_state()

    def _attach_headless_dashboard(self) -> None:
        state = self._load_headless_state()
        if not state:
            raise RuntimeError(f"Session {self.session_name} does not exist")

        reason = self._tmux_failure_reason or "tmux not available"
        info = textwrap.dedent(
            f"""
            tmux is unavailable, so Hephaestus started agents in headless mode.
            Reason: {reason}

            Agents continue to run in the background and stream output to logs.
            Use `hephaestus logs --all -f` to follow combined logs or
            `hephaestus logs -a master` to inspect a specific agent.
            Press Ctrl+C to return to your shell; agents keep running.
            """
        ).strip()

        self.console.print(
            Panel(info, title=f"Headless Session: {self.session_name}", border_style="yellow")
        )

        try:
            with Live(console=self.console, refresh_per_second=0.5) as live:
                while True:
                    latest_state = self._load_headless_state()
                    agents = []
                    if latest_state:
                        agents = latest_state.get("agents", [])
                    table = self._build_headless_table(agents)
                    instructions = Panel(
                        "Tip: run `hephaestus logs --all -f` in another terminal to stream output.",
                        border_style="cyan",
                    )
                    live.update(Group(table, instructions))
                    time.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Detached from headless session[/yellow]")

    def _build_headless_table(self, agents: List[Dict[str, object]]) -> Table:
        table = Table(title="Agents", expand=True)
        table.add_column("Agent")
        table.add_column("PID", justify="right")
        table.add_column("Status")
        table.add_column("Log")

        if not agents:
            table.add_row("-", "-", "inactive", "-")
            return table

        for agent in agents:
            name = agent.get("name", "?")
            pid = agent.get("pid")
            log_path = agent.get("log_file", "")
            status = "running" if self._is_pid_running(pid) else "stopped"
            status_color = "green" if status == "running" else "red"
            table.add_row(name, str(pid or "-"), f"[{status_color}]{status}[/{status_color}]", log_path)

        return table

    def _remove_headless_state(self) -> None:
        if self.headless_state_file.exists():
            try:
                self.headless_state_file.unlink()
            except OSError as exc:
                logger.warning(f"Failed to remove headless state file: {exc}")
