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

_WINDOWS_RESERVED_FOLDER_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}
"""
Matches Windows reserved device names that cannot be used as folder names, even with an extension.
"""

def collapse_spaces(value: str) -> str:
    """Collapse repeated whitespace and trim the ends of a string. Example: collapse_spaces("  Solo   Leveling  ") returns "Solo Leveling"."""
    return _WHITESPACE_RE.sub(" ", value).strip()


def normalize_keyword(keyword: str) -> str:
    """Normalize a search keyword for case-insensitive comparisons. Example: normalize_keyword("  Solo Leveling  ") returns "solo leveling"."""
    return collapse_spaces(keyword).casefold()


def sanitize_folder_name(value: str) -> str:
    """Remove unsafe Windows path characters from a folder name. Example: sanitize_folder_name("Re: Zero?") returns "Re Zero"."""
    cleaned = _INVALID_PATH_CHARS_RE.sub("", collapse_spaces(value))
    cleaned = cleaned.rstrip(". ")
    if cleaned.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_FOLDER_NAMES:
        return f"{cleaned} Folder"
    return cleaned
