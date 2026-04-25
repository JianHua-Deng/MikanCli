# MikanCli

MikanCli is a Python CLI for turning an anime search keyword into a qBittorrent RSS feed and download-rule setup workflow.

## Current increment

The repository currently contains the first small slice of the project:

- a Python CLI scaffold
- keyword normalization
- Mikan Bangumi search, subgroup discovery, and subgroup RSS feed resolution
- draft qBittorrent rule construction and interactive qBittorrent submission
- focused tests for the pure logic

This increment now searches Mikan, lets you select the Bangumi and subgroup,
resolves the subgroup-specific RSS feed, and prints that feed alongside the
draft rule details. In interactive search mode, MikanCli can now submit the
RSS feed and auto-download rule to qBittorrent after you confirm the draft.
After submission, it reads qBittorrent back to verify that the feed and rule
were created. qBittorrent WebUI setup verification is also available.

Internally, the project is now split more cleanly by responsibility:

- `mikancli/cli/` contains CLI entrypoint, prompts, and interactive navigation
- `mikancli/core/` contains models, normalization helpers, and rule-building logic
- `mikancli/integrations/` contains external service adapters such as Mikan
- `config.py`, `display.py`, and `bootstrap.py` stay at the package root as shared support modules

## Usage

```bash
python -m mikancli "solo leveling" --include HEVC --exclude 720p
```

You can also run it with no extra arguments and let the script guide you:

```bash
python -m mikancli
```

To set up qBittorrent WebUI access for future increments:

```bash
python -m mikancli --setup-qbittorrent
```

When you run `python -m mikancli` with no extra arguments, the first menu now lets you choose between:

- `Search anime`
- `Modify qBittorrent configurations`

If you choose `Search anime` and qBittorrent is not configured yet, MikanCli can still guide you into qBittorrent setup before continuing.

On first run, MikanCli will automatically install any missing project dependencies before continuing.

If `--save-path` is omitted, MikanCli first checks for a local default in `.mikancli.json`.
In a normal interactive run, the guided prompts now use `InquirerPy`, so list selections stay in place instead of printing a new block of text on every key press.
Every interactive menu now includes an `Exit MikanCli` option, and text prompts accept `exit` or `quit` to stop the tool cleanly.
The first search prompt now says that explicitly, so the quit path is visible before any lookup starts.

- use the saved default folder
- use the system Downloads folder
- browse for a folder
- type a folder path manually

If the chosen folder is not already the saved default, MikanCli asks whether it should be saved for future runs.

Current guided flow:

- ask for anime keyword if you did not type one
- search Mikan for matching Bangumi entries
- let you choose the correct Mikan entry when more than one match is found
- fetch subgroup entries from the selected Bangumi page
- let you choose the correct subgroup RSS feed when more than one subgroup is found
- show the subgroup RSS contents before confirmation
- let you confirm, go back to subgroup selection, or search again
- optionally ask for include words
- optionally ask for exclude words
- let you choose the base download folder from a menu
- ask for the content folder name inside that base folder, defaulting to the selected Bangumi title
- allow quitting cleanly from any interactive menu or prompt
- print the resolved Mikan page URL, subgroup, and subgroup RSS feed URL with the draft rule summary
- ask whether to submit the RSS feed and download rule to qBittorrent when WebUI access is configured
- verify submitted qBittorrent feeds and rules by reading them back from the WebUI API

## qBittorrent setup

Before MikanCli can talk to qBittorrent, do a one-time setup inside qBittorrent:

1. Open qBittorrent settings.
2. Enable WebUI / remote control.
3. Check the WebUI address, username, and password there.

Then run:

```bash
python -m mikancli --setup-qbittorrent
```

Setup notes:

- if you press Enter for the URL, MikanCli uses `http://localhost:8080`
- you can enter `localhost:8080` and MikanCli will normalize it automatically
- username and password may be left blank for the first test if your local qBittorrent allows it

Troubleshooting:

- if MikanCli says it could not reach qBittorrent, WebUI may be disabled or using a different port
- if MikanCli says the credentials were rejected, re-check the WebUI username/password in qBittorrent settings

## Packaging note

Planned improvement:

- make `mikancli` accessible from any terminal location so users do not need to `cd` into the project folder first
- likely support a normal installed CLI workflow where the user can open a terminal and run `mikancli` directly
- later consider a more user-friendly distribution path such as `pipx`, PyPI packaging, or a Windows executable for non-technical users
