from __future__ import annotations

from mikancli.cli.prompts import prompt_text
from mikancli.core.normalize import collapse_spaces


def prompt_required_text(prompt: str) -> str:
    """Prompt until the user enters non-empty text. Returns the cleaned text, or propagates ExitRequested when the user quits."""
    while True:
        entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
        if entered:
            return entered
        print("A value is required.")


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
    """Prompt for optional comma-separated words and parse the result. Returns a tuple of cleaned words, or an empty tuple when the user leaves the prompt blank."""
    entered = collapse_spaces(prompt_text(prompt, allow_exit=True))
    if not entered:
        return ()

    return parse_word_list(entered)
