"""Markdown to PDF rendering via pandoc + weasyprint.

Public surface is :func:`render_markdown_to_pdf`. The function
isolates the side effects of calling ``pypandoc`` so the
orchestrator can rely on a single ``RenderFailedError`` for all
rendering failures.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pypandoc

from . import exceptions
from .config import RenderConfig


def build_default_css(config: RenderConfig) -> str:
    """Build a CSS string from the typography/color config.

    The CSS targets only elements that don't have inline color
    styles (which pandoc generates from MD spans with explicit
    colors). The MD's original colors are preserved, and our
    defaults only apply to elements without explicit colors.

    Color defaults are validated for WCAG AA on white background.
    """
    font_face = ""
    if config.font_file:
        # Determine font format from extension.
        ext = config.font_file.suffix.lower()
        if ext in (".ttf", ".ttc"):
            fmt = "truetype"
        elif ext == ".otf":
            fmt = "opentype"
        else:
            fmt = "truetype"  # default fallback
        font_face = (
            f"@font-face {{\n"
            f"    font-family: 'CustomFont';\n"
            f"    src: url('{config.font_file}') format('{fmt}');\n"
            f"}}\n\n"
        )
        # When a custom font is set, prepend it to font_family.
        font_stack = "'CustomFont', " + config.font_family
    else:
        font_stack = config.font_family

    m = config.margins
    return f"""@page {{
    size: {config.page_size};
    margin: {m.get("top", 2.0)}cm {m.get("right", 2.0)}cm {m.get("bottom", 2.0)}cm {m.get("left", 2.0)}cm;
}}

{font_face}body {{
    font-family: {font_stack};
    color: {config.body_color};
    font-size: 11pt;
    line-height: 1.5;
}}

h1, h2, h3, h4, h5, h6 {{
    color: {config.heading_color};
    font-weight: 600;
    line-height: 1.3;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}}

h1 {{ font-size: 1.8em; }}
h2 {{ font-size: 1.5em; }}
h3 {{ font-size: 1.25em; }}
h4 {{ font-size: 1.1em; }}
h5 {{ font-size: 1em; }}
h6 {{ font-size: 0.9em; }}

a {{
    color: {config.link_color};
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}

code, pre, kbd, samp {{
    font-family: 'SF Mono', Menlo, Consolas, 'Courier New', monospace;
    color: {config.code_color};
    background-color: {config.code_bg_color};
    padding: 0.1em 0.3em;
    border-radius: 3px;
    font-size: 0.9em;
}}

pre {{
    padding: 0.75em;
    overflow-x: auto;
    line-height: 1.4;
    border-radius: 4px;
}}

pre code {{
    background: transparent;
    padding: 0;
}}

blockquote {{
    border-left: 4px solid {config.code_bg_color};
    padding-left: 1em;
    margin-left: 0;
    color: {config.body_color};
    opacity: 0.85;
}}

table {{
    border-collapse: collapse;
    margin: 1em 0;
}}
th, td {{
    border: 1px solid {config.code_bg_color};
    padding: 0.4em 0.7em;
    text-align: left;
}}
th {{
    background-color: {config.code_bg_color};
    font-weight: 600;
}}

img {{
    max-width: 100%;
    height: auto;
}}

hr {{
    border: none;
    border-top: 1px solid {config.code_bg_color};
    margin: 2em 0;
}}
"""


def _css_cache_path(config: RenderConfig, output_root: Path) -> Path:
    """Path to the cached CSS file for a given config.

    The CSS is cached in a hidden subdir of the output root so it
    survives between runs and isn't regenerated unnecessarily. The
    filename is a hash of the config so different configs produce
    different files.
    """
    fingerprint = hashlib.sha256(
        f"{config.font_family}|{config.font_file}|{config.body_color}|"
        f"{config.heading_color}|{config.link_color}|{config.code_color}|"
        f"{config.code_bg_color}|{config.page_size}|{dict(sorted(config.margins.items()))}".encode()
    ).hexdigest()[:16]
    cache_dir = output_root / ".mirror-pdf-drive-cache"
    return cache_dir / f"style-{fingerprint}.css"


def build_pandoc_args(
    config: RenderConfig,
    output_root: Path | None = None,
) -> list[str]:
    """Build the ``extra_args`` list for ``pypandoc.convert_file``.

    If ``config.css_file`` is set, that file is used. Otherwise,
    a CSS file is generated from the typography config and cached
    in the output root (if provided). The cache key is a hash of
    the config, so different configs produce different files and
    re-renders don't regenerate the CSS.
    """
    args: list[str] = [
        "--pdf-engine=weasyprint",
        "-V",
        f"papersize={config.page_size}",
    ]
    if config.html_template:
        args.extend(["--template", str(config.html_template)])

    if config.css_file:
        # User-provided CSS takes precedence.
        args.extend(["-c", str(config.css_file)])
    elif output_root is not None:
        # Generate and cache CSS from the typography config.
        css = build_default_css(config)
        css_path = _css_cache_path(config, output_root)
        if not css_path.exists():
            css_path.parent.mkdir(parents=True, exist_ok=True)
            css_path.write_text(css, encoding="utf-8")
        args.extend(["-c", str(css_path)])
    else:
        # No output root provided: generate the CSS in a temp file.
        # This path is mostly for tests; in production the output
        # root is always provided.
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".css", delete=False, encoding="utf-8"
        ) as f:
            f.write(build_default_css(config))
            css_path = Path(f.name)
        args.extend(["-c", str(css_path)])

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

    # Use the output path's parent as the cache root for the CSS.
    extra_args = build_pandoc_args(config, output_root=output_path.parent)

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


__all__ = [
    "render_markdown_to_pdf",
    "build_pandoc_args",
    "build_default_css",
]
