"""Renderer tests (pypandoc is mocked — we never invoke pandoc in unit tests)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from mirror_pdf_drive import exceptions
from mirror_pdf_drive.config import RenderConfig
from mirror_pdf_drive.renderer import build_pandoc_args, render_markdown_to_pdf


def test_build_pandoc_args_basic() -> None:
    args = build_pandoc_args(RenderConfig())
    assert args[0] == "--pdf-engine=weasyprint"
    assert "papersize=A4" in args
    # No template, no css.
    assert "--template" not in args
    assert "-c" not in args


def test_build_pandoc_args_with_template_and_css(tmp_path: Path) -> None:
    template = tmp_path / "t.html"
    css = tmp_path / "s.css"
    template.write_text("<html></html>")
    css.write_text("body{}")
    args = build_pandoc_args(
        RenderConfig(html_template=template, css_file=css)
    )
    assert "--template" in args
    assert str(template) in args
    assert "-c" in args
    assert str(css) in args


def test_build_pandoc_args_metadata() -> None:
    args = build_pandoc_args(
        RenderConfig(metadata={"title": "X", "author": "Y"})
    )
    assert "title=X" in args
    assert "author=Y" in args


def test_render_happy_path(tmp_path: Path) -> None:
    md = tmp_path / "in.md"
    md.write_text("# Hi\n")
    out = tmp_path / "out.pdf"
    with mock.patch("mirror_pdf_drive.renderer.pypandoc.convert_file") as m:
        result = render_markdown_to_pdf(md, out, RenderConfig())
    assert result == out
    m.assert_called_once()
    call = m.call_args
    assert call.args[0] == str(md)
    assert call.args[1] == "pdf"
    assert call.kwargs["outputfile"] == str(out)


def test_render_creates_parent_dir(tmp_path: Path) -> None:
    md = tmp_path / "in.md"
    md.write_text("# Hi\n")
    out = tmp_path / "nested" / "deeper" / "out.pdf"
    with mock.patch("mirror_pdf_drive.renderer.pypandoc.convert_file"):
        render_markdown_to_pdf(md, out, RenderConfig())
    assert out.parent.exists()


def test_render_wraps_runtime_error(tmp_path: Path) -> None:
    md = tmp_path / "in.md"
    md.write_text("# Hi\n")
    out = tmp_path / "out.pdf"
    with mock.patch(
        "mirror_pdf_drive.renderer.pypandoc.convert_file",
        side_effect=RuntimeError("pandoc crashed"),
    ):
        with pytest.raises(exceptions.RenderFailedError) as excinfo:
            render_markdown_to_pdf(md, out, RenderConfig())
    assert excinfo.value.code == "RENDER_FAILED"
    assert excinfo.value.context["pandoc_error"] == "pandoc crashed"
    assert excinfo.value.context["md_path"] == str(md)
