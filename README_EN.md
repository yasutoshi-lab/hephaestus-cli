# Hephaestus-CLI

A tmux-based multi-agent CLI tool for managing multiple LLM agents (Master + Workers) to execute complex tasks collaboratively.

## Overview

Hephaestus-CLI is a Linux-based command-line tool that leverages tmux to orchestrate multiple Claude Code agents working together. It features:

- **Master-Worker Architecture**: One Master agent coordinates multiple Worker agents
- **Tmux Integration**: Visual management of multiple agents in split panes
- **Task Management**: Automatic task distribution and progress tracking
- **Health Monitoring**: Automatic agent health checks and error recovery
- **File-Based Communication**: Markdown-based message passing between agents
- **Self-Contained**: Everything runs within a `hephaestus-work` directory

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hephaestus-CLI                       │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐                                       │
│  │   CLI Entry  │ (init, attach, kill)                  │
│  └──────┬───────┘                                       │
│         │                                                │
│  ┌──────▼───────────────────────────────┐              │
│  │    Session Manager (tmux wrapper)     │              │
│  └──────┬───────────────────────────────┘              │
│         │                                                │
│  ┌──────▼────────┬──────────┬──────────┬──────────┐    │
│  │    Master     │ Worker-1 │ Worker-2 │ Worker-N │    │
│  │ (claude-code) │  (c-c)   │  (c-c)   │  (c-c)   │    │
│  └───────────────┴──────────┴──────────┴──────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.10 or higher
- tmux (installed on your system)
- claude-code CLI installed and configured
- Linux operating system

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/hephaestus-cli.git
cd hephaestus-cli

# Build the package
python3 -m build

# Install with uv
uv tool install dist/hephaestus_cli-0.1.0-*.whl
```

### Using pip

```bash
# Clone and build
git clone https://github.com/your-org/hephaestus-cli.git
cd hephaestus-cli

# Install in development mode
pip install -e .

# Or build and install
python3 -m build
pip install dist/hephaestus_cli-0.1.0-*.whl
```

## Quick Start

### 1. Initialize Hephaestus

Navigate to your project directory and initialize:

```bash
cd /path/to/your/project
hephaestus init
```

This creates a `hephaestus-work` directory with the following structure:

```
hephaestus-work/
├── config.yaml                     # Configuration file
├── cache/                          # Agent states and rate limits
├── tasks/                          # Task queue (pending/in_progress/completed)
├── checkpoints/                    # Recovery checkpoints
├── progress/                       # Agent progress tracking
├── logs/                           # System and agent logs
└── communication/                  # Inter-agent messaging
```

### 2. Start Agents

Attach to the tmux session (creates it if it doesn't exist):

```bash
hephaestus attach --create
```

This opens a tmux session with split panes:
- Top pane: Master agent
- Additional panes: Worker agents (default: 3 workers)

### 3. Work with Agents

Once attached:
- Navigate between panes using tmux keybindings (default: `Ctrl+b` then arrow keys)
- The Master pane is where you input high-level tasks
- Workers automatically receive and execute subtasks from the Master
- All agents run `claude-code` and can access tools

### 4. Stop Agents

Detach from tmux session (agents keep running):
```bash
# Press Ctrl+b, then d
```

Kill all agents and destroy session:
```bash
hephaestus kill
```

## Configuration

Edit `hephaestus-work/config.yaml` to customize:

```yaml
version: 1.0

agents:
  master:
    enabled: true
    command: "claude-code"
    args: []
  workers:
    count: 3  # Change number of workers
    command: "claude-code"
    args: []

monitoring:
  health_check_interval: 30  # seconds
  retry_attempts: 3
  retry_delay: 5

tmux:
  session_name: "hephaestus"
  layout: "tiled"  # even-horizontal, even-vertical, main-horizontal, main-vertical, tiled
