from __future__ import annotations

from autofeedsync.models import RuleDraft, SearchRequest
from autofeedsync.normalize import collapse_spaces, normalize_keyword


def _dedupe_nonempty(values: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []

    for value in values:
        cleaned = collapse_spaces(value)
        if not cleaned:
            continue

        marker = cleaned.casefold()
        if marker in seen:
            continue

        seen.add(marker)
        ordered.append(cleaned)

    return tuple(ordered)


def build_rule_draft(request: SearchRequest) -> RuleDraft:
    collapsed_keyword = collapse_spaces(request.keyword)
    rule_name = collapsed_keyword

    must_contain = _dedupe_nonempty(
        [
            request.group or "",
            request.resolution or "",
            *request.include_words,
        ]
    )
    must_not_contain = _dedupe_nonempty(list(request.exclude_words))

    notes = (
        "Mikan lookup not implemented yet.",
        "qBittorrent submission not implemented yet.",
    )

    return RuleDraft(
        keyword=collapsed_keyword,
        normalized_keyword=normalize_keyword(request.keyword),
        rule_name=rule_name,
        must_contain=must_contain,
        must_not_contain=must_not_contain,
        save_path=request.save_path,
        notes=notes,
    )
