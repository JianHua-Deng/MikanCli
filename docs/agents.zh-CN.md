# Agent 和脚本使用指南

语言：[简体中文](agents.zh-CN.md) | [English](agents.md)

自动化请使用以下命令。它们不会提示交互输入，向标准输出返回一个 JSON 响应；`--help` 返回纯文本帮助。

## 工作流程

```sh
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

将示例 ID 替换为查询结果中的实际 ID。每一步都检查退出码和 `ok`，提交前检查计划。

只有 `rules apply` 会写入 qBittorrent。它会创建缺失的订阅、保存并验证规则，且可能触发下载。相同规则返回 `unchanged`；同名规则内容不同时会失败，除非指定 `--if-exists replace`。全局 RSS 偏好设置不会改变。

提交操作接受 UTF-8 文件或标准输入（`--file -`），内容可以是完整的计划成功响应，也可以是其中原始的 `data` 对象。提交时使用计划中保存的值。

## 命令与选项

| 命令 | 用途 |
| --- | --- |
| `search KEYWORD` | 列出动画候选项；无匹配时返回空结果。 |
| `subgroups --bangumi-id ID` | 列出动画的字幕组订阅。 |
| `feed --bangumi-id ID --subgroup-id ID` | 预览所选订阅中的发布内容。 |
| `rules plan --bangumi-id ID --subgroup-id ID --name NAME` | 生成计划，不提交。 |
| `rules apply --file PATH` | 提交并验证已保存的计划。 |
| `rules get --name NAME` | 读取已保存的规则并检查其订阅。 |
| `config show` | 查看隐藏凭据后的有效配置。 |
| `schema` | 导出响应和计划的 JSON Schema。 |

`search` 和 `feed` 接受 `--limit N`（正整数，默认 20）和 `--offset N`（非负整数，默认 0）。

`rules plan` 的可选参数：

| 选项 | 含义 |
| --- | --- |
| `--include VALUE` | 必须包含的字面词或短语；重复指定时要求全部匹配。 |
| `--exclude VALUE` | 要排除的字面词或短语；重复指定时任一匹配即排除。 |
| `--min-episode N` | 动画最低集数。 |
| `--save-path PATH` | 精确的目标路径；不会追加标题子文件夹。 |
| `--category NAME` | qBittorrent 分类。 |
| `--add-paused` / `--no-add-paused` | 设置匹配的种子是否以暂停状态添加。 |
| `--feed-path PATH` | 新订阅的位置；相同 URL 的现有订阅会被复用。 |

未指定路径、分类和暂停选项时，使用配置中的默认值。`--save-path ""` 使用 qBittorrent 的默认目标路径。

通用选项可放在命令之前或之后：`--config PATH`、`--timeout SECONDS`（默认 15；大于 0 且不超过 300，分别限制每次网络请求）、`--json`、`--non-interactive`，以及 `--language en` / `--language zh-CN`。JSON 和非交互行为已默认启用。命令帮助和错误消息目前使用英文。

## 响应与错误

```json
{"schema_version":1,"ok":true,"data":{},"error":null}
```

失败时，`ok` 为 `false`，`data` 为 `null`，`error` 包含 `code`、`message`、`retryable` 和 `details`。请根据错误码和退出码决定后续操作。诊断信息写入标准错误。

计划数据包含 `plan_version: 1`、`rule_name`、`feed_url`、`feed_path` 和 `rule_definition`。运行 `mikancli schema` 获取完整 Schema。

分页的搜索和订阅数据包含 `items`、`total`、`offset` 和 `limit`。

| 退出码 | 含义与处理方法 |
| --- | --- |
| `0` | 成功，包括空结果和未变更的规则。 |
| `1` | 上游或网络失败；检查 `retryable`。 |
| `2` | 参数、配置或计划无效；修正输入。 |
| `3` | 资源不存在或尚未配置 qBittorrent。 |
| `4` | 冲突或选择不明确；检查现有规则或指定明确的 ID。 |
| `5` | 部分成功或写入结果未知；重试前检查规则和订阅。 |
| `130` | 操作已取消。 |

## 配置

配置选择顺序：`--config PATH` → `MIKANCLI_CONFIG` → 默认用户配置。以下环境变量会覆盖已保存的 qBittorrent 设置：

- `MIKANCLI_QBITTORRENT_URL`
- `MIKANCLI_QBITTORRENT_USERNAME`
- `MIKANCLI_QBITTORRENT_PASSWORD`

WebUI URL 必须使用 HTTP(S)，不能嵌入凭据、查询参数或片段。请在独立的用户名和密码设置中提供凭据。

## 旧版用法

单独运行 `mikancli` 会打开引导菜单。旧版 `mikancli KEYWORD --json` 使用不同的成功响应格式，并要求动画和字幕组的匹配结果均唯一；存在多个匹配项时返回 `AMBIGUOUS_SELECTION`，退出码为 4。

命令名在第一个位置参数处为保留名称。若旧版搜索关键词与命令名相同，请使用 `mikancli --json -- search`。
