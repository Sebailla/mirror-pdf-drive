"""OAuth authentication for the Google Drive API.

Scope is intentionally narrow (``drive.file``). The default
auth directory follows XDG: ``~/.config/mirror-pdf-drive/``,
overridable via the ``MIRROR_PDF_DRIVE_AUTH_DIR`` env var.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import exceptions
from .config import AuthConfig

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def resolve_auth_dir(auth_config: AuthConfig) -> Path:
    """Resolve the auth directory, honoring env var and config overrides."""
    env_dir = os.environ.get("MIRROR_PDF_DRIVE_AUTH_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    if auth_config.dir:
        return Path(os.path.expandvars(str(auth_config.dir))).expanduser()
    return Path.home() / ".config" / "mirror-pdf-drive"


def resolve_client_secret_path(auth_config: AuthConfig) -> Path:
    return resolve_auth_dir(auth_config) / auth_config.client_secret_file


def resolve_token_path(auth_config: AuthConfig) -> Path:
    return resolve_auth_dir(auth_config) / auth_config.token_file


def load_or_refresh_credentials(
    auth_config: AuthConfig,
) -> Credentials | None:
    """Load credentials from disk; refresh if expired. Returns None if absent."""
    token_path = resolve_token_path(auth_config)
    if not token_path.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds if creds and creds.valid else None


def run_oauth_flow(auth_config: AuthConfig) -> None:
    """Run the full OAuth flow and persist the token to disk."""
    client_secret = resolve_client_secret_path(auth_config)
    if not client_secret.exists():
        raise FileNotFoundError(
            f"client_secret.json not found at {client_secret}. "
            "Download it from GCP Console: "
            "https://console.cloud.google.com/apis/credentials"
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
    creds = flow.run_local_server(port=0)

    token_path = resolve_token_path(auth_config)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())


def get_drive_service(auth_config: AuthConfig) -> Any:
    """Return an authenticated Drive v3 client, or raise AuthRequiredError."""
    creds = load_or_refresh_credentials(auth_config)
    if not creds:
        raise exceptions.AuthRequiredError(
            "OAuth token not found or invalid. Run 'mirror-pdf-drive --init' to authenticate.",
            context={"auth_dir": str(resolve_auth_dir(auth_config))},
        )
    return build("drive", "v3", credentials=creds)


__all__ = [
    "SCOPES",
    "get_drive_service",
    "run_oauth_flow",
    "load_or_refresh_credentials",
    "resolve_auth_dir",
    "resolve_client_secret_path",
    "resolve_token_path",
]
