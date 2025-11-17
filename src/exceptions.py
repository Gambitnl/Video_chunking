"""Custom exceptions for the D&D Session Processor pipeline."""


class CancelledError(Exception):
    """
    Exception raised when processing is cancelled by the user.

    This exception is used to signal that a processing operation was
    intentionally cancelled by the user (e.g., via a UI cancel button)
    rather than failing due to an error.

    Example:
        >>> from threading import Event
        >>> cancel_event = Event()
        >>> cancel_event.set()
        >>> if cancel_event.is_set():
        ...     raise CancelledError("Processing was cancelled by user")
    """

    def __init__(self, message: str = "Processing was cancelled by user"):
        """
        Initialize the CancelledError exception.

        Args:
            message: Custom cancellation message (default: "Processing was cancelled by user")
        """
        super().__init__(message)
        self.message = message
