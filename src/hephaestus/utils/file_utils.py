"""File system utilities for Hephaestus-CLI.

This module provides functions for directory structure creation,
file operations, and template management.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Work directory name
WORK_DIR_NAME = "hephaestus-work"


def get_work_directory(base_path: Optional[Path] = None) -> Path:
    """Get the hephaestus-work directory path.

    Args:
        base_path: Base directory path. Defaults to current working directory.

    Returns:
        Path to hephaestus-work directory
    """
    if base_path is None:
        base_path = Path.cwd()
    return base_path / WORK_DIR_NAME


def ensure_directory(path: Path, mode: int = 0o700) -> None:
    """Ensure a directory exists with proper permissions.

    Args:
        path: Directory path to create
        mode: Unix file permissions (default: 0o700 for security)
    """
    path.mkdir(parents=True, exist_ok=True, mode=mode)
    # Explicitly set permissions in case umask interfered
    os.chmod(path, mode)
    logger.debug(f"Created directory: {path} with mode {oct(mode)}")


def create_directory_structure(base_path: Optional[Path] = None) -> Path:
    """Create the complete hephaestus-work directory structure.

    Args:
        base_path: Base directory path. Defaults to current working directory.

    Returns:
        Path to the created hephaestus-work directory

    Raises:
        OSError: If directory creation fails
    """
    work_dir = get_work_directory(base_path)

    # Define directory structure
    directories = [
        work_dir,
        work_dir / "cache" / "agent_states",
        work_dir / "cache" / "rate_limits",
        work_dir / "tasks" / "pending",
        work_dir / "tasks" / "in_progress",
        work_dir / "tasks" / "completed",
        work_dir / "checkpoints",
        work_dir / "progress",
        work_dir / "logs",
        work_dir / "communication" / "master_to_worker",
        work_dir / "communication" / "worker_to_master",
    ]

    # Create all directories
    for directory in directories:
        ensure_directory(directory)

    logger.info(f"Created hephaestus-work directory structure at {work_dir}")
    return work_dir


def copy_template(template_name: str, destination: Path) -> None:
    """Copy a template file to the destination.

    Args:
        template_name: Name of the template file (e.g., 'config.yaml.template')
        destination: Destination file path

    Raises:
        FileNotFoundError: If template file is not found
    """
    # Get the package directory
    package_dir = Path(__file__).parent.parent.parent.parent
    template_path = package_dir / "templates" / template_name

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Copy template to destination
    shutil.copy2(template_path, destination)
    logger.debug(f"Copied template {template_name} to {destination}")


def list_files(directory: Path, pattern: str = "*") -> List[Path]:
    """List files in a directory matching a pattern.

    Args:
        directory: Directory to search
        pattern: Glob pattern (default: "*" for all files)

    Returns:
        List of matching file paths
    """
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern))


def cleanup_old_files(directory: Path, max_age_days: int = 30) -> int:
    """Remove files older than specified age.

    Args:
        directory: Directory to clean
        max_age_days: Maximum age in days

    Returns:
        Number of files removed
    """
    import time

    if not directory.exists():
        return 0

    max_age_seconds = max_age_days * 24 * 3600
    current_time = time.time()
    removed_count = 0

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    removed_count += 1
                    logger.debug(f"Removed old file: {file_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove {file_path}: {e}")

    return removed_count


def get_directory_size(directory: Path) -> int:
    """Calculate total size of directory in bytes.

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total_size = 0
    if directory.exists():
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
    return total_size


