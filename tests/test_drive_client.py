"""Drive client tests with mocked googleapiclient."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from googleapiclient.errors import HttpError

from mirror_pdf_drive import drive_client, exceptions


def _make_service(existing: dict | None) -> mock.MagicMock:
    """Build a fake drive service whose ``files().list()`` returns ``existing``."""
    service = mock.MagicMock()
    list_result = {"files": [existing] if existing else []}
    service.files().list.return_value.execute.return_value = list_result
    return service


def test_upload_skip_returns_existing_id(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing={"id": "existing123", "name": "doc.pdf"})
    file_id = drive_client.upload_pdf(pdf, service, "folderX", "skip")
    assert file_id == "existing123"
    service.files().create.assert_not_called()
    service.files().update.assert_not_called()


def test_upload_replace_calls_update(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing={"id": "existing123", "name": "doc.pdf"})
    service.files().update.return_value.execute.return_value = {"id": "existing123"}
    file_id = drive_client.upload_pdf(pdf, service, "folderX", "replace")
    assert file_id == "existing123"
    service.files().update.assert_called_once()
    service.files().create.assert_not_called()


def test_upload_version_calls_create_with_versioned_name(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing=None)
    # The version strategy starts probing at doc-1.pdf. Return empty so the
    # first probe wins.
    service.files().list.return_value.execute.return_value = {"files": []}
    service.files().create.return_value.execute.return_value = {"id": "newId"}
    file_id = drive_client.upload_pdf(pdf, service, "folderX", "version")
    assert file_id == "newId"
    create_kwargs = service.files().create.call_args.kwargs
    assert create_kwargs["body"]["name"] == "doc-1.pdf"


def test_upload_create_raises_on_http_error(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing=None)
    service.files().create.return_value.execute.side_effect = HttpError(
        mock.MagicMock(status=500), b"boom"
    )
    with pytest.raises(exceptions.UploadFailedError) as excinfo:
        drive_client.upload_pdf(pdf, service, "folderX", "skip")
    assert excinfo.value.code == "UPLOAD_FAILED"


def test_upload_skip_no_existing_calls_create(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing=None)
    service.files().create.return_value.execute.return_value = {"id": "freshId"}
    file_id = drive_client.upload_pdf(pdf, service, "folderX", "skip")
    assert file_id == "freshId"
    service.files().create.assert_called_once()


def test_update_raises_on_http_error(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = mock.MagicMock()
    service.files().update.return_value.execute.side_effect = HttpError(
        mock.MagicMock(status=500), b"boom"
    )
    with pytest.raises(exceptions.UploadFailedError) as excinfo:
        drive_client.update_file(service, "abc", pdf)
    assert excinfo.value.code == "UPLOAD_FAILED"


# --- find_or_create_folder ---


def test_find_or_create_folder_creates_when_missing() -> None:
    service = mock.MagicMock()
    # list returns empty → must create
    service.files().list.return_value.execute.return_value = {"files": []}
    service.files().create.return_value.execute.return_value = {"id": "newFolderId"}
    folder_id = drive_client.find_or_create_folder(service, "docs", "parentX")
    assert folder_id == "newFolderId"
    create_kwargs = service.files().create.call_args.kwargs
    assert create_kwargs["body"]["name"] == "docs"
    assert create_kwargs["body"]["mimeType"] == "application/vnd.google-apps.folder"
    assert create_kwargs["body"]["parents"] == ["parentX"]


def test_find_or_create_folder_returns_existing() -> None:
    service = mock.MagicMock()
    service.files().list.return_value.execute.return_value = {
        "files": [{"id": "existingFolderId", "name": "docs"}]
    }
    folder_id = drive_client.find_or_create_folder(service, "docs", "parentX")
    assert folder_id == "existingFolderId"
    service.files().create.assert_not_called()


def test_find_or_create_folder_raises_on_http_error_on_list() -> None:
    service = mock.MagicMock()
    service.files().list.return_value.execute.side_effect = HttpError(
        mock.MagicMock(status=500), b"boom"
    )
    with pytest.raises(exceptions.UploadFailedError) as excinfo:
        drive_client.find_or_create_folder(service, "docs", "parentX")
    assert excinfo.value.code == "UPLOAD_FAILED"


def test_find_or_create_folder_raises_on_http_error_on_create() -> None:
    service = mock.MagicMock()
    service.files().list.return_value.execute.return_value = {"files": []}
    service.files().create.return_value.execute.side_effect = HttpError(
        mock.MagicMock(status=500), b"boom"
    )
    with pytest.raises(exceptions.UploadFailedError) as excinfo:
        drive_client.find_or_create_folder(service, "docs", "parentX")
    assert excinfo.value.code == "UPLOAD_FAILED"


# --- upload_pdf with subfolder_path ---


def test_upload_pdf_with_subfolder_path_creates_chain(tmp_path: Path) -> None:
    """When subfolder_path is provided, the chain of folders is created and the file goes to the final folder."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")

    service = mock.MagicMock()
    # list() returns empty for every folder lookup (no existing folders)
    service.files().list.return_value.execute.return_value = {"files": []}
    # First three calls create the folder chain; fourth creates the file
    service.files().create.return_value.execute.side_effect = [
        {"id": "gastosId"},
        {"id": "docsId"},
        {"id": "operacionId"},
        {"id": "fileId"},
    ]

    file_id = drive_client.upload_pdf(
        pdf,
        service,
        folder_id="rootId",
        conflict_strategy="skip",
        subfolder_path=["gastos-personales", "docs", "operacion"],
    )
    assert file_id == "fileId"
    folder_creates = [
        c.kwargs["body"]["name"]
        for c in service.files().create.call_args_list[:-1]
    ]
    assert folder_creates == ["gastos-personales", "docs", "operacion"]
    file_create_kwargs = service.files().create.call_args_list[-1].kwargs
    assert file_create_kwargs["body"]["parents"] == ["operacionId"]
    assert file_create_kwargs["body"]["name"] == "doc.pdf"


