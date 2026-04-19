# Automation Engineering: Practicum Proposal

## Student Information
- **Name:** Jianhua Deng
- **Instructor:** Alex Washburn

---

## 1. Project Title

Automated Mikan RSS Feed and Rule Manager for qBittorrent

---

## 2. Overview / Abstract
Anime torrent users who rely on qBittorrent RSS automation still have to do several manual steps before that automation is in place. They must search Mikan (`mikanani.me`) to find the correct series page or RSS feed, compare similar results to choose the right show, copy the feed into qBittorrent, and then manually create RSS download rules so new episodes download automatically. Repeating this process for each new show is tedious and error-prone.

This project proposes a Python-based command-line interface (CLI) tool that automates that workflow. Instead of importing or syncing a user's watchlist from MyAnimeList or AniList, the tool will ask the user for a keyword, search Mikan, present matching results, and let the user choose the correct series. After that selection, the tool will automatically resolve the RSS feed, generate the appropriate qBittorrent RSS download rule, allow the user to define include and exclude words for filtering releases, assign the save location, and push the configuration through the qBittorrent Web API. The result is a focused automation that removes the repetitive manual work of finding feeds and setting up qBittorrent one show at a time.

---

## 3. Task Description

### 3.1 Manual Process Description

The current manual workflow for setting up automated downloads for a new anime involves the following steps:

1. Open Mikan in a browser.
2. Type the anime title or a related keyword into the site's search interface.
3. Inspect the search results to determine which entry matches the intended show.
4. Check release naming, subtitle group, or resolution clues to avoid selecting the wrong feed.
5. Open the matching page and locate the RSS feed URL.
6. Open qBittorrent and add the RSS feed manually.
7. Create an RSS download rule manually so matching episodes are downloaded automatically.
8. Enter include words and exclude words manually to control which releases are accepted or rejected.
9. Optionally choose or create a save folder for that series.

This is performed by the user whenever they want to automate downloads for a new series.

### 3.2 Problem Statement

The current process has several pain points:

- **Repetitive manual searching** - the same search-and-verify workflow is repeated every time the user wants a new show.
- **Ambiguous search results** - similar titles, alternate spellings, and season labels can make it easy to choose the wrong entry.
- **Slow feed discovery** - locating the actual RSS URL often takes several clicks after the search itself.
- **Language and UI friction** - tracker interfaces may be harder to navigate quickly for users unfamiliar with the site's language or layout.
- **Manual qBittorrent setup** - after finding the feed, the user still has to add it and create RSS rules by hand.
- **Rule configuration errors** - mistakes in filters, folder paths, or naming can lead to missed or incorrect downloads.

### 3.3 Automation Goal

A successful automation will allow the user to:

- Enter a keyword once on the command line and automatically search Mikan.
- Review search results and choose the correct series when the match is ambiguous.
- Optionally provide include and exclude words that should be applied to the RSS download rule.
- Automatically add the resolved RSS feed to qBittorrent and create the associated download rule.
- Reduce the full setup process for one show from several minutes of manual browsing and clicking to a short guided command.
- Standardize feed lookup, rule creation, and save-path setup so the process is consistent across shows.

---

## 4. Inputs to the Task

### 4.1 Input Sources

- **User keyword** - a title, partial title, or search phrase entered on the command line.
- **User selection** - the result chosen from a ranked list of matches.
- **Optional filters** - subtitle group, resolution, or result limit.
- **Rule keywords** - optional include words and exclude words supplied by the user for qBittorrent rule filtering.
- **Mikan search and RSS pages** (`mikanani.me`) - used to locate matching results and feed URLs.
- **qBittorrent Web API** - used to create RSS feeds and download rules automatically.

### 4.2 Input Formats

- Plain-text CLI arguments for the keyword and optional filters.
- Numeric or textual user input for selecting one search result.
- Plain-text user input for include-word and exclude-word lists.
- HTML pages if scraping is required to search or resolve the feed URL.
- XML/RSS 2.0 if the tool validates a discovered feed before using it.
- JSON or form-based HTTP payloads for qBittorrent Web API requests.

