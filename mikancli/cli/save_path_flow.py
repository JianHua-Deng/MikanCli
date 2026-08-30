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
from mikancli.i18n import t


def should_save_as_default(selected_path: str, config: AppConfig) -> bool:
    """Ask whether a selected download folder should become the saved default. Returns False without prompting when the selected path already matches the saved default."""
    
    if config.default_save_path == selected_path:
        return False

    return confirm_choice(
        t("save.default_prompt", path=selected_path),
        default=True,
        allow_exit=True,
    )


def prompt_for_manual_save_path() -> str | None:
    """Prompt the user to type a download folder path. Returns the cleaned path, or None when the prompt is left blank."""
    entered = collapse_spaces(
        prompt_text(t("save.manual_prompt"), allow_exit=True)
    )
    return entered or None


def prompt_for_content_folder_name(default_name: str, base_path: str | None) -> str:
    """Prompt for the folder name inside the selected base download folder. Returns a sanitized folder name, falling back to the sanitized default title when left blank."""

    safe_default_name = sanitize_folder_name(default_name)
    while True:
        entered = collapse_spaces(
            prompt_text(
                t("save.content_folder_prompt"),
                default=safe_default_name,
                allow_exit=True,
            )
        )
        folder_name = sanitize_folder_name(entered or safe_default_name) or t("save.default_folder_name")
        if not base_path:
            return folder_name

        content_path = Path(base_path) / folder_name
        if not content_path.exists():
            return folder_name

        if confirm_choice(
            t("save.folder_exists", path=content_path),
            default=False,
            allow_exit=True,
        ):
            return folder_name

        print(t("save.choose_different"))


def build_content_save_path(base_path: str | None, folder_name: str) -> str | None:
    """Join a base download path with a safe content folder name. Example: build_content_save_path("D:/Anime", "Re: Zero?") returns "D:/Anime/Re Zero"."""

    if not base_path:
        return None
    safe_folder_name = sanitize_folder_name(folder_name) or t("save.default_folder_name")
    return str(Path(base_path) / safe_folder_name)


def prompt_for_save_path(config: AppConfig, config_path: Path) -> str:
    """Guide the user through choosing and optionally saving a base download folder. Returns the chosen folder path and may update the config file."""

    downloads_path = get_system_downloads_path()
    menu_options: list[tuple[str, str]] = []

    if config.default_save_path:
        menu_options.append(("saved-default", t("save.use_saved_default", path=config.default_save_path)))

    menu_options.append(("downloads", t("save.use_downloads", path=downloads_path)))
    menu_options.append(("browse", t("save.browse")))
    menu_options.append(("manual", t("save.manual")))

    while True:
        selected_key = select_option(
            t("save.choose_option"),
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
                print(t("save.no_folder_selected"))
                continue
        else:
            selected_path = prompt_for_manual_save_path()
            if not selected_path:
                print(t("save.no_path_entered"))
                continue

        if should_save_as_default(selected_path, config):
            save_config(
                config_path,
                AppConfig(
                    default_save_path=selected_path,
                    language=config.language,
                    qbittorrent_url=config.qbittorrent_url,
                    qbittorrent_username=config.qbittorrent_username,
                    qbittorrent_password=config.qbittorrent_password,
                    qbittorrent_category=config.qbittorrent_category,
                    qbittorrent_add_paused=config.qbittorrent_add_paused,
                ),
            )

        return selected_path


def resolve_save_path(cli_save_path: str | None, config: AppConfig, *, prompt_for_default: bool, config_path: Path) -> str | None:
    """Resolve the base save path from CLI input, saved config, Downloads, or an interactive prompt. Returns a path string when one is available, otherwise None."""
    if cli_save_path:
        return collapse_spaces(cli_save_path)

    if not prompt_for_default:
        return config.default_save_path or get_system_downloads_path()

    return prompt_for_save_path(config, config_path)
