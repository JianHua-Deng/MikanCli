from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")
"""
Matches one or more whitespace characters, including spaces, tabs, and newlines.
It is used before trimming text so uneven spacing becomes one readable single-space gap.
Example: before "  Solo \\n Leveling  " -> result "Solo Leveling".
"""

_INVALID_PATH_CHARS_RE = re.compile(r'[<>:"/\\|?*]')
"""
Matches characters that Windows does not allow in file or folder names.
It is used when creating download folder names so titles from Mikan do not produce invalid paths.
Example: before 'One Piece: "Egghead"?' -> result "One Piece Egghead".
"""

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
