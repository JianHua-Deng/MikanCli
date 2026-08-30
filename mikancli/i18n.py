from __future__ import annotations

import os

from mikancli.core.normalize import collapse_spaces

DEFAULT_LANGUAGE = "en"
LANGUAGE_ENV_VAR = "MIKANCLI_LANG"
SUPPORTED_LANGUAGES = ("en", "zh-CN")
LANGUAGE_LABELS = {
    "en": "English",
    "zh-CN": "简体中文",
}

_current_language = DEFAULT_LANGUAGE


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "arg.description": "Search Mikan for an anime, inspect subgroup RSS contents, and preview or submit qBittorrent RSS rule inputs.",
        "arg.keyword.help": "Anime title or search phrase.",
        "arg.include.help": "Word that must appear in accepted releases. Repeat for multiple values.",
        "arg.exclude.help": "Word that must not appear in accepted releases. Repeat for multiple values.",
        "arg.save_path.help": "Optional save path to attach to the qBittorrent rule.",
        "arg.json.help": "Print the draft as JSON.",
        "arg.setup_qbittorrent.help": "Configure and verify qBittorrent WebUI access.",
        "arg.language.help": "Choose CLI language: en or zh-CN.",
        "common.exit_mikancli": "Exit MikanCli",
        "common.use_arrow_keys": "Use arrow keys",
        "common.yes": "Yes",
        "common.no": "No",
        "common.exited": "Exited MikanCli.",
        "common.not_found": "(not found)",
        "common.none": "(none)",
        "common.not_set": "(not set)",
        "common.unknown": "(unknown)",
        "common.value_required": "A value is required.",
        "startup.choose_action": "Choose what you want to do",
        "startup.search": "Search anime",
        "startup.qbittorrent": "Modify qBittorrent configurations",
        "startup.language": "Change language",
        "language.choose": "Choose language",
        "language.saved": "Language changed to {language}.",
        "language.invalid": "Unsupported language '{language}'. Supported values: {supported}.",
        "request.keyword_required_json": "keyword is required when using --json",
        "filters.include_prompt": "Enter include words separated by commas, or press Enter to skip: ",
        "filters.exclude_prompt": "Enter exclude words separated by commas, or press Enter to skip: ",
        "draft.review_note": "Review the draft before submitting it to qBittorrent.",
        "search.prompt": "Enter anime title or search keyword (or type 'exit' to quit): ",
        "search.prompt_retry": "Enter another anime title or search keyword (or type 'exit' to quit): ",
        "search.choose_candidate": "Choose the Mikan entry for '{keyword}'",
        "search.search_again": "Search with different words",
        "search.choose_subgroup": "Choose the subgroup for '{title}'",
        "search.back_to_candidates": "Back to Bangumi list",
        "search.back_to_subgroups": "Back to subgroup list",
        "search.use_subgroup": "Use this subgroup feed?",
        "search.no_search_again": "No, search with different words",
        "search.json_preview_note": "JSON mode only prints the draft; interactive mode can submit it to qBittorrent.",
        "search.no_matching_json": "No matching Mikan Bangumi entry was found for the keyword.",
        "search.no_subgroup_json": "No subgroup-specific RSS feed was found for the selected Bangumi.",
        "search.no_results": "No Mikan results found for '{keyword}'.",
        "search.no_subgroup": "No subgroup-specific RSS feed was found for the selected Bangumi.",
        "qb.setup.title": "----- qBittorrent setup instructions -----",
        "qb.setup.step1": "1. Install qBittorrent and open its settings.",
        "qb.setup.step2": "2. Enable WebUI / remote control if it is not enabled yet.",
        "qb.setup.step3": "3. Copy the WebUI address, username, and password from qBittorrent.",
        "qb.setup.step4": "4. Enter those values below.",
        "qb.setup.step5": "5. After successful verification, the values will be saved to the config file for future runs.",
        "qb.setup.url_prompt": "Enter qBittorrent WebUI URL (http://localhost:8080 is the usual default)",
        "qb.setup.auth_hint": "If you have \"Bypass authentication for clients on localhost\" enabled in qBittorrent settings, you can just press Enter for the next two prompts.",
        "qb.setup.username_prompt": "Enter qBittorrent WebUI username (press Enter to leave blank)",
        "qb.setup.password_prompt": "Enter qBittorrent WebUI password (press Enter to leave blank)",
        "qb.setup.verifying": "Verifying qBittorrent connection...",
        "qb.setup.verified": "qBittorrent connection verified successfully (version: {version}).",
        "qb.setup.offer": "qBittorrent is not set up yet. Set up qBittorrent WebUI now?",
        "qb.setup.continue_without": "Continue without qBittorrent setup for now?",
        "qb.setup.retry": "Retry qBittorrent setup?",
        "qb.submit.not_configured": "qBittorrent is not configured. Please set up qBittorrent access to submit rules.",
        "qb.submit.feed_name_prompt": "Enter qBittorrent RSS feed name (press Enter to use the default)",
        "qb.submit.continue": "Continue to qBittorrent submission details for this RSS feed and rule?",
        "qb.submit.replace_existing": "qBittorrent already has a rule named '{rule_name}'. Replace it?",
        "qb.submit.submitting": "Submitting RSS feed and download rule to qBittorrent...",
        "qb.submit.failed": "Failed to submit to qBittorrent: {error}",
        "qb.submit.success": "qBittorrent feed and download rule submitted and verified successfully.",
        "save.default_prompt": "Save '{path}' as the default download folder for future runs?",
        "save.manual_prompt": "Enter a download folder path",
        "save.content_folder_prompt": "Enter the folder name for downloaded content (press Enter to use the default title from Mikan)",
        "save.folder_exists": "'{path}' already exists. Continue using this folder?",
        "save.choose_different": "Choose a different folder name.",
        "save.choose_option": "Choose a download folder option",
        "save.use_saved_default": "Use saved default: {path}",
        "save.use_downloads": "Use Downloads folder: {path}",
        "save.browse": "Browse for folder",
        "save.manual": "Type folder path manually",
        "save.no_folder_selected": "No folder was selected. Choose another option.",
        "save.no_path_entered": "No path was entered. Choose another option.",
        "save.default_folder_name": "MikanCli Download",
        "display.rule_header": "---- Rule Draft ----",
        "display.keyword": "Keyword: {value}",
        "display.normalized_keyword": "Normalized keyword: {value}",
        "display.rule_name": "Rule name: {value}",
        "display.mikan_title": "Mikan title: {value}",
        "display.mikan_subgroup": "Mikan subgroup: {value}",
        "display.mikan_page": "Mikan page: {value}",
        "display.feed_url": "Feed URL: {value}",
        "display.must_contain": "Must contain: {value}",
        "display.must_not_contain": "Must not contain: {value}",
        "display.save_path": "Save path: {value}",
        "display.rule_footer": "---- End Rule Draft Summary ----",
        "display.next_step": "Next step: {value}",
        "display.feed_preview": "Subgroup preview: {title}",
        "display.feed_url_plain": "Feed URL: {url}",
        "display.items": "Items: {count}",
        "display.feed_empty": "(The RSS feed is empty.)",
        "display.size_updated": "Size: {size} | Updated: {updated}",
    },
    "zh-CN": {
        "arg.description": "搜索 Mikan 动画，查看字幕组 RSS 内容，并预览或提交 qBittorrent RSS 规则。",
        "arg.keyword.help": "动画标题或搜索关键词。",
        "arg.include.help": "已接受发布标题中必须包含的词。可重复传入多个值。",
        "arg.exclude.help": "已接受发布标题中不能包含的词。可重复传入多个值。",
        "arg.save_path.help": "附加到 qBittorrent 规则的可选保存路径。",
        "arg.json.help": "以 JSON 形式打印规则草稿。",
        "arg.setup_qbittorrent.help": "配置并验证 qBittorrent WebUI 访问。",
        "arg.language.help": "选择 CLI 语言：en 或 zh-CN。",
        "common.exit_mikancli": "退出 MikanCli",
        "common.use_arrow_keys": "使用方向键",
        "common.yes": "是",
        "common.no": "否",
        "common.exited": "已退出 MikanCli。",
        "common.not_found": "（未找到）",
        "common.none": "（无）",
        "common.not_set": "（未设置）",
        "common.unknown": "（未知）",
        "common.value_required": "必须输入一个值。",
        "startup.choose_action": "选择你想执行的操作",
        "startup.search": "搜索动画",
        "startup.qbittorrent": "修改 qBittorrent 配置",
        "startup.language": "切换语言",
        "language.choose": "选择语言",
        "language.saved": "语言已切换为{language}。",
        "language.invalid": "不支持的语言 '{language}'。支持的值：{supported}。",
        "request.keyword_required_json": "使用 --json 时必须提供 keyword",
        "filters.include_prompt": "输入包含词，用逗号分隔；直接按 Enter 跳过：",
        "filters.exclude_prompt": "输入排除词，用逗号分隔；直接按 Enter 跳过：",
        "draft.review_note": "提交到 qBittorrent 前请检查规则草稿。",
        "search.prompt": "输入动画标题或搜索关键词（输入 'exit' 退出）：",
        "search.prompt_retry": "输入另一个动画标题或搜索关键词（输入 'exit' 退出）：",
        "search.choose_candidate": "为 '{keyword}' 选择 Mikan 条目",
        "search.search_again": "使用其他关键词搜索",
        "search.choose_subgroup": "为 '{title}' 选择字幕组",
        "search.back_to_candidates": "返回 Bangumi 列表",
        "search.back_to_subgroups": "返回字幕组列表",
        "search.use_subgroup": "使用这个字幕组订阅？",
        "search.no_search_again": "否，使用其他关键词搜索",
        "search.json_preview_note": "JSON 模式只打印规则草稿；交互模式可以提交到 qBittorrent。",
        "search.no_matching_json": "没有找到匹配该关键词的 Mikan Bangumi 条目。",
        "search.no_subgroup_json": "所选 Bangumi 没有找到字幕组专属 RSS 订阅。",
        "search.no_results": "没有找到与 '{keyword}' 匹配的 Mikan 结果。",
        "search.no_subgroup": "所选 Bangumi 没有找到字幕组专属 RSS 订阅。",
        "qb.setup.title": "----- qBittorrent 设置说明 -----",
        "qb.setup.step1": "1. 安装 qBittorrent 并打开设置。",
        "qb.setup.step2": "2. 如果还没有启用 WebUI / 远程控制，请先启用。",
        "qb.setup.step3": "3. 从 qBittorrent 复制 WebUI 地址、用户名和密码。",
        "qb.setup.step4": "4. 在下面输入这些值。",
        "qb.setup.step5": "5. 验证成功后，这些值会保存到配置文件，供以后运行使用。",
        "qb.setup.url_prompt": "输入 qBittorrent WebUI URL（通常默认是 http://localhost:8080）",
        "qb.setup.auth_hint": "如果你在 qBittorrent 设置中启用了“绕过 localhost 客户端认证”，下面两个提示可以直接按 Enter。",
        "qb.setup.username_prompt": "输入 qBittorrent WebUI 用户名（按 Enter 留空）",
        "qb.setup.password_prompt": "输入 qBittorrent WebUI 密码（按 Enter 留空）",
        "qb.setup.verifying": "正在验证 qBittorrent 连接...",
        "qb.setup.verified": "qBittorrent 连接验证成功（版本：{version}）。",
        "qb.setup.offer": "尚未设置 qBittorrent。现在设置 qBittorrent WebUI 吗？",
        "qb.setup.continue_without": "暂时不设置 qBittorrent 并继续？",
        "qb.setup.retry": "重试 qBittorrent 设置？",
        "qb.submit.not_configured": "qBittorrent 尚未配置。请先设置 qBittorrent 访问后再提交规则。",
        "qb.submit.feed_name_prompt": "输入 qBittorrent RSS 订阅名称（按 Enter 使用默认值）",
        "qb.submit.continue": "继续为这个 RSS 订阅和规则填写 qBittorrent 提交信息？",
        "qb.submit.replace_existing": "qBittorrent 中已经有名为 '{rule_name}' 的规则。要替换它吗？",
        "qb.submit.submitting": "正在向 qBittorrent 提交 RSS 订阅和下载规则...",
        "qb.submit.failed": "提交到 qBittorrent 失败：{error}",
        "qb.submit.success": "qBittorrent 订阅和下载规则已提交并验证成功。",
        "save.default_prompt": "将 '{path}' 保存为以后运行的默认下载文件夹？",
        "save.manual_prompt": "输入下载文件夹路径",
        "save.content_folder_prompt": "输入下载内容的文件夹名称（按 Enter 使用 Mikan 的默认标题）",
        "save.folder_exists": "'{path}' 已存在。继续使用这个文件夹？",
        "save.choose_different": "请选择另一个文件夹名称。",
        "save.choose_option": "选择下载文件夹选项",
        "save.use_saved_default": "使用已保存的默认路径：{path}",
        "save.use_downloads": "使用 Downloads 文件夹：{path}",
        "save.browse": "浏览选择文件夹",
        "save.manual": "手动输入文件夹路径",
        "save.no_folder_selected": "没有选择文件夹。请选择另一个选项。",
        "save.no_path_entered": "没有输入路径。请选择另一个选项。",
        "save.default_folder_name": "MikanCli 下载",
        "display.rule_header": "---- 规则草稿 ----",
        "display.keyword": "关键词：{value}",
        "display.normalized_keyword": "规范化关键词：{value}",
        "display.rule_name": "规则名称：{value}",
        "display.mikan_title": "Mikan 标题：{value}",
        "display.mikan_subgroup": "Mikan 字幕组：{value}",
        "display.mikan_page": "Mikan 页面：{value}",
        "display.feed_url": "订阅 URL：{value}",
        "display.must_contain": "必须包含：{value}",
        "display.must_not_contain": "不能包含：{value}",
        "display.save_path": "保存路径：{value}",
        "display.rule_footer": "---- 规则草稿摘要结束 ----",
        "display.next_step": "下一步：{value}",
        "display.feed_preview": "字幕组预览：{title}",
        "display.feed_url_plain": "订阅 URL：{url}",
        "display.items": "条目数量：{count}",
        "display.feed_empty": "（RSS 订阅为空。）",
        "display.size_updated": "大小：{size} | 更新时间：{updated}",
    },
}


def normalize_language(value: str | None) -> str | None:
    cleaned = collapse_spaces(value or "")
    if not cleaned:
        return None

    marker = cleaned.replace("_", "-").casefold()
    if marker in {"en", "english"}:
        return "en"
    if marker in {"zh", "zh-cn", "zh-hans", "cn", "chinese", "simplified-chinese"}:
        return "zh-CN"
    return None


def language_from_env() -> str | None:
    return normalize_language(os.environ.get(LANGUAGE_ENV_VAR))


def set_language(language: str | None) -> str:
    global _current_language

    normalized = normalize_language(language) or DEFAULT_LANGUAGE
    _current_language = normalized
    return _current_language


def get_language() -> str:
    return _current_language


def t(key: str, **values: object) -> str:
    template = TRANSLATIONS.get(_current_language, {}).get(key)
    if template is None:
        template = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    if values:
        return template.format(**values)
    return template
