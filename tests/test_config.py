"""Config loading and validation tests."""

from __future__ import annotations

from pathlib import Path

import pydantic
import pytest
import yaml

from mirror_pdf_drive import config as cfg_mod
from mirror_pdf_drive import exceptions


def test_load_config_happy_path(valid_config_yaml: Path) -> None:
    cfg = cfg_mod.load_config(valid_config_yaml)
    assert isinstance(cfg, cfg_mod.MirrorConfig)
    assert cfg.version == 1
    assert cfg.drive.conflict_strategy == "skip"
    assert cfg.render.page_size == "A4"


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(exceptions.ConfigNotFoundError) as excinfo:
        cfg_mod.load_config(tmp_path / "nope.yaml")
    assert excinfo.value.code == "CONFIG_NOT_FOUND"
    assert "nope.yaml" in str(excinfo.value.context.get("path", ""))


def test_load_config_invalid_strategy(valid_source_dir: Path, tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "source": {"root": str(valid_source_dir)},
                "output": {"root": str(tmp_path / "out")},
                "render": {},
                "drive": {"conflict_strategy": "explode"},
                "auth": {"dir": str(tmp_path / "auth")},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(exceptions.InvalidConfigError) as excinfo:
        cfg_mod.load_config(cfg_path)
    assert excinfo.value.code == "INVALID_CONFIG"


def test_load_config_missing_source_root(tmp_path: Path) -> None:
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "source": {"root": str(tmp_path / "does-not-exist")},
                "output": {"root": str(tmp_path / "out")},
                "render": {},
                "drive": {},
                "auth": {"dir": str(tmp_path / "auth")},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(exceptions.InvalidConfigError) as excinfo:
        cfg_mod.load_config(cfg_path)
    assert excinfo.value.code == "INVALID_CONFIG"


def test_source_config_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(pydantic.ValidationError):
        cfg_mod.SourceConfig(root=tmp_path / "missing")


def test_drive_config_validates_strategy() -> None:
    cfg_mod.DriveConfig(root_folder_id="r", conflict_strategy="replace")
    cfg_mod.DriveConfig(root_folder_id="r", conflict_strategy="version")
    with pytest.raises(pydantic.ValidationError):
        cfg_mod.DriveConfig(root_folder_id="r", conflict_strategy="nope")


def test_drive_config_root_folder_id() -> None:
    """root_folder_id is accepted and is the new preferred field."""
    cfg = cfg_mod.DriveConfig(root_folder_id="root123")
    assert cfg.root_folder_id == "root123"
    assert cfg.folder_id is None
    assert cfg.effective_root_folder_id() == "root123"


def test_drive_config_project_folder_name() -> None:
    """project_folder_name is accepted as an optional override."""
    cfg = cfg_mod.DriveConfig(
        root_folder_id="root123", project_folder_name="my-project"
    )
    assert cfg.project_folder_name == "my-project"


def test_drive_config_requires_root_or_folder() -> None:
    """A drive config with neither root_folder_id nor folder_id fails."""
    with pytest.raises(pydantic.ValidationError) as excinfo:
        cfg_mod.DriveConfig()
    assert "root_folder_id or folder_id" in str(excinfo.value)


def test_drive_config_folder_id_still_works_for_backwards_compat() -> None:
    """Legacy folder_id is still accepted as a single-folder target."""
    cfg = cfg_mod.DriveConfig(folder_id="legacy123")
    assert cfg.effective_root_folder_id() == "legacy123"


def test_drive_config_root_takes_precedence_over_folder() -> None:
    """When both are set, root_folder_id wins."""
    cfg = cfg_mod.DriveConfig(
        root_folder_id="root123", folder_id="legacy456"
    )
    assert cfg.effective_root_folder_id() == "root123"


def test_render_config_defaults() -> None:
    rc = cfg_mod.RenderConfig()
    assert rc.page_size == "A4"
    assert rc.margins["top"] == 2.0
    assert rc.metadata["author"] == "Sebastián Illa"
