# MikanCli

Language: [简体中文](README.md) | [English](README.en.md)

MikanCli is a Python command-line tool for finding bangumi/anime on Mikanani.me, choosing the correct Bangumi and subgroup RSS feed, and turning that selection into a qBittorrent RSS download rule.

It supports a guided interactive flow and noninteractive JSON commands for agents and scripts, including discovery, saved rule plans, and verified application to qBittorrent.

## Features

- Search Mikan by anime title or keyword
- Choose from matching Bangumi results and subgroup-specific RSS feeds
- Preview recent RSS feed items with pagination before confirming a feed
- Read Rich-formatted rule summaries, feed previews, and status messages, with loading indicators for network requests
- Build qBittorrent RSS rules with include and exclude filters
- Filter anime-style episode numbers at or above a minimum episode
- Choose and save a default download folder
- Configure qBittorrent WebUI access from the CLI
- Submit RSS feeds and auto-download rules to qBittorrent, then verify that qBittorrent saved them
- Print rule drafts as JSON without submitting anything
- Use explicit IDs, versioned JSON responses, and idempotent saved plans in agent workflows

## Screenshots

![Search input (demo data)](docs/images/search-input.en.png)

![RSS feed preview (demo data)](docs/images/feed-preview.en.png)

## Requirements

- Python 3.10 or newer
- `pipx` for installing MikanCli as a standalone CLI app
- qBittorrent, if you want MikanCli to submit RSS feeds and rules automatically

## Quick Start | Install

I recommend installing MikanCli with `pipx` so you can use it as a CLI app from any terminal.
You can skip the following if you already have `pipx` installed:

```bash
python -m pip install --user pipx           # Install pipx for the current user
python -m pipx ensurepath                   # Add the pipx executable folder to PATH
```

Refresh by reopening a new terminal after running `pipx ensurepath`, then run:

```bash
pipx install mikancli
```

## How to Use

Now that it is installed, run the following and follow the menu:

```bash
mikancli
```

## Agents and Scripts

Use explicit commands to search candidates, choose IDs, preview releases, and save a rule plan before applying it. These commands never prompt and always return JSON. Reapplying the same plan reports it as unchanged.

```bash
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

Replace the example IDs with discovery results and review the plan before applying it. Among these noninteractive commands, only `rules apply` writes to qBittorrent and can trigger RSS downloads. Use `config show` to inspect redacted configuration and `schema` to export the response and plan JSON Schemas.

These commands accept `--config PATH`, `--timeout SECONDS`, and optional `--json` / `--non-interactive` flags. See the agent usage guide in [English](docs/agents.md) or [简体中文](docs/agents.zh-CN.md) for the full command reference, response schema, exit codes, and credential environment variables.

## Install by Cloning the Repo

To install from a local clone:

```bash
git clone https://github.com/JianHua-Deng/MikanCli.git
cd MikanCli
python -m pipx install -e .
```

For development, an editable `pip` install also works:

```bash
python -m pip install -e .
python -m mikancli
```

Dependencies, including Rich for output and InquirerPy for prompts, are declared in `pyproject.toml` and installed by `pip` or `pipx`. MikanCli does not install packages at runtime.

After pulling dependency changes into an existing editable `pip` installation, rerun `python -m pip install -e .` in that environment. Update `pipx` installations through `pipx` so dependencies stay in the app's environment.

## Terminal Output

Rich formats rule summaries, feed previews, and feedback. InquirerPy handles menus and text input. Release titles containing brackets are displayed literally, and long titles, URLs, and paths wrap to fit the terminal.

Interactive terminals show loading indicators during network requests. Indicators stop before prompts and after failures. Redirected output uses static status messages, and feed previews retain their plain-text layout.

To disable Rich colors in PowerShell:

```powershell
$env:NO_COLOR = "1"
mikancli
```

Remove that setting with `Remove-Item Env:NO_COLOR`. Bold or dim text and loading animations may remain; InquirerPy manages menu styling separately.

The `--json` draft mode prints one JSON document without Rich formatting or progress messages.

The explicit noninteractive commands also use JSON-only stdout, including errors, with a versioned `schema_version`, `ok`, `data`, and `error` envelope. Human-readable `--help` is an exception. Without an interactive terminal, use one of these commands or the legacy `--json` mode; the guided flow fails immediately instead of prompting.

## Guided Flow

When you run `mikancli` without arguments, the first menu lets you:

- search anime
- modify qBittorrent configuration
- change language
- exit MikanCli

The search flow then:

1. asks for an anime title or keyword
2. searches Mikan for matching Bangumi entries
3. lets you choose the correct Bangumi entry
4. fetches subgroup RSS feeds from the selected Bangumi page
5. lets you choose a subgroup
6. previews recent RSS feed items
7. asks for include, exclude, and minimum episode filters
8. asks where downloads should be saved
9. builds a rule draft
10. submits the feed and rule to qBittorrent
11. verifies the submitted feed and rule through the qBittorrent WebUI API

Interactive prompts accept `exit` or `quit` where text input is requested, and menus include an exit option.

## qBittorrent Setup

Before MikanCli can submit feeds or rules, enable qBittorrent WebUI:

1. Open qBittorrent settings
2. Enable WebUI or remote control
3. Confirm the WebUI address, username, and password. If the address is empty, it usually means it is `http://localhost:[port]`
4. Run `mikancli --setup-qbittorrent`

