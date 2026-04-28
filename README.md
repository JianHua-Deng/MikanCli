# MikanCli

MikanCli is a Python CLI for finding Bangumi/Anime from Mikan and automating the set up flow of qbitorrent's download rules 

## Requirements
- Have `Qbitorrent` installed on your machine
- Have `pipx` and `pip` installed

## Internal Responsibility

Internally, the project is split by directories via the following responsibility:

- `mikancli/cli/` contains CLI entrypoint, prompts, and interactive navigation
- `mikancli/core/` contains models/data classes, normalization helpers, and rule-building logic
- `mikancli/integrations/` contains external service adapters such as Mikan
- `config.py` and `display.py` stay at the package root as shared support modules

## Install

For normal use after MikanCli is published, install it as a CLI app with `pipx`:

```bash
python -m pip install --user pipx               # For installing pipx for the current specific user of this machine
python -m pipx ensurepath                       # Updates machine's PATH variable to include the folder where pipx places executable files
```

Then install the CLI:
```bash
python -m pipx install mikancli
```

Then you are good to go, open a new terminal and run MikanCli to use it:

```bash
mikancli
```

## Install by Git Cloning the Repo

Clone the repository, then install it from the project folder:

```bash
git clone <repo-url>
cd MikanCli
python -m pip install --user pipx
python -m pipx ensurepath
python -m pipx install -e .
```

This installs MikanCli in editable mode, installs the dependencies declared in
`pyproject.toml`, and registers the `mikancli` command. After that, open a new
terminal and run MikanCli from any location:

```bash
mikancli
```

For development, a direct editable pip install also works:

```bash
python -m pip install -e .
```

You can also run the module directly from the project folder after installing
the local environment:

```bash
python -m mikancli
```

Dependencies are installed by `pip` when the package is installed. MikanCli does
not install packages at runtime.

## Usage

Search directly from the command line:

```bash
mikancli "solo leveling" --include HEVC --exclude 720p
```

You can also run it with no extra arguments and let the script guide you:

```bash
mikancli
```

To set up qBittorrent WebUI access for future increments:

```bash
mikancli --setup-qbittorrent
```

When you run `mikancli` with no extra arguments, the first menu now lets you choose between:

- `Search anime`
- `Modify qBittorrent configurations`

If you choose `Search anime` and qBittorrent is not configured yet, MikanCli can still guide you into qBittorrent setup before continuing.

If `--save-path` is omitted, MikanCli first checks for a saved default in the
user config file. On Windows, the default config location is
`%APPDATA%\MikanCli\config.json`.
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
mikancli --setup-qbittorrent
```

Setup notes:

- if you press Enter for the URL, MikanCli uses `http://localhost:8080`
- you can enter `localhost:8080` and MikanCli will normalize it automatically
- username and password may be left blank for the first test if your local qBittorrent allows it

Troubleshooting:

- if MikanCli says it could not reach qBittorrent, WebUI may be disabled or using a different port
- if MikanCli says the credentials were rejected, re-check the WebUI username/password in qBittorrent settings

## Packaging and release

MikanCli is structured as an installable Python CLI package. The console command
is declared in `pyproject.toml`:

```toml
[project.scripts]
mikancli = "mikancli.cli.entrypoint:main"
```

Current local install flow:

```bash
python -m pipx install -e .
mikancli
```

Planned public install flow after publishing to PyPI:

```bash
python -m pip install mikancli
mikancli
```

Recommended CLI-app install flow after publishing:

```bash
python -m pipx install mikancli
mikancli
```

Remaining packaging work:

- add a release workflow for building and publishing distributions
- later consider a Windows executable for non-technical users
