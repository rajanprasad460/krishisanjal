import os
import json
import hashlib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import urllib.parse
import time

BASE_URL = "https://bara.akc.gov.np"
NOTICE_URL = f"{BASE_URL}/notice"
JSON_FILE = "notices.json"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "close",
}


def make_session():
    session = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


session = make_session()


def get_notice_id(notice):
    source = notice.get("pdf_url", "") or (
        notice.get("title", "") + notice.get("published_date", "")
    )
    return "akc_" + hashlib.md5(source.encode("utf-8")).hexdigest()[:8]


def load_existing_notices():
    if not os.path.exists(JSON_FILE):
        return [], set()

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)

    for notice in existing:
        notice["notice_id"] = notice.get("notice_id") or get_notice_id(notice)

    existing_keys = {
        n.get("pdf_url") or f"{n.get('title')}|{n.get('published_date')}"
        for n in existing
    }

    return existing, existing_keys


def make_key(notice):
    return notice.get("pdf_url") or f"{notice.get('title')}|{notice.get('published_date')}"


def scrape_page(page):
    url = NOTICE_URL if page == 0 else f"{NOTICE_URL}?page={page}"

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch page {page}: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    notices = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        title = cells[0].get_text(" ", strip=True)
        published_date = cells[1].get_text(" ", strip=True)
        deadline = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""

        link_tag = row.find("a", href=True)
        file_url = urllib.parse.urljoin(BASE_URL, link_tag["href"]) if link_tag else ""

        if not title:
            continue

        notice = {
            "title": title,
            "published_date": published_date,
            "deadline": deadline,
            "status": "closed"
            if deadline.lower() in ["closed", "expired", "closed !!!"]
            else "active",
            "summary": f"This notice is about {title}. Deadline/status: {deadline or 'Not mentioned'}.",
            "details": (
                "This notice was published by Agriculture Knowledge Center, Bara. "
                f"Applicants should read the attached file and complete the process before: "
                f"{deadline or 'Not mentioned'}."
            ),
            "pdf_url": file_url,
            "district": "Bara",
            "source": url,
            "is_new": True,
            "downloaded": False,
            "extracted": False,
            "ai_processed": False,
        }

        notice["notice_id"] = get_notice_id(notice)
        notices.append(notice)

    return notices


def scrape_only_new_notices():
    existing, existing_keys = load_existing_notices()
    new_notices = []
    page = 0
    failed_pages = 0
    max_failed_pages = 3

    while True:
        print(f"Checking page {page}...")
        notices = scrape_page(page)

        if notices is None:
            failed_pages += 1
            print(f"Page {page} failed. Failure count: {failed_pages}/{max_failed_pages}")

            if failed_pages >= max_failed_pages:
                print("Too many failed pages. Stopping scraper.")
                break

            page += 1
            time.sleep(5)
            continue

        failed_pages = 0

        if not notices:
            break

        page_new_count = 0

        for notice in notices:
            key = make_key(notice)
            if key not in existing_keys:
                print(f"New notice found: {notice['title']}")
                existing_keys.add(key)
                new_notices.append(notice)
                page_new_count += 1

        if page_new_count == 0:
            print("No new notices on this page. Stopping early.")
            break

        page += 1
        time.sleep(3)

    updated = new_notices + existing

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    print(f"Added {len(new_notices)} new notices.")
    print(f"Total notices now: {len(updated)}.")
    return len(new_notices)


if __name__ == "__main__":
    scrape_only_new_notices()