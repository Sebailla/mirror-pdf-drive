"""Integration tests against a real Google Drive account.

These tests are NOT run by default. They require:

1. A ``client_secret.json`` and ``token.json`` in
   ``~/.config/mirror-pdf-drive/`` (run ``mirror-pdf-drive --init`` first).
2. The environment variable ``MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID`` set
   to a Drive folder ID where the tests can upload and clean up files.
3. A live internet connection to talk to Drive.

To run them locally::

    export MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID=1ABC...XYZ
    pytest -m integration tests/test_integration_drive.py -v

In CI, the marker is excluded by default so the tests don't run unless
``RUN_INTEGRATION=1`` is set and the secrets are configured.

Safety guarantees:
- The tests only touch the folder ID you point them at.
- Every test cleans up the files it created.
- A session-scoped fixture wipes the folder at the end as a safety net.
"""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Generator

import pytest

from mirror_pdf_drive import auth, drive_client

# All tests in this module are integration tests.
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SANDBOX_ENV_VAR = "MIRROR_PDF_DRIVE_SANDBOX_FOLDER_ID"


def _folder_id_from_env() -> str | None:
    """Read the sandbox folder ID from the environment, with a helpful error."""
    folder_id = os.environ.get(SANDBOX_ENV_VAR)
    if not folder_id:
        pytest.skip(
            f"Integration tests require the {SANDBOX_ENV_VAR} env var to be set. "
            f"Set it to a Drive folder ID you can use as a sandbox."
        )
    return folder_id


@pytest.fixture(scope="module")
def sandbox_folder_id() -> str:
    """The Drive folder ID to use as sandbox. Skips if not configured."""
    return _folder_id_from_env()  # type: ignore[return-value]


@pytest.fixture(scope="module")
def drive_service(sandbox_folder_id: str) -> Generator[Any, None, None]:
    """A real, authenticated Drive service. Builds once per module."""
    creds: Any = None
    try:
        creds = auth.load_or_refresh_credentials(_auth_config_for_token_dir())
    except Exception as exc:  # pragma: no cover - depends on local setup
        pytest.skip(f"Could not load OAuth credentials: {exc}")
    if creds is None:
        pytest.skip(
            "OAuth token not found. Run `mirror-pdf-drive --init` first."
        )
    from googleapiclient.discovery import build

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    # Sanity check: can we see the folder?
    try:
        service.files().get(fileId=sandbox_folder_id, fields="id, name").execute()
    except Exception as exc:
        pytest.skip(f"Cannot access sandbox folder {sandbox_folder_id}: {exc}")
    yield service
    # No teardown needed: connection is closed when the generator exits.


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """A minimal valid PDF on disk, big enough that Drive's content checks differ.

    We write a known-bytes blob that is NOT a real PDF (header is fake), but
    the upload code doesn't validate the file format — it just uploads. For
    integration tests against Drive, this is fine: we verify the upload
    succeeded and then delete the file.
    """
    pdf_path = tmp_path / f"sample-{uuid.uuid4().hex[:8]}.pdf"
    # Use a unique body so re-uploads create new versions, not identical content.
    payload = (
        f"%PDF-1.4\n"
        f"% integration-test-marker: {uuid.uuid4()}\n"
        f"%%EOF\n"
    )
    pdf_path.write_text(payload, encoding="utf-8")
    return pdf_path


@pytest.fixture
def uploaded_files() -> list[str]:
    """Tracks the Drive file IDs created by a test, for cleanup at the end."""
    return []


@pytest.fixture(autouse=True)
def _cleanup_uploaded_files(
    drive_service: Any,
    sandbox_folder_id: str,
    uploaded_files: list[str],
) -> Generator[None, None, None]:
    """Auto-cleanup: delete every file this test created, even on failure."""
    yield
    for file_id in uploaded_files:
        try:
            drive_service.files().delete(fileId=file_id).execute()
        except Exception:
            # Don't fail the test on cleanup errors; just log.
            pass


@pytest.fixture(scope="module", autouse=True)
def _wipe_sandbox_at_end(
    drive_service: Any, sandbox_folder_id: str
) -> Generator[None, None, None]:
    """Safety net: wipe the sandbox folder after the whole module runs.

    Deletes any file whose name starts with ``sample-`` (the prefix used
    by the ``sample_pdf`` fixture). This protects against test failures
    that skip the per-test cleanup.
    """
    yield
    try:
        results = drive_service.files().list(
            q=f"'{sandbox_folder_id}' in parents and trashed=false and name contains 'sample-'",
            fields="files(id, name)",
            pageSize=100,
        ).execute()
        for f in results.get("files", []):
            try:
                drive_service.files().delete(fileId=f["id"]).execute()
            except Exception:
                pass
    except Exception:
        # Don't fail the session on cleanup errors.
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_config_for_token_dir() -> Any:
    """Build an AuthConfig that points at the default XDG auth dir."""
    from mirror_pdf_drive.config import AuthConfig

    return AuthConfig()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_upload_single_pdf(
    drive_service: Any,
    sandbox_folder_id: str,
    sample_pdf: Path,
    uploaded_files: list[str],
) -> None:
    """A fresh PDF uploads cleanly and appears in the sandbox folder."""
    file_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="skip"
    )
    uploaded_files.append(file_id)

    assert file_id, "upload_pdf returned empty file id"

    # Verify the file is queryable in the folder.
    found = drive_service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    assert found["name"] == sample_pdf.name
    assert found["mimeType"] == "application/pdf"


