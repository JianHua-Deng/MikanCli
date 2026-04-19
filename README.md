# AutoFeedSync

AutoFeedSync is a Python CLI for turning an anime search keyword into a qBittorrent RSS feed and download-rule setup workflow.

## Current increment

The repository currently contains the first small slice of the project:

- a Python CLI scaffold
- keyword normalization
- draft qBittorrent rule construction
- focused tests for the pure logic

This increment does not yet query Mikan or send data to qBittorrent.

## Usage

```bash
python -m autofeedsync "solo leveling" --group SubsPlease --resolution 1080p --include HEVC --exclude 720p
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
- optionally ask for release group
- let you choose a resolution preference from a menu
- optionally ask for include words
- optionally ask for exclude words
- let you choose the download folder from a menu
