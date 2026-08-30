from __future__ import annotations

from mikancli.cli.prompts import prompt_text
from mikancli.core.normalize import collapse_spaces
from mikancli.i18n import t


def prompt_required_text(prompt: str) -> str:
    while True:
        entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
        if entered:
            return entered
        print(t("common.value_required"))


def parse_word_list(value: str) -> tuple[str, ...]:
    """Parse a comma-separated word list while dropping blanks and duplicates. Example: parse_word_list("HEVC, 1080p, HEVC") returns ("HEVC", "1080p")."""
    words: list[str] = []
    seen: set[str] = set()

    for raw_part in value.split(","):
        cleaned = collapse_spaces(raw_part)
        if not cleaned:
            continue

        marker = cleaned.casefold()
        if marker in seen:
            continue

        seen.add(marker)
        words.append(cleaned)

    return tuple(words)


def prompt_word_list(prompt: str) -> tuple[str, ...]:
    entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
    if not entered:
        return ()

    return parse_word_list(entered)


def parse_optional_positive_int(value: str, *, field_name: str) -> int | None:
    cleaned = collapse_spaces(value)
    if not cleaned:
        return None

    try:
        parsed = int(cleaned)
    except ValueError as exc:
        raise ValueError(t("filters.positive_int_required", field=field_name)) from exc

    if parsed < 1:
        raise ValueError(t("filters.positive_int_required", field=field_name))
    return parsed


def prompt_optional_positive_int(prompt: str, *, field_name: str) -> int | None:
    while True:
        entered = prompt_text(prompt, allow_exit=True)
        try:
            return parse_optional_positive_int(entered, field_name=field_name)
        except ValueError as exc:
            print(exc)
