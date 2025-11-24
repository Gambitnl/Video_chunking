"""Centralized logging system for D&D Session Processor"""
import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, Sequence
import sys


LOG_LEVEL_CHOICES: Sequence[str] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def _resolve_log_level(level: Union[str, int]) -> int:
    """Normalize log level names and values into logging constants."""
    if isinstance(level, int):
        return level
    if not isinstance(level, str):
        raise ValueError(f"Unsupported log level: {level!r}")

    normalized = level.strip().upper()
    if normalized not in logging._nameToLevel:
        raise ValueError(f"Unsupported log level: {level!r}")
    return logging._nameToLevel[normalized]


class SessionLogger:
    """Unified logging system with file and console output"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._setup_logging()
            SessionLogger._initialized = True

    def _setup_logging(self):
        """Configure logging with both file and console handlers"""
        from .config import Config

        # Create logs directory
        log_dir = Config.PROJECT_ROOT / "logs"
        log_dir.mkdir(exist_ok=True)

        # Log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"session_processor_{timestamp}.log"

        # Create logger
        self.logger = logging.getLogger("DDSessionProcessor")
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        self.logger.handlers.clear()

        # File handler - detailed logs
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(_resolve_log_level(getattr(Config, "LOG_LEVEL_FILE", "DEBUG")))
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler - important messages only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(_resolve_log_level(getattr(Config, "LOG_LEVEL_CONSOLE", "INFO")))
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.file_handler = file_handler
        self.console_handler = console_handler

        # Store paths
        self.log_file = log_file
        self.log_dir = log_dir

        self.logger.info("=" * 80)
        self.logger.info("D&D Session Processor - Logging Started")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info("=" * 80)

    def get_logger(self, name: Optional[str] = None):
        """Get a logger instance"""
        if name:
            return logging.getLogger(f"DDSessionProcessor.{name}")
        return self.logger

    def get_log_file_path(self) -> Path:
        """Return current log file path"""
        return self.log_file

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, exc_info=False, **kwargs):
        """Log error message"""
        self.logger.error(message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info=True, **kwargs):
        """Log critical error message"""
        self.logger.critical(message, exc_info=exc_info, **kwargs)

    def set_console_level(self, level: Union[str, int]):
        """Adjust console handler log level at runtime."""
        resolved = _resolve_log_level(level)
        if hasattr(self, "console_handler"):
            self.console_handler.setLevel(resolved)
        self.logger.info("Console log level set to %s", logging.getLevelName(resolved))

    def set_file_level(self, level: Union[str, int]):
        """Adjust file handler log level at runtime."""
        resolved = _resolve_log_level(level)
        if hasattr(self, "file_handler"):
            self.file_handler.setLevel(resolved)
        self.logger.info("File log level set to %s", logging.getLevelName(resolved))

    def get_console_level(self) -> str:
        """Return active console log level name."""
        if hasattr(self, "console_handler"):
            return logging.getLevelName(self.console_handler.level)
        return logging.getLevelName(logging.INFO)

    def get_file_level(self) -> str:
        """Return active file log level name."""
        if hasattr(self, "file_handler"):
            return logging.getLevelName(self.file_handler.level)
        return logging.getLevelName(logging.DEBUG)

    def _read_last_lines(self, filepath: Path, n_lines: int) -> list[str]:
        """
        Efficiently read the last n lines of a file without reading the entire file.
        """
        if not filepath.exists():
            return []

        block_size = 65536  # 64KB blocks
        lines_found = []

        try:
            with open(filepath, 'rb') as f:
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                if file_size == 0:
                    return []

                remaining_bytes = file_size
                buffer = b""

                while remaining_bytes > 0 and len(lines_found) <= n_lines:
                    # Determine how much to read
                    read_size = min(block_size, remaining_bytes)
                    remaining_bytes -= read_size

                    f.seek(remaining_bytes)
                    chunk = f.read(read_size)

                    # Prepend chunk to buffer
                    buffer = chunk + buffer

                    # Check lines
                    lines = buffer.split(b'\n')

                    # If the file ends with a newline, the last element is empty.
                    # We usually don't want to count that as a "line" for the purpose of "last N lines"
                    # unless the file actually has empty lines at the end.
                    # But standard tools like tail usually ignore the trailing newline split.

                    valid_lines_count = len(lines)
                    if lines and lines[-1] == b"":
                        valid_lines_count -= 1

                    # If we haven't reached start of file, the first line might be partial (lines[0])
                    if remaining_bytes > 0:
                        # We have (valid_lines_count - 1) full lines in this chunk (excluding first partial)
                        # We check if we have enough full lines to satisfy request
                        if valid_lines_count > n_lines:
                            # We have enough.
                            # If lines[-1] is empty, we exclude it from the "last n lines" consideration if we want text lines.
                            # But let's just return the last n lines from the split.

                            # If lines[-1] is empty, we might return it.
                            # If we want 50 lines, and we have 51, and the 51st is empty.
                            # lines[-50:] would include the empty one.

                            # Let's filter out the very last empty element if it exists and we have enough lines without it.
                            start_idx = -n_lines
                            if lines[-1] == b"":
                                # If we strip the last empty one, do we still have enough?
                                if len(lines) - 1 >= n_lines:
                                     return [l.decode('utf-8', errors='replace') for l in lines[-n_lines-1:-1]]
                                else:
                                     # Not enough without the partial line at start?
                                     # We continue reading.
                                     pass
                            else:
                                return [l.decode('utf-8', errors='replace') for l in lines[-n_lines:]]
                    else:
                        # Reached start of file
                        # If the last line is empty, ignore it if we have enough lines
                         if lines[-1] == b"" and len(lines) > n_lines:
                             return [l.decode('utf-8', errors='replace') for l in lines[-n_lines-1:-1]]
                         return [l.decode('utf-8', errors='replace') for l in lines[-n_lines:]]

                # If we exit loop (read whole file)
                lines = buffer.split(b'\n')
                if lines and lines[-1] == b"" and len(lines) > n_lines:
                     return [l.decode('utf-8', errors='replace') for l in lines[-n_lines-1:-1]]
                return [l.decode('utf-8', errors='replace') for l in lines[-n_lines:]]

        except Exception as e:
            # Fallback to simple read if something complex fails, or just log error
            self.logger.error(f"Error reading last lines: {e}")
            return []

    def get_recent_logs(self, lines: int = 100) -> str:
        """Get recent log entries"""
        if not self.log_file.exists():
            return "No log file found."

        try:
            # Use the robust tail implementation
            recent_lines = self._read_last_lines(self.log_file, lines)
            return '\n'.join(recent_lines) + '\n'
        except Exception as e:
            return f"Error reading log file: {e}"

    def get_error_logs(self, lines: int = 50) -> str:
        """Get recent error and warning log entries"""
        if not self.log_file.exists():
            return "No log file found."

        try:
            # For error logs, we might need to scan more than 'lines' to find 'lines' errors.
            # But reading the whole file is bad.
            # Compromise: Read last 20000 lines (approx 2-3MB) and filter errors.
            # If not enough, that's life. We don't want to scan 1GB.

            scan_depth = max(lines * 100, 20000)
            candidates = self._read_last_lines(self.log_file, scan_depth)

            error_lines = [
                line for line in candidates
                if 'ERROR' in line or 'WARNING' in line or 'CRITICAL' in line
            ]

            recent_errors = error_lines[-lines:]
            if not recent_errors:
                return "No errors or warnings found in recent logs."
            return '\n'.join(recent_errors) + '\n'
        except Exception as e:
            return f"Error reading log file: {e}"

    def clear_old_logs(self, days: int = 7):
        """Clear log files older than specified days"""
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        cleared_count = 0

        for log_file in self.log_dir.glob("session_processor_*.log"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    log_file.unlink()
                    cleared_count += 1
            except Exception as e:
                self.logger.warning(f"Could not delete old log file {log_file}: {e}")

        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old log files (older than {days} days)")

        return cleared_count


# Global logger instance
_logger_instance = SessionLogger()


def get_logger(name: Optional[str] = None):
    """Get logger instance - convenience function"""
    return _logger_instance.get_logger(name)


def get_log_file_path() -> Path:
    """Convenience accessor for current log file path"""
    return _logger_instance.get_log_file_path()


def log_session_start(session_id: str, **kwargs):
    """Log the start of a session processing"""
    logger = get_logger("session")
    logger.info("=" * 60)
    logger.info(f"Starting session processing: {session_id}")
    for key, value in kwargs.items():
        logger.info(f"  {key}: {value}")
    logger.info("=" * 60)


def log_session_end(session_id: str, duration: float, success: bool = True):
    """Log the end of a session processing"""
    logger = get_logger("session")
    logger.info("=" * 60)
    if success:
        logger.info(f"Session processing completed: {session_id}")
        logger.info(f"Total duration: {duration:.2f} seconds")
    else:
        logger.error(f"Session processing failed: {session_id}")
        logger.error(f"Duration before failure: {duration:.2f} seconds")
    logger.info("=" * 60)


def log_error_with_context(error: Exception, context: str = ""):
    """Log an error with additional context"""
    logger = get_logger("error")
    if context:
        logger.error(f"Error in {context}: {str(error)}", exc_info=True)
    else:
        logger.error(f"Error: {str(error)}", exc_info=True)


def set_console_log_level(level: Union[str, int]) -> None:
    """Public helper to adjust console logging verbosity."""
    _logger_instance.set_console_level(level)


def set_file_log_level(level: Union[str, int]) -> None:
    """Public helper to adjust file logging verbosity."""
    _logger_instance.set_file_level(level)


def get_console_log_level() -> str:
    """Return active console log level name."""
    return _logger_instance.get_console_level()


def get_file_log_level() -> str:
    """Return active file log level name."""
    return _logger_instance.get_file_level()


# Initialize logging on module import
_logger_instance.info("Logging system initialized")
