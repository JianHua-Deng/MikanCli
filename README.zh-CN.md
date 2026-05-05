# MikanCli

语言：[English](README.md) | [简体中文](README.zh-CN.md)

MikanCli 是一个 Python 命令行工具，用于在 Mikanani.me 上查找番剧/动画，选择正确的 Bangumi 和字幕组 RSS 订阅，并把该选择转换成 qBittorrent RSS 下载规则。

它支持引导式交互流程，也支持用于脚本或检查的 JSON 预览模式。目前交互式流程是最完整的模式。

## 功能

- 根据动画标题或关键词搜索 Mikan
- 从匹配的 Bangumi 结果和字幕组 RSS 订阅中进行选择
- 在确认订阅前预览最近的 RSS 条目
- 使用包含和排除过滤条件生成 qBittorrent RSS 规则
- 选择并保存默认下载文件夹
- 从命令行配置 qBittorrent WebUI 访问
- 将 RSS 订阅和自动下载规则提交到 qBittorrent，并验证 qBittorrent 已保存这些内容
- 以 JSON 形式打印规则草稿，不提交任何内容

## 环境要求

- Python 3.10 或更新版本
- `pipx`，用于把 MikanCli 安装为独立命令行应用
- qBittorrent，如果你希望 MikanCli 自动提交 RSS 订阅和规则

## 快速开始 | 安装

推荐使用 `pipx` 安装 MikanCli，这样你可以在任何终端中直接使用它。
如果你已经安装了 `pipx`，可以跳过下面两条命令：

```bash
python -m pip install --user pipx           # 为当前用户安装 pipx
python -m pipx ensurepath                   # 将 pipx 可执行文件目录添加到 PATH
```

运行 `pipx ensurepath` 后，重新打开一个终端，然后执行：

```bash
pipx install mikancli
```

## 使用方法

安装完成后，运行下面的命令并按照菜单操作：

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

用于开发时，也可以使用可编辑的 `pip` 安装：

```bash
python -m pip install -e .
python -m mikancli
```

依赖项声明在 `pyproject.toml` 中，并由 `pip` 或 `pipx` 安装。MikanCli 不会在运行时安装依赖包。

## 引导式流程

不带参数运行 `mikancli` 时，第一个菜单会让你选择：

- 搜索动画
- 修改 qBittorrent 配置
- 退出 MikanCli

搜索流程会依次：

1. 询问动画标题或关键词
2. 在 Mikan 上搜索匹配的 Bangumi 条目
3. 让你选择正确的 Bangumi 条目
4. 从所选 Bangumi 页面获取字幕组 RSS 订阅
5. 让你选择字幕组
6. 预览最近的 RSS 订阅条目
7. 询问包含和排除过滤条件
8. 询问下载保存位置
9. 生成规则草稿
10. 将订阅和规则提交到 qBittorrent
11. 通过 qBittorrent WebUI API 验证提交的订阅和规则

在需要输入文本的交互式提示中，可以输入 `exit` 或 `quit` 退出；菜单中也会包含退出选项。

## qBittorrent 设置

在 MikanCli 可以提交订阅或规则之前，需要先启用 qBittorrent WebUI：

1. 打开 qBittorrent 设置
2. 启用 WebUI 或远程控制
3. 确认 WebUI 地址、用户名和密码。如果地址为空，通常表示它是 `http://localhost:[port]`
4. 运行 `mikancli --setup-qbittorrent`

设置说明：

- URL 直接按 Enter 会使用 `http://localhost:8080`
- 输入 `localhost:8080` 会自动规范化为 `http://localhost:8080`
- 如果 qBittorrent WebUI 允许 localhost 绕过认证，用户名和密码可以留空
- 如果 qBittorrent 拒绝连接，请重新检查 qBittorrent 设置里的 WebUI 端口和凭据

## 配置

MikanCli 将配置保存在 JSON 文件中：

- Windows：`%APPDATA%\Roaming\MikanCli\config.json`

保存的设置可以包括：

- 默认下载文件夹
- qBittorrent WebUI URL
- qBittorrent 用户名和密码
- qBittorrent 分类
- qBittorrent 是否应将匹配的种子以暂停状态添加

qBittorrent 密码会保存在配置文件中，这样 MikanCli 后续运行时才能提交规则。共享机器上请保护好这个文件。

## 中文支持计划

中文支持已经列入计划，但目前还没有实现。目标是让交互式命令行同时支持英文和简体中文，同时保持命令名称、JSON 字段名、Mikan 标题、字幕组名称、URL 和 qBittorrent API 数据不变。

计划实现内容：

1. 添加一个轻量的本地化层，用来管理用户可见的消息、提示文本、菜单选项、设置说明、校验错误和摘要输出。
2. 支持通过 `--language en` / `--language zh-CN` 这样的命令行选项、`MIKANCLI_LANG` 环境变量，以及交互式保存的配置值来选择语言。
3. 在交互式命令行中始终保留切换语言的入口，包括启动菜单或设置菜单里的语言切换选项，让用户随时可以更改当前语言，而不需要手动编辑配置文件。
4. 将流程模块里硬编码的英文界面文本迁移为翻译键。
5. 为搜索流程、qBittorrent 设置流程、下载文件夹流程、规则摘要和常见错误添加简体中文翻译。
6. 保持脚本输出稳定：`--json` 的字段名和结构不变，只在合适的地方本地化人类可读的说明文本。
7. 添加测试覆盖语言选择、缺失翻译回退逻辑，以及有代表性的中文提示，确保发布前能发现遗漏的翻译。

## 项目结构

```text
mikancli/
  cli/             CLI 入口、提示和交互流程
  core/            数据类、规范化和规则生成逻辑
  integrations/    Mikan 和 qBittorrent 适配器
  config.py        用户配置和文件夹选择辅助函数
  display.py       文本摘要和订阅预览
```

控制台命令在 `pyproject.toml` 中声明：

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

## 命令用法

```text
usage: mikancli [-h] [--include INCLUDE] [--exclude EXCLUDE]
                [--save-path SAVE_PATH] [--json] [--setup-qbittorrent]
                [--version]
                [keyword]
```

选项：

- `keyword`：动画标题或搜索短语
- `--include VALUE`：要求已接受的发布标题中包含某个词或短语。可重复传入多个值
- `--exclude VALUE`：拒绝标题中包含某个词或短语的发布。可重复传入多个值
- `--save-path PATH`：为生成的 qBittorrent 规则使用这个基础下载文件夹
- `--json`：以 JSON 形式打印规则草稿。此模式不会提交到 qBittorrent
- `--setup-qbittorrent`：配置并验证 qBittorrent WebUI 设置
- `--version`：打印已安装的 CLI 版本

## 发布

仓库包含 GitHub Actions 工作流 `.github/workflows/publish.yml`。当 GitHub Release 发布时，该工作流会构建发行包，使用 `twine` 检查，并发布到 PyPI。