Setup notes:

- Pressing Enter for the URL uses `http://localhost:8080`
- Entering `localhost:8080` is normalized to `http://localhost:8080`
- Username and password can be left blank if your qBittorrent WebUI allows localhost access without authentication
- If qBittorrent rejects the connection, re-check the WebUI port and credentials in qBittorrent settings

## Configuration

MikanCli stores configuration in a JSON file:

- Windows: `%APPDATA%\MikanCli\config.json`

Use `--config PATH` or `MIKANCLI_CONFIG` to select a different file. Noninteractive commands also accept `MIKANCLI_QBITTORRENT_URL`, `MIKANCLI_QBITTORRENT_USERNAME`, and `MIKANCLI_QBITTORRENT_PASSWORD` as overrides for saved qBittorrent settings.

Saved settings can include:

- default download folder
- language preference
- qBittorrent WebUI URL
- qBittorrent username and password
- qBittorrent category
- whether qBittorrent should add matched torrents paused

The qBittorrent password is stored in the config file so MikanCli can submit rules in later runs. Keep that file private on shared machines.

## Language Support

MikanCli supports English and Simplified Chinese for the guided flow, including menus, prompts, setup instructions, summaries, and legacy option help. Noninteractive command help and machine error messages are currently in English; `--language` is accepted for compatibility. Command names, option names, JSON field names and error codes, Mikan titles, subgroup names, URLs, and qBittorrent API payloads stay stable.

Language selection uses this precedence order:

1. `--language en` or `--language zh-CN`
2. `MIKANCLI_LANG=en` or `MIKANCLI_LANG=zh-CN`
3. saved config value
4. English fallback

Interactive users can always change language from the startup menu. The selected language is saved to the config file for future runs.

## Project Structure

```text
mikancli/
  cli/             entrypoint, noninteractive commands, prompts, and guided flows
  core/            dataclasses, normalization, and rule-building logic
  integrations/    Mikan and qBittorrent adapters
  services/        rule plans, validated application, and saved-rule inspection
  config.py        user config and folder selection helpers
  display.py       Rich summaries, feed previews, feedback, and loading indicators
```

The console command is declared in `pyproject.toml`:

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

## Commands Usage

The [agent guide](docs/agents.md) lists all noninteractive commands. Run `mikancli COMMAND --help` or `mikancli rules ACTION --help` for their options. The guided flow and legacy draft preview accept these options:

```text
usage: mikancli [-h] [--include INCLUDE] [--exclude EXCLUDE]
                [--min-episode MIN_EPISODE] [--save-path SAVE_PATH] [--json]
                [--setup-qbittorrent] [--language {en,zh-CN}] [--version]
                [--config CONFIG] [--timeout TIMEOUT] [--non-interactive]
                [keyword]
```

Options:

- `keyword`: anime title or search phrase
- `--include VALUE`: require a word or phrase in accepted release titles. Repeat for multiple values
- `--exclude VALUE`: reject release titles containing a word or phrase. Repeat for multiple values
- `--min-episode NUMBER`: only accept anime-style release titles at or above this episode number
- `--save-path PATH`: use this base download folder for the generated qBittorrent rule
- `--json`: print the rule draft as JSON. This mode does not submit to qBittorrent
- `--setup-qbittorrent`: configure and verify qBittorrent WebUI settings
- `--language {en,zh-CN}`: choose CLI language for this run
- `--version`: print the installed CLI version
- `--config PATH`: select a config file instead of the default user config
- `--timeout SECONDS`: set the legacy JSON lookup timeout, greater than 0 and at most 300 seconds
- `--non-interactive`: fail if this invocation would require a prompt

Legacy `mikancli KEYWORD --json` requires exactly one matching anime and subgroup. Ambiguity and lookup failures return a JSON error and nonzero exit status. Use the explicit commands to inspect candidates and choose IDs. Command names are reserved as the first positional argument; for a legacy keyword such as `search`, use `mikancli --json -- search`.

## Minimum Episode Filtering

Use `--min-episode` when RSS item titles use common anime formats with a dash before the episode number or a bracketed episode number:

```text
[SubsPlease] One Piece - 1126 (1080p)
[Skymoon-Raws][One Piece][1126][ViuTV][WEB-RIP][CHT][SRT][1080p][MKV]
```

For example:

```bash
mikancli "one piece" --include SubsPlease --min-episode 1126
```

MikanCli converts the minimum episode into a qBittorrent regular expression in the rule's `mustContain` field and enables `useRegex`. Normal `--include` and `--exclude` values still behave as literal words or phrases, and every include value must also be present in a title before qBittorrent treats it as a match.

When submitting a minimum-episode rule through the guided flow, MikanCli checks qBittorrent's RSS article retention limit. If qBittorrent is keeping fewer than 500 articles per feed, MikanCli offers to increase that setting so qBittorrent can see enough of Mikan's feed to match newer episodes. Noninteractive `rules apply` does not change global RSS preferences.

## Release

The repository includes a GitHub Actions workflow at `.github/workflows/publish.yml` that publishes to PyPI from `main` when the package version in `pyproject.toml` changes.
