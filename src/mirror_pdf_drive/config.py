"""Configuration loading and validation for mirror-pdf-drive.

The schema is a Pydantic v2 model. ``load_config(path)`` is the
single public entry point used by the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pydantic
import yaml

from . import exceptions


class SourceConfig(pydantic.BaseModel):
    root: Path
    include: list[str] = pydantic.Field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = pydantic.Field(default_factory=list)
    max_depth: int = 10

    @pydantic.field_validator("root")
    @classmethod
    def _root_must_exist(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"source.root '{v}' does not exist")
        return v


class OutputConfig(pydantic.BaseModel):
    root: Path
    clean: bool = False


class RenderConfig(pydantic.BaseModel):
    html_template: Path | None = None
    css_file: Path | None = None
    page_size: str = "A4"
    margins: dict[str, float] = pydantic.Field(
        default_factory=lambda: {
            "top": 2.0,
            "bottom": 2.0,
            "left": 2.0,
            "right": 2.0,
        }
    )
    metadata: dict[str, str] = pydantic.Field(
        default_factory=lambda: {
            "title": "Documents-es",
            "author": "Sebastián Illa",
        }
    )

    # Tipografía. Inter y Roboto como preferred (Google Fonts populares,
    # sans-serif modernas), con fallback a fuentes del sistema si
    # no están instaladas localmente.
    font_family: str = "Inter, Roboto, Helvetica, Arial, sans-serif"

    # Path opcional a un archivo .ttf/.otf para embeber via @font-face.
    # Si está set, se carga antes que font_family.
    font_file: Path | None = None

    # Colores. Todos validados para WCAG AA en fondo blanco.
    # El CSS default no sobrescribe colores inline que pandoc pone
    # desde MD (ej. <span style="color: #abc">), solo aplica a
    # elementos sin color explícito.
    body_color: str = "#1a1a1a"  # near-black, 16.5:1 contrast
    heading_color: str = "#000000"  # pure black, 21:1 contrast
    link_color: str = "#0563c1"  # Office blue, 7.4:1 contrast
    code_color: str = "#1a1a1a"  # match body
    code_bg_color: str = "#f6f8fa"  # GitHub-style very light gray


class DriveConfig(pydantic.BaseModel):
    """Google Drive configuration.

    The CLI mirrors the local source tree into a per-project
    subfolder of a single fixed root folder. Resolution order:

    1. ``root_folder_id`` is the fixed root folder in Drive where
       all projects are mirrored. Recommended: a single dedicated
       folder like "Mirror PDFs" in your Drive root.
    2. ``folder_id`` is the legacy single-folder target. Kept for
       backwards compatibility; ``root_folder_id`` takes
       precedence when both are set.
    3. At least one of the two must be set.
    4. ``project_folder_name`` overrides the auto-detected project
       folder name (default: ``Path.cwd().name``).
    """

    root_folder_id: str | None = None
    folder_id: str | None = None
    folder_name: str = "Documents-es PDFs"
    project_folder_name: str | None = None
    conflict_strategy: str = "skip"

    @pydantic.field_validator("conflict_strategy")
    @classmethod
    def _valid_strategy(cls, v: str) -> str:
        if v not in ("skip", "replace", "version"):
            raise ValueError(f"invalid conflict_strategy: {v}")
        return v

    @pydantic.model_validator(mode="after")
    def _at_least_one_target(self) -> "DriveConfig":
        if self.root_folder_id is None and self.folder_id is None:
            raise ValueError("drive config requires either root_folder_id or folder_id")
        return self

    def effective_root_folder_id(self) -> str:
        """Return the root folder id, preferring ``root_folder_id`` over legacy ``folder_id``."""
        if self.root_folder_id is not None:
            return self.root_folder_id
        assert self.folder_id is not None  # guaranteed by validator
        return self.folder_id


class AuthConfig(pydantic.BaseModel):
    dir: Path | None = None
    client_secret_file: str = "client_secret.json"
    token_file: str = "token.json"


class MirrorConfig(pydantic.BaseModel):
    version: int = 1
    source: SourceConfig
    output: OutputConfig
    render: RenderConfig
    drive: DriveConfig
    auth: AuthConfig


def load_config(path: Path) -> MirrorConfig:
    """Load and validate the YAML config at ``path``.

    Raises:
        ConfigNotFoundError: when the file does not exist.
        InvalidConfigError: when pydantic validation fails.
    """
    if not path.exists():
        raise exceptions.ConfigNotFoundError(
            f"Config file not found: {path}",
            context={"path": str(path)},
        )

    with open(path, encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    try:
        return MirrorConfig(**raw)
    except pydantic.ValidationError as exc:
        raise exceptions.InvalidConfigError(
            f"Config validation failed: {path}",
            context={"path": str(path), "errors": exc.errors()},
        ) from exc


__all__ = [
    "SourceConfig",
    "OutputConfig",
    "RenderConfig",
    "DriveConfig",
    "AuthConfig",
    "MirrorConfig",
    "load_config",
]
