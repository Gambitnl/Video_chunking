"""
Google Drive OAuth authentication and document retrieval.

This module handles OAuth 2.0 authentication with Google Drive API
and provides functions to retrieve document content.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import Config


# OAuth 2.0 scopes - we only need read-only access to Drive files
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Token storage location
TOKEN_FILE = Path(Config.OUTPUT_DIR) / "gdrive_token.json"

# OAuth client config file path (user needs to provide this)
CLIENT_CONFIG_FILE = Path.cwd() / "gdrive_credentials.json"


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
                print("Error: No 'code' parameter found in redirect URL")
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
        print(f"Error exchanging code for token: {e}")
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
            print(f"Error refreshing token: {e}")
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
