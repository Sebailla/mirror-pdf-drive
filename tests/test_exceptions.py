"""Exception class contract tests."""

from __future__ import annotations

import pytest

from mirror_pdf_drive import exceptions as ex


@pytest.mark.parametrize(
    "cls,expected_code",
    [
        (ex.AppError, "APP_ERROR"),
        (ex.ConfigNotFoundError, "CONFIG_NOT_FOUND"),
        (ex.InvalidConfigError, "INVALID_CONFIG"),
        (ex.AuthRequiredError, "AUTH_REQUIRED"),
        (ex.RenderFailedError, "RENDER_FAILED"),
        (ex.UploadFailedError, "UPLOAD_FAILED"),
    ],
)
def test_exception_has_code(cls: type[ex.AppError], expected_code: str) -> None:
    assert cls.code == expected_code


@pytest.mark.parametrize(
    "cls",
    [
        ex.ConfigNotFoundError,
        ex.InvalidConfigError,
        ex.AuthRequiredError,
        ex.RenderFailedError,
        ex.UploadFailedError,
    ],
)
def test_subclass_of_app_error(cls: type[ex.AppError]) -> None:
    assert issubclass(cls, ex.AppError)


def test_context_default_is_empty_dict() -> None:
    err = ex.AppError("boom")
    assert err.message == "boom"
    assert err.context == {}


def test_context_is_stored() -> None:
    err = ex.RenderFailedError("nope", context={"md_path": "x.md"})
    assert err.context == {"md_path": "x.md"}
