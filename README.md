# MikanCli

MikanCli is a Python command-line tool for finding bangumi/anime on Mikan, choosing the correct Bangumi and subgroup RSS feed, and turning that selection into a qBittorrent RSS auto-download rule

It supports both a guided interactive flow and a JSON preview mode for scripting or inspection. Though, only the interactive flow is pretty much finished as of now

## Features

- Search Mikan by anime title or keyword
- Choose from matching Bangumi results and subgroup-specific RSS feeds
- Preview recent RSS feed items before confirming a feed
- Build qBittorrent RSS rules with include and exclude filters
- Choose and save a default download folder
- Configure qBittorrent WebUI access from the CLI
- Submit RSS feeds and auto-download rules to qBittorrent, then verify that qBittorrent saved them
- Print rule drafts as JSON without submitting anything

## Requirements

- Python 3.10 or newer.
- qBittorrent, if you want MikanCli to submit RSS feeds and rules automatically
- qBittorrent WebUI enabled for automatic submission
- `pipx` for installing MikanCli as a standalone CLI app

## Quick Start | Install

I recommend installing it with `pipx`, such so you can use it as a CLI app anytime anywhere from the terminal
You can skip the following if you already have `pipx` installed:

```bash
python -m pip install --user pipx           # Installing pipx for the current user on this machine
python -m pipx ensurepath                   # Update machine's PATH variable to include the folder where pipx places executable files
```

Refresh by reopening a new terminal after `pipx ensurepath`, then run:

```bash
pipx install mikancli
```

## How to use

Now that it is installed, run the following and follow the menu to use it:
```bash
mikancli
```

## Install by cloning the Repo

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

Dependencies are declared in `pyproject.toml` and installed by `pip` or `pipx`. MikanCli does not install packages at runtime.

## Guided Flow

When you run `mikancli` without arguments, the first menu lets you:

- search anime
- modify qBittorrent configuration
- exit MikanCli

The search flow then:

1. asks for an anime title or keyword
2. searches Mikan for matching Bangumi entries
3. lets you choose the correct Bangumi entry
4. fetches subgroup RSS feeds from the selected Bangumi page
5. lets you choose a subgroup
6. previews recent RSS feed items
7. asks for include and exclude filters
8. asks where downloads should be saved
9. builds a rule draft
10. optionally submits the feed and rule to qBittorrent
11. verifies the submitted feed and rule through the qBittorrent WebUI API

Interactive prompts accept `exit` or `quit` where text input is requested, and menus include an exit option.

## qBittorrent Setup

Before MikanCli can submit feeds or rules, enable qBittorrent WebUI:

1. Open qBittorrent settings.
2. Enable WebUI or remote control.
3. Confirm the WebUI address, username, and password. If the address is empty, it usually mean it is just `http://localhost:[port]`
4. Run `mikancli --setup-qbittorrent`.

Setup notes:

- Pressing Enter for the URL uses `http://localhost:8080`.
- Entering `localhost:8080` is normalized to `http://localhost:8080`.
- Username and password can be left blank if your qBittorrent WebUI allows localhost access without authentication.
- If qBittorrent rejects the connection, re-check the WebUI port and credentials in qBittorrent settings.

## Configuration

MikanCli stores user-level configuration in a JSON file:

- Windows: `%APPDATA%\MikanCli\config.json`
- macOS: `~/Library/Application Support/MikanCli/config.json`
- Linux and other POSIX systems: `$XDG_CONFIG_HOME/mikancli/config.json` or `~/.config/mikancli/config.json`

Saved settings can include:

- default download folder
- qBittorrent WebUI URL
- qBittorrent username and password
- qBittorrent category
- whether qBittorrent should add matched torrents paused

The qBittorrent password is stored in the config file so MikanCli can submit rules in later runs. Keep that file private on shared machines.

## Project Structure

```text
mikancli/
  cli/            CLI entrypoint, prompts, and interactive flows
  core/           dataclasses, normalization, and rule-building logic
  integrations/   Mikan and qBittorrent adapters
  config.py       user config and folder selection helpers
  display.py      text summaries and feed previews
```

The console command is declared in `pyproject.toml`:

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

## Commands Usage

```text
usage: mikancli [-h] [--include INCLUDE] [--exclude EXCLUDE]
                [--save-path SAVE_PATH] [--json] [--setup-qbittorrent]
                [--version]
                [keyword]
```

Options:

- `keyword`: anime title or search phrase.
- `--include VALUE`: require a word or phrase in accepted release titles. Repeat for multiple values.
- `--exclude VALUE`: reject release titles containing a word or phrase. Repeat for multiple values.
- `--save-path PATH`: use this base download folder for the generated qBittorrent rule.
- `--json`: print the rule draft as JSON. This mode does not submit to qBittorrent.
- `--setup-qbittorrent`: configure and verify qBittorrent WebUI settings.
- `--version`: print the installed CLI version.

## Release

The repository includes a GitHub Actions workflow at `.github/workflows/publish.yml` that builds distributions, checks them with `twine`, and publishes to PyPI when a GitHub release is published.
