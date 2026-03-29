import csv
import hashlib
import html
import json
import os
import re
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URLS_FILE = "extracted_urls.txt"
HASHES_FILE = "outputs/page_hashes.json"
LOG_FILE = "outputs/change_log.txt"
TITLES_FILE = "hyperlinks_with_page_titles.csv"
SUMMARY_FILE = "outputs/changes_summary.html"
REQUEST_TIMEOUT_SECONDS = 30


def now_iso_utc():
    return datetime.utcnow().isoformat()


def normalise_content(raw_content):
    """Reduce HTML noise so hashes track meaningful page changes."""
    content = raw_content
    content = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", content)
    content = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", content)
    content = re.sub(r"(?is)<!--.*?-->", " ", content)
    content = re.sub(r"(?is)<[^>]+>", " ", content)
    content = html.unescape(content)
    content = re.sub(r"\s+", " ", content).strip()
    return content


def build_retry_session():
    """Create a requests session with retry/backoff for transient failures."""
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "url-change-detector/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def load_url_to_title(titles_file):
    mapping = {}
    with open(titles_file, "r", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            mapping[row["URL"]] = row["Display Text"]
    return mapping


def load_urls(urls_file):
    with open(urls_file, "r", encoding="utf-8") as file_obj:
        return [line.strip() for line in file_obj if line.strip()]


def load_previous_hashes(hashes_file):
    if not os.path.exists(hashes_file):
        print("HASHES_FILE does not exist, starting with empty previous_hashes.")
        return {}

    try:
        with open(hashes_file, "r", encoding="utf-8") as file_obj:
            previous_hashes = json.load(file_obj)
        print("Loaded previous_hashes:", previous_hashes)
        return previous_hashes
    except (json.JSONDecodeError, ValueError) as exc:
        print("Error loading previous_hashes:", exc)
        return {}


def hash_page_content(session, url):
    response = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    normalised_content = normalise_content(response.text)
    content_hash = hashlib.sha256(normalised_content.encode("utf-8")).hexdigest()
    return content_hash, normalised_content


def process_urls(urls, url_to_title, previous_hashes, session, log_file):
    current_hashes = {}
    changed_pages = []

    with open(log_file, "w", encoding="utf-8") as log:
        for idx, url in enumerate(urls):
            try:
                content_hash, normalised_content = hash_page_content(session, url)
                current_hashes[url] = content_hash

                if idx < 2:
                    print("Sample normalised content for", url, ":", normalised_content[:500])

                if url in previous_hashes and previous_hashes[url] != content_hash:
                    title = url_to_title.get(url, url)
                    log_line = f"{now_iso_utc()} - CHANGE DETECTED: {title} ({url})\n"
                    log.write(log_line)
                    changed_pages.append((title, url))
                    print("Wrote to log:", log_line.strip())
                elif url not in previous_hashes:
                    title = url_to_title.get(url, url)
                    log_line = f"{now_iso_utc()} - NEW URL MONITORED: {title} ({url})\n"
                    log.write(log_line)
                    print("Wrote to log:", log_line.strip())
            except Exception as exc:
                log_line = f"{now_iso_utc()} - ERROR FETCHING {url}: {exc}\n"
                log.write(log_line)
                print("Wrote to log:", log_line.strip())

    return current_hashes, changed_pages


def save_hashes(hashes_file, current_hashes):
    with open(hashes_file, "w", encoding="utf-8") as file_obj:
        json.dump(current_hashes, file_obj, indent=2)


def write_no_changes_marker_if_needed(log_file, changed_pages):
    if changed_pages:
        return
    with open(log_file, "a", encoding="utf-8") as log:
        log_line = f"{now_iso_utc()} - NO CHANGES THIS RUN\n"
        log.write(log_line)
        print("Wrote to log:", log_line.strip())


def write_changes_summary(summary_file, changed_pages):
    if not changed_pages:
        return
    with open(summary_file, "w", encoding="utf-8") as file_obj:
        html_content = "<h2>The following pages have been updated:</h2><ul>"
        for title, url in changed_pages:
            html_content += f'<li><a href="{url}">{title}</a></li>'
        html_content += "</ul>"
        file_obj.write(html_content)


def main():
    print("Current working directory:", os.getcwd())
    print("Does HASHES_FILE exist?", os.path.exists(HASHES_FILE))

    url_to_title = load_url_to_title(TITLES_FILE)
    urls = load_urls(URLS_FILE)
    previous_hashes = load_previous_hashes(HASHES_FILE)
    session = build_retry_session()

    current_hashes, changed_pages = process_urls(
        urls=urls,
        url_to_title=url_to_title,
        previous_hashes=previous_hashes,
        session=session,
        log_file=LOG_FILE,
    )

    print("Saving current_hashes:", current_hashes)
    save_hashes(HASHES_FILE, current_hashes)
    write_no_changes_marker_if_needed(LOG_FILE, changed_pages)
    write_changes_summary(SUMMARY_FILE, changed_pages)
    print("Monitoring complete. Changes logged if detected.")


if __name__ == "__main__":
    main()