### 4.3 Input Frequency

The tool is primarily run on demand whenever the user wants to set up automated downloads for a new show.

---

## 5. Outputs and End States

### 5.1 Outputs

- Ranked candidate search results for the user's keyword.
- The selected RSS feed URL for the chosen series.
- A new RSS feed subscription added to qBittorrent.
- A qBittorrent RSS download rule configured for the selected show, including optional include and exclude keyword filters.
- A console summary describing what feed and rule were created.

### 5.2 Output Formats

- Console output in plain text.
- Optional JSON output for scripting or downstream automation.
- qBittorrent internal state updated through its Web API.

### 5.3 End State Conditions

The task is complete when:

1. The user's keyword has been searched against Mikan.
2. The user has selected the intended series from the returned candidates.
3. A valid RSS feed URL has been identified for that series.
4. qBittorrent has been updated with the feed and its associated download rule.
5. The tool reports success or a clear error message if any step fails.

---

## 6. Data Transformations

### 6.1 Transformation Steps

- **Input normalization** - clean and normalize the user's keyword to improve matching.
- **Search execution** - submit the keyword to Mikan search endpoints or scrape the search pages.
- **Parsing / extraction** - parse returned HTML or RSS data to extract titles, links, and candidate feed URLs.
- **Filtering / ranking** - apply optional filters such as subtitle group or resolution and rank the results for user selection.
- **Feed resolution** - convert the selected result into a usable RSS feed URL and validate it.
- **Rule generation** - build the qBittorrent rule name, include-word filter, exclude-word filter, and save path based on the selected show and user preferences.
- **Formatting / API submission** - send the feed and rule configuration to qBittorrent and print a summary to the console.

### 6.2 Transformation Example

**Example:** User searches for `solo leveling` with a preference for `1080p`, includes `SubsPlease`, and excludes `720p`.

**Input (CLI):**

```bash
python autofeedsync.py "solo leveling" --resolution 1080p --include SubsPlease --exclude 720p
```

**Transformation:**

1. Normalize the keyword to `solo leveling`.
2. Search Mikan for matching entries.
3. Extract candidate titles and RSS links from the search results.
4. Prefer candidates whose titles or recent entries include `1080p`.
5. Present the candidate list to the user and let them choose the intended series.
6. Resolve the final RSS feed URL from the chosen result.
7. Build a qBittorrent rule that requires `SubsPlease` and rejects `720p`.
8. Create the qBittorrent RSS feed and download rule automatically.

**Output (console):**

```text
Source: Mikan
Best match: Solo Leveling
RSS: https://mikanani.me/RSS/Bangumi?bangumiId=...
qBittorrent feed added successfully
qBittorrent rule created: Solo Leveling
Include words: SubsPlease
Exclude words: 720p
```

---

## 7. Proposed Automation Approach

### 7.1 Techniques

- **HTTP requests** - query Mikan search pages or feed endpoints.
- **Web scraping** - use lightweight scraping to extract result titles, subgroup links, and RSS URLs from Mikan pages.
- **Interactive CLI selection** - present ranked candidates and let the user confirm which show should be automated.
- **Rule customization** - let the user supply include and exclude words that map cleanly onto qBittorrent RSS rule fields.
- **RSS validation** - fetch the chosen feed to confirm it is well-formed and relevant.
- **API interaction** - send feed and rule configuration to qBittorrent through its Web API.
- **CLI scripting** - implement the workflow as a Python command-line program with flags for filters and output mode.

### 7.2 Tools and Technologies

| Category | Tool / Technology |
|---|---|
| Programming Language | Python 3.10+ |
| HTTP | requests |
| HTML Parsing | BeautifulSoup4, lxml |
| RSS Parsing | feedparser |
| CLI Interface | argparse or typer |
| Matching Logic | Python standard library (`re`, `difflib`) |
| qBittorrent Integration | qbittorrent-api or direct Web API requests |
| Logging | Python logging module or rich |

