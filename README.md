# AutoFeedSync

AutoFeedSync is a Python CLI for turning an anime search keyword into a qBittorrent RSS feed and download-rule setup workflow.

## Current increment

The repository currently contains the first small slice of the project:

- a Python CLI scaffold
- keyword normalization
- Mikan Bangumi search, subgroup discovery, and subgroup RSS feed resolution
- draft qBittorrent rule construction
- focused tests for the pure logic

This increment now searches Mikan, lets you select the Bangumi and subgroup,
resolves the subgroup-specific RSS feed, and prints that feed alongside the
draft rule details. qBittorrent submission is still not implemented.

Internally, the project is now split more cleanly by responsibility:

- `cli.py` keeps the entrypoint and CLI assembly
- `interactive.py` handles Bangumi/subgroup navigation
- `display.py` handles text rendering
- `input_helpers.py` handles reusable text and word-list input parsing

## Usage

```bash
python -m autofeedsync "solo leveling" --include HEVC --exclude 720p
```

You can also run it with no extra arguments and let the script guide you:

```bash
python -m autofeedsync
```

On first run, AutoFeedSync will automatically install any missing project dependencies before continuing.

If `--save-path` is omitted, AutoFeedSync first checks for a local default in `.autofeedsync.json`.
In a normal interactive run, the guided prompts now use `InquirerPy`, so list selections stay in place instead of printing a new block of text on every key press.

- use the saved default folder
- use the system Downloads folder
- browse for a folder
- type a folder path manually

If the chosen folder is not already the saved default, AutoFeedSync asks whether it should be saved for future runs.

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
- let you choose the download folder from a menu
- print the resolved Mikan page URL, subgroup, and subgroup RSS feed URL with the draft rule summary
