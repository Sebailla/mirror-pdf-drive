"""CLI / orchestrator tests."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest import mock

import pytest

import mirror_pdf_drive.mirror as mirror
from mirror_pdf_drive import exceptions
from mirror_pdf_drive.config import (
    AuthConfig,
    DriveConfig,
    MirrorConfig,
    OutputConfig,
    RenderConfig,
    SourceConfig,
)


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
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service") as m_svc,
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf") as m_render,
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload,
    ):
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
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf") as m_render,
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload,
    ):
        code = mirror.main(["--force", "--no-upload", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_OK
    assert m_render.call_count >= 1
    m_upload.assert_not_called()


# ---------------------------------------------------------------------------
# Coverage targets: lines / branches in mirror.py that the original suite
# did not exercise. Each test below names the behavior it locks in.
# ---------------------------------------------------------------------------


def test_apply_overrides_source_and_output_and_folder(tmp_path: Path) -> None:
    """All three CLI override paths modify a single copy of the config."""
    src = tmp_path / "orig_src"
    src.mkdir()
    out = tmp_path / "orig_out"
    base = MirrorConfig(
        version=1,
        source=SourceConfig(root=src),
        output=OutputConfig(root=out),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="orig-fid"),
        auth=AuthConfig(),
    )
    cli_src = tmp_path / "cli_src"
    cli_src.mkdir()
    cli_out = tmp_path / "cli_out"
    args = argparse.Namespace(
        source_dir=cli_src,
        output_dir=cli_out,
        folder_id="cli-fid",
        project_folder_name=None,
    )
    overridden = mirror._apply_overrides(base, args)

    assert overridden.source.root == cli_src
    assert overridden.output.root == cli_out
    assert overridden.drive.folder_id == "cli-fid"
    # Original is untouched (model_copy, not mutation).
    assert base.source.root == src
    assert base.output.root == out
    assert base.drive.folder_id == "orig-fid"


def test_apply_overrides_no_flags_returns_same_config(tmp_path: Path) -> None:
    """No overrides set → returns the original config object (no copy)."""
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    base = MirrorConfig(
        version=1,
        source=SourceConfig(root=src),
        output=OutputConfig(root=out),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="fid"),
        auth=AuthConfig(),
    )
    args = argparse.Namespace(
        source_dir=None, output_dir=None, folder_id=None, project_folder_name=None
    )
    assert mirror._apply_overrides(base, args) is base


def test_output_path_for_path_outside_source_root(tmp_path: Path) -> None:
    """md_path not under source.root falls back to filename only (no ValueError)."""
    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=src),
        output=OutputConfig(root=out),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    outside = Path("/definitely-not-under-src/foo.md")
    out_path = mirror._output_path_for(outside, cfg)
    assert out_path == out / "foo.pdf"


def test_output_path_for_path_inside_source_root(tmp_path: Path) -> None:
    """md_path under source.root mirrors the relative tree under output.root."""
    src = tmp_path / "src"
    sub = src / "sub"
    sub.mkdir(parents=True)
    out = tmp_path / "out"
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=src),
        output=OutputConfig(root=out),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    out_path = mirror._output_path_for(sub / "foo.md", cfg)
    assert out_path == out / "sub" / "foo.pdf"


def test_should_skip_when_force_is_true(tmp_path: Path) -> None:
    """--force always re-renders, even when the PDF is newer than the MD."""
    md = tmp_path / "a.md"
    md.write_text("# a")
    pdf = tmp_path / "a.pdf"
    pdf.write_text("old")
    # Make the PDF strictly newer.
    import os
    import time

    new = time.time() + 60
    os.utime(pdf, (new, new))
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=tmp_path),
        output=OutputConfig(root=tmp_path),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    assert mirror._should_skip(md, pdf, cfg, force=True) is False


def test_should_skip_when_pdf_missing(tmp_path: Path) -> None:
    """No PDF on disk → never skip, even without --force."""
    md = tmp_path / "a.md"
    md.write_text("# a")
    pdf = tmp_path / "a.pdf"  # not created
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=tmp_path),
        output=OutputConfig(root=tmp_path),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    assert mirror._should_skip(md, pdf, cfg, force=False) is False


def test_should_skip_when_pdf_older_than_md(tmp_path: Path) -> None:
    """PDF older than MD → do NOT skip (re-render)."""
    md = tmp_path / "a.md"
    md.write_text("# a")
    pdf = tmp_path / "a.pdf"
    pdf.write_text("old")
    import os
    import time

    old = time.time() - 600
    new = time.time()
    os.utime(md, (new, new))
    os.utime(pdf, (old, old))
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=tmp_path),
        output=OutputConfig(root=tmp_path),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    assert mirror._should_skip(md, pdf, cfg, force=False) is False


def test_discover_files_with_explicit_paths_returns_only_existing(
    valid_source_dir: Path,
) -> None:
    """When paths are passed, missing ones are dropped; existing ones are returned."""
    cfg = MirrorConfig(
        version=1,
        source=SourceConfig(root=valid_source_dir),
        output=OutputConfig(root=valid_source_dir),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="test-folder"),
        auth=AuthConfig(),
    )
    a_abs = valid_source_dir / "a.md"
    b_abs = valid_source_dir / "b.md"
    result = mirror.discover_files(cfg, [Path("a.md"), Path("nope.md"), b_abs])
    # Order is the order of inputs; missing files are filtered out.
    assert result == [a_abs, b_abs]


def test_handle_one_render_failure_increments_counter(
    valid_config_yaml: Path,
) -> None:
    """Pandoc failure → render_failures += 1, no upload attempted."""
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch(
            "mirror_pdf_drive.mirror.render_markdown_to_pdf",
            side_effect=exceptions.RenderFailedError("boom", context={"pandoc_error": "x"}),
        ) as m_render,
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload,
    ):
        code = mirror.main(
            [
                "--force",
                "--no-upload",  # belt-and-suspenders: ensure no_upload path
                "--config",
                str(valid_config_yaml),
            ]
        )
    assert code == mirror.EXIT_RENDER_FAILED
    m_render.assert_called()
    m_upload.assert_not_called()


def test_handle_one_upload_failure_increments_counter(
    valid_config_yaml: Path,
) -> None:
    """Successful render + failed upload → upload_failures += 1, exit UPLOAD_FAILED."""
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf"),
        mock.patch(
            "mirror_pdf_drive.mirror.drive_client.upload_pdf",
            side_effect=exceptions.UploadFailedError("boom", context={"api_error": "x"}),
        ) as m_upload,
    ):
        code = mirror.main(["--force", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_UPLOAD_FAILED
    m_upload.assert_called()


def test_handle_one_no_upload_after_render(
    valid_config_yaml: Path,
) -> None:
    """--no-upload after a successful render skips upload entirely."""
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf") as m_render,
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload,
    ):
        code = mirror.main(["--force", "--no-upload", "--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_OK
    m_render.assert_called()
    m_upload.assert_not_called()


def test_handle_one_skip_increments_skipped(
    valid_config_yaml: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When the PDF is newer than the MD, the file is skipped and counted."""
    cfg = mirror.config_mod.load_config(valid_config_yaml)
    src = cfg.source.root
    out = cfg.output.root
    md = src / "a.md"
    pdf = out / "a.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_text("existing")
    import os
    import time

    new = time.time() + 600
    os.utime(md, (time.time(), time.time()))
    os.utime(pdf, (new, new))

    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf") as m_render,
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf") as m_upload,
    ):
        code = mirror.main(["--config", str(valid_config_yaml), str(md)])
    assert code == mirror.EXIT_OK
    m_render.assert_not_called()
    m_upload.assert_not_called()
    out_text = capsys.readouterr().out
    assert "Omitidos: 1" in out_text


