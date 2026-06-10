"""CLI / orchestrator tests."""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest import mock

import pytest

import mirror_pdf_drive.mirror as mirror
from mirror_pdf_drive import exceptions


def test_parse_argv_dry_run() -> None:
    args = mirror.parse_argv(["--dry-run"])
    assert args.dry_run is True
    assert args.paths == []


def test_parse_argv_version() -> None:
    args = mirror.parse_argv(["--version"])
    assert args.version is True


def test_parse_argv_paths() -> None:
    args = mirror.parse_argv(["--dry-run", "docs/a.md", "docs/b.md"])
    assert args.dry_run is True
    assert [str(p) for p in args.paths] == ["docs/a.md", "docs/b.md"]


def test_parse_argv_all_flags() -> None:
    args = mirror.parse_argv(
        [
            "--config",
            "cfg.yaml",
            "--source-dir",
            "src",
            "--output-dir",
            "out",
            "--dry-run",
            "--force",
            "--verbose",
            "--no-upload",
            "--folder-id",
            "fid",
            "--init",
        ]
    )
    assert args.config == Path("cfg.yaml")
    assert args.source_dir == Path("src")
    assert args.output_dir == Path("out")
    assert args.dry_run is True
    assert args.force is True
    assert args.verbose is True
    assert args.no_upload is True
    assert args.folder_id == "fid"
    assert args.init is True


def test_main_version_prints_and_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    code = mirror.main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert "mirror-pdf-drive" in captured.out


def test_main_config_not_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = mirror.main(["--config", str(tmp_path / "nope.yaml")])
    assert code == mirror.EXIT_CONFIG_ERROR
    out = capsys.readouterr().out
    assert "No se encontró" in out


def test_main_init_calls_oauth_flow(valid_config_yaml: Path) -> None:
    with mock.patch("mirror_pdf_drive.mirror.auth.run_oauth_flow") as m_flow:
        code = mirror.main(["--init", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_OK
    m_flow.assert_called_once()


def test_main_init_missing_client_secret(
    valid_config_yaml: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with mock.patch(
        "mirror_pdf_drive.mirror.auth.run_oauth_flow",
        side_effect=FileNotFoundError("client_secret.json not found"),
    ):
        code = mirror.main(["--init", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_CONFIG_ERROR


def test_main_auth_required_returns_2(valid_config_yaml: Path) -> None:
    with mock.patch(
        "mirror_pdf_drive.mirror.auth.get_drive_service",
        side_effect=exceptions.AuthRequiredError("nope", context={}),
    ):
        code = mirror.main(["--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_AUTH_REQUIRED


def test_main_dry_run_does_not_render(
    valid_config_yaml: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service") as m_svc, mock.patch(
        "mirror_pdf_drive.mirror.render_markdown_to_pdf"
    ) as m_render, mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload:
        code = mirror.main(["--dry-run", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_OK
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    m_render.assert_not_called()
    m_upload.assert_not_called()
    m_svc.assert_called_once()


def test_compute_exit_code_priority() -> None:
    s = mirror.Stats()
    assert mirror.compute_exit_code(s) == mirror.EXIT_OK
    s.render_failures = 1
    assert mirror.compute_exit_code(s) == mirror.EXIT_RENDER_FAILED
    s.upload_failures = 1
    assert mirror.compute_exit_code(s) == mirror.EXIT_UPLOAD_FAILED


def test_stats_counters() -> None:
    s = mirror.Stats()
    assert s.rendered == 0
    assert s.uploaded == 0
    assert s.skipped == 0
    assert s.render_failures == 0
    assert s.upload_failures == 0
    s.rendered += 1
    assert s.rendered == 1


def test_main_force_and_render_calls(
    valid_config_yaml: Path,
) -> None:
    with mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"), mock.patch(
        "mirror_pdf_drive.mirror.render_markdown_to_pdf"
    ) as m_render, mock.patch(
        "mirror_pdf_drive.mirror.drive_client.upload_pdf"
    ) as m_upload:
        code = mirror.main(
            ["--force", "--no-upload", "--config", str(valid_config_yaml)]
        )
    assert code == mirror.EXIT_OK
    assert m_render.call_count >= 1
    m_upload.assert_not_called()
