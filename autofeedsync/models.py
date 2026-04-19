from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AppConfig:
    default_save_path: str | None = None


@dataclass(frozen=True)
class SearchRequest:
    keyword: str
    include_words: tuple[str, ...] = ()
    exclude_words: tuple[str, ...] = ()
    group: str | None = None
    resolution: str | None = None
    save_path: str | None = None


@dataclass(frozen=True)
class RuleDraft:
    keyword: str
    normalized_keyword: str
    rule_name: str
    must_contain: tuple[str, ...]
    must_not_contain: tuple[str, ...]
    save_path: str | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
