"""Application restart manager for Gradio UI."""
import os
import sys
import subprocess
from pathlib import Path
from typing import Optional

from src.logger import get_logger

logger = get_logger(__name__)


class RestartManager:
    """Manages application restart functionality."""

    @staticmethod
    def restart_application(delay_seconds: float = 2.0) -> bool:
        """
        Restart the application by spawning a new process and exiting the current one.

        Args:
            delay_seconds: Delay before starting new instance (to allow cleanup)

        Returns:
            True if restart initiated successfully, False otherwise
        """
        try:
            logger.info("=" * 80)
            logger.info("APPLICATION RESTART REQUESTED")
            logger.info("=" * 80)

            # Get the current Python executable and script path
            python_executable = sys.executable
            script_path = Path(__file__).parent.parent / "app.py"

            if not script_path.exists():
                logger.error(f"Cannot find app.py at {script_path}")
                return False

            logger.info(f"Python executable: {python_executable}")
            logger.info(f"Script path: {script_path}")
            logger.info(f"Working directory: {Path.cwd()}")

            # Build the restart command
            if sys.platform == "win32":
                # Windows: Use cmd to run with delay
                restart_cmd = [
                    "cmd",
                    "/c",
                    f"timeout /t {int(delay_seconds)} /nobreak > nul && \"{python_executable}\" \"{script_path}\""
                ]
            else:
                # Unix-like: Use sh with sleep
                restart_cmd = [
                    "sh",
                    "-c",
f"sleep {delay_seconds} && \"{python_executable}\" \"{script_path}\""
                ]

            logger.info(f"Restart command: {' '.join(restart_cmd)}")
            logger.info("Spawning new process...")

            # Spawn the new process detached from current process
            if sys.platform == "win32":
                # Windows: CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS
                subprocess.Popen(
                    restart_cmd,
                    cwd=Path.cwd(),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
                    close_fds=True,
                )
            else:
                # Unix-like: Use nohup for detachment
                subprocess.Popen(
                    restart_cmd,
                    cwd=Path.cwd(),
                    start_new_session=True,
                    close_fds=True,
                )

            logger.info("New process spawned successfully")
            logger.info("Current process will exit in a moment...")
            logger.info("=" * 80)

            # Schedule exit
            import threading
            def delayed_exit():
                import time
                time.sleep(1)  # Give time for response to be sent
                logger.info("Exiting current process for restart...")
                os._exit(0)

            exit_thread = threading.Thread(target=delayed_exit, daemon=True)
            exit_thread.start()

            return True

        except Exception as e:
            logger.exception("Failed to restart application")
            return False

    @staticmethod
    def get_restart_instructions() -> str:
        """Get manual restart instructions for the current platform."""
        if sys.platform == "win32":
            return """
**Manual Restart Instructions (Windows):**

1. Close this browser tab
2. In your terminal/command prompt, press Ctrl+C to stop the server
3. Run `python app.py` again to restart
"""
        else:
            return """
**Manual Restart Instructions (Unix/Linux/Mac):**

1. Close this browser tab
2. In your terminal, press Ctrl+C to stop the server
3. Run `python app.py` again to restart
"""
