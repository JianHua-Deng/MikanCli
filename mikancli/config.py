from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mikancli.core.models import AppConfig
from mikancli.core.normalize import collapse_spaces

CONFIG_FILENAME = ".mikancli.json"
LEGACY_CONFIG_FILENAMES = (".autofeedsync.json",)
WINDOWS_DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"


def get_config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else Path.cwd()
    return root / CONFIG_FILENAME


def load_config(config_path: Path) -> AppConfig:
    target_path = config_path
    if not target_path.exists():
        for legacy_filename in LEGACY_CONFIG_FILENAMES:
            legacy_path = config_path.with_name(legacy_filename)
            if legacy_path.exists():
                target_path = legacy_path
                break
        else:
            return AppConfig()

    payload = json.loads(target_path.read_text(encoding="utf-8"))
    default_save_path = payload.get("default_save_path")

    if default_save_path is not None:
        default_save_path = collapse_spaces(str(default_save_path)) or None

    return AppConfig(default_save_path=default_save_path)


def save_config(config_path: Path, config: AppConfig) -> None:
    payload = {"default_save_path": config.default_save_path}
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_system_downloads_path() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                value, _ = winreg.QueryValueEx(key, WINDOWS_DOWNLOADS_GUID)
                expanded = os.path.expandvars(value)
                return str(Path(expanded))
        except OSError:
            pass

    return str(Path.home() / "Downloads")


def pick_directory(initial_dir: str | None = None) -> str | None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    try:
        selected = filedialog.askdirectory(
            initialdir=initial_dir or get_system_downloads_path(),
            title="Select download folder",
        )
    finally:
        root.destroy()

    cleaned = collapse_spaces(selected)
    return cleaned or None