def test_upload_pdf_with_empty_subfolder_path_behaves_like_no_subfolder(
    tmp_path: Path,
) -> None:
    """Empty subfolder_path means upload directly to folder_id."""
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    service = _make_service(existing=None)
    service.files().create.return_value.execute.return_value = {"id": "freshId"}
    file_id = drive_client.upload_pdf(
        pdf, service, "folderX", "skip", subfolder_path=[]
    )
    assert file_id == "freshId"
    # Only one create call (the file, no folders)
    service.files().create.assert_called_once()
    create_kwargs = service.files().create.call_args.kwargs
    assert create_kwargs["body"]["parents"] == ["folderX"]


# --- query escaping (single quotes and backslashes) ---


def test_escape_query_string() -> None:
    """The helper escapes backslashes first, then single quotes.

    Per the Drive API v3 query language: a literal single quote
    is escaped with one backslash, and a literal backslash is
    escaped as two backslashes. Order matters: backslashes must
    be escaped BEFORE single quotes, otherwise the escaped
    backslashes would be re-escaped.
    """
    assert drive_client._escape_query_string("simple") == "simple"
    # Single quote escaped as backslash + quote (1 backslash)
    assert drive_client._escape_query_string("O'Brien") == "O\\'Brien"
    # Backslash escaped as two backslashes
    assert drive_client._escape_query_string("back\\slash") == "back\\\\slash"
    # Multiple single quotes
    assert drive_client._escape_query_string("a'b'c") == "a\\'b\\'c"
    # Backslash and single quote combined (backslash escaped first, then single quote)
    assert drive_client._escape_query_string("a\\'b") == "a\\\\\\'b"
    # Empty string
    assert drive_client._escape_query_string("") == ""


def test_find_file_escapes_single_quote_in_name() -> None:
    """A name with a single quote must be escaped in the query."""
    service = mock.MagicMock()
    service.files().list.return_value.execute.return_value = {"files": []}
    drive_client.find_file_in_folder(service, "O'Brien", "parent123")
    query = service.files().list.call_args.kwargs["q"]
    # The literal name should be present with the quote escaped as backslash-quote
    assert "O\\'Brien" in query, f"Expected escaped single quote in query, got: {query}"


def test_find_or_create_folder_escapes_single_quote_in_name() -> None:
    """A folder name with a single quote must be escaped in the query."""
    service = mock.MagicMock()
    service.files().list.return_value.execute.return_value = {
        "files": [{"id": "existing123", "name": "User's Docs"}]
    }
    result = drive_client.find_or_create_folder(service, "User's Docs", "parent123")
    assert result == "existing123"
    query = service.files().list.call_args.kwargs["q"]
    assert "User\\'s Docs" in query, f"Expected escaped single quote in query, got: {query}"


def test_find_file_with_simple_name_unchanged() -> None:
    """A name without special chars passes through to the query unchanged."""
    service = mock.MagicMock()
    service.files().list.return_value.execute.return_value = {"files": []}
    drive_client.find_file_in_folder(service, "simple-name.md", "parent123")
    query = service.files().list.call_args.kwargs["q"]
    # The name should be in the query as-is (no escaping needed)
    assert "'simple-name.md'" in query, f"Expected unescaped name, got: {query}"
