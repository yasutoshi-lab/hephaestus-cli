# hephaestus logs

## Overview

`hephaestus logs` displays and streams agent log files.

## Usage

```bash
hephaestus logs [OPTIONS]
```

## Options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--agent` | `-a` | - | Agent name to display (can specify multiple) |
| `--follow` | `-f` | false | Follow log output in real-time (like tail -f) |
| `--lines` | `-n` | 50 | Number of lines to display |
| `--all` | - | false | Show logs from all agents |
| `--list` | `-l` | false | List available log files |
| `--help` | - | - | Show help message |

## Agent Names

You can specify the following agent names:

- `master`: Master agent log
- `worker-1`, `worker-2`, ...: Each worker agent log
- `system`: System log
- `communication`: Inter-agent communication log

## Examples

### List Available Log Files

```bash
hephaestus logs --list
```

Example output:
```
                    Available Logs
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent    ┃ Log File          ┃ Size    ┃ Last Modified       ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Master   │ master.log        │ 486.0 B │ 2025-11-07 02:39:49 │
│ Worker-1 │ worker_1.log      │ 485.0 B │ 2025-11-07 02:39:52 │
│ Worker-2 │ worker_2.log      │ 425.0 B │ 2025-11-07 02:39:55 │
│ System   │ system.log        │ 133.0 B │ 2025-11-07 02:39:06 │
│ Comm     │ communication.log │ 396.0 B │ 2025-11-07 02:39:57 │
└──────────┴───────────────────┴─────────┴─────────────────────┘
```

### Display Specific Agent Logs

```bash
# Last 50 lines from Master agent (default)
hephaestus logs -a master

# Last 100 lines from Master agent
hephaestus logs -a master -n 100

# Last 20 lines from Worker-1
hephaestus logs -a worker-1 -n 20
```

### Display Multiple Agent Logs

```bash
# Display Master and Worker-1 logs
hephaestus logs -a master -a worker-1

# Display Worker-1 and Worker-2 logs
hephaestus logs -a worker-1 -a worker-2
```

### Follow Logs in Real-time

```bash
# Follow Master agent logs in real-time
hephaestus logs -a master -f

# Follow all agent logs in real-time
hephaestus logs --all -f

# Follow Worker-1 logs in real-time
hephaestus logs -a worker-1 --follow
```

**Note**: Real-time following can be stopped with `Ctrl+C`.

### Check Communication Logs

```bash
# Display inter-agent communication log
hephaestus logs -a communication

# Follow communication log in real-time
hephaestus logs -a communication -f
```

### Check System Logs

```bash
hephaestus logs -a system
```

## Headless Mode Usage

When `hephaestus attach` falls back to headless mode (because tmux is unavailable), this command becomes the primary way to observe agent output:

- Use `hephaestus logs --all -f` to tail every agent log concurrently while the headless dashboard is running
- Narrow the stream with `-a master`, `-a worker-1`, etc. to debug a single agent
- The command automatically creates log files under `.hephaestus-work/logs/` if they do not exist yet, so you can start following logs even before the agents emit output

Combine this with `hephaestus kill` to stop headless sessions when you are done.

## Color-coded Display

Logs are color-coded by agent for easy viewing:

- **Master**: Cyan
- **Worker**: Green
- **System**: Yellow
- **Communication**: Magenta

## Output Format

### Individual Log Display

```
╭───────────────────────────────── master Log ─────────────────────────────────╮
│ Last 3 lines from: master.log                                                │
╰──────────────────────────────────────────────────────────────────────────────╯
2025-11-07 10:00:04,678 - Master - INFO - Tasks assigned to workers
2025-11-07 10:00:05,901 - Master - INFO - Monitoring worker progress
```

### Real-time Following

```
╭─────────────────────────────────  Log Stream ─────────────────────────────────╮
│ Streaming logs from: master.log                                              │
╰──────────────────────────────────────────────────────────────────────────────╯

Press Ctrl+C to stop streaming

[Master] 2025-11-07 10:00:04,678 - Master - INFO - Tasks assigned to workers
[Master] 2025-11-07 10:00:05,901 - Master - INFO - Monitoring worker progress
...
```

## Errors and Solutions

### When Not Initialized

```
Not initialized. Run 'hephaestus init' first.
```

**Solution**: Run `hephaestus init`.

### When Specified Agent Log Doesn't Exist

```
Log file not found for agent: worker-5
```

**Solution**:
- Check available logs with `hephaestus logs --list`
- Verify agent name spelling
- Check if session is running (`hephaestus status`)

## Use Cases

### Debugging

```bash
# Check logs of Worker with error
hephaestus logs -a worker-2 -n 100

# Check all agent logs
hephaestus logs --all -n 50
```

### Monitor Task Execution

```bash
# Monitor Master operations in real-time
hephaestus logs -a master -f

# Monitor specific Worker progress in real-time
hephaestus logs -a worker-1 -f
```

### Check Communication

```bash
# Check inter-agent communication
hephaestus logs -a communication -f
```

## Notes

- If log file doesn't exist, agent may not have started yet
- Real-time following (`-f`) waits until log file is updated
- For large logs, recommend limiting lines with `-n` option

## Performance

- Log display is fast and handles large log files efficiently
- Real-time following detects file changes efficiently

## Related Commands

- [hephaestus dashboard](./dashboard_en.md) - Graphical monitoring
- [hephaestus status](./status_en.md) - Quick status check
- [hephaestus monitor](./monitor_en.md) - Monitor task distribution

## Log File Location

Log files are stored in `.hephaestus-work/logs/` directory:

```
.hephaestus-work/logs/
├── master.log           # Master agent log
├── worker_1.log         # Worker-1 log
├── worker_2.log         # Worker-2 log
├── worker_N.log         # Worker-N log
├── system.log           # System log
└── communication.log    # Communication log
```
