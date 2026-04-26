from __future__ import annotations

from pathlib import Path

from mikancli.cli.prompts import confirm_choice, prompt_text, select_option
from mikancli.config import (
    get_system_downloads_path,
    pick_directory,
    save_config,
)
from mikancli.core.models import AppConfig
from mikancli.core.normalize import collapse_spaces, sanitize_folder_name


def should_save_as_default(selected_path: str, config: AppConfig) -> bool:
    if config.default_save_path == selected_path:
        return False

    return confirm_choice(
        f"Save '{selected_path}' as the default download folder for future runs?",
        default=True,
        allow_exit=True,
    )


def prompt_for_manual_save_path() -> str | None:
    entered = collapse_spaces(
        prompt_text("Enter a download folder path", allow_exit=True)
    )
    return entered or None


def prompt_for_content_folder_name(default_name: str) -> str:
    safe_default_name = sanitize_folder_name(default_name)
    entered = collapse_spaces(
        prompt_text(
            "Enter the folder name for downloaded content (press Enter to use the default title from Mikan)",
            default=safe_default_name,
            allow_exit=True,
        )
    )
    return sanitize_folder_name(entered or safe_default_name) or "MikanCli Download"


def build_content_save_path(base_path: str | None, folder_name: str) -> str | None:
    if not base_path:
        return None
    safe_folder_name = sanitize_folder_name(folder_name) or "MikanCli Download"
    return str(Path(base_path) / safe_folder_name)


def prompt_for_save_path(config: AppConfig, config_path: Path) -> str:
    downloads_path = get_system_downloads_path()
    menu_options: list[tuple[str, str]] = []

    if config.default_save_path:
        menu_options.append(("saved-default", f"Use saved default: {config.default_save_path}"))

    menu_options.append(("downloads", f"Use Downloads folder: {downloads_path}"))
    menu_options.append(("browse", "Browse for folder"))
    menu_options.append(("manual", "Type folder path manually"))

    while True:
        selected_key = select_option(
            "Choose a download folder option",
            menu_options,
            default=menu_options[0][0],
            allow_exit=True,
        )

        if selected_key == "saved-default":
            return config.default_save_path or downloads_path

        if selected_key == "downloads":
            selected_path = downloads_path
        elif selected_key == "browse":
            selected_path = pick_directory(
                initial_dir=config.default_save_path or downloads_path
            )
            if not selected_path:
                print("No folder was selected. Choose another option.")
                continue
        else:
            selected_path = prompt_for_manual_save_path()
            if not selected_path:
                print("No path was entered. Choose another option.")
                continue

        if should_save_as_default(selected_path, config):
            save_config(
                config_path,
                AppConfig(
                    default_save_path=selected_path,
                    qbittorrent_url=config.qbittorrent_url,
                    qbittorrent_username=config.qbittorrent_username,
                    qbittorrent_password=config.qbittorrent_password,
                    qbittorrent_category=config.qbittorrent_category,
                    qbittorrent_add_paused=config.qbittorrent_add_paused,
                ),
            )

        return selected_path


def resolve_save_path(
    cli_save_path: str | None,
    config: AppConfig,
    *,
    prompt_for_default: bool,
    config_path: Path,
) -> str | None:
    if cli_save_path:
        return collapse_spaces(cli_save_path)

    if not prompt_for_default:
        return config.default_save_path or get_system_downloads_path()

    return prompt_for_save_path(config, config_path)
