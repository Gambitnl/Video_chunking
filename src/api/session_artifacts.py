"""
Session Artifacts API - RESTful endpoints for session artifact management.

This module provides API endpoints that return JSON metadata and stream file/session
downloads. It wraps the SessionArtifactService backend and handles serialization,
error responses, and file streaming.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..session_artifact_service import (
    SessionArtifactService,
    SessionDirectorySummary,
    ArtifactMetadata,
    ArtifactPreview,
    SessionArtifactServiceError,
)
from ..logger import get_logger
from ..config import Config


logger = get_logger(__name__)


class SessionArtifactsAPI:
    """
    API for session artifact operations.

    Provides JSON endpoints for listing sessions, getting metadata, directory trees,
    file previews, and file downloads. All responses follow a consistent format with
    status, data, and error fields.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the API.

        Args:
            output_dir: Base output directory (defaults to Config.OUTPUT_DIR)
        """
        self.service = SessionArtifactService(output_dir=output_dir)
        self.logger = get_logger('session_artifacts_api')

    def _success_response(self, data: Any) -> Dict[str, Any]:
        """
        Create a success response.

        Args:
            data: Response data

        Returns:
            Standardized success response dictionary
        """
        return {
            "status": "success",
            "data": data,
            "error": None,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _error_response(self, message: str, status: str = "error") -> Dict[str, Any]:
        """
        Create an error response.

        Args:
            message: Error message
            status: Status code (error, not_found, invalid)

        Returns:
            Standardized error response dictionary
        """
        return {
            "status": status,
            "data": None,
            "error": message,
            "timestamp": datetime.utcnow().isoformat()
        }

    def list_sessions(self) -> Dict[str, Any]:
        """
        List all sessions.

        Returns:
            Response dictionary with session list
        """
        try:
            summaries = self.service.list_sessions()

            # Convert to dictionaries
            sessions = [
                {
                    "name": s.name,
                    "relative_path": s.relative_path,
                    "file_count": s.file_count,
                    "total_size_bytes": s.total_size_bytes,
                    "created": s.created.isoformat(),
                    "modified": s.modified.isoformat(),
                }
                for s in summaries
            ]

            return self._success_response({
                "sessions": sessions,
                "count": len(sessions),
            })
        except Exception as e:
            self.logger.error(f"Failed to list sessions: {e}", exc_info=True)
            return self._error_response(f"Failed to list sessions: {str(e)}")

    def get_directory_tree(self, relative_path: str) -> Dict[str, Any]:
        """
        Get directory listing for a session or subdirectory.

        Args:
            relative_path: Relative path from output directory

        Returns:
            Response dictionary with directory listing
        """
        if not relative_path:
            return self._error_response("relative_path is required", status="invalid")

        try:
            artifacts = self.service.list_directory(relative_path)

            # Convert to dictionaries
            items = [
                {
                    "name": a.name,
                    "relative_path": a.relative_path,
                    "artifact_type": a.artifact_type,
                    "size_bytes": a.size_bytes,
                    "created": a.created.isoformat(),
                    "modified": a.modified.isoformat(),
                    "is_directory": a.is_directory,
                }
                for a in artifacts
            ]

            return self._success_response({
                "relative_path": relative_path,
                "items": items,
                "count": len(items),
            })
        except SessionArtifactServiceError as e:
            if "does not exist" in str(e):
                return self._error_response(str(e), status="not_found")
            return self._error_response(str(e), status="invalid")
        except Exception as e:
            self.logger.error(f"Failed to get tree for {relative_path}: {e}", exc_info=True)
            return self._error_response(f"Failed to get directory tree: {str(e)}")

    def get_artifact_metadata(self, relative_path: str) -> Dict[str, Any]:
        """
        Get metadata for a specific artifact.

        Args:
            relative_path: Relative path to artifact

        Returns:
            Response dictionary with artifact metadata
        """
        if not relative_path:
            return self._error_response("relative_path is required", status="invalid")

        try:
            metadata = self.service.get_artifact_metadata(relative_path)

            return self._success_response({
                "name": metadata.name,
                "relative_path": metadata.relative_path,
                "artifact_type": metadata.artifact_type,
                "size_bytes": metadata.size_bytes,
                "created": metadata.created.isoformat(),
                "modified": metadata.modified.isoformat(),
                "is_directory": metadata.is_directory,
            })
        except SessionArtifactServiceError as e:
            if "does not exist" in str(e):
                return self._error_response(str(e), status="not_found")
            return self._error_response(str(e), status="invalid")
        except Exception as e:
            self.logger.error(f"Failed to get metadata for {relative_path}: {e}", exc_info=True)
            return self._error_response(f"Failed to get artifact metadata: {str(e)}")

    def get_file_preview(
        self,
        relative_path: str,
        max_size_kb: int = 10,
        encoding: str = "utf-8"
    ) -> Dict[str, Any]:
        """
        Get file content preview.

        Args:
            relative_path: Relative path to file
            max_size_kb: Maximum size to preview in KB
            encoding: Text encoding to use

        Returns:
            Response dictionary with file content
        """
        if not relative_path:
            return self._error_response("relative_path is required", status="invalid")

        try:
            max_bytes = max_size_kb * 1024
            preview = self.service.get_text_preview(
                relative_path=relative_path,
                max_bytes=max_bytes,
                encoding=encoding
            )

            return self._success_response({
                "relative_path": preview.relative_path,
                "content": preview.content,
                "truncated": preview.truncated,
                "encoding": preview.encoding,
                "byte_length": preview.byte_length,
            })
        except SessionArtifactServiceError as e:
            if "does not exist" in str(e) or "not a file" in str(e):
                return self._error_response(str(e), status="not_found")
            return self._error_response(str(e), status="invalid")
        except Exception as e:
            self.logger.error(f"Failed to preview file {relative_path}: {e}", exc_info=True)
            return self._error_response(f"Failed to preview file: {str(e)}")

    def download_file(self, relative_path: str) -> Optional[Tuple[Path, str]]:
        """
        Get file path for download.

        Args:
            relative_path: Relative path to file

        Returns:
            Tuple of (file_path, filename) or None if not found
        """
        if not relative_path:
            return None

        try:
            # Resolve the path through the service (sandboxed)
            artifact_path = self.service._resolve_relative_path(relative_path)

            if not artifact_path.exists() or not artifact_path.is_file():
                return None

            return (artifact_path, artifact_path.name)
        except Exception as e:
            self.logger.error(f"Failed to prepare file download: {e}", exc_info=True)
            return None

    def download_session(self, relative_path: str) -> Optional[Tuple[Path, str]]:
        """
        Create and get path to session zip file for download.

        Args:
            relative_path: Relative path to session directory

        Returns:
            Tuple of (zip_path, filename) or None if failed
        """
        if not relative_path:
            return None

        try:
            zip_path = self.service.create_session_zip(relative_path)
            if zip_path is None:
                return None

            return (zip_path, zip_path.name)
        except Exception as e:
            self.logger.error(f"Failed to create session zip: {e}", exc_info=True)
            return None


# Global API instance (can be imported by other modules)
_api_instance: Optional[SessionArtifactsAPI] = None


def get_api_instance(output_dir: Optional[Path] = None) -> SessionArtifactsAPI:
    """
    Get or create the global API instance.

    Args:
        output_dir: Base output directory (only used on first call)

    Returns:
        SessionArtifactsAPI instance
    """
    global _api_instance
    if _api_instance is None:
        _api_instance = SessionArtifactsAPI(output_dir=output_dir)
    return _api_instance


# Convenience functions for direct use
def list_sessions_api() -> Dict[str, Any]:
    """List all sessions (convenience wrapper)."""
    api = get_api_instance()
    return api.list_sessions()


def get_directory_tree_api(relative_path: str) -> Dict[str, Any]:
    """Get directory tree (convenience wrapper)."""
    api = get_api_instance()
    return api.get_directory_tree(relative_path)


def get_artifact_metadata_api(relative_path: str) -> Dict[str, Any]:
    """Get artifact metadata (convenience wrapper)."""
    api = get_api_instance()
    return api.get_artifact_metadata(relative_path)


def get_file_preview_api(
    relative_path: str,
    max_size_kb: int = 10,
    encoding: str = "utf-8"
) -> Dict[str, Any]:
    """Get file preview (convenience wrapper)."""
    api = get_api_instance()
    return api.get_file_preview(relative_path, max_size_kb, encoding)


def download_file_api(relative_path: str) -> Optional[Tuple[Path, str]]:
    """Download file (convenience wrapper)."""
    api = get_api_instance()
    return api.download_file(relative_path)


def download_session_api(relative_path: str) -> Optional[Tuple[Path, str]]:
    """Download session (convenience wrapper)."""
    api = get_api_instance()
    return api.download_session(relative_path)
