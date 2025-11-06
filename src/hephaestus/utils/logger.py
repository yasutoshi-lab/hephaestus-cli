"""Logging utility for Hephaestus-CLI.

This module provides structured logging functionality with support for
file and console output, log rotation, and sensitive information masking.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import re


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive information in logs."""

    PATTERNS = [
        (re.compile(r'(api[_-]?key\s*[=:]\s*)[^\s]+', re.IGNORECASE), r'\1****'),
        (re.compile(r'(password\s*[=:]\s*)[^\s]+', re.IGNORECASE), r'\1****'),
        (re.compile(r'(token\s*[=:]\s*)[^\s]+', re.IGNORECASE), r'\1****'),
        (re.compile(r'(secret\s*[=:]\s*)[^\s]+', re.IGNORECASE), r'\1****'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive information in log messages."""
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        return True


def setup_logger(
    name: str,
    log_file: Optional[Path] = None,
    level: str = "INFO",
    log_format: Optional[str] = None,
) -> logging.Logger:
    """Set up a logger with file and console handlers.

    Args:
        name: Logger name (typically module name)
        log_file: Optional path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Default format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(SensitiveDataFilter())
    logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(SensitiveDataFilter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get an existing logger by name.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