```

## Commands

### `hephaestus init`

Initialize hephaestus-work directory.

Options:
- `-w, --workers N`: Number of worker agents (default: 3)
- `-f, --force`: Force reinitialization

Example:
```bash
hephaestus init --workers 5
```

### `hephaestus attach`

Attach to the tmux session.

Options:
- `-c, --create`: Create session if it doesn't exist

Example:
```bash
hephaestus attach --create
```

### `hephaestus kill`

Stop all agents and destroy the tmux session.

Options:
- `-f, --force`: Skip confirmation prompt

Example:
```bash
hephaestus kill --force
```

### `hephaestus status`

Show current status of agents and tasks.

Example:
```bash
hephaestus status
```

## Usage Patterns

### Example 1: Code Refactoring Project

```bash
# Initialize with 4 workers
hephaestus init --workers 4

# Start session
hephaestus attach --create

# In Master pane, instruct:
# "Refactor the entire codebase to use dependency injection.
#  Split the work across available workers."

# Master will:
# 1. Analyze the codebase
# 2. Create subtasks (e.g., refactor module A, B, C, D)
# 3. Assign tasks to workers
# 4. Monitor progress and consolidate results
```

### Example 2: Documentation Generation

```bash
# Initialize with default workers
hephaestus init

# Start session
hephaestus attach --create

# In Master pane:
# "Generate comprehensive documentation for all Python modules.
#  Each worker should handle different packages."

# Workers will process in parallel while Master coordinates
```

## Directory Structure Explained

### `cache/`
- `agent_states/`: Stores agent status and metadata
- `rate_limits/`: Tracks API rate limit information

### `tasks/`
- `pending/`: Tasks waiting to be assigned
- `in_progress/`: Currently executing tasks
- `completed/`: Finished tasks with results

### `communication/`
- `master_to_worker/`: Messages from Master to Workers
- `worker_to_master/`: Status updates and results from Workers

### `logs/`
- `master.log`: Master agent logs
- `worker_N.log`: Individual worker logs
- `system.log`: System-level logs

## Advanced Features

### Task Management

Tasks are automatically managed through Markdown files. The Master agent creates tasks that Workers can pick up and execute.

### Health Monitoring

- Automatic health checks every 30 seconds
- Detects crashed agents, rate limits, resource issues
- Automatic recovery with configurable retry attempts
- Error history tracking in cache

### Checkpoints

System automatically creates checkpoints for long-running tasks, enabling recovery from failures.

## Troubleshooting

### Session won't start

Check if tmux is installed:
```bash
tmux -V
```

Check if claude-code is available:
```bash
which claude-code
```

### Agents not communicating

Check communication directory permissions:
```bash
ls -la hephaestus-work/communication/
```

View logs:
```bash
tail -f hephaestus-work/logs/system.log
```

### High resource usage

Reduce worker count in config.yaml:
```yaml
agents:
  workers:
    count: 2  # Reduced from 3
```

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
hephaestus-cli/
├── src/hephaestus/
│   ├── cli.py                  # CLI entry point
│   ├── config.py               # Configuration management
│   ├── session_manager.py      # Tmux session handling
│   ├── agent_controller.py     # Agent lifecycle
│   ├── communication.py        # Inter-agent messaging
│   ├── task_manager.py         # Task queue management
│   ├── health_monitor.py       # Health monitoring
│   └── utils/                  # Utility modules
├── templates/                  # Config templates
├── tests/                      # Test suite
└── pyproject.toml             # Package configuration
```

## Contributing

Contributions are welcome! Please see CONTRIBUTING.md for guidelines.

## License

MIT License - See LICENSE file for details.

## References

- [Claude Code](https://github.com/anthropics/claude-code)
- [Claude-Code-Communication](https://github.com/nishimoto265/Claude-Code-Communication)
- [tmux](https://github.com/tmux/tmux)

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/hephaestus-cli/issues
- Documentation: See design documents in repository

---

**Version**: 0.1.0
**Status**: Alpha
**Last Updated**: 2025-01-06
