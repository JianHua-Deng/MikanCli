# Agent and script usage

Language: [简体中文](agents.zh-CN.md) | [English](agents.md)

Use the explicit commands below for automation. They never prompt and always emit one JSON response on stdout, even without `--json`. Choose a Bangumi and subgroup from the discovery results, then save, inspect, and apply a rule plan.

## Discover, plan, apply, verify

Replace `123` and `456` with IDs returned by discovery. The plan is a local JSON file; only `rules apply` changes qBittorrent.

```sh
mikancli search "One Piece"
mikancli subgroups --bangumi-id 123
mikancli feed --bangumi-id 123 --subgroup-id 456 --limit 20 --offset 0
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p > plan.json
mikancli rules apply --file plan.json --if-exists fail
mikancli rules get --name "One Piece"
```

Check each command's exit status and `ok` before continuing. Inspect `plan.json` before applying it. Applying creates the feed if needed and saves the RSS rule, which can trigger downloads according to qBittorrent's RSS settings. It does not change global RSS preferences.

For pipeline input, `rules apply --file -` reads JSON from stdin. Apply accepts either the successful response saved by `rules plan` or its raw `data` object. Shell redirection must produce a UTF-8 JSON file.

## Command reference

| Command | Purpose |
| --- | --- |
| `search KEYWORD` | List matching Bangumi candidates. No matches is a successful empty result. |
| `subgroups --bangumi-id ID` | List available subgroups for a chosen Bangumi. |
| `feed --bangumi-id ID --subgroup-id ID --limit 20 --offset 0` | Preview a page of feed releases. |
| `rules plan --bangumi-id ID --subgroup-id ID --name NAME` | Create a reviewable rule plan without writing to qBittorrent. |
| `rules apply --file PATH --if-exists fail` | Apply a saved plan and verify the saved rule. Use `-` for stdin. |
| `rules get --name NAME` | Read the current qBittorrent rule. |
| `config show` | Inspect effective configuration with credentials redacted. |
| `schema` | Export JSON Schema documents for the response envelope and rule plan. |

`rules plan` supports these optional arguments:

| Option | Meaning |
| --- | --- |
| `--include VALUE` | Include filter; repeat for multiple values. |
| `--exclude VALUE` | Exclude filter; repeat for multiple values. |
| `--min-episode N` | Minimum anime episode number. |
| `--save-path PATH` | Exact download destination; no extra title subfolder is appended. |
| `--category NAME` | qBittorrent category. |
| `--add-paused` / `--no-add-paused` | Override the configured initial paused state. |
| `--feed-path PATH` | Location used when adding a missing RSS feed. An existing feed with the same URL is reused. |

When omitted, the download path, category, and paused state use configured defaults. An empty download path uses qBittorrent's default destination.

Every explicit command accepts `--json`, `--non-interactive`, `--config PATH`, `--timeout SECONDS`, and `--language en|zh-CN` before or after the command. `--json` and `--non-interactive` are optional because these commands already provide that behavior. The timeout must be greater than 0 and at most 300 seconds, and bounds each network request.

```sh
mikancli --config agent-config.json --timeout 15 search "One Piece"
mikancli search "One Piece" --config agent-config.json --timeout 15
mikancli rules plan --bangumi-id 123 --subgroup-id 456 --name "One Piece" --include 1080p --include HEVC --exclude batch --save-path "/downloads/One Piece" --no-add-paused
```

## Response contract

All explicit command responses use this versioned envelope:

```json
{"schema_version":1,"ok":true,"data":{},"error":null}
```

Failures set `ok` to `false`, `data` to `null`, and `error` to an object containing `code`, `message`, `retryable`, and `details`. Branch on the stable error code and exit status; messages may vary by language. Stdout contains JSON only. Non-ASCII text is escaped in JSON so saved plans also roundtrip through Windows terminals with older encodings. Diagnostics belong on stderr. `--help` is human-readable help rather than a JSON response.

A plan's `data` contains `plan_version: 1`, `rule_name`, `feed_url`, `feed_path`, and `rule_definition`. `rule_definition` is the proposed qBittorrent RSS rule. Use `mikancli schema` for the full machine-readable contract. Review the saved plan again after changing configuration or intended filters; apply uses the plan's saved values.

| Exit status | Meaning / recovery |
| --- | --- |
| `0` | Success, including an empty search or an unchanged rule. |
| `1` | Upstream or network failure; inspect `retryable` before retrying. |
| `2` | Invalid arguments or plan; fix the input. |
| `3` | Resource not found or qBittorrent not configured; choose an existing resource or configure access. |
| `4` | Conflict or ambiguity; select explicit IDs or review the existing rule. |
| `5` | Partial success or unknown write outcome; read the saved rule and inspect qBittorrent before retrying. |
| `130` | Cancelled. |

Reapplying an identical plan succeeds with an `unchanged` result. A different rule with the same name fails with a conflict unless `--if-exists replace` is explicit. Review the existing rule with `rules get` before replacing it. A failed apply can leave a newly created feed in place, so treat exit status `5` as a request to inspect current state.

## Configuration and credentials

Use a separate config file for automation when appropriate. Selection order is `--config PATH`, then `MIKANCLI_CONFIG`, then the normal user config path. These environment variables override saved qBittorrent settings:

- `MIKANCLI_QBITTORRENT_URL`
- `MIKANCLI_QBITTORRENT_USERNAME`
- `MIKANCLI_QBITTORRENT_PASSWORD`

`config show` redacts the username, password, and credentials embedded in the URL. Use environment variables to supply credentials without putting them in command arguments. Existing `--setup-qbittorrent` remains available for interactive configuration.

## Compatibility

Running `mikancli` in a terminal still opens the guided flow. With redirected stdin, choose an explicit noninteractive command to avoid prompts. Legacy `mikancli KEYWORD --json` remains a draft preview with its original success response shape. It now requires a unique anime and subgroup: ambiguous matches return `AMBIGUOUS_SELECTION`, and failed lookups return an error envelope and nonzero exit status. Use `search`, `subgroups`, and `rules plan` for the versioned agent interface.

Command names are reserved as the first positional argument. To use one as a legacy search keyword, place it after `--`, for example `mikancli --json -- search`.

This interface is a CLI contract. It does not require an MCP server.
