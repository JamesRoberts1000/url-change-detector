# URL Change Detector

Monitors a list of web pages and reports meaningful content changes.

The script fetches each URL, normalizes HTML into plain text, hashes the normalized content, and compares that hash against the previous run.

## How It Works

- Loads URLs from `extracted_urls.txt`.
- Loads URL-to-title mapping from `hyperlinks_with_page_titles.csv`.
- Loads previous hashes from `outputs/page_hashes.json` (if present).
- Fetches each URL with retry/backoff and a clear `User-Agent`.
- Normalizes HTML before hashing to reduce noise from scripts/styles/markup-only changes.
- Writes run results to:
  - `outputs/change_log.txt`
  - `outputs/page_hashes.json`
  - `outputs/changes_summary.html` (only when changes are detected)

## Input Files

### `extracted_urls.txt`

- One URL per line.
- Empty lines are ignored.

### `hyperlinks_with_page_titles.csv`

Must contain these columns:

- `Display Text`
- `URL`

The `Display Text` value is used in log entries and email summary output.

## Output Files

### `outputs/page_hashes.json`

- Persistent state from one run to the next.
- Maps each URL to its latest normalized-content hash.

### `outputs/change_log.txt`

- Overwritten on each run (current run only).
- Possible entries:
  - `CHANGE DETECTED: ...`
  - `NEW URL MONITORED: ...`
  - `ERROR FETCHING ...`
  - `NO CHANGES THIS RUN`

### `outputs/changes_summary.html`

- Written only when at least one page changed.
- Used by GitHub Actions email notification step.

## Run Locally

1. Ensure Python 3.10+ is installed.
2. Install dependency:

```bash
pip install requests
```

3. Run from the repository root:

```bash
python monitor_pages.py
```

## GitHub Actions Workflow

Workflow file: `.github/workflows/daily-check.yml`

It:

- Runs daily (and can be triggered manually).
- Attempts to download previous `page-hashes` artifact when available.
- Runs `monitor_pages.py`.
- Uploads updated hashes and run log as artifacts.
- Sends email only if the current run reports changes and creates `outputs/changes_summary.html`.

## Notes and Troubleshooting

- After changing hash logic (for example, normalization rules), the next run may detect many pages as changed once while a new baseline is established.
- If `page-hashes` artifact is missing (first run or expired artifact), the workflow continues with an empty hash baseline.
- Pages with highly dynamic visible content can still produce legitimate frequent changes.
