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


class DriveConfig(pydantic.BaseModel):
    folder_id: str | None = None
    folder_name: str = "Documents-es PDFs"
    conflict_strategy: str = "skip"

    @pydantic.field_validator("conflict_strategy")
    @classmethod
    def _valid_strategy(cls, v: str) -> str:
        if v not in ("skip", "replace", "version"):
            raise ValueError(f"invalid conflict_strategy: {v}")
        return v


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
