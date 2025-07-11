import hashlib
import json
import os
import csv
from datetime import datetime
import requests

# File paths
URLS_FILE = "extracted_urls.txt"
HASHES_FILE = "outputs/page_hashes.json"
LOG_FILE = "outputs/change_log.txt"
TITLES_FILE = "hyperlinks_with_page_titles.csv"

# Load URL to title mapping
url_to_title = {}
with open(TITLES_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        url_to_title[row['URL']] = row['Display Text']

# Load URLs from file
with open(URLS_FILE, 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

# Load previous hashes if available
if os.path.exists(HASHES_FILE):
    try:
        with open(HASHES_FILE, 'r') as f:
            previous_hashes = json.load(f)
    except (json.JSONDecodeError, ValueError):
        previous_hashes = {}
else:
    previous_hashes = {}

# Initialise dictionary to store current hashes
current_hashes = {}
changed_pages = []  # Store changed pages for email

# Open log file for appending
with open(LOG_FILE, 'a') as log:
    for url in urls:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            current_hashes[url] = content_hash
            
            # Compare with previous hash
            if url in previous_hashes:
                if previous_hashes[url] != content_hash:
                    title = url_to_title.get(url, url)  # Use URL if title not found
                    log.write(f"{datetime.utcnow().isoformat()} - CHANGE DETECTED: {title} ({url})\n")
                    changed_pages.append((title, url))
                # No need for else here - if hash matches, page hasn't changed
            else:
                # This is a new URL we haven't seen before
                title = url_to_title.get(url, url)
                log.write(f"{datetime.utcnow().isoformat()} - NEW URL MONITORED: {title} ({url})\n")
                    
        except Exception as e:
            log.write(f"{datetime.utcnow().isoformat()} - ERROR FETCHING {url}: {e}\n")
            # Don't include the hash for failed fetches
            continue

# Save current hashes for next run
with open(HASHES_FILE, 'w') as f:
    json.dump(current_hashes, f, indent=2)

# Create HTML summary of changes if any were detected
if changed_pages:
    with open("outputs/changes_summary.html", 'w', encoding='utf-8') as f:
        html_content = "<h2>The following pages have been updated:</h2><ul>"
        for title, url in changed_pages:
            html_content += f'<li><a href="{url}">{title}</a></li>'
        html_content += "</ul>"
        f.write(html_content)

print("Monitoring complete. Changes logged if detected.")