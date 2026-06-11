"""CLI entry point for mirror-pdf-drive.

The flow is fixed: parse args → load config → authenticate →
discover files → render → upload → print summary.

Exit code priority (worst wins):

    5 (unexpected) > 2 (auth) > 1 (config) > 4 (upload) > 3 (render) > 0 (ok)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Iterable, Sequence

from . import __version__, auth, drive_client, exceptions
from . import config as config_mod
from .config import MirrorConfig
from .renderer import render_markdown_to_pdf

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_AUTH_REQUIRED = 2
EXIT_RENDER_FAILED = 3
EXIT_UPLOAD_FAILED = 4
EXIT_UNEXPECTED = 5


class Stats:
    """Mutable counters used by ``run`` and ``print_summary``."""

    def __init__(self) -> None:
        self.discovered: int = 0
        self.rendered: int = 0
        self.uploaded: int = 0
        self.skipped: int = 0
        self.render_failures: int = 0
        self.upload_failures: int = 0


def parse_argv(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse CLI args. ``argv`` follows the same convention as ``sys.argv[1:]``."""
    parser = argparse.ArgumentParser(
        prog="mirror-pdf-drive",
        description="Convierte MD a PDF y sube a Google Drive.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("mirror-pdf-drive.config.yaml"),
        help="Path al archivo de configuración YAML.",
    )
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--init",
        action="store_true",
        help="Bootstrap: valida config y hace OAuth flow.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Imprime la versión y sale.",
    )
    parser.add_argument("paths", nargs="*", type=Path, default=[])
    return parser.parse_args(argv)


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _load_config_or_exit(args: argparse.Namespace) -> MirrorConfig | int:
    try:
        cfg = config_mod.load_config(args.config)
    except exceptions.ConfigNotFoundError as exc:
        print(f"No se encontró el archivo de configuración: {exc.context.get('path', args.config)}")
        return EXIT_CONFIG_ERROR
    except exceptions.InvalidConfigError as exc:
        print(f"Configuración inválida: {exc.message}")
        return EXIT_CONFIG_ERROR
    return cfg


def _apply_overrides(cfg: MirrorConfig, args: argparse.Namespace) -> MirrorConfig:
    """Apply CLI overrides (--source-dir, --output-dir, --folder-id)."""
    overrides: dict[str, object] = {}
    if args.source_dir is not None:
        overrides["source"] = cfg.source.model_copy(update={"root": args.source_dir})
    if args.output_dir is not None:
        overrides["output"] = cfg.output.model_copy(update={"root": args.output_dir})
    if args.folder_id is not None:
        overrides["drive"] = cfg.drive.model_copy(update={"folder_id": args.folder_id})
    if not overrides:
        return cfg
    return cfg.model_copy(update=overrides)


def _output_path_for(md_path: Path, cfg: MirrorConfig) -> Path:
    """Compute the PDF output path mirroring the source tree under output.root."""
    try:
        relative = md_path.relative_to(cfg.source.root)
    except ValueError:
        relative = Path(md_path.name)
    return cfg.output.root / relative.with_suffix(".pdf")


def _should_skip(md_path: Path, output_pdf: Path, cfg: MirrorConfig, force: bool) -> bool:
    """Idempotency check based on mtime: skip if PDF is newer than MD."""
    if force:
        return False
    if not output_pdf.exists():
        return False
    return output_pdf.stat().st_mtime >= md_path.stat().st_mtime


def discover_files(cfg: MirrorConfig, requested: Iterable[Path]) -> list[Path]:
    """Resolve the list of markdown files to process.

    If ``requested`` is empty, walks ``source.root`` honoring
    ``include``/``exclude``. Otherwise resolves each requested
    path (relative to ``source.root`` or absolute).
    """
    requested = list(requested)
    if not requested:
        files: list[Path] = []
        for pattern in cfg.source.include:
            files.extend(cfg.source.root.glob(pattern))
        excluded: set[Path] = set()
        for pattern in cfg.source.exclude:
            excluded.update(cfg.source.root.glob(pattern))
        return sorted(p for p in files if p not in excluded and p.is_file())

    out: list[Path] = []
    for p in requested:
        if not p.is_absolute():
            p = cfg.source.root / p
        if p.is_file():
            out.append(p)
    return out


