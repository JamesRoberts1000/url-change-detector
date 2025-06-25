import hashlib
import json
import os
from datetime import datetime
import requests

# File paths
URLS_FILE = "extracted_urls.txt"
HASHES_FILE = "outputs/page_hashes.json"
LOG_FILE = "outputs/change_log.txt"

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
                    log.write(f"{datetime.utcnow().isoformat()} - CHANGE DETECTED: {url}\n")
                else:
                    log.write(f"{datetime.utcnow().isoformat()} - NEW URL MONITORED: {url}\n")
                    
        except Exception as e:
            log.write(f"{datetime.utcnow().isoformat()} - ERROR FETCHING {url}: {e}\n")

# Save current hashes for next run
with open(HASHES_FILE, 'w') as f:
    json.dump(current_hashes, f, indent=2)

print("Monitoring complete. Changes logged if detected.")