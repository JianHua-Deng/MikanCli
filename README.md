# MikanCli

语言：[简体中文](README.md) | [English](README.en.md)

MikanCli 是一个 Python 命令行工具，可以在 Mikanani.me 上搜索番剧/动画，选定对应的 Bangumi 条目和字幕组 RSS 订阅，并据此生成 qBittorrent 的 RSS 下载规则。

它既提供引导式交互流程，也提供面向 AI Agent 和脚本的非交互式 JSON 命令：可以查找订阅、保存规则计划，再提交到 qBittorrent 并验证结果。

## 功能

- 按动画标题或关键词搜索 Mikan
- 从匹配的 Bangumi 结果和字幕组 RSS 订阅中进行选择
- 在确认订阅前分页预览最近的 RSS 条目
- 使用 Rich 显示规则摘要、订阅预览和状态消息，并在网络请求期间显示加载指示器
- 使用包含和排除过滤条件生成 qBittorrent RSS 规则
- 按最低集数过滤动画发布标题
- 选择并保存默认下载文件夹
- 通过命令行配置 qBittorrent WebUI 访问
- 将 RSS 订阅和自动下载规则提交到 qBittorrent，并验证 qBittorrent 已保存这些内容
- 以 JSON 形式输出规则草稿，不提交任何内容
- 通过显式 ID、带版本号的 JSON 响应和支持安全重复提交的规则计划，支持 Agent 工作流

## 界面预览

![搜索输入框（演示数据）](docs/images/search-input.png)

![RSS 订阅预览（演示数据）](docs/images/feed-preview.png)

## 环境要求

- Python 3.10 或更新版本
- `pipx`，用于将 MikanCli 安装为独立命令行应用
- qBittorrent，如果你希望 MikanCli 自动提交 RSS 订阅和规则

## 快速开始 | 安装

推荐使用 `pipx` 安装 MikanCli，这样可以在任意终端中直接使用。
如果已经安装 `pipx`，可以跳过以下两条命令：

```bash
python -m pip install --user pipx           # 为当前用户安装 pipx
python -m pipx ensurepath                   # 将 pipx 可执行文件目录添加到 PATH
```

运行 `pipx ensurepath` 后，请重新打开一个终端，然后执行：

```bash
pipx install mikancli
```

## 使用方法

安装完成后，运行以下命令，并按菜单提示操作：

```bash
mikancli
```

## AI Agent 和脚本

用显式命令搜索候选项、选定 ID、预览发布内容，然后保存规则计划并提交。这些命令不会发起交互式提示，始终输出 JSON。重复提交同一计划时，会报告规则未变更。

