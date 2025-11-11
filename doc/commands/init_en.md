# hephaestus init

## Overview

`hephaestus init` initializes the Hephaestus working environment in the current directory.

## Usage

```bash
hephaestus init [OPTIONS]
```

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--workers` | `-w` | 3 | Specify the number of worker agents |
| `--agent-type` | `-a` | claude | Type of AI agent to use (claude, gemini, codex) |
| `--force` | `-f` | - | Force reinitialization even if .hephaestus-work exists |
| `--help` | - | - | Show help message |

## Behavior

When you run this command, the following operations are performed:

1. **Directory Structure Creation**
   ```
   .hephaestus-work/
   ├── .claude/              # Agent configuration
   │   ├── CLAUDE.md         # Common configuration (for claude)
   │   ├── GEMINI.md         # Common configuration (for gemini)
   │   ├── AGENT.md          # Common configuration (for codex)
   │   ├── master/           # Master configuration
   │   │   └── [Agent-specific README file]
   │   └── worker/           # Worker configuration
   │       └── [Agent-specific README file]
   ├── config.yaml           # System configuration
   ├── cache/                # Cache
   │   ├── agent_states/
   │   └── rate_limits/
   ├── tasks/                # Task management
   │   ├── pending/
   │   ├── in_progress/
   │   └── completed/
   ├── communication/        # Inter-agent communication
   │   ├── master_to_worker/
   │   └── worker_to_master/
   ├── logs/                 # Log files
   ├── checkpoints/          # Checkpoints
   └── progress/             # Progress tracking
   ```

2. **Configuration File Generation**
   - `config.yaml`: System-wide configuration (including agent_type field)
   - Agent-type-specific README files:
     - Claude: `.claude/CLAUDE.md`, `.claude/master/CLAUDE.md`, `.claude/worker/CLAUDE.md`
     - Gemini: `.claude/GEMINI.md`, `.claude/master/GEMINI.md`, `.claude/worker/GEMINI.md`
     - Codex: `.claude/AGENT.md`, `.claude/master/AGENT.md`, `.claude/worker/AGENT.md`

3. **Initialization Confirmation**
   - Upon successful completion, information about created directories and files is displayed

## Examples

### Basic Initialization

```bash
hephaestus init
```

Creates an environment with 3 worker agents using Claude Code by default.

### Initialize with Specific Agent Type

```bash
# Use Gemini CLI
hephaestus init --agent-type gemini

# Use ChatGPT Codex
hephaestus init --agent-type codex

# Use Claude Code (explicit)
hephaestus init --agent-type claude
```

Commands and README files are automatically configured according to the agent type.

### Initialize with Specific Worker Count

```bash
hephaestus init --workers 5
```

Creates an environment with 5 worker agents.

### Initialize with Both Agent Type and Worker Count

```bash
hephaestus init --agent-type gemini --workers 4
```

Creates an environment using Gemini CLI with 4 worker agents.

### Force Reinitialization

```bash
hephaestus init --force
```

Overwrites existing `.hephaestus-work` directory without warning.

## Errors and Solutions

### When .hephaestus-work Directory Already Exists

```
.hephaestus-work directory already exists at:
/path/to/.hephaestus-work

Use --force to reinitialize.
```

**Solution**: Use `--force` option to reinitialize, or manually delete the directory and run again.

### Permission Denied

```
Permission denied: '.hephaestus-work'
```

**Solution**: Ensure you have write permissions in the current directory.

## Notes

- After initialization, you can edit `config.yaml` to customize worker count and other settings
- Using `--force` option will result in loss of all existing data including tasks and logs
- After initialization, you can start agents with `hephaestus attach --create`

## Related Commands

- [hephaestus attach](./attach_en.md) - Start agents
- [hephaestus status](./status_en.md) - Check initialization status
- [hephaestus kill](./kill_en.md) - Terminate session

## Configuration File

For details about `config.yaml` generated after initialization, see [Configuration Guide](../configuration_en.md).
