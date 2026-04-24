from __future__ import annotations

from mikancli.core.models import MikanBangumi, MikanSubgroup, RuleDraft, SearchRequest
from mikancli.core.normalize import collapse_spaces, normalize_keyword


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


def build_rule_draft(
    request: SearchRequest,
    *,
    bangumi: MikanBangumi | None = None,
    subgroup: MikanSubgroup | None = None,
    notes: tuple[str, ...] | None = None,
) -> RuleDraft:
    collapsed_keyword = collapse_spaces(request.keyword)

    must_contain = _dedupe_nonempty(list(request.include_words))
    must_not_contain = _dedupe_nonempty(list(request.exclude_words))

    return RuleDraft(
        keyword=collapsed_keyword,
        normalized_keyword=normalize_keyword(request.keyword),
        rule_name=collapsed_keyword,
        must_contain=must_contain,
        must_not_contain=must_not_contain,
        mikan_title=bangumi.title if bangumi else None,
        mikan_bangumi_id=bangumi.bangumi_id if bangumi else None,
        mikan_page_url=bangumi.page_url if bangumi else None,
        mikan_subgroup=subgroup.title if subgroup else None,
        mikan_subgroup_id=subgroup.subgroup_id if subgroup else None,
        mikan_publish_group_url=subgroup.publish_group_url if subgroup else None,
        feed_url=subgroup.feed_url if subgroup else (bangumi.feed_url if bangumi else None),
        save_path=request.save_path,
        notes=notes or ("qBittorrent submission not implemented yet.",),
    )
