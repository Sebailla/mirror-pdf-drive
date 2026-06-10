"""Markdown to PDF rendering via pandoc + weasyprint.

Public surface is :func:`render_markdown_to_pdf`. The function
isolates the side effects of calling ``pypandoc`` so the
orchestrator can rely on a single ``RenderFailedError`` for all
rendering failures.
"""

from __future__ import annotations

from pathlib import Path

import pypandoc

from . import exceptions
from .config import RenderConfig


def build_pandoc_args(config: RenderConfig) -> list[str]:
    """Build the ``extra_args`` list for ``pypandoc.convert_file``."""
    args: list[str] = [
        "--pdf-engine=weasyprint",
        "-V",
        f"papersize={config.page_size}",
    ]
    if config.html_template:
        args.extend(["--template", str(config.html_template)])
    if config.css_file:
        # pandoc with weasyprint uses CSS via -c.
        args.extend(["-c", str(config.css_file)])
    for key, value in config.metadata.items():
        if value:
            args.extend(["-V", f"{key}={value}"])
    return args


def render_markdown_to_pdf(
    md_path: Path,
    output_path: Path,
    config: RenderConfig,
) -> Path:
    """Render ``md_path`` to a PDF at ``output_path``.

    Creates the parent directory if needed. Raises
    :class:`RenderFailedError` if pandoc fails.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    extra_args = build_pandoc_args(config)

    try:
        pypandoc.convert_file(
            str(md_path),
            "pdf",
            outputfile=str(output_path),
            extra_args=extra_args,
        )
    except RuntimeError as exc:
        raise exceptions.RenderFailedError(
            f"pandoc failed to render {md_path}",
            context={
                "md_path": str(md_path),
                "output_path": str(output_path),
                "pandoc_error": str(exc),
            },
        ) from exc

    return output_path


__all__ = ["render_markdown_to_pdf", "build_pandoc_args"]
