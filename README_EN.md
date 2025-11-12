# Hephaestus

> 🏗️ Under Development

A tmux-based multi-agent CLI tool for managing multiple LLM agents (Master + Workers) to execute complex tasks collaboratively. When tmux can't be used (e.g., CI containers or sandboxed terminals), it automatically falls back to a headless, log-driven mode so agents keep running.

> 📖 [日本語README](README.md) | 📚 [Detailed Documentation](doc/commands/)

## Key Features

- **Master-Worker Architecture**: One Master agent coordinates multiple Worker agents
- **Multiple AI Agent Support**: Supports Claude Code, Gemini CLI, and ChatGPT Codex
- **Real-Time Monitoring**: TUI dashboard and log streaming for visibility
- **Strict Persona Management**: Force-inject agent roles at startup
- **Tmux Integration**: Visual management of multiple agents in split panes
- **Headless Fallback**: Automatically switches to a background/headless runner when tmux is unavailable, with log streaming + status panel
- **Automatic Task Distribution**: Markdown-based file communication for task assignment
- **Enforced Communication Protocol**: Reliable inter-agent communication using `hephaestus send`

## UI

**Image Sample**  
<img src=./media/ui-sample.png width=600>

**Working Sample**  
<img src=./media/working-sample.gif width=600>

## Prerequisites

- Python 3.10 or higher
- tmux (recommended; the CLI falls back to headless mode automatically if tmux is missing or blocked)
- One of the following AI agents:
  - [Claude Code](https://github.com/anthropics/claude-code)
  - [Gemini CLI](https://github.com/google/gemini-cli)
  - [ChatGPT Codex](https://chatgpt.com/codex)
- Linux operating system

## Use Cases

- Research
- Small- to Medium-Scale System Development
- Refactoring

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
# 1. Initialize (uses Claude Code by default)
cd /path/to/your/project
hephaestus init

# Or specify a specific AI agent
hephaestus init --agent-type gemini    # Use Gemini CLI
hephaestus init --agent-type codex     # Use ChatGPT Codex
hephaestus init --agent-type claude    # Use Claude Code (explicit)

# 2. Start session
hephaestus attach --create
#   ↳ Automatically falls back to headless mode when tmux can't be used and shows a lightweight dashboard

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

### Operating Without tmux

`hephaestus attach --create` first attempts to launch a tmux session. If tmux is not installed, is disallowed, or prints errors such as `error connecting to /tmp/tmux-1000/default (Operation not permitted)`, Hephaestus automatically switches to headless mode.

- A lightweight dashboard appears in the current terminal listing each agent's PID, log path, and status
- Agent stdout/stderr are continuously written to `.hephaestus-work/logs/*.log`; use another terminal to run `hephaestus logs --all -f` or `hephaestus logs -a master -f` for real-time streaming
- Pressing `Ctrl+C` exits the dashboard but keeps agents running; use `hephaestus kill` whenever you want to stop them

When tmux becomes available again, the next `hephaestus attach` automatically returns to the regular tmux session—no extra steps needed.

### Switching Agents After Rate Limits

If your current agent hits an API limit, you can swap to another provider without recreating the workspace:

```bash
hephaestus kill  # stop the running tmux session
hephaestus attach --create --change-agent codex
```

This command regenerates `.Claude/`, `.Gemini/`, or `.Codex/` inside `.hephaestus-work/` along with `config.yaml`, while leaving `tasks/`, `logs/`, `communication/`, etc. untouched.

## Configuration

Edit `.hephaestus-work/config.yaml` to customize:

```yaml
version: 1.0
agent_type: "claude"  # claude, gemini, codex

agents:
  master:
    enabled: true
    command: "claude --dangerously-skip-permissions"  # Auto-configured by agent type
    args: []
  workers:
    count: 3  # Change number of workers
    command: "claude --dangerously-skip-permissions"
    args: []

monitoring:
  health_check_interval: 30  # seconds
  retry_attempts: 3
  retry_delay: 5

tmux:
  session_name: "hephaestus"
  layout: "tiled"  # even-horizontal, even-vertical, main-horizontal, main-vertical, tiled
```

**Commands by Agent Type:**
- `claude`: `claude --dangerously-skip-permissions`
- `gemini`: `gemini --yolo`
- `codex`: `codex --full-auto`

**Technical Note - Persona Injection Methods:**
Each agent type uses a different persona injection approach at startup:
- **Claude Code / Gemini CLI**: After agent startup, waits 3 seconds then injects persona via `echo` commands
- **ChatGPT Codex**: Passes persona as a command-line argument at startup (executed as `codex "PERSONA" --full-auto` via temporary script file)

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
# Code Refactoring Project (using Claude Code)
hephaestus init --agent-type claude --workers 4
hephaestus attach --create
# In Master pane:
# "Refactor the entire codebase to use dependency injection.
#  Split the work across available workers."
```

```bash
# Data Analysis Project (using Gemini CLI)
hephaestus init --agent-type gemini --workers 3
hephaestus attach --create
# In Master pane:
# "Analyze multiple datasets and create an integrated report."
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
cat .hephaestus-work/logs/communication.log
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

**`error connecting to /tmp/tmux-XXXX/default (Operation not permitted)` appears**
- tmux cannot create or access its socket in this environment. The CLI automatically switches to headless mode—just follow the on-screen instructions
- Stream logs with `hephaestus logs --all -f`. When tmux becomes available again, run `hephaestus attach` to re-enter the normal tmux session

**Agents not communicating**
```bash
hephaestus logs -a master -f    # Check logs
ls -la .hephaestus-work/communication/    # Verify permissions
```

**High resource usage**
```bash
# Reduce worker count in config.yaml
hephaestus init --workers 2 --force
```

## License

MIT License

---

**Version**: 0.1.0 | **Status**: Alpha
