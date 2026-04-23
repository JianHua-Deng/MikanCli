from __future__ import annotations

from mikancli.normalize import collapse_spaces
from mikancli.prompts import prompt_text


def prompt_required_text(prompt: str) -> str:
    while True:
        entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
        if entered:
            return entered
        print("A value is required.")


def parse_word_list(value: str) -> tuple[str, ...]:
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
