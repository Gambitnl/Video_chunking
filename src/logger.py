"""Centralized logging system for D&D Session Processor"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import sys


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
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler - important messages only
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

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

    def get_recent_logs(self, lines: int = 100) -> str:
        """Get recent log entries"""
        if not self.log_file.exists():
            return "No log file found."

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                return ''.join(recent_lines)
        except Exception as e:
            return f"Error reading log file: {e}"

    def get_error_logs(self, lines: int = 50) -> str:
        """Get recent error and warning log entries"""
        if not self.log_file.exists():
            return "No log file found."

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                error_lines = [
                    line for line in all_lines
                    if 'ERROR' in line or 'WARNING' in line or 'CRITICAL' in line
                ]
                recent_errors = error_lines[-lines:]
                if not recent_errors:
                    return "No errors or warnings found."
                return ''.join(recent_errors)
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


# Initialize logging on module import
_logger_instance.info("Logging system initialized")