### 7.3 System Architecture

The system follows a five-stage pipeline:

1. **CLI Input Handler** - reads the keyword and optional filters from the command line.
2. **Search Adapter** - queries Mikan and collects raw search results.
3. **Result Resolver** - parses candidate entries, ranks matches, and prompts the user to choose one.
4. **Rule Builder** - resolves the final RSS URL and builds the qBittorrent feed, include-word filter, exclude-word filter, and save-path configuration.
5. **qBittorrent Pusher** - authenticates with qBittorrent and creates the feed and download rule.

Each stage can be implemented as a separate Python module so the Mikan search, parsing, selection, and qBittorrent integration logic can be tested independently.

---

## 8. Pseudocode for Automated Task

```text
BEGIN

  ARGS = PARSE command-line arguments
  keyword = ARGS.keyword
  group_filter = ARGS.group
  resolution_filter = ARGS.resolution
  include_words = ARGS.include_words
  exclude_words = ARGS.exclude_words

  mikan_results = search_mikan(keyword)
  candidates = extract_rss_candidates(mikan_results, source="Mikan")

  candidates = filter_candidates(candidates, group_filter, resolution_filter)
  ranked = rank_candidates(candidates, keyword)

  IF ranked is empty:
    PRINT "No matching RSS feed found."
    EXIT

  selection = PROMPT user to choose a candidate
  chosen = ranked[selection]

  feed_url = resolve_feed_url(chosen)
  validate_feed(feed_url)

  rule_name = build_rule_name(chosen)
  must_contain = build_include_filter(chosen, group_filter, resolution_filter, include_words)
  must_not_contain = build_exclude_filter(exclude_words)
  save_path = build_save_path(chosen)

  QB_CLIENT = CONNECT to qBittorrent Web API
  QB_CLIENT.add_feed(url=feed_url, name=rule_name)
  QB_CLIENT.set_rule(
    name = rule_name,
    must_contain = must_contain,
    must_not_contain = must_not_contain,
    save_path = save_path,
    feeds = [feed_url],
    enabled = TRUE
  )

  PRINT success summary

END
```

---

## 9. Testing and Validation Plan

**Test Cases:**

- Unit tests for keyword normalization and matching logic.
- Unit tests for HTML parsing to verify correct extraction of titles and RSS links from saved Mikan sample pages.
- Unit tests for ranking logic to ensure the intended result is selected when multiple similar titles exist.
- Unit tests for qBittorrent payload generation so feed names, include/exclude filters, rules, and save paths are constructed correctly.
- Integration tests that run the CLI against known search terms, select a result, and confirm the feed and rule appear in qBittorrent.
- Edge-case tests for empty results, alternate spellings, sequel titles, ambiguous keywords, duplicate runs, and conflicting include/exclude words.

**Expected vs. Actual Results:**

- For each test keyword, compare the selected RSS feed URL against a manually verified expected result.
- Confirm that invalid or malformed candidate URLs are rejected during validation.
- After submission, query qBittorrent to verify that the feed and RSS rule exist with the expected include and exclude settings.

**Error Handling Strategies:**

- Network errors: retry with backoff and return a clear error if the site is unreachable.
- No results found: return a clean message instead of crashing.
- Ambiguous results: print multiple candidates rather than forcing a low-confidence choice.
- Parsing failures: log which Mikan page failed and stop with a clear error if no valid candidate can be extracted.
- qBittorrent authentication or API errors: stop with a clear error message and do not leave partially configured rules without reporting them.

---

## 10. References

- Mikan Project: https://mikanani.me/
- qBittorrent Web API documentation: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API
- qbittorrent-api Python library: https://pypi.org/project/qbittorrent-api/
- feedparser Python library: https://pypi.org/project/feedparser/
- Beautiful Soup documentation: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- requests Python library: https://requests.readthedocs.io/

---

## Instructor Feedback
*(To be completed by instructor)*

- **Approval Status:**
- **Comments:**
- **Suggested Improvements:**
