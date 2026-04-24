from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mikancli.core.models import AppConfig
from mikancli.core.normalize import collapse_spaces

CONFIG_FILENAME = ".mikancli.json"
WINDOWS_DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"


def get_config_path(base_dir: Path | None = None) -> Path:
    root = base_dir if base_dir is not None else Path.cwd()
    return root / CONFIG_FILENAME


def _resolve_existing_config_path(config_path: Path) -> Path | None:
    target_path = config_path
    if target_path.exists():
        return target_path

    return None


def _load_config_payload(config_path: Path) -> dict[str, object]:
    target_path = _resolve_existing_config_path(config_path)
    if target_path is None:
        return {}

    payload = json.loads(target_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {}

    return payload


def load_config(config_path: Path) -> AppConfig:
    payload = _load_config_payload(config_path)

    default_save_path = payload.get("default_save_path")
    qbittorrent_url = payload.get("qbittorrent_url")
    qbittorrent_username = payload.get("qbittorrent_username")
    qbittorrent_password = payload.get("qbittorrent_password")

    if default_save_path is not None:
        default_save_path = collapse_spaces(str(default_save_path)) or None
    if qbittorrent_url is not None:
        qbittorrent_url = collapse_spaces(str(qbittorrent_url)) or None
    if qbittorrent_username is not None:
        qbittorrent_username = collapse_spaces(str(qbittorrent_username)) or None
    if qbittorrent_password is not None:
        qbittorrent_password = str(qbittorrent_password)

    return AppConfig(
        default_save_path=default_save_path,
        qbittorrent_url=qbittorrent_url,
        qbittorrent_username=qbittorrent_username,
        qbittorrent_password=qbittorrent_password,
    )


def save_config(config_path: Path, config: AppConfig) -> None:
    payload = _load_config_payload(config_path)
    payload.update(
        {
            "default_save_path": config.default_save_path,
            "qbittorrent_url": config.qbittorrent_url,
            "qbittorrent_username": config.qbittorrent_username,
            "qbittorrent_password": config.qbittorrent_password,
        }
    )
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