```bash
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

请将示例中的 ID 替换为搜索结果中的实际 ID，并在提交前检查计划。在这些非交互式命令中，只有 `rules apply` 会写入 qBittorrent，且可能触发 RSS 下载。可用 `config show` 查看已隐藏凭据的配置，用 `schema` 导出响应和规则计划的 JSON Schema。

这些命令接受 `--config PATH`、`--timeout SECONDS`，以及可选的 `--json` / `--non-interactive` 标志。完整的命令参考、响应结构、退出码和凭据环境变量请见 Agent 使用指南：[简体中文](docs/agents.zh-CN.md) | [English](docs/agents.md)。

## 通过克隆仓库安装

从本地克隆安装：

```bash
git clone https://github.com/JianHua-Deng/MikanCli.git
cd MikanCli
python -m pipx install -e .
```

开发时也可以使用可编辑模式的 `pip` 安装：

```bash
python -m pip install -e .
python -m mikancli
```

依赖项（包括用于输出的 Rich 和用于交互提示的 InquirerPy）声明在 `pyproject.toml` 中，由 `pip` 或 `pipx` 安装。MikanCli 运行时不会安装依赖包。

如果已有可编辑模式的 `pip` 安装，在拉取依赖变更后，需要在原环境中重新运行 `python -m pip install -e .`。通过 `pipx` 安装的应用应使用 `pipx` 更新，以确保依赖仍安装在应用自己的环境中。

## 终端输出

Rich 负责显示规则摘要、订阅预览和反馈消息，InquirerPy 负责菜单和文本输入。发布标题中的方括号会原样显示；较长的标题、URL 和路径会按终端宽度自动换行。

交互式终端会在网络请求期间显示加载指示器，并在提示输入前或请求失败后停止。输出被重定向时，会改用静态状态消息，订阅预览仍保留纯文本布局。

在 PowerShell 中禁用 Rich 颜色：

```powershell
$env:NO_COLOR = "1"
mikancli
```

使用 `Remove-Item Env:NO_COLOR` 移除此设置。粗体、暗色样式和加载动画可能仍会显示；菜单样式由 InquirerPy 单独管理。

`--json` 草稿模式只输出一个 JSON 文档，不使用 Rich 格式，也不显示进度消息。

显式非交互式命令同样只向标准输出写入 JSON；错误响应也采用带版本号的 `schema_version`、`ok`、`data` 和 `error` 结构。唯一例外是面向用户的 `--help` 帮助文本。没有交互式终端时，请改用这些命令或旧版 `--json` 模式；引导式流程会立即报错，不会等待输入。

## 引导式流程

不带参数运行 `mikancli` 时，首先会看到菜单，可选择：

- 搜索动画
- 修改 qBittorrent 配置
- 切换语言
- 退出 MikanCli

搜索流程依次为：

1. 输入动画标题或关键词
2. 在 Mikan 上搜索匹配的 Bangumi 条目
3. 选择正确的 Bangumi 条目
4. 从所选 Bangumi 页面获取字幕组 RSS 订阅
5. 选择字幕组
6. 预览最近的 RSS 订阅条目
7. 设置包含、排除和最低集数过滤条件
8. 选择下载保存位置
9. 生成规则草稿
10. 将订阅和规则提交到 qBittorrent
11. 通过 qBittorrent WebUI API 验证订阅和规则已保存

在需要输入文本的交互提示中，可输入 `exit` 或 `quit` 退出；菜单中也会提供退出选项。

## qBittorrent 设置

在 MikanCli 提交订阅或规则之前，需要先启用 qBittorrent WebUI：

1. 打开 qBittorrent 设置
2. 启用 WebUI 或远程控制
3. 确认 WebUI 地址、用户名和密码。地址为空通常表示 `http://localhost:[port]`
4. 运行 `mikancli --setup-qbittorrent`

设置说明：

- URL 直接按 Enter 将使用 `http://localhost:8080`
- 输入 `localhost:8080` 会自动规范化为 `http://localhost:8080`
- 如果 qBittorrent WebUI 允许 localhost 免认证访问，用户名和密码可以留空
- 如果 qBittorrent 拒绝连接，请重新检查 qBittorrent 设置中的 WebUI 端口和凭据

## 配置

MikanCli 将配置保存在 JSON 文件中：

- Windows：`%APPDATA%\MikanCli\config.json`

可通过 `--config PATH` 或 `MIKANCLI_CONFIG` 指定其他配置文件。非交互式命令还支持用 `MIKANCLI_QBITTORRENT_URL`、`MIKANCLI_QBITTORRENT_USERNAME` 和 `MIKANCLI_QBITTORRENT_PASSWORD` 环境变量覆盖已保存的 qBittorrent 设置。

保存的设置可包括：

- 默认下载文件夹
- 语言偏好
- qBittorrent WebUI URL
- qBittorrent 用户名和密码
- qBittorrent 分类
- qBittorrent 是否以暂停状态添加匹配的种子

qBittorrent 密码会保存在配置文件中，以便 MikanCli 后续运行时提交规则。在共享机器上请妥善保护该文件。

## 语言支持

MikanCli 的引导式流程支持英文和简体中文，涵盖菜单、提示、设置说明、摘要和旧版选项帮助。非交互式命令的帮助文本和机器错误消息目前使用英文；这些命令虽接受 `--language` 选项，但仅用于保持兼容。命令名、选项名、JSON 字段名和错误码、Mikan 标题、字幕组名称、URL 以及 qBittorrent API 数据均保持固定，不随语言变化。

语言选择优先级如下：

