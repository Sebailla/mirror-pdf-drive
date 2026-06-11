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


def find_file_in_folder(service: DriveService, name: str, folder_id: str) -> dict[str, Any] | None:
    """Find a file by ``name`` in a Drive folder. Returns the file dict or None.

    Raises ``UploadFailedError`` if the folder doesn't exist or the API
    returns an HTTP error. A missing file in an existing folder returns None.
    """
    query = f"name='{name}' and '{folder_id}' in parents and trashed=false"
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


def upload_pdf(
    pdf_path: Path,
    drive_service: DriveService,
    folder_id: str,
    conflict_strategy: str,
) -> str:
    """Upload ``pdf_path`` to Drive, applying ``conflict_strategy``.

    Returns the Drive file id of the (possibly existing) file.
    """
    file_name = pdf_path.name

    if conflict_strategy == "skip":
        existing = find_file_in_folder(drive_service, file_name, folder_id)
        if _is_truthy_id(existing):
            log.info("skip (exists): %s", file_name)
            assert existing is not None  # for type-checkers
            return existing["id"]

    if conflict_strategy == "replace":
        existing = find_file_in_folder(drive_service, file_name, folder_id)
        if _is_truthy_id(existing):
            assert existing is not None
            return update_file(drive_service, existing["id"], pdf_path)

    if conflict_strategy == "version":
        file_name = next_versioned_name(drive_service, file_name, folder_id)

    return create_file(drive_service, file_name, folder_id, pdf_path)


__all__ = [
    "upload_pdf",
    "find_file_in_folder",
    "create_file",
    "update_file",
    "next_versioned_name",
]