def test_run_unexpected_app_error_returns_5(
    valid_config_yaml: Path,
) -> None:
    """An AppError other than Render/Upload propagates from _handle_one → EXIT_UNEXPECTED."""
    boom = exceptions.ConfigNotFoundError("oops", context={"path": "x"})
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror._handle_one", side_effect=boom),
    ):
        code = mirror.main(["--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_UNEXPECTED


def test_main_systemexit_non_int_returns_unexpected(
    valid_config_yaml: Path,
) -> None:
    """argparse's SystemExit with a non-int code is normalized to EXIT_UNEXPECTED."""

    def _raise(*_a, **_kw):
        # argparse exits with a string like "2" when --help is intercepted,
        # but SystemExit.code is normally an int. We simulate the int-branch
        # exit code path; a non-int path is covered by the safety net.
        raise SystemExit(0)

    # Patch parse_argv to raise SystemExit with a non-int code.
    with mock.patch(
        "mirror_pdf_drive.mirror.parse_argv",
        side_effect=SystemExit("not-an-int"),
    ):
        code = mirror.main(["--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_UNEXPECTED


def test_main_unhandled_exception_returns_unexpected(
    valid_config_yaml: Path,
) -> None:
    """Any uncaught Exception inside run() → EXIT_UNEXPECTED (safety net)."""
    with mock.patch(
        "mirror_pdf_drive.mirror.run",
        side_effect=RuntimeError("kaboom"),
    ):
        code = mirror.main(["--config", str(valid_config_yaml)])
    assert code == mirror.EXIT_UNEXPECTED


def test_main_dry_run_skip_prints_message(
    valid_config_yaml: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run + skip path prints the [DRY-RUN] skip line and counts the skip."""
    cfg = mirror.config_mod.load_config(valid_config_yaml)
    src = cfg.source.root
    out = cfg.output.root
    md = src / "a.md"
    pdf = out / "a.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_text("existing")
    import os
    import time

    new = time.time() + 600
    os.utime(md, (time.time(), time.time()))
    os.utime(pdf, (new, new))

    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf") as m_render,
    ):
        code = mirror.main(["--dry-run", "--config", str(valid_config_yaml), str(md)])
    assert code == mirror.EXIT_OK
    m_render.assert_not_called()
    out_text = capsys.readouterr().out
    assert "[DRY-RUN] skip (exists)" in out_text
    assert "Omitidos: 1" in out_text


def test_main_setup_logging_verbose(
    valid_config_yaml: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """--verbose flips logging to DEBUG and the run still completes."""
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf"),
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf"),
    ):
        with caplog.at_level("DEBUG"):
            code = mirror.main(
                [
                    "--verbose",
                    "--force",
                    "--no-upload",
                    "--config",
                    str(valid_config_yaml),
                ]
            )
    assert code == mirror.EXIT_OK


def test_main_invalid_config_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An invalid YAML (bad conflict_strategy) → InvalidConfigError → EXIT_CONFIG_ERROR."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# a")
    out = tmp_path / "out"
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "\n".join(
            [
                "version: 1",
                f"source: {{ root: {src} }}",
                f"output: {{ root: {out} }}",
                "render: {}",
                "drive: { folder_id: fid, conflict_strategy: bogus }",
                "auth: {}",
            ]
        ),
        encoding="utf-8",
    )
    code = mirror.main(["--config", str(bad)])
    assert code == mirror.EXIT_CONFIG_ERROR
    out_text = capsys.readouterr().out
    assert "Configuración inválida" in out_text


# --- Project folder isolation ---


def test_project_subfolder_path_under_source_root(tmp_path: Path) -> None:
    """A .md at source_root/docs/operacion/foo.md maps to [project, docs, operacion]."""
    from mirror_pdf_drive.mirror import _project_subfolder_path

    src = tmp_path / "src"
    sub = src / "docs" / "operacion"
    sub.mkdir(parents=True)
    md = sub / "foo.md"
    md.write_text("# foo")
    chain = _project_subfolder_path(md, src, "gastos-personales")
    assert chain == ["gastos-personales", "docs", "operacion"]


def test_project_subfolder_path_with_no_subdirs(tmp_path: Path) -> None:
    """A .md directly under source_root maps to just [project]."""
    from mirror_pdf_drive.mirror import _project_subfolder_path

    src = tmp_path / "src"
    src.mkdir()
    md = src / "foo.md"
    md.write_text("# foo")
    chain = _project_subfolder_path(md, src, "gastos-personales")
    assert chain == ["gastos-personales"]


def test_project_subfolder_path_outside_source_root(tmp_path: Path) -> None:
    """A .md not under source_root falls back to [project] (best effort)."""
    from mirror_pdf_drive.mirror import _project_subfolder_path

    md = tmp_path / "elsewhere" / "foo.md"
    md.parent.mkdir()
    md.write_text("# foo")
    chain = _project_subfolder_path(md, tmp_path / "src", "gastos-personales")
    assert chain == ["gastos-personales"]


def test_main_uses_cwd_when_no_override(
    valid_config_yaml: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no project_folder_name override, the summary uses Path.cwd().name."""
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf"),
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf"),
    ):
        code = mirror.main(
            [
                "--force",
                "--no-upload",
                "--config",
                str(valid_config_yaml),
            ]
        )
    assert code == mirror.EXIT_OK
    out_text = capsys.readouterr().out
    expected_project = Path.cwd().name
    assert expected_project in out_text
    assert "Drive:" in out_text


def test_main_uses_config_override_when_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When drive.project_folder_name is set, the summary uses that name."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# a")
    out = tmp_path / "out"
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "version: 1",
                f"source: {{ root: {src} }}",
                f"output: {{ root: {out} }}",
                "render: {}",
                "drive:",
                "  root_folder_id: root123",
                "  project_folder_name: my-custom-name",
                "  conflict_strategy: skip",
                "auth: {}",
            ]
        ),
        encoding="utf-8",
    )
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf"),
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf"),
    ):
        code = mirror.main(["--force", "--no-upload", "--config", str(cfg_path)])
    assert code == mirror.EXIT_OK
    out_text = capsys.readouterr().out
    assert "my-custom-name" in out_text
    assert "Drive: root123/my-custom-name/" in out_text


def test_main_cli_project_folder_name_overrides_config(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The --project-folder-name CLI flag overrides the config value."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("# a")
    out = tmp_path / "out"
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "version: 1",
                f"source: {{ root: {src} }}",
                f"output: {{ root: {out} }}",
                "render: {}",
                "drive:",
                "  root_folder_id: root123",
                "  project_folder_name: from-config",
                "  conflict_strategy: skip",
                "auth: {}",
            ]
        ),
        encoding="utf-8",
    )
    with (
        mock.patch("mirror_pdf_drive.mirror.auth.get_drive_service"),
        mock.patch("mirror_pdf_drive.mirror.render_markdown_to_pdf"),
        mock.patch("mirror_pdf_drive.mirror.drive_client.upload_pdf"),
    ):
        code = mirror.main(
            [
                "--force",
                "--no-upload",
                "--project-folder-name",
                "from-cli",
                "--config",
                str(cfg_path),
            ]
        )
    assert code == mirror.EXIT_OK
    out_text = capsys.readouterr().out
    assert "from-cli" in out_text
    assert "from-config" not in out_text
