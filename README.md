# MikanCli

语言：[简体中文](README.md) | [English](README.en.md)

MikanCli 是一个 Python 命令行工具，可以在 Mikanani.me 上搜索番剧/动画，选定对应的 Bangumi 条目和字幕组 RSS 订阅，并据此生成 qBittorrent 的 RSS 下载规则。

它既提供引导式交互流程，也支持用于脚本或检查的 JSON 预览模式。目前交互式流程是功能最完整的模式。

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

- Windows：`%APPDATA%\Roaming\MikanCli\config.json`

保存的设置可包括：

- 默认下载文件夹
- 语言偏好
- qBittorrent WebUI URL
- qBittorrent 用户名和密码
- qBittorrent 分类
- qBittorrent 是否以暂停状态添加匹配的种子

qBittorrent 密码会保存在配置文件中，以便 MikanCli 后续运行时提交规则。在共享机器上请妥善保护该文件。

## 语言支持

MikanCli 的面向用户 CLI 文本支持英文和简体中文，包括交互菜单、提示、设置说明、摘要和帮助文本。命令名、选项名、JSON 字段名、Mikan 标题、字幕组名称、URL 和 qBittorrent API 数据保持固定，不随语言变化。

语言选择优先级如下：

1. `--language en` 或 `--language zh-CN`
2. `MIKANCLI_LANG=en` 或 `MIKANCLI_LANG=zh-CN`
3. 已保存的配置值
4. 默认回退到英文

交互式用户可随时从启动菜单切换语言。所选语言会保存到配置文件，供后续运行使用。

## 项目结构

```text
mikancli/
  cli/             CLI 入口、提示和交互流程
  core/            数据类、规范化和规则生成逻辑
  integrations/    Mikan 和 qBittorrent 适配器
  config.py        用户配置和文件夹选择辅助函数
  display.py       Rich 摘要、订阅预览、反馈和加载指示器
```

控制台命令在 `pyproject.toml` 中声明：

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

## 命令用法

```text
usage: mikancli [-h] [--include INCLUDE] [--exclude EXCLUDE]
                [--min-episode MIN_EPISODE] [--save-path SAVE_PATH] [--json]
                [--setup-qbittorrent] [--language {en,zh-CN}] [--version]
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

提交最低集数规则时，MikanCli 会检查 qBittorrent 的 RSS 条目保留上限。如果 qBittorrent 每个订阅保留的条目少于 500 条，MikanCli 会询问是否调高该设置，以便 qBittorrent 能看到足够多的 Mikan 订阅条目来匹配较新的集数。

## 发布

仓库包含 GitHub Actions 工作流 `.github/workflows/publish.yml`。当 `main` 分支中 `pyproject.toml` 的包版本发生变化时，该工作流会发布到 PyPI。