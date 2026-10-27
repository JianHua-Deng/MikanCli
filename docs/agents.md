# Agent and script usage

Language: [简体中文](agents.zh-CN.md) | [English](agents.md)

Use these commands for automation. They never prompt and return one JSON response on stdout; `--help` returns plain help text.

## Workflow

```sh
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

Replace the example IDs with discovery results. Check the exit status and `ok` at each step, and review the plan before applying it.

Only `rules apply` writes to qBittorrent. It creates missing feeds, saves and verifies the rule, and can trigger downloads. Identical rules return `unchanged`; different rules with the same name fail unless `--if-exists replace` is specified. Global RSS preferences are not changed.

Apply accepts a UTF-8 file or stdin (`--file -`), containing either the successful plan response or its raw `data` object. It uses the saved plan values.

## Commands and options

| Command | Purpose |
| --- | --- |
| `search KEYWORD` | List anime candidates; no matches returns an empty result. |
| `subgroups --bangumi-id ID` | List subgroup feeds for an anime. |
| `feed --bangumi-id ID --subgroup-id ID` | Preview releases in the selected feed. |
| `rules plan --bangumi-id ID --subgroup-id ID --name NAME` | Build a plan without submitting it. |
| `rules apply --file PATH` | Apply and verify a saved plan. |
| `rules get --name NAME` | Read a saved rule and check its feeds. |
| `config show` | Show effective configuration with credentials redacted. |
| `schema` | Export JSON Schemas for responses and plans. |

`search` and `feed` accept `--limit N` (positive; default 20) and `--offset N` (nonnegative; default 0).

Optional `rules plan` arguments:

| Option | Meaning |
| --- | --- |
| `--include VALUE` | Required literal term; repeat to require all terms. |
| `--exclude VALUE` | Rejected literal term; repeat to reject any matching term. |
| `--min-episode N` | Minimum anime episode number. |
| `--save-path PATH` | Exact destination; no title subfolder is added. |
| `--category NAME` | qBittorrent category. |
| `--add-paused` / `--no-add-paused` | Set whether matched torrents are added paused. |
| `--feed-path PATH` | Location for a new feed; existing feeds with the same URL are reused. |

Omitted path, category, and paused options use config defaults. `--save-path ""` selects qBittorrent's default destination.

Common options can appear before or after a command: `--config PATH`, `--timeout SECONDS` (default 15; greater than 0 and at most 300, per network request), `--json`, `--non-interactive`, and `--language en` / `--language zh-CN`. JSON and noninteractive behavior are already enabled. Command help and error messages are currently in English.

## Responses and errors

```json
{"schema_version":1,"ok":true,"data":{},"error":null}
```

On failure, `ok` is `false`, `data` is `null`, and `error` contains `code`, `message`, `retryable`, and `details`. Use error codes and exit status to decide what to do next. Diagnostics go to stderr.

Plan data contains `plan_version: 1`, `rule_name`, `feed_url`, `feed_path`, and `rule_definition`. Run `mikancli schema` for the full schemas.

Paginated search and feed data contain `items`, `total`, `offset`, and `limit`.

| Exit status | Meaning / action |
| --- | --- |
| `0` | Success, including empty results and unchanged rules. |
| `1` | Upstream or network failure; check `retryable`. |
| `2` | Invalid arguments, config, or plan; fix the input. |
| `3` | Resource missing or qBittorrent not configured. |
| `4` | Conflict or ambiguity; inspect the existing rule or choose explicit IDs. |
| `5` | Partial success or unknown write outcome; inspect the rule and feeds before retrying. |
| `130` | Cancelled. |

## Configuration

Config selection: `--config PATH` → `MIKANCLI_CONFIG` → default user config. These environment variables override saved qBittorrent settings:

- `MIKANCLI_QBITTORRENT_URL`
- `MIKANCLI_QBITTORRENT_USERNAME`
- `MIKANCLI_QBITTORRENT_PASSWORD`

The WebUI URL must use HTTP(S) without embedded credentials, query parameters, or fragments. Supply credentials in the separate username and password settings.

## Legacy usage

`mikancli` alone opens the guided menu. Legacy `mikancli KEYWORD --json` uses a different success format and requires a unique anime and subgroup; ambiguous matches return `AMBIGUOUS_SELECTION` with exit status 4.

Command names are reserved as the first positional argument. For a legacy keyword matching a command name, use `mikancli --json -- search`.
