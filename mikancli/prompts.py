from __future__ import annotations

from typing import TypeVar

from mikancli.normalize import collapse_spaces

T = TypeVar("T")
EXIT_OPTION = "__exit_cli__"
EXIT_TEXT_VALUES = {"exit", "quit"}


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


def select_option(
    message: str,
    options: list[tuple[T, str]],
    *,
    default: T | None = None,
    allow_exit: bool = False,
) -> T:
    inquirer = _get_inquirer()

    choices = [{"value": value, "name": label} for value, label in options]
    if allow_exit:
        choices.append({"value": EXIT_OPTION, "name": "Exit MikanCli"})
    prompt = inquirer.select(
        message=message,
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
        message=message,
        default=default or "",
    )
    entered = collapse_spaces(prompt.execute())
    if allow_exit and entered.casefold() in EXIT_TEXT_VALUES:
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
