from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypeVar

from mikancli.core.normalize import collapse_spaces

T = TypeVar("T")
EXIT_OPTION = "__exit_cli__"
EXIT_TEXT_VALUES = {"exit", "quit"}
PROMPT_SEPARATOR = "----------------------------------------"
MENU_SEPARATOR_LABEL = ""


class ExitRequested(Exception):
    """Raised when the user explicitly chooses to quit the interactive CLI."""


def _get_inquirer():
    try:
        from InquirerPy import inquirer
    except ImportError as exc:
        raise RuntimeError(
            "Interactive mode requires InquirerPy. Install project dependencies first."
        ) from exc

    return inquirer


def _prepare_prompt_message(message: str) -> str:
    print(f"\n{PROMPT_SEPARATOR}")
    return message.strip("\n")


def _get_menu_separator() -> Any | None:
    try:
        from InquirerPy.separator import Separator
    except ImportError:
        return None

    return Separator(MENU_SEPARATOR_LABEL)


def _build_select_choices(
    options: list[tuple[T, str]],
    *,
    allow_exit: bool,
    separator_before_values: Iterable[T] = (),
    separator_before_exit: bool = True,
) -> list[object]:
    separator_values = set(separator_before_values)
    separator = _get_menu_separator()
    choices: list[object] = []

    for value, label in options:
        if value in separator_values and separator is not None:
            choices.append(separator)
        choices.append({"value": value, "name": label})

    if allow_exit:
        if choices and separator_before_exit and separator is not None:
            choices.append(separator)
        choices.append({"value": EXIT_OPTION, "name": "Exit MikanCli"})

    return choices


def select_option(
    message: str,
    options: list[tuple[T, str]],
    *,
    default: T | None = None,
    allow_exit: bool = False,
    separator_before_values: Iterable[T] = (),
    separator_before_exit: bool = True,
) -> T:
    inquirer = _get_inquirer()

    choices = _build_select_choices(
        options,
        allow_exit=allow_exit,
        separator_before_values=separator_before_values,
        separator_before_exit=separator_before_exit,
    )
    prompt = inquirer.select(
        message=_prepare_prompt_message(message),
        choices=choices,
        default=default,
        pointer=">",
        instruction="Use arrow keys",
        max_height="70%",
        cycle=True,
    )
    selected = prompt.execute()
    if allow_exit and selected == EXIT_OPTION:
        raise ExitRequested()
    return selected


def prompt_text(
    message: str,
    *,
    default: str | None = None,
    allow_exit: bool = False,
) -> str:
    inquirer = _get_inquirer()

    prompt = inquirer.text(
        message=_prepare_prompt_message(message),
        default=default or "",
    )
    entered = collapse_spaces(prompt.execute())
    if allow_exit and entered.casefold() in EXIT_TEXT_VALUES:
        raise ExitRequested()
    return entered


def prompt_password(
    message: str,
    *,
    allow_exit: bool = False,
) -> str:
    inquirer = _get_inquirer()
    prompt_factory = getattr(inquirer, "secret", None)
    if prompt_factory is not None:
        prompt = prompt_factory(message=_prepare_prompt_message(message))
    else:  # pragma: no cover - fallback for alternate InquirerPy versions
        prompt = inquirer.text(message=_prepare_prompt_message(message), secret=True)

    entered = prompt.execute()
    if allow_exit and entered.strip().casefold() in EXIT_TEXT_VALUES:
        raise ExitRequested()
    return entered


def confirm_choice(
    message: str,
    *,
    default: bool = True,
    allow_exit: bool = False,
) -> bool:
    default_value = "yes" if default else "no"
    selected = select_option(
        message,
        [
            ("yes", "Yes"),
            ("no", "No"),
        ],
        default=default_value,
        allow_exit=allow_exit,
    )
    return selected == "yes"
