from __future__ import annotations

from typing import TypeVar

from autofeedsync.normalize import collapse_spaces

T = TypeVar("T")


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
) -> T:
    inquirer = _get_inquirer()

    choices = [{"value": value, "name": label} for value, label in options]
    prompt = inquirer.select(
        message=message,
        choices=choices,
        default=default,
        pointer=">",
        instruction="Use arrow keys",
        max_height="70%",
        cycle=True,
    )
    return prompt.execute()


def prompt_text(
    message: str,
    *,
    default: str | None = None,
) -> str:
    inquirer = _get_inquirer()

    prompt = inquirer.text(
        message=message,
        default=default or "",
    )
    return collapse_spaces(prompt.execute())


def confirm_choice(message: str, *, default: bool = True) -> bool:
    default_value = "yes" if default else "no"
    selected = select_option(
        message,
        [
            ("yes", "Yes"),
            ("no", "No"),
        ],
        default=default_value,
    )
    return selected == "yes"
