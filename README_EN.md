# Hephaestus

> 🏗️ Under Development

A tmux-based multi-agent CLI tool for managing multiple LLM agents (Master + Workers) to execute complex tasks collaboratively.

> 📖 [日本語README](README.md) | 📚 [Detailed Documentation](doc/commands/)

## Key Features

- **Master-Worker Architecture**: One Master agent coordinates multiple Worker agents
- **Real-Time Monitoring**: TUI dashboard and log streaming for visibility
- **Strict Persona Management**: Force-inject agent roles at startup
- **Tmux Integration**: Visual management of multiple agents in split panes
- **Automatic Task Distribution**: Markdown-based file communication for task assignment
- **Enforced Communication Protocol**: Reliable inter-agent communication using `hephaestus send`

## Prerequisites

- Python 3.10 or higher
- tmux
- claude code
- Linux operating system

## Installation

### Using uv (Recommended)

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/Hephaestus.git
cd Hephaestus

# Build the package
python3 -m build

# Install with uv
uv tool install dist/hephaestus-0.1.0-*.whl
```

### Using pip

```bash
# Clone and build
git clone https://github.com/your-org/Hephaestus.git
cd Hephaestus

# Install in development mode
pip install -e .

# Or build and install
python3 -m build
pip install dist/hephaestus-0.1.0-*.whl
```

## Quick Start

```bash
# 1. Initialize
cd /path/to/your/project
hephaestus init

# 2. Start session
hephaestus attach --create

# 3. Work
# - Input high-level tasks in Master pane
# - Workers automatically execute subtasks
# - Tmux keybindings: Ctrl+b → arrow keys to navigate

# 4. Monitor (in another terminal)
hephaestus dashboard    # Real-time monitoring
hephaestus logs -a master -f    # Log streaming

# 5. Stop
hephaestus kill
```

## Configuration

Edit `hephaestus-work/config.yaml` to customize:

```yaml
version: 1.0

agents:
  master:
    enabled: true
    command: "claude"
    args: []
  workers:
    count: 3  # Change number of workers
    command: "claude"
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

| Command | Description | Documentation |
|---------|-------------|---------------|
| `hephaestus init` | Initialize environment | [Details](doc/commands/init_en.md) |
| `hephaestus attach` | Attach/create tmux session | [Details](doc/commands/attach_en.md) |
| `hephaestus status` | Show current status | [Details](doc/commands/status_en.md) |
| `hephaestus send` | Send message to agents | [Details](doc/commands/send_en.md) |
| `hephaestus dashboard` | Real-time TUI dashboard | [Details](doc/commands/dashboard_en.md) |
| `hephaestus logs` | Display/stream logs | [Details](doc/commands/logs_en.md) |
| `hephaestus monitor` | Monitor task distribution | [Details](doc/commands/monitor_en.md) |
| `hephaestus kill` | Terminate session | [Details](doc/commands/kill_en.md) |

See each command's documentation for detailed usage.

## Usage Examples

### Basic Usage

```bash
# Code Refactoring Project
hephaestus init --workers 4
hephaestus attach --create
# In Master pane:
# "Refactor the entire codebase to use dependency injection.
#  Split the work across available workers."
```

Master automatically splits tasks and assigns them to Workers for parallel processing.

### Manual Inter-Agent Communication

```bash
# List available agents
hephaestus send --list

# Send message to specific Worker
hephaestus send worker-1 "Start analyzing the src/ directory"

# Report progress to Master (from within Worker)
hephaestus send master "Task completed. Please review the results"

# Check communication logs
cat hephaestus-work/logs/communication.log
```

**Note**: Agent personas enforce the use of `hephaestus send`:
- **Master**: Must use `hephaestus send worker-{N}` when assigning tasks
- **Worker**: Must use `hephaestus send master` when reporting progress

## Troubleshooting

**Session won't start**
```bash
tmux -V    # Check if tmux is installed
which claude    # Check if claude is available
```

**Agents not communicating**
```bash
hephaestus logs -a master -f    # Check logs
ls -la hephaestus-work/communication/    # Verify permissions
```

**High resource usage**
```bash
# Reduce worker count in config.yaml
hephaestus init --workers 2 --force
```

## References

- [Claude Code](https://github.com/anthropics/claude-code)

## License

MIT License

---

**Version**: 0.1.0 | **Status**: Alpha
