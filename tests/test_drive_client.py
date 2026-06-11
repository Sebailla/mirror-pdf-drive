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
