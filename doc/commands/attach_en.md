# hephaestus attach

## Overview

`hephaestus attach` attaches (connects) to the Hephaestus tmux session.

## Usage

```bash
hephaestus attach [OPTIONS]
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--create` | `-c` | Create a new session if one doesn't exist |
| `--change-agent <type>` | - | Replace agent configuration with `claude`, `gemini`, or `codex` before attaching (session must not be running) |
| `--help` | - | Show help message |

## Behavior

1. If an existing tmux session exists, attach to that session
2. If `--create` option is specified, create a new session if one doesn't exist
3. If `--change-agent` is provided, the command rewrites `config.yaml` and regenerates agent persona files before creating the tmux session (requires the previous session to be stopped via `hephaestus kill`)
4. Within the tmux session, Master + Worker agents start in separate panes

### Headless Fallback Mode

The command automatically detects when tmux cannot be used (missing binary, sandboxed terminals printing `error connecting to /tmp/tmux-1000/default (Operation not permitted)`, etc.) and transparently switches to headless mode instead of failing.

- A Rich-based dashboard is shown in the current terminal listing agent names, PIDs, log paths, and live status
- Agents continue running in the background; press `Ctrl+C` to exit the dashboard at any time
- Use `hephaestus logs --all -f` (or `-a master`, `-a worker-1`, etc.) in another terminal to stream output while in headless mode
- Run `hephaestus kill` to stop the headless session; no additional flags are required

Once tmux becomes available again, `hephaestus attach` transparently returns to tmux without manual cleanup.

## Examples

### Attach to Existing Session

```bash
hephaestus attach
```

### Create Session and Attach

```bash
hephaestus attach --create
```

The `--create` option is required for first-time startup.

### Change Agent After Hitting Rate Limits

```bash
hephaestus kill
hephaestus attach --create --change-agent codex
```

This sequence replaces `.Claude/` (or `.Gemini/`, `.Codex/`) and updates `config.yaml` so the next tmux session boots with the newly selected agent.

## Operations Within tmux Session

After attaching, the following tmux key bindings are available:

| Key Binding | Function |
|------------|----------|
| `Ctrl+b` → `d` | Detach from session (agents continue running) |
| `Ctrl+b` → Arrow keys | Move between panes |
| `Ctrl+b` → `z` | Maximize/restore current pane |
| `Ctrl+b` → `[` | Scroll mode (q to exit) |

## Session Layout

```
┌─────────────────────────────────────────────┐
│                Master Agent                 │  ← Master agent
├──────────────┬──────────────┬───────────────┤
│  Worker-1    │  Worker-2    │   Worker-3    │  ← Worker agents
│              │              │               │
│              │              │               │
└──────────────┴──────────────┴───────────────┘
```

## Agent Startup Behavior

Each agent undergoes the following process on startup:

1. **Persona Injection**: The agent-specific README (e.g., `CLAUDE.md`, `GEMINI.md`, `AGENT.md`) is automatically loaded and role is assigned to agent
2. **Initialization Confirmation**: Confirms agent recognizes its role
3. **Waiting State**: Waits for task assignment

## Errors and Solutions

### Session Doesn't Exist

```
No session found: hephaestus

Use --create flag to create a new session:
  hephaestus attach --create
```

**Solution**: Add `--create` option.

### Not Initialized

```
.hephaestus-work directory not found!

Run hephaestus init first to initialize the environment.
```

**Solution**: First run `hephaestus init`.

### tmux Not Installed

```
tmux: command not found
```

**Solution**: Install tmux:
```bash
# Ubuntu/Debian
sudo apt-get install tmux

# macOS
brew install tmux
```

## Notes

- Detaching from session does not stop agents - they continue running
- Use `--change-agent` only after stopping the current session (`hephaestus kill`) to avoid conflicts
- You can reattach to the same session later
- Use `hephaestus kill` to terminate the session

## Related Commands

- [hephaestus init](./init_en.md) - Initialize (run first)
- [hephaestus kill](./kill_en.md) - Terminate session
- [hephaestus status](./status_en.md) - Check session status
- [hephaestus dashboard](./dashboard_en.md) - Monitor in separate window
