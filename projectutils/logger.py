import logging
import os
import sys
from pathlib import Path

from .env import get_logs_dir


def _get_log_level_from_env() -> int:
    """
    Get logging level from LOG_LEVEL environment variable.

    Returns:
        The logging level constant (e.g., logging.INFO, logging.DEBUG)
    """
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Map string levels to logging constants
    level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,  # Alternative spelling
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.CRITICAL,  # Alternative spelling
    }

    return level_mapping.get(level_str, logging.INFO)


def setup_logger(script_file_path: str, level: int = None) -> logging.Logger:
    """
    Sets up a logger for a given script file.

    Args:
        script_file_path: The __file__ path of the script.
        level: The logging level (e.g., logging.INFO, logging.DEBUG).
               If None, reads from LOG_LEVEL environment variable (defaults to INFO).

    Returns:
        A configured logger instance.
    """
    # Get level from environment variable if not explicitly provided
    if level is None:
        level = _get_log_level_from_env()

    # Convert to Path object for easier manipulation
    script_path = Path(script_file_path).resolve()

    # Try to get relative path from current working directory
    try:
        # Get relative path from cwd, which should be the project root
        relative_path = script_path.relative_to(Path.cwd())
    except ValueError:
        # If script is outside cwd, fall back to using the full path
        # but replace path separators to make it filesystem-safe
        relative_path = Path(str(script_path).replace(os.sep, "_"))

    # Create a unique identifier using the relative path without extension
    script_identifier = str(relative_path.with_suffix(""))
    # Replace path separators with dots for logger name (follows Python module naming)
    logger_name = script_identifier.replace(os.sep, ".")
    # Replace path separators with underscores for log filename (filesystem-safe)
    log_filename = script_identifier.replace(os.sep, "_")

    logs_dir = get_logs_dir()

    # Ensure logs_dir is a Path object if get_logs_dir() returns a string
    if isinstance(logs_dir, str):
        logs_dir = Path(logs_dir)

    # Create logs directory if it doesn't exist
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f"{log_filename}.log"

    # Create logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)

    # Create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    # Add handlers to the logger
    # Clear existing handlers to prevent duplicate messages if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
