# hephaestus send

## Overview

`hephaestus send` is a command for sending messages between agents. It's used for task distribution from Master to Workers and progress reporting from Workers to Master.

## Usage

```bash
# List available agents
hephaestus send --list

# Send a message
hephaestus send <agent-name> <message>
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--list` | `-l` | List all available agents |

## Arguments

- `<agent-name>`: Target agent name (master, worker-1, worker-2, etc.)
- `<message>`: Message to send

## Usage Examples

### List Available Agents

```bash
hephaestus send --list
```

**Example Output**:
```
                          Agent List
┏━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Agent Name ┃ Status   ┃ Pane            ┃
┡━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ master    │ Active   │ hephaestus:0.0  │
│ worker-1  │ Active   │ hephaestus:0.1  │
│ worker-2  │ Active   │ hephaestus:0.2  │
│ worker-3  │ Active   │ hephaestus:0.3  │
└───────────┴──────────┴─────────────────┘
```

### Send Message to Worker

```bash
hephaestus send worker-1 "Start analyzing the code in src/ directory"
```

**Output**:
```
Sending message to worker-1...
✓ Message sent to worker-1
Message: Start analyzing the code in src/ directory

Communication logged to: hephaestus-work/logs/communication.log
```

### Report Progress to Master (from Worker)

```bash
hephaestus send master "Task task_001 completed. Results saved to communication/worker_to_master/task_001_results.md"
```

### Broadcast to Multiple Workers (Script Example)

```bash
# Send to all workers at once
for i in {1..3}; do
    hephaestus send worker-$i "URGENT: Please pause your current work immediately"
done
```

## Integration with Agent Personas

Agent personas (CLAUDE.md) enforce the use of `hephaestus send` at specific milestones:

### Master Agent

**Required when assigning tasks**:
```bash
# 1. Create task file
# communication/master_to_worker/task_001_analysis.md

# 2. Must notify via send command (executed automatically)
hephaestus send worker-1 "New task assigned: Code Analysis. Please read task_001_analysis.md"
```

### Worker Agent

**Required for progress reporting**:

1. **Task Start**:
```bash
hephaestus send master "Task task_001 started. Analyzing code. ETA: 30 minutes"
```

2. **Progress Updates**:
```bash
hephaestus send master "Task task_001 progress: 50% complete. Found 5 issues"
```

3. **Completion**:
```bash
hephaestus send master "Task task_001 COMPLETED. Results saved to task_001_results.md"
```

4. **Blockers**:
```bash
hephaestus send master "Task task_001 BLOCKED: Missing dependency. Need assistance"
```

## Communication Logs

All communications are automatically logged:

```bash
# View logs
cat hephaestus-work/logs/communication.log

# Search for specific agent communication
grep "master -> worker-1" hephaestus-work/logs/communication.log
```

**Log Format**:
```
[2025-11-08 18:30:45] master -> worker-1: New task assigned: Code Analysis
[2025-11-08 18:31:00] worker-1 -> master: Task acknowledged. Starting work
[2025-11-08 18:45:30] worker-1 -> master: Task completed. Results ready
```

## Errors and Solutions

### Session Not Running

```
No active session found: hephaestus

Start the session first with: hephaestus attach --create
```

**Solution**: Start the session with `hephaestus attach --create`.

### Agent Not Found

```
✗ Failed to send message to worker-5
Check if the agent exists with: hephaestus send --list
```

**Solution**:
- Check agent list with `hephaestus send --list`
- Verify worker count in config.yaml
- Use correct agent name (master, worker-1, worker-2, etc.)

### Missing Arguments

```
Missing arguments

Usage:
  hephaestus send --list                    # List agents
  hephaestus send <agent> <message>         # Send message
```

**Solution**: Specify both agent name and message.

## Usage Scenarios

### 1. Urgent Task Assignment

```bash
# Send high-priority task immediately
hephaestus send worker-2 "URGENT: Prioritize security vulnerability fix"
```

### 2. Status Check

```bash
# Ask worker for status update
hephaestus send worker-1 "Please report current task progress"
```

### 3. Work Interruption

```bash
# Instruct all workers to pause
for i in {1..3}; do
    hephaestus send worker-$i "Please pause work and await new instructions"
done
```

### 4. Debug and Testing

```bash
# Test communication system
hephaestus send worker-1 "Test message - Please acknowledge"

# Monitor logs for acknowledgment
tail -f hephaestus-work/logs/communication.log
```

## Technical Details

### Communication Mechanism

`hephaestus send` sends messages through the following steps:

1. **Pane Discovery**: Locate target agent by tmux pane title
2. **Clear Input**: Send Ctrl+C to clear existing input
3. **Send Message**: Use tmux send-keys to transmit message
4. **Execute**: Send Enter to execute the message
5. **Log**: Record in communication.log

### Message Limitations

- Special characters (`$`, `"`, `` ` ``, etc.) are properly escaped
- Very long messages are split for transmission
- Consider tmux line length limits when designing messages

## Related Commands

- [hephaestus attach](./attach_en.md) - Start session
- [hephaestus monitor](./monitor_en.md) - Automatic task distribution
- [hephaestus logs](./logs_en.md) - View logs
- [hephaestus status](./status_en.md) - Check session status

## References

- [Claude-Code-Communication](https://github.com/nishimoto265/Claude-Code-Communication) - Original agent-send.sh implementation
