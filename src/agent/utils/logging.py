"""
Logging configuration for SpecKit Agent System.

Provides configurable logging with file and console output.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console_output: bool = True,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging configuration for the agent system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console_output: Whether to output to console
        log_format: Optional custom log format string

    Returns:
        Configured logger instance
    """
    # Get or create logger
    logger = logging.getLogger("speckit-agent")

    # Clear existing handlers
    logger.handlers.clear()

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Default format
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "speckit-agent") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (defaults to speckit-agent)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def configure_from_env() -> logging.Logger:
    """
    Configure logging from environment variables.

    Environment variables:
        SPECKIT_LOG_LEVEL: Log level (default: INFO)
        SPECKIT_LOG_FILE: Path to log file (optional)
        SPECKIT_LOG_CONSOLE: Enable console output (default: true)

    Returns:
        Configured logger instance
    """
    import os

    level = os.environ.get("SPECKIT_LOG_LEVEL", "INFO")
    log_file = os.environ.get("SPECKIT_LOG_FILE")
    console = os.environ.get("SPECKIT_LOG_CONSOLE", "true").lower() == "true"

    return setup_logging(
        level=level,
        log_file=Path(log_file) if log_file else None,
        console_output=console
    )


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(self, logger: logging.Logger, level: str):
        """
        Initialize log context.

        Args:
            logger: Logger to modify
            level: Temporary log level
        """
        self.logger = logger
        self.new_level = getattr(logging, level.upper(), logging.INFO)
        self.original_level = None

    def __enter__(self):
        """Enter context - change log level."""
        self.original_level = self.logger.level
        self.logger.setLevel(self.new_level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original log level."""
        if self.original_level is not None:
            self.logger.setLevel(self.original_level)
        return False


# Default logger instance
_default_logger: Optional[logging.Logger] = None


def init_default_logger(level: str = "INFO") -> logging.Logger:
    """
    Initialize the default logger.

    Args:
        level: Log level

    Returns:
        Default logger instance
    """
    global _default_logger
    _default_logger = setup_logging(level=level)
    return _default_logger


def log_info(message: str) -> None:
    """Log an info message."""
    logger = _default_logger or get_logger()
    logger.info(message)


def log_debug(message: str) -> None:
    """Log a debug message."""
    logger = _default_logger or get_logger()
    logger.debug(message)


def log_warning(message: str) -> None:
    """Log a warning message."""
    logger = _default_logger or get_logger()
    logger.warning(message)


def log_error(message: str) -> None:
    """Log an error message."""
    logger = _default_logger or get_logger()
    logger.error(message)
