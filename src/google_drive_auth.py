"""
Google Drive OAuth authentication and document retrieval.

This module handles OAuth 2.0 authentication with Google Drive API
and provides functions to retrieve document content.
"""

import json
import os
import re
import webbrowser
import threading
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import Config
from src.logger import get_logger


# OAuth 2.0 scopes - we only need read-only access to Drive files
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Token storage location
TOKEN_FILE = Path(Config.OUTPUT_DIR) / "gdrive_token.json"

# OAuth client config file path (user needs to provide this)
CLIENT_CONFIG_FILE = Path.cwd() / "gdrive_credentials.json"


# Global variables to capture OAuth callback
_oauth_code = None
_oauth_error = None
logger = get_logger(__name__)
_server_ready = threading.Event()


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler to capture OAuth callback."""

    def do_GET(self):
        """Handle the OAuth redirect."""
        global _oauth_code, _oauth_error

        # Parse the callback URL
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Extract code or error
        if 'code' in params:
            _oauth_code = params['code'][0]
            message = "Authentication successful! You can close this window and return to the application."
            self.send_response(200)
        elif 'error' in params:
            _oauth_error = params['error'][0]
            message = f"Authentication failed: {_oauth_error}. You can close this window."
            self.send_response(400)
        else:
            message = "Unknown response from Google. You can close this window."
            self.send_response(400)

        # Send HTML response
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = f"""
        <html>
        <head><title>OAuth Authentication</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h2>{message}</h2>
            <p>This window can be closed.</p>
            <script>window.close();</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress server log messages."""
        pass


def authenticate_automatically() -> Tuple[bool, str]:
    """
    Perform OAuth authentication with automatic browser flow.

    This function:
    1. Starts a local HTTP server to catch the OAuth callback
    2. Opens the user's browser to Google's authorization page
    3. Waits for the user to authorize
    4. Automatically captures and processes the authorization code

    Returns:
        Tuple of (success: bool, message: str)
    """
    global _oauth_code, _oauth_error

    # Reset global state
    _oauth_code = None
    _oauth_error = None

    # Check for credentials file
    if not CLIENT_CONFIG_FILE.exists():
        return False, (
            f"⚠️ Setup Required: OAuth credentials file not found.\n\n"
            f"📍 Expected location: {CLIENT_CONFIG_FILE}\n\n"
            f"📖 Please follow the setup guide to create your credentials:\n"
            f"   docs/GOOGLE_OAUTH_SIMPLE_SETUP.md\n\n"
            f"⏱️ This is a one-time setup that takes about 5-10 minutes.\n"
            f"💰 It's completely FREE - no billing required!\n\n"
            f"Once you have the file, just click this button again."
        )

    try:
        # Create the OAuth flow
        flow = Flow.from_client_secrets_file(
            str(CLIENT_CONFIG_FILE),
            scopes=SCOPES,
            redirect_uri='http://localhost:8080/'
        )

        # Generate authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )

        # Start local server to catch callback
        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
        server.timeout = 300  # 5 minute timeout

        def run_server():
            """Run the server in a separate thread."""
            _server_ready.set()
            server.handle_request()  # Handle one request then stop

        # Start server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Wait for server to be ready
        _server_ready.wait(timeout=2)
        _server_ready.clear()

        # Open browser for user to authorize
        webbrowser.open(auth_url)

        # Wait for callback (server will handle one request)
        server_thread.join(timeout=310)  # Wait up to 5 minutes + buffer

        # Check results
        if _oauth_error:
            return False, f"Authentication failed: {_oauth_error}"

        if not _oauth_code:
            return False, (
                "Authentication timed out or was cancelled.\n"
                "Please try again and make sure to approve the authorization in your browser."
            )

        # Exchange code for token
        flow.fetch_token(code=_oauth_code)
        creds = flow.credentials

        # Save credentials
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

        return True, (
            "Success! You are now authenticated with Google Drive.\n"
            "You can now load private Google Docs without making them publicly shared."
        )

    except Exception as e:
        return False, f"Error during authentication: {str(e)}"


def get_auth_url() -> Tuple[str, Flow]:
    """
    Generate OAuth authorization URL for the user to visit.

    Returns:
        Tuple of (authorization_url, flow_object)
        User should visit the URL to authorize the application.
    """
    if not CLIENT_CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"OAuth credentials file not found at {CLIENT_CONFIG_FILE}.\n"
            "Please download your OAuth 2.0 credentials from Google Cloud Console "
            "and save as 'gdrive_credentials.json' in the project root."
        )

    # Use localhost redirect (OOB is deprecated as of 2022)
    # User will copy-paste the full redirect URL from browser
    flow = Flow.from_client_secrets_file(
        str(CLIENT_CONFIG_FILE),
        scopes=SCOPES,
        redirect_uri='http://localhost:8080/'
    )

    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent to ensure we get refresh token
    )

    return auth_url, flow


def exchange_code_for_token(flow: Flow, auth_response: str) -> bool:
    """
    Exchange authorization code for access token and save credentials.

    Args:
        flow: The Flow object from get_auth_url()
        auth_response: Either the full redirect URL or just the authorization code

    Returns:
        True if successful, False otherwise
    """
    try:
        # If the response looks like a URL, extract the code from it
        if auth_response.startswith('http'):
            parsed = urlparse(auth_response)
            code_params = parse_qs(parsed.query).get('code')
            if not code_params:
                logger.error("No 'code' parameter found in redirect URL")
                return False
            auth_code = code_params[0]
        else:
            # Assume it's just the code itself
            auth_code = auth_response

        flow.fetch_token(code=auth_code)
        creds = flow.credentials

        # Save credentials to file
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json())

        return True
    except Exception as e:
        logger.error(f"Error exchanging code for token: {e}")
        return False


def get_credentials() -> Optional[Credentials]:
    """
    Load and refresh credentials if needed.

    Returns:
        Valid Credentials object or None if not authenticated
    """
    if not TOKEN_FILE.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        except RefreshError as e:
            logger.error(f"Error refreshing token: {e}")
            # Token may be invalid, delete it to force re-auth
            TOKEN_FILE.unlink(missing_ok=True)
            return None

    return creds if creds and creds.valid else None


def is_authenticated() -> bool:
    """Check if user has valid credentials."""
    creds = get_credentials()
    return creds is not None


def revoke_credentials() -> bool:
    """
    Revoke and delete stored credentials.

    Returns:
        True if successful
    """
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    return True


def get_document_content(doc_url: str) -> str:
    """
    Retrieve Google Doc content using authenticated Drive API.

    Args:
        doc_url: Full Google Docs URL or just the document ID

    Returns:
        Plain text content of the document
    """
    creds = get_credentials()
    if not creds:
        return "Error: Not authenticated. Please authorize with Google Drive first."

    try:
        # Extract document ID from URL
        doc_id = _extract_doc_id(doc_url)

        # Build Drive API service
        service = build('drive', 'v3', credentials=creds)

        # Export document as plain text
        content = service.files().export(
            fileId=doc_id,
            mimeType='text/plain'
        ).execute()

        return content.decode('utf-8') if isinstance(content, bytes) else content

    except HttpError as e:
        if e.resp.status == 404:
            return f"Error: Document not found. Make sure the document ID is correct."
        elif e.resp.status == 403:
            return f"Error: Access denied. Make sure you have access to this document."
        else:
            return f"Error accessing document: {e}"
    except Exception as e:
        return f"Error retrieving document: {e}"


def _extract_doc_id(doc_url: str) -> str:
    """
    Extract document ID from Google Docs URL using regex.

    Args:
        doc_url: Full URL or just the document ID

    Returns:
        Document ID string
    """
    # Regex to find the document ID in various URL formats
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', doc_url)
    if match:
        return match.group(1)

    # If no match, assume the input is the ID itself
    return doc_url
