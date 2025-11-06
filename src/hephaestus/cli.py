"""CLI entry point for Hephaestus-CLI.

This module implements the command-line interface using Click.
"""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .utils.logger import setup_logger
from .utils.file_utils import create_directory_structure, get_work_directory, create_agent_config_files
from .config import create_default_config, ConfigManager
from .session_manager import SessionManager
from .agent_communicator import AgentCommunicator
from .task_distributor import TaskDistributor

console = Console()
logger = None  # Will be initialized in commands


def init_logger():
    """Initialize the logger."""
    global logger
    work_dir = get_work_directory()
    log_file = work_dir / "logs" / "system.log" if work_dir.exists() else None
    logger = setup_logger("hephaestus", log_file=log_file)


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="0.1.0", prog_name="hephaestus-cli")
def main(ctx):
    """Hephaestus-CLI: A tmux-based multi-agent CLI tool.

    Manages multiple LLM agents (Master + Workers) to execute complex tasks collaboratively.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command(name="init")
@click.option(
    "--workers",
    "-w",
    default=3,
    type=int,
    help="Number of worker agents (default: 3)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force initialization even if hephaestus-work exists",
)
def init_command(workers: int, force: bool):
    """Initialize hephaestus-work directory in current location.

    Creates the necessary directory structure, configuration file,
    and prepares the environment for agent execution.
    """
    init_logger()

    work_dir = get_work_directory()

    # Check if already initialized
    if work_dir.exists() and not force:
        console.print(
            Panel(
                f"[yellow]hephaestus-work directory already exists at:[/yellow]\n{work_dir}\n\n"
                "Use --force to reinitialize.",
                title="Already Initialized",
                border_style="yellow",
            )
        )
        sys.exit(1)

    try:
        # Create directory structure
        console.print("[cyan]Creating hephaestus-work directory structure...[/cyan]")
        create_directory_structure()

        # Create default config
        console.print("[cyan]Creating configuration file...[/cyan]")
        config_path = work_dir / "config.yaml"
        config = create_default_config(config_path)

        # Update worker count if specified
        if workers != 3:
            config.workers.count = workers
            manager = ConfigManager(config_path)
            manager.save(config)

        # Create agent configuration files
        console.print("[cyan]Creating agent configuration files (CLAUDE.md)...[/cyan]")
        create_agent_config_files(work_dir)

        # Success message
        table = Table(title="Initialization Complete", show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Work Directory", str(work_dir))
        table.add_row("Config File", str(config_path))
        table.add_row("Master Agents", "1")
        table.add_row("Worker Agents", str(workers))
        table.add_row("Tmux Session", config.tmux.session_name)

        console.print(table)
        console.print("\n[green]✓[/green] Initialization successful!")
        console.print("\n[cyan]Next steps:[/cyan]")
        console.print("  1. Review configuration: [bold]hephaestus-work/config.yaml[/bold]")
        console.print("  2. Start agents: [bold]hephaestus attach[/bold]")

    except Exception as e:
        console.print(f"[red]✗ Initialization failed:[/red] {e}")
        logger.error(f"Initialization failed: {e}", exc_info=True)
        sys.exit(1)


@main.command(name="attach")
@click.option(
    "--create",
    "-c",
    is_flag=True,
    help="Create a new session if one doesn't exist",
)
def attach_command(create: bool):
    """Attach to the tmux session with all agents.

    Opens a tmux session showing Master and Worker agents in split panes.
    Each pane runs a claude instance.
    """
    init_logger()

    work_dir = get_work_directory()

    # Check if initialized
    if not work_dir.exists():
        console.print(
            Panel(
                "[red]hephaestus-work directory not found![/red]\n\n"
                "Run [bold]hephaestus init[/bold] first to initialize the environment.",
                title="Not Initialized",
                border_style="red",
            )
        )
        sys.exit(1)

    try:
        # Load configuration
        config_path = work_dir / "config.yaml"
        config_manager = ConfigManager(config_path)
        config = config_manager.load()

        # Create session manager
        session_manager = SessionManager(config, work_dir)

        # Check if session exists
        if session_manager.session_exists():
            console.print(f"[cyan]Attaching to existing session: {config.tmux.session_name}[/cyan]")
            session_manager.attach()
        elif create:
            console.print(f"[cyan]Creating new session: {config.tmux.session_name}[/cyan]")
            session_manager.create_session()
            session_manager.attach()
        else:
            console.print(
                Panel(
                    f"[yellow]No session found: {config.tmux.session_name}[/yellow]\n\n"
                    "Use [bold]--create[/bold] flag to create a new session:\n"
                    f"  [bold]hephaestus attach --create[/bold]",
                    title="Session Not Found",
                    border_style="yellow",
                )
            )
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]✗ Failed to attach:[/red] {e}")
        logger.error(f"Attach failed: {e}", exc_info=True)
        sys.exit(1)


@main.command(name="kill")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force kill without confirmation",
)
def kill_command(force: bool):
    """Stop all agents and terminate the tmux session.

    Gracefully shuts down all Master and Worker agents,
    saves current state, and destroys the tmux session.
    """
    init_logger()

    work_dir = get_work_directory()

    # Check if initialized
    if not work_dir.exists():
        console.print("[yellow]No hephaestus-work directory found. Nothing to kill.[/yellow]")
        sys.exit(0)

    try:
        # Load configuration
        config_path = work_dir / "config.yaml"
        config_manager = ConfigManager(config_path)
        config = config_manager.load()

        # Create session manager
        session_manager = SessionManager(config, work_dir)

        # Check if session exists
        if not session_manager.session_exists():
            console.print(f"[yellow]No active session found: {config.tmux.session_name}[/yellow]")
            sys.exit(0)

        # Confirm unless force flag is set
        if not force:
            if not click.confirm(
                f"Are you sure you want to kill session '{config.tmux.session_name}' and stop all agents?"
            ):
                console.print("[cyan]Operation cancelled.[/cyan]")
                sys.exit(0)

        # Kill session
        console.print(f"[cyan]Stopping all agents and killing session: {config.tmux.session_name}[/cyan]")
        session_manager.kill_session()

        console.print("[green]✓[/green] Session terminated successfully!")

    except Exception as e:
        console.print(f"[red]✗ Failed to kill session:[/red] {e}")
        logger.error(f"Kill failed: {e}", exc_info=True)
        sys.exit(1)


@main.command(name="status")
def status_command():
    """Show current status of agents and tasks.

    Displays information about running agents, active tasks,
    and system health.
    """
    init_logger()

    work_dir = get_work_directory()

    # Check if initialized
    if not work_dir.exists():
        console.print("[yellow]Not initialized. Run 'hephaestus init' first.[/yellow]")
        sys.exit(1)

    try:
        # Load configuration
        config_path = work_dir / "config.yaml"
        config_manager = ConfigManager(config_path)
        config = config_manager.load()

        # Create session manager
        session_manager = SessionManager(config, work_dir)

        # Check session status
        session_active = session_manager.session_exists()

        # Display status
        table = Table(title="Hephaestus Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Work Directory", str(work_dir))
        table.add_row("Tmux Session", config.tmux.session_name)
        table.add_row(
            "Session Active", "[green]Yes[/green]" if session_active else "[red]No[/red]"
        )
        table.add_row("Worker Count", str(config.workers.count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]✗ Failed to get status:[/red] {e}")
        logger.error(f"Status check failed: {e}", exc_info=True)
        sys.exit(1)


@main.command(name="monitor")
@click.option(
    "--interval",
    "-i",
    default=5,
    type=int,
    help="Task check interval in seconds (default: 5)",
)
@click.option(
    "--max-iterations",
    "-m",
    default=120,
    type=int,
    help="Maximum monitoring iterations (default: 120, ~10 minutes)",
)
def monitor_command(interval: int, max_iterations: int):
    """Monitor and auto-distribute tasks to workers.

    This command starts a background process that monitors the
    communication/master_to_worker directory and automatically
    notifies workers about new task assignments via tmux send-keys.
    """
    init_logger()

    work_dir = get_work_directory()

    # Check if initialized
    if not work_dir.exists():
        console.print("[yellow]Not initialized. Run 'hephaestus init' first.[/yellow]")
        sys.exit(1)

    try:
        # Load configuration
        config_path = work_dir / "config.yaml"
        config_manager = ConfigManager(config_path)
        config = config_manager.load()

        # Create session manager to check if session exists
        session_manager = SessionManager(config, work_dir)

        if not session_manager.session_exists():
            console.print(
                Panel(
                    f"[red]No active session found: {config.tmux.session_name}[/red]\n\n"
                    "Start the session first with: [bold]hephaestus attach --create[/bold]",
                    title="Session Not Running",
                    border_style="red",
                )
            )
            sys.exit(1)

        # Create communicator and distributor
        communicator = AgentCommunicator(config.tmux.session_name, work_dir)
        distributor = TaskDistributor(config, work_dir, communicator)

        # Display monitoring info
        console.print(
            Panel(
                f"[cyan]Monitoring task distribution[/cyan]\n\n"
                f"Session: {config.tmux.session_name}\n"
                f"Workers: {config.workers.count}\n"
                f"Check interval: {interval}s\n"
                f"Max duration: ~{(interval * max_iterations) // 60} minutes",
                title="Task Monitor Started",
                border_style="cyan",
            )
        )

        console.print("\n[yellow]Press Ctrl+C to stop monitoring[/yellow]\n")

        # Start monitoring
        try:
            distributor.monitor_and_distribute_tasks(
                interval=interval,
                max_iterations=max_iterations
            )

            # Show final status
            status = distributor.get_status_summary()
            console.print("\n[green]✓[/green] Monitoring completed")
            console.print(f"Tasks: {status['total']} total, {status['completed']} completed")

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Monitoring stopped by user[/yellow]")
            status = distributor.get_status_summary()
            console.print(f"Tasks: {status['total']} total, {status['completed']} completed")

    except Exception as e:
        console.print(f"[red]✗ Monitoring failed:[/red] {e}")
        logger.error(f"Monitor failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
