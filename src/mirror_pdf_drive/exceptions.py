"""Domain exceptions for mirror-pdf-drive.

Each error has a stable string ``code`` used by the CLI and by
external consumers (skill, CI) to classify failures.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for all mirror-pdf-drive errors."""

    code: str = "APP_ERROR"

    def __init__(self, message: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.context:
            return f"{self.message} (context={self.context})"
        return self.message


class ConfigNotFoundError(AppError):
    code = "CONFIG_NOT_FOUND"


class InvalidConfigError(AppError):
    code = "INVALID_CONFIG"


class AuthRequiredError(AppError):
    code = "AUTH_REQUIRED"


class RenderFailedError(AppError):
    code = "RENDER_FAILED"


class UploadFailedError(AppError):
    code = "UPLOAD_FAILED"


__all__ = [
    "AppError",
    "ConfigNotFoundError",
    "InvalidConfigError",
    "AuthRequiredError",
    "RenderFailedError",
    "UploadFailedError",
]