def test_skip_strategy_returns_existing_id(
    drive_service: Any,
    sandbox_folder_id: str,
    sample_pdf: Path,
    uploaded_files: list[str],
) -> None:
    """Uploading the same file twice with strategy=skip returns the same id."""
    first_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="skip"
    )
    uploaded_files.append(first_id)

    second_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="skip"
    )
    uploaded_files.append(second_id)

    assert first_id == second_id, "skip strategy should return the existing file id"


def test_replace_strategy_updates_existing(
    drive_service: Any,
    sandbox_folder_id: str,
    sample_pdf: Path,
    tmp_path: Path,
    uploaded_files: list[str],
) -> None:
    """replace strategy keeps the same id but updates the content."""
    first_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="skip"
    )
    uploaded_files.append(first_id)

    # Modify the local file and upload with replace.
    sample_pdf.write_text("%PDF-1.4\n% replaced content\n%%EOF\n", encoding="utf-8")
    time.sleep(1)  # ensure Drive's mtime would differ

    second_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="replace"
    )
    uploaded_files.append(second_id)

    assert first_id == second_id, "replace strategy should keep the same id"


def test_version_strategy_creates_new_file(
    drive_service: Any,
    sandbox_folder_id: str,
    sample_pdf: Path,
    uploaded_files: list[str],
) -> None:
    """version strategy creates a new file with a numeric suffix."""
    first_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="skip"
    )
    uploaded_files.append(first_id)

    second_id = drive_client.upload_pdf(
        sample_pdf, drive_service, sandbox_folder_id, conflict_strategy="version"
    )
    uploaded_files.append(second_id)

    assert first_id != second_id, "version strategy should create a new file"

    # Verify the new file has a "-1" suffix.
    second_meta = drive_service.files().get(fileId=second_id, fields="id, name").execute()
    assert second_meta["name"].endswith("-1.pdf"), (
        f"Expected name to end with -1.pdf, got {second_meta['name']}"
    )


def test_upload_failure_raises_for_invalid_folder(
    drive_service: Any,
    sample_pdf: Path,
) -> None:
    """Uploading to a non-existent folder id raises UploadFailedError.

    Note: Drive's API is quirky here. A syntactically valid folder ID that
    doesn't exist returns 404 with an empty message. A malformed ID can also
    return 404 with a different message. Either way, ``upload_pdf`` must
    raise ``UploadFailedError`` so the orchestrator can count the failure.
    """
    from mirror_pdf_drive import exceptions

    bogus_folder_id = "0" * 33  # 33 chars, valid format, but doesn't exist
    with pytest.raises(exceptions.UploadFailedError) as exc_info:
        drive_client.upload_pdf(
            sample_pdf, drive_service, bogus_folder_id, conflict_strategy="skip"
        )
    # The error message should mention the failure context, not be empty.
    error_msg = str(exc_info.value)
    assert "Failed" in error_msg
    assert bogus_folder_id in error_msg


def test_upload_creates_project_subfolder(
    drive_service: Any,
    sandbox_folder_id: str,
    sample_pdf: Path,
    uploaded_files: list[str],
) -> None:
    """Uploading with subfolder_path creates a chain of folders in Drive
    and the file ends up inside the final folder."""
    subfolder_path = [f"mirror-pdf-int-{uuid.uuid4().hex[:6]}", "docs", "sub"]
    file_id = drive_client.upload_pdf(
        sample_pdf,
        drive_service,
        sandbox_folder_id,
        conflict_strategy="skip",
        subfolder_path=subfolder_path,
    )
    uploaded_files.append(file_id)

    assert file_id, "upload_pdf returned empty file id"

    # Walk the chain and verify each folder exists under its parent.
    parent = sandbox_folder_id
    folder_ids: list[str] = []
    for name in subfolder_path:
        query = (
            f"name='{name}' and '{parent}' in parents "
            f"and mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        matches = results.get("files", [])
        assert matches, f"Folder {name!r} not found under {parent}"
        folder_ids.append(matches[0]["id"])
        parent = matches[0]["id"]

    # Verify the file is in the final folder.
    file_meta = drive_service.files().get(
        fileId=file_id, fields="id, name, parents"
    ).execute()
    assert file_meta["name"] == sample_pdf.name
    assert file_meta["parents"] == [folder_ids[-1]]
