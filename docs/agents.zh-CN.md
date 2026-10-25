# Agent 和脚本使用指南

语言：[简体中文](agents.zh-CN.md) | [English](agents.md)

自动化请使用以下显式命令。它们不会提示交互输入，即使未指定 `--json`，也始终向标准输出写入一个 JSON 响应。先从查询结果中选择 Bangumi 和字幕组，再保存、检查并提交规则计划。

## 查询、规划、提交与验证

将 `123` 和 `456` 替换为查询结果返回的实际 ID。计划保存为本地 JSON 文件；只有 `rules apply` 会修改 qBittorrent。

```sh
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20 --offset 0
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

每一步完成后，请检查命令的退出码和 `ok`，再继续执行。提交前请检查 `plan.json`。提交时会按需创建订阅并保存 RSS 规则，根据 qBittorrent 的 RSS 设置，这可能触发下载。该操作不会修改全局 RSS 偏好设置。

使用管道输入时，`rules apply --file -` 从标准输入读取 JSON。它既接受 `rules plan` 保存的完整成功响应，也接受其中原始的 `data` 对象。Shell 重定向需要生成 UTF-8 编码的 JSON 文件。

## 命令参考

| 命令 | 用途 |
| --- | --- |
| `search KEYWORD` | 列出匹配的 Bangumi 候选项。没有匹配项时，成功返回空结果。 |
| `subgroups --bangumi-id ID` | 列出所选 Bangumi 的可用字幕组。 |
| `feed --bangumi-id ID --subgroup-id ID --limit 20 --offset 0` | 分页预览订阅中的发布内容。 |
| `rules plan --bangumi-id ID --subgroup-id ID --name NAME` | 创建可供检查的规则计划，不写入 qBittorrent。 |
| `rules apply --file PATH --if-exists fail` | 提交已保存的计划，并验证保存后的规则。使用 `-` 从标准输入读取。 |
| `rules get --name NAME` | 读取 qBittorrent 中的当前规则。 |
| `config show` | 查看隐藏凭据后的有效配置。 |
| `schema` | 导出响应封装和规则计划的 JSON Schema 文档。 |

`rules plan` 支持以下可选参数：

| 选项 | 含义 |
| --- | --- |
| `--include VALUE` | 包含过滤条件；可重复指定多个值。 |
| `--exclude VALUE` | 排除过滤条件；可重复指定多个值。 |
| `--min-episode N` | 动画最低集数。 |
| `--save-path PATH` | 精确的下载目标路径；不会额外追加以标题命名的子文件夹。 |
| `--category NAME` | qBittorrent 分类。 |
| `--add-paused` / `--no-add-paused` | 覆盖配置中的初始暂停状态。 |
| `--feed-path PATH` | 添加缺失 RSS 订阅时使用的位置。若相同 URL 的订阅已存在，则复用该订阅。 |

未指定时，下载路径、分类和暂停状态使用配置中的默认值。下载路径为空时，使用 qBittorrent 的默认目标路径。

所有显式命令都接受 `--json`、`--non-interactive`、`--config PATH`、`--timeout SECONDS` 和 `--language en|zh-CN`，这些选项可放在命令之前或之后。由于这些命令本身已提供 JSON 输出和非交互行为，`--json` 和 `--non-interactive` 可以省略。超时时间必须大于 0 且不超过 300 秒，并分别限制每次网络请求的等待时间。

```sh
mikancli --config agent-config.json --timeout 15 search "One Piece"
mikancli search "One Piece" --config agent-config.json --timeout 15
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p --include HEVC --exclude batch --save-path "/downloads/One Piece" --no-add-paused
```

## 响应约定

所有显式命令的响应都使用以下带版本号的封装：

```json
{"schema_version":1,"ok":true,"data":{},"error":null}
```

失败时，`ok` 为 `false`，`data` 为 `null`，`error` 为包含 `code`、`message`、`retryable` 和 `details` 的对象。请根据稳定的错误码和退出码决定后续操作；消息文本可能随语言变化。标准输出只包含 JSON。JSON 中的非 ASCII 文本会被转义，因此保存的计划也能在使用旧编码的 Windows 终端中正确写入并重新读取。诊断信息写入标准错误。`--help` 输出供人阅读的帮助文本，而非 JSON 响应。

计划的 `data` 包含 `plan_version: 1`、`rule_name`、`feed_url`、`feed_path` 和 `rule_definition`。其中 `rule_definition` 是拟提交的 qBittorrent RSS 规则。运行 `mikancli schema` 可获取完整的机器可读约定。更改配置或预期过滤条件后，请重新检查已保存的计划；提交操作使用计划中保存的值。

| 退出码 | 含义与处理方法 |
| --- | --- |
| `0` | 成功，包括搜索结果为空或规则未变更。 |
| `1` | 上游或网络失败；重试前请检查 `retryable`。 |
| `2` | 参数或计划无效；请修正输入。 |
| `3` | 未找到资源或尚未配置 qBittorrent；请选择现有资源或配置访问方式。 |
| `4` | 存在冲突或选择不明确；请指定明确的 ID 或检查现有规则。 |
| `5` | 部分成功或写入结果未知；重试前请读取已保存的规则并检查 qBittorrent。 |
| `130` | 操作已取消。 |

重复提交完全相同的计划会成功，并返回 `unchanged` 结果。如果同名规则的内容不同，则会因冲突而失败，除非显式指定 `--if-exists replace`。替换前请使用 `rules get` 检查现有规则。提交失败时，新建的订阅可能仍然保留，因此退出码为 `5` 时应检查当前状态。

## 配置与凭据

可以根据需要为自动化使用独立的配置文件。配置文件的选择优先级依次为 `--config PATH`、`MIKANCLI_CONFIG`、常规用户配置路径。以下环境变量会覆盖已保存的 qBittorrent 设置：

- `MIKANCLI_QBITTORRENT_URL`
- `MIKANCLI_QBITTORRENT_USERNAME`
- `MIKANCLI_QBITTORRENT_PASSWORD`

`config show` 会隐藏用户名、密码以及 URL 中嵌入的凭据。使用环境变量提供凭据，无需将其放入命令参数。现有的 `--setup-qbittorrent` 仍可用于交互式配置。

## 兼容性

在终端中运行 `mikancli` 仍会打开引导式流程。重定向标准输入时，请选择显式的非交互命令，以避免交互提示。旧版 `mikancli KEYWORD --json` 仍用于预览规则草稿，并保留原有的成功响应结构。它现在要求动画和字幕组的匹配结果均唯一：存在多个匹配项时返回 `AMBIGUOUS_SELECTION`，查询失败时返回错误封装和非零退出码。需要带版本号的 Agent 接口时，请使用 `search`、`subgroups` 和 `rules plan`。

命令名在第一个位置参数处为保留名称。若要将其中一个名称用作旧版搜索关键词，请将它放在 `--` 之后，例如 `mikancli --json -- search`。

此接口是 CLI 约定，无需 MCP 服务器。
