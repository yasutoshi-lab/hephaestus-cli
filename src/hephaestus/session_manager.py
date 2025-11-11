"""Tmux session management for Hephaestus.

This module handles creation, management, and destruction of tmux sessions
for running Master and Worker agents.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, List
import libtmux
from libtmux.pane import PaneDirection

from .config import Config, AGENT_README_FILES
from .agent_controller import AgentController

logger = logging.getLogger(__name__)


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
        self.server = libtmux.Server()
        self.agent_controller = AgentController(config, work_dir)

    def session_exists(self) -> bool:
        """Check if the tmux session exists.

        Returns:
            True if session exists, False otherwise
        """
        try:
            session = self.server.find_where({"session_name": self.session_name})
            return session is not None
        except Exception as e:
            logger.warning(f"Error checking session existence: {e}")
            return False

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
            logger.error(f"Failed to create session: {e}", exc_info=True)
            raise

    def _start_agent_in_pane(self, pane: libtmux.Pane, agent_type: str, agent_id: int) -> None:
        """Start an agent (claude) in a tmux pane.

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
            agent_work_dir = self.work_dir / ".claude" / "master"
        else:
            agent_work_dir = self.work_dir / ".claude" / "worker"

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

        # Start claude
        command = self.config.master.command if agent_type == "master" else self.config.workers.command
        args = self.config.master.args if agent_type == "master" else self.config.workers.args

        # Build command with arguments
        cmd_parts = [command] + args
        full_command = " ".join(cmd_parts)

        # Start the agent
        pane.send_keys(full_command)

        logger.info(f"Started {agent_name} in pane {pane.id}")

        # Inject persona after a brief delay to allow claude to start
        import time
        time.sleep(3)  # Wait for claude to initialize
        self._inject_persona(pane, agent_type, agent_name)

    def _inject_persona(self, pane: libtmux.Pane, agent_type: str, agent_name: str) -> None:
        """Inject persona configuration into agent on startup.

        Args:
            pane: Tmux pane object
            agent_type: Type of agent ('master' or 'worker')
            agent_name: Display name of the agent
        """
        try:
            # Get README filename based on agent type
            readme_filename = AGENT_README_FILES.get(self.config.agent_type, "CLAUDE.md")

            # Load persona from agent-specific README file
            if agent_type == "master":
                persona_file = self.work_dir / ".claude" / "master" / readme_filename
            else:
                persona_file = self.work_dir / ".claude" / "worker" / readme_filename

            if not persona_file.exists():
                logger.warning(f"Persona file not found: {persona_file}")
                return

            # Read persona content
            with open(persona_file, 'r', encoding='utf-8') as f:
                persona_content = f.read()

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
            simple_prompt = f"Initialize as {agent_name}. Acknowledge your role as defined in {readme_filename} and confirm you are ready to operate according to your role description."
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
        if not self.session_exists():
            raise RuntimeError(f"Session {self.session_name} does not exist")

        try:
            # Use subprocess to attach (this will take over the terminal)
            subprocess.run(["tmux", "attach-session", "-t", self.session_name])
        except Exception as e:
            logger.error(f"Failed to attach to session: {e}", exc_info=True)
            raise

    def kill_session(self) -> None:
        """Kill the tmux session and all agents.

        This will gracefully stop all agents and destroy the session.
        """
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