def _handle_one(
    md_path: Path,
    cfg: MirrorConfig,
    args: argparse.Namespace,
    stats: Stats,
    drive_service: object,
) -> None:
    output_pdf = _output_path_for(md_path, cfg)

    if _should_skip(md_path, output_pdf, cfg, args.force):
        log.info("skip (mtime): %s", md_path)
        stats.skipped += 1
        if args.dry_run:
            print(f"[DRY-RUN] skip (exists): {output_pdf}")
        return

    if args.dry_run:
        print(
            f"[DRY-RUN] render: {md_path} -> {output_pdf} (strategy: {cfg.drive.conflict_strategy})"
        )
        if not args.no_upload:
            print(f"[DRY-RUN] upload: {output_pdf.name} -> folder {cfg.drive.folder_id}")
        stats.rendered += 1
        return

    try:
        render_markdown_to_pdf(md_path, output_pdf, cfg.render)
        stats.rendered += 1
    except exceptions.RenderFailedError as exc:
        log.error("render failed: %s (%s)", md_path, exc.context.get("pandoc_error"))
        stats.render_failures += 1
        return

    if args.no_upload:
        return

    try:
        drive_client.upload_pdf(
            output_pdf,
            drive_service,
            cfg.drive.folder_id or "",
            cfg.drive.conflict_strategy,
        )
        stats.uploaded += 1
    except exceptions.UploadFailedError as exc:
        log.error(
            "upload failed: %s, api_error: %s",
            output_pdf,
            exc.context.get("api_error"),
        )
        stats.upload_failures += 1


def run(args: argparse.Namespace) -> int:
    """Execute the CLI flow. Returns an exit code."""
    _setup_logging(args.verbose)

    if args.version:
        print(f"mirror-pdf-drive {__version__}")
        return EXIT_OK

    loaded = _load_config_or_exit(args)
    if isinstance(loaded, int):
        return loaded
    cfg = _apply_overrides(loaded, args)

    if args.init:
        try:
            auth.run_oauth_flow(cfg.auth)
        except FileNotFoundError as exc:
            print(str(exc))
            return EXIT_CONFIG_ERROR
        print(f"OAuth flow completado. Token guardado en {auth.resolve_token_path(cfg.auth)}")
        return EXIT_OK

    try:
        drive_service = auth.get_drive_service(cfg.auth)
    except exceptions.AuthRequiredError as exc:
        print("Necesitás autorizar la herramienta. Corré: mirror-pdf-drive --init")
        log.debug("auth required: %s", exc.context)
        return EXIT_AUTH_REQUIRED

    stats = Stats()
    files = discover_files(cfg, args.paths)
    stats.discovered = len(files)

    for md_path in files:
        try:
            _handle_one(md_path, cfg, args, stats, drive_service)
        except exceptions.AppError as exc:
            log.exception("unexpected app error on %s: %s", md_path, exc)
            return EXIT_UNEXPECTED

    print_summary(stats)
    return compute_exit_code(stats)


def print_summary(stats: Stats) -> None:
    print(
        f"Renderizados: {stats.rendered}. Subidos: {stats.uploaded}. "
        f"Omitidos: {stats.skipped}. Fallos: "
        f"{stats.render_failures + stats.upload_failures}."
    )


def compute_exit_code(stats: Stats) -> int:
    """Worst-wins priority: unexpected > auth > config > upload > render > ok."""
    if stats.upload_failures > 0:
        return EXIT_UPLOAD_FAILED
    if stats.render_failures > 0:
        return EXIT_RENDER_FAILED
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. ``argv`` defaults to ``sys.argv[1:]``."""
    if argv is None:
        argv = sys.argv[1:]
    try:
        return run(parse_argv(argv))
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_UNEXPECTED
    except Exception:  # pragma: no cover - safety net
        log.exception("unhandled exception")
        return EXIT_UNEXPECTED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