def create_agent_config_files(work_dir: Path) -> None:
    """Create CLAUDE.md configuration files for master and worker agents.

    Creates hierarchical CLAUDE.md files to configure agent personas and behaviors.

    Args:
        work_dir: Path to hephaestus-work directory
    """
    claude_dir = work_dir / ".claude"
    master_dir = claude_dir / "master"
    worker_dir = claude_dir / "worker"

    # Create directories
    ensure_directory(claude_dir)
    ensure_directory(master_dir)
    ensure_directory(worker_dir)

    # Common configuration for all agents
    common_config = """# Hephaestus Multi-Agent System

This is a Hephaestus multi-agent workspace. You are part of a collaborative system with Master and Worker agents working together.

## Project Structure

```
hephaestus-work/
├── .claude/              # Agent configuration files
│   ├── master/          # Master agent specific configs
│   └── worker/          # Worker agent specific configs
├── tasks/               # Task management
│   ├── pending/         # Tasks waiting to be assigned
│   ├── in_progress/     # Currently executing tasks
│   └── completed/       # Finished tasks
├── communication/       # Inter-agent communication
│   ├── master_to_worker/  # Master → Worker messages
│   └── worker_to_master/  # Worker → Master messages
├── logs/                # Agent logs
├── cache/               # Cached data and state
├── checkpoints/         # Task checkpoints
└── progress/            # Progress tracking
```

## Communication Protocol

### File-Based Messaging
- Use markdown files in `communication/` directories
- Filename format: `{timestamp}_{from}_{to}_{task_id}.md`
- Include task ID, priority, and clear instructions

### Task Files
- Tasks are stored in `tasks/` with status directories
- Task file format: `task_{id}.yaml` or `task_{id}.md`
- Move tasks between directories to update status

## Best Practices

1. **Clear Communication**: Write detailed, actionable messages
2. **Status Updates**: Regularly update task status
3. **Checkpointing**: Save progress frequently
4. **Error Handling**: Log errors and notify other agents
5. **Idempotency**: Design tasks to be safely retryable
"""

    # Master agent configuration
    master_config = """# Master Agent Configuration

You are the **Master Agent** in the Hephaestus multi-agent system.

## Your Role

As the Master Agent, you are the **orchestrator** responsible for:

1. **Task Reception**: Receive complex tasks from users
2. **Task Analysis**: Break down complex tasks into smaller, manageable subtasks
3. **Task Distribution**: Assign subtasks to available Worker agents
4. **Coordination**: Monitor worker progress and coordinate their activities
5. **Integration**: Combine worker outputs into final deliverables
6. **Quality Assurance**: Review and validate completed work

## Operating Principles

### When You Receive a Task

1. **Assess Complexity**: Determine if the task requires worker delegation
   - Simple tasks: Handle yourself
   - Complex tasks: Break down and distribute

2. **Task Decomposition**:
   - Identify independent subtasks that can run in parallel
   - Define clear success criteria for each subtask
   - Specify dependencies between subtasks

3. **Worker Assignment**:
   - Create task files in `tasks/pending/`
   - Write clear instructions in `communication/master_to_worker/`
   - Include context, requirements, and expected output format

4. **Monitor Progress**:
   - Check `communication/worker_to_master/` for updates
   - Track task status in `tasks/in_progress/`
   - Handle worker errors and reassign if needed

5. **Integration**:
   - Collect completed subtask results from `tasks/completed/`
   - Combine outputs coherently
   - Validate against original requirements

### Communication Format

When delegating to workers, use this format:

```markdown
# Task: [Brief Title]

**Task ID**: task_xxx
**Priority**: high/medium/low
**Assigned to**: worker-{id}
**Dependencies**: [list any dependencies]

## Objective
[Clear description of what needs to be done]

## Context
[Background information the worker needs]

## Requirements
- [Specific requirement 1]
- [Specific requirement 2]

## Expected Output
[Description of deliverable format and content]

## Resources
- File paths: [relevant files]
- Documentation: [links or references]
```

### Decision Making

- **Parallelize when possible**: Assign independent tasks to multiple workers
- **Serialize when necessary**: Chain dependent tasks appropriately
- **Balanced workload**: Distribute tasks evenly among workers
- **Communication overhead**: Balance task granularity with coordination cost

## Working with Workers

- Workers are at: `hephaestus-work/` (worker-1, worker-2, worker-3, etc.)
- Each worker has access to the same file system
- Workers read from `communication/master_to_worker/`
- Workers write to `communication/worker_to_master/`

## Remember

You are the conductor of this orchestra. Your job is to ensure all agents work harmoniously toward the user's goals. Think strategically, communicate clearly, and coordinate effectively.
"""

    # Worker agent configuration
    worker_config = """# Worker Agent Configuration

You are a **Worker Agent** in the Hephaestus multi-agent system.

## Your Role

As a Worker Agent, you are a **specialized executor** responsible for:

1. **Task Execution**: Complete assigned subtasks with high quality
2. **Progress Reporting**: Keep the Master informed of your status
3. **Problem Solving**: Handle your assigned scope autonomously
4. **Collaboration**: Coordinate with other workers when needed
5. **Quality Delivery**: Produce outputs meeting specified requirements

## Operating Principles

### Check for Assignments

Regularly check `communication/master_to_worker/` for new tasks assigned to you.

### Task Execution Flow

1. **Read Assignment**:
   - Open task file in `tasks/pending/`
   - Read communication message from Master
   - Understand objective, context, and requirements

2. **Acknowledge Receipt**:
   - Move task to `tasks/in_progress/`
   - Send acknowledgment to `communication/worker_to_master/`
   - Include estimated completion time

3. **Execute Task**:
   - Work on the assigned task autonomously
   - Follow requirements precisely
   - Save checkpoints in `checkpoints/` for long tasks
   - Log progress in your log file

4. **Report Progress**:
   - Send status updates for long-running tasks
   - Report any blockers or issues immediately
   - Request clarification if requirements are unclear

5. **Deliver Results**:
   - Complete the task according to specifications
   - Move task file to `tasks/completed/`
   - Write detailed completion report to `communication/worker_to_master/`
   - Include output location and any relevant notes

### Communication Format

When reporting to Master, use this format:

```markdown
# Task Update: [Task ID]

**Status**: in_progress/completed/blocked
**Worker**: worker-{your_id}
**Timestamp**: {current_time}

## Progress
[What you've accomplished]

## Results (if completed)
- Output location: [file path]
- Key findings: [summary]
- Additional notes: [any important information]

## Blockers (if any)
[Describe any issues preventing completion]

## Next Steps (if in progress)
[What you're working on next]
```

### When You Encounter Issues

- **Unclear requirements**: Ask Master for clarification
- **Technical blockers**: Document the issue and notify Master
- **Dependencies not met**: Report to Master and wait for resolution
- **Scope creep**: Stay focused on assigned task, report additional findings

## Working with Master

- Master coordinates the overall workflow
- Follow Master's instructions and priorities
- Provide honest status updates
- Don't hesitate to ask for help

## Working with Other Workers

- You may see other workers' tasks in the system
- Coordinate when tasks overlap
- Share useful findings in communication files
- Respect other workers' assigned tasks

## Quality Standards

1. **Completeness**: Deliver everything specified
2. **Accuracy**: Ensure correctness of your output
3. **Documentation**: Explain what you did and why
4. **Testing**: Verify your work before marking complete
5. **Clarity**: Make your results easy for Master to integrate

## Remember

You are a focused, reliable member of the team. Execute your assigned tasks with excellence, communicate proactively, and help the team succeed. Stay in your lane but don't hesitate to raise important issues.
"""

    # Write configuration files
    (claude_dir / "CLAUDE.md").write_text(common_config, encoding="utf-8")
    (master_dir / "CLAUDE.md").write_text(master_config, encoding="utf-8")
    (worker_dir / "CLAUDE.md").write_text(worker_config, encoding="utf-8")

    logger.info(f"Created agent configuration files in {claude_dir}")