1. `--language en` 或 `--language zh-CN`
2. `MIKANCLI_LANG=en` 或 `MIKANCLI_LANG=zh-CN`
3. 已保存的配置值
4. 默认回退到英文

交互式用户可随时从启动菜单切换语言。所选语言会保存到配置文件，供后续运行使用。

## 项目结构

```text
mikancli/
  cli/             CLI 入口、非交互式命令、提示和引导式流程
  core/            数据类、规范化和规则生成逻辑
  integrations/    Mikan 和 qBittorrent 适配器
  services/        规则计划、经验证的提交以及已保存规则查询
  config.py        用户配置和文件夹选择辅助函数
  display.py       Rich 摘要、订阅预览、反馈和加载指示器
```

控制台命令在 `pyproject.toml` 中声明：

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

## 命令用法

[Agent 使用指南](docs/agents.zh-CN.md) 列出了所有非交互式命令。运行 `mikancli COMMAND --help` 或 `mikancli rules ACTION --help` 可查看对应选项。引导式流程和旧版草稿预览接受以下选项：

```text
usage: mikancli [-h] [--include INCLUDE] [--exclude EXCLUDE]
                [--min-episode MIN_EPISODE] [--save-path SAVE_PATH] [--json]
                [--setup-qbittorrent] [--language {en,zh-CN}] [--version]
                [--config CONFIG] [--timeout TIMEOUT] [--non-interactive]
                [keyword]
```

选项：

- `keyword`：动画标题或搜索短语
- `--include VALUE`：要求已接受的发布标题中包含某个词或短语。可重复传入多个值
- `--exclude VALUE`：拒绝标题中包含某个词或短语的发布。可重复传入多个值
- `--min-episode NUMBER`：只接受达到此集数或更高集数的动画发布标题
- `--save-path PATH`：为生成的 qBittorrent 规则使用该基础下载文件夹
- `--json`：以 JSON 形式输出规则草稿。此模式不会提交到 qBittorrent
- `--setup-qbittorrent`：配置并验证 qBittorrent WebUI 设置
- `--language {en,zh-CN}`：为本次运行选择 CLI 语言
- `--version`：输出已安装的 CLI 版本
- `--config PATH`：指定配置文件，替代默认用户配置
- `--timeout SECONDS`：设置旧版 JSON 查询的超时时间，须大于 0 且不超过 300 秒
- `--non-interactive`：如果本次调用需要交互输入，则立即报错

旧版 `mikancli KEYWORD --json` 要求恰好匹配一个动画条目和一个字幕组。结果不唯一或查询失败时，会返回 JSON 错误和非零退出码。请改用显式命令查看候选项并选定 ID。命令名在第一个位置参数处为保留名称；若要将 `search` 等命令名用作旧版搜索关键词，请使用 `mikancli --json -- search`。

## 最低集数过滤

当 RSS 条目标题采用常见动画格式，在集数前使用短横线或用方括号标注集数时，可以使用 `--min-episode`：

```text
[SubsPlease] One Piece - 1126 (1080p)
[Skymoon-Raws][One Piece][1126][ViuTV][WEB-RIP][CHT][SRT][1080p][MKV]
```

例如：

```bash
mikancli "one piece" --include SubsPlease --min-episode 1126
```

MikanCli 会将最低集数转换为 qBittorrent 规则 `mustContain` 字段中的正则表达式，并启用 `useRegex`。普通的 `--include` 和 `--exclude` 值仍按字面词或短语处理；只有标题中包含所有 include 值，qBittorrent 才会视为匹配。

通过引导式流程提交最低集数规则时，MikanCli 会检查 qBittorrent 的 RSS 条目保留上限。如果 qBittorrent 每个订阅保留的条目少于 500 条，MikanCli 会询问是否调高该设置，以便 qBittorrent 能看到足够多的 Mikan 订阅条目来匹配较新的集数。非交互式 `rules apply` 不会修改全局 RSS 偏好设置。

## 发布

仓库包含 GitHub Actions 工作流 `.github/workflows/publish.yml`。当 `main` 分支中 `pyproject.toml` 的包版本发生变化时，该工作流会发布到 PyPI。