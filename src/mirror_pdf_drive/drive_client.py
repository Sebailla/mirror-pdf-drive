"""Google Drive upload client.

The public surface is :func:`upload_pdf`. The client only knows
how to talk to Drive; it does not know how credentials were
obtained (that is ``auth.py``'s job).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from . import exceptions

log = logging.getLogger(__name__)

# A structural type for the drive service, kept loose on purpose
# to avoid leaking googleapiclient types into the orchestrator.
DriveService = Any


def _is_truthy_id(file_entry: dict[str, Any] | None) -> bool:
    return bool(file_entry and file_entry.get("id"))


def _escape_query_string(value: str) -> str:
    """Escape a string for safe interpolation into a Drive API query.

    The Drive API v3 query language uses single quotes for string
    literals. A literal single quote inside the value is escaped with
    a backslash, and a literal backslash is escaped as ``\\``. The
    resulting string is safe to drop between single quotes in a
    query like ``name='<value>'``.

    Order matters: backslashes must be escaped BEFORE single quotes,
    otherwise the escaped backslashes would be re-escaped.

    Examples:
        >>> _escape_query_string("simple")
        "simple"
        >>> _escape_query_string("O'Brien")
        "O\\'Brien"
        >>> _escape_query_string("back\\slash")
        "back\\\\slash"
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def find_file_in_folder(service: DriveService, name: str, folder_id: str) -> dict[str, Any] | None:
    """Find a file by ``name`` in a Drive folder. Returns the file dict or None.

    Raises ``UploadFailedError`` if the folder doesn't exist or the API
    returns an HTTP error. A missing file in an existing folder returns None.
    """
    query = (
        f"name='{_escape_query_string(name)}' "
        f"and '{folder_id}' in parents and trashed=false"
    )
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
    except HttpError as exc:
        raise exceptions.UploadFailedError(
            f"Failed to look up files in folder {folder_id}",
            context={
                "folder_id": folder_id,
                "file_name": name,
                "api_error": str(exc),
            },
        ) from exc
    files = results.get("files", [])
    return files[0] if files else None


def create_file(service: DriveService, name: str, folder_id: str, pdf_path: Path) -> str:
    """Upload a new file to Drive. Returns the new file id."""
    file_metadata = {"name": name, "parents": [folder_id]}
    media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    except HttpError as exc:
        raise exceptions.UploadFailedError(
            f"Failed to upload {pdf_path.name}",
            context={"pdf_path": str(pdf_path), "api_error": str(exc)},
        ) from exc
    return file.get("id", "")


def update_file(service: DriveService, file_id: str, pdf_path: Path) -> str:
    """Replace the content of an existing Drive file. Returns the file id."""
    media = MediaFileUpload(str(pdf_path), mimetype="application/pdf")
    try:
        file = service.files().update(fileId=file_id, media_body=media, fields="id").execute()
    except HttpError as exc:
        raise exceptions.UploadFailedError(
            f"Failed to update {pdf_path.name}",
            context={
                "pdf_path": str(pdf_path),
                "file_id": file_id,
                "api_error": str(exc),
            },
        ) from exc
    return file.get("id", "")


def next_versioned_name(service: DriveService, name: str, folder_id: str) -> str:
    """Compute a non-clashing name by appending ``-N`` before the extension."""
    stem, dot, suffix = name.rpartition(".")
    base = stem or name
    ext = f".{suffix}" if dot else ""
    n = 1
    while True:
        candidate = f"{base}-{n}{ext}"
        if not find_file_in_folder(service, candidate, folder_id):
            return candidate
        n += 1


def find_or_create_folder(service: DriveService, name: str, parent_id: str) -> str:
    """Find a folder by ``name`` inside ``parent_id``. Create it if missing.

    Idempotent: safe to call multiple times for the same ``name``/``parent_id``.

    Raises ``UploadFailedError`` on API errors.
    """
    query = (
        f"name='{_escape_query_string(name)}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
    except HttpError as exc:
        raise exceptions.UploadFailedError(
            f"Failed to look up folder {name!r} in parent {parent_id}",
            context={
                "folder_name": name,
                "parent_id": parent_id,
                "api_error": str(exc),
            },
        ) from exc

    files = results.get("files", [])
    if files:
        return files[0]["id"]

    file_metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    try:
        created = service.files().create(body=file_metadata, fields="id").execute()
    except HttpError as exc:
        raise exceptions.UploadFailedError(
            f"Failed to create folder {name!r} in parent {parent_id}",
            context={
                "folder_name": name,
                "parent_id": parent_id,
                "api_error": str(exc),
            },
        ) from exc
    return created.get("id", "")


def _resolve_target_folder(
    service: DriveService,
    root_folder_id: str,
    subfolder_path: list[str],
) -> str:
    """Walk the chain of subfolders under ``root_folder_id``, creating as needed.

    Returns the final folder id where files should be uploaded.
    """
    current = root_folder_id
    for name in subfolder_path:
        current = find_or_create_folder(service, name, current)
    return current


def upload_pdf(
    pdf_path: Path,
    drive_service: DriveService,
    folder_id: str,
    conflict_strategy: str,
    subfolder_path: list[str] | None = None,
) -> str:
    """Upload ``pdf_path`` to Drive, applying ``conflict_strategy``.

    If ``subfolder_path`` is provided (e.g. ``["docs", "operacion"]``),
    the chain of folders is created (or reused) under ``folder_id`` and
    the file is uploaded to the final folder. If None, the file goes
    directly to ``folder_id``.

    Returns the Drive file id of the (possibly existing) file.
    """
    target = _resolve_target_folder(
        drive_service, folder_id, subfolder_path or []
    )
    file_name = pdf_path.name

    if conflict_strategy == "skip":
        existing = find_file_in_folder(drive_service, file_name, target)
        if _is_truthy_id(existing):
            log.info("skip (exists): %s", file_name)
            assert existing is not None  # for type-checkers
            return existing["id"]

    if conflict_strategy == "replace":
        existing = find_file_in_folder(drive_service, file_name, target)
        if _is_truthy_id(existing):
            assert existing is not None
            return update_file(drive_service, existing["id"], pdf_path)

    if conflict_strategy == "version":
        file_name = next_versioned_name(drive_service, file_name, target)

    return create_file(drive_service, file_name, target, pdf_path)


__all__ = [
    "upload_pdf",
    "find_file_in_folder",
    "find_or_create_folder",
    "create_file",
    "update_file",
    "next_versioned_name",
]
