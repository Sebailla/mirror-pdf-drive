"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from mirror_pdf_drive.config import (
    AuthConfig,
    DriveConfig,
    MirrorConfig,
    OutputConfig,
    RenderConfig,
    SourceConfig,
)


@pytest.fixture
def valid_source_dir(tmp_path: Path) -> Path:
    """A directory with two .md files and a non-md file."""
    (tmp_path / "a.md").write_text("# A\n")
    (tmp_path / "b.md").write_text("# B\n")
    (tmp_path / "ignore.txt").write_text("nope")
    return tmp_path


@pytest.fixture
def valid_config(valid_source_dir: Path, tmp_path: Path) -> MirrorConfig:
    """A fully valid MirrorConfig pointing at tmp dirs."""
    return MirrorConfig(
        version=1,
        source=SourceConfig(root=valid_source_dir),
        output=OutputConfig(root=tmp_path / "out"),
        render=RenderConfig(),
        drive=DriveConfig(folder_id="folderABC"),
        auth=AuthConfig(dir=tmp_path / "auth"),
    )


@pytest.fixture
def valid_config_yaml(valid_source_dir: Path, tmp_path: Path) -> Path:
    """Write a real YAML config file on disk for load_config() tests."""
    cfg_path = tmp_path / "mirror-pdf-drive.config.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "version: 1",
                "source:",
                f"  root: {valid_source_dir}",
                "output:",
                f"  root: {tmp_path / 'out'}",
                "render:",
                "  page_size: A4",
                "drive:",
                "  folder_id: folderABC",
                "  conflict_strategy: skip",
                "auth:",
                f"  dir: {tmp_path / 'auth'}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return cfg_path
