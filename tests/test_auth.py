"""Auth tests with mocked Google credentials."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from mirror_pdf_drive import auth, exceptions
from mirror_pdf_drive.config import AuthConfig


def test_resolve_auth_dir_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MIRROR_PDF_DRIVE_AUTH_DIR", str(tmp_path / "override"))
    resolved = auth.resolve_auth_dir(AuthConfig())
    assert resolved == (tmp_path / "override")


def test_resolve_auth_dir_config_override(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path / "from-config")
    assert auth.resolve_auth_dir(cfg) == (tmp_path / "from-config")


def test_resolve_auth_dir_xdg_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MIRROR_PDF_DRIVE_AUTH_DIR", raising=False)
    fake_home = Path("/home/fake")
    monkeypatch.setattr("pathlib.Path.home", lambda: fake_home)
    assert auth.resolve_auth_dir(AuthConfig()) == fake_home / ".config" / "mirror-pdf-drive"


def test_resolve_client_secret_and_token_paths(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path)
    assert auth.resolve_client_secret_path(cfg) == tmp_path / "client_secret.json"
    assert auth.resolve_token_path(cfg) == tmp_path / "token.json"


def test_load_credentials_missing_token(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path)
    assert auth.load_or_refresh_credentials(cfg) is None


def test_load_credentials_expired_with_refresh_refreshes(tmp_path: Path) -> None:
    token_path = tmp_path / "token.json"
    token_path.write_text('{"refresh_token": "rt"}')
    fake_creds = mock.MagicMock()
    fake_creds.expired = True
    fake_creds.refresh_token = "rt"
    fake_creds.valid = True
    fake_creds.to_json.return_value = '{"refresh_token": "rt"}'
    with mock.patch(
        "mirror_pdf_drive.auth.Credentials.from_authorized_user_file",
        return_value=fake_creds,
    ) as m_load:
        result = auth.load_or_refresh_credentials(AuthConfig(dir=tmp_path))
    assert result is fake_creds
    fake_creds.refresh.assert_called_once()
    m_load.assert_called_once()


def test_get_drive_service_raises_when_no_token(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path)
    with pytest.raises(exceptions.AuthRequiredError) as excinfo:
        auth.get_drive_service(cfg)
    assert excinfo.value.code == "AUTH_REQUIRED"


def test_run_oauth_flow_missing_client_secret(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        auth.run_oauth_flow(cfg)


def test_run_oauth_flow_writes_token(tmp_path: Path) -> None:
    cfg = AuthConfig(dir=tmp_path)
    (tmp_path / "client_secret.json").write_text("{}")
    fake_creds = mock.MagicMock()
    fake_creds.to_json.return_value = '{"token": "x"}'
    fake_flow = mock.MagicMock()
    fake_flow.run_local_server.return_value = fake_creds
    with mock.patch(
        "mirror_pdf_drive.auth.InstalledAppFlow.from_client_secrets_file",
        return_value=fake_flow,
    ):
        auth.run_oauth_flow(cfg)
    assert (tmp_path / "token.json").exists()
