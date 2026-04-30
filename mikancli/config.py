from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from mikancli.core.models import AppConfig
from mikancli.core.normalize import collapse_spaces

USER_CONFIG_FILENAME = "config.json"
WINDOWS_CONFIG_DIR_NAME = "MikanCli"
POSIX_CONFIG_DIR_NAME = "mikancli"
WINDOWS_DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"


def get_config_path(base_dir: Path | None = None) -> Path:
    """Return the MikanCli config path. Defaults to a user-level config file so installed CLI runs share settings across terminal locations."""
    if base_dir is not None:
        return base_dir / USER_CONFIG_FILENAME

    if sys.platform == "win32":
        config_root = os.environ.get("APPDATA")
        if config_root:
            return Path(config_root) / WINDOWS_CONFIG_DIR_NAME / USER_CONFIG_FILENAME
        return Path.home() / "AppData" / "Roaming" / WINDOWS_CONFIG_DIR_NAME / USER_CONFIG_FILENAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / WINDOWS_CONFIG_DIR_NAME / USER_CONFIG_FILENAME

    config_root = os.environ.get("XDG_CONFIG_HOME")
    if config_root:
        return Path(config_root) / POSIX_CONFIG_DIR_NAME / USER_CONFIG_FILENAME
    return Path.home() / ".config" / POSIX_CONFIG_DIR_NAME / USER_CONFIG_FILENAME


def resolve_existing_config_path(config_path: Path) -> Path | None:
    target_path = config_path
    if target_path.exists():
        return target_path

    return None


def load_config_payload(config_path: Path) -> dict[str, object]:
    target_path = resolve_existing_config_path(config_path)
    if target_path is None:
        return {}

    try:
        payload = json.loads(target_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}

    return payload


def coerce_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        cleaned = collapse_spaces(value).casefold()
        if cleaned in {"true", "yes", "1", "on"}:
            return True
        if cleaned in {"false", "no", "0", "off", ""}:
            return False
    if value is None:
        return default
    return bool(value)


def load_config(config_path: Path) -> AppConfig:
    """Load app configuration from JSON, coercing known fields into AppConfig. Returns an empty AppConfig when the config file is missing or not a JSON object."""
    payload = load_config_payload(config_path)

    default_save_path = payload.get("default_save_path")
    qbittorrent_url = payload.get("qbittorrent_url")
    qbittorrent_username = payload.get("qbittorrent_username")
    qbittorrent_password = payload.get("qbittorrent_password")
    qbittorrent_category = payload.get("qbittorrent_category")
    qbittorrent_add_paused = payload.get("qbittorrent_add_paused")

    if default_save_path is not None:
        default_save_path = collapse_spaces(str(default_save_path)) or None
    if qbittorrent_url is not None:
        qbittorrent_url = collapse_spaces(str(qbittorrent_url)) or None
    if qbittorrent_username is not None:
        qbittorrent_username = collapse_spaces(str(qbittorrent_username)) or None
    if qbittorrent_password is not None:
        qbittorrent_password = str(qbittorrent_password)
    if qbittorrent_category is not None:
        qbittorrent_category = collapse_spaces(str(qbittorrent_category)) or None

    return AppConfig(
        default_save_path=default_save_path,
        qbittorrent_url=qbittorrent_url,
        qbittorrent_username=qbittorrent_username,
        qbittorrent_password=qbittorrent_password,
        qbittorrent_category=qbittorrent_category,
        qbittorrent_add_paused=coerce_bool(qbittorrent_add_paused),
    )


def save_config(config_path: Path, config: AppConfig) -> None:
    """Write AppConfig fields to the config file while preserving unknown JSON keys. Returns None after writing the merged JSON payload."""
    payload = load_config_payload(config_path)
    payload.update(
        {
            "default_save_path": config.default_save_path,
            "qbittorrent_url": config.qbittorrent_url,
            "qbittorrent_username": config.qbittorrent_username,
            "qbittorrent_password": config.qbittorrent_password,
            "qbittorrent_category": config.qbittorrent_category,
            "qbittorrent_add_paused": config.qbittorrent_add_paused,
        }
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_system_downloads_path() -> str:
    """Return the user's Downloads folder with a Windows registry lookup when available. Falls back to the home-directory Downloads path when the platform lookup is unavailable."""
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
    """Open a native folder picker. Returns the selected directory, or None if tkinter is unavailable or the picker is cancelled."""
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
