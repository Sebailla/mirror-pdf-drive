"""Renderer tests (pypandoc is mocked — we never invoke pandoc in unit tests)."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from mirror_pdf_drive import exceptions
from mirror_pdf_drive.config import RenderConfig
from mirror_pdf_drive.renderer import (
    build_default_css,
    build_pandoc_args,
    render_markdown_to_pdf,
)


def test_build_pandoc_args_basic(tmp_path: Path) -> None:
    out = tmp_path / "out.pdf"
    args = build_pandoc_args(RenderConfig(), output_root=tmp_path)
    assert args[0] == "--pdf-engine=weasyprint"
    assert "papersize=A4" in args
    # No template, but a default CSS is generated.
    assert "--template" not in args
    assert "-c" in args
    css_path = Path(args[args.index("-c") + 1])
    assert css_path.exists()
    assert css_path.suffix == ".css"


def test_build_pandoc_args_with_template_and_user_css(tmp_path: Path) -> None:
    template = tmp_path / "t.html"
    css = tmp_path / "s.css"
    template.write_text("<html></html>")
    css.write_text("body{}")
    args = build_pandoc_args(
        RenderConfig(html_template=template, css_file=css),
        output_root=tmp_path,
    )
    assert "--template" in args
    assert str(template) in args
    # User CSS takes precedence over generated CSS.
    assert "-c" in args
    assert str(css) in args


def test_build_pandoc_args_metadata(tmp_path: Path) -> None:
    args = build_pandoc_args(
        RenderConfig(metadata={"title": "X", "author": "Y"}),
        output_root=tmp_path,
    )
    assert "title=X" in args
    assert "author=Y" in args


def test_build_pandoc_args_caches_css(tmp_path: Path) -> None:
    """A second call with the same config should reuse the cached CSS."""
    config = RenderConfig()
    args1 = build_pandoc_args(config, output_root=tmp_path)
    css_path1 = Path(args1[args1.index("-c") + 1])
    args2 = build_pandoc_args(config, output_root=tmp_path)
    css_path2 = Path(args2[args2.index("-c") + 1])
    assert css_path1 == css_path2


def test_build_pandoc_args_different_configs_different_css(tmp_path: Path) -> None:
    args1 = build_pandoc_args(RenderConfig(body_color="#000000"), output_root=tmp_path)
    args2 = build_pandoc_args(RenderConfig(body_color="#ff0000"), output_root=tmp_path)
    assert args1[args1.index("-c") + 1] != args2[args2.index("-c") + 1]


def test_build_default_css_contains_font_family() -> None:
    css = build_default_css(RenderConfig())
    assert "font-family" in css
    assert "Inter" in css
    assert "Roboto" in css


def test_build_default_css_uses_custom_font_family() -> None:
    config = RenderConfig(font_family="'Comic Sans MS', cursive")
    css = build_default_css(config)
    assert "Comic Sans MS" in css


def test_build_default_css_color_respected() -> None:
    config = RenderConfig(body_color="#ff0000")
    css = build_default_css(config)
    assert "#ff0000" in css


def test_build_default_css_font_file_embedded(tmp_path: Path) -> None:
    font_path = tmp_path / "test.ttf"
    font_path.write_bytes(b"fake ttf")
    config = RenderConfig(font_file=font_path)
    css = build_default_css(config)
    assert "@font-face" in css
    assert str(font_path) in css
    assert "'CustomFont'" in css


def test_build_default_css_otf_format() -> None:
    """OTF files should use the opentype format in @font-face."""
    from pathlib import Path as P

    config = RenderConfig(font_file=P("/tmp/nonexistent.otf"))
    css = build_default_css(config)
    assert "opentype" in css


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


def test_build_default_css_includes_page_numbering() -> None:
    """The default CSS must include a 'Página X de Y' counter in the footer.

    WeasyPrint honors the CSS Paged Media spec for @page margin boxes.
    counter(page) and counter(pages) are the standard named counters.
    """
    css = build_default_css(RenderConfig())
    assert "@bottom-right" in css
    assert "counter(page)" in css
    assert "counter(pages)" in css
    assert "Página" in css


def test_build_default_css_no_header() -> None:
    """By design choice, the default CSS has no top-of-page header.

    Only the footer with page numbering is shown. The @page rule
    must NOT contain @top-left, @top-right, or @top-center.
    """
    css = build_default_css(RenderConfig())
    assert "@top-left" not in css
    assert "@top-right" not in css
    assert "@top-center" not in css


def test_build_default_css_footer_uses_custom_font_family() -> None:
    """The footer should pick up a custom font_family config.

    Verifies the font_stack variable is in scope where the footer
    is generated (this is a regression test for a known bug where
    font_stack was defined after the @page block in the f-string).
    """
    config = RenderConfig(font_family="'Comic Sans MS', cursive")
    css = build_default_css(config)
    assert "Comic Sans MS" in css
    # Specifically check the @bottom-right block uses it.
    assert "'Comic Sans MS', cursive" in css


def test_docs_have_no_cjk_characters() -> None:
    """The user-facing docs must not contain CJK (Chinese/Japanese/Korean) characters.

    These are written for a Spanish-language audience. CJK characters
    are easy to miss in code review (e.g. '宏观' instead of 'general')
    and break the readability of the rendered PDFs. This test fails
    fast if any are introduced.

    Covered ranges:
    - U+4E00-U+9FFF   CJK Unified Ideographs
    - U+3400-U+4DBF   CJK Unified Ideographs Extension A
    - U+3040-U+30FF   Hiragana + Katakana
    - U+AC00-U+D7AF   Hangul Syllables
    """
    import re
    from pathlib import Path as P

    docs_root = P(__file__).parent.parent / "docs"
    cjk_re = re.compile(
        "[一-鿿㐀-䶿぀-ゟ゠-ヿ가-힯]"
    )
    offenders: list[tuple[str, int, str]] = []
    for md in sorted(docs_root.rglob("*.md")):
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            if cjk_re.search(line):
                offenders.append((str(md.relative_to(docs_root.parent)), i, line.strip()))
    assert not offenders, (
        "Found CJK characters in docs:\n"
        + "\n".join(f"  {p}:{ln}: {txt}" for p, ln, txt in offenders)
    )
