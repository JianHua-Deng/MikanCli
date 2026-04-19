from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")
_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*]')

# Replaces multiple whitespaces or newlines with a single space and trims the edges
def collapse_spaces(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value).strip()

# Cleans up spacing and aggressively lowercases the string for consistent, case-insensitive matching
def normalize_keyword(keyword: str) -> str:
    return collapse_spaces(keyword).casefold()

# Removes illegal path characters and trailing periods/spaces to ensure safe Windows folder creation
def sanitize_folder_name(value: str) -> str:
    cleaned = _INVALID_PATH_CHARS_RE.sub("", collapse_spaces(value))
    return cleaned.rstrip(". ")